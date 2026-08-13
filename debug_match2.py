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

# Check all artists that could be matched
matched = []
unmatched = []

for artist_key in artist_genres.keys():
    if artist_key.startswith('$'):
        continue
    
    # Extract primary artist (first artist before ' x ', ' and ', ' with ')
    parts = artist_key.split(' x ')
    if len(parts) == 1:
        parts = artist_key.split(' and ')
    if len(parts) == 1:
        parts = artist_key.split(' with ')
    if len(parts) == 1:
        # Try just splitting by space for single-word keys
        primary = artist_key.split(' ')[0].strip()
    else:
        primary = parts[0].strip()
    
    key = normalize_key(primary)
    
    if key in overrides:
        matched.append((artist_key, primary, overrides[key]))
    else:
        unmatched.append((artist_key, primary))

print(f'Matched: {len(matched)}')
print(f'Unmatched: {len(unmatched)}')

print('\nMatched artists:')
for key, primary, genre in matched[:50]:
    print(f'  {primary}: {genre}')

print(f'\nUnmatched sample (first 50):')
for key, primary in unmatched[:50]:
    print(f'  {primary}')
