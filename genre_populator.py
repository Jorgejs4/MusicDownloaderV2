import os
import csv
import json
import time
import requests

# ==============================
# 🚀 POBLADOR DE GÉNEROS v1.0
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_CSV = os.path.join(BASE_DIR, "playlist.csv")
CACHE_FILE = os.path.join(BASE_DIR, "artist_genres.json")

# Mapeo de sub-géneros a categorías principales
GENRE_MAP = {
    "Rock": ["rock", "hard rock", "grunge", "punk", "metal", "heavy", "classic rock", "progressive rock", "psychedelic rock"],
    "Indie & Alt": ["indie", "alternative", "alt-rock", "dream pop", "shoegaze", "art pop", "experimental", "britpop"],
    "Pop": ["pop", "dance-pop", "synthpop", "electropop", "teen pop", "boy band", "girl group", "k-pop", "j-pop"],
    "Hip Hop & Rap": ["hip hop", "rap", "trap", "urban", "gangsta rap", "drill", "lo-fi hip hop", "cloud rap"],
    "R&B & Soul": ["r&b", "soul", "neo soul", "funk", "disco", "motown", "gospel"],
    "Electronic": ["electronic", "house", "techno", "edm", "dance", "trance", "dubstep", "electro", "ambient", "idm"],
    "Latin & Urban": ["reggaeton", "trap latino", "pop latino", "salsa", "merengue", "bachata", "regional mexicano", "vallenato", "flamenco", "rumba", "latin"],
    "Chill & Lo-Fi": ["chill", "lofi", "relax", "mellow", "slow", "acoustic", "jazz", "blues", "folk", "singer-songwriter"],
    "Soundtrack & Classical": ["score", "soundtrack", "ost", "classical", "opera", "orchestra", "instrumental", "piano"],
}

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)

def get_major_genres(tags):
    found = set()
    for tag in tags:
        tag_name = tag.get('name', '').lower()
        for major, minors in GENRE_MAP.items():
            if tag_name in minors or any(m in tag_name for m in minors):
                found.add(major)
    return list(found)

def fetch_artist_info(artist_name):
    print(f"🔍 Buscando: {artist_name}...", end="", flush=True)
    try:
        # MusicBrainz API
        url = f"https://musicbrainz.org/ws/2/artist/?query=artist:\"{artist_name}\"&fmt=json"
        headers = {'User-Agent': 'MusicDownloaderBot/1.0 (jorge@example.com)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('artists'):
                artist = data['artists'][0]
                tags = artist.get('tags', [])
                genres = get_major_genres(tags)
                if not genres:
                    # Intentar con 'genres' si 'tags' falla
                    genres = get_major_genres(artist.get('genres', []))
                
                if genres:
                    print(f" ✅ {genres}")
                    return genres
                else:
                    print(" ⚠️ Sin géneros claros.")
                    return ["Otros"]
        elif response.status_code == 503:
            print(" 🛑 Error 503 (Servidor ocupado).")
            return None
        else:
            print(f" ❌ Error {response.status_code}")
            return None
    except Exception as e:
        print(f" ❌ Error: {e}")
        return None
    return ["Otros"]

def main():
    if not os.path.exists(PROJECT_CSV):
        print("❌ Error: playlist.csv no encontrado.")
        return

    cache = load_cache()
    
    # Extraer artistas únicos
    all_artists = set()
    with open(PROJECT_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            a = row.get("Nombre(s) del artista") or row.get("Artist Name(s)") or row.get("Artist")
            if a:
                # Tomar solo el primer artista principal
                main_artist = a.split(',')[0].split('&')[0].strip()
                all_artists.add(main_artist)

    to_fetch = [a for a in all_artists if a not in cache]
    print(f"📊 Artistas totales: {len(all_artists)}")
    print(f"🚀 Artistas por buscar: {len(to_fetch)}")
    
    if not to_fetch:
        print("✅ Todo el cache está al día.")
        return

    try:
        for i, artist in enumerate(to_fetch):
            print(f"[{i+1}/{len(to_fetch)}] ", end="")
            genres = fetch_artist_info(artist)
            if genres is not None:
                cache[artist] = genres
                # Guardar cada 10 artistas para no perder progreso
                if i % 10 == 0:
                    save_cache(cache)
            
            # Respetar rate limit de MusicBrainz (1 seg)
            time.sleep(1.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Proceso interrumpido por el usuario.")
    finally:
        save_cache(cache)
        print(f"\n💾 Cache guardado. Total en cache: {len(cache)} artistas.")

if __name__ == "__main__":
    main()
