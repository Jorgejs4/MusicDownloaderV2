"""
Escanea carpetas vacías en canciones_auto y añade las canciones correspondientes
a problematic_songs.csv y failed_songs.json para que no se reintenten.
"""
import os
import csv
import json
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "canciones_auto")
PROJECT_CSV = os.path.join(BASE_DIR, "playlist.csv")
PROBLEMATIC_CSV = os.path.join(BASE_DIR, "problematic_songs.csv")
ERROR_FILE = os.path.join(BASE_DIR, "failed_songs.json")
DB_FILE = os.path.join(BASE_DIR, "downloaded.json")

def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

def find_empty_folders():
    """Encuentra todas las carpetas vacías (sin .mp3 ni .lrc) en canciones_auto"""
    empty_folders = []
    for root, dirs, files in os.walk(MUSIC_DIR):
        if not dirs:  # Solo carpetas hoja (nivel álbum)
            has_media = any(f.lower().endswith(('.mp3', '.lrc')) for f in files)
            if not has_media:
                rel_path = os.path.relpath(root, MUSIC_DIR)
                parts = rel_path.replace("\\", "/").split("/")
                if len(parts) >= 2:
                    artist = parts[0]
                    album = parts[1]
                    empty_folders.append((artist, album))
    return empty_folders

def load_csv_songs():
    """Carga todas las canciones del CSV"""
    songs = []
    with open(PROJECT_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Nombre de la canción") or row.get("Track Name") or row.get("Name")
            artist = row.get("Nombre(s) del artista") or row.get("Artist Name(s)") or row.get("Artist")
            album = row.get("Nombre del álbum") or row.get("Album Name") or "Unknown Album"
            track_id = row.get("URL de la canción") or row.get("Track ID") or f"{artist}-{title}"
            if title and artist:
                songs.append({
                    "id": track_id,
                    "title": title,
                    "artist": artist,
                    "album": album
                })
    return songs

def normalize(s):
    """Normaliza texto para comparación"""
    s = sanitize(s).lower()
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

def match_empty_folders_to_songs(empty_folders, csv_songs):
    """Empareja carpetas vacías con canciones del CSV"""
    matched = []
    
    for folder_artist, folder_album in empty_folders:
        folder_artist_norm = normalize(folder_artist)
        folder_album_norm = normalize(folder_album)
        
        for song in csv_songs:
            song_artist_norm = normalize(song['artist'])
            song_album_norm = normalize(song['album'])
            
            # Coincidencia: artista coincide Y (álbum coincide O carpeta está vacía sin álbum específico)
            if folder_artist_norm == song_artist_norm:
                # Verificar si el álbum también coincide o si la carpeta del álbum no tiene coincidencia mejor
                if folder_album_norm == song_album_norm:
                    matched.append(song)
                elif folder_album_norm in song_album_norm or song_album_norm in folder_album_norm:
                    matched.append(song)
    
    # Eliminar duplicados por ID
    seen_ids = set()
    unique_matched = []
    for song in matched:
        if song['id'] not in seen_ids:
            seen_ids.add(song['id'])
            unique_matched.append(song)
    
    return unique_matched

def add_to_problematic_csv(songs):
    """Añade canciones a problematic_songs.csv"""
    file_exists = os.path.exists(PROBLEMATIC_CSV)
    
    # Cargar existentes para evitar duplicados
    existing = set()
    if file_exists:
        with open(PROBLEMATIC_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row.get("Nombre de la canción", "").strip().lower(), 
                       row.get("Nombre(s) del artista", "").strip().lower())
                existing.add(key)
    
    added = 0
    with open(PROBLEMATIC_CSV, mode='a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Nombre de la canción", "Nombre(s) del artista", "Nombre del álbum"])
        
        for song in songs:
            key = (song['title'].strip().lower(), song['artist'].strip().lower())
            if key not in existing:
                writer.writerow([song['title'], song['artist'], song['album']])
                existing.add(key)
                added += 1
    
    return added

def add_to_failed_json(songs):
    """Añade canciones a failed_songs.json"""
    failed = {}
    if os.path.exists(ERROR_FILE):
        try:
            with open(ERROR_FILE, "r", encoding="utf-8") as f:
                failed = json.load(f)
        except:
            failed = {}
    
    added = 0
    for song in songs:
        if song['id'] not in failed:
            failed[song['id']] = {
                "title": song['title'],
                "artist": song['artist'],
                "time": "orphan_folder"
            }
            added += 1
    
    with open(ERROR_FILE, "w", encoding="utf-8") as f:
        json.dump(failed, f, indent=4)
    
    return added

def main():
    print("🔍 Escaneando carpetas vacías en canciones_auto...")
    empty_folders = find_empty_folders()
    print(f"📁 Encontradas {len(empty_folders)} carpetas vacías")
    
    if not empty_folders:
        print("✅ No hay carpetas vacías")
        return
    
    print("\n📋 Cargando canciones del CSV...")
    csv_songs = load_csv_songs()
    print(f"📊 {len(csv_songs)} canciones en el CSV")
    
    print("\n🔗 Emparejando carpetas vacías con canciones...")
    matched_songs = match_empty_folders_to_songs(empty_folders, csv_songs)
    print(f"🎯 {len(matched_songs)} canciones identificadas como huérfanas")
    
    if not matched_songs:
        print("✅ No se encontraron canciones huérfanas")
        return
    
    print("\n📝 Añadiendo a problematic_songs.csv...")
    prob_added = add_to_problematic_csv(matched_songs)
    print(f"✅ {prob_added} canciones añadidas")
    
    print("\n📝 Añadiendo a failed_songs.json...")
    fail_added = add_to_failed_json(matched_songs)
    print(f"✅ {fail_added} canciones añadidas")
    
    print(f"\n{'='*50}")
    print(f"✅ PROCESO COMPLETADO")
    print(f"📁 Carpetas vacías: {len(empty_folders)}")
    print(f"🎵 Canciones huérfanas: {len(matched_songs)}")
    print(f"📋 Añadidas a problematic: {prob_added}")
    print(f"📋 Añadidas a failed: {fail_added}")
    print(f"{'='*50}")
    
    print("\n🎵 Canciones huérfanas identificadas:")
    for i, song in enumerate(matched_songs[:20], 1):
        print(f"  {i}. {song['artist']} - {song['title']}")
    
    if len(matched_songs) > 20:
        print(f"  ... y {len(matched_songs) - 20} más")

if __name__ == "__main__":
    main()
