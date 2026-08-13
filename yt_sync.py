"""
yt_sync.py — Sincronización con YouTube Music
=============================================
Sincroniza las canciones del playlist.csv con una playlist de YouTube Music.

REQUISITOS (una sola vez):
  1. pip install ytmusicapi
  2. ytmusicapi oauth        ← sigue las instrucciones, guarda como oauth.json
     (o: ytmusicapi browser  si prefieres cabeceras del navegador)

CHANGELOG v1.1:
- FIX: Manejo de errores más claro con instrucciones de setup.
- FIX: Verificación de oauth.json antes de iniciar.
- FIX: Bloque de canciones reducido a 20 (más estable).
- ADD: Modo --dry-run para probar sin modificar YT Music.
- ADD: Contador de progreso visible.
"""

import os
import csv
import json
import time
import argparse
from dotenv import load_dotenv

try:
    from ytmusicapi import YTMusic
    YTMUSICAPI_AVAILABLE = True
except ImportError:
    YTMusic = None
    YTMUSICAPI_AVAILABLE = False

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_CSV = os.path.join(BASE_DIR, "playlist.csv")
AUTH_FILE = os.path.join(BASE_DIR, "oauth.json")
PLAYLIST_NAME = "Spotify Liked (Auto)"
BATCH_SIZE = 20       # Canciones por lote (menor = más estable)
SEARCH_DELAY = 0.3    # Segundos entre búsquedas para no ser bloqueado


def check_requirements() -> bool:
    """Verifica que todo esté listo antes de continuar. Devuelve False si falta algo."""
    ok = True

    if not YTMUSICAPI_AVAILABLE:
        print("\n❌ Falta 'ytmusicapi'. Instálalo con:")
        print("   pip install ytmusicapi")
        ok = False

    if not os.path.exists(AUTH_FILE):
        print(f"\n❌ No se encontró '{AUTH_FILE}'.")
        print("Para crearlo, ejecuta UNO de estos comandos y sigue las instrucciones:")
        print()
        print("  Opción A (recomendada — OAuth):")
        print("    ytmusicapi oauth")
        print("    → Guarda el resultado como 'oauth.json' en esta carpeta.")
        print()
        print("  Opción B (cabeceras del navegador):")
        print("    ytmusicapi browser")
        print("    → Pega las cabeceras cuando se pida y guarda como 'oauth.json'.")
        ok = False
    else:
        # Verificar que el JSON es válido
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # El archivo template viene con placeholders; detectarlos
            if "SAPISIDHASH <pegado-desde" in str(data) or "tu-cookie" in str(data):
                print(f"\n❌ '{AUTH_FILE}' contiene valores de ejemplo sin rellenar.")
                print("Ejecuta 'ytmusicapi oauth' y sobreescribe el archivo con los datos reales.")
                ok = False
        except json.JSONDecodeError:
            print(f"\n❌ '{AUTH_FILE}' no es un JSON válido. Vuelve a generarlo con 'ytmusicapi oauth'.")
            ok = False

    if not os.path.exists(PROJECT_CSV):
        print(f"\n❌ No se encontró '{PROJECT_CSV}'. Exporta primero tu playlist desde Exportify.")
        ok = False

    return ok


def setup_ytmusic() -> "YTMusic | None":
    """Inicia sesión en YTMusic con manejo de errores descriptivo."""
    try:
        yt = YTMusic(AUTH_FILE)
        # Verificación rápida: pedimos las playlists para confirmar que la sesión funciona
        yt.get_library_playlists(limit=1)
        print("✅ Sesión de YouTube Music iniciada correctamente.")
        return yt
    except Exception as e:
        error_msg = str(e).lower()
        if "401" in error_msg or "unauthorized" in error_msg:
            print(f"\n❌ Sesión de YouTube Music caducada o inválida.")
            print("Vuelve a ejecutar 'ytmusicapi oauth' y reemplaza 'oauth.json'.")
        elif "403" in error_msg or "forbidden" in error_msg:
            print(f"\n❌ Acceso denegado. Puede que la cuenta no tenga YouTube Music Premium.")
        else:
            print(f"\n❌ Error al iniciar YTMusic: {e}")
        return None


def get_or_create_playlist(yt: "YTMusic", name: str) -> str:
    """Busca la playlist por nombre o la crea si no existe. Devuelve el playlistId."""
    try:
        playlists = yt.get_library_playlists(limit=50)
        for pl in playlists:
            if pl.get("title") == name:
                print(f"📋 Playlist encontrada: '{name}' (ID: {pl['playlistId']})")
                return pl["playlistId"]
    except Exception as e:
        print(f"⚠ No se pudieron obtener las playlists: {e}")

    print(f"🆕 Creando nueva playlist: '{name}'...")
    playlist_id = yt.create_playlist(
        name,
        "Sincronizada automáticamente desde Spotify",
        privacy_status="PRIVATE",
    )
    print(f"✅ Playlist creada con ID: {playlist_id}")
    return playlist_id


