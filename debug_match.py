import json
import re

with open('genre_overrides.json', 'r') as f:
    overrides = json.load(f)

with open('artist_genres.json', 'r') as f:
    artist_genres = json.load(f)

def normalize_key(name):
    name = str(name or '').lower().strip()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# Check some artists that should match
test_artists = ['24kgoldn', 'iann dior', 'j cole', 'lil skies', 'lil uzi vert', 'g eazy', 'kasabian', 'bastille', 'j cole']

print('Testing artist matching:')
for artist in test_artists:
    key = normalize_key(artist)
    in_overrides = key in overrides
    matching_key = None
    for k in overrides.keys():
        if k.lower() == key.lower():
            matching_key = k
            break
    print(f'{artist} -> key: "{key}" -> in_overrides: {in_overrides}, matching: {matching_key}')

# Check a few entries from artist_genres
print('\nSample artist_genres keys:')
for i, key in enumerate(list(artist_genres.keys())[:20]):
    if not key.startswith('$'):
        print(f'  "{key}"')
