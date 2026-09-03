import os
import time
import logging
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
import parking_mask # Import definice masky

# --- LOGOVÁNÍ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
IMGSZ = int(os.getenv("IMGSZ", 1280))

# Inicializace modelu
model = YOLO('yolo26l.pt')

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
            # Pro Railway/produkci přidáme sslmode=require pokud není v URL
            if "sslmode=" not in DATABASE_URL:
                separator = "&" if "?" in DATABASE_URL else "?"
                url_with_ssl = f"{DATABASE_URL}{separator}sslmode=require"
                return psycopg2.connect(url_with_ssl, cursor_factory=RealDictCursor)
            return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        else:
            return psycopg2.connect(
                host=DB_HOST, database=DB_NAME, 
                user=DB_USER, password=DB_PASSWORD,
                cursor_factory=RealDictCursor
            )
    except Exception as e:
        logger.error(f"DB Connection Error: {e}")
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
            logger.info("Databáze inicializována.")
        except Exception as e:
            logger.error(f"Chyba inicializace DB: {e}")
        finally:
            if conn:
                cur.close()
                conn.close()
    else:
        logger.error("Nelze inicializovat DB - nepodařilo se připojit.")

def save_to_db(timestamp_str, count):
    conn = get_db_connection()
    if conn:
        try:
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            cur = conn.cursor()
            cur.execute("INSERT INTO parkoviste_zaznamy (timestamp, count) VALUES (%s, %s)", (dt, count))
            conn.commit()
            logger.info(f"Uloženo do DB: {dt} - {count} aut")
        except Exception as e:
            logger.error(f"Chyba při ukládání do DB: {e}")
        finally:
            if conn:
                cur.close()
                conn.close()
    else:
        logger.error(f"Data neuložena - nepodařilo se připojit k DB (count: {count})")

# --- POMOCNÉ FUNKCE ---
def cleanup_old_images():
    """Smaže obrázky starší než RETENTION_DAYS ze složek archive."""
    limit_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0
    logger.info(f"CLEANUP: Mazání starých obrázků (starší než {RETENTION_DAYS} dnů, {limit_date}).")
    
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
                logger.error(f"Chyba při mazání souboru {filepath}: {e}")
    
    if deleted_count > 0:
        logger.info(f"CLEANUP: Smazáno {deleted_count} starých obrázků.")

def stahni_a_detekuj():
    try:
        # 1. Získání URL obrázku
        response = requests.get(URL_STRANKY, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        img_tag = soup.find('img', alt=ALT_TEXT)
        
        if not img_tag:
            logger.warning("Obrázek nenalezen na stránce.")
            return

        img_url = urljoin(URL_STRANKY, img_tag['src'])
        img_data = requests.get(img_url, timeout=15).content
        
        # 2. Uložení originální fotky
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"parking_{timestamp}.jpg"
        original_path = os.path.join(SLOZKA_ORIGINAL, filename)
        
        with open(original_path, 'wb') as f:
            f.write(img_data)
            
        # 2b. Načteme obrázek pro vizualizaci a kontrolu
        frame = cv2.imread(original_path)
        
        # 3. DETEKCE AUT
        # Detekujeme na celém obrázku pro zachování kontextu (model lépe pozná auta)
        print('Čas za hájení detekce:', datetime.now())
        results = model.predict(source=original_path, classes=VEHICLE_CLASSES, conf=YOLO_CONF, iou=YOLO_IOU, imgsz=IMGSZ, save=False, verbose=False)
        print('Čas ukončení detekce:', datetime.now())
        
        # Spočítáme počet detekovaných objektů UVNITŘ zóny
        count = 0
        
        # Připravíme kopii obrázku pro vykreslení
        annotated_frame = frame.copy()

        # Získání aktuálních parkovacích zón (včetně případných offsetů z .env / souboru)
        current_zones = parking_mask.get_parking_zones()

        # Vykreslení hranice parkovacích zón (zeleně - definice oblasti)
        cv2.polylines(annotated_frame, current_zones, isClosed=True, color=(0, 255, 0), thickness=2)

        for r in results:
            boxes = r.boxes
            for box in boxes:                
                # Získání souřadnic boxu
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Výpočet středu boxu
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                #print("Nalezeno vozidlo: ", cx, cy)
                
                # Kontrola, zda je střed uvnitř NĚKTERÉ z parkovacích zón
                is_in_zone = False
                for zone in current_zones:
                    # measureDist=False vrací +1 (uvnitř), -1 (venku), 0 (na hraně)
                    if cv2.pointPolygonTest(zone, (cx, cy), False) >= 0:
                        is_in_zone = True
                        #print("Uvnitř zóny")
                        break
                
                if is_in_zone:
                    count += 1
                    # Vykreslíme box (zeleně pro započítaná auta)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Můžeme přidat i label
                    # conf = float(box.conf)
                    # cv2.putText(annotated_frame, f"{conf:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    # Auta mimo zónu můžeme ignorovat nebo vykreslit červeně pro debug
                    # Pro finální nasazení asi spíše nevykreslovat, nebo vykreslit tence šedě
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 1)

        result_plot = annotated_frame

        logger.info(f"Detekováno vozidel: {count}")
        
        # Uložení anotovaného obrázku
        if result_plot is not None:
            annotated_path = os.path.join(SLOZKA_ANNOTATED, filename)
            cv2.imwrite(annotated_path, result_plot)
        
        # 4. ZÁPIS DO DATABÁZE
        save_to_db(timestamp, count)

        # 5. Úklid starých fotek
        cleanup_old_images()

    except Exception as e:
        logger.error(f"Chyba ve stahni_a_detekuj: {e}")

if __name__ == "__main__":
    logger.info("Čekám 5s na start databáze...")
    time.sleep(5)
    init_db()
    
    # Prvotní úklid při startu
    logger.info("Spouštím úklid starých souborů...")
    cleanup_old_images()
    
    logger.info("Spouštím monitoring parkoviště...")
    stahni_a_detekuj()    

def start_worker_loop():
    """Funkce pro spuštění workeru v samostatném vlákně"""
    logger.info("Worker: Čekám 5s na start databáze (zpožděný start)...")
    time.sleep(5) # Krátké čekání, api.py už bude běžet
    init_db()
    
    logger.info("Worker: Spouštím úklid starých souborů...")
    cleanup_old_images()
    
    logger.info("Worker: Spouštím monitoring parkoviště...")
    while True:
        try:
            stahni_a_detekuj()
        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
        
        logger.info(f"Worker: Čekám {INTERVAL_SEKUNDY/60} minut do další kontroly...")
        time.sleep(INTERVAL_SEKUNDY)