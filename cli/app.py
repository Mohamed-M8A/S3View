import sys
import os
import time
import argparse

from core.main import run_logic_pipeline, boot_system
from core.paths import Paths
from core import config

from cli.visuals import CLIVisuals
from cli.editor import TerminalEditor
from cli.credentials import CredentialManager
from cli.installer import SystemInstaller


class S3ViewCLI:
    def __init__(self):
        self.commands_path = None

    def _get_file_info(self):
        if not os.path.exists(self.commands_path):
            return 0, 0, ""

        size_bytes = os.path.getsize(self.commands_path)
        with open(self.commands_path, "r", encoding="utf-8-sig") as f:
            content = f.read().strip()

        lines_count = len(content.splitlines()) if content else 0
        return size_bytes, lines_count, content

    def _run_pipeline(self, is_dry):
        curr_conf = config.load_config()
        curr_conf["DRY_RUN"] = is_dry
        config.save_config(curr_conf)

        mode_label = "DRY RUN (Simulation)" if is_dry else "LIVE EXECUTION"
        print("\n" + "═" * 65)
        print(f" Running Pipeline: [{mode_label}]")
        print("═" * 65 + "\n")

        result = run_logic_pipeline(is_cli=True)

        if result and "error" in result:
            CLIVisuals.print_error(result["error"])

        return result

    def _run_pipeline_interactive(self, is_dry):
        self._run_pipeline(is_dry)
        print("\n" + "═" * 65)
        input(" Done. Press ENTER to return to main menu...")

    def _run_pipeline_and_exit(self, is_dry):
        result = self._run_pipeline(is_dry)
        sys.exit(1 if result and "error" in result else 0)

    def _open_menu(self):
        while True:
            CLIVisuals.clear_screen()
            CLIVisuals.print_banner()
            CLIVisuals.print_simple_info()

            size_bytes, lines_count, content = self._get_file_info()

            print("\n--- FILE METRICS " + "-" * 48)
            if os.path.exists(self.commands_path):
                print(f" Status: Active | Total Lines: {lines_count} | Size: {size_bytes} Bytes")
            else:
                print(" Status: [File Not Found] | Lines: 0")

            print("\n--- ACTIVE COMMANDS " + "-" * 45)
            if content:
                for idx, line in enumerate(content.splitlines(), 1):
                    print(f" {idx:02d} | {line}")
            else:
                print(" [Empty File - No commands configured]")
            print("-" * 65)

            print("\n SELECT ACTION:")
            print("  [1] RUN DRY     (Simulation Mode)")
            print("  [2] RUN LIVE    (Real Execution)")
            print("  [3] EDIT FILE   (In-Terminal Editor)")
            print("  [4] RECONFIGURE (Update Keys)")
            print("  [5] RESET VAULT (Clear All Keys)")
            print("  [6] INSTALL     (Add s3v / s3view to PATH)")
            print("  [0] EXIT")
            print("═" * 65)

            choice = input(" --> Select [0-6]: ").strip()

            if choice == "1":
                self._run_pipeline_interactive(is_dry=True)
            elif choice == "2":
                self._run_pipeline_interactive(is_dry=False)
            elif choice == "3":
                TerminalEditor.open(self.commands_path)
            elif choice == "4":
                CredentialManager.configure()
                time.sleep(1)
            elif choice == "5":
                CredentialManager.reset_vault()
                time.sleep(1)
            elif choice == "6":
                SystemInstaller.install()
                time.sleep(1)
            elif choice == "0":
                sys.exit(0)

    @staticmethod
    def _build_parser():
        parser = argparse.ArgumentParser(prog="s3v", description="S3View Enterprise CLI")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--dry", "--test", "--dry-run", dest="dry_run", action="store_true")
        group.add_argument("--now", "--run", "-y", dest="live_run", action="store_true")
        group.add_argument("--config", dest="do_config", action="store_true")
        group.add_argument("--reset", dest="do_reset", action="store_true")
        group.add_argument("--install", dest="do_install", action="store_true")
        return parser

    def run(self):
        boot_system()
        self.commands_path = Paths.resource_path("WORKSPACE/Commands.view")

        parser = self._build_parser()
        args = parser.parse_args()

        if args.do_reset:
            CredentialManager.reset_vault()
            return

        if args.do_config:
            CredentialManager.configure()
            return

        if args.do_install:
            SystemInstaller.install()
            return

        if args.dry_run:
            self._run_pipeline_and_exit(is_dry=True)
            return

        if args.live_run:
            self._run_pipeline_and_exit(is_dry=False)
            return

        self._open_menu()
