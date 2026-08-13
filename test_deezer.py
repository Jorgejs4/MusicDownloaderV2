import requests
import json

print('=== Test Deezer API ===')
url = 'https://api.deezer.com/search/artist?q=Avicii'
r = requests.get(url, timeout=10)
print('Status:', r.status_code)

if r.status_code == 200:
    data = r.json()
    if data.get('data'):
        artist = data['data'][0]
        print('Artist:', artist.get('name'))
        artist_id = artist.get('id')
        print('ID:', artist_id)
        
        # Get genre info
        detail_url = 'https://api.deezer.com/artist/' + str(artist_id)
        r2 = requests.get(detail_url, timeout=10)
        if r2.status_code == 200:
            d = r2.json()
            print('Genres:', d.get('genres'))
            print('Keys:', list(d.keys()))

print()
print('=== Test mapping ===')
# Test our genre mapping
tags = ['Electronic', 'EDM', 'Dance', 'Pop']
GENRE_MAP = {
    'Electronic / Dance': ['edm', 'dance', 'electronic', 'house'],
    'Pop / R&B': ['pop'],
}

matched = set()
for tag in tags:
    for genre, keywords in GENRE_MAP.items():
        for kw in keywords:
            if kw in tag.lower():
                matched.add(genre)
                print(f'{tag} matches {genre} via {kw}')

print('Matched genres:', list(matched))
