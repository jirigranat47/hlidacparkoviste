import numpy as np

# Definice polygonu pro parkovací místa (Region of Interest)
# Souřadnice jsou ve formátu [x, y].
# Toto je výchozí obdélník, který pokrývá většinu obrazu, ale vynechává okraje.
# Uživatel by si měl tyto body upravit podle skutečného záběru kamery.

PARKING_ZONES = [
    #První polygon (spodní západní část)
    np.array([
        [434, 499],     # Levý horní
        [524, 556],     # Pravý horní
        [35, 925],     # Pravý dolní
        [30, 740]       # Levý dolní
    ], dtype=np.int32),
    
    #Druhý polygon (spodní jižní část)
    np.array([
        [700, 533],
        [850, 559],
        [950, 1020],
        [670, 1020]
    ], dtype=np.int32),

    #Třetí polygon (parkování podél severní části)
    np.array([
        [470, 360],
        [550, 359],
        [1, 700],
        [3, 600]
    ], dtype=np.int32),
]