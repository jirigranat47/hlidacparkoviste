import os
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import cv2
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
from ultralytics import YOLO
from dotenv import load_dotenv

# Načtení environment proměnných z .env souboru (pokud existuje)
load_dotenv()

# --- KONFIGURACE ---
URL_STRANKY = "https://www.kostelecno.cz/webkamera"
ALT_TEXT = "Webkamera na náměstí"
SLOZKA_BASE = "webcam_archive"
SLOZKA_ORIGINAL = os.path.join(SLOZKA_BASE, "original")
SLOZKA_ANNOTATED = os.path.join(SLOZKA_BASE, "annotated")
INTERVAL_SEKUNDY = int(os.getenv("INTERVAL_SEKUNDY", 300))  # 5 minut
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", 7))  # Jak dlouho uchovávat fotky

# ID tříd v YOLO (COCO dataset): 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 7]

# Nastavení citlivosti detektoru (možné přepsat přes ENV)
YOLO_CONF = float(os.getenv("YOLO_CONF", 0.25))
YOLO_IOU = float(os.getenv("YOLO_IOU", 0.7))

# Inicializace modelu
model = YOLO('yolov8n.pt')

# Vytvoření složek
for folder in [SLOZKA_ORIGINAL, SLOZKA_ANNOTATED]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "parkoviste_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tajne_heslo")

# --- DATABÁZOVÉ FUNKCE ---
def get_db_connection():
    try:
        if DATABASE_URL:
            return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        else:
            return psycopg2.connect(
                host=DB_HOST, database=DB_NAME, 
                user=DB_USER, password=DB_PASSWORD,
                cursor_factory=RealDictCursor
            )
    except Exception as e:
        print(f"API DB Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS parkoviste_zaznamy (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("Databáze inicializována.")
        except Exception as e:
            print(f"Chyba inicializace DB: {e}")

def save_to_db(timestamp_str, count):
    conn = get_db_connection()
    if conn:
        try:
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            cur = conn.cursor()
            cur.execute("INSERT INTO parkoviste_zaznamy (timestamp, count) VALUES (%s, %s)", (dt, count))
            conn.commit()
            cur.close()
            conn.close()
            print(f"Uloženo do DB: {dt} - {count} aut")
        except Exception as e:
            print(f"Chyba při ukládání do DB: {e}")

# --- POMOCNÉ FUNKCE ---
def cleanup_old_images():
    """Smaže obrázky starší než RETENTION_DAYS ze složek archive."""
    limit_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0
    
    for folder in [SLOZKA_ORIGINAL, SLOZKA_ANNOTATED]:
        if not os.path.exists(folder):
            continue
            
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            try:
                # Smazat pokud je to soubor a je starší než limit
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < limit_date:
                        os.remove(filepath)
                        deleted_count += 1
            except Exception as e:
                print(f"Chyba při mazání souboru {filepath}: {e}")
    
    if deleted_count > 0:
        print(f"[{datetime.now()}] CLEANUP: Smazáno {deleted_count} starých obrázků.")

def stahni_a_detekuj():
    try:
        # 1. Získání URL obrázku
        response = requests.get(URL_STRANKY, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        img_tag = soup.find('img', alt=ALT_TEXT)
        
        if not img_tag:
            print("Obrázek nenalezen.")
            return

        img_url = urljoin(URL_STRANKY, img_tag['src'])
        img_data = requests.get(img_url).content
        
        # 2. Uložení originální fotky
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"parking_{timestamp}.jpg"
        original_path = os.path.join(SLOZKA_ORIGINAL, filename)
        
        with open(original_path, 'wb') as f:
            f.write(img_data)
        
        # 3. DETEKCE AUT
        # save=False, aby se nevytvářely runs/detect složky
        # classes omezí detekci jen na vozidla
        results = model.predict(source=original_path, classes=VEHICLE_CLASSES, conf=YOLO_CONF, iou=YOLO_IOU, save=False, verbose=False)
        
        # Spočítáme počet detekovaných objektů a získáme plot
        count = 0
        result_plot = None
        
        for r in results:
            count += len(r.boxes)
            # Vykreslení bounding boxů do obrázku
            # plot() vrací numpy array (BGR)
            result_plot = r.plot()

        print(f"[{datetime.now()}] Detekováno vozidel: {count}")
        
        # Uložení anotovaného obrázku
        if result_plot is not None:
            annotated_path = os.path.join(SLOZKA_ANNOTATED, filename)
            cv2.imwrite(annotated_path, result_plot)
        else:
             # Pokud se nic nenašlo nebo nastala chyba plotování, můžeme uložit original i do annotated, nebo nic.
             # Zde uložíme alespoň original, aby bylo vidět co se dělo, i když bez boxů (když boxes=0, plot vrací čistý obr).
             # Ale result_plot by měl být validní i když boxes=0.
             pass

        
        # 4. ZÁPIS DO DATABÁZE
        save_to_db(timestamp, count)

        # 5. Úklid starých fotek
        cleanup_old_images()

    except Exception as e:
        print(f"Chyba: {e}")

if __name__ == "__main__":
    print("Čekám 10s na start databáze...")
    time.sleep(10)
    init_db()
    
    # Prvotní úklid při startu
    print("Spouštím úklid starých souborů...")
    cleanup_old_images()
    
    print("Spouštím monitoring parkoviště...")
    while True:
        stahni_a_detekuj()
        print(f"Čekám {INTERVAL_SEKUNDY/60} minut do další kontroly...")
        time.sleep(INTERVAL_SEKUNDY)

def start_worker_loop():
    """Funkce pro spuštění workeru v samostatném vlákně"""
    print("Worker: Čekám 5s na start databáze (zpožděný start)...")
    time.sleep(5) # Krátké čekání, api.py už bude běžet
    init_db()
    
    print("Worker: Spouštím úklid starých souborů...")
    cleanup_old_images()
    
    print("Worker: Spouštím monitoring parkoviště...")
    while True:
        try:
            stahni_a_detekuj()
        except Exception as e:
            print(f"Worker Error: {e}")
        
        print(f"Worker: Čekám {INTERVAL_SEKUNDY/60} minut do další kontroly...")
        time.sleep(INTERVAL_SEKUNDY)