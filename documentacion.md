# Documentación del Proyecto: Music Downloader (v4.0 / Titanium v12.0)

Este documento detalla la arquitectura, el flujo de trabajo y las especificaciones técnicas del ecosistema de descarga y sincronización de música.

## 1. Objetivo del Programa
El objetivo principal es automatizar el proceso de obtención de música de alta calidad (320kbps) a partir de las listas de reproducción de Spotify ("Liked Songs"), integrando metadatos completos (ID3v2.3), carátulas, letras (normales y sincronizadas) y manteniendo una sincronización bidireccional entre un PC (Windows) y un dispositivo móvil (Android/Termux).

---

## 2. Arquitectura y Componentes
El proyecto se divide en cuatro capas principales:
1.  **Extracción de Datos**: Obtención de la lista de canciones desde Spotify.
2.  **Orquestación**: Coordinación de procesos entre PC y Móvil.
3.  **Motor de Descarga**: Búsqueda, descarga y procesamiento de archivos MP3.
4.  **Gestión de Biblioteca**: Control de duplicados, errores y limpieza (Mirror Sync).

### Archivos Clave:
- `auto_sync.py`: El "cerebro" que coordina la ejecución, el envío de archivos vía Wi-Fi (SSH/SCP) y el disparo de procesos en Termux.
- `music_csv_auto.py`: El procesador de colas. Gestiona el CSV, la base de datos de descargados y el multi-threading.
- `musicDownloader3.py`: El motor técnico. Utiliza `yt-dlp` para audio y `mutagen` para etiquetado.
- `exportify_bot.py`: Automatización con Playwright para descargar el CSV de Spotify sin usar la API oficial (evitando restricciones de desarrollador).
- `downloaded.json`: Base de datos de persistencia para evitar descargas duplicadas.
- `failed_songs.json`: Registro de errores para reintentos inteligentes.

---

## 3. Flujo del Código

### Paso 1: Extracción (Exportify)
1. `auto_sync.py` lanza `exportify_bot.py`.
2. El bot abre un navegador (Chromium) con la sesión de Spotify del usuario.
3. Localiza la fila de "Liked Songs" y descarga el archivo `playlist.csv`.

### Paso 2: Sincronización PC -> Móvil (Opcional Wi-Fi)
1. Si se detecta conexión SSH con el móvil:
   - Se envían los scripts actualizados (`music_csv_auto.py`, `musicDownloader3.py`) y el `.env`.
   - Se envía el `playlist.csv` actualizado.
   - Se ordena a Termux iniciar la descarga localmente para ahorrar transferencia de archivos grandes.

### Paso 3: Procesamiento de la Cola (Titanium Engine)
1. `music_csv_auto.py` lee el CSV.
2. **Mirror Sync**: Compara lo que hay en la carpeta de música con el CSV. Si una canción ya no está en el CSV, la mueve a `Papelera_Spotify`.
3. Filtra canciones que ya están en `downloaded.json`.
4. Lanza un `ThreadPoolExecutor` (máximo 8 hilos) para procesar descargas en paralelo.

### Paso 4: Descarga y Enriquecimiento
Para cada canción:
1. **Búsqueda**: Intenta localizar el audio en YouTube usando ISRC (máxima precisión) o `Artista - Título`.
2. **Descarga**: Obtiene el audio en la mejor calidad disponible y lo convierte a MP3 (320kbps).
3. **Metadatos**: 
   - Incrusta carátula (Thumbnail de YT).
   - Busca letras en **Genius** (normales) y **LRCLib** (sincronizadas `.lrc`).
   - Escribe etiquetas ID3v2.3 (compatibles con la mayoría de reproductores Android).
4. **Finalización**: Registra el ID en `downloaded.json`.

---

## 4. Funciones Implementadas

### En `music_csv_auto.py`:
- `mirror_sync(csv_songs, installed_map)`: Mantiene la biblioteca limpia eliminando lo que el usuario quitó de Spotify.
- `process_track_thread()`: Maneja el ciclo de vida de una descarga individual dentro de un hilo.
- `get_progress_bar()`: Visualización estética del progreso en la terminal.

### En `musicDownloader3.py`:
- `download_mp3(track)`: Lógica compleja de búsqueda con fallbacks (cookies de navegador, búsqueda por ISRC, validación de duración).
- `embed_tags(path, track, lyrics, synced)`: Inyección de metadatos y creación de archivos `.lrc`.
- `get_synced(track)`: Integración con la API de LRCLib para letras sincronizadas.
- `scan_media(path)`: Notifica al sistema Android (MediaScanner) para que la música aparezca instantáneamente en reproductores como Retro Music.

---

## 5. Configuraciones y Pasos

### Requisitos:
- **PC**: Python 3.10+, FFmpeg instalado en el PATH, Google Chrome/Edge (para cookies).
- **Móvil**: Termux instalado, `sshd` configurado, Python3 y `yt-dlp`.

### Configuración del `.env`:
```env
GENIUS_TOKEN=tu_token_de_genius
SSH_USER=u0_aXXX
SSH_IP=192.168.1.XXX
SSH_PORT=8022
```

### Pasos para ejecución:
1. Ejecutar `Lanzar_Sincronizacion.bat` o `python auto_sync.py`.
2. El sistema descargará el CSV automáticamente.
3. Si el móvil está en la misma red y con `sshd` activo, se sincronizará solo.
4. Las canciones aparecerán en `canciones_auto/` (PC) y `/sdcard/Music/music downloader movil/` (Móvil).

---

## 6. Problemas, Fallos y Cosas a Mejorar

### Fallos/Problemas Actuales:
1. **Bloqueos de YouTube**: YT detecta descargas masivas. Se ha mitigado usando cookies de navegadores locales (`chrome`, `edge`), pero sigue siendo un punto de falla.
2. **Precisión de Búsqueda**: A veces descarga versiones en vivo o remixes si el ISRC no está disponible en el CSV de Exportify.
3. **Dependencia de Exportify**: Si el sitio web de Exportify cambia su diseño, `exportify_bot.py` dejará de funcionar hasta que se actualicen los selectores de Playwright.

### Mejoras Posibles:
- [ ] **Interfaz Gráfica**: Crear una pequeña GUI para monitorear las descargas sin usar la consola.
- [ ] **Soporte para Álbumes/Playlists Específicas**: Actualmente está muy centrado en "Liked Songs".
- [ ] **Validación de Audio**: Implementar una comprobación de pico de volumen o silencio al inicio/final.
- [ ] **Dockerización**: Facilitar la instalación de dependencias (FFmpeg, Python, etc.) mediante un contenedor.
- [ ] **Sistema de Reintentos**: Mejorar el uso de `failed_songs.json` para que reintente automáticamente con diferentes queries de búsqueda tras X tiempo.

### Cosas a mejorar en el código:
- Centralizar más la configuración en un solo archivo JSON/YAML en lugar de mezclar `.env` y variables globales.
- Mejorar el manejo de excepciones en `mirror_sync` para evitar movimientos accidentales a la papelera en caso de error de lectura del disco.
