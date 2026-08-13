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

# Check if full keys match
matched_full = []
unmatched = []

for artist_key in artist_genres.keys():
    if artist_key.startswith('$'):
        continue
    
    key = normalize_key(artist_key)
    
    # Check full key match
    if key in overrides:
        matched_full.append((artist_key, overrides[key]))
    else:
        unmatched.append(artist_key)

print(f'Full key matches: {len(matched_full)}')
print(f'Unmatched: {len(unmatched)}')

print('\nMatched full keys:')
for key, genre in matched_full[:30]:
    print(f'  "{key}": {genre}')

print('\nUnmatched sample:')
for key in unmatched[:30]:
    print(f'  "{key}"')
