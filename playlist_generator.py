import csv
import json
import os
import re
import unicodedata
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from config_manager import config

try:
    from mutagen.id3 import ID3
except:
    pass

# Importar clasificador unificado
try:
    from genre_classifier import GenreClassifier
    classifier = GenreClassifier(verbose=False)
except ImportError:
    classifier = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def fetch_genres_from_provider(artist_name, title=None):
    if classifier:
        return classifier.classify(artist_name, title)
    return ["Sin clasificar"]

def get_year_from_lastfm(artist, title, path):
    if classifier:
        return classifier.fetch_year(artist, title)
    return None

def get_current_music_dir():
    return config.get_music_dir()

def get_current_playlist_dir():
    """Devuelve la carpeta de playlists y garantiza que exista.

    La descarga incremental actualiza las listas antes de que se ejecute
    ``generate_playlists()``. Por eso no se puede asumir que esa carpeta ya
    haya sido creada por la generación completa.
    """
    playlist_dir = os.path.join(get_current_music_dir(), "_Playlists")
    os.makedirs(playlist_dir, exist_ok=True)
    return playlist_dir

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name).replace("/", " ")).strip()

def _safe_print(msg):
    try:
        print(msg)
    except:
        pass

def process_single_track(root, name, music_dir, valid_filenames):
    try:
        if not name.lower().endswith(".mp3"): return None
        
        if valid_filenames and name.lower() not in valid_filenames:
            return None

        abs_path = os.path.join(root, name)
        
        song_title = name[:-4]
        if " - " in song_title:
            song_title = song_title.split(" - ", 1)[1]
        
        rel_path = "../" + os.path.relpath(abs_path, music_dir).replace("\\", "/")
        
        parts = os.path.relpath(abs_path, music_dir).split(os.sep)
        artist_raw = parts[0]
        
        genres = fetch_genres_from_provider(artist_raw, song_title)
        year = get_year_from_lastfm(artist_raw, song_title, abs_path)
        
        primary_genre = None
        is_espanolas = False

        genre_mapping = {
            "Rap": ["rap", "trap", "drill", "phonk"],
            "Hiphop": ["hip hop", "hip-hop", "urban"],
            "Rock": ["rock", "grunge", "metal"],
            "Indie-Alt": ["indie", "alternative", "bedroom pop"],
            "Pop": ["pop", "synthpop"],
            "Electronica": ["edm", "dance", "house", "techno"],
            "Lofi-chill": ["lofi", "chill", "soul", "jazz", "ambient"],
            "Kpop": ["k-pop", "kpop"],
            "Españolas": ["espanol", "spanish", "reggaeton", "latin"]
        }

        for g in genres:
            safe_g = sanitize(g).lower()
            if "espanol" in safe_g or "spanish" in safe_g: is_espanolas = True

            for cat, keywords in genre_mapping.items():
                if any(kw in safe_g for kw in keywords):
                    primary_genre = cat
                    break
            if primary_genre: break

        decade = "Sin clasificar"
        if year and str(year).isdigit():
            year_int = int(year)
            if 1900 < year_int < 2027:
                decade = f"{(year_int//10)*10}s"
        to_assign = []
        if primary_genre: to_assign.append(primary_genre)
        if decade != "Sin clasificar": to_assign.append(decade)
        if is_espanolas: to_assign.append("Españolas")

        # Si no se ha asignado a nada, va a "Sin clasificar"
        if not to_assign:
            to_assign.append("Sin clasificar")

        return {"rel_path": rel_path, "to_assign": to_assign}

    except Exception as e:
        _safe_print(f" ⚠️ Error en archivo {name}: {e}")
        return None

