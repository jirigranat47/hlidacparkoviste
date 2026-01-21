import os
import glob
from datetime import datetime

# Definice cesty k archivu (shodné s main.py, ideálně by mělo být v konfigu)
# Pro zjednodušení zde definujeme znovu, nebo bychom mohli importovat z configu, pokud by existoval.
# V main.py je to: os.path.join("webcam_archive", "annotated")
ANNOTATED_DIR = os.path.join("webcam_archive", "annotated")

def get_latest_annotated_image_path(base_dir: str = ".") -> str | None:
    """
    Vyhledá nejnovější obrázek ve složce webcam_archive/annotated.
    Vrací absolutní cestu k souboru nebo None, pokud nic nenajde.
    """
    search_path = os.path.join(base_dir, ANNOTATED_DIR, "*.jpg")
    files = glob.glob(search_path)
    
    if not files:
        return None
        
    # Seřadíme soubory podle času změny (creation/modification time) sestupně
    # Nejnovější bude první
    latest_file = max(files, key=os.path.getmtime)
    
    return os.path.abspath(latest_file)
