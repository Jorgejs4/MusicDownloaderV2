import os
import json
import time
import csv
import sys
import re
import importlib.util
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config_manager import config

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

def sanitize(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", str(name or ""))
    return name.strip()

class DownloadEngine:
    def __init__(self, csv_path=None, music_dir=None, db_file=None):
        self.csv_path = csv_path or os.path.join(BASE_DIR, "playlist.csv")
        self.music_dir = music_dir or config.get_music_dir()
        self.db_file = db_file or os.path.join(BASE_DIR, "downloaded.json")
        self.engine = None

    def _load_engine(self, progress_callback=None):
        try:
            engine_path = os.path.join(BASE_DIR, "musicDownloader3.py")
            if os.path.exists(engine_path):
                spec = importlib.util.spec_from_file_location("musicDownloader3", engine_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.engine = module
                if progress_callback: progress_callback("✅ Motor de descarga cargado dinámicamente.")
                return True
        except Exception as e:
            if progress_callback: progress_callback(f"❌ Error al cargar motor: {e}")
        return False

    def quick_scan(self, remote_files=None, progress_callback=None):
        installed_basenames = set()
        if os.path.exists(self.music_dir):
            for root, _, files in os.walk(self.music_dir):
                for f in files:
                    if f.lower().endswith((".mp3", ".lrc")):
                        installed_basenames.add(f.lower().strip())

        if remote_files:
            for f in remote_files:
                name = os.path.basename(f).lower().strip()
                installed_basenames.add(name)

        if progress_callback:
            progress_callback(f"🔍 Escaneados {len(installed_basenames)} archivos locales/remotos.")
            sample = list(installed_basenames)[:5]
            progress_callback(f"   Muestra de archivos: {sample}")

        downloaded_ids = set()
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    downloaded_ids = set(json.load(f))
            except: pass

        to_download = []
        if not os.path.exists(self.csv_path): 
            if progress_callback: progress_callback(f"⚠️ No existe CSV en: {self.csv_path}")
            return [], downloaded_ids

        with open(self.csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count_skipped = 0
            for row in reader:
                title = (row.get("Nombre de la canción") or row.get("Nombre de la canciÃ³n") or 
                         row.get("Track Name") or row.get("Name") or "").strip()
                artist = (row.get("Nombre(s) del artista") or row.get("Nombre(s) del artista") or 
                          row.get("Artist Name(s)") or row.get("Artist") or "").strip()
                
                duration_ms = (row.get("Duración de la canción (ms)") or 
                               row.get("DuraciÃ³n de la canciÃ³n (ms)") or 
                               row.get("Duration (ms)") or "0")
                try:
                    duration_s = int(duration_ms) // 1000
                except:
                    duration_s = 0

                if not title or not artist: continue
                
                track_id = row.get("URL de la canción") or row.get("Track ID") or f"{artist}-{title}"
                expected_filename = f"{sanitize(artist)} - {sanitize(title)}.mp3".lower().strip()

                if expected_filename not in installed_basenames:
                    to_download.append({
                        "id": track_id, "title": title, "artist": artist,
                        "album": row.get("Album Name", "Unknown"), 
                        "duration": 0
                    })
                else:
                    count_skipped += 1
            
            if progress_callback:
                progress_callback(f"📊 Resumen: {len(to_download)} para descargar, {count_skipped} ya presentes.")
                
        return to_download, downloaded_ids

    def run(self, progress_callback=None, remote_files=None, stop_event=None):
        if not self.engine:
            if not self._load_engine(progress_callback):
                return {"success": False, "failed": []}

        to_download, downloaded_ids = self.quick_scan(remote_files=remote_files, progress_callback=progress_callback)
        if not to_download:
            if progress_callback: progress_callback("✅ Todo está al día.")
            return {"success": True, "failed": [], "modified_playlists": []}

        failed_songs = []
        failed_log_path = os.path.join(BASE_DIR, "failed_songs_blacklist.json")
        blacklist = set()
        if os.path.exists(failed_log_path):
            try:
                with open(failed_log_path, "r", encoding="utf-8") as f: blacklist = set(json.load(f))
            except: pass

        modified_playlists = set()
        for song in to_download:
            song_key = f"{song['artist']} - {song['title']}"
            if song_key in blacklist: continue
            if stop_event and stop_event.is_set(): break

            try:
                if progress_callback: progress_callback(f"🎵 {song['artist']} - {song['title']}...")
                song["base_dir"] = self.music_dir
                path, _ = self.engine.process_track(None, song)
                if path:
                    downloaded_ids.add(song['id'])
                    with open(self.db_file, "w", encoding="utf-8") as f:
                        json.dump(list(downloaded_ids), f, indent=4)

                    try:
                        import playlist_generator
                        genres = playlist_generator.fetch_genres_from_provider(song['artist'], song['title'])
                        year = playlist_generator.get_year_from_lastfm(song['artist'], song['title'], path)
                        playlist_generator.update_playlist_for_track(path, genres, year)
                        modified_playlists.add("Todas las canciones.m3u8")
                    except Exception as e:
                        if progress_callback: progress_callback(f"   ⚠️ Error en playlist: {e}")
                else:
                    failed_songs.append(song_key)
                    blacklist.add(song_key)
            except Exception as e:
                failed_songs.append(f"{song_key} (Error: {e})")
                blacklist.add(song_key)

        if os.path.exists(failed_log_path) or failed_songs:
            with open(failed_log_path, "w", encoding="utf-8") as f: json.dump(list(blacklist), f)
            
        return {"success": True, "failed": failed_songs, "modified_playlists": list(modified_playlists)}

if __name__ == "__main__":
    d = DownloadEngine()
    d.run(print)