def load_csv_songs() -> list[dict]:
    """Carga canciones del CSV y normaliza los nombres de columna."""
    songs = []
    with open(PROJECT_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (
                row.get("Nombre de la canción")
                or row.get("Track Name")
                or row.get("Name")
                or ""
            ).strip()
            artist = (
                row.get("Nombre(s) del artista")
                or row.get("Artist Name(s)")
                or row.get("Artist")
                or ""
            ).strip()
            if title and artist:
                songs.append({"title": title, "artist": artist})
    return songs


def format_time(seconds):
    if seconds < 0: seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

def sync_to_yt_music(dry_run: bool = False):
    """Función principal de sincronización."""

    # 1. Verificar requisitos
    if not check_requirements():
        print("\n⛔ Sincronización con YouTube Music cancelada. Resuelve los errores de arriba primero.")
        return

    # 2. Conectar
    yt = setup_ytmusic()
    if not yt:
        return

    # 3. Obtener o crear playlist
    playlist_id = get_or_create_playlist(yt, PLAYLIST_NAME)

    # 4. Obtener canciones ya en la playlist (para evitar duplicados)
    print("⏳ Obteniendo canciones actuales de la playlist...")
    current_video_ids: set[str] = set()
    try:
        current_pl = yt.get_playlist(playlist_id, limit=5000)
        current_video_ids = {
            item["videoId"]
            for item in current_pl.get("tracks", [])
            if item.get("videoId")
        }
        print(f"   → {len(current_video_ids)} canciones ya en la playlist.")
    except Exception as e:
        print(f"⚠ No se pudieron obtener las canciones actuales: {e}")

    # 5. Leer CSV
    songs = load_csv_songs()
    print(f"\n🔍 Analizando {len(songs)} canciones del CSV...")

    # 6. Buscar en YT Music y colectar las que faltan
    to_add: list[str] = []
    not_found: list[str] = []
    start_search_time = time.time()

    for idx, row in enumerate(songs, start=1):
        title, artist = row["title"], row["artist"]
        query = f"{artist} - {title}"

        try:
            results = yt.search(query, filter="songs", limit=1)
            if results:
                video_id = results[0].get("videoId")
                if video_id and video_id not in current_video_ids:
                    to_add.append(video_id)
                    current_video_ids.add(video_id)
                    print(f"  [{idx}/{len(songs)}] ✅ {query}")
                else:
                    print(f"  [{idx}/{len(songs)}] 📌 Ya existe: {query}")
            else:
                not_found.append(query)
                print(f"  [{idx}/{len(songs)}] ❓ No encontrada: {query}")
        except Exception as e:
            not_found.append(query)
            print(f"  [{idx}/{len(songs)}] ⚠ Error buscando '{query}': {e}")

        # Estimación de búsqueda
        elapsed = time.time() - start_search_time
        avg_per_song = elapsed / idx
        remaining_songs = len(songs) - idx
        est_remaining = avg_per_song * remaining_songs
        if idx % 5 == 0 or idx == len(songs):
            print(f"  ⏱️ Búsqueda: {idx}/{len(songs)} | Restante: ~{format_time(est_remaining)}")

        time.sleep(SEARCH_DELAY)

    # 7. Añadir a la playlist en lotes
    if not to_add:
        print("\n😎 La playlist de YT Music ya está al día. Nada que añadir.")
    elif dry_run:
        print(f"\n🧪 DRY-RUN: Se añadirían {len(to_add)} canciones (no se modificó nada).")
    else:
        print(f"\n🚀 Añadiendo {len(to_add)} canciones en lotes de {BATCH_SIZE}...")
        added_total = 0
        start_add_time = time.time()
        total_batches = (len(to_add) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(to_add), BATCH_SIZE):
            batch = to_add[i : i + BATCH_SIZE]
            current_batch_num = (i // BATCH_SIZE) + 1
            try:
                yt.add_playlist_items(playlist_id, batch)
                added_total += len(batch)
                
                # Estimación de envío
                elapsed_add = time.time() - start_add_time
                avg_per_batch = elapsed_add / current_batch_num
                remaining_batches = total_batches - current_batch_num
                est_rem_add = avg_per_batch * remaining_batches
                
                print(f"  ✔ Lote {current_batch_num}/{total_batches}: {added_total}/{len(to_add)} canciones | Restante: ~{format_time(est_rem_add)}")
                time.sleep(1)  # Pausa entre lotes
            except Exception as e:
                print(f"  ❌ Error en lote {current_batch_num}: {e}")

    # 8. Resumen final
    print(f"\n{'─'*40}")
    print(f"  Añadidas:      {len(to_add)}")
    print(f"  No encontradas: {len(not_found)}")
    if not_found:
        print(f"\n  Canciones no encontradas en YT Music:")
        for s in not_found[:10]:
            print(f"    - {s}")
        if len(not_found) > 10:
            print(f"    ... y {len(not_found) - 10} más.")
    print(f"{'─'*40}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincroniza playlist.csv con YouTube Music")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué se añadiría sin modificar nada",
    )
    args = parser.parse_args()
    sync_to_yt_music(dry_run=args.dry_run)