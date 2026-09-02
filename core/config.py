"""
core/config.py -- reads and writes settings.json/credentials.json plus the
OS keyring, and exposes the merged result as one flat dict via
load_config()/save_config().

Caching (added 2026-08-30 session): load_config() previously re-read both
JSON files and re-queried the OS keyring on every single call -- 5 file
reads and 30 keyring round-trips measured for one single-line CLI command.
It now keeps a per-process in-memory cache (_CONFIG_CACHE), but the cache
is only ever trusted after a cheap os.stat() confirms neither file's mtime
has changed since it was filled. This matters specifically because the
user can change credentials or settings mid-session (switching AWS
accounts via the interactive --config menu, or hand-editing
credentials.json while S3View's interactive menu is still open) -- a cache
with no invalidation would keep serving the old account's keys after that.
The mtime check costs two stat() syscalls versus a full JSON parse plus up
to 6 keyring round-trips, so the fast path stays fast while any real
change -- from this process via save_config(), or from anything else --
is picked up on the very next load_config() call. save_config() also
invalidates the cache explicitly and unconditionally (even on partial
write failure), because filesystem mtime resolution is only 1-second
granular on some filesystems -- a save() immediately followed by a
load() within the same second could otherwise be missed by mtime
comparison alone.
"""

import json
import os
import time
import keyring
from core.paths import Paths

DEFAULT_SETTINGS = {
    "GENERAL": {
        "DRY_RUN": False,
        "MAX_WORKERS": 15,
        "RAM_LIMIT_MB": 200,
        "VAULT_CLEANUP": True,
        "LOCAL_WORKERS": 4,
        "TASK_TIMEOUT_SECONDS": 300,
        "HTTP_LOG_MAX_ENTRIES": 1000,
        "BUFFER_RAM_MB": 40,
        "CUSTOM_DOMAIN": "",
        "UI_THEME": "theme-01-obsidian"
    },
    "REPORTS": {
        "ENABLE_REPORTS": True,
        "REPORT_HTML": True,
        "REPORT_TSV": True,
        "REPORT_JSON": True,
        "REPORT_SQLITE": False,
        "REPORT_DUCKDB": False,
        "REPORT_NETWORK": False,
        "SHARE_FORMAT_HTML": True,
        "SHARE_FORMAT_JSON": False,
        "SHARE_FORMAT_TXT": False,
        "SHARE_INCLUDE_ORIGINAL_URL": False
    }
}

DEFAULT_CREDS = {
    "USE_KEYRING": True,
    "PROVIDER": "",
    "REGION": "",
    "ACCOUNT_ID": "",
    "ACCESS_KEY": "",
    "SECRET_KEY": "",
    "S3_ENDPOINT": ""
}

GENERAL_BOOL_KEYS = ("DRY_RUN", "VAULT_CLEANUP")
GENERAL_INT_KEYS = ("MAX_WORKERS", "RAM_LIMIT_MB", "LOCAL_WORKERS", "TASK_TIMEOUT_SECONDS", "HTTP_LOG_MAX_ENTRIES", "BUFFER_RAM_MB")
REPORTS_BOOL_KEYS = ("ENABLE_REPORTS", "REPORT_HTML", "REPORT_TSV", "REPORT_JSON", "REPORT_SQLITE", "REPORT_DUCKDB", "REPORT_NETWORK", "SHARE_FORMAT_HTML", "SHARE_FORMAT_JSON", "SHARE_FORMAT_TXT", "SHARE_INCLUDE_ORIGINAL_URL")

_CONFIG_CACHE = {"data": None, "signature": None}


def get_full_path(filename):
    root_directory = Paths.get_root_path()
    physical_path = os.path.join(root_directory, "WORKSPACE/CONFIG", filename)
    return os.path.normpath(physical_path).replace("\\", "/")


def _read_json_file(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as file_handle:
            return json.load(file_handle)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json_file(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=4)
    except OSError:
        pass


def _to_bool(value):
    return value.lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)


def _normalize_configuration(nested_data):
    general = nested_data.get("GENERAL", {})
    for key in GENERAL_BOOL_KEYS:
        if key in general:
            general[key] = _to_bool(general[key])

    for key in GENERAL_INT_KEYS:
        if key in general:
            try:
                general[key] = int(general[key])
            except (ValueError, TypeError):
                general[key] = DEFAULT_SETTINGS["GENERAL"].get(key, 0)

    nested_data["GENERAL"] = general

    reports = nested_data.get("REPORTS", {})
    for key in REPORTS_BOOL_KEYS:
        if key in reports:
            reports[key] = _to_bool(reports[key])

    nested_data["REPORTS"] = reports

    return nested_data


