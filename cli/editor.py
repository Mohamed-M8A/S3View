import os

from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import Layout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings

from cli.visuals import CLIVisuals


class TerminalEditor:
    @staticmethod
    def open(path):
        initial_text = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                initial_text = f.read()

        text_area = TextArea(
            text=initial_text,
            multiline=True,
            line_numbers=True,
            scrollbar=True,
            focus_on_click=True
        )

        kb = KeyBindings()

        @kb.add("c-s")
        def save_and_exit(event):
            full_text = text_area.text
            with open(path, "w", encoding="utf-8") as f:
                f.write(full_text)
            event.app.exit(result=True)

        @kb.add("c-c")
        def cancel_and_exit(event):
            event.app.exit(result=False)

        CLIVisuals.clear_screen()
        print("=" * 65)
        print(" S3VIEW IN-TERMINAL LIVE EDITOR")
        print(" - Use Arrow Keys to navigate freely.")
        print(" - Press [Ctrl + S] to SAVE and return.")
        print(" - Press [Ctrl + C] to CANCEL and discard changes.")
        print("=" * 65 + "\n")

        layout = Layout(text_area)
        app = Application(layout=layout, key_bindings=kb, full_screen=False)
        return app.run()
