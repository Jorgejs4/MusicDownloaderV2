import json
import os
from collections import Counter

MUSIC_DIR = "canciones_auto"
artists = []

for root, dirs, files in os.walk(MUSIC_DIR):
    if "_Playlists" in root:
        continue
    for name in files:
        if name.lower().endswith(".mp3"):
            rel_path = os.path.relpath(os.path.join(root, name), MUSIC_DIR)
            parts = rel_path.split(os.sep)
            artist = parts[0] if len(parts) > 1 else "Unknown"
            artists.append(artist)

counter = Counter(artists)
print("Top 50 artistas sin clasificar:")
for artist, count in counter.most_common(50):
    print(f"  {count:3d}x {artist}")