def _flatten_settings(nested_data):
    general = nested_data.get("GENERAL", {})
    reports = nested_data.get("REPORTS", {})
    return {**general, **reports}


def _repair_and_load(filename, default_structure):
    physical_path = get_full_path(filename)
    loaded_data = _read_json_file(physical_path)

    if loaded_data is None:
        _write_json_file(physical_path, default_structure)
        return dict(default_structure)

    needs_repair = False
    for section, content in default_structure.items():
        if section not in loaded_data:
            loaded_data[section] = content
            needs_repair = True
        elif isinstance(content, dict):
            for sub_key, sub_val in content.items():
                if sub_key not in loaded_data[section]:
                    loaded_data[section][sub_key] = sub_val
                    needs_repair = True

    if needs_repair:
        _write_json_file(physical_path, loaded_data)

    return loaded_data


def load_config():
    settings_path = get_full_path("settings.json")
    credentials_path = get_full_path("credentials.json")
    current_signature = (_safe_mtime(settings_path), _safe_mtime(credentials_path))

    if _CONFIG_CACHE["data"] is not None and _CONFIG_CACHE["signature"] == current_signature:
        return dict(_CONFIG_CACHE["data"])

    unified_configuration = _load_config_uncached(settings_path, credentials_path)

    fresh_signature = (_safe_mtime(settings_path), _safe_mtime(credentials_path))
    _CONFIG_CACHE["data"] = dict(unified_configuration)
    _CONFIG_CACHE["signature"] = fresh_signature

    return unified_configuration


def _safe_mtime(path):
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def _load_config_uncached(settings_path, credentials_path):
    system_settings = _repair_and_load("settings.json", DEFAULT_SETTINGS)
    cloud_credentials = _repair_and_load("credentials.json", DEFAULT_CREDS)

    use_keyring = _to_bool(cloud_credentials.get("USE_KEYRING", True))

    resolved_credentials = {"USE_KEYRING": use_keyring}
    for key in DEFAULT_CREDS:
        if key == "USE_KEYRING":
            continue

        env_val = os.getenv(f"S3V_{key}")
        if env_val:
            resolved_credentials[key] = env_val
            continue

        if use_keyring:
            try:
                vault_val = keyring.get_password("S3View", key)
                if vault_val:
                    resolved_credentials[key] = vault_val
                    continue
            except Exception:
                pass

        resolved_credentials[key] = cloud_credentials.get(key, "")

    system_settings = _normalize_configuration(system_settings)
    flat_settings = _flatten_settings(system_settings)

    return {**flat_settings, **resolved_credentials}


def save_config(unified_dictionary):
    from core.report import Reporting

    settings_path = get_full_path("settings.json")
    credentials_path = get_full_path("credentials.json")

    settings_data = {
        "GENERAL": {k: unified_dictionary[k] for k in DEFAULT_SETTINGS["GENERAL"] if k in unified_dictionary},
        "REPORTS": {k: unified_dictionary[k] for k in DEFAULT_SETTINGS["REPORTS"] if k in unified_dictionary}
    }

    use_keyring = _to_bool(unified_dictionary.get("USE_KEYRING", True))

    credentials_data = {k: unified_dictionary[k] for k in DEFAULT_CREDS if k in unified_dictionary}
    credentials_data["USE_KEYRING"] = use_keyring

    warnings = []

    try:
        _write_json_file(settings_path, settings_data)

        secret_fields = [k for k in DEFAULT_CREDS if k != "USE_KEYRING"]

        if use_keyring:
            for key in secret_fields:
                if key in unified_dictionary and unified_dictionary[key]:
                    try:
                        keyring.set_password("S3View", key, str(unified_dictionary[key]))
                        credentials_data[key] = ""
                    except Exception as exc:
                        credentials_data[key] = unified_dictionary[key]
                        warnings.append(f"Could not store '{key}' in OS keyring ({exc}); saved in credentials.json instead.")

        _write_json_file(credentials_path, credentials_data)

    except Exception as exc:
        Reporting.save_error_log(str(exc), "CONFIG_PERSISTENCE")
        raise Exception(f"CRITICAL: Configuration write failure -> {exc}")
    finally:
        _CONFIG_CACHE["data"] = None
        _CONFIG_CACHE["signature"] = None

    return warnings


def get_credentials():
    return load_config()