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

from typing import Optional

def get_ffmpeg_path() -> Optional[str]:
    """ Return path to bundled ffmpeg executable folder or system fallback """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    paths_to_check = [
        os.path.join(base_path, "_internal", "bin"),
        os.path.join(base_path, "bin"),
        os.path.join(base_path, "libraries bin"),
        os.path.join(os.path.abspath("."), "libraries bin")
    ]
    
    for p in paths_to_check:
        if os.path.exists(os.path.join(p, "ffmpeg.exe")) or os.path.exists(os.path.join(p, "ffmpeg")):
            return p
            
    # Fallback to None so yt-dlp uses its default PATH search
    return None

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
