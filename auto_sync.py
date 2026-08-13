import os
import shutil
import time
import subprocess
import sys
import json
import shlex
import socket
import tarfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv

# Cargar configuración desde .env
load_dotenv()

# ==============================
# 🔴 CONFIGURACIÓN (v9.5 - ROBUST SYNC)
# ==============================
SSH_USER = os.environ.get("SSH_USER", "u0_a461") 
SSH_IP   = os.environ.get("SSH_IP", "127.0.0.1")
SSH_PORT = os.environ.get("SSH_PORT", "8022")

REMOTE_SYS_BASE = "~/Music-Downloader"
BATCH_SIZE = 50 

SSH_OPTIONS = [
    "ConnectTimeout=15",
    "StrictHostKeyChecking=no",
    "UserKnownHostsFile=/dev/null",
    "PasswordAuthentication=no",
    "PreferredAuthentications=publickey",
    "BatchMode=yes",
    "LogLevel=ERROR",
    "ServerAliveInterval=10"
]

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
PROJECT_CSV = os.path.join(BASE_DIR, 'playlist.csv')
SYNCABLE_EXTENSIONS = {".mp3", ".lrc", ".m3u8"}

class SyncEngine:
    def __init__(self, device_config, local_root=None):
        from config_manager import config
        self.user = device_config.get("ssh_user", SSH_USER)
        self.ip = str(device_config.get("ssh_ip", SSH_IP)).strip().strip(".")
        self.port = str(device_config.get("ssh_port", SSH_PORT))
        self.remote_base = device_config.get("remote_base", REMOTE_SYS_BASE)
        self.remote_music = device_config.get("remote_music", "/storage/emulated/0/Music/music downloader movil")
        
        # FIX: Ensure local_root is specific to the active profile
        self.local_root = local_root or config.get_music_dir()
        print(f"ðŸ” DEBUG SYNC: Local root is {self.local_root}")

    def get_ssh_base_cmd(self, exe="ssh"):
        cmd = [exe, "-P" if exe == "scp" else "-p", self.port]
        key_path = os.path.expanduser("~/.ssh/id_ed25519")
        if os.path.exists(key_path): cmd.extend(["-i", key_path])
        for opt in SSH_OPTIONS: cmd.extend(["-o", opt])
        return cmd

    def run_ssh_command(self, command):
        try:
            full_remote_cmd = f"termux-wake-lock && {command}"
            full_cmd = self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", full_remote_cmd]
            subprocess.run(full_cmd, capture_output=True, check=True, timeout=30)
            return True
        except: return False

    def check_connection(self):
        """Intenta conectar por SSH y devuelve (bool_exito, mensaje_error)."""
        full_cmd = self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", "echo 'CONNECTED'"]
        try:
            res = subprocess.run(full_cmd, capture_output=True, timeout=12)
            # Decodificar manualmente con UTF-8
            out = res.stdout.decode('utf-8', errors='ignore')
            if "CONNECTED" in out:
                return True, "OK"
            err = res.stderr.decode('utf-8', errors='ignore').strip() or f"Código de salida: {res.returncode}"
            return False, err
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado (Timeout)"
        except Exception as e:
            return False, str(e)

    def get_remote_files(self):
        """Devuelve un conjunto de rutas relativas (minúsculas) de archivos en el móvil."""
        conn_ok, _ = self.check_connection()
        if not conn_ok: 
            print("❌ No hay conexión SSH para escanear archivos remotos.")
            return set()
        
        # 1. Determinar ruta de música real
        try:
            res_path = subprocess.run(self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", "readlink -f ~/storage/music"], 
                                      capture_output=True, timeout=15)
            # Decodificar manualmente para evitar errores de charmap en Windows
            path_out = res_path.stdout.decode('utf-8', errors='ignore').strip()
            real_base = path_out if path_out else "/storage/emulated/0/Music"
        except:
            real_base = "/storage/emulated/0/Music"
            
        real_music_dir = real_base + "/music downloader movil"

        # 2. Escaneo recursivo profundo
        list_cmd = f"find {shlex.quote(real_music_dir)} -type f"
        try:
            res_remote = subprocess.run(self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", list_cmd], 
                                        capture_output=True, timeout=60)
            
            remote_files = set()
            prefix_normalized = real_music_dir.lower().replace("\\", "/").rstrip("/") + "/"
            
            # Decodificar manualmente con UTF-8
            stdout_str = res_remote.stdout.decode('utf-8', errors='ignore')
            lines = stdout_str.splitlines()
            for line in lines:
                p_norm = line.lower().replace("\\", "/").strip()
                if prefix_normalized in p_norm:
                    # Extraemos la ruta relativa (ej: artista/cancion.mp3)
                    rel_p = p_norm.split(prefix_normalized, 1)[1]
                    if rel_p: 
                        remote_files.add(rel_p)
            
            return remote_files
        except Exception as e:
            print(f"❌ Error al listar archivos remotos: {e}")
            return set()

    def cleanup_remote_problematic_songs(self):
        """Elimina del móvil las canciones que el usuario ha marcado como 'malas' y carpetas redundantes."""
        targets = [
            "how it goes", "slackface", "thoughts of you", "These word", 
            "too long", "7PM", "blasphemy", "whats changed", "rae of sunshine",
            "faint", "decode", "morph", "englishman in new york"
        ]
        
        # 1. Determinar ruta de música real
        try:
            res_path = subprocess.run(self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", "readlink -f ~/storage/music"], 
                                      capture_output=True, timeout=15)
            path_out = res_path.stdout.decode('utf-8', errors='ignore').strip()
            real_base = path_out if path_out else "/storage/emulated/0/Music"
        except:
            real_base = "/storage/emulated/0/Music"
            
        real_music_dir = real_base + "/music downloader movil"

        # 2. BORRAR CARPETAS REDUNDANTES (Aplanamiento de estructura)
        # Esto elimina 'default/Liked' y similares si existen dentro de la carpeta de musica
        redundant_dirs = ["default", "canciones_auto"]
        for rd in redundant_dirs:
            print(f"🧹 Eliminando carpeta redundante en móvil: {rd}...")
            self.run_ssh_command(f"rm -rf {shlex.quote(real_music_dir + '/' + rd)}")

        # 3. Borrado selectivo de canciones 'malas'
        find_parts = [f"-iname '*{t}*'" for t in targets]
        find_filter = " -o ".join(find_parts)
        rm_cmd = fr"find {shlex.quote(real_music_dir)} -type f \( {find_filter} \) -delete"
        
        print(f"🧹 Limpiando canciones problemáticas en el móvil...")
        self.run_ssh_command(rm_cmd)

    def push_files(self, specific_files=None):
        if not os.path.exists(self.local_root): return {"success": False, "msg": "No hay música local"}

        # 0. Limpieza de canciones problemáticas en remoto para forzar su envío
        self.cleanup_remote_problematic_songs()

        # 0.1 Intentar rsync si está disponible (solo para sincronización completa)
        if not specific_files and self.check_rsync_available():
            print("✨ Usando RSYNC para máxima fiabilidad y reanudación...")
            # Obtener ruta remota real
            try:
                res_path = subprocess.run(self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", "readlink -f ~/storage/music"], 
                                          capture_output=True, timeout=15)
                path_out = res_path.stdout.decode('utf-8', errors='ignore').strip()
                real_base = path_out if path_out else "/storage/emulated/0/Music"
            except:
                real_base = "/storage/emulated/0/Music"
            real_music_dir = real_base + "/music downloader movil"
            
            if self.push_files_rsync(self.local_root, real_music_dir):
                self.run_ssh_command(f"termux-media-scan -r {shlex.quote(real_music_dir)}")
                return {"success": True, "stats": {"mode": "rsync"}}
            print("⚠️ Rsync falló o no es compatible, volviendo al método tradicional.")

        stats = {"scripts": 0, "songs": 0, "playlists": []}
        
        # 1. Sincronizar scripts (solo si no es un sync específico)
        if not specific_files:
            scripts = ["playlist.csv", "downloaded.json", "music_csv_auto.py", "musicDownloader3.py", ".env"]
            for f in scripts:
                f_abs = os.path.join(BASE_DIR, f)
                if os.path.exists(f_abs):
                    try:
                        subprocess.run(self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", f"mkdir -p {self.remote_base} && cat > {self.remote_base}/{f}"], 
                                       stdin=open(f_abs, "rb"), capture_output=True, timeout=15)
                        stats["scripts"] += 1
                    except: pass

        # 2. Sincronizar música
        try:
            res_path = subprocess.run(self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", "readlink -f ~/storage/music"], 
                                      capture_output=True, timeout=15)
            path_out = res_path.stdout.decode('utf-8', errors='ignore').strip()
            real_base = path_out if path_out else "/storage/emulated/0/Music"
        except:
            real_base = "/storage/emulated/0/Music"
        
        real_music_dir = real_base + "/music downloader movil"
        playlist_remote_dir = real_music_dir + "/_Playlists" # Ruta explícita para listas
        
        print(f"🔍 DEBUG SSH: Moviendo música a -> {real_music_dir}")
        print(f"🔍 DEBUG SSH: Moviendo listas a -> {playlist_remote_dir}")
        
        self.run_ssh_command(f"mkdir -p {shlex.quote(real_music_dir)}")
        self.run_ssh_command(f"mkdir -p {shlex.quote(playlist_remote_dir)}")

        song_files_to_send = []
        playlist_files_to_send = [] # Lista separada para listas
        
        if specific_files:
            for rel_p in specific_files:
                abs_p = os.path.join(self.local_root, rel_p)
                if os.path.exists(abs_p):
                    if rel_p.lower().endswith(".m3u8"):
                        playlist_files_to_send.append((abs_p, rel_p.replace("\\", "/")))
                    else:
                        song_files_to_send.append((abs_p, rel_p.replace("\\", "/")))
        else:
            # Sincro completa (delta)
            remote_files_clean = self.get_remote_files()
            
            for root, dirs, files in os.walk(self.local_root):
                for file in files:
                    if os.path.splitext(file)[1].lower() not in SYNCABLE_EXTENSIONS: continue
                    abs_p = os.path.join(root, file)
                    rel_p_music = os.path.relpath(abs_p, self.local_root).replace("\\", "/")
                    
                    if file.lower().endswith(".m3u8"):
                        # Las playlists van directo a la carpeta _Playlists
                        playlist_files_to_send.append((abs_p, file))
                        stats["playlists"].append(file)
                    elif rel_p_music.lower() not in remote_files_clean:
                        song_files_to_send.append((abs_p, rel_p_music))
                        stats["songs"] += 1

        # Enviar música
        if song_files_to_send:
            print(f"📦 Enviando {len(song_files_to_send)} canciones...")
            for i in range(0, len(song_files_to_send), BATCH_SIZE):
                self.stream_songs_batch_internal(song_files_to_send[i:i+BATCH_SIZE], self.local_root, real_music_dir)
        
        # Enviar playlists
        if playlist_files_to_send:
            print(f"📦 Enviando {len(playlist_files_to_send)} playlists a _Playlists...")
            self.stream_songs_batch_internal(playlist_files_to_send, self.local_root, playlist_remote_dir)

        self.run_ssh_command(f"termux-media-scan -r {shlex.quote(real_music_dir)}")
        return {"success": True, "stats": stats}

    def stream_songs_batch_internal(self, file_list, local_root, remote_music_dir):
        local_tar_path = os.path.join(BASE_DIR, "temp_sync.tar")
        
        # DEBUG: Ver qué estamos intentando enviar
        print(f"🔍 DEBUG: Preparando lote en {local_root}")
        
        try:
            # 1. Crear TAR local usando el módulo nativo de Python (mucho más robusto)
            print(f"📦 Empaquetando {len(file_list)} archivos con tarfile nativo...")
            with tarfile.open(local_tar_path, "w") as tar:
                count = 0
                for abs_path, rel_path in file_list:
                    if os.path.isfile(abs_path):
                        # Forzar el nombre dentro del tar a usar forward slashes
                        arcname = rel_path.replace("\\", "/")
                        tar.add(abs_path, arcname=arcname)
                        count += 1
            
            if count == 0:
                print("⚠️ No se añadieron archivos al lote.")
                return False

            # 2. Enviar TAR vía SSH y extraer
            remote_dest_q = shlex.quote(remote_music_dir)
            remote_cmd = f"mkdir -p {remote_dest_q} && tar -C {remote_dest_q} -xmf -"
            ssh_cmd = self.get_ssh_base_cmd("ssh") + [f"{self.user}@{self.ip}", remote_cmd]
            
            print(f"🚀 Transfiriendo lote ({os.path.getsize(local_tar_path)/1024/1024:.2f} MB)...")
            with open(local_tar_path, "rb") as f_tar:
                res_ssh = subprocess.run(ssh_cmd, stdin=f_tar, capture_output=True)
            
            if res_ssh.returncode != 0:
                err_msg = res_ssh.stderr.decode('utf-8', errors='ignore')
                print(f"❌ Error en la transferencia/extracción remota: {err_msg}")
                return False
            
            print("✅ Lote enviado y extraído con éxito.")
            return True
                
        except Exception as e:
            print(f"❌ Excepción en stream_songs_batch_internal: {e}")
            return False
        finally:
            if os.path.exists(local_tar_path):
                try: os.remove(local_tar_path)
                except: pass

def run_sync():
    pass
