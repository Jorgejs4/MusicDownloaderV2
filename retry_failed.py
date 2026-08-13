import os, re, csv, json, time, random, logging, glob, subprocess, unicodedata
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# --- RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROBLEMATIC_FILE = os.path.join(BASE_DIR, "problematic_songs.csv")
FAILED_JSON = os.path.join(BASE_DIR, "failed_songs.json")
DB_FILE = os.path.join(BASE_DIR, "downloaded.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "canciones_auto"))
COOKIES_TXT = os.path.join(BASE_DIR, "cookies.txt")

import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

quiet_logger = QuietLogger()

logging.basicConfig(level=logging.INFO, format="[RETRY-CLEAN] %(asctime)s [%(levelname)s] %(message)s", encoding='utf-8')
log = logging.getLogger("RetryWarMachine")

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name or "")).strip()

def clean_for_search(text):
    if not text: return ""
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^1234567890]*\]', '', text)
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r"\s+", " ", text).strip().lower()

def purge_song_from_lists(artist, title):
    """Elimina la canción de problematic_songs.csv y failed_songs.json"""
    # 1. Limpiar CSV
    if os.path.exists(PROBLEMATIC_FILE):
        rows = []
        try:
            with open(PROBLEMATIC_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not (row.get("Nombre(s) del artista") == artist and row.get("Nombre de la canción") == title):
                        rows.append(row)
            with open(PROBLEMATIC_FILE, "w", encoding="utf-8", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["Nombre de la canción", "Nombre(s) del artista", "Nombre del álbum"])
                writer.writeheader()
                writer.writerows(rows)
        except: pass

    # 2. Limpiar JSON de fallos
    if os.path.exists(FAILED_JSON):
        try:
            with open(FAILED_JSON, "r", encoding="utf-8") as f: data = json.load(f)
            new_data = {k: v for k, v in data.items() if not (v.get("artist") == artist and v.get("title") == title)}
            with open(FAILED_JSON, "w", encoding="utf-8") as f: json.dump(new_data, f, indent=4)
        except: pass

    # 3. Añadir a downloaded.json
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: db = json.load(f)
            track_id = f"{artist}-{title}"
            if track_id not in db:
                db.append(track_id)
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db, f, indent=4)
        except: pass

def check_if_exists(artist, title):
    """Comprueba si el archivo ya existe físicamente en el disco"""
    safe_name = f"{sanitize(artist)} - {sanitize(title)}.mp3".lower()
    if not os.path.exists(OUTPUT_DIR): return False
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            if f.lower() == safe_name: return True
    return False

def generate_query_matrix(artist, title):
    return [
        f"{artist} - {title} lyrics",
        f"{artist} - {title} official audio",
        f"{artist} - {title}",
        f"{title} {artist} lyrics",
        title
    ]

def try_download(track, query, use_player=False):
    title, artist = track["title"], track["artist"]
    safe_name = sanitize(f"{artist} - {title}")
    album = track.get("album", "Unknown") or "Unknown"
    song_dir = os.path.join(OUTPUT_DIR, sanitize(artist), sanitize(album))
    os.makedirs(song_dir, exist_ok=True)
    mp3_path = os.path.join(song_dir, f"{safe_name}.mp3")
    
    search_opts = {"quiet": True, "no_warnings": True, "ignoreerrors": True, "logger": quiet_logger}
    try:
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            res = ydl.extract_info(f"ytsearch3:{query}", download=False)
            candidates = res.get('entries', []) or []
    except: return None
    
    if not candidates: return None
    
    for candidate in candidates:
        if not candidate or not candidate.get('webpage_url'): continue
        
        import shutil
        node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.EXE"
        download_opts = {
            "outtmpl": os.path.join(song_dir, f"{safe_name}.%(ext)s"),
            "quiet": True, "no_warnings": True, "ignoreerrors": True, "nocheckcertificate": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"}],
            "format": "best",
            "jsruntimes": [node_path] if node_path else None,
            "logger": quiet_logger
        }
        if use_player:
            download_opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}
        if os.path.exists(COOKIES_TXT): download_opts["cookiefile"] = COOKIES_TXT

        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([candidate['webpage_url']])
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 10000: return mp3_path
        except: continue
    return None

def main():
    if not os.path.exists(PROBLEMATIC_FILE):
        print("No hay archivo de canciones problemáticas."); return

    with open(PROBLEMATIC_FILE, mode='r', encoding='utf-8') as f:
        raw_songs = list(csv.DictReader(f))

    print(f"\n>> LIMPIEZA: Procesando {len(raw_songs)} canciones...")
    
    rescued = 0
    cleaned = 0
    for i, row in enumerate(raw_songs):
        track = {
            "title": row.get("Nombre de la canción", ""),
            "artist": row.get("Nombre(s) del artista", ""),
            "album": row.get("Nombre del álbum", "Unknown")
        }
        
        artist, title = track["artist"], track["title"]
        if not artist or not title: continue

        print(f"\n[{i+1}/{len(raw_songs)}] {artist} - {title}")

        try:
            # Comprobar si ya existe
            if check_if_exists(artist, title):
                print("   [OK] Ya estaba descargada. Limpiando de las listas...")
                purge_song_from_lists(artist, title)
                cleaned += 1
                continue

            # Intentar descarga agresiva
            queries = generate_query_matrix(artist, title)
            found = False
            for q in queries:
                for use_player in [False, True]:
                    path = try_download(track, q, use_player)
                    if path:
                        print(f"   ✅ DESCARGADA! -> {path}")
                        purge_song_from_lists(artist, title)
                        rescued += 1
                        found = True; break
                if found: break
                time.sleep(0.5)
            
            if not found: print("   ❌ Sigue sin funcionar.")
        except Exception as e:
            print(f"   ⚠️ Error inesperado en esta canción: {e}")
            continue

    print(f"\nFIN. Se han limpiado {cleaned} ya existentes y rescatado {rescued} nuevas.")

if __name__ == "__main__":
    main()
