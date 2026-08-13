import http.server
import html as html_lib
import socketserver
import os
import qrcode
import socket
import zipfile
import json
import re
import shutil
import subprocess
import sys
import time
from threading import Thread, Lock
from urllib.parse import urlparse, parse_qs
import urllib.request

class WriteThrough:
    def __init__(self, wfile):
        self.wfile = wfile

    def write(self, data):
        self.wfile.write(data)
        return len(data)

    def flush(self):
        self.wfile.flush()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

_AUDIO_EXTENSIONS = (".mp3", ".lrc", ".m3u8")
_ZIP_JOB_LOCK = Lock()
_ZIP_JOB = {
    "layout": "audio_songs",
    "state": "idle",
    "message": "ZIP no preparado.",
    "progress": 0,
    "total": 0,
    "download_url": None,
    "size": 0,
    "error": None,
}

def _runtime_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _zip_cache_dir():
    path = os.path.join(_runtime_base_dir(), ".tmp", "qr_sync")
    os.makedirs(path, exist_ok=True)
    return path

def _layout_from_query(query):
    params = parse_qs(query)
    return "raw" if params.get("layout", ["audio_songs"])[0] == "raw" else "audio_songs"

def _zip_paths(layout):
    suffix = "raw" if layout == "raw" else "audio_songs"
    base = _zip_cache_dir()
    return (
        os.path.join(base, f"music_library_{suffix}.zip"),
        os.path.join(base, f"music_library_{suffix}.json"),
    )

def _library_entries(root):
    entries = []
    if not os.path.exists(root):
        return entries
    for r, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(_AUDIO_EXTENSIONS):
                abs_path = os.path.join(r, f)
                rel = os.path.relpath(abs_path, root).replace("\\", "/")
                try:
                    stat = os.stat(abs_path)
                except OSError:
                    continue
                entries.append({
                    "abs": abs_path,
                    "rel": rel,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                })
    entries.sort(key=lambda item: item["rel"].lower())
    return entries

def _zip_entry_name(rel, layout):
    if layout == "raw":
        return rel
    return f"audio/songs/{rel}"

def _zip_signature(entries, layout):
    return {
        "layout": layout,
        "files": [
            {"path": item["rel"], "size": item["size"], "mtime_ns": item["mtime_ns"]}
            for item in entries
        ],
    }

def _read_zip_meta(meta_path):
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

def _is_zip_current(root, layout):
    zip_path, meta_path = _zip_paths(layout)
    if not os.path.exists(zip_path) or os.path.getsize(zip_path) <= 0:
        return False, 0
    entries = _library_entries(root)
    current = _zip_signature(entries, layout)
    stored = _read_zip_meta(meta_path)
    if stored != current:
        return False, 0
    return True, os.path.getsize(zip_path)

def _set_zip_job(**updates):
    with _ZIP_JOB_LOCK:
        _ZIP_JOB.update(updates)
        _ZIP_JOB["updated_at"] = time.time()

def _get_zip_job():
    with _ZIP_JOB_LOCK:
        return dict(_ZIP_JOB)

