import os
import shutil

ROOT_DIR = r"C:\Users\jorge\Desktop\proyectos\music downloader b3\canciones_auto"
# Moveremos todo de 'Adriana' a 'default' (o donde esté la versión completa)
SOURCE_USER = os.path.join(ROOT_DIR, "Adriana")
DEST_USER = os.path.join(ROOT_DIR, "default")

def merge_libraries():
    for root, dirs, files in os.walk(SOURCE_USER):
        for name in files:
            # Recrear estructura en DEST_USER
            rel_path = os.path.relpath(root, SOURCE_USER)
            target_dir = os.path.join(DEST_USER, rel_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            src_file = os.path.join(root, name)
            dst_file = os.path.join(target_dir, name)
            
            # Solo mover si no existe en destino
            if not os.path.exists(dst_file):
                shutil.move(src_file, dst_file)
            else:
                # Si existe, eliminar el de la carpeta 'Adriana' (es duplicado)
                os.remove(src_file)

    # Eliminar carpeta vacía
    shutil.rmtree(SOURCE_USER)
    print("Biblioteca fusionada con éxito.")

if __name__ == "__main__":
    merge_libraries()
