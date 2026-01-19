import os
import time
import requests
import psycopg2
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from ultralytics import YOLO
from dotenv import load_dotenv

# Načtení environment proměnných z .env souboru (pokud existuje)
load_dotenv()

# --- KONFIGURACE ---
URL_STRANKY = "https://www.kostelecno.cz/webkamera"
ALT_TEXT = "Webkamera na náměstí"
SLOZKA_PRO_FOTKY = "webcam_archive"
INTERVAL_SEKUNDY = 600  # 10 minut
POCET_VOLNYCH_MIST = 103

# ID tříd v YOLO (COCO dataset): 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 7]

# Inicializace modelu (verze 'n' - nano je nejrychlejší a pro tento účel stačí)
model = YOLO('yolov8n.pt')

if not os.path.exists(SLOZKA_PRO_FOTKY):
    os.makedirs(SLOZKA_PRO_FOTKY)

# --- DATABÁZOVÉ FUNKCE ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database=os.getenv("DB_NAME", "parkoviste_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "tajne_heslo")
        )
        return conn
    except Exception as e:
        print(f"Chyba připojení k DB: {e}")
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
            # timestamp_str je ve formátu "%Y%m%d_%H%M%S", převedeme na datetime
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            cur = conn.cursor()
            cur.execute("INSERT INTO parkoviste_zaznamy (timestamp, count) VALUES (%s, %s)", (dt, count))
            conn.commit()
            cur.close()
            conn.close()
            print(f"Uloženo do DB: {dt} - {count} aut")
        except Exception as e:
            print(f"Chyba při ukládání do DB: {e}")

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
        
        # 2. Uložení fotky
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(SLOZKA_PRO_FOTKY, f"parking_{timestamp}.jpg")
        with open(filepath, 'wb') as f:
            f.write(img_data)

        # 3. DETEKCE AUT
        # stream=True šetří paměť, classes omezí detekci jen na vozidla
        results = model.predict(source=filepath, classes=VEHICLE_CLASSES, conf=0.25, save=True)
        
        # Spočítáme počet detekovaných objektů
        count = 0
        for r in results:
            count += len(r.boxes)

        print(f"[{datetime.now()}] Detekováno vozidel: {count}")
        
        # 4. ZÁPIS DO DATABÁZE
        save_to_db(timestamp, count)

    except Exception as e:
        print(f"Chyba: {e}")

if __name__ == "__main__":
    print("Čekám 10s na start databáze...")
    time.sleep(10)
    init_db()
    print("Spouštím monitoring parkoviště...")
    while True:
        stahni_a_detekuj()
        print(f"Čekám {INTERVAL_SEKUNDY/60} minut do další kontroly...")
        time.sleep(INTERVAL_SEKUNDY)