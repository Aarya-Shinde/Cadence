# src/utils/paths.py
"""Single source of truth for all runtime file/folder paths.

Every module imports from here — no more scattered "music_player.db" literals.
"""

from pathlib import Path
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running from normal Python script
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# All data files sit next to the working directory (where main.py is run from).
# Change this one constant to relocate everything.
_BASE = Path(os.path.abspath("."))

def get_ffmpeg_path() -> str:
    """ Return path to bundled ffmpeg executable folder """
    # We bundle ffmpeg into a 'bin' folder inside the EXE
    return resource_path("bin")

DB_PATH          = str(_BASE / "cadence.db")          # SQLite: songs + lyrics + album_art
CONFIG_PATH      = str(_BASE / "cadence_config.json") # User settings
LOG_FILE         = "cadence.log"                       # RotatingFileHandler filename
LOG_DIR          = str(_BASE / "logs")                 # Log directory
def get_album_art_dir() -> str:
    from utils.config import get_config
    base = Path(get_config().get('music_folder', _BASE))
    return str(base / ".album_art_cache")

def get_lyrics_dir() -> str:
    from utils.config import get_config
    base = Path(get_config().get('music_folder', _BASE))
    return str(base / ".lyrics")
