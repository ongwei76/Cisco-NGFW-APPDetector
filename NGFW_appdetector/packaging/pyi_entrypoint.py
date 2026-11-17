"""PyInstaller entrypoint for ngfw-appdetector.

Loads the Typer app through package imports so relative imports resolve correctly.
"""

from ngfw_appdetector.cli import app

if __name__ == "__main__":
    app()
