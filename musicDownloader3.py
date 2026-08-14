import os, re, json, time, shutil, logging, unicodedata, sys, subprocess
import yt_dlp
from mutagen.id3 import ID3, TIT2, TPE1, TALB, USLT, APIC, TYER, TDRC
from mutagen.mp3 import MP3
from difflib import SequenceMatcher

# Importar clasificador para metadatos
try:
    from genre_classifier import GenreClassifier
    classifier = GenreClassifier(verbose=False)
except ImportError:
    classifier = None

logging.basicConfig(level=logging.INFO, format="[CORE] %(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("MusicEngine")

def _safe_console_text(text):
    return str(text or "").encode("ascii", errors="replace").decode("ascii")

def _safe_print(text):
    print(_safe_console_text(text))

_safe_print("Motor de descarga (musicDownloader3) cargado correctamente.")

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name or "")).strip()

def get_ffmpeg_location():
    """Localiza los binarios incluidos tanto en el proyecto como en el EXE."""
    candidates = []
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidates.append(os.path.join(bundle_dir, "bin"))

    module_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(module_dir, "bin"))
    candidates.append(os.path.join(os.path.dirname(module_dir), "bin"))

    for directory in candidates:
        ffmpeg = os.path.join(directory, "ffmpeg.exe")
        ffprobe = os.path.join(directory, "ffprobe.exe")
        if os.path.isfile(ffmpeg) and os.path.isfile(ffprobe):
            return directory

    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return shutil.which("ffmpeg")
    return None

def get_ydl_opts(out_path):
    node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.EXE"
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
    }
    if node_path and os.path.exists(node_path):
        opts["jsruntimes"] = [node_path]
    ffmpeg_location = get_ffmpeg_location()
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    # No inyectar un po_token placeholder: puede invalidar la extracción.
    opts["extractor_args"] = {"youtube": {"player_client": ["web_creator", "android", "tv"]}}
    return opts

