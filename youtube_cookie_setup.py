import os
import time
import json
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "youtube_session")
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")
AUTH_INFO_FILE = os.path.join(BASE_DIR, "youtube_auth.json")
PREFERRED_BROWSERS = [
    ("chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ("msedge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]

YOUTUBE_DOMAINS = (
    ".youtube.com",
    ".google.com",
    ".accounts.google.com",
    ".music.youtube.com",
    ".youtubei.googleapis.com",
    ".googlevideo.com",
)
LOGIN_COOKIE_NAMES = {
    "sapisid",
    "__secure-1psapisid",
    "__secure-3psapisid",
    "sid",
    "__secure-1psid",
    "__secure-3psid",
    "login_info",
}


def to_netscape_line(cookie: dict) -> str:
    domain = cookie.get("domain", "")
    include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
    path = cookie.get("path", "/")
    secure = "TRUE" if cookie.get("secure") else "FALSE"
    expires = int(cookie.get("expires", 0) or 0)
    name = cookie.get("name", "")
    value = cookie.get("value", "")
    return "\t".join([domain, include_subdomains, path, secure, str(expires), name, value])


def is_youtube_cookie(cookie: dict) -> bool:
    domain = (cookie.get("domain") or "").lower()
    return any(domain.endswith(target) for target in YOUTUBE_DOMAINS)


def save_cookies_txt(cookies: list[dict]):
    filtered = [cookie for cookie in cookies if is_youtube_cookie(cookie)]
    filtered.sort(key=lambda c: ((c.get("domain") or ""), (c.get("name") or "")))

    with open(COOKIE_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Generado automáticamente por youtube_cookie_setup.py\n")
        for cookie in filtered:
            f.write(to_netscape_line(cookie) + "\n")

    return len(filtered)


def save_auth_info(page):
    auth_info = {
        "visitor_data": None,
        "data_sync_id": None,
        "delegated_session_id": None,
        "updated_at": int(time.time()),
    }
    try:
        page.goto("https://www.youtube.com", wait_until="domcontentloaded")
        time.sleep(3)
        extracted = page.evaluate(
            """() => {
                const safeGet = (key) => {
                    try {
                        if (window.ytcfg && typeof window.ytcfg.get === 'function') {
                            return window.ytcfg.get(key) || null;
                        }
                    } catch (e) {}
                    return null;
                };
                return {
                    visitor_data: safeGet('VISITOR_DATA'),
                    data_sync_id: safeGet('DATASYNC_ID'),
                    delegated_session_id: safeGet('DELEGATED_SESSION_ID'),
                };
            }"""
        )
        if isinstance(extracted, dict):
            auth_info.update(extracted)
    except Exception:
        pass

    with open(AUTH_INFO_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_info, f, indent=2, ensure_ascii=False)

    return auth_info


def has_login_cookies(cookies: list[dict]) -> bool:
    for cookie in cookies:
        if not is_youtube_cookie(cookie):
            continue
        if (cookie.get("name") or "").lower() in LOGIN_COOKIE_NAMES:
            return True
    return False


def launch_browser_context(playwright):
    launch_kwargs = {
        "user_data_dir": USER_DATA_DIR,
        "headless": False,
        "slow_mo": 250,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    }

    for name, executable_path in PREFERRED_BROWSERS:
        if not os.path.exists(executable_path):
            continue
        try:
            print(f"Usando navegador real: {name}")
            return playwright.chromium.launch_persistent_context(
                executable_path=executable_path,
                **launch_kwargs,
            )
        except Exception as e:
            print(f"No se pudo abrir {name}: {e}")

    print("Usando Chromium de Playwright como último recurso.")
    return playwright.chromium.launch_persistent_context(**launch_kwargs)


def main():
    os.makedirs(USER_DATA_DIR, exist_ok=True)

    print("Abriendo navegador para preparar cookies de YouTube...")
    print("Inicia sesion en YouTube o YouTube Music en la ventana que se abrira.")
    print("El script esperara automaticamente hasta detectar cookies de sesion.")

    with sync_playwright() as p:
        browser = launch_browser_context(p)

        page = browser.new_page()
        page.goto("https://accounts.google.com/ServiceLogin?service=youtube", wait_until="domcontentloaded")
        time.sleep(3)

        cookies = []
        deadline = time.time() + 600
        last_notice = 0
        while time.time() < deadline:
            try:
                cookies = browser.cookies()
            except Exception:
                break
            if has_login_cookies(cookies):
                break

            now = time.time()
            if now - last_notice >= 15:
                print("Esperando login de YouTube... completa el inicio de sesion en la ventana abierta.")
                last_notice = now
            time.sleep(5)

        total = save_cookies_txt(cookies)
        auth_info = save_auth_info(page)
        browser.close()

    if total <= 0 or not has_login_cookies(cookies):
        print("No se pudieron extraer cookies utiles de YouTube.")
        print("Asegurate de haber iniciado sesion realmente en la ventana del navegador.")
        return

    print(f"cookies.txt generado con {total} cookies.")
    print(f"Ruta: {COOKIE_FILE}")
    if auth_info.get("visitor_data") or auth_info.get("data_sync_id"):
        print(f"Auth info guardada en: {AUTH_INFO_FILE}")
    print("Ya puedes ejecutar de nuevo: python auto_sync.py")


if __name__ == "__main__":
    main()
