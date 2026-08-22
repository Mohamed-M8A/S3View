import os
import zipfile
import uuid
import shutil
from core.paths import Paths

class ArchiveOps:
    SPACE_BUFFER_FACTOR = 1.2

    @staticmethod
    def get_vault_path():
        vault_physical_path = Paths.resource_path("_sys/.vault")
        os.makedirs(vault_physical_path, exist_ok=True)
        return vault_physical_path

    @staticmethod
    def validate_space(required_bytes):
        vault_directory = ArchiveOps.get_vault_path()
        _, _, free_bytes = shutil.disk_usage(vault_directory)
        
        if free_bytes < (required_bytes * ArchiveOps.SPACE_BUFFER_FACTOR):
            return False
        return True

    @staticmethod
    def create_temp_archive():
        vault_directory = ArchiveOps.get_vault_path()
        unique_id = uuid.uuid4().hex[:8]
        return Paths.join(vault_directory, f"arch_{unique_id}.tmp")

    @staticmethod
    def add_to_zip(zip_handle, local_file_path, internal_archive_path):
        zip_handle.write(local_file_path, internal_archive_path)

    @staticmethod
    def finalize_zip(temporary_zip_path, final_destination_path, move_mode=True):
        os.makedirs(os.path.dirname(final_destination_path), exist_ok=True)
        
        if move_mode:
            shutil.move(temporary_zip_path, final_destination_path)
        else:
            shutil.copy2(temporary_zip_path, final_destination_path)
            
        return final_destination_path

    @staticmethod
    def compress_files(target_physical_path, file_registry_map, compression_level=6):
        with zipfile.ZipFile(target_physical_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zip_object:
            for physical_file, internal_name in file_registry_map.items():
                zip_object.write(physical_file, internal_name)