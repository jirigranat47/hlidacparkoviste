from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import timezone, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi.responses import FileResponse
import latest_image_service

from threading import Thread
import main as worker_module  # Importujeme modul workeru

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_template_context(request: Request, **kwargs):
    """Helper function to create template context with common variables."""
    is_localhost = request.url.hostname in ["localhost", "127.0.0.1"]
    context = {
        "request": request,
        "version": APP_VERSION,
        "is_localhost": is_localhost
    }
    context.update(kwargs)
    return context

def get_parking_status():
    """
    Vypočítá aktuální stav parkování (placené/zdarma) a čas do změny stavu.
    
    Pravidla:
    - Pondělí-Pátek: 6:00-18:00 placené, jinak zdarma
    - Sobota: 6:00-12:00 placené, jinak zdarma
    - Neděle: celý den zdarma
    
    Ceny:
    - První hodina: 10 Kč
    - Každá další hodina: 20 Kč
    
    Returns:
        dict: Informace o stavu parkování
    """
    prague_tz = ZoneInfo("Europe/Prague")
    now = datetime.now(prague_tz)
    
    weekday = now.weekday()  # 0=pondělí, 6=neděle
    hour = now.hour
    minute = now.minute
    
    is_paid = False
    next_change = None
    
    # Neděle (6) - celý den zdarma
    if weekday == 6:
        is_paid = False
        # Další změna je pondělí v 6:00
        days_until_monday = (7 - weekday) % 7 or 7  # 1 den
        next_change = now.replace(hour=6, minute=0, second=0, microsecond=0)
        next_change = next_change + timedelta(days=days_until_monday)
    
    # Sobota (5)
    elif weekday == 5:
        if 6 <= hour < 12:
            is_paid = True
            # Další změna je dnes v 12:00
            next_change = now.replace(hour=12, minute=0, second=0, microsecond=0)
        elif hour < 6:
            is_paid = False
            # Další změna je dnes v 6:00
            next_change = now.replace(hour=6, minute=0, second=0, microsecond=0)
        else:  # hour >= 12
            is_paid = False
            # Další změna je pondělí v 6:00
            next_change = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=2)
    
    # Pondělí-Pátek (0-4)
    else:
        if 6 <= hour < 18:
            is_paid = True
            # Další změna je dnes v 18:00
            next_change = now.replace(hour=18, minute=0, second=0, microsecond=0)
        elif hour < 6:
            is_paid = False
            # Další změna je dnes v 6:00
            next_change = now.replace(hour=6, minute=0, second=0, microsecond=0)
        else:  # hour >= 18
            is_paid = False
            # Další změna je zítra v 6:00 (nebo v pondělí pokud je pátek)
            days_to_add = 3 if weekday == 4 else 1  # Pátek -> pondělí
            next_change = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=days_to_add)
    
    # Vypočítat čas do změny
    time_diff = next_change - now
    hours_until = int(time_diff.total_seconds() // 3600)
    minutes_until = int((time_diff.total_seconds() % 3600) // 60)
    
    return {
        "is_paid": is_paid,
        "next_change": next_change.isoformat(),
        "time_until_change": {
            "hours": hours_until,
            "minutes": minutes_until,
            "total_seconds": int(time_diff.total_seconds())
        },
        "pricing": {
            "first_hour": 10,
            "additional_hour": 20,
            "currency": "Kč"
        },
        "schedule": {
            "weekdays": "Po-Pá 6:00-18:00",
            "saturday": "So 6:00-12:00",
            "sunday": "Zdarma"
        }
    }

# Verze aplikace pro cache-busting
APP_VERSION = "1.0.6"
print(f"System: Verze aplikace: {APP_VERSION}")

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
def get_stats(detail: bool = False):
    conn = get_db_connection()
    if not conn:
        return [] # V případě chyby připojení vrátí prázdný seznam

    try:
        cur = conn.cursor()
        # Dotaz pro získání průměrné obsazenosti za každou hodinu
        # v posledních 24 hodinách. Data jsou seřazena chronologicky.
        if detail:
             query = """
                SELECT
                    timestamp,
                    count
                FROM
                    parkoviste_zaznamy
                WHERE
                    timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY
                    timestamp;
            """
        else:
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
        
        # Konverze na dict a přidání UTC časové zóny
        result = []
        for row in data:
            row_dict = dict(row)
            if row_dict.get('hour_bucket'):
                row_dict['hour_bucket'] = row_dict['hour_bucket'].replace(tzinfo=timezone.utc)
            if row_dict.get('timestamp'):
                row_dict['timestamp'] = row_dict['timestamp'].replace(tzinfo=timezone.utc)
            result.append(row_dict)
            
        return result
    except Exception as e:
        print(f"API Error in get_stats: {e}")
        return [] # V případě chyby v dotazu také vrátí prázdný seznam
    finally:
        # Zajistíme, že se spojení vždy uzavře
        if conn:
            cur.close()
            conn.close()

@app.get("/stats/history")
def get_stats_history(date: str = None, detail: bool = False):
    """
    Vrátí průměrnou obsazenost za každou hodinu pro vybraný den.
    Parametr date musí být ve formátu YYYY-MM-DD.
    """
    from datetime import datetime, date as dt_date
    
    # Validace parametru date
    if not date:
        return {"error": "Parametr 'date' je povinný (formát: YYYY-MM-DD)"}, 400
    
    try:
        # Parsování data
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Kontrola, zda není datum v budoucnosti
        if selected_date > dt_date.today():
            return {"error": "Nelze zobrazit data z budoucnosti"}, 400
            
    except ValueError:
        return {"error": "Neplatný formát data. Použijte YYYY-MM-DD"}, 400
    
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        # Dotaz pro získání průměrné obsazenosti za každou hodinu vybraného dne
        if detail:
            query = """
                SELECT
                    timestamp,
                    count
                FROM
                    parkoviste_zaznamy
                WHERE
                    timestamp >= %s::date
                    AND timestamp < %s::date + INTERVAL '1 day'
                ORDER BY
                    timestamp;
            """
            cur.execute(query, (date, date))
        else:
            query = """
                SELECT
                    date_trunc('hour', timestamp) AS hour_bucket,
                    ROUND(AVG(count))::integer AS avg_count
                FROM
                    parkoviste_zaznamy
                WHERE
                    timestamp >= %s::date
                    AND timestamp < %s::date + INTERVAL '1 day'
                GROUP BY
                    hour_bucket
                ORDER BY
                    hour_bucket;
            """
            cur.execute(query, (date, date))
        data = cur.fetchall()
        
        # Konverze na dict a přidání UTC časové zóny
        result = []
        for row in data:
            row_dict = dict(row)
            if row_dict.get('hour_bucket'):
                row_dict['hour_bucket'] = row_dict['hour_bucket'].replace(tzinfo=timezone.utc)
            if row_dict.get('timestamp'):
                row_dict['timestamp'] = row_dict['timestamp'].replace(tzinfo=timezone.utc)
            result.append(row_dict)
            
        return result
    except Exception as e:
        print(f"API Error in get_stats_history: {e}")
        return []
    finally:
        if conn:
            cur.close()
            conn.close()

@app.get("/stats/weekday")
def get_stats_weekday(day: int = None):
    """
    Vrátí průměrnou obsazenost za každou hodinu pro vybraný den v týdnu.
    Parametr day: 0=neděle, 1=pondělí, 2=úterý, ..., 6=sobota (0-6)
    Počítá průměry pouze z dat z posledních 6 měsíců.
    """
    # Validace parametru day
    if day is None:
        return {"error": "Parametr 'day' je povinný (0-6, kde 0=neděle, 1=pondělí, ..., 6=sobota)"}, 400
    
    if not isinstance(day, int) or day < 0 or day > 6:
        return {"error": "Parametr 'day' musí být číslo 0-6 (0=neděle, 1=pondělí, ..., 6=sobota)"}, 400
    
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        # Dotaz pro získání průměrné obsazenosti za každou hodinu daného dne v týdnu
        # PostgreSQL: EXTRACT(DOW FROM timestamp) vrací 0=neděle, 1=pondělí, ..., 6=sobota
        # Počítá průměry pouze z dat z posledních 6 měsíců
        query = """
            SELECT
                EXTRACT(HOUR FROM timestamp)::integer AS hour,
                ROUND(AVG(count))::integer AS avg_count
            FROM
                parkoviste_zaznamy
            WHERE
                EXTRACT(DOW FROM timestamp) = %s
                AND timestamp >= NOW() - INTERVAL '6 months'
            GROUP BY
                hour
            ORDER BY
                hour;
        """
        cur.execute(query, (day,))
        data = cur.fetchall()
        
        # Konverze na dict
        result = [dict(row) for row in data]
        
        return result
    except Exception as e:
        print(f"API Error in get_stats_weekday: {e}")
        return []
    finally:
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
    
    # Přidat informace o parkování
    result = data or {"count": 0}
    result["parking_status"] = get_parking_status()
    
    return result

@app.get("/latest-image")
def get_latest_image():
    """
    Vrátí nejnovější oanotovaný obrázek z parkoviště.
    Pokud žádný obrázek neexistuje, vrátí 404.
    """
    image_path = latest_image_service.get_latest_annotated_image_path()
    if image_path and os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/jpeg")
    return {"error": "Image not found"}, 404


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
    return templates.TemplateResponse(request=request, name="index.html", context=get_template_context(request))

@app.get("/history", response_class=HTMLResponse)
def read_history(request: Request):
    return templates.TemplateResponse(request=request, name="history.html", context=get_template_context(request))

@app.get("/statistics", response_class=HTMLResponse)
def read_statistics(request: Request):
    return templates.TemplateResponse(request=request, name="statistics.html", context=get_template_context(request))

@app.get("/latest", response_class=HTMLResponse)
def read_latest(request: Request):
    # Získání času posledního snímku
    image_path = latest_image_service.get_latest_annotated_image_path()
    last_updated = "Není k dispozici"
    
    if image_path and os.path.exists(image_path):
        timestamp = os.path.getmtime(image_path)
        # Převedení na časové pásmo Praha
        prague_tz = ZoneInfo("Europe/Prague")
        dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_prague = dt_utc.astimezone(prague_tz)
        last_updated = dt_prague.strftime("%d.%m.%Y %H:%M:%S")
    
    return templates.TemplateResponse(request=request, name="latest.html", context=get_template_context(request, last_updated=last_updated))

@app.get("/service/archive", response_class=HTMLResponse)
def read_archive(request: Request):
    return templates.TemplateResponse(request=request, name="archive.html", context=get_template_context(request))

@app.get("/api/archive/list")
def list_archive_files():
    """
    Vrátí seznam souborů ve složce webcam_archive/annotated.
    """
    archive_dir = os.path.join("webcam_archive", "annotated")
    if not os.path.exists(archive_dir):
        return []

    files = []
    for filename in os.listdir(archive_dir):
        file_path = os.path.join(archive_dir, filename)
        if os.path.isfile(file_path):
            stats = os.stat(file_path)
            files.append({
                "filename": filename,
                "size": stats.st_size,
                "modified": stats.st_mtime,
                "modified_iso": datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc).isoformat()
            })
    
    # Seřadit od nejnovějších
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files

@app.get("/service/archive/download/{filename}")
def download_archive_file(filename: str):
    """
    Umožní stáhnutí souboru z archivu.
    """
    # Bezpečnostní kontrola - filename nesmí obsahovat cesty
    if ".." in filename or "/" in filename or "\\" in filename:
         return {"error": "Invalid filename"}, 400
         
    archive_dir = os.path.join("webcam_archive", "annotated")
    file_path = os.path.join(archive_dir, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path, filename=filename)
    
    return {"error": "File not found"}, 404

@app.get("/service/archive/view/{filename}")
def view_archive_file(filename: str):
    """
    Zobrazí soubor z archivu (inline).
    """
    # Bezpečnostní kontrola
    if ".." in filename or "/" in filename or "\\" in filename:
         return {"error": "Invalid filename"}, 400
         
    archive_dir = os.path.join("webcam_archive", "annotated")
    file_path = os.path.join(archive_dir, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    
    return {"error": "File not found"}, 404

@app.get("/sw.js", include_in_schema=False)
def service_worker(request: Request):
    return templates.TemplateResponse(request=request, name="sw.js", context={"request": request, "version": APP_VERSION}, media_type="application/javascript")
