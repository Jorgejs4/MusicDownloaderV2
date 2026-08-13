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

# Get all genres for an artist or collaboration
def get_genres_for_artist(artist_key, overrides):
    key = normalize_key(artist_key)
    
    # Check full key
    if key in overrides:
        return overrides[key]
    
    # Split by various separators and check each part
    separators = [' x ', ' and ', ' with ', ' & ', '/', ' featuring ', ' feat. ', ' ft. ']
    parts = [key]
    for sep in separators:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(sep))
        parts = new_parts
    
    # Also try splitting by common patterns
    # Check each individual word as potential artist name
    words = key.split(' ')
    
    for part in parts:
        part = part.strip()
        if part in overrides:
            return overrides[part]
    
    # Try first word
    first_word = words[0] if words else key
    if first_word in overrides:
        return overrides[first_word]
    
    return None

# Re-classify all artists
matched = []
unmatched = []
all_genres = []

for artist_key in artist_genres.keys():
    if artist_key.startswith('$'):
        continue
    
    genres = get_genres_for_artist(artist_key, overrides)
    
    if genres:
        matched.append((artist_key, genres))
        all_genres.extend(genres)
    else:
        unmatched.append(artist_key)

print(f'Classified: {len(matched)}')
print(f'Unclassified: {len(unmatched)}')
print(f'Total: {len(matched) + len(unmatched)}')

if len(matched) + len(unmatched) > 0:
    print(f'Classification rate: {len(matched)/(len(matched) + len(unmatched))*100:.1f}%')

# Count genres
from collections import Counter
genre_counts = Counter(all_genres)
print('\nGenre distribution:')
for genre, count in genre_counts.most_common():
    print(f'  {genre}: {count}')

print('\nSample matched:')
for key, genres in matched[:30]:
    print(f'  "{key}": {genres}')

print('\nUnmatched sample:')
for key in unmatched[:30]:
    print(f'  "{key}"')