def update_playlist_for_track(abs_path, genres, year):
    """AÃ±ade una canciÃ³n reciÃ©n descargada a las listas correspondientes."""
    music_dir = get_current_music_dir()
    playlist_dir = get_current_playlist_dir()
    os.makedirs(playlist_dir, exist_ok=True)
    # Fix: Prepend ../ because playlists are in _Playlists/ subfolder
    rel_path = "../" + os.path.relpath(abs_path, music_dir).replace("\\", "/")
    
    # 1. Determinar Listas (Misma logica que generate_playlists)
    to_assign = []
    
    # GÃ©nero
    genre_mapping = {
        "Rap": ["rap", "trap", "drill", "phonk"],
        "Hiphop": ["hip hop", "hip-hop", "urban"],
        "Rock": ["rock", "grunge", "metal"],
        "Indie-Alt": ["indie", "alternative", "bedroom pop"],
        "Pop": ["pop", "synthpop"],
        "Electronica": ["edm", "dance", "house", "techno"],
        "Lofi-chill": ["lofi", "chill", "soul", "jazz", "ambient"],
        "Kpop": ["k-pop", "kpop"],
        "EspaÃ±olas": ["espanol", "spanish", "reggaeton", "latin"]
    }
    
    is_espanolas = False
    primary_genre = None
    for g in genres:
        safe_g = sanitize(g).lower()
        if "espanol" in safe_g or "spanish" in safe_g: is_espanolas = True
        for cat, keywords in genre_mapping.items():
            if any(kw in safe_g for kw in keywords):
                primary_genre = cat
                break
        if primary_genre: break
    
    if primary_genre: to_assign.append(primary_genre)
    if is_espanolas: to_assign.append("EspaÃ±olas")
    
    # DÃ©cada
    if year and str(year).isdigit():
        y = int(year)
        if 1900 < y < 2027:
            to_assign.append(f"{(y//10)*10}s")

    # 2. AÃ±adir a los archivos .m3u8
    for pl in to_assign:
        safe_pl = sanitize(pl)
        pl_path = os.path.join(playlist_dir, f"{safe_pl}.m3u8")
        
        # Leer existentes para evitar duplicados
        existing = set()
        has_header = False
        if os.path.exists(pl_path):
            with open(pl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line == "#EXTM3U":
                        has_header = True
                        continue
                    if line:
                        existing.add(line)
        
        if rel_path not in existing:
            # Re-escribir con header si no existe, o simplemente append
            mode = "w" if not has_header and not os.path.exists(pl_path) else "a"
            with open(pl_path, mode, encoding="utf-8", newline="\n") as f:
                if mode == "w":
                    f.write("#EXTM3U\n")
                f.write(rel_path + "\n")

def generate_playlists():
    music_dir = get_current_music_dir()
    playlist_dir = get_current_playlist_dir()
    
    # 0. LEER CSV ACTUAL (Strict filtering)
    valid_filenames = set()
    csv_path = os.path.join(BASE_DIR, "playlist.csv")
    if os.path.exists(csv_path):
        try:
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t = (row.get("Nombre de la canciÃ³n") or row.get("Track Name") or row.get("Name") or "").strip()
                    a = (row.get("Nombre(s) del artista") or row.get("Artist Name(s)") or row.get("Artist") or "").strip()
                    if t and a:
                        fname = f"{sanitize(a)} - {sanitize(t)}.mp3".lower()
                        valid_filenames.add(fname)
        except Exception as e:
            _safe_print(f" ⚠️ Error leyendo CSV para filtro: {e}")

    # Limpiar todas las listas antiguas
    if os.path.exists(playlist_dir):
        for f in os.listdir(playlist_dir):
            if f.endswith(".m3u8"):
                try: os.remove(os.path.join(playlist_dir, f))
                except: pass
    else: os.makedirs(playlist_dir, exist_ok=True)

    _safe_print(f" Cargando base de datos para: {os.path.basename(os.path.dirname(music_dir))}...")
    if valid_filenames:
        _safe_print(f" 🎯 Filtro estricto activo: solo se procesarán {len(valid_filenames)} canciones del CSV.")

    playlist_data = {}
    
    # Recopilar todos los archivos MP3 primero
    all_mp3s = []
    for root, dirs, files in os.walk(music_dir):
        if "_Playlists" in root: continue
        for name in files:
            if name.lower().endswith(".mp3"):
                all_mp3s.append((root, name))

    total_files = len(all_mp3s)
    _safe_print(f" Procesando {total_files} canciones en {music_dir} (vía Multi-threading)...")

    processed = 0
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(process_single_track, root, name, music_dir, valid_filenames) for root, name in all_mp3s]
        
        for future in as_completed(futures):
            res = future.result()
            if res:
                rel_path = res["rel_path"]
                for pl in res["to_assign"]:
                    safe_pl = sanitize(pl)
                    if safe_pl not in playlist_data: playlist_data[safe_pl] = []
                    playlist_data[safe_pl].append(rel_path)
            
            processed += 1
            if processed % 100 == 0:
                _safe_print(f"   🚀 Progreso: {processed}/{total_files}...")
    
    _safe_print(f" Guardando {len(playlist_data)} listas...")

    for pl_name, songs in playlist_data.items():
        pl_path = os.path.join(playlist_dir, f"{pl_name}.m3u8")
        with open(pl_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("#EXTM3U\n")
            # Ordenar canciones alfabéticamente para consistencia
            for s in sorted(songs): f.write(s + "\n")

    return {"playlists": list(playlist_data.keys())}
