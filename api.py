from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os

from threading import Thread
import main as worker_module  # Importujeme modul workeru

app = FastAPI()

# Konfigurace připojení
# Railway poskytuje 'DATABASE_URL', lokálně používáme jednotlivé proměnné nebo také DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "parkoviste_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tajne_heslo")

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



@app.get("/stats")
def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    # Vybere posledních 100 záznamů
    cur.execute("SELECT timestamp, count FROM parkoviste_zaznamy ORDER BY timestamp DESC LIMIT 100")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

@app.get("/current")
def get_current():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT count FROM parkoviste_zaznamy ORDER BY timestamp DESC LIMIT 1")
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data or {"count": 0}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
def startup_event():
    # Spustíme worker ve vedlejším vlákně
    # Daemon=True zajistí, že se vlákno ukončí, když skončí hlavní proces
    worker_thread = Thread(target=worker_module.start_worker_loop, daemon=True)
    worker_thread.start()
    print("System: Worker vlákno spuštěno.")

@app.get("/")
def read_root():
    return FileResponse('static/index.html')