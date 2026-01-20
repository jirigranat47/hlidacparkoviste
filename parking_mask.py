import numpy as np

# Definice polygonu pro parkovací místa (Region of Interest)
# Souřadnice jsou ve formátu [x, y].
# Toto je výchozí obdélník, který pokrývá většinu obrazu, ale vynechává okraje.
# Uživatel by si měl tyto body upravit podle skutečného záběru kamery.

PARKING_ZONES = [
    np.array([
        [434, 499],     # Levý horní
        [564, 556],     # Pravý horní
        [123, 920],     # Pravý dolní
        [40, 771]       # Levý dolní
    ], dtype=np.int32),
    
    #Druhý polygon (odkomentujte a doplňte souřadnice)
    np.array([
        [756, 550],
        [910, 559],
        [1006, 1020],
        [772, 1020]
    ], dtype=np.int32),
]

# Příklad složitějšího polygonu (zakomentovaný):
# PARKING_ZONE = np.array([
#     [100, 200],
#     [500, 200],
#     [600, 800],
#     [50, 800]
# ], dtype=np.int32)
