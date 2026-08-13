import os
import shutil
import time
import subprocess
import sys
import json
import shlex
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv

# Cargar configuración desde .env
load_dotenv()

# ==============================
# 🔴 CONFIGURACIÓN (v8.5 - LAN DISCOVERY OPTIMIZED)
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_CSV = os.path.join(BASE_DIR, 'playlist.csv')
MAIN_SCRIPT = os.path.join(BASE_DIR, 'music_csv_auto.py')
VERIFY_SCRIPT = os.path.join(BASE_DIR, 'verify_downloads.py')
GENERATOR_SCRIPT = os.path.join(BASE_DIR, 'playlist_generator.py')
SYNCABLE_EXTENSIONS = {".mp3", ".lrc", ".m3u8"}

def get_ssh_base_cmd(exe="ssh"):
    cmd = [exe, "-P" if exe == "scp" else "-p", SSH_PORT]
    key_path = os.path.expanduser("~/.ssh/id_ed25519")
    if os.path.exists(key_path): cmd.extend(["-i", key_path])
    for opt in SSH_OPTIONS: cmd.extend(["-o", opt])
    return cmd

def run_ssh_command(ip, command):
    try:
        full_remote_cmd = f"termux-wake-lock && {command}"
        full_cmd = get_ssh_base_cmd("ssh") + [f"{SSH_USER}@{ip}", full_remote_cmd]
        subprocess.run(full_cmd, capture_output=True, check=True, timeout=30)
        return True
    except: return False

def run_ssh_probe(ip, remote_command="echo 'CONNECTED'", timeout=8):
    full_cmd = get_ssh_base_cmd("ssh") + [f"{SSH_USER}@{ip}", remote_command]
    try:
        res = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "ok": "CONNECTED" in res.stdout,
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "exception": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "exception": str(exc),
        }

def check_ssh_connection(ip):
    return run_ssh_probe(ip).get("ok", False)

def is_port_open(ip, port, timeout=1.0):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((ip, port)) == 0
    except:
        return False

def print_ssh_diagnostics(ip):
    key_path = os.path.expanduser("~/.ssh/id_ed25519")
    print(f"[SSH] Diagnostico para {SSH_USER}@{ip}:{SSH_PORT}")

    if not os.path.exists(key_path):
        print(f"   - No existe la clave local esperada: {key_path}")
        print("   - Este script tiene PasswordAuthentication=no y BatchMode=yes.")
        print("   - Si en Termux no tienes tu clave pública en ~/.ssh/authorized_keys, la conexión fallará.")

    if not is_port_open(ip, int(SSH_PORT), timeout=1.5):
        print("   - El puerto SSH no responde en esa IP.")
        print("   - Suele significar IP del móvil cambiada, móvil fuera de la misma WiFi o sshd no levantado.")
        return

    probe = run_ssh_probe(ip)
    if probe["ok"]:
        print("   - El servidor SSH responde correctamente.")
        return

    stderr = (probe.get("stderr") or "").lower()
    if "permission denied" in stderr:
        print("   - El puerto responde, pero la autenticación ha fallado.")
        print("   - Revisa SSH_USER y la clave pública cargada en Termux.")
    elif "connection refused" in stderr:
        print("   - La IP existe, pero el servicio SSH no está aceptando conexiones.")
    elif "no route to host" in stderr or "host unreachable" in stderr:
        print("   - No hay ruta de red hasta el móvil.")
    elif probe.get("exception"):
        print(f"   - Error local al probar SSH: {probe['exception']}")
    elif probe.get("stderr"):
        print(f"   - Respuesta SSH: {probe['stderr']}")
    else:
        print("   - El servidor está abierto, pero la prueba SSH no devolvió 'CONNECTED'.")

def discover_mobile_ip(port=8022):
    """Escanea la red local buscando el puerto de Termux (8022)"""
    # Obtener la IP base del PC
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        prefix = ".".join(local_ip.split(".")[:-1]) + "."
        print(f"[LAN] Tu IP local es {local_ip}. Escaneando rango {prefix}1-254...")
    except:
        prefix = "192.168.1."
        print(f"[LAN] No se pudo detectar IP local. Probando rango {prefix}x...")

    def check_ip(ip):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4) # Aumentado para mayor fiabilidad en WiFi
            if sock.connect_ex((ip, port)) == 0:
                return ip
        return None

    ips_to_check = [prefix + str(i) for i in range(1, 255)]
    ips_to_check.insert(0, "127.0.0.1")

    with ThreadPoolExecutor(max_workers=80) as executor:
        futures = {executor.submit(check_ip, ip): ip for ip in ips_to_check}
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"[LAN] Movil encontrado en: {result}")
                return result
    return None

