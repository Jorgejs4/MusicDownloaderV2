import customtkinter as ctk
import os
import sys
import threading
import subprocess
import queue
from PIL import Image, ImageTk
from config_manager import config
from exportify_bot import run_exportify_bot
from music_csv_auto import DownloadEngine
from auto_sync import SyncEngine
from qr_sync import QRServer
import playlist_generator
import restaurar_respaldo

# Asegurar copia de seguridad inicial
restaurar_respaldo.create_backup()

# Configuración de apariencia
ctk.set_appearance_mode(config.settings["general"]["theme"])
ctk.set_default_color_theme(config.settings["general"]["color_theme"])

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Music Downloader B3 - Pro Edition")
        self.geometry("1100x800")

        # Estado del proceso
        self.stop_event = threading.Event()
        self.active_thread = None
        self.ui_queue = queue.Queue()

        # Configurar grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Crear sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Music B3", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.home_button = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Inicio",
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", command=self.home_button_event)
        self.home_button.grid(row=1, column=0, sticky="ew")

        self.accounts_button = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Cuentas",
                                             fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                             anchor="w", command=self.accounts_button_event)
        self.accounts_button.grid(row=2, column=0, sticky="ew")

        self.devices_button = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Dispositivos",
                                            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                            anchor="w", command=self.devices_button_event)
        self.devices_button.grid(row=3, column=0, sticky="ew")

        self.qr_sync_button = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Sincro QR Pro",
                                            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                            anchor="w", command=self.qr_sync_button_event)
        self.qr_sync_button.grid(row=4, column=0, sticky="ew")

        self.cleaner_button = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Limpiador Pro",
                                            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                            anchor="w", command=self.cleaner_button_event)
        self.cleaner_button.grid(row=5, column=0, sticky="ew")

        self.settings_button = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Ajustes",
                                             fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                             anchor="w", command=self.settings_button_event)
        self.settings_button.grid(row=6, column=0, sticky="ew", pady=(0, 20))

        # Crear frames
        self.home_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.accounts_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.devices_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.qr_sync_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.cleaner_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.setup_home_frame()
        self.setup_accounts_frame()
        self.setup_devices_frame()
        self.setup_qr_sync_frame()
        self.setup_cleaner_frame()
        self.setup_settings_frame()

        self.select_frame_by_name("home")
        self.qr_server = QRServer(progress_callback=lambda msg, *args: self.ui_call(self.append_log, f"📱 [QR Sync]: {msg}\n"))
        self.after(100, self.process_ui_queue)

    def setup_home_frame(self):
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(self.home_frame, text="Listo para sincronizar", font=ctk.CTkFont(size=24, weight="bold"))
        self.status_label.grid(row=0, column=0, padx=20, pady=20)

        self.profile_frame = ctk.CTkFrame(self.home_frame)
        self.profile_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.profile_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(self.profile_frame, text="Spotify Account:").grid(row=0, column=0, padx=10, pady=5)
        self.account_selector = ctk.CTkOptionMenu(self.profile_frame, values=list(config.settings["accounts"].keys()), command=self.change_account)
        self.account_selector.set(config.settings["active_profile"]["account"])
        self.account_selector.grid(row=1, column=0, padx=10, pady=10)

        ctk.CTkLabel(self.profile_frame, text="Target Playlist:").grid(row=0, column=1, padx=10, pady=5)
        self.playlist_entry = ctk.CTkEntry(self.profile_frame, placeholder_text="Liked o nombre de playlist")
        self.playlist_entry.insert(0, config.get_active_playlist())
        self.playlist_entry.bind("<FocusOut>", self.save_playlist_pref)
        self.playlist_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.profile_frame, text="Sync Device:").grid(row=0, column=2, padx=10, pady=5)
        self.device_selector = ctk.CTkOptionMenu(self.profile_frame, values=list(config.settings["devices"].keys()), command=self.change_device)
        self.device_selector.set(config.settings["active_profile"]["device"])
        self.device_selector.grid(row=1, column=2, padx=10, pady=10)

        # NUEVO: Modo de procesamiento directamente en Inicio
        ctk.CTkLabel(self.profile_frame, text="Modo Trabajo:").grid(row=0, column=3, padx=10, pady=5)
        self.proc_menu = ctk.CTkOptionMenu(self.profile_frame, 
                                          values=["Completo (+Listas)", "Solo Descargar"], 
                                          command=self.change_processing_mode)
        current_proc = config.settings["general"].get("processing_mode", "FULL")
        self.proc_menu.set("Completo (+Listas)" if current_proc == "FULL" else "Solo Descargar")
        self.proc_menu.grid(row=1, column=3, padx=10, pady=10)

        self.btn_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, padx=40, pady=20, sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.dl_button = ctk.CTkButton(self.btn_frame, text="SOLO DESCARGAR (PC)", height=50, 
                                       fg_color="#1f538d", hover_color="#14375e",
                                       font=ctk.CTkFont(size=14, weight="bold"), 
                                       command=lambda: self.start_process(sync=False))
        self.dl_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.sync_button = ctk.CTkButton(self.btn_frame, text="DESCARGAR Y SINCRONIZAR", height=50, 
                                         font=ctk.CTkFont(size=14, weight="bold"), 
                                         command=lambda: self.start_process(sync=True))
        self.sync_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.cancel_button = ctk.CTkButton(self.btn_frame, text="CANCELAR", height=50, fg_color="#A02020", hover_color="#801010", state="disabled", command=self.cancel_process)
        self.cancel_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.log_textbox = ctk.CTkTextbox(self.home_frame, height=300)
        self.log_textbox.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

    def save_playlist_pref(self, event=None):
        val = self.playlist_entry.get().strip() or "Liked"
        config.settings["active_profile"]["playlist"] = val
        config.save_settings()

    def setup_accounts_frame(self):
        self.accounts_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.accounts_frame, text="Gestión de Cuentas", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=20)
        self.accounts_scroll = ctk.CTkScrollableFrame(self.accounts_frame, height=450)
        self.accounts_scroll.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.refresh_accounts_list()
        ctk.CTkButton(self.accounts_frame, text="+ Añadir Nueva Cuenta", command=self.add_account_dialog).grid(row=2, column=0, pady=20)

    def refresh_accounts_list(self):
        for widget in self.accounts_scroll.winfo_children(): widget.destroy()
        for acc_id, data in config.settings["accounts"].items():
            f = ctk.CTkFrame(self.accounts_scroll)
            f.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(f, text=f"{data['name']} (ID: {acc_id})", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            ctk.CTkButton(f, text="Ajustes", width=60, command=lambda a=acc_id: self.edit_account_settings(a)).pack(side="right", padx=5)
            ctk.CTkButton(f, text="Nombre", width=60, command=lambda a=acc_id: self.edit_account_name(a)).pack(side="right", padx=5)

    def setup_devices_frame(self):
        self.devices_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.devices_frame, text="Gestión de Dispositivos", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=20)
        self.devices_scroll = ctk.CTkScrollableFrame(self.devices_frame, height=450)
        self.devices_scroll.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.refresh_devices_list()
        ctk.CTkButton(self.devices_frame, text="+ Añadir Nuevo Dispositivo", command=self.add_device_dialog).grid(row=2, column=0, pady=20)

    def refresh_devices_list(self):
        for widget in self.devices_scroll.winfo_children(): widget.destroy()
        for dev_id, data in config.settings["devices"].items():
            f = ctk.CTkFrame(self.devices_scroll)
            f.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(f, text=f"{data['name']} - {data['ssh_ip']}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            ctk.CTkButton(f, text="Ajustes IP/SSH", width=60, command=lambda d=dev_id: self.edit_device_settings(d)).pack(side="right", padx=5)
            ctk.CTkButton(f, text="Nombre", width=60, command=lambda d=dev_id: self.edit_device_name(d)).pack(side="right", padx=5)

    def edit_account_name(self, acc_id):
        new = ctk.CTkInputDialog(text="Nuevo nombre para la cuenta:", title="Editar Nombre").get_input()
        if new:
            config.settings["accounts"][acc_id]["name"] = new
            config.save_settings()
            self.refresh_accounts_list()

    def edit_account_settings(self, acc_id):
        data = config.settings["accounts"][acc_id]
        new_dir = ctk.CTkInputDialog(text=f"Directorio de Sesión (Spotify):\nActual: {data['spotify_session_dir']}", title="Editar Ajustes").get_input()
        if new_dir:
            data["spotify_session_dir"] = new_dir
            config.save_settings()

    def edit_device_name(self, dev_id):
        new = ctk.CTkInputDialog(text="Nuevo nombre para el dispositivo:", title="Editar Nombre").get_input()
        if new:
            config.settings["devices"][dev_id]["name"] = new
            config.save_settings()
            self.refresh_devices_list()

    def edit_device_settings(self, dev_id):
        data = config.settings["devices"][dev_id]
        new_ip = ctk.CTkInputDialog(text=f"Nueva Dirección IP (LAN):\nActual: {data['ssh_ip']}", title="Ajustes IP").get_input()
        if new_ip:
            data["ssh_ip"] = new_ip
            config.save_settings()
            self.refresh_devices_list()

    def setup_qr_sync_frame(self):
        self.qr_sync_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.qr_sync_frame, text="Sincronización QR Pro", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, pady=20)
        self.qr_desc = ctk.CTkLabel(self.qr_sync_frame, text="Escanea para sincronizar o descargar tu música desde el móvil sin cables ni apps.\n💡 TRUCO: Puedes descargar toda la biblioteca en ZIP o escuchar canciones individuales.", font=ctk.CTkFont(size=13), text_color="gray")
        self.qr_desc.grid(row=1, column=0, pady=10)

        self.qr_canvas_container = ctk.CTkFrame(self.qr_sync_frame, fg_color="white", corner_radius=12, width=320, height=320)
        self.qr_canvas_container.grid(row=2, column=0, pady=15)
        self.qr_canvas_container.grid_propagate(False)

        self.qr_image_label = ctk.CTkLabel(self.qr_canvas_container, text="QR no activo\nPresiona un botón abajo", font=ctk.CTkFont(size=14), text_color="gray40")
        self.qr_image_label.place(relx=0.5, rely=0.5, anchor="center")

        self.url_box_frame = ctk.CTkFrame(self.qr_sync_frame, fg_color="transparent")
        self.url_box_frame.grid(row=3, column=0, pady=5)

        self.qr_url_label = ctk.CTkLabel(self.url_box_frame, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1DB954")
        self.qr_url_label.pack(side="left", padx=5)

        self.copy_url_btn = ctk.CTkButton(self.url_box_frame, text="📋 Copiar", width=80, height=28, command=self.copy_qr_url, state="disabled")
        self.copy_url_btn.pack(side="left", padx=5)

        self.btn_container = ctk.CTkFrame(self.qr_sync_frame, fg_color="transparent")
        self.btn_container.grid(row=4, column=0, pady=15)

        self.qr_toggle_btn = ctk.CTkButton(self.btn_container, text="ACTIVAR LOCAL (Wi-Fi)", height=50, width=200, command=self.toggle_qr_server)
        self.qr_toggle_btn.pack(side="left", padx=10)

        self.zrok_btn = ctk.CTkButton(self.btn_container, text="ACTIVAR REMOTO (Cualquier Red)", height=50, width=200, fg_color="#6B21A8", hover_color="#581C87", command=self.start_zrok_remote)
        self.zrok_btn.pack(side="left", padx=10)

    def copy_qr_url(self):
        url = self.qr_url_label.cget("text")
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.append_log(f"📋 Enlace copiado al portapapeles: {url}\n")

    def start_zrok_remote(self):
        """Inicia el servidor y lo expone al mundo vía Zrok."""
        if not self.qr_server.server:
            self.toggle_qr_server()

        self.append_log("🌐 Iniciando túnel remoto para acceso global...\n")
        self.zrok_btn.configure(state="disabled", text="⏳ Conectando...")

        def _remote_task():
            import re
            try:
                # 1. Intentar Zrok primero
                port = self.qr_server.port
                cmd = f"zrok share public http://localhost:{port} --headless"
                self.zrok_proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                found_url = None
                for line in self.zrok_proc.stdout:
                    if "https://" in line:
                        match = re.search(r"https://[a-z0-9-.]+\.zrok\.io", line)
                        if match:
                            temp_url = match.group(0)
                            if "api-v1" in temp_url:
                                continue
                            found_url = temp_url
                            break
                
                if found_url:
                    img_qr, _ = self.qr_server.generate_qr(override_url=found_url)
                    self.ui_call(self._show_qr, img_qr, found_url)
                    self.ui_call(self.append_log, f"✅ Acceso Remoto Activo (Zrok): {found_url}\n")
                    self.ui_call(self.zrok_btn.configure, state="normal", text="REMOTO ZROK ACTIVO", fg_color="#1DB954")
                else:
                    # 2. Fallback a Cloudflare
                    self.ui_call(self.append_log, "⚠️ Zrok no disponible, intentando Cloudflare...\n")
                    img_qr, url = self.qr_server.generate_qr(require_public=True)
                    self.ui_call(self._show_qr, img_qr, url)
                    self.ui_call(self.append_log, f"✅ Acceso Remoto Activo (Cloudflare): {url}\n")
                    self.ui_call(self.zrok_btn.configure, state="normal", text="REMOTO CLOUDFLARE ACTIVO", fg_color="#2f80ed")

            except Exception as e:
                self.ui_call(self.append_log, f"❌ Error en acceso remoto: {e}\n")
                self.ui_call(self.zrok_btn.configure, state="normal", text="ACTIVAR REMOTO (Cualquier Red)")

        threading.Thread(target=_remote_task, daemon=True).start()

    def toggle_qr_server(self):
        current_text = self.qr_toggle_btn.cget("text")
        if "ACTIVAR" in current_text:
            # Deshabilitar botón mientras arranca
            self.qr_toggle_btn.configure(state="disabled", text="⏳ Iniciando servidor...")

            def _start():
                try:
                    # 1️⃣ Servidor HTTP local
                    self.qr_server.start()

                    # 2️⃣ QR local
                    img_qr, url = self.qr_server.generate_qr(require_public=False)

                    # 3️⃣ Actualizar UI
                    self.ui_call(self._show_qr, img_qr, url)

                except Exception as e:
                    self.qr_server.stop()
                    self.ui_call(self.append_log, f"❌ Error al iniciar QR: {e}\n")
                    self.ui_call(self.qr_toggle_btn.configure, state="normal", text="ACTIVAR LOCAL (Wi-Fi)")

            threading.Thread(target=_start, daemon=True).start()

        else:
            self.qr_server.stop()
            self.qr_image_label.configure(image=None, text="QR no activo\nPresiona un botón abajo")
            self.qr_url_label.configure(text="")
            self.copy_url_btn.configure(state="disabled")
            self.qr_toggle_btn.configure(
                text="ACTIVAR LOCAL (Wi-Fi)",
                state="normal",
                fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            )
            self.zrok_btn.configure(state="normal", text="ACTIVAR REMOTO (Cualquier Red)", fg_color="#6B21A8")

    def _show_qr(self, img_qr, url):
        """Actualiza la UI con el QR usando CTkImage nativo de CustomTkinter."""
        try:
            from PIL import Image
            
            # 1. Convertir a PIL
            if hasattr(img_qr, "get_image"):
                pil_img = img_qr.get_image()
            else:
                pil_img = img_qr.convert("RGB") if hasattr(img_qr, "convert") else img_qr
            
            # 2. Redimensionar para CTkImage
            pil_img = pil_img.resize((280, 280), Image.Resampling.LANCZOS)

            # 3. Crear CTkImage nativo (evita warnings de CTkLabel)
            self.ctk_qr_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(280, 280))
            self.qr_image_label.configure(image=self.ctk_qr_img, text="")
            
            # 4. Actualizar URL y Botones
            self.qr_url_label.configure(text=str(url))
            self.copy_url_btn.configure(state="normal")
            self.qr_toggle_btn.configure(
                state="normal",
                text="DESACTIVAR SERVIDOR QR",
                fg_color="#A02020"
            )
            
            self.append_log(f"✅ QR actualizado en pantalla: {url}\n")
            
        except Exception as e:
            self.append_log(f"❌ Error al mostrar QR: {e}\n")
            import traceback
            print(traceback.format_exc())

    def setup_settings_frame(self):
        self.settings_frame.grid_columnconfigure(0, weight=1)
        
        # Título
        ctk.CTkLabel(self.settings_frame, text="Ajustes de la Aplicación", 
                     font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, pady=(30, 20))
        
        # Contenedor central
        container = ctk.CTkFrame(self.settings_frame)
        container.grid(row=1, column=0, padx=40, pady=10, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        # 1. Tema Visual
        ctk.CTkLabel(container, text="Apariencia de la Interfaz:", 
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, pady=(10, 5))
        
        self.theme_menu = ctk.CTkOptionMenu(container, values=["Dark", "Light", "System"], 
                                            width=300,
                                            command=self.change_appearance_mode_event)
        self.theme_menu.set(config.settings["general"].get("theme", "Dark").capitalize())
        self.theme_menu.grid(row=1, column=0, pady=(0, 20))
        
        # 2. Método de Sincro por defecto
        ctk.CTkLabel(container, text="Método de Sincronización Preferido:", 
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=2, column=0, pady=(10, 5))
        
        self.sync_method_menu = ctk.CTkOptionMenu(container, values=["SSH (Automático)", "QR (Manual)"], 
                                                 width=300,
                                                 command=self.change_sync_method)
        current_sync = config.settings["general"].get("sync_method", "SSH")
        self.sync_method_menu.set("SSH (Automático)" if current_sync == "SSH" else "QR (Manual)")
        self.sync_method_menu.grid(row=3, column=0, pady=(0, 20))

        # 3. Restauración de Respaldo del Motor
        ctk.CTkLabel(container, text="Respaldo y Deshacer Cambios:", 
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=4, column=0, pady=(10, 5))
        
        self.restore_btn = ctk.CTkButton(container, text="🔄 DESHACER / RESTAURAR MOTOR ANTERIOR", 
                                        width=300, fg_color="#A02020", hover_color="#801010",
                                        command=self.restore_previous_engine)
        self.restore_btn.grid(row=5, column=0, pady=(0, 30))

    def restore_previous_engine(self):
        try:
            import restaurar_respaldo
            ok = restaurar_respaldo.restore_backup()
            if ok:
                self.append_log("🔄 Motor de descarga restaurado a la versión anterior.\n")
            else:
                self.append_log("⚠️ No se encontraron archivos de respaldo previos para restaurar.\n")
        except Exception as e:
            self.append_log(f"❌ Error al restaurar respaldo: {e}\n")

    def change_sync_method(self, val):
        method = "SSH" if "SSH" in val else "QR"
        config.settings["general"]["sync_method"] = method
        config.save_settings()
        self.append_log(f"⚙️ Método de entrega cambiado a: {method}\n")

    def change_processing_mode(self, val):
        mode = "FULL" if "Completo" in val else "ONLY_DOWNLOAD"
        config.settings["general"]["processing_mode"] = mode
        config.save_settings()
        self.append_log(f"⚙️ Modo cambiado a: {val}\n")

    def setup_cleaner_frame(self):
        self.cleaner_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.cleaner_frame, text="Limpiador de Duplicados Inteligente", 
                     font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, pady=20)
        
        self.clean_desc = ctk.CTkLabel(self.cleaner_frame, text="Busca canciones repetidas en tu PC para ahorrar espacio en el móvil.\nUsa coincidencia por nombre y tamaño de archivo.", font=ctk.CTkFont(size=14))
        self.clean_desc.grid(row=1, column=0, pady=10)

        self.scan_dupes_btn = ctk.CTkButton(self.cleaner_frame, text="ESCANEAR BIBLIOTECA EN BUSCA DE DUPLICADOS", 
                                           height=50, command=self.run_duplicate_scan)
        self.scan_dupes_btn.grid(row=2, column=0, pady=20)

        self.dupes_scroll = ctk.CTkScrollableFrame(self.cleaner_frame, height=400)
        self.dupes_scroll.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

    def run_duplicate_scan(self):
        self.scan_dupes_btn.configure(state="disabled", text="ESCANEANDO...")
        
        def run():
            try:
                import duplicate_cleaner
                music_root = os.path.join(config.BASE_DIR, "canciones_auto")
                self.ui_call(self.append_log, f"🔍 Escaneando duplicados en: {music_root}\n")
                groups = duplicate_cleaner.find_duplicates(music_root)
                self.ui_call(self.display_duplicates, groups)
            except Exception as e:
                import traceback
                self.ui_call(self.append_log, f"❌ Error fatal en escaneo: {e}\n{traceback.format_exc()}\n")
            finally:
                self.ui_call(self.scan_dupes_btn.configure, state="normal", text="ESCANEAR BIBLIOTECA EN BUSCA DE DUPLICADOS")

        threading.Thread(target=run, daemon=True).start()

    def display_duplicates(self, groups):
        # Este método debe ser llamado vía ui_call, por lo tanto corre en el hilo principal
        for widget in self.dupes_scroll.winfo_children(): widget.destroy()
        
        if not groups:
            ctk.CTkLabel(self.dupes_scroll, text="¡Felicidades! No se han encontrado duplicados.", font=ctk.CTkFont(weight="bold")).pack(pady=20)
            return

        for group in groups:
            f = ctk.CTkFrame(self.dupes_scroll)
            f.pack(fill="x", padx=5, pady=10)
            
            ctk.CTkLabel(f, text=f"Grupo de Duplicados ({len(group)} archivos):", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=5)
            
            for item in group:
                row = ctk.CTkFrame(f, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=2)
                
                txt = f"{item['rel_path']} ({item['size']/1024/1024:.2f} MB)"
                ctk.CTkLabel(row, text=txt).pack(side="left")
                
                # Usamos una función lambda para el borrado
                path = item['path']
                btn = ctk.CTkButton(row, text="Eliminar", width=60, fg_color="#A02020", hover_color="#801010",
                                   command=lambda p=path, r=row: self.delete_file_ui(p, r))
                btn.pack(side="right")

    def delete_file_ui(self, path, row_widget):
        try:
            if os.path.exists(path):
                os.remove(path)
                row_widget.destroy()
                self.append_log(f"🗑️ Archivo eliminado: {os.path.basename(path)}\n")
        except Exception as e:
            self.append_log(f"❌ Error al borrar: {e}\n")

    def select_frame_by_name(self, name):
        buttons = {"home": self.home_button, "accounts": self.accounts_button, "devices": self.devices_button, "qr_sync": self.qr_sync_button, "cleaner": self.cleaner_button, "settings": self.settings_button}
        for k, b in buttons.items(): b.configure(fg_color=("gray75", "gray25") if k == name else "transparent")
        for f in [self.home_frame, self.accounts_frame, self.devices_frame, self.qr_sync_frame, self.cleaner_frame, self.settings_frame]: f.grid_forget()
        getattr(self, f"{name}_frame").grid(row=0, column=1, sticky="nsew")

    def home_button_event(self): self.select_frame_by_name("home")
    def accounts_button_event(self): self.select_frame_by_name("accounts")
    def devices_button_event(self): self.select_frame_by_name("devices")
    def qr_sync_button_event(self): self.select_frame_by_name("qr_sync")
    def cleaner_button_event(self): self.select_frame_by_name("cleaner")
    def settings_button_event(self): self.select_frame_by_name("settings")

    def change_appearance_mode_event(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        config.settings["general"]["theme"] = new_mode.lower()
        config.save_settings()

    def change_account(self, val):
        config.settings["active_profile"]["account"] = val
        config.save_settings()

    def change_device(self, val):
        config.settings["active_profile"]["device"] = val
        config.save_settings()

    def add_account_dialog(self):
        acc_id = ctk.CTkInputDialog(text="ID único (ej: personal):", title="Nueva Cuenta").get_input()
        if acc_id:
            name = ctk.CTkInputDialog(text="Nombre amigable:", title="Nueva Cuenta").get_input()
            config.add_account(acc_id, name or acc_id, f"spotify_session_{acc_id}", f"youtube_session_{acc_id}", f"oauth_{acc_id}.json")
            self.account_selector.configure(values=list(config.settings["accounts"].keys()))
            self.refresh_accounts_list()

    def add_device_dialog(self):
        dev_id = ctk.CTkInputDialog(text="ID único (ej: movil2):", title="Nuevo Dispositivo").get_input()
        if dev_id:
            ip = ctk.CTkInputDialog(text="Dirección IP:", title="Nuevo Dispositivo").get_input()
            config.add_device(dev_id, dev_id, "u0_a461", ip or "127.0.0.1", "8022", "~/Music-Downloader", "/storage/emulated/0/Music/music downloader movil")
            self.device_selector.configure(values=list(config.settings["devices"].keys()))
            self.refresh_devices_list()

    def process_ui_queue(self):
        while True:
            try:
                item = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            if len(item) == 2:
                fn, args = item
                kwargs = {}
            else:
                fn, args, kwargs = item
            fn(*args, **kwargs)
        self.after(100, self.process_ui_queue)

    def ui_call(self, fn, *args, **kwargs):
        self.ui_queue.put((fn, args, kwargs))

    def append_log(self, message):
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")

    def start_process(self, sync=True):
        self.stop_event.clear()
        self.dl_button.configure(state="disabled")
        self.sync_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        
        self.save_playlist_pref()

        def run():
            try:
                acc = config.get_active_account()
                pl_name = config.get_active_playlist()
                music_dir = config.get_music_dir()
                
                mode_txt = "Descarga + Sincro" if sync else "Solo Descarga (PC)"
                self.ui_call(self.append_log, f"🚀 Iniciando [{mode_txt}]: {pl_name}\n")
                
                if self.stop_event.is_set(): return
                
                # 1. Exportar CSV
                self.ui_call(self.append_log, f"🔍 Exportando CSV...\n")
                csv_path = os.path.join(config.BASE_DIR, "playlist.csv")
                run_exportify_bot(
                    target_playlist=pl_name,
                    user_data_dir=os.path.join(config.BASE_DIR, acc["spotify_session_dir"]),
                    output_path=csv_path
                )

                if not os.path.exists(csv_path):
                    self.ui_call(self.append_log, "❌ No se pudo obtener el CSV.\n")
                    return

                # 2. Descargar canciones
                remote_files = set()
                dev = config.get_active_device()
                if sync and config.settings["general"]["sync_method"] == "SSH":
                    self.ui_call(self.append_log, "📥 Conectando con móvil para evitar duplicados remotos...\n")
                    sync_engine = SyncEngine(dev, local_root=music_dir)
                    conn_ok, _ = sync_engine.check_connection()
                    if conn_ok:
                        remote_files = sync_engine.get_remote_files()

                dl = DownloadEngine(csv_path=csv_path, music_dir=music_dir)
                dl_res = dl.run(
                    progress_callback=lambda m: self.ui_call(self.append_log, f"   {m}\n"), 
                    remote_files=remote_files,
                    stop_event=self.stop_event
                )

                if not dl_res.get("success", False):
                    self.ui_call(self.append_log, "❌ Error en la fase de descarga.\n")
                    return

                # 3. Regenerar Playlists
                self.ui_call(self.append_log, "✨ Reconstruyendo Playlists...\n")
                playlist_generator.generate_playlists()

                # 4. Sincronización (Solo si se solicitó)
                if sync:
                    sync_method = config.settings["general"].get("sync_method", "SSH")
                    if sync_method == "SSH" and "SOLO PREPARAR" not in dev["name"].upper():
                        sync_engine = SyncEngine(dev, local_root=music_dir)
                        conn_ok, conn_err = sync_engine.check_connection()
                        if conn_ok:
                            self.ui_call(self.append_log, f"📡 Enviando archivos a {dev['name']}...\n")
                            sync_res = sync_engine.push_files()
                            if sync_res.get("success"):
                                self.ui_call(self.append_log, "✅ Sincronización terminada.\n")
                        else:
                            self.ui_call(self.append_log, f"⚠️ Error SSH: {conn_err}\n")
                
                self.ui_call(self.append_log, "🏁 Tarea completada.\n")

            except Exception as e:
                self.ui_call(self.append_log, f"❌ Error: {e}\n")
            finally: 
                self.ui_call(self.set_button_state_custom, "normal", "disabled")
        
        threading.Thread(target=run, daemon=True).start()

    def set_button_state_custom(self, btn_state, cancel_state):
        self.dl_button.configure(state=btn_state)
        self.sync_button.configure(state=btn_state)
        self.cancel_button.configure(state=cancel_state)

    def cancel_process(self):
        self.stop_event.set()
        self.append_log("\nSolicitando cancelación...\n")
        self.cancel_button.configure(state="disabled")

    def start_sync(self):
        # Eliminado, reemplazado por start_process
        pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
