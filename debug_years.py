
from genre_classifier import GenreClassifier
import os

def test_classifier():
    classifier = GenreClassifier()
    # Test cases: Artist, Title
    test_songs = [
        ("Queen", "Bohemian Rhapsody"), # 1970s
        ("Nirvana", "Smells Like Teen Spirit"), # 1990s
        ("Eminem", "Without Me"), # 2000s
        ("The Police", "Every Breath You Take (2003 Remaster)"), # Should be 1980s
        ("Daft Punk", "Get Lucky") # 2010s
    ]
    
    print(f"{'Artist':<20} | {'Title':<40} | {'Year':<10}")
    print("-" * 75)
    
    for artist, title in test_songs:
        year = classifier.fetch_year(artist, title)
        print(f"{artist:<20} | {title:<40} | {str(year):<10}")

if __name__ == "__main__":
    test_classifier()
