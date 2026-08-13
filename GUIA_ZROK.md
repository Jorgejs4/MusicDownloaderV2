# 🚀 GUÍA DEFINITIVA: Sincronización Zrok (Modo Titanium)

Si has tenido errores 504, 505 o "Connection Refused", es porque el servidor de Zrok tiene sesiones "fantasmas" guardadas. Vamos a resetearlo todo con este método de **Purga Total**.

---

## 📱 PASO 1: Móvil (Termux) - El "Reset"

Cierra Termux y vuelve a abrirlo. Pega estos comandos por orden:

1.  **Matar fantasmas**:
    ```bash
    pkill -9 zrok
    ```
2.  **Habilitar cuenta (solo si daba error 401)**:
    ```bash
    zrok disable
    zrok enable TU_TOKEN_AQUI
    ```
3.  **Lanzar el túnel "Limpio" (ID Aleatorio)**:
    *Copia y pega exactamente esto:*
    ```bash
    zrok share private 127.0.0.1:8022 --backend-mode tcpTunnel --headless
    ```
4.  **Anota tu ID**:
    Verás que Zrok te da un ID de 12 letras (ejemplo: `v0x2a9z4w6m`). **Cópialo**. No cierres esta ventana de Termux.

---

## 💻 PASO 2: PC - El "Puente"

1.  Abre el archivo **`.env`** en la carpeta del proyecto.
2.  Actualiza estas dos líneas:
    ```env
    ZROK_SHARE_ID=pega_aqui_tu_id_de_12_letras
    SSH_PORT=8025
    ```
    *(Nota: Usamos el puerto 8025 para que no choque con nada anterior)*.
3.  Guarda el archivo.

---

## ⚡ PASO 3: Ejecución Final

Simplemente lanza el archivo **`Lanzar_Sincronizacion.bat`** en tu PC.

### ¿Qué debería pasar?
- El PC dirá `Iniciando túnel Zrok...`
- Pasará a `Verificando conexión...`. 
- Al tener un ID nuevo, debería conectar en el primer o segundo intento.
- Verás: `✅ Conexión Establecida`.
- Empezará la transferencia consolidada: `📦 Transfiriendo archivos...`.

---

## 🔄 PASO 4: Para el Futuro (Auto-arranque)

Una vez que compruebes que esto funciona, podemos editar tu `.bashrc` en el móvil para que use ese ID siempre, pero por ahora **¡vamos a probar la conexión!**

---
*Si algo falla, haz una captura de pantalla de la terminal azul de Zrok en el PC.*
