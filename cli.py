import sys

from cli.app import S3ViewCLI

if __name__ == "__main__":
    try:
        S3ViewCLI().run()
    except KeyboardInterrupt:
        sys.exit(0)
