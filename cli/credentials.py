import getpass
import keyring

from core import config
from core.config import DEFAULT_CREDS, save_config
from core.cloud.providers import list_providers, get_provider

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
            if key == "USE_KEYRING":
                continue
            try:
                keyring.delete_password(cls.VAULT_NAME, key)
            except keyring.errors.PasswordDeleteError:
                pass
            except Exception as exc:
                print(f"[!] Could not remove '{key}': {exc}")

        print("[+] Vault cleared successfully.")

    @staticmethod
    def _select_provider(current_provider_id):
        providers = list_providers()
        print("\n Available Providers:")
        for index, provider in enumerate(providers, 1):
            marker = "  <- current" if provider.id == current_provider_id else ""
            region_note = "region required" if provider.region_required else "region optional"
            print(f"  [{index:>2}] {provider.display_name} ({region_note}){marker}")

        choice = input(" > Select Provider (number, Enter to keep current): ").strip()
        if not choice:
            return get_provider(current_provider_id)

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(providers):
                raise ValueError
            return providers[index]
        except ValueError:
            print(" [!] Invalid selection, keeping previous provider.")
            return get_provider(current_provider_id)

    @staticmethod
    def _prompt_optional(label, current_value):
        suffix = f" (current: {current_value})" if current_value else ""
        raw_input_value = input(f" > Enter {label}{suffix}, Enter to keep: ").strip()
        return raw_input_value if raw_input_value else current_value

    @staticmethod
    def _prompt_required(label):
        while True:
            raw_input_value = input(f" > Enter {label} (required): ").strip()
            if raw_input_value:
                return raw_input_value
            print(" [!] This field is required and cannot be empty.")

    @staticmethod
    def configure():
        print(f"\n{CLIVisuals.COLOR_BLUE}[*] S3View: Configuration Mode{CLIVisuals.COLOR_RESET}")
        new_settings = config.load_config()

        selected_provider = CredentialManager._select_provider(new_settings.get("PROVIDER", ""))
        new_settings["PROVIDER"] = selected_provider.id

        new_settings["ACCOUNT_ID"] = CredentialManager._prompt_optional("Account ID", new_settings.get("ACCOUNT_ID", ""))

        access_key_input = input(" > Enter Access Key (Enter to keep current): ").strip()
        if access_key_input:
            new_settings["ACCESS_KEY"] = access_key_input

        secret_key_input = getpass.getpass(" > Enter Secret Key (hidden, Enter to keep current): ").strip()
        if secret_key_input:
            new_settings["SECRET_KEY"] = secret_key_input

        if not new_settings.get("ACCESS_KEY") or not new_settings.get("SECRET_KEY"):
            print(" [!] Access Key and Secret Key are required and were not previously set.")
            if not new_settings.get("ACCESS_KEY"):
                new_settings["ACCESS_KEY"] = CredentialManager._prompt_required("Access Key")
            if not new_settings.get("SECRET_KEY"):
                new_settings["SECRET_KEY"] = getpass.getpass(" > Enter Secret Key (required, hidden): ").strip()

        if selected_provider.region_required:
            current_region = new_settings.get("REGION", "")
            if current_region:
                new_settings["REGION"] = CredentialManager._prompt_optional(
                    f"Region (required for {selected_provider.display_name})", current_region
                )
            else:
                new_settings["REGION"] = CredentialManager._prompt_required(
                    f"Region (required for {selected_provider.display_name})"
                )
        else:
            region_input = input(
                f" > Enter Region (optional for {selected_provider.display_name}, Enter to skip/keep): "
            ).strip()
            if region_input:
                new_settings["REGION"] = region_input

        new_settings["S3_ENDPOINT"] = CredentialManager._prompt_optional("S3 Endpoint", new_settings.get("S3_ENDPOINT", ""))

        current_use_keyring = bool(new_settings.get("USE_KEYRING", True))
        default_hint = "Y/n" if current_use_keyring else "y/N"
        keyring_input = input(
            f" > Store secrets in OS keyring instead of plain JSON? ({default_hint}): "
        ).strip().lower()
        if keyring_input in ("y", "yes"):
            new_settings["USE_KEYRING"] = True
        elif keyring_input in ("n", "no"):
            new_settings["USE_KEYRING"] = False
        else:
            new_settings["USE_KEYRING"] = current_use_keyring

        try:
            warnings = save_config(new_settings)
            for warning in warnings:
                print(f"{CLIVisuals.COLOR_ORANGE}[!] {warning}{CLIVisuals.COLOR_RESET}")

            if new_settings["USE_KEYRING"]:
                print("[+] Configuration updated. Secrets stored in the OS keyring where possible.")
            else:
                print("[+] Configuration updated. Secrets stored in plain text in credentials.json.")
        except Exception as exc:
            print(f"[-] Failed to save credentials: {exc}")
