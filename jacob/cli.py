"""Command-line interface for Jacob."""

import argparse

from jacob import __version__


def main():
    parser = argparse.ArgumentParser(description="Jacob")
    parser.add_argument("--version", action="version", version=f"jacob {__version__}")
    args = parser.parse_args()
    print("Hello from Jacob!")


if __name__ == "__main__":
    main()
