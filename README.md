# Music Downloader B3

`music downloader b3` mezcla:

- sincronizacion y flujo PC -> movil de `music Donwlader v2`
- descarga prioritaria desde YouTube inspirada en `musicdownloader`
- fallback a SoundCloud solo si YouTube no da una coincidencia fiable

## Objetivo

Evitar los falsos positivos de SoundCloud y mantener la sincronizacion buena de `v2`.

## Cambios clave

- YouTube va primero por defecto.
- Cada candidato se puntua por:
  - similitud de titulo
  - presencia del artista
  - diferencia de duracion
  - penalizacion por `remix`, `cover`, `karaoke`, etc.
- SoundCloud queda como fallback, con umbral mas estricto.
- Si todo falla, hay un ultimo fallback legado de YouTube.

## Archivos importantes

- `musicDownloader3.py`: motor de descarga B3
- `music_csv_auto.py`: lectura de `playlist.csv` y cola local
- `auto_sync.py`: sincronizacion turbo con el telefono
- `youtube_cookie_setup.py`: genera `cookies.txt` para mejorar YouTube
- `setup guide.md`: guia de configuracion

## Uso rapido

```powershell
.\Lanzar_Sincronizacion.bat
```

Modo diagnostico:

```powershell
$env:DIAGNOSTIC_MODE="1"
$env:MAX_SONGS_PER_RUN="1"
$env:STOP_ON_FIRST_FAILURE="1"
.\Lanzar_Sincronizacion.bat
```
