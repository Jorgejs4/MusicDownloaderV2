import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE_DIR, "artist_genres.json")
OVERRIDES_PATH = os.path.join(BASE_DIR, "genre_overrides.json")

STATIC_OVERRIDES = {
    "avicii": ["Electronic / Dance"],
    "daft punk": ["Electronic / Dance"],
    "deadmau5": ["Electronic / Dance"],
    "calvin harris": ["Electronic / Dance"],
    "martin garrix": ["Electronic / Dance"],
    "zedd": ["Electronic / Dance"],
    "skrillex": ["Electronic / Dance"],
    "tiesto": ["Electronic / Dance"],
    "linkin park": ["Rock / Alternative"],
    "red hot chili peppers": ["Rock / Alternative"],
    "coldplay": ["Rock / Alternative"],
    "oasis": ["Rock / Alternative"],
    "u2": ["Rock / Alternative"],
    "green day": ["Rock / Alternative"],
    "eminem": ["Hip Hop / Rap / Trap"],
    "kendrick lamar": ["Hip Hop / Rap / Trap"],
    "juice wrld": ["Hip Hop / Rap / Trap"],
    "lil wayne": ["Hip Hop / Rap / Trap"],
    "drake": ["Hip Hop / Rap / Trap"],
    "kanye west": ["Hip Hop / Rap / Trap"],
    "dua lipa": ["Pop / R&B"],
    "bruno mars": ["Pop / R&B"],
    "billie eilish": ["Pop / R&B"],
    "lady gaga": ["Pop / R&B"],
    "good kid": ["Rock / Alternative"],
    "xxxtentacion": ["Hip Hop / Rap / Trap"],
    "$not": ["Chill / Lofi / Soul"],
}

def load_overrides():
    overrides = dict(STATIC_OVERRIDES)
    if os.path.exists(OVERRIDES_PATH):
        try:
            with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
                user_overrides = json.load(f)
                for artist, genre in user_overrides.items():
                    if isinstance(genre, list):
                        overrides[artist.lower()] = genre
                    elif isinstance(genre, str):
                        overrides[artist.lower()] = [genre]
        except Exception as e:
            print(f"Error loading overrides: {e}")
    return overrides

def normalize_key(name):
    name = str(name or "").lower().strip()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def classify_artist(artist_name, overrides):
    if not artist_name:
        return ["Sin clasificar"]
    
    key = normalize_key(artist_name)
    
    if key in overrides:
        genres = overrides[key]
        print(f"  {artist_name} -> {genres} [override]")
        return genres
    
    return ["Sin clasificar"]

def main():
    print("Loading overrides...")
    overrides = load_overrides()
    print(f"Loaded {len(overrides)} artist overrides")
    
    # Load existing artist genres
    artist_genres = {}
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                artist_genres = json.load(f)
        except:
            pass
    
    print(f"Found {len(artist_genres)} artists in cache")
    
    # Re-classify all artists using new overrides
    new_cache = {}
    classified = 0
    unclassified = 0
    
    for artist_key, old_genres in artist_genres.items():
        if artist_key.startswith('$'):
            new_cache[artist_key] = old_genres
            continue
        
        # Extract primary artist (first artist before ' x ', ' and ', ' with ')
        parts = artist_key.split(' x ')
        if len(parts) == 1:
            parts = artist_key.split(' and ')
        if len(parts) == 1:
            parts = artist_key.split(' with ')
        primary_artist = parts[0].strip()
        
        # Try to classify using overrides
        key = normalize_key(primary_artist)
        
        if key in overrides:
            genres = overrides[key]
            new_cache[artist_key] = genres
            classified += 1
        else:
            # Keep original classification
            new_cache[artist_key] = old_genres
            unclassified += 1
    
    # Save new cache
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(new_cache, f, indent=4, ensure_ascii=False)
    
    print(f"\nResults:")
    print(f"  Classified with new overrides: {classified}")
    print(f"  Still unclassified: {unclassified}")
    print(f"  Total: {len(new_cache)}")
    
    if len(new_cache) > 0:
        print(f"  Classification rate: {classified/len(new_cache)*100:.1f}%")
    
    print(f"\nCache saved to {CACHE_PATH}")

if __name__ == "__main__":
    main()
