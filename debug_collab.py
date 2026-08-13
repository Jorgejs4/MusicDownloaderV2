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

# Check specific collaborations
test_cases = [
    "calvin harris dua lipa",
    "david guetta sia",
    "eminem rihanna",
    "ellie goulding juice wrld",
    "juice wrld the weeknd"
]

print("Testing collaborations:")
for test in test_cases:
    key = normalize_key(test)
    print(f"  '{test}' -> key: '{key}'")
    print(f"    In overrides: {key in overrides}")
    
    # Try splitting
    separators = [' x ', ' and ', ' with ', ' & ', '/']
    parts = [key]
    for sep in separators:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(sep))
        parts = new_parts
    
    print(f"    Parts: {parts}")
    for part in parts:
        part = part.strip()
        if part in overrides:
            print(f"    MATCH: '{part}' -> {overrides[part]}")
