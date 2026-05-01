# src/utils/paths.py
"""Single source of truth for all runtime file/folder paths.

Every module imports from here — no more scattered "music_player.db" literals.
"""

from pathlib import Path

# All data files sit next to the working directory (where main.py is run from).
# Change this one constant to relocate everything.
_BASE = Path(".")

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
