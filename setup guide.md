# Setup Guide

## 1. Copia la configuracion

Si ya tienes `.env` funcional en `music Donwlader v2`, puedes reutilizarlo casi tal cual.

Variables minimas:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`
- `SSH_IP`
- `SSH_PORT`
- `SSH_USER`

Opcionales:

- `GENIUS_TOKEN`
- `ZROK_ID`
- `DOWNLOAD_BACKENDS`
- `MAX_WORKERS`

Base recomendada:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
GENIUS_TOKEN=
OUTPUT_DIR=canciones_auto
DOWNLOAD_BACKENDS=youtube,soundcloud
ENABLE_V1_STRICT_FIRST=1
SSH_IP=192.168.1.244
SSH_PORT=8022
SSH_USER=u0_a461
MAX_WORKERS=3
YTDLP_ENABLE_BROWSER_COOKIES=0
DIAGNOSTIC_MODE=0
MAX_SONGS_PER_RUN=0
STOP_ON_FIRST_FAILURE=0
```

## 2. Python y dependencias

El proyecto intenta usar `.venv\Scripts\python.exe` desde `Lanzar_Sincronizacion.bat`.

Si el entorno virtual no existe o le faltan paquetes, instala como minimo:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install yt-dlp mutagen lyricsgenius requests playwright
.\.venv\Scripts\playwright.exe install
```

Si ya vienes de `v2`, probablemente esto ya lo tengas.

## 3. Cookies de YouTube

Para que YouTube vaya fino, genera o refresca `cookies.txt`:

```powershell
.\.venv\Scripts\python.exe .\youtube_cookie_setup.py
```

Esto genera:

- `cookies.txt`
- `youtube_auth.json`

`b3` usa esas cookies primero. Si fallan, intenta sin cookies.

Por defecto ya no intenta leer cookies del navegador con `yt-dlp`, porque en muchos equipos eso dispara errores de `DPAPI` o perfiles inexistentes. Solo actívalo si realmente lo necesitas:

```env
YTDLP_ENABLE_BROWSER_COOKIES=1
YT_DLP_COOKIE_BROWSERS=chrome,edge
```

## 4. Termux / telefono

En el movil necesitas SSH funcionando en Termux.

Comandos tipicos:

```bash
pkg install openssh termux-api
sshd
termux-wake-lock
```

Y concede permisos de almacenamiento:

```bash
termux-setup-storage
```

## 5. Primera prueba recomendada

Haz una prueba corta:

```powershell
$env:DIAGNOSTIC_MODE="1"
$env:MAX_SONGS_PER_RUN="1"
$env:STOP_ON_FIRST_FAILURE="1"
.\Lanzar_Sincronizacion.bat
```

Esto descarga solo una cancion y se detiene en el primer fallo, que es la forma mas rapida de validar:

- Exportify
- descarga YouTube
- fallback
- sincronizacion al telefono

## 6. Como decide B3 si una cancion es correcta

Antes de descargar, `b3` puntua candidatos por:

- query por `ISRC` si existe
- similitud del titulo
- presencia del artista en titulo/canal/uploader
- diferencia de duracion respecto a Spotify
- penalizacion por `remix`, `cover`, `karaoke`, `instrumental`, `nightcore`, etc.

Regla operativa:

- primero prueba un modo `V1 estricto` que replica la ruta clasica del proyecto original
- YouTube es preferente
- SoundCloud solo entra si YouTube no entrega un candidato con score suficiente
- si ambos fallan, entra un fallback legado de YouTube

Si quieres saltarte esa fase inicial y usar solo el motor nuevo:

```env
ENABLE_V1_STRICT_FIRST=0
```

## 7. Si algo falla

- Si falla YouTube: regenera `cookies.txt`
- Si no conecta con el movil: revisa `SSH_IP`, `SSH_PORT`, `SSH_USER`
- Si Playwright no abre Spotify/Exportify: reinstala navegadores de Playwright
- Si quieres reducir errores durante pruebas: deja `MAX_WORKERS=1`

## 8. Interpretacion del log de YouTube

Si ves esto:

- `Skipping client "android" since it does not support cookies`
- `android/ios client https formats require a GVS PO Token`

significa:

- con cookies, esos clientes no son validos
- sin cookies, esos clientes pueden exigir un `PO Token`

`b3` ya prioriza perfiles mas compatibles (`web_music`, `web`, `mweb`, `tv`) y deja `android/ios` como ultimo recurso.
