import json

# Load overrides
with open('genre_overrides.json', 'r') as f:
    overrides = json.load(f)

# Load artist genres
with open('artist_genres.json', 'r') as f:
    artist_genres = json.load(f)

# Count classified vs unclassified
classified = 0
unclassified = 0
classified_by_override = 0
total = 0

for key, genres in artist_genres.items():
    if key == '$not' or key.startswith('$'):
        continue
    total += 1
    if 'Sin clasificar' in genres:
        unclassified += 1
    else:
        classified += 1

# Check how many can be classified by overrides
for key in artist_genres.keys():
    if key == '$not' or key.startswith('$'):
        continue
    # Extract primary artist
    parts = key.split(' x ')
    if len(parts) == 1:
        parts = key.split(' and ')
    if len(parts) == 1:
        parts = key.split(' with ')
    primary = parts[0].strip()
    
    # Check override
    primary_lower = primary.lower()
    for override_key in overrides.keys():
        if override_key.lower() == primary_lower:
            classified_by_override += 1
            break

print(f'Total artists: {total}')
print(f'Classified: {classified}')
print(f'Unclassified: {unclassified}')
print(f'Can be classified with new overrides: {classified_by_override}')
if total > 0:
    print(f'Potential classification rate: {classified_by_override/total*100:.1f}%')
