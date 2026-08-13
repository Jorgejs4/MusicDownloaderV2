import difflib
import re
import unicodedata

def normalize_for_comparison(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    words = re.findall(r'\w+', text)
    return " ".join(sorted(words))

def get_canonical_name(name, existing_names, threshold=0.75):
    if not existing_names: return name
    norm_name = normalize_for_comparison(name)
    for existing in existing_names:
        if norm_name == normalize_for_comparison(existing):
            return existing if len(existing) <= len(name) else name
    best_ratio = 0
    best_match = None
    for existing in existing_names:
        ratio = difflib.SequenceMatcher(None, norm_name, normalize_for_comparison(existing)).ratio()
        if ratio > threshold and ratio > best_ratio:
            best_ratio = ratio
            best_match = existing
    if best_match:
        return best_match if len(best_match) <= len(name) else name
    return name

# Tests
existing = ["Rock Alternative"]
print(f"Test 1: {get_canonical_name('Alternative Rock', existing)}") # Should be 'Rock Alternative'
print(f"Test 2: {get_canonical_name('Rock 2024', existing)}") # Should be 'Rock Alternative' (if ratio > 0.75)
print(f"Test 3: {get_canonical_name('Chill Hits', ['Chill'])}") # Should be 'Chill'
