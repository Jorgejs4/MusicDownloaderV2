import os
import shutil
import re

ROOT_DIR = r"C:\Users\jorge\Desktop\proyectos\music downloader b3\canciones_auto"

def get_primary_artist(artist_folder):
    # Split by comma and take the first part
    parts = artist_folder.split(',')
    return parts[0].strip()

def organize_library():
    for root, dirs, files in os.walk(ROOT_DIR):
        # Only process artist folders, which are typically children of a user/profile folder like 'Adriana' or 'default'
        # Skip playlist folders
        if "_Playlists" in root:
            continue

        # Look for folders containing commas, signifying multiple artists
        parent_dir = os.path.dirname(root)
        folder_name = os.path.basename(root)
        
        if ',' in folder_name:
            primary_artist = get_primary_artist(folder_name)
            target_parent = os.path.join(parent_dir, primary_artist)
            
            if not os.path.exists(target_parent):
                os.makedirs(target_parent)
            
            # Move contents of the composite folder to the primary artist folder
            target_dir = os.path.join(target_parent, folder_name)
            if not os.path.exists(target_dir):
                shutil.move(root, target_dir)
                print(f"Moved {folder_name} to {target_dir}")
            else:
                # Merge if folder exists
                for file in files:
                    src = os.path.join(root, file)
                    dst = os.path.join(target_dir, file)
                    shutil.move(src, dst)
                os.rmdir(root)
                print(f"Merged {folder_name} into {target_dir}")

if __name__ == "__main__":
    organize_library()
