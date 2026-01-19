# Hlídač parkoviště - Kostelec nad Orlicí

Projekt pro automatické sledování obsazenosti městského parkoviště pomocí počítačového vidění (AI).

## Cíl projektu
Aplikace v pravidelných intervalech (10 min) stahuje obraz z veřejné webkamery, pomocí modelu YOLOv8 detekuje počet zaparkovaných vozidel a ukládá data do databáze. Výsledkem bude webový dashboard s aktuálním stavem, historií a statistikami pro lepší plánování příjezdu na náměstí.

## Aktuální stav (MVP)
- [x] Funkční stahování obrazu z webu města.
- [x] Integrace YOLOv8 pro detekci vozidel (car, bus, truck).
- [x] Dockerizace projektu (Worker, API, PostgreSQL).
- [x] Základní FastAPI backend pro export dat.

## Rychlé spuštění
```bash
docker-compose up -d --build