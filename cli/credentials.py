import getpass
import keyring

from core import config
from core.config import DEFAULT_CREDS, save_config

from cli.visuals import CLIVisuals


class CredentialManager:
    VAULT_NAME = "S3View"

    @classmethod
    def reset_vault(cls):
        print(f"\n{CLIVisuals.COLOR_ORANGE}[!] WARNING: This will clear all stored credentials from the system vault.{CLIVisuals.COLOR_RESET}")
        confirm = input(" Are you sure? (y/n): ").strip().lower()
        if confirm != "y":
            print("[*] Operation cancelled.")
            return

        for key in DEFAULT_CREDS:
            try:
                keyring.delete_password(cls.VAULT_NAME, key)
            except keyring.errors.PasswordDeleteError:
                pass
            except Exception as exc:
                print(f"[!] Could not remove '{key}': {exc}")

        print("[+] Vault cleared successfully.")

    @staticmethod
    def configure():
        print(f"\n{CLIVisuals.COLOR_BLUE}[*] S3View: Configuration Mode{CLIVisuals.COLOR_RESET}")
        new_settings = config.load_config()
        new_settings["ACCOUNT_ID"] = input(" > Enter Account ID (Optional): ").strip()
        new_settings["ACCESS_KEY"] = input(" > Enter Access Key: ").strip()
        new_settings["SECRET_KEY"] = getpass.getpass(" > Enter Secret Key (hidden): ").strip()
        new_settings["S3_ENDPOINT"] = input(" > Enter S3 Endpoint (Optional): ").strip()
        save_config(new_settings)
        print("[+] Configuration updated and secured.")
