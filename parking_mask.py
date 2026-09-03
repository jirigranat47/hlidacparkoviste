import os
import json
import logging
import numpy as np
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Výchozí definice polygonů pro parkovací místa (Region of Interest)
# Souřadnice jsou ve formátu [x, y].
DEFAULT_PARKING_ZONES = [
    # 1. polygon: Střední část (šikmá stání vlevo dole)
    [
        [434, 499],     # Levý horní
        [524, 556],     # Pravý horní
        [35, 925],      # Pravý dolní
        [30, 740]       # Levý dolní
    ],
    
    # 2. polygon: Jižní část (podélná stání vpravo)
    [
        [700, 533],
        [850, 559],
        [950, 1020],
        [670, 1020]
    ],

    # 3. polygon: Severní část (stání podél budov vlevo)
    [
        [470, 360],
        [550, 359],
        [1, 700],
        [3, 600]
    ],
]

def _parse_zones_data(raw_data):
    """
    Normalizuje data zón z JSONu do seznamu seznamů bodů [[x, y], ...].
    Podporuje jak čisté body [[[x, y], ...], ...], tak objekty [{"name": "...", "points": [...]}, ...].
    """
    zones = []
    if isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict) and "points" in item:
                zones.append(item["points"])
            elif isinstance(item, list):
                zones.append(item)
    return zones

def get_parking_zones():
    """
    Dynamicky načte a sestaví seznam parkovacích zón:
    1. Znovu načte .env pro okamžité uplatnění změn za běhu
    2. Zkontroluje proměnnou PARKING_ZONES_JSON (přímý JSON string v ENV)
    3. Pokud není, zkontroluje soubor PARKING_ZONES_FILE nebo výchozí parking_zones.json
    4. Pokud není, použije DEFAULT_PARKING_ZONES
    5. Aplikuje globální posuny ZONE_OFFSET_X a ZONE_OFFSET_Y (posun záběru kamery např. větrem)
    
    Vrací seznam numpy polí [np.array(..., dtype=np.int32)] vhodných pro cv2.polylines a cv2.pointPolygonTest.
    """
    # Načtení aktuálního .env (override=True zajistí znovunačtení změn v souboru)
    load_dotenv(override=True)

    zones_data = None

    # 1. Priorita: PARKING_ZONES_JSON v ENV
    env_zones_json = os.getenv("PARKING_ZONES_JSON")
    if env_zones_json and env_zones_json.strip():
        try:
            parsed = json.loads(env_zones_json)
            zones_data = _parse_zones_data(parsed)
            logger.debug("Parkovací zóny načteny z PARKING_ZONES_JSON v ENV.")
        except Exception as e:
            logger.error(f"Chyba při parsování PARKING_ZONES_JSON: {e}")

    # 2. Priorita: JSON soubor (PARKING_ZONES_FILE nebo parking_zones.json)
    if not zones_data:
        zones_file = os.getenv("PARKING_ZONES_FILE", "parking_zones.json")
        if os.path.exists(zones_file):
            try:
                with open(zones_file, "r", encoding="utf-8") as f:
                    parsed = json.load(f)
                    zones_data = _parse_zones_data(parsed)
                    logger.debug(f"Parkovací zóny načteny ze souboru {zones_file}.")
            except Exception as e:
                logger.error(f"Chyba při čtení souboru se zónami '{zones_file}': {e}")

    # 3. Fallback: Výchozí předdefinované zóny
    if not zones_data:
        zones_data = DEFAULT_PARKING_ZONES

    # 4. Načtení offsetů pro korekci posunu kamery (např. vlivem větru)
    try:
        offset_x = int(os.getenv("ZONE_OFFSET_X", 0))
    except (ValueError, TypeError):
        offset_x = 0

    try:
        offset_y = int(os.getenv("ZONE_OFFSET_Y", 0))
    except (ValueError, TypeError):
        offset_y = 0

    # 5. Transformace na numpy int32 arrays s aplikovaným posunem
    np_zones = []
    for zone in zones_data:
        shifted_zone = []
        for pt in zone:
            shifted_zone.append([int(pt[0]) + offset_x, int(pt[1]) + offset_y])
        np_zones.append(np.array(shifted_zone, dtype=np.int32))

    return np_zones

# Pro zpětnou kompatibilitu
PARKING_ZONES = get_parking_zones()