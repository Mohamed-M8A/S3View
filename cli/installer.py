import sys
import os
import platform
import stat

from core.paths import Paths

from cli.visuals import CLIVisuals


class SystemInstaller:
    ALIASES = ("s3v", "s3view")

    @staticmethod
    def _target_bin_dir():
        raw_path = Paths.resource_path("_sys/cmd")
        if os.name == "nt":
            return os.path.normpath(raw_path)
        return raw_path

    @staticmethod
    def _is_frozen():
        return getattr(sys, "frozen", False) or "__compiled__" in globals()

    @classmethod
    def _launch_command(cls):
        if cls._is_frozen():
            return [os.path.abspath(sys.executable)]
        return [os.path.abspath(sys.executable), os.path.abspath(sys.argv[0])]

    @classmethod
    def _write_windows_wrapper(cls, bin_dir, alias):
        wrapper_path = os.path.join(bin_dir, f"{alias}.cmd")
        command_parts = " ".join(f'"{part}"' for part in cls._launch_command())
        content = f"@echo off\r\n{command_parts} %*\r\n"
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(content)
        return wrapper_path

    @classmethod
    def _write_unix_wrapper(cls, bin_dir, alias):
        wrapper_path = os.path.join(bin_dir, alias)
        command_parts = " ".join(f'"{part}"' for part in cls._launch_command())
        content = f'#!/usr/bin/env bash\n{command_parts} "$@"\n'
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(content)
        st = os.stat(wrapper_path)
        os.chmod(wrapper_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return wrapper_path

    @staticmethod
    def _is_dir_in_path(target_dir):
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        normalized = [os.path.normcase(os.path.normpath(p)) for p in path_entries]
        return os.path.normcase(os.path.normpath(target_dir)) in normalized

    @classmethod
    def _suggest_unix_path_update(cls, bin_dir):
        shell = os.environ.get("SHELL", "")
        profile_file = ".bashrc"
        if "zsh" in shell:
            profile_file = ".zshrc"

        profile_path = os.path.join(os.path.expanduser("~"), profile_file)
        export_line = f'export PATH="$PATH:{bin_dir}"'

        print(f"\n{CLIVisuals.COLOR_YELLOW}[!] '{bin_dir}' is not in your PATH.{CLIVisuals.COLOR_RESET}")
        confirm = input(f" Add it to {profile_path} now? (y/n): ").strip().lower()
        if confirm != "y":
            print(f"[*] You can add it manually later with:\n    {export_line}")
            return

        try:
            with open(profile_path, "a", encoding="utf-8") as f:
                f.write(f"\n{export_line}\n")
            print(f"[+] PATH updated in {profile_path}. Restart your terminal to apply.")
        except OSError as exc:
            CLIVisuals.print_error(f"Failed to update {profile_path}: {exc}")

    @staticmethod
    def _suggest_windows_path_update(bin_dir):
        registry_entry = bin_dir if bin_dir.endswith(os.sep) else bin_dir + os.sep

        print(f"\n{CLIVisuals.COLOR_YELLOW}[!] '{bin_dir}' is not in your PATH.{CLIVisuals.COLOR_RESET}")
        confirm = input(" Add it to your user PATH now? (y/n): ").strip().lower()
        if confirm != "y":
            print(f"[*] You can add it manually via System Properties > Environment Variables.")
            return

        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                try:
                    current_path, _ = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    current_path = ""
                new_path = f"{current_path};{registry_entry}" if current_path else registry_entry
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print("[+] PATH updated. Restart your terminal to apply.")
        except Exception as exc:
            CLIVisuals.print_error(f"Failed to update PATH: {exc}")

    @classmethod
    def install(cls):
        print(f"\n{CLIVisuals.COLOR_BLUE}[*] S3View: Self-Installation{CLIVisuals.COLOR_RESET}")
        mode_label = "Compiled Executable" if cls._is_frozen() else "Python Script"
        print(f"[*] Detected run mode: {mode_label}")
        system_name = platform.system()
        bin_dir = cls._target_bin_dir()

        try:
            os.makedirs(bin_dir, exist_ok=True)
        except OSError as exc:
            CLIVisuals.print_error(f"Could not create install directory '{bin_dir}': {exc}")
            return

        wrapper_paths = []
        try:
            for alias in cls.ALIASES:
                if system_name == "Windows":
                    wrapper_paths.append(cls._write_windows_wrapper(bin_dir, alias))
                else:
                    wrapper_paths.append(cls._write_unix_wrapper(bin_dir, alias))
        except OSError as exc:
            CLIVisuals.print_error(f"Failed to write wrapper script: {exc}")
            return

        print("[+] Wrappers created:")
        for wrapper_path in wrapper_paths:
            print(f"    - {wrapper_path}")

        if cls._is_dir_in_path(bin_dir):
            alias_list = ", ".join(cls.ALIASES)
            print(f"[+] Install directory is already in PATH. You can run {alias_list} from anywhere.")
            return

        if system_name == "Windows":
            cls._suggest_windows_path_update(bin_dir)
        else:
            cls._suggest_unix_path_update(bin_dir)
