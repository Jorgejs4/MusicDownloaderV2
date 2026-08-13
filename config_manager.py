import os
import json
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "active_profile": {
        "account": "default",
        "device": "default",
        "playlist": "Liked"
    },
    "accounts": {
        "default": {
            "name": "Mi Cuenta Principal",
            "spotify_session_dir": "spotify_session",
            "youtube_session_dir": "youtube_session",
            "oauth_file": "oauth.json"
        }
    },
    "devices": {
        "default": {
            "name": "Mi Móvil (Termux)",
            "ssh_user": "u0_a461",
            "ssh_ip": "192.168.1.242",
            "ssh_port": "8022",
            "remote_base": "~/Music-Downloader",
            "remote_music": "/storage/emulated/0/Music/music downloader movil"
        },
        "no_sync": {
            "name": "SOLO PREPARAR (Sin Sincro)",
            "ssh_user": "",
            "ssh_ip": "0.0.0.0",
            "ssh_port": "0",
            "remote_base": "",
            "remote_music": ""
        }
    },
    "general": {
        "max_workers": 1,
        "sync_method": "SSH",
        "processing_mode": "FULL",
        "auto_verify": True,
        "theme": "dark",
        "color_theme": "blue"
    }
}

class ConfigManager:
    def __init__(self):
        self.BASE_DIR = get_base_dir()
        self.settings = self.load_settings()

    def load_settings(self):
        settings_file = os.path.join(self.BASE_DIR, "settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge deep enough for active_profile
                    merged = DEFAULT_SETTINGS.copy()
                    for k, v in data.items():
                        if k == "active_profile" and isinstance(v, dict):
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    return merged
            except:
                return DEFAULT_SETTINGS
        return DEFAULT_SETTINGS

    def save_settings(self):
        settings_file = os.path.join(self.BASE_DIR, "settings.json")
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def get_active_account(self):
        acc_id = self.settings["active_profile"]["account"]
        return self.settings["accounts"].get(acc_id, self.settings["accounts"]["default"])

    def get_active_device(self):
        dev_id = self.settings["active_profile"]["device"]
        return self.settings["devices"].get(dev_id, self.settings["devices"]["default"])

    def get_active_playlist(self):
        return self.settings["active_profile"].get("playlist", "Liked")

    def get_music_dir(self):
        """Devuelve la carpeta de música para el perfil activo."""
        acc = self.settings["active_profile"]["account"]
        pl = self.get_active_playlist()
        # Sanitizar nombre de playlist para carpeta
        import re
        safe_pl = re.sub(r'[\\/*?:"<>|]', "", pl).strip()
        path = os.path.join(self.BASE_DIR, "canciones_auto", acc, safe_pl)
        os.makedirs(path, exist_ok=True)
        return path

    def get_playlist_dir(self):
        """Devuelve la carpeta de listas para el perfil activo."""
        path = os.path.join(self.get_music_dir(), "_Playlists")
        os.makedirs(path, exist_ok=True)
        return path

    def add_account(self, acc_id, name, spotify_dir, youtube_dir, oauth_file):
        self.settings["accounts"][acc_id] = {
            "name": name,
            "spotify_session_dir": spotify_dir,
            "youtube_session_dir": youtube_dir,
            "oauth_file": oauth_file
        }
        self.save_settings()

    def add_device(self, dev_id, name, user, ip, port, remote_base, remote_music):
        clean_ip = str(ip).strip().strip(".")
        self.settings["devices"][dev_id] = {
            "name": name,
            "ssh_user": user,
            "ssh_ip": clean_ip,
            "ssh_port": port,
            "remote_base": remote_base,
            "remote_music": remote_music
        }
        self.save_settings()

config = ConfigManager()
