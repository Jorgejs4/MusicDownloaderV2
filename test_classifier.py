from genre_classifier import GenreClassifier

classifier = GenreClassifier(verbose=True)

test_artists = ['Avicii', 'Coldplay', 'Melendi']

print("=" * 60)
print("TEST - Genre Classifier")
print("=" * 60)

for artist in test_artists:
    genres = classifier.classify(artist)
    print(f"  {artist}: {genres}")

print()
print("Stats:", classifier.get_stats())