import json

with open('artist_genres.json', 'r') as f:
    data = json.load(f)

artists = set()
for key in data.keys():
    if key == '$not' or key.startswith('$'):
        continue
    parts = key.split(' x ')
    if len(parts) == 1:
        parts = key.split(' and ')
    if len(parts) == 1:
        parts = key.split(' with ')
    primary = parts[0].strip().lower()
    artists.add(primary)

with open('unique_artists.txt', 'w') as f:
    for a in sorted(artists):
        f.write(a + '\n')

print(f'Found {len(artists)} unique primary artists')
