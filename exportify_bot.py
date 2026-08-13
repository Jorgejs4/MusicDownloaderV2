import os
import time
import re
import sys
from playwright.sync_api import sync_playwright

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

def run_exportify_bot(target_playlist="Liked", user_data_dir=None, output_path=None):
    if not user_data_dir:
        user_data_dir = os.path.join(BASE_DIR, "spotify_session")
    if not output_path:
        output_path = os.path.join(BASE_DIR, "playlist.csv")

    with sync_playwright() as p:
        browser_exes = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        
        executable_path = None
        for path in browser_exes:
            if os.path.exists(path):
                executable_path = path
                break
        
        launch_kwargs = {
            "user_data_dir": user_data_dir,
            "headless": False,
            "slow_mo": 500,
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        
        if executable_path:
            print(f"🚀 Usando navegador del sistema: {executable_path}")
            launch_kwargs["executable_path"] = executable_path
        else:
            print("⚠️ No se encontró Chrome/Edge, intentando con el por defecto de Playwright...")

        browser = p.chromium.launch_persistent_context(**launch_kwargs)
        
        page = browser.new_page()
        print("🌐 Entrando en Exportify...")
        page.goto("https://watsonbox.github.io/exportify/")
        
        try:
            start_button = page.locator("#loginButton")
            if start_button.count() == 0:
                start_button = page.get_by_role("button", name=re.compile(r"Comenzar|Get Started", re.IGNORECASE))
            
            if start_button.count() > 0:
                print("🚀 Pulsando botón de inicio (Comenzar)...")
                start_button.click()
        except Exception as e:
            print(f"ℹ No se encontró el botón de inicio o ya se saltó.")

        if "Log In" in page.content():
            print("🔑 Por favor, inicia sesión en Spotify.")
        
        try:
            print("⏳ Esperando a que cargue la lista de playlists...")
            page.wait_for_selector('table', timeout=60000)
            page.wait_for_timeout(2000)

            if target_playlist.lower() in ["liked", "canciones que me gustan"]:
                print("🔍 Buscando la fila de 'Liked'...")
                row = page.get_by_role("row").filter(has=page.locator('a[href*=":saved"]')).first
                if row.count() == 0:
                    patterns = [r"^Liked$", r"Liked Songs", r"Canciones que me gustan", r"Tus me gusta"]
                    for p_pat in patterns:
                        row_locator = page.get_by_role("row").filter(has_text=re.compile(p_pat, re.IGNORECASE))
                        if row_locator.count() > 0:
                            row = row_locator.first
                            break
            else:
                # Buscar por nombre o URL
                print(f"🔍 Buscando playlist: {target_playlist}...")
                # Exportify tiene un buscador integrado en el DOM
                search_input = page.locator('input[placeholder*="Search"], input[type="search"]').first
                if search_input.count() > 0:
                    search_input.fill(target_playlist)
                    page.wait_for_timeout(1000)
                
                row = page.get_by_role("row").filter(has_text=re.compile(re.escape(target_playlist), re.IGNORECASE)).first
                if row.count() == 0:
                    # Si no lo encuentra por texto, quizás es una URL pegada en el buscador
                    print("⚠️ No encontrada por nombre, intentando búsqueda exacta...")

            if row.count() > 0:
                export_button = row.locator('button').filter(has_text=re.compile(r"Exportar|Export", re.IGNORECASE)).first
                if export_button.count() > 0:
                    print("📥 Iniciando descarga...")
                    with page.expect_download(timeout=60000) as download_info:
                        export_button.click()
                    
                    download = download_info.value
                    download.save_as(output_path)
                    print(f"✅ CSV guardado en: {output_path}")
                else:
                    print("❌ Botón de exportar no encontrado.")
            else:
                print(f"❌ No se encontró la playlist '{target_playlist}'.")

        except Exception as e:
            print(f"❌ Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    run_exportify_bot()
