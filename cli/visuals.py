import os


class CLIVisuals:
    COLOR_ORANGE = "\033[38;2;255;140;0m"
    COLOR_YELLOW = "\033[38;2;255;200;0m"
    COLOR_BLUE = "\033[38;2;0;191;255m"
    COLOR_RESET = "\033[0m"

    @staticmethod
    def clear_screen():
        if os.name == "nt":
            os.system("cls")
        else:
            print("\033[2J\033[3J\033[H", end="", flush=True)

    @classmethod
    def print_banner(cls):
        c_org = cls.COLOR_ORANGE
        c_yel = cls.COLOR_YELLOW
        c_blu = cls.COLOR_BLUE
        rst = cls.COLOR_RESET

        banner = f"""
  {c_blu}███████╗██████╗ {c_org}██╗   ██╗██╗███████╗{c_yel}██╗    ██╗
  {c_blu}██╔════╝╚════██╗{c_org}██║   ██║██║██╔════╝{c_yel}██║    ██║
  {c_blu}███████╗ █████╔╝{c_org}██║   ██║██║█████╗  {c_yel}██║ █╗ ██║
  {c_blu}╚════██║ ╚═══██╗{c_org}╚██╗ ██╔╝██║██╔══╝  {c_yel}██║███╗██║
  {c_blu}███████║██████╔╝{c_org} ╚████╔╝ ██║███████╗{c_yel}╚███╔███╔╝
  {c_blu}╚══════╝╚═════╝ {c_org}  ╚═══╝  ╚═╝╚══════╝{c_yel} ╚══╝╚══╝ {rst}
        """
        print(banner)

    @staticmethod
    def print_simple_info():
        print("═" * 65)
        print(" S3VIEW COMMAND CENTER")
        print(" File : Commands.view (Stores custom command sequence)")
        print("═" * 65)

    @classmethod
    def print_error(cls, message):
        print("\n" + "!" * 65)
        print(f" {cls.COLOR_ORANGE}CRITICAL ERROR:{cls.COLOR_RESET}")
        print(f" {message}")
        print("!" * 65)
