import os
import shutil
from core.paths import Paths

class LocalOps:

    @staticmethod
    def ensure_directory(destination_path):
        parent_directory = os.path.dirname(destination_path)
        if parent_directory:
            os.makedirs(parent_directory, exist_ok=True)

    @staticmethod
    def l2l(source_path, destination_path, move_mode=False):
        LocalOps.ensure_directory(destination_path)

        if os.path.isdir(source_path):
            if move_mode:
                return shutil.move(source_path, destination_path)
            
            return shutil.copytree(source_path, destination_path, dirs_exist_ok=True)

        if move_mode:
            return shutil.move(source_path, destination_path)
        return shutil.copy2(source_path, destination_path)

    @staticmethod
    def loc_del(file_path):
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)

    @staticmethod
    def loc_exists(file_path):
        return os.path.exists(file_path)

    @staticmethod
    def loc_list(directory_path, recursive=True):
        discovered_items = []
        if not os.path.exists(directory_path):
            return discovered_items

        if recursive:
            for root, _, files in os.walk(directory_path):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    discovered_items.append(Paths.clean(full_path))
        else:
            for entry in os.listdir(directory_path):
                full_path = os.path.join(directory_path, entry)
                discovered_items.append(Paths.clean(full_path))
        return discovered_items

    @staticmethod
    def loc_make_dir(directory_path):
        os.makedirs(directory_path, exist_ok=True)

    @staticmethod
    def loc_rename(source_path, destination_path):
        LocalOps.ensure_directory(destination_path)
        return os.rename(source_path, destination_path)