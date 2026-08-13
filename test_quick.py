from genre_classifier import GenreClassifier
import time

classifier = GenreClassifier(verbose=True)

test_artists = ["Avicii", "Coldplay", "Melendi", "Juice WRLD", "Fito y Fitipaldis"]

print("=" * 60)
print("TEST - Genre Classifier v2")
print("=" * 60)

for artist in test_artists:
    start = time.time()
    genres = classifier.classify(artist)
    elapsed = time.time() - start
    print(f"{artist}: {genres} ({elapsed:.1f}s)")
    time.sleep(1)

print()
print("Stats:", classifier.get_stats())