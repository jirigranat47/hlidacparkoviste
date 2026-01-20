from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os

from threading import Thread
import main as worker_module  # Importujeme modul workeru

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Verze aplikace pro cache-busting (načítá z ENV nebo použije timestamp)
import time
APP_VERSION = os.getenv("APP_VERSION", str(int(time.time())))

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
    if not conn:
        return [] # V případě chyby připojení vrátí prázdný seznam

    try:
        cur = conn.cursor()
        # Dotaz pro získání průměrné obsazenosti za každou hodinu
        # v posledních 24 hodinách. Data jsou seřazena chronologicky.
        query = """
            SELECT
                date_trunc('hour', timestamp) AS hour_bucket,
                ROUND(AVG(count))::integer AS avg_count
            FROM
                parkoviste_zaznamy
            WHERE
                timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY
                hour_bucket
            ORDER BY
                hour_bucket;
        """
        cur.execute(query)
        data = cur.fetchall()
        return data
    except Exception as e:
        print(f"API Error in get_stats: {e}")
        return [] # V případě chyby v dotazu také vrátí prázdný seznam
    finally:
        # Zajistíme, že se spojení vždy uzavře
        if conn:
            cur.close()
            conn.close()

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

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "version": APP_VERSION})