def _build_cached_zip(root, layout, cb=None):
    entries = _library_entries(root)
    zip_path, meta_path = _zip_paths(layout)
    part_path = zip_path + ".part"
    total = len(entries)
    _set_zip_job(
        layout=layout,
        state="building",
        message=f"Preparando ZIP: 0/{total}",
        progress=0,
        total=total,
        download_url=None,
        size=0,
        error=None,
    )
    if cb:
        cb(f"Preparando ZIP QR con {total} archivos...")

    try:
        with zipfile.ZipFile(part_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            for idx, item in enumerate(entries, start=1):
                zf.write(item["abs"], _zip_entry_name(item["rel"], layout))
                if idx == total or idx % 25 == 0:
                    _set_zip_job(
                        message=f"Preparando ZIP: {idx}/{total}",
                        progress=idx,
                        total=total,
                    )
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(_zip_signature(entries, layout), f, ensure_ascii=False, indent=2)
        os.replace(part_path, zip_path)
        size = os.path.getsize(zip_path)
        _set_zip_job(
            state="ready",
            message="ZIP preparado. Ya puedes iniciar la descarga.",
            progress=total,
            total=total,
            download_url=f"/download_zip?layout={layout}",
            size=size,
            error=None,
        )
        if cb:
            cb(f"ZIP QR preparado: {size / (1024 * 1024):.1f} MB")
    except Exception as exc:
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except OSError:
            pass
        _set_zip_job(
            state="error",
            message=f"No se pudo preparar el ZIP: {exc}",
            error=str(exc),
        )
        if cb:
            cb(f"Error preparando ZIP QR: {exc}")

def _start_zip_job(root, layout, cb=None):
    current, size = _is_zip_current(root, layout)
    if current:
        _set_zip_job(
            layout=layout,
            state="ready",
            message="ZIP preparado. Ya puedes iniciar la descarga.",
            progress=1,
            total=1,
            download_url=f"/download_zip?layout={layout}",
            size=size,
            error=None,
        )
        return

    with _ZIP_JOB_LOCK:
        if _ZIP_JOB.get("state") == "building" and _ZIP_JOB.get("layout") == layout:
            return

    Thread(target=_build_cached_zip, args=(root, layout, cb), daemon=True).start()

class SyncHandler(http.server.BaseHTTPRequestHandler):
    progress_callback = None

    def log_message(self, format, *args):
        msg = format % args
        cb = type(self).progress_callback
        if cb:
            try:
                cb(f"Log: {msg}")
            except Exception:
                pass

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        try:
            if path == "/healthz":
                self.serve_health()
            elif path == "/get_library":
                self.send_library_json()
            elif path == "/download_file":
                self.serve_file(url.query)
            elif path == "/download_zip":
                self.serve_zip(url.query)
            elif path == "/prepare_zip":
                self.prepare_zip(url.query)
            elif path == "/zip_status":
                self.send_zip_status(url.query)
            elif path == "/manifest.json":
                self.serve_manifest()
            else:
                self.serve_ui()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self.log_message("Unhandled error: %s", exc)
            try:
                self.send_error(500, "Internal server error")
            except (BrokenPipeError, ConnectionResetError):
                pass

    def serve_health(self):
        data = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_zip(self, query=""):
        from config_manager import config
        root = config.get_music_dir()
        layout = _layout_from_query(query)
        current, _ = _is_zip_current(root, layout)
        if not current:
            _start_zip_job(root, layout, type(self).progress_callback)
            data = (
                b"ZIP preparandose en el PC. Vuelve a intentarlo cuando el estado indique que esta listo."
            )
            self.send_response(202)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        zip_path, _ = _zip_paths(layout)
        filename = "music_library_raw.zip" if layout == "raw" else "music_library_audio_songs.zip"
        self.serve_static_file(zip_path, "application/zip", filename)

    def prepare_zip(self, query=""):
        from config_manager import config
        layout = _layout_from_query(query)
        _start_zip_job(config.get_music_dir(), layout, type(self).progress_callback)
        self.send_zip_status(query)

    def send_zip_status(self, query=""):
        from config_manager import config
        layout = _layout_from_query(query)
        current, size = _is_zip_current(config.get_music_dir(), layout)
        job = _get_zip_job()
        if current and job.get("state") != "building":
            _set_zip_job(
                layout=layout,
                state="ready",
                message="ZIP preparado. Ya puedes iniciar la descarga.",
                progress=1,
                total=1,
                download_url=f"/download_zip?layout={layout}",
                size=size,
                error=None,
            )
        elif (
            not current
            and job.get("state") != "building"
            and job.get("layout") == layout
        ):
            _set_zip_job(
                layout=layout,
                state="idle",
                message="ZIP no preparado o biblioteca cambiada.",
                progress=0,
                total=0,
                download_url=None,
                size=0,
                error=None,
            )
        data = json.dumps(_get_zip_job()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_static_file(self, abs_path, content_type, download_name=None):
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            self.send_error(404)
            return

        size = os.path.getsize(abs_path)
        start = 0
        end = size - 1
        status = 200
        range_header = self.headers.get("Range")

        if range_header:
            match = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
            if not match:
                self.send_error(416)
                return
            start_text, end_text = match.groups()
            if start_text:
                start = int(start_text)
                end = int(end_text) if end_text else end
            elif end_text:
                suffix_len = int(end_text)
                start = max(size - suffix_len, 0)
            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            end = min(end, size - 1)
            status = 206

        length = end - start + 1 if size else 0
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "private, no-cache")
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        with open(abs_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def serve_manifest(self):
        manifest = {
            "name": "Music B3 Sync",
            "short_name": "SyncB3",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#121212",
            "theme_color": "#1DB954",
            "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/3844/3844724.png", "sizes": "512x512", "type": "image/png"}]
        }
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(manifest).encode())

    def serve_ui(self):
        from config_manager import config
        acc_data = config.get_active_account()
        acc = html_lib.escape(str(acc_data["name"]))
        pl = html_lib.escape(str(config.get_active_playlist()))
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Music Sync Pro - {pl}</title>
  <link rel="manifest" href="/manifest.json">
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0d1117;
      --panel: #161b22;
      --line: #30363d;
      --green: #1db954;
      --green-hover: #1ed760;
      --blue: #2f80ed;
      --text: #f0f6fc;
      --muted: #8b949e;
      --card-bg: rgba(255,255,255,0.04);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: radial-gradient(circle at top right, rgba(29, 185, 84, 0.15), transparent 40%), var(--bg);
      color: var(--text);
      padding: 16px;
    }}
    main {{
      max-width: 680px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(29,185,84,0.18), rgba(47,128,237,0.12));
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      text-align: center;
    }}
    .hero h1 {{ font-size: 26px; font-weight: 800; margin-bottom: 6px; }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      background: rgba(29, 185, 84, 0.2);
      color: var(--green-hover);
      font-size: 13px;
      font-weight: bold;
      margin-top: 6px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
    }}
    .btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      border: 0;
      border-radius: 14px;
      padding: 15px;
      margin: 8px 0;
      color: #000;
      background: var(--green);
      font-size: 16px;
      font-weight: bold;
      text-align: center;
      text-decoration: none;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .btn:hover {{ background: var(--green-hover); }}
    .btn.secondary {{ background: var(--blue); color: #fff; }}
    .btn.ghost {{ background: transparent; color: var(--text); border: 1px solid var(--line); }}
    .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .tip-box {{
      background: rgba(255, 204, 0, 0.08);
      border: 1px dashed rgba(255, 204, 0, 0.35);
      border-radius: 12px;
      padding: 12px;
      font-size: 13px;
      color: #e6b800;
      line-height: 1.4;
    }}
    .search-box {{
      width: 100%;
      padding: 12px 16px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #0d1117;
      color: var(--text);
      font-size: 15px;
      margin: 10px 0;
    }}
    .song-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 380px;
      overflow-y: auto;
      margin-top: 10px;
      padding-right: 4px;
    }}
    .song-item {{
      background: var(--card-bg);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .song-info {{
      flex: 1;
      min-width: 0;
    }}
    .song-title {{
      font-size: 14px;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .song-sub {{
      font-size: 12px;
      color: var(--muted);
    }}
    .song-actions {{
      display: flex;
      gap: 6px;
      align-items: center;
    }}
    .btn-icon {{
      background: #21262d;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 13px;
      cursor: pointer;
      text-decoration: none;
    }}
    .btn-icon:hover {{ background: #30363d; }}
    audio {{ width: 100%; height: 32px; margin-top: 8px; }}
    progress {{ width: 100%; height: 10px; border-radius: 5px; accent-color: var(--green); }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>🎵 Music Sync Pro</h1>
      <p style="color: var(--muted); font-size: 14px;">Perfil: <strong>{acc}</strong> | Playlist: <strong>{pl}</strong></p>
      <span class="badge" id="library-count">Cargando biblioteca...</span>
    </section>

    <!-- DESCARGA DIRECTA ZIP -->
    <section class="card">
      <h3 style="margin-bottom: 8px;">📦 Descarga Rápida</h3>
      <a class="btn" id="direct-zip-btn" href="/download_zip?layout=audio_songs" download>
        📥 Descargar Toda la Música (.ZIP)
      </a>
      <div class="tip-box">
        💡 <strong>Recomendación:</strong> En Android puedes usar <b>1DM</b> o <b>ADM</b> para descargas ultrarrápidas y reanudables de este enlace.
      </div>
    </section>

    <!-- EXPLORADOR DE CANCIONES Y REPRODUCTOR -->
    <section class="card">
      <h3>🔍 Explorador de Canciones</h3>
      <input type="text" id="search-input" class="search-box" placeholder="Buscar canción, artista o álbum...">
      <div id="player-container" style="display:none; margin-bottom: 10px;">
        <p id="now-playing" style="font-size: 13px; color: var(--green); font-weight: bold;"></p>
        <audio id="audio-player" controls></audio>
      </div>
      <div class="song-list" id="songs-container">
        <p style="color: var(--muted); text-align: center; padding: 20px;">Cargando lista de canciones...</p>
      </div>
    </section>

    <!-- OPCIONES AVANZADAS -->
    <section class="card">
      <details>
        <summary style="cursor: pointer; font-weight: bold; color: var(--muted);">⚙️ Opciones Avanzadas (ZIP en Caché / Carpetas)</summary>
        <div style="margin-top: 15px;">
          <button class="btn secondary" id="prepare-zip-btn" style="padding: 10px;">Preparar ZIP en PC</button>
          <a class="btn secondary" id="zip-download-link" href="/download_zip?layout=audio_songs" hidden style="padding: 10px;">Descargar ZIP Listo</a>
          <progress id="zip-progress" value="0" max="1" hidden></progress>
          <p id="zip-status" style="font-size: 13px; color: var(--muted); margin: 6px 0;"></p>
          <button class="btn ghost" id="sync-folder-btn" style="padding: 10px; font-size: 14px;">Sincronizar a Carpeta (Chrome PC)</button>
        </div>
      </details>
    </section>
  </main>

  <script>
    let allSongs = [];
    const songsContainer = document.getElementById("songs-container");
    const searchInput = document.getElementById("search-input");
    const countBadge = document.getElementById("library-count");
    const playerContainer = document.getElementById("player-container");
    const audioPlayer = document.getElementById("audio-player");
    const nowPlaying = document.getElementById("now-playing");

    async function loadLibrary() {{
      try {{
        const res = await fetch("/get_library", {{ cache: "no-store" }});
        allSongs = await res.json();
        countBadge.textContent = `${{allSongs.length}} canciones disponibles`;
        renderSongs(allSongs);
      }} catch(e) {{
        countBadge.textContent = "Error al leer biblioteca";
        songsContainer.innerHTML = `<p style="color:#ff6b6b;text-align:center;">No se pudo cargar la lista.</p>`;
      }}
    }}

    function renderSongs(songs) {{
      if (!songs || songs.length === 0) {{
        songsContainer.innerHTML = `<p style="color:var(--muted);text-align:center;padding:20px;">No se encontraron canciones.</p>`;
        return;
      }}
      songsContainer.innerHTML = songs.map(s => {{
        const parts = s.path.split('/');
        const filename = parts[parts.length - 1];
        const isMp3 = filename.toLowerCase().endsWith('.mp3');
        if (!isMp3) return '';
        const cleanName = filename.replace(/\\.[^/.]+$/, "");
        return `
          <div class="song-item">
            <div class="song-info">
              <div class="song-title">${{cleanName}}</div>
              <div class="song-sub">${{parts.slice(0, -1).join(' / ') || 'General'}}</div>
            </div>
            <div class="song-actions">
              <button class="btn-icon" onclick="playSong('${{encodeURIComponent(s.path)}}', '${{cleanName.replace(/'/g, "\\\\'")}}')">▶</button>
              <a class="btn-icon" href="/download_file?path=${{encodeURIComponent(s.path)}}" download="${{filename}}">⬇</a>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function playSong(path, name) {{
      playerContainer.style.display = 'block';
      nowPlaying.textContent = "Reproduciendo: " + name;
      audioPlayer.src = "/download_file?path=" + path;
      audioPlayer.play();
    }}

    searchInput.addEventListener("input", (e) => {{
      const q = e.target.value.toLowerCase();
      const filtered = allSongs.filter(s => s.path.toLowerCase().includes(q));
      renderSongs(filtered);
    }});

    // ZIP Preparado
    const prepareZipBtn = document.getElementById("prepare-zip-btn");
    const zipDownloadLink = document.getElementById("zip-download-link");
    const zipProgress = document.getElementById("zip-progress");
    const zipStatus = document.getElementById("zip-status");

    async function checkZip() {{
      try {{
        const info = await fetch("/zip_status?layout=audio_songs", {{ cache: "no-store" }}).then(r => r.json());
        if (info.state === "ready") {{
          zipDownloadLink.hidden = false;
          prepareZipBtn.style.display = "none";
          zipStatus.textContent = `ZIP listo para descargar (${{(info.size / 1024 / 1024).toFixed(1)}} MB)`;
        }} else if (info.state === "building") {{
          zipProgress.hidden = false;
          zipProgress.max = info.total || 1;
          zipProgress.value = info.progress || 0;
          zipStatus.textContent = info.message;
          setTimeout(checkZip, 1500);
        }}
      }} catch(e) {{}}
    }}

    prepareZipBtn.addEventListener("click", async () => {{
      prepareZipBtn.disabled = true;
      zipStatus.textContent = "Preparando ZIP en PC...";
      await fetch("/prepare_zip?layout=audio_songs");
      setTimeout(checkZip, 1000);
    }});

    loadLibrary();
    checkZip();
  </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_library_json(self):
        from config_manager import config
        import playlist_generator
        playlist_generator.generate_playlists()
        root = config.get_music_dir()
        library = []
        if os.path.exists(root):
            for r, d, files in os.walk(root):
                for f in files:
                    if f.lower().endswith((".mp3", ".lrc", ".m3u8")):
                        rel = os.path.relpath(os.path.join(r, f), root).replace("\\", "/")
                        library.append({"path": rel})
        data = json.dumps(library).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def serve_file(self, query):
        from config_manager import config
        params = parse_qs(query)
        rel_path = params.get("path", [""])[0]
        if not rel_path:
            self.send_error(400)
            return

        root = os.path.abspath(config.get_music_dir())
        abs_path = os.path.abspath(os.path.join(root, rel_path))
        if abs_path != root and not abs_path.startswith(root + os.sep):
            self.send_error(403)
            return

        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            self.serve_static_file(abs_path, "application/octet-stream")
        else:
            self.send_error(404)

_TUNNEL_URL_PATTERN = re.compile(r'https://[a-z0-9\-]+\.lhr\.life')
_CLOUDFLARE_URL_PATTERN = re.compile(r'https://[a-z0-9\-]+\.trycloudflare\.com')
_ANSI_PATTERN = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

class QRServer:
    def __init__(self, port=8000, progress_callback=None):
        self.port = port
        self.local_ip = self._get_local_ip()
        self.public_url = None
        self.progress_callback = progress_callback
        self.server = None
        self.tunnel_proc = None

    def _get_local_ip(self):
        # 1. Intentar resolver por conexión de salida
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        except Exception:
            pass

        # 2. Enumerar IPs del host buscando 192.168.x.x o 10.x.x.x
        try:
            hostname = socket.gethostname()
            candidates = socket.gethostbyname_ex(hostname)[2]
            for ip in candidates:
                if ip.startswith("192.168.") or ip.startswith("10."):
                    return ip
            for ip in candidates:
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    return ip
        except Exception:
            pass
        return '127.0.0.1'

    def _cb(self, msg: str):
        if self.progress_callback:
            try:
                self.progress_callback(msg)
            except Exception:
                pass

    def _strip_ansi(self, text: str) -> str:
        return _ANSI_PATTERN.sub("", text).strip()

    def _tools_dir(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, ".tmp", "tools")
        os.makedirs(path, exist_ok=True)
        return path

    def _local_cloudflared_path(self):
        return os.path.join(self._tools_dir(), "cloudflared.exe")

    def _ensure_cloudflared(self):
        path = shutil.which("cloudflared")
        if path:
            return path

        local_path = self._local_cloudflared_path()
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        self._cb("Descargando Cloudflare Quick Tunnel portable...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            with urllib.request.urlopen(url, timeout=25) as response, open(local_path, "wb") as out:
                shutil.copyfileobj(response, out)
            return local_path
        except Exception as exc:
            self._cb(f"No se pudo preparar cloudflared: {exc}")
            return None

    def _wait_for_url(self, pattern, timeout: int):
        captured_url = []

        def _reader():
            try:
                for line in iter(self.tunnel_proc.stdout.readline, ""):
                    clean = self._strip_ansi(line)
                    if clean:
                        self._cb(f"[tunnel] {clean}")
                    m = pattern.search(line)
                    if m:
                        captured_url.append(m.group(0))
            except Exception:
                pass

        Thread(target=_reader, daemon=True).start()
        deadline = time.time() + timeout
        while not captured_url and time.time() < deadline:
            if self.tunnel_proc.poll() is not None:
                return None
            time.sleep(0.3)
        return captured_url[0] if captured_url else None

    def _public_health_ok(self, url: str, timeout: int = 10):
        try:
            with urllib.request.urlopen(f"{url.rstrip('/')}/healthz", timeout=timeout) as response:
                return response.status == 200 and response.read(8) == b"ok"
        except Exception as exc:
            self._cb(f"Healthcheck publico fallido para {url}: {exc}")
            return False

    def _wait_for_public_health(self, url: str, timeout: int = 15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._public_health_ok(url, timeout=4):
                return True
            time.sleep(1)
        return False

    def _stop_tunnel_process(self):
        if self.tunnel_proc and self.tunnel_proc.poll() is None:
            self.tunnel_proc.terminate()
            try:
                self.tunnel_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.tunnel_proc.kill()
        self.tunnel_proc = None

    def _start_cloudflare_tunnel(self, timeout: int):
        cloudflared = self._ensure_cloudflared()
        if not cloudflared:
            return None

        self._cb("Iniciando tunel publico Cloudflare...")
        cmd = [
            cloudflared,
            "tunnel",
            "--url", f"http://127.0.0.1:{self.port}",
            "--no-autoupdate",
        ]
        try:
            self.tunnel_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            self._cb(f"No se pudo iniciar cloudflared: {exc}")
            return None
        return self._wait_for_url(_CLOUDFLARE_URL_PATTERN, timeout)

    def start_tunnel(self, timeout: int = 20):
        if self.public_url and self._public_health_ok(self.public_url, timeout=4):
            return

        self.public_url = None
        self._stop_tunnel_process()

        cloudflare_url = self._start_cloudflare_tunnel(timeout=timeout)
        if cloudflare_url and self._wait_for_public_health(cloudflare_url):
            self.public_url = cloudflare_url
            self._cb(f"Tunel activo: {self.public_url}")
            return
        self._stop_tunnel_process()

        self._cb("Iniciando tunel publico alternativo (localhost.run)...")
        cmd = [
            "ssh", "-T", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
            "-R", f"80:127.0.0.1:{self.port}", "ssh.localhost.run"
        ]
        try:
            self.tunnel_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self._cb("'ssh' no encontrado en PATH. Instala OpenSSH o deja que Cloudflare se descargue.")
            return

        public_url = self._wait_for_url(_TUNNEL_URL_PATTERN, timeout)
        if public_url and self._wait_for_public_health(public_url, timeout=10):
            self.public_url = public_url
            self._cb(f"Tunel activo: {self.public_url}")
        else:
            self._stop_tunnel_process()
            self._cb("No se pudo abrir un tunel publico sano. Revisa conexion saliente a internet.")

    def generate_qr(self, require_public=True, override_url=None):
        """Devuelve (imagen_qr, url). Llama a start_tunnel() si aun no hay tunel activo."""
        if override_url:
            self._cb(f"Generando QR para URL manual: {override_url}")
            return qrcode.make(override_url), override_url
            
        if not require_public:
            url = f"http://{self.local_ip}:{self.port}"
            self._cb(f"Usando URL local para el QR: {url}")
            return qrcode.make(url), url
        if not self.public_url:
            self.start_tunnel()
        if require_public and not self.public_url:
            raise RuntimeError("No se pudo crear una URL publica valida para el QR.")
        url = self.public_url or f"http://{self.local_ip}:{self.port}"
        if not self.public_url:
            self._cb(f"Usando URL local para el QR: {url}")
        return qrcode.make(url), url

    def start(self):
        if self.server:
            return
        SyncHandler.progress_callback = self.progress_callback
        self.server = ThreadedHTTPServer(("", self.port), SyncHandler)
        Thread(target=self.server.serve_forever, daemon=True).start()
        self._cb(f"Servidor HTTP escuchando en puerto {self.port}")

    def start_all(self):
        self.start()
        self.start_tunnel()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self._stop_tunnel_process()
        self.public_url = None
