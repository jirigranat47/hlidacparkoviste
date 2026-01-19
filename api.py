from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI()

# Konfigurace připojení (stejná jako u workeru)
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "parkoviste_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tajne_heslo")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, 
        user=DB_USER, password=DB_PASSWORD,
        cursor_factory=RealDictCursor # Vrací data jako slovníky (JSON ready)
    )



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

@app.get("/")
def read_root():
    return FileResponse('static/index.html')