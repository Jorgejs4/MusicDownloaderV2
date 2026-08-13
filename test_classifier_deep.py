import requests
from urllib.parse import quote
import json

LASTFM_API_KEY = "8f3d9d3000b200b8e73456c2763e1460"

def test_lastfm(artist, track=None):
    print(f"\n--- Testing Last.fm: {artist} - {track or 'Artist only'} ---")
    params = {
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "autocorrect": 1
    }
    if track:
        params["method"] = "track.getTopTags"
        params["artist"] = artist
        params["track"] = track
    else:
        params["method"] = "artist.getTopTags"
        params["artist"] = artist
        
    try:
        resp = requests.get("http://ws.audioscrobbler.com/2.0/", params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            tags = data.get("toptags" if track else "toptags", {}).get("tag", [])
            tag_names = [t.get("name") for t in tags[:15]]
            print(f"Tags found: {tag_names}")
            return tag_names
        else:
            print(f"Error Body: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return []

def test_deezer(artist):
    print(f"\n--- Testing Deezer: {artist} ---")
    try:
        url = f"https://api.deezer.com/search/artist?q={quote(artist)}"
        resp = requests.get(url, timeout=10).json()
        if resp.get("data"):
            a_id = resp["data"][0]["id"]
            print(f"Artist ID: {a_id}")
            alb_url = f"https://api.deezer.com/artist/{a_id}/albums"
            albs = requests.get(alb_url, timeout=10).json()
            for alb in albs.get("data", [])[:3]:
                genre_id = alb.get("genre_id")
                print(f"Album: {alb.get('title')} | Genre ID: {genre_id}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    # Test typical problematic artists/tracks
    test_lastfm("Sting", "Englishman In New York")
    test_lastfm("Twenty One Pilots", "Morph")
    test_lastfm("Logic", "The Glorious Five")
    test_lastfm("Melendi")
    test_deezer("Melendi")