def stream_songs_batch(ip, file_list, local_root, remote_music_dir):
    if not file_list: return True
    batch_list_path = os.path.join(BASE_DIR, "temp_batch_list.txt")
    with open(batch_list_path, "w", encoding="utf-8") as f:
        for _, rel_path in file_list: f.write(rel_path + "\n")
    try:
        remote_dest_q = shlex.quote(remote_music_dir)
        remote_cmd = f"mkdir -p {remote_dest_q} && tar -C {remote_dest_q} -xmf -"
        ssh_cmd = get_ssh_base_cmd("ssh") + [f"{SSH_USER}@{ip}", remote_cmd]
        tar_cmd = ["tar", "-cf", "-", "-T", batch_list_path]
        p_tar = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=local_root)
        p_ssh = subprocess.Popen(ssh_cmd, stdin=p_tar.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_tar.stdout.close()
        p_ssh.communicate(timeout=300)
        return p_ssh.returncode == 0
    except: return False
    finally:
        if os.path.exists(batch_list_path): os.remove(batch_list_path)

def push_everything_consolidated(ip):
    local_music = os.path.join(BASE_DIR, "canciones_auto")
    if not os.path.exists(local_music): return False

    print(f"📡 Sincronizando scripts con {ip}...")
    scripts = [
        "playlist.csv", "downloaded.json", "music_csv_auto.py", 
        "musicDownloader3.py", "verify_downloads.py", "retry_failed.py",
        "auto_sync.py", "problematic_songs.csv", "duplicate_songs.json", 
        "playlist_generator.py", ".env"
    ]
    for f in scripts:
        f_abs = os.path.join(BASE_DIR, f)
        if os.path.exists(f_abs):
            try:
                # Usamos cat para evitar problemas de permisos en el destino
                subprocess.run(get_ssh_base_cmd("ssh") + [f"{SSH_USER}@{ip}", f"mkdir -p {REMOTE_SYS_BASE} && cat > {REMOTE_SYS_BASE}/{f}"], 
                               stdin=open(f_abs, "rb"), capture_output=True, timeout=10)
            except: pass

    print("📡 Escaneando almacenamiento remoto...")
    res_path = subprocess.run(get_ssh_base_cmd("ssh") + [f"{SSH_USER}@{ip}", "readlink -f ~/storage/music"], 
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    real_base = res_path.stdout.strip() if res_path.stdout.strip() else "/storage/emulated/0/Music"
    real_music_dir = real_base + "/music downloader movil"
    
    # Crear directorio remoto si no existe
    run_ssh_command(ip, f"mkdir -p {shlex.quote(real_music_dir)}")

    list_cmd = f"find {shlex.quote(real_music_dir)} -type f"
    res_remote = subprocess.run(get_ssh_base_cmd("ssh") + [f"{SSH_USER}@{ip}", list_cmd], 
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    
    remote_paths_raw = res_remote.stdout.splitlines()
    remote_files_clean = set()
    prefix_normalized = real_music_dir.replace("\\", "/").lower().rstrip("/") + "/"
    for p in remote_paths_raw:
        p_norm = p.replace("\\", "/").lower()
        if prefix_normalized in p_norm:
            p_clean = p_norm.split(prefix_normalized, 1)[1].strip("/")
            if p_clean: remote_files_clean.add(p_clean)

    song_files_to_send = []
    for root, dirs, files in os.walk(local_music):
        for file in files:
            if os.path.splitext(file)[1].lower() not in SYNCABLE_EXTENSIONS: continue
            abs_p = os.path.join(root, file)
            rel_p_music = os.path.relpath(abs_p, local_music).replace("\\", "/")
            if rel_p_music.lower() not in remote_files_clean:
                song_files_to_send.append((abs_p, rel_p_music))

    if song_files_to_send:
        print(f"🚀 Enviando {len(song_files_to_send)} archivos nuevos...")
        for i in range(0, len(song_files_to_send), BATCH_SIZE):
            batch = song_files_to_send[i:i + BATCH_SIZE]
            stream_songs_batch(ip, batch, local_music, real_music_dir)

    print("🔄 Forzando escaneo de medios en Retro Music...")
    run_ssh_command(ip, f"termux-media-scan -r {shlex.quote(real_music_dir)}")
    print("✅ Sincronización completada.")
    return True

def run_sync():
    is_android = os.path.exists("/sdcard")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Motor de Sincronización...")
    
    if not is_android:
        try:
            from exportify_bot import run_exportify_bot
            run_exportify_bot()
        except ImportError:
            print("⚠️ Playwright no disponible, saltando Exportify...")

    if os.path.exists(PROJECT_CSV):
        print("\n🚀 Procesando descargas...")
        subprocess.run([sys.executable, MAIN_SCRIPT])
        
        print("\n🎵 Generando playlists...")
        subprocess.run([sys.executable, GENERATOR_SCRIPT])
        
    if not is_android:
        print("\n🌐 Iniciando fase de transferencia TURBO...")
        
        target_ip = SSH_IP
        if not check_ssh_connection(target_ip):
            print(f"⚠️ {target_ip} no responde. Escaneando red local...")
            print_ssh_diagnostics(target_ip)
            target_ip = discover_mobile_ip(int(SSH_PORT))
            if not target_ip:
                print("\n❌ No se encontró ningún móvil con 'sshd' activo en tu WiFi.")
                print("💡 Asegúrate de:")
                print("   1. Estar en el mismo WiFi que el PC.")
                print("   2. Escribir 'sshd' en Termux.")
                print("   3. Tener activado el punto de acceso o WiFi (no datos móviles).")
                return

        if not check_ssh_connection(target_ip):
            print_ssh_diagnostics(target_ip)
            print("\n❌ Se encontró una IP candidata, pero la sesión SSH sigue fallando.")
            return

        push_everything_consolidated(target_ip)

if __name__ == "__main__":
    run_sync()
