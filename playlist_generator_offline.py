import os
import json
import re
import unicodedata
import glob as glob_module

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "canciones_auto")
PLAYLIST_DIR = os.path.join(MUSIC_DIR, "_Playlists")
OVERRIDES_PATH = os.path.join(BASE_DIR, "genre_overrides.json")

STATIC_OVERRIDES = {
    "Avicii": "Electronic / Dance",
    "Daft Punk": "Electronic / Dance",
    "Martin Garrix": "Electronic / Dance",
    "Zedd": "Electronic / Dance",
    "Calvin Harris": "Electronic / Dance",
    "Eminem": "Hip Hop / Rap / Trap",
    "Kendrick Lamar": "Hip Hop / Rap / Trap",
    "Juice WRLD": "Hip Hop / Rap / Trap",
    "XXXTENTACION": "Hip Hop / Rap / Trap",
    "Coldplay": "Rock / Alternative",
    "Linkin Park": "Rock / Alternative",
    "Red Hot Chili Peppers": "Rock / Alternative",
    "Oasis": "Rock / Alternative",
    "Green Day": "Rock / Alternative",
    "Melendi": "Rock / Pop Español",
    "Fito": "Rock / Pop Español",
    "Estopa": "Rock / Pop Español",
    "Extremoduro": "Rock / Pop Español",
    "Hombres G": "Latin Rock",
    "Soda Stereo": "Latin Rock",
    "Mana": "Latin Rock",
    "Enanitos Verdes": "Latin Rock",
    "Dua Lipa": "Pop / R&B",
    "Taylor Swift": "Pop / R&B",
    "Bruno Mars": "Pop / R&B",
    "Billie Eilish": "Pop / R&B",
    "Good Kid": "Rock / Alternative",
    "$not": "Chill / Lofi / Soul",
}

KEYWORD_GENRE_MAP = {
    "Hip Hop / Rap / Trap": ["rap", "hip hop", "trap", "drill", "hip-hop", "phonk"],
    "Chill / Lofi / Soul": ["lofi", "lo-fi", "chill", "jazz", "soul", "lo-fi hip hop", "mellow"],
    "Rock / Alternative": ["rock", "alternative", "grunge", "alt rock", "indie rock"],
    "Indie / Bedroom Pop": ["indie", "bedroom pop", "dream pop", "synthpop", "art pop"],
    "Electronic / Dance": ["edm", "electronic", "house", "techno", "dj", "dance", "electro", "trance"],
    "Pop / R&B": ["pop", "r&b", "rnb", "rn-b"],
    "Rock / Pop Español": ["español", "espanol", "rock en espanol", "pop espanol"],
    "Latin Urban / Reggaeton": ["reggaeton", "urbano", "latin", "latin trap", "dembow"],
    "Metal / Punk / Hardcore": ["metal", "punk", "hardcore", "hard rock", "metalcore"],
    "Acoustic / Folk / Country": ["acoustic", "folk", "country", "americana"],
    "Soundtrack / Classical": ["soundtrack", "ost", "score", "classical", "instrumental"],
    "Latin Rock": ["rock nacional", "latin rock", "rock latino"],
}

def normalize_text(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w\s$]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def load_overrides():
    overrides = {}
    if os.path.exists(OVERRIDES_PATH):
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for artist, genre in data.items():
                    overrides[normalize_text(artist)] = genre
            except:
                pass
    for artist, genre in STATIC_OVERRIDES.items():
        overrides[normalize_text(artist)] = genre
    return overrides

def classify_by_heuristic(artist_name):
    norm_artist = normalize_text(artist_name)
    for genre, keywords in KEYWORD_GENRE_MAP.items():
        for kw in keywords:
            if kw in norm_artist:
                return genre
    return None

def classify_track(artist_name, overrides):
    norm_artist = normalize_text(artist_name)
    if norm_artist in overrides:
        return overrides[norm_artist]
    genre = classify_by_heuristic(norm_artist)
    if genre:
        return genre
    return "Sin clasificar"

def get_all_mp3_files():
    mp3_files = []
    if not os.path.exists(MUSIC_DIR):
        return mp3_files
    for root, dirs, files in os.walk(MUSIC_DIR):
        if "_Playlists" in root:
            continue
        for f in files:
            if f.lower().endswith(".mp3"):
                full_path = os.path.join(root, f)
                relative_path = os.path.relpath(full_path, MUSIC_DIR).replace("\\", "/")
                mp3_files.append(relative_path)
    return mp3_files

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name or "")).strip()

def clean_playlist_dir():
    if not os.path.exists(PLAYLIST_DIR):
        os.makedirs(PLAYLIST_DIR, exist_ok=True)
        return
    for f in os.listdir(PLAYLIST_DIR):
        full_path = os.path.join(PLAYLIST_DIR, f)
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except:
                pass

def generate_playlists():
    print("=" * 60)
    print("PLAYLIST GENERATOR - Modo Offline (sin internet)")
    print("=" * 60)
    
    overrides = load_overrides()
    print(f"Overrides cargados: {len(overrides)}")
    
    mp3_files = get_all_mp3_files()
    print(f"Archivos encontrados: {len(mp3_files)}")
    
    if not mp3_files:
        print("No se encontraron archivos MP3")
        return
    
    clean_playlist_dir()
    
    playlists = {}
    unclassified = []
    
    for mp3_file in mp3_files:
        folder_parts = mp3_file.split("/")
        if len(folder_parts) >= 2:
            artist = folder_parts[0]
        else:
            artist = "Unknown"
        
        genre = classify_track(artist, overrides)
        
        if genre == "Sin clasificar":
            unclassified.append(mp3_file)
        else:
            if genre not in playlists:
                playlists[genre] = []
            playlists[genre].append(mp3_file)
    
    print("\n" + "=" * 60)
    print("GENERANDO PLAYLISTS")
    print("=" * 60)
    
    total_songs = 0
    
    for genre, files in playlists.items():
        safe_genre = sanitize_filename(genre)
        playlist_path = os.path.join(PLAYLIST_DIR, f"{safe_genre}.m3u8")
        with open(playlist_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("#EXTM3U\n")
            for file in files:
                # Fix: Prepend ../ because playlists are in _Playlists/ subfolder
                f.write(f"../{file}\n")
        print(f"  {genre}: {len(files)} canciones")
        total_songs += len(files)
    
    if unclassified:
        playlist_path = os.path.join(PLAYLIST_DIR, "Sin clasificar.m3u8")
        with open(playlist_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("#EXTM3U\n")
            for file in unclassified:
                f.write(f"../{file}\n")
        print(f"  Sin clasificar: {len(unclassified)} canciones")
        total_songs += len(unclassified)
    
    all_files = sorted(mp3_files)
    
    master_path = os.path.join(PLAYLIST_DIR, "Todas las canciones.m3u8")
    with open(master_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        for file in all_files:
            f.write(f"../{file}\n")
    print(f"  Todas las canciones: {len(all_files)} canciones")
    
    print("\n" + "=" * 60)
    print("COMPLETADO!")
    print(f"   Total canciones: {total_songs}")
    print(f"   Playlists creadas: {len(playlists) + (1 if unclassified else 0) + 1}")
    print("=" * 60)

if __name__ == "__main__":
    generate_playlists()