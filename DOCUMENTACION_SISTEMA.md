# Documentación del Sistema - Music Downloader B3 (Pro Edition)

## 1. ¿Qué estamos haciendo y cómo?
Estamos manteniendo y mejorando un sistema de descarga y sincronización de música automatizado entre Spotify (PC) y Android (Termux).

### Flujo de trabajo actual:
1.  **Extracción (Exportify)**: Usamos un bot que abre Spotify Web y descarga tus "Liked Songs" a un archivo `playlist.csv`.
2.  **Escaneo Inteligente (Delta)**: Comparamos lo que tienes en el PC y lo que tienes en el móvil mediante SSH. Solo descargamos lo que falta en AMBOS sitios.
3.  **Descarga y Etiquetado**: El motor busca el audio en YouTube (320kbps), le inyecta las carátulas y metadatos de Spotify, y busca la letra sincronizada (.lrc).
4.  **Clasificación Incremental**: A medida que una canción baja, se clasifica por género (vía Last.fm API) y década, y se añade a las listas `.m3u8` al instante.
5.  **Sincronización Turbo SSH**: Usamos comandos de `tar` comprimido a través de un túnel SSH para enviar archivos al móvil masivamente sin que Android limite la velocidad.

---

## 2. ¿Qué intentamos hacer y cómo?
*   **Eficiencia Total**: Eliminar los escaneos completos de la biblioteca que tardaban minutos. Ahora el sistema es "incremental".
*   **Precisión**: Evitar que se bajen versiones en vivo o covers. Se ha implementado un filtro de títulos que compara el nombre de Spotify con el de YouTube con un 80% de coincidencia mínima.
*   **Orden**: Organizar la música en carpetas `Artista/Album/Cancion.mp3`.

---

## 3. ¿Qué fallaba y por qué?

### El error "Motor no disponible":
*   **Causa**: El archivo `musicDownloader3.py` tenía errores de sintaxis (indentación) tras una actualización, lo que impedía que Python lo cargara. 
*   **Estado actual**: Ya está arreglado físicamente, pero la GUI a veces retiene en memoria la versión antigua o falla al encontrar las dependencias (`yt-dlp`, `mutagen`) si no se lanzan desde el entorno correcto. He forzado la recarga del módulo para solucionar esto.

### Las "Listas Basura" (letras sueltas):
*   **Causa**: Un error de lógica trataba los géneros como una cadena de texto en lugar de una lista. Al iterar sobre "Pop", creaba una lista "P", otra "o", otra "p".
*   **Estado actual**: Solucionado. Ahora valida que sean géneros reales y añade el prefijo "Decada" a las listas de años.

### Canciones faltantes ("Decode", "Faint"):
*   **Causa**: Estaban en la base de datos `downloaded.json` pero no en el disco. El programa confiaba en la DB y no en la realidad física.
*   **Estado actual**: Ahora el programa prioriza la existencia del archivo. Si no está en la carpeta, se descarga.

---

## 4. Ideas que añadirían valor al proyecto

1.  **Limpieza Automática de Duplicados**: Un script que detecte si tienes la misma canción con dos nombres ligeramente distintos (ej: "Song - Live" y "Song") y deje solo la mejor.
2.  **Sincronización de Playlists de Spotify**: No solo bajar las "Liked Songs", sino también mantener tus carpetas de playlists de Spotify sincronizadas como carpetas reales en el móvil.
3.  **Normalización de Audio (Loudness)**: Asegurar que todas las canciones suenen al mismo volumen (ReplayGain).
4.  **Interfaz de Ajustes en la GUI**: Poder cambiar la IP del móvil o las credenciales de Last.fm directamente desde la ventana de Ajustes sin tocar archivos `.json`.
5.  **Modo "Escucha Local"**: Una pequeña pestaña en la GUI para reproducir la música descargada directamente desde el PC.
6.  **Detección de Calidad**: Un verificador que analice si un MP3 ya descargado es realmente 320kbps o es una basura de 128kbps, y lo marque para redescargar si es necesario.