def is_valid_match(yt_entry, track_title, track_artist, expected_duration=None):
    """Compara el título y duración de YouTube con los metadatos con alta tolerancia."""
    yt_title = str(yt_entry.get('title', '')).lower()
    yt_duration = yt_entry.get('duration')
    
    def clean(text):
        # Normalización profunda
        text = unicodedata.normalize("NFKD", str(text or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r'[^\w\s]', ' ', text).lower()
        return set(text.split())

    yt_words = clean(yt_title)
    t_words = clean(track_title)
    a_words = clean(track_artist)
    
    # 1. Filtro de duración (Margen de 30 segundos para ser muy permisivo con intros)
    if expected_duration and yt_duration:
        try:
            diff = abs(int(yt_duration) - int(expected_duration))
            if diff > 35: # Subido a 35s para no perder versiones oficiales con intro
                log.warning(f"Salto por duracion: YT={yt_duration}s vs Esperado={expected_duration}s (Diff={diff}s)")
                return False
        except: pass

    # 2. Palabras prohibidas CRÍTICAS
    # Rechazo absoluto si contienen estas palabras, no importa el contexto.
    forbidden = ["cover", "tribute", "reaction", "slowed", "reverb", "karaoke", "teaser", "leak", "loop", "remix"]
    for f in forbidden:
        if f in yt_title:
            log.warning(f"Rechazado por palabra prohibida absoluta ({f}): {yt_title}")
            return False

    # 3. Puntuación por Palabras Clave
    # ¿Cuántas palabras del título y artista de Spotify están en el vídeo de YT?
    needed_words = t_words.union(a_words)
    found_words = needed_words.intersection(yt_words)
    
    # Las palabras del título valen doble
    title_found = t_words.intersection(yt_words)
    artist_found = a_words.intersection(yt_words)
    
    score = (len(title_found) / len(t_words) * 0.7) + (len(artist_found) / len(a_words) * 0.3) if t_words and a_words else 0
    
    # Bonus por oficialidad
    channel = str(yt_entry.get('uploader', '') or "").lower()
    is_official = "topic" in channel or "official" in channel or any(w in channel for w in a_words)
    if is_official: score += 0.2
    
    # Aceptar si el score es decente (0.7) o si es oficial y el título está casi todo
    success = score >= 0.7 or (is_official and len(title_found) / len(t_words) > 0.8)
    
    if not success:
        log.warning(f"Candidato rechazado (Score: {score:.2f}): {yt_title}")
        
    return success

def normalize_loudness(file_path):
    """Normaliza el volumen del archivo MP3 a -14 LUFS usando FFmpeg."""
    if not os.path.exists(file_path): return
    
    temp_out = file_path.replace(".mp3", "_norm.mp3")
    # Filtro loudnorm: I=-14 (objetivo), TP=-1.0 (True Peak), LRA=11 (Rango dinámico)
    ffmpeg_location = get_ffmpeg_location()
    ffmpeg_command = (
        os.path.join(ffmpeg_location, "ffmpeg.exe")
        if ffmpeg_location and os.path.isdir(ffmpeg_location)
        else (ffmpeg_location or "ffmpeg")
    )
    cmd = [
        ffmpeg_command, "-y", "-i", file_path,
        "-filter:a", "loudnorm=I=-14:TP=-1.0:LRA=11",
        "-ar", "44100", "-b:a", "320k",
        temp_out
    ]
    
    try:
        log.info(f"🔊 Normalizando audio a -14 LUFS: {os.path.basename(file_path)}")
        res = subprocess.run(cmd, capture_output=True, check=True)
        if os.path.exists(temp_out):
            os.replace(temp_out, file_path) # Sobrescribir original con el normalizado
            return True
    except Exception as e:
        log.warning(f"⚠️ Error en normalización: {e}")
        if os.path.exists(temp_out): os.remove(temp_out)
    return False

def process_track(genius, track):
    """Procesa una canciÃ³n: busca, descarga y etiqueta"""
    try:
        title = track.get("title", "Unknown Title")
        artist = track.get("artist", "Unknown Artist")
        album = track.get("album", "Unknown Album")
        duration = track.get("duration") # Esperamos que venga en segundos
        force_redownload = bool(track.get("force_redownload"))

        safe_artist = sanitize(artist)
        # Fix: Use primary artist for directory structure
        primary_artist = safe_artist.split(',')[0].strip()
        safe_album = sanitize(album)
        safe_name = f"{safe_artist} - {sanitize(title)}"

        # Directorio de salida (Dinamico si viene de DownloadEngine)
        base_dir = track.get("base_dir", "canciones_auto")
        song_dir = os.path.join(base_dir, primary_artist, safe_album)
        os.makedirs(song_dir, exist_ok=True)
        mp3_path = os.path.join(song_dir, f"{safe_name}.mp3")

        if force_redownload and os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except OSError:
                pass

        # Si ya existe, devolver Ã©xito de inmediato
        if (not force_redownload) and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 10000:
            return mp3_path, track

        # Obtener metadatos extra (Año)
        if classifier:
            metadata = classifier.get_metadata(artist, title)
            track["year"] = metadata.get("year", "2026")
            track["genres"] = metadata.get("genres", ["Sin clasificar"])
        else:
            track["year"] = "2026"

        # Búsquedas más diversas para maximizar éxito
        queries = [
            f'"{artist}" "{title}" official audio',
            f'"{artist}" "{title}" topic',
            f'"{artist}" "{title}" lyrics',
            f'"{artist}" "{title}" audio',
            f'"{artist}" {title}'
        ]

        for query in queries:
            try:
                # Extraer info bÃ¡sica de varios resultados
                search_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    res = ydl.extract_info(f"ytsearch8:{query}", download=False)
                    candidates = res.get('entries', [])

                for entry in candidates:
                    if not entry: continue
                    
                    # Para tener duraciÃ³n fiable hay que obtener info completa (o confiar en flat)
                    # En ytsearch, flat_extract suele dar duration si estÃ¡ disponible
                    if not is_valid_match(entry, title, artist, expected_duration=duration):
                        log.warning("Saltando resultado irrelevante: %s", _safe_console_text(entry.get("title")))
                        continue

                    log.info("Descargando %s para: %s", entry.get("id"), _safe_console_text(title))

                    with yt_dlp.YoutubeDL(get_ydl_opts(os.path.join(song_dir, f"{safe_name}.%(ext)s"))) as ydl: 
                        ydl.download([entry['url']])

                    if os.path.exists(mp3_path):
                        log.info("Descargada: %s", _safe_console_text(safe_name))
                        
                        # Normalizar volumen (ReplayGain) antes de etiquetar
                        normalize_loudness(mp3_path)
                        
                        embed_tags(mp3_path, track)
                        return mp3_path, track
            except Exception as e:
                log.error("Error en busqueda/descarga: %s", e)
                continue

        return None, track
    except Exception as e:
        log.error("Error critico en motor: %s", e)
        return None, track

def embed_tags(path, track):
    try:
        try: audio = ID3(path)
        except: audio = ID3()
        
        # Eliminar tags antiguos para evitar conflictos
        for frame in ["TIT2", "TPE1", "TALB", "TYER", "TDRC", "USLT"]:
            audio.delall(frame)
            
        audio.add(TIT2(encoding=3, text=track.get("title", "")))
        audio.add(TPE1(encoding=3, text=track.get("artist", "")))
        audio.add(TALB(encoding=3, text=track.get("album", "")))
        
        year = track.get("year")
        if year and year != "2026":
            audio.add(TYER(encoding=3, text=year)) # ID3v2.3
            audio.add(TDRC(encoding=3, text=year)) # ID3v2.4
            
        # Intentar letra
        lyrics = get_lyrics(None, track)
        if lyrics:
            audio.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics))
            
        audio.save(path, v2_version=3)
        
        # Guardar archivo .lrc si hay letra sincronizada
        synced = get_synced(track)
        if synced:
            lrc_path = path.replace(".mp3", ".lrc")
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write(synced)
                
    except Exception as e:
        log.error("Error al etiquetar: %s", e)

def get_lyrics(g, track):
    if classifier:
        return classifier.fetch_lyrics(track.get("artist"), track.get("title"))
    return None

def get_synced(track):
    # La misma funcion fetch_lyrics devuelve sincronizada si está disponible
    return None # Por ahora devolvemos None para no duplicar en el .mp3 si queremos .lrc aparte
