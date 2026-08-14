"""Sincronización incremental de música mediante Android Debug Bridge."""

import os
import shutil
import subprocess
import sys
from urllib.parse import quote

from config_manager import config

SYNCABLE_EXTENSIONS = {".mp3", ".lrc", ".m3u8"}


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ADBSyncEngine:
    def __init__(self, device_config, local_root=None, progress_callback=None):
        self.device_config = device_config
        self.local_root = local_root or config.get_music_dir()
        self.progress_callback = progress_callback
        self.remote_music = device_config.get(
            "adb_remote_music",
            device_config.get("remote_music", "/storage/emulated/0/Music/music downloader movil"),
        )
        self.address = str(device_config.get("adb_address", "")).strip()
        self.serial = str(device_config.get("adb_serial", "")).strip()
        self.adb = self._find_adb()

    def _log(self, message):
        if self.progress_callback:
            self.progress_callback(message)

    def _find_adb(self):
        candidates = [
            shutil.which("adb"),
            os.path.join(_base_dir(), "platform-tools", "adb.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(os.environ.get("ANDROID_HOME", ""), "platform-tools", "adb.exe"),
            os.path.join(os.environ.get("ANDROID_SDK_ROOT", ""), "platform-tools", "adb.exe"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _run(self, args, timeout=30):
        if not self.adb:
            return None, "adb no encontrado"
        try:
            result = subprocess.run(
                [self.adb] + args,
                capture_output=True,
                timeout=timeout,
            )
            stdout = result.stdout.decode("utf-8", errors="replace").strip()
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            return result, stdout or stderr
        except Exception as exc:
            return None, str(exc)

    def _device_args(self):
        return ["-s", self.serial] if self.serial else []

    def check_connection(self):
        if not self.adb:
            return False, "No se encontró adb. Instala Android Platform Tools."

        if self.address:
            result, output = self._run(["connect", self.address], timeout=15)
            if result is None or result.returncode != 0 or "connected" not in output.lower():
                return False, output or "No se pudo conectar por ADB Wi-Fi."
            self.serial = self.address

        result, output = self._run(["devices"], timeout=15)
        if result is None or result.returncode != 0:
            return False, output

        devices = []
        for line in output.splitlines():
            if "\tdevice" in line:
                devices.append(line.split("\t", 1)[0].strip())

        if self.serial and self.serial in devices:
            return True, f"ADB conectado: {self.serial}"
        if not self.serial and devices:
            self.serial = devices[0]
            return True, f"ADB conectado: {self.serial}"
        return False, "No hay ningún dispositivo ADB autorizado."

    def get_remote_files(self):
        ok, error = self.check_connection()
        if not ok:
            self._log(f"⚠️ ADB: {error}")
            return set()

        result, output = self._run(
            self._device_args() + ["shell", "find", self.remote_music, "-type", "f"],
            timeout=60,
        )
        if result is None or result.returncode != 0:
            self._log(f"⚠️ No se pudo escanear el móvil por ADB: {output}")
            return set()

        prefix = self.remote_music.rstrip("/") + "/"
        remote = set()
        for line in output.splitlines():
            path = line.strip()
            if path.startswith(prefix):
                remote.add(path[len(prefix):].lower().replace("\\", "/"))
        self._log(f"📱 ADB: {len(remote)} archivos encontrados en el móvil.")
        return remote

    def _shell(self, *args, timeout=30):
        return self._run(self._device_args() + ["shell"] + list(args), timeout=timeout)

    def _push(self, local_path, relative_path):
        remote_path = self.remote_music.rstrip("/") + "/" + relative_path.replace("\\", "/")
        remote_dir = remote_path.rsplit("/", 1)[0]
        result, output = self._shell("mkdir", "-p", remote_dir)
        if result is None or result.returncode != 0:
            return False, output
        result, output = self._run(
            self._device_args() + ["push", local_path, remote_path],
            timeout=180,
        )
        return bool(result and result.returncode == 0), output

    def push_files(self, specific_files=None):
        ok, error = self.check_connection()
        if not ok:
            return {"success": False, "msg": error}

        remote_files = self.get_remote_files() if not specific_files else set()
        candidates = []
        if specific_files:
            for relative in specific_files:
                local = os.path.join(self.local_root, relative)
                if os.path.isfile(local):
                    candidates.append((local, relative.replace("\\", "/")))
        else:
            for root, _, files in os.walk(self.local_root):
                for filename in files:
                    if os.path.splitext(filename)[1].lower() not in SYNCABLE_EXTENSIONS:
                        continue
                    local = os.path.join(root, filename)
                    relative = os.path.relpath(local, self.local_root).replace("\\", "/")
                    if relative.lower() not in remote_files or filename.lower().endswith(".m3u8"):
                        candidates.append((local, relative))

        sent = 0
        failed = []
        for index, (local, relative) in enumerate(candidates, start=1):
            self._log(f"📡 ADB: enviando {index}/{len(candidates)}: {relative}")
            success, error = self._push(local, relative)
            if success:
                sent += 1
            else:
                failed.append(f"{relative}: {error}")

        # Fuerza la actualización de la biblioteca multimedia de Android.
        if sent:
            self._shell(
                "am", "broadcast",
                "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                "-d", "file:///" + quote(self.remote_music, safe="/") + "/",
                timeout=30,
            )
        return {
            "success": not failed,
            "msg": f"{sent} archivos enviados por ADB.",
            "stats": {"songs": sent, "failed": failed},
        }
