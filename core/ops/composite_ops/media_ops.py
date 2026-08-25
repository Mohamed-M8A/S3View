import shutil
from PIL import Image
from core.paths import Paths
from core.report import Reporting

class MediaOps:
    SPACE_BUFFER_FACTOR = 2.2

    @staticmethod
    def validate_space(required_bytes):
        base_path = Paths.get_root_path()
        _, _, free_bytes = shutil.disk_usage(base_path)
        return free_bytes > (required_bytes * MediaOps.SPACE_BUFFER_FACTOR)

    @staticmethod
    def transform(source_physical_path, target_physical_path, target_format, quality=80, extra_parameters=None):
        try:
            clamped_quality = max(1, min(100, int(quality)))
            
            with Image.open(source_physical_path) as image_object:
                if image_object.mode in ("RGBA", "P") and target_format in ("JPEG", "JPG"):
                    image_object = image_object.convert("RGB")
                
                save_settings = {"quality": clamped_quality} if target_format in ("JPEG", "JPG", "WEBP") else {}
                
                if extra_parameters:
                    save_settings.update(extra_parameters)
                
                image_object.save(target_physical_path, target_format, **save_settings)
                return True
                
        except Exception as exc:
            Reporting.save_error_log(str(exc), "MEDIA_TRANSFORM_FAILURE")
            return False