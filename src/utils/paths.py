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
ALBUM_ART_DIR    = str(_BASE / "album_art_cache")      # Cached album art PNGs
LYRICS_DIR       = str(_BASE / "lyrics")               # Cached .txt lyrics files
