import os, json, csv, re
import musicDownloader3 as engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_CSV = os.path.join(BASE_DIR, "playlist.csv")
DB_FILE = os.path.join(BASE_DIR, "downloaded.json")
REPORT_FILE = os.path.join(BASE_DIR, "verification_report.json")
QUARANTINE_FILE = os.path.join(BASE_DIR, "quarantine_songs.json")
MUSIC_DIR = os.path.join(BASE_DIR, "canciones_auto")

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name or "")).strip()

def run_verification():
    if not os.path.exists(PROJECT_CSV): return
    
    print(f"\n{'='*50}\n🔎 INICIANDO VERIFICACIÓN DE CALIDAD\n{'='*50}")
    
    downloaded_ids = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: downloaded_ids = json.load(f)
    
    valid_count = 0
    quarantine_list = []
    
    # Mapeo de archivos locales
    installed = {}
    for root, dirs, files in os.walk(MUSIC_DIR):
        for f in files:
            if f.lower().endswith(".mp3"): installed[f.lower()] = os.path.join(root, f)

    with open(PROJECT_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Nombre de la canción") or row.get("Track Name") or row.get("Name")
            artist = row.get("Nombre(s) del artista") or row.get("Artist Name(s)") or row.get("Artist")
            if not title or not artist: continue
            
            clean_name = f"{sanitize(artist)} - {sanitize(title)}.mp3".lower()
            if clean_name in installed:
                path = installed[clean_name]
                size = os.path.getsize(path)
                
                # Control de calidad básico: si pesa menos de 2MB o no tiene manifest
                reason = None
                if size < 2 * 1024 * 1024: reason = "Archivo sospechosamente pequeño"
                
                if reason:
                    quarantine_list.append({"song": f"{artist} - {title}", "reason": reason, "path": path})
                else:
                    valid_count += 1

    # Informe final
    print(f"✅ Verificación completada.")
    print(f"   • Canciones OK: {valid_count}")
    print(f"   • En cuarentena: {len(quarantine_list)}")
    
    if quarantine_list:
        print("\n⚠️ DETALLE DE CUARENTENA:")
        for q in quarantine_list:
            print(f"   • {q['song']} -> {q['reason']}")
        
        with open(QUARANTINE_FILE, "w", encoding="utf-8") as f:
            json.dump(quarantine_list, f, indent=4, ensure_ascii=False)
        print(f"\n📂 Listado guardado en quarantine_songs.json")
    
    print(f"{'='*50}\n")

if __name__ == "__main__":
    run_verification()
