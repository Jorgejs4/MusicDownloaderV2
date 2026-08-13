import os
import json
import re
import time
import random
import requests
import threading
from urllib.parse import quote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE_DIR, "artist_genres.json")
YEAR_CACHE_PATH = os.path.join(BASE_DIR, "track_years.json")
OVERRIDES_PATH = os.path.join(BASE_DIR, "genre_overrides.json")

# Last.fm API Credentials
LASTFM_API_KEY = "fbd990760310e5c1a1f48e26c750dad6"
# LASTFM_SECRET = "8f9610544f55f76ae4079bd5959ba260" # Guardado para referencia futura

GENRE_MAP = {
    "rap": ["trap", "drill", "grime", "boom bap", "phonk", "gangsta rap", "rap", "underground rap", "southern rap", "hip hop", "hip-hop"],
    "hiphop": ["hip hop", "hip-hop", "urban", "conscious hip hop", "rnb", "contemporary r&b", "soul"],
    "rock": ["rock", "alternative", "indie rock", "grunge", "punk", "metal", "hard rock", "classic rock", "new wave", "indie", "pop rock", "pop-rock"],
    "pop": ["pop", "dance pop", "synthpop", "teen pop", "k-pop", "indie pop", "dance-pop", "kpop", "korean pop"],
    "kpop": ["k-pop", "kpop", "korean pop", "k-pop boy group", "k-pop girl group"],
    "electronica": ["edm", "dance", "electronic", "house", "techno", "trance", "dubstep", "dnb", "electro", "synthwave", "progressive house", "deep house", "uk garage"],
    "lofi/chill": ["lofi", "lo-fi", "chill", "chillhop", "mellow", "ambient", "downtempo", "soul", "jazzhop", "relax", "jazz", "blues", "study beats"],
    "españolas": ["espanol", "español", "spanish", "reggaeton", "urbano latino", "latin trap", "rock en espanol", "pop espanol", "musica ligera", "flamenco", "latin", "musica en espanol"],
}

STATIC_OVERRIDES = {
    "avicii": ["electronica"],
    "daft punk": ["electronica"],
    "deadmau5": ["electronica"],
    "eminem": ["rap"],
    "kendrick lamar": ["hiphop", "rap"],
    "juice wrld": ["rap", "hiphop"],
    "xxxtentacion": ["rap", "lofi/chill"],
    "melendi": ["españolas", "pop", "rock"],
    "bad bunny": ["españolas", "rap"],
    "quevedo": ["españolas", "rap"],
    "rosalia": ["españolas", "pop"],
    "c. tangana": ["españolas", "rap"],
    "ouse": ["lofi/chill"],
    "avgust": ["pop"],
    "will dio": ["rap"],
    "scuare": ["rap"],
    "trill flacko": ["rap"],
    "snoh aalegra": ["lofi/chill", "pop"],
    "a-ha": ["pop", "electronica"],
    "the police": ["rock"],
    "coldplay": ["rock", "pop"],
    "oasis": ["rock"],
    "sting": ["rock", "pop"],
    "logic": ["rap", "hiphop"],
    "twenty one pilots": ["rock", "pop", "rap"],
}

