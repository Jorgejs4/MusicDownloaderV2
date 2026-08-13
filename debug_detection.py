import os
import csv
import json
import re
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
MUSIC_DIR = os.path.join(BASE_DIR, "canciones_auto")
CSV_PATH = os.path.join(BASE_DIR, "playlist.csv")
DB_FILE = os.path.join(BASE_DIR, "downloaded.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "failed_songs_blacklist.json")

def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", str(name or "")).strip()

def run_diagnostic():
    print("--- DIAGNÓSTICO DE DETECCIÓN DE CANCIONES ---")
    
    # 1. Escaneo de archivos físicos
    installed = set()
    if os.path.exists(MUSIC_DIR):
        for root, _, files in os.walk(MUSIC_DIR):
            for f in files:
                if f.lower().endswith(".mp3"):
                    name = f.lower().strip()
                    installed.add(name)
    print(f"Total archivos MP3 encontrados: {len(installed)}")

    # 2. Cargar Blacklist
    blacklist = set()
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            blacklist = set(json.load(f))
    print(f"Canciones en blacklist: {len(blacklist)}")

    # 3. Analizar CSV
    targets = ["Faint", "Decode", "how it goes", "slackface", "7PM", "blasphemy"]
    found_in_csv = 0
    
    if not os.path.exists(CSV_PATH):
        print("❌ ERROR: No se encuentra playlist.csv")
        return

    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        print("\nRevisando objetivos en CSV...")
        for row in reader:
            title = (row.get("Nombre de la canción") or row.get("Nombre de la canciÃ³n") or 
                     row.get("Track Name") or row.get("Name") or "").strip()
            artist = (row.get("Nombre(s) del artista") or row.get("Nombre(s) del artista") or 
                      row.get("Artist Name(s)") or row.get("Artist") or "").strip()
            
            is_target = any(t.lower() in title.lower() for t in targets)
            if is_target:
                found_in_csv += 1
                expected = f"{sanitize(artist)} - {sanitize(title)}.mp3".lower().strip()
                status = "EXISTE" if expected in installed else "FALTA"
                in_blacklist = "SÍ" if f"{artist} - {title}" in blacklist else "NO"
                
                print(f"Found: {artist} - {title}")
                print(f"   -> Esperado: {expected}")
                print(f"   -> Estado físico: {status}")
                print(f"   -> En Blacklist: {in_blacklist}")
                
    if found_in_csv == 0:
        print("❌ No se encontró ninguna de las canciones buscadas en el CSV.")

if __name__ == "__main__":
    run_diagnostic()
