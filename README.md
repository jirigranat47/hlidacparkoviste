# Hlídač parkoviště - Kostelec nad Orlicí

Projekt pro automatické sledování obsazenosti městského parkoviště pomocí počítačového vidění (AI).

## Cíl projektu
Aplikace v pravidelných intervalech (10 min) stahuje obraz z veřejné webkamery, pomocí modelu YOLOv8 detekuje počet zaparkovaných vozidel a ukládá data do databáze. Výsledkem je webový dashboard s aktuálním stavem, historií a statistikami pro lepší plánování příjezdu na náměstí.

## Funkce
- ✅ **Real-time monitoring**: Automatická detekce vozidel pomocí YOLOv8 každých 10 minut
- ✅ **Webový dashboard**: Přehledné zobrazení aktuálního stavu parkoviště
- ✅ **Živý náhled**: Zobrazení posledního anotovaného snímku z kamery
- ✅ **Statistiky za 24 hodin**: Graf obsazenosti parkoviště za posledních 24 hodin
- ✅ **Historická data**: Procházení dat z minulých dní s grafickým zobrazením
- ✅ **Denní statistiky**: Průměrná obsazenost podle dne v týdnu (založeno na 6měsíčních datech)
- ✅ **Responzivní design**: Plně optimalizováno pro mobilní zařízení
- ✅ **Barevný indikátor**: Vizuální rozlišení úrovně obsazenosti (zelená/žlutá/červená)
- ✅ **PWA**: Přehledné zobrazení aktuálního stavu parkoviště

## Technologie
- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Chart.js
- **AI model**: YOLOv8 (detekce vozidel)
- **Databáze**: PostgreSQL
- **Deployment**: Docker, Docker Compose

## API Endpointy
- `GET /` - Hlavní dashboard s aktuálním stavem a grafem za 24 hodin
- `GET /history` - Historický přehled s výběrem konkrétního dne
- `GET /statistics` - Statistiky podle dne v týdnu
- `GET /current` - Aktuální počet vozidel (JSON)
- `GET /stats` - Průměrná obsazenost za posledních 24 hodin (JSON)
- `GET /stats/history?date=YYYY-MM-DD` - Data pro konkrétní den (JSON)
- `GET /stats/weekday?day=0-6` - Průměry pro den v týdnu (0=neděle, 6=sobota) (JSON)
- `GET /latest` - Stránka zobrazující poslední anotovaný snímek z kamery
- `GET /latest-image` - Nejnovější anotovaný snímek z kamery

## Konfigurace prostředí

Před prvním spuštěním je nutné připravit konfigurační soubor `.env`. K dispozici je vzorová šablona [`.env.template`](file:///.env.template).

```bash
# Vytvoření .env ze šablony
# Windows PowerShell:
Copy-Item .env.template .env

# Linux / macOS:
cp .env.template .env
```

### Seznam proměnných v `.env`
| Proměnná | Výchozí hodnota | Popis |
|---|---|---|
| `DB_NAME` | `parkoviste_db` | Název databáze v PostgreSQL |
| `DB_USER` | `postgres` | Databázový uživatel |
| `DB_PASSWORD` | `tajne_heslo` | Databázové heslo |
| `DB_HOST` | `db` | Hostitel databáze (v Docker Compose síti je to `db`) |
| `DATABASE_URL` | *(volitelné)* | Přímý connection string pro cloudové nasazení (např. Railway) |
| `INTERVAL_SEKUNDY` | `300` | Interval stahování a vyhodnocování snímků z kamery (v sekundách) |
| `RETENTION_DAYS` | `7` | Doba uchovávání snímků v archivu před automatickým promazáním |
| `YOLO_CONF` | `0.25` | Minimální jistota detekce modelu YOLOv8 |
| `YOLO_IOU` | `0.7` | IoU práh pro Non-Maximum Suppression modelu YOLO |
| `IMGSZ` | `1280` | Rozlišení vstupu pro detekci |
| `PORT` | `8000` | Port webového serveru |
| `ZONE_OFFSET_X` | `0` | Horizontální posun všech zón v pixelech (`+` doprava, `-` doleva) |
| `ZONE_OFFSET_Y` | `0` | Vertikální posun všech zón v pixelech (`+` dolů, `-` nahoru) |
| `PARKING_ZONES_FILE` | `parking_zones.json` | Cesta k JSON souboru se souřadnicemi zón |
| `PARKING_ZONES_JSON` | *(volitelné)* | Přímý JSON řetězec se souřadnicemi zón přímo v `.env` |

### Kalibrace parkovacích zón a řešení posunu kamery (např. větrem)

Pokud se kamera větrem nebo otřesem posune a zelené zóny nesedí na skutečná parkovací místa, lze situaci vyřešit několika způsoby:

1. **Rychlá kompenzace posunu celého záběru (doporučeno při pohnutí kamery):**
   V souboru `.env` jednoduše upravte posun:
   ```env
   # Např. posun o 15 px doprava a 10 px nahoru:
   ZONE_OFFSET_X=15
   ZONE_OFFSET_Y=-10
   ```
   *Změna se uplatní automaticky při dalším stažení snímku bez nutnosti restartovat kontejner.*

2. **Úprava bodů zón v [`parking_zones.json`](file:///parking_zones.json):**
   V tomto souboru jsou definovány jednotlivé polygony pro parkovací sekce. Můžete zde upravovat body, přidávat nové nebo měnit jejich tvar:
   ```json
   [
     {
       "name": "Střední část (šikmá stání vlevo dole)",
       "points": [[434, 499], [524, 556], [35, 925], [30, 740]]
     }
   ]
   ```

3. **Zjištění přesných souřadnic pixelů na webu (kalibrační režim):**
   Tato funkce je pro běžné návštěvníky skryta. Pro její zobrazení otevřete stránku s GET parametrem:  
   👉 **[http://localhost:8000/latest?calibrate=1](http://localhost:8000/latest?calibrate=1)**  
   Po najetí kurzorem myši na libovolné místo snímku se pod obrázkem v reálném čase zobrazují přesné souřadnice `[x, y]` skutečného obrazu a kliknutím je zkopírujete do schránky.

## Rychlé spuštění
```bash
docker-compose up -d --build
```

Po spuštění jsou dostupné tyto služby:
- **Aplikace a webový dashboard**: [http://localhost:8000](http://localhost:8000)
- **Adminer (správa databáze)**: [http://localhost:8088](http://localhost:8088) *(Systém: PostgreSQL, Server: db, Uživatel/Heslo/DB dle `.env`)*
- **PostgreSQL**: port `5432`

## Správa verzí
Verze aplikace je definována v souboru `api.py`:

```python
APP_VERSION = "1.0.6"
```
Pro změnu verze stačí upravit tuto konstantu a restartovat aplikaci (nebo pokračovat na auto-reload).

## Historie změn
- **2026-05-11**: Oprava stability workeru a připojení k databázi.
  - Implementováno SSL (`sslmode=require`) pro stabilní spojení s Railway PostgreSQL.
  - Fixnuty úniky databázových spojení (přidány `finally` bloky pro uzavírání).
  - Přechod z `print()` na standardní modul `logging` pro lepší sledování stavu v produkci.
  - Přidány timeouty (15s) pro síťové požadavky ve workeru.
  - Zpřesněna diagnostika selhání připojení k DB.
