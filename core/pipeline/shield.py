import os
import re
from core.config import get_full_path
from core.paths import Paths

class Shield:
    WINDOWS_SENSITIVE_SUBPATHS = [
        "/WINDOWS", "/WINDOWS/SYSTEM32", "/WINDOWS/SYSWOW64",
        "/WINDOWS/DRIVERS", "/WINDOWS/SYSTEM", "/WINDOWS/INF",
        "/USERS", "/USERS/PUBLIC", "/PROGRAM FILES",
        "/PROGRAM FILES (X86)", "/PROGRAMDATA", "/BOOT",
        "/RECOVERY", "/PERFLOGS", "/SYSTEM VOLUME INFORMATION",
        "/$RECYCLE.BIN"
    ]

    WINDOWS_SENSITIVE_FILES = [
        "/PAGEFILE.SYS", "/HIBERFIL.SYS", "/SWAPFILE.SYS",
        "/CONFIG.SYS", "/AUTOEXEC.BAT"
    ]

    SENSITIVE_LINUX_PATHS = [
        "/etc", "/boot", "/dev", "/proc", "/sys", "/bin", "/sbin",
        "/root", "/lib", "/lib64", "/usr", "/usr/bin", "/usr/sbin",
        "/usr/lib", "/usr/local/bin", "/usr/local/sbin", "/var",
        "/var/log", "/var/run", "/var/spool", "/opt", "/mnt",
        "/media", "/srv", "/run", "/lost+found"
    ]

    GENERIC_DANGEROUS_FOLDER_NAMES = [
        "$RECYCLE.BIN", 
        "SYSTEM VOLUME INFORMATION", 
        "RECYCLER"
    ]

    _CACHE = None

    @staticmethod
    def _strip_drive_letter(path):
        match = re.match(r"^[A-Z]:(.*)$", path, re.I)
        return match.group(1) if match else path

    @staticmethod
    def _is_windows_system_forbidden(path):
        normalized_path = path.upper()
        path_without_drive = Shield._strip_drive_letter(normalized_path)
        
        if not path_without_drive: 
            return False
            
        if path_without_drive in Shield.WINDOWS_SENSITIVE_FILES: 
            return True
            
        return any(
            path_without_drive == p or path_without_drive.startswith(p + "/") 
            for p in Shield.WINDOWS_SENSITIVE_SUBPATHS
        )

    @staticmethod
    def _is_linux_system_forbidden(path):
        return any(
            path == p or path.startswith(p + "/") 
            for p in Shield.SENSITIVE_LINUX_PATHS
        )

    @staticmethod
    def load_protected_list(force_reload=False):
        if Shield._CACHE is not None and not force_reload:
            return Shield._CACHE
        
        protected_entries = []
        vshield_file_path = get_full_path("Protected.vshield")
        
        if os.path.exists(vshield_file_path):
            try:
                with open(vshield_file_path, "r", encoding="utf-8-sig") as file:
                    for line in file:
                        stripped_line = line.strip()
                        if stripped_line.startswith('"') and stripped_line.endswith('"'):
                            raw_path = stripped_line[1:-1]
                            if raw_path:
                                protected_entries.append(Paths.clean(raw_path))
            except:
                pass
                
        Shield._CACHE = list(set(protected_entries))
        return Shield._CACHE

    @staticmethod
    def is_allowed(path_object, exclusions=None, protected_list=None):
        payload = getattr(path_object, "payload", None) or path_object.get("payload", "")
        current_payload = Paths.clean(payload)
        
        if not current_payload: 
            return False

        is_windows_env = (os.name == 'nt')
        path_segments = current_payload.split("/")
        base_filename = path_segments[-1]
        
        def normalize_for_comparison(value):
            return value.upper() if is_windows_env else value
        
        subject_payload = normalize_for_comparison(current_payload)
        subject_filename = normalize_for_comparison(base_filename)
        subject_segments = [normalize_for_comparison(s) for s in path_segments]

        for exclusion in (exclusions or []):
            norm_excl = normalize_for_comparison(Paths.clean(exclusion).strip("/"))
            if norm_excl in (subject_payload, subject_filename) or norm_excl in subject_segments:
                return False

        upper_segments = [s.upper() for s in path_segments]
        for danger_name in Shield.GENERIC_DANGEROUS_FOLDER_NAMES:
            if danger_name.upper() in upper_segments:
                return False

        if is_windows_env:
            if Shield._is_windows_system_forbidden(current_payload): 
                return False
        else:
            if Shield._is_linux_system_forbidden(current_payload): 
                return False

        for protected_path in (protected_list or []):
            norm_protected = normalize_for_comparison(protected_path)
            
            is_exact_match = (subject_payload == norm_protected)
            is_child_path = subject_payload.startswith(norm_protected + "/")
            is_parent_path = norm_protected.startswith(subject_payload + "/")
            
            if is_exact_match or is_child_path or is_parent_path:
                return False

        return True