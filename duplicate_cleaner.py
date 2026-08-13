import os
import re
import json
import unicodedata
from difflib import SequenceMatcher

def normalize_name(name):
    """Limpia el nombre del archivo para comparación."""
    name = os.path.splitext(name)[0].lower()
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = re.sub(r'[^\w\s]', '', name)
    return " ".join(name.split())

def find_duplicates(music_root):
    """
    Escanea la biblioteca en busca de posibles duplicados.
    Retorna una lista de grupos de archivos sospechosos.
    """
    if not os.path.exists(music_root):
        return []

    all_files = []
    for root, _, files in os.walk(music_root):
        for f in files:
            if f.lower().endswith(".mp3"):
                abs_path = os.path.join(root, f)
                all_files.append({
                    "path": abs_path,
                    "rel_path": os.path.relpath(abs_path, music_root),
                    "name": f,
                    "norm": normalize_name(f),
                    "size": os.path.getsize(abs_path)
                })

    duplicates = []
    processed = set()

    for i, file1 in enumerate(all_files):
        if file1["path"] in processed: continue
        
        group = [file1]
        for j in range(i + 1, len(all_files)):
            file2 = all_files[j]
            if file2["path"] in processed: continue

            # Lógica de detección:
            # 1. Nombres idénticos normalizados
            # 2. Similitud muy alta (>90%)
            # 3. Tamaños muy parecidos (margen 5%)
            ratio = SequenceMatcher(None, file1["norm"], file2["norm"]).ratio()
            size_diff = abs(file1["size"] - file2["size"]) / max(file1["size"], 1)

            if file1["norm"] == file2["norm"] or (ratio > 0.9 and size_diff < 0.05):
                group.append(file2)
                processed.add(file2["path"])

        if len(group) > 1:
            processed.add(file1["path"])
            duplicates.append(group)

    return duplicates

if __name__ == "__main__":
    # Test rápido
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    dupes = find_duplicates(path)
    for g in dupes:
        print("\nPosible Duplicado:")
        for f in g:
            print(f"  - {f['rel_path']} ({f['size']/1024/1024:.2f} MB)")
