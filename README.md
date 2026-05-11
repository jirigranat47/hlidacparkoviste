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

## Rychlé spuštění
```bash
docker-compose up -d --build
## Správa verzí
Verze aplikace je definována v souboru api.py.

`python
APP_VERSION = "1.0.3"
``
Pro změnu verze stačí upravit tuto konstantu a restartovat aplikaci (nebo pokračovat na auto-reload).

## Historie změn
- **2026-05-11**: Oprava stability workeru a připojení k databázi.
  - Implementováno SSL (`sslmode=require`) pro stabilní spojení s Railway PostgreSQL.
  - Fixnuty úniky databázových spojení (přidány `finally` bloky pro uzavírání).
  - Přechod z `print()` na standardní modul `logging` pro lepší sledování stavu v produkci.
  - Přidány timeouty (15s) pro síťové požadavky ve workeru.
  - Zpřesněna diagnostika selhání připojení k DB.
