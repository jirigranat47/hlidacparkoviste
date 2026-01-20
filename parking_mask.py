import numpy as np

# Definice polygonu pro parkovací místa (Region of Interest)
# Souřadnice jsou ve formátu [x, y].
# Toto je výchozí obdélník, který pokrývá většinu obrazu, ale vynechává okraje.
# Uživatel by si měl tyto body upravit podle skutečného záběru kamery.

PARKING_ZONES = [
    np.array([
        [434, 499],     # Levý horní
        [564, 556],     # Pravý horní
        [72, 948],     # Pravý dolní
        [40, 771]       # Levý dolní
    ], dtype=np.int32),
    
    #Druhý polygon (spodní jižní část)
    np.array([
        [756, 533],
        [910, 559],
        [1021, 1020],
        [751, 1020]
    ], dtype=np.int32),

    #Třetí polygon (parkování podél severní části)
    np.array([
        [552, 360],
        [631, 359],
        [1, 734],
        [3, 620]
    ], dtype=np.int32),
]