class GenreClassifier:
    def __init__(self, cache_path=None, verbose=True):
        self.cache_path = cache_path or CACHE_PATH
        self.year_cache_path = YEAR_CACHE_PATH
        self.cache = self._load_cache(self.cache_path)
        self.year_cache = self._load_cache(self.year_cache_path)
        self.overrides = self._load_overrides()
        self.verbose = verbose
        self.stats = {"overrides": 0, "lastfm": 0, "musicbrainz": 0, "deezer": 0, "heuristic": 0, "cached": 0}
        self.lock = threading.Lock()
    
    def _load_cache(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _load_overrides(self):
        overrides = {}
        for k, v in STATIC_OVERRIDES.items():
            overrides[self._normalize_key(k)] = v
            
        if os.path.exists(OVERRIDES_PATH):
            try:
                with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
                    user_overrides = json.load(f)
                    for artist, genre in user_overrides.items():
                        norm_artist = self._normalize_key(artist)
                        if isinstance(genre, list):
                            overrides[norm_artist] = genre
                        elif isinstance(genre, str):
                            overrides[norm_artist] = [genre]
            except:
                pass
        return overrides
    
    def _save_cache(self):
        with self.lock:
            try:
                with open(self.cache_path, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, indent=4, ensure_ascii=False)
            except:
                pass

    def _save_year_cache(self):
        with self.lock:
            try:
                with open(self.year_cache_path, "w", encoding="utf-8") as f:
                    json.dump(self.year_cache, f, indent=4, ensure_ascii=False)
            except:
                pass
    
    def _normalize_key(self, name):
        name = str(name or "").lower().strip()
        name = re.split(r" feat\.? | ft\.? | & | , | with ", name, flags=re.IGNORECASE)[0]
        name = re.sub(r"[^\w\s]", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name
    
    def _map_to_genre(self, tags):
        if not tags: return []
        matched = set()
        tags_lower = [t.lower() for t in tags if isinstance(t, str)]
        for genre, keywords in GENRE_MAP.items():
            for keyword in keywords:
                for tag in tags_lower:
                    if keyword == tag or (len(keyword) > 3 and (keyword in tag or tag in keyword)):
                        matched.add(genre)
        return list(matched) if matched else []
    
    def _log(self, msg):
        if self.verbose: print(f"🧬 [Classifier]: {msg}")
    
    def get_metadata(self, artist_name, song_title=None):
        genres = self.classify(artist_name, song_title)
        year = self.fetch_year(artist_name, song_title)
        return {"genres": genres, "year": year, "artist": artist_name, "title": song_title}

    def _fetch_lastfm_tags(self, artist, title=None):
        try:
            params = {"api_key": LASTFM_API_KEY, "format": "json", "autocorrect": 1}
            if title:
                params["method"] = "track.getTopTags"
                params["artist"] = artist
                params["track"] = title
            else:
                params["method"] = "artist.getTopTags"
                params["artist"] = artist
            
            resp = requests.get("http://ws.audioscrobbler.com/2.0/", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                tags_data = data.get("toptags", {}).get("tag", [])
                if not tags_data and title: return self._fetch_lastfm_tags(artist)
                tags = [t.get("name") for t in tags_data[:10]]
                if tags:
                    self.stats["lastfm"] += 1
                    return self._map_to_genre(tags)
            return None
        except: return None

    def _fetch_deezer_metadata(self, artist, title=None):
        try:
            query = f"artist:\"{artist}\""
            if title: query += f" track:\"{title}\""
            url = f"https://api.deezer.com/search?q={quote(query)}"
            resp = requests.get(url, timeout=8).json()
            found_genres = set()
            if resp.get("data"):
                for track in resp["data"][:3]:
                    album_id = track.get("album", {}).get("id")
                    if album_id:
                        alb_resp = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=5).json()
                        genre_list = alb_resp.get("genres", {}).get("data", [])
                        if not genre_list and alb_resp.get("genre_id"):
                            genre_list = [{"name": str(alb_resp.get("genre_id"))}]
                        for g in genre_list:
                            name = g.get("name", "").lower()
                            if name == "132": name = "pop rock"
                            if name == "116": name = "pop"
                            mapped = self._map_to_genre([name])
                            if mapped: found_genres.update(mapped)
            return list(found_genres) if found_genres else None
        except: return None

    def fetch_year(self, artist_name, song_title):
        if not song_title: return None
        
        cache_key = self._normalize_key(f"{artist_name} - {song_title}")
        if cache_key in self.year_cache:
            return self.year_cache[cache_key]

        # Clean title for year lookup
        clean_title = re.sub(r'\s*\(?remaster(ed)?\)?\s*', '', song_title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'\s*\(?\d{4}\s*remaster\)?\s*', '', clean_title, flags=re.IGNORECASE).strip()
        # Remove common year-like patterns from title to avoid false positives
        query_title = re.sub(r'\b(19\d{2}|20\d{2})\b', '', clean_title).strip()

        try:
            # First attempt: Exact match search
            url = f"https://api.deezer.com/search?q=artist:\"{quote(artist_name)}\" track:\"{quote(query_title)}\""
            data = requests.get(url, timeout=8).json()
            
            years = []
            # We check more candidates to find the OLDEST release (usually the original)
            for item in data.get("data", [])[:10]:
                album_id = item.get("album", {}).get("id")
                if album_id:
                    alb = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=5).json()
                    if alb.get("release_date"): 
                        years.append(alb["release_date"][:4])
            
            final_year = None
            if years:
                # Return the MINIMUM year found (likely the original release)
                final_year = min(years)

            # Second attempt: broader search if no results
            if not final_year:
                url = f"https://api.deezer.com/search?q={quote(artist_name + ' ' + query_title)}"
                data = requests.get(url, timeout=8).json()
                for item in data.get("data", [])[:5]:
                    album_id = item.get("album", {}).get("id")
                    if album_id:
                        alb = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=5).json()
                        if alb.get("release_date"): years.append(alb["release_date"][:4])
                if years: final_year = min(years)
            
            if final_year:
                self.year_cache[cache_key] = final_year
                self._save_year_cache()
                return final_year
            
        except: pass
        return None

    def fetch_lyrics(self, artist, title):
        try:
            url = f"https://lrclib.net/api/get?artist_name={quote(artist)}&track_name={quote(title)}"
            data = requests.get(url, timeout=5).json()
            return data.get("syncedLyrics") or data.get("plainLyrics")
        except: return None
    
    def classify(self, artist_name, song_title=None):
        if not artist_name: return ["Sin clasificar"]
        cache_key = self._normalize_key(f"{artist_name} - {song_title}" if song_title else artist_name)
        if cache_key in self.cache:
            self.stats["cached"] += 1
            return self.cache[cache_key]
        artist_key = self._normalize_key(artist_name)
        if artist_key in self.overrides:
            self.stats["overrides"] += 1
            return self.overrides[artist_key]
        self._log(f"Buscando géneros: {artist_name} - {song_title}")
        genres = self._fetch_lastfm_tags(artist_name, song_title)
        if not genres or genres == ["Sin clasificar"]:
            genres = self._fetch_deezer_metadata(artist_name, song_title)
            if genres: self.stats["deezer"] += 1
        if not genres: genres = self._infer_from_name(artist_name)
        self.cache[cache_key] = genres
        self._save_cache()
        return genres

    def _infer_from_name(self, artist_name):
        name_lower = artist_name.lower()
        matched = set()
        for genre, keywords in GENRE_MAP.items():
            for kw in keywords:
                if kw in name_lower: matched.add(genre)
        self.stats["heuristic"] += 1
        return list(matched) if matched else ["Sin clasificar"]

    def get_stats(self):
        return {**self.stats, "total": sum(self.stats.values())}

if __name__ == "__main__":
    classifier = GenreClassifier()
    print(classifier.get_metadata("Sting", "Englishman In New York"))
