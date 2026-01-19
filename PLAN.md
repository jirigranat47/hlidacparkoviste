# Plán vývoje a cíle

Tento dokument slouží jako instrukce pro další postup vývoje.

## Priorita 1: Maska parkovacích míst (ROI)
**Problém**: Aktuálně se počítají všechna auta v záběru, včetně projíždějících.
**Cíl**: Implementovat v `main.py` polygonovou masku (Region of Interest), aby se počítala pouze auta stojící na definovaných parkovacích místech.

## Priorita 2: Statistiky v API
**Cíl**: Rozšířit `api.py` o výpočty:
- Průměrná obsazenost v danou hodinu (např. "Jak bývá plno v pondělí v 10:00?").
- Odhad volných míst (kapacita náměstí minus aktuální count).

## Priorita 3: Frontend Dashboard
**Cíl**: Vytvořit jednoduchou webovou stránku (v rámci FastAPI nebo samostatně):
- Zobrazení aktuálního počtu aut.
- Graf obsazenosti za posledních 24 hodin (Chart.js).
- Barevný indikátor (Zelená/Oranžová/Červená).

## Priorita 4: Nasazení na VPS
**Cíl**: Připravit skripty pro nasazení na Linux server (např. přes Git a Docker Compose).