import os
import csv
import re

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name).replace("/", " ")).strip()

ROOT = r"C:\Users\jorge\Desktop\proyectos\music downloader b3\canciones_auto"
CSV_PATH = r"C:\Users\jorge\Desktop\proyectos\music downloader b3\playlist.csv"

def clean_user(user_folder):
    music_dir = os.path.join(ROOT, user_folder, "Liked")
    if not os.path.exists(music_dir):
        print(f"Carpeta no encontrada: {music_dir}")
        return
    if not os.path.exists(CSV_PATH):
        print("No se encuentra playlist.csv en la raiz")
        return
    
    valid = set()
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = (row.get("Nombre de la canción") or row.get("Nombre de la canciÃ³n") or row.get("Track Name") or row.get("Name") or "").strip()
            a = (row.get("Nombre(s) del artista") or row.get("Artist Name(s)") or row.get("Artist") or "").strip()
            if t and a:
                valid.add(f"{sanitize(a)} - {sanitize(t)}.mp3".lower())
    
    removed = 0
    # Walk and remove files NOT in CSV
    for root, dirs, files in os.walk(music_dir):
        if "_Playlists" in root: continue
        for f in files:
            if f.lower().endswith(".mp3"):
                if f.lower() not in valid:
                    try:
                        os.remove(os.path.join(root, f))
                        removed += 1
                    except: pass
    
    print(f"Usuario {user_folder}: {removed} archivos huerfanos eliminados.")

if __name__ == "__main__":
    # Limpiamos 'default' con el CSV actual. 
    # (Clara Mae estaba apareciendo aqui a pesar de no estar en el CSV)
    clean_user("default")
