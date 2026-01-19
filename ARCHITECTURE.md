# Architektura systému

## Komponenty (Docker kontejnery)
1. **db (PostgreSQL 15)**: Perzistentní úložiště pro historická data obsazenosti.
2. **app (Worker)**: Python skript (`main.py`), který obstarává:
   - Scraping obrázku (BeautifulSoup4 + Requests).
   - Inferenci (YOLOv8 nano).
   - Zápis do DB (Psycopg2).
3. **api (FastAPI)**: Backend poskytující data pro frontend.
4. **adminer**: Webové rozhraní pro správu databáze (port 8080).

## Datové schéma
Tabulka `occupancy`:
- `id`: SERIAL (PK)
- `timestamp`: TIMESTAMP
- `count`: INTEGER (počet detekovaných vozidel)

## Klíčové technologie
- **AI/ML**: Ultralytics YOLOv8
- **Backend**: FastAPI, Uvicorn
- **DB**: PostgreSQL
- **DevOps**: Docker, Docker Compose