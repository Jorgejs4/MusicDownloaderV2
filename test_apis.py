import requests

def test_discogs(artist):
    try:
        url = f'https://api.discogs.com/database/search?q={artist}&type=artist'
        headers = {'User-Agent': 'Mozilla/5.0 (MusicDownloader/1.0)'}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                genres = result.get('genre', [])
                style = result.get('style', [])
                return f"Genres: {genres}, Styles: {style[:3]}"
        return f'Status: {resp.status_code}'
    except Exception as e:
        return f'Error: {e}'

test_artists = ['Radiohead', 'Daft Punk', 'Kendrick Lamar', 'Cuco', 'Brakence']
for artist in test_artists:
    result = test_discogs(artist)
    print(f'{artist}: {result}')
