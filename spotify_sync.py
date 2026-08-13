import os
import json
import time
import sys
import subprocess
import requests
import re
import base64
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ==============================
# 🔴 CONFIGURACIÓN (v5.0 - SEO Scraper Engine)
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "downloaded.json")
MAIN_SCRIPT = os.path.join(BASE_DIR, "musicDownloader3.py")
PLAYLIST_URL = os.environ.get("SPOTIFY_PLAYLIST_URL")

# Cargar base de datos local
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            downloaded = set(json.load(f))
    except:
        downloaded = set()
else:
    downloaded = set()

def get_songs_via_seo(url):
    """Extrae canciones del bloque SEO de la página pública de Spotify"""
    print(f"🔍 Extrayendo canciones (Modo Fantasma v5.0)...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'es-ES,es;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            print(f"❌ Error al acceder a Spotify (Status {response.status_code})")
            return []

        # Spotify guarda los datos en un bloque de script llamado 'session' o 'initial-state'
        # Vamos a buscar todos los bloques de script y extraer el que tenga más cara de JSON de música
        songs = []
        
        # Patrón para el formato moderno (JSON base64 o plano)
        match = re.search(r'id="initial-state">([^<]+)<', response.text)
        if match:
            try:
                # A veces viene en base64, a veces en plano
                raw_data = match.group(1)
                try:
                    decoded = base64.b64decode(raw_data).decode('utf-8')
                    data = json.loads(decoded)
                except:
                    data = json.loads(raw_data)
                
                # Navegar por el laberinto de Spotify para encontrar los tracks
                # Este path suele cambiar, así que buscamos "items" de forma recursiva
                def find_tracks(obj):
                    if isinstance(obj, dict):
                        if 'track' in obj and 'name' in obj['track']:
                            t = obj['track']
                            songs.append({
                                "id": t.get('id') or t.get('uri'),
                                "title": t.get('name'),
                                "artist": t['artists'][0]['name'] if t.get('artists') else "Unknown",
                                "album": t.get('album', {}).get('name', "Playlist")
                            })
                        else:
                            for v in obj.values(): find_tracks(v)
                    elif isinstance(obj, list):
                        for item in obj: find_tracks(item)

                find_tracks(data)
            except: pass

        # Failsafe: Búsqueda de patrones directos si el JSON falla
        if not songs:
            # Patrón: "trackName":"Nombre","artistName":"Artista"
            pattern = r'"name":"([^"]+?)","artists":\[{"name":"([^"]+?)"}\]'
            found = re.findall(pattern, response.text)
            for title, artist in found:
                if title != "Spotify" and title not in [s['title'] for s in songs]:
                    songs.append({
                        "id": f"{artist}-{title}",
                        "title": title,
                        "artist": artist,
                        "album": "Spotify Playlist"
                    })

        return songs
    except Exception as e:
        print(f"❌ Error en Modo Fantasma: {e}")
        return []

def sync():
    if not PLAYLIST_URL:
        print("❌ ERROR: Configura SPOTIFY_PLAYLIST_URL en tu .env")
        return

    all_songs = get_songs_via_seo(PLAYLIST_URL)
    
    if not all_songs:
        print("ℹ No se pudieron obtener canciones automáticamente.")
        print("💡 ÚLTIMO RECURSO: Como ya tienes el 'playlist.csv', ejecuta:")
        print("   python music_csv_auto.py")
        return

    new_songs = [s for s in all_songs if s['id'] not in downloaded]

    print(f"✅ Total encontrado: {len(all_songs)}")
    print(f"🚀 Canciones nuevas para descargar: {len(new_songs)}")

    for i, song in enumerate(new_songs):
        print(f"\n[ {i+1} / {len(new_songs)} ] Descargando: {song['artist']} - {song['title']}")
        
        cmd = [
            sys.executable, MAIN_SCRIPT,
            "-a", song['artist'],
            "-t", song['title'],
            "--album", song['album'],
            "--send"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            downloaded.add(song['id'])
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(list(downloaded), f, indent=4)
        except Exception as e:
            print(f"❌ Error en {song['title']}")

if __name__ == "__main__":
    sync()
