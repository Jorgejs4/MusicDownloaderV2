#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exportador de cookies de YouTube para yt-dlp
Uso: python export_cookies.py
"""

import os
import sys
import subprocess

def export_cookies_from_browser():
    """Intenta exportar cookies del navegador a un archivo"""
    
    output_file = "cookies.txt"
    
    # Intentar con Chrome primero (requiere que esté cerrado)
    browsers = ["chrome", "edge", "brave", "firefox"]
    
    for browser in browsers:
        print(f"Intentando exportar cookies de {browser}...")
        try:
            # Usar yt-dlp para exportar cookies
            result = subprocess.run(
                [
                    sys.executable, "-m", "yt_dlp",
                    "--cookies-from-browser", browser,
                    "--cookies", output_file,
                    "--print", "Cookies exportadas correctamente",
                    "https://www.youtube.com"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
                print(f"✅ Cookies exportadas exitosamente de {browser}")
                print(f"📁 Archivo: {os.path.abspath(output_file)}")
                return True
                
        except Exception as e:
            print(f"❌ Error con {browser}: {e}")
            continue
    
    print("\n⚠️ No se pudieron exportar cookies automáticamente.")
    print("\nInstrucciones manuales:")
    print("1. Instala la extensión 'Get cookies.txt LOCALLY' en Chrome")
    print("2. Ve a YouTube y asegúrate de estar logueado")
    print("3. Haz clic en la extensión → Export → Guarda como cookies.txt")
    print("4. Coloca el archivo en esta carpeta")
    return False

if __name__ == "__main__":
    export_cookies_from_browser()