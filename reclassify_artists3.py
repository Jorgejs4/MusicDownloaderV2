import json
import re
from collections import Counter

with open('genre_overrides.json', 'r') as f:
    overrides = json.load(f)

with open('artist_genres.json', 'r') as f:
    artist_genres = json.load(f)

def normalize_key(name):
    name = str(name or '').lower().strip()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_genres_for_artist(artist_key, overrides):
    key = normalize_key(artist_key)
    
    if key in overrides:
        return overrides[key]
    
    # Split by spaces and check each word
    words = key.split(' ')
    
    # Try each word individually
    for word in words:
        word = word.strip()
        if word in overrides:
            return overrides[word]
    
    # Try first 2-word combination
    for i in range(len(words) - 1):
        two_words = f"{words[i]} {words[i+1]}"
        if two_words in overrides:
            return overrides[two_words]
    
    # Try first 3-word combination
    for i in range(len(words) - 2):
        three_words = f"{words[i]} {words[i+1]} {words[i+2]}"
        if three_words in overrides:
            return overrides[three_words]
    
    return None

# Re-classify all artists
new_cache = {}
classified_count = 0
unclassified_count = 0
all_genres = []

for artist_key, old_genres in artist_genres.items():
    if artist_key.startswith('$'):
        new_cache[artist_key] = old_genres
        continue
    
    genres = get_genres_for_artist(artist_key, overrides)
    
    if genres:
        new_cache[artist_key] = genres
        classified_count += 1
        if isinstance(genres, list):
            all_genres.extend(genres)
        else:
            all_genres.append(genres)
    else:
        new_cache[artist_key] = ["Sin clasificar"]
        unclassified_count += 1

# Save new cache
with open('artist_genres.json', 'w', encoding='utf-8') as f:
    json.dump(new_cache, f, indent=4, ensure_ascii=False)

print(f'Classification Results:')
print(f'  Classified: {classified_count}')
print(f'  Unclassified: {unclassified_count}')
print(f'  Total: {classified_count + unclassified_count}')

if classified_count + unclassified_count > 0:
    rate = classified_count / (classified_count + unclassified_count) * 100
    print(f'  Classification rate: {rate:.1f}%')

genre_counts = Counter(all_genres)
print('\nGenre distribution:')
for genre, count in genre_counts.most_common():
    print(f'  {genre}: {count}')

print('\nSaved to artist_genres.json')
