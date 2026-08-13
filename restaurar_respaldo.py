import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_TO_RESTORE = [
    ("music_csv_auto.py.bak", "music_csv_auto.py"),
    ("musicDownloader3.py.bak", "musicDownloader3.py"),
]

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))

def create_backup():
    """Crea una copia de seguridad inicial si no existe."""
    for bak, src in FILES_TO_RESTORE:
        src_path = os.path.join(BASE_DIR, src)
        bak_path = os.path.join(BASE_DIR, bak)
        if os.path.exists(src_path) and not os.path.exists(bak_path):
            shutil.copy2(src_path, bak_path)

def restore_backup():
    safe_print("=" * 60)
    safe_print("[RESTAURADOR DE RESPALDO DE MOTOR DE DESCARGA]")
    safe_print("=" * 60)
    
    restored_any = False
    for bak, target in FILES_TO_RESTORE:
        bak_path = os.path.join(BASE_DIR, bak)
        target_path = os.path.join(BASE_DIR, target)
        
        if os.path.exists(bak_path):
            shutil.copy2(bak_path, target_path)
            safe_print(f"[OK] Restaurado correctamente: {target} desde {bak}")
            restored_any = True
        else:
            safe_print(f"[WARN] No se encontro el archivo de respaldo: {bak}")
            
    if restored_any:
        safe_print("\nEl motor de descarga ha sido restaurado a su version anterior.")
        return True
    else:
        safe_print("\nNo fue posible restaurar ningun archivo.")
        return False

if __name__ == "__main__":
    restore_backup()
