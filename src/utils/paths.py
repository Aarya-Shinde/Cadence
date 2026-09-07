# src/utils/paths.py
"""Single source of truth for all runtime file/folder paths.

Every module imports from here — no more scattered "music_player.db" literals.
"""

from pathlib import Path
import sys
import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running from normal Python script
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Executable / Application root directory
_BASE = Path(os.path.abspath("."))

def get_app_data_dir() -> Path:
    """Returns persistent, user-writable AppData folder for database and config.
    This guarantees data survives MSI reinstalls and app updates.
    """
    if sys.platform == "win32":
        local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        data_dir = Path(local_app_data) / "Cadence"
    elif sys.platform == "darwin":
        data_dir = Path.home() / "Library" / "Application Support" / "Cadence"
    else:
        data_dir = Path.home() / ".local" / "share" / "Cadence"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

_USER_DATA_DIR = get_app_data_dir()

def _migrate_legacy_data(legacy_base: Path, target_dir: Path):
    """Migrates legacy database, config, and cache files from working dir to AppData if needed."""
    candidate_sources = [
        legacy_base,
        legacy_base / "src",
        Path(os.getcwd()),
    ]
    
    # 1. Migrate database
    target_db = target_dir / "cadence.db"
    if not target_db.exists() or target_db.stat().st_size == 0:
        for src_dir in candidate_sources:
            old_db = src_dir / "cadence.db"
            if old_db.exists() and old_db.resolve() != target_db.resolve() and old_db.stat().st_size > 0:
                try:
                    shutil.copy2(old_db, target_db)
                    logger.info(f"Migrated legacy database from {old_db} to {target_db}")
                    break
                except Exception as e:
                    logger.warning(f"Could not migrate db from {old_db}: {e}")

    # 2. Migrate config
    target_config = target_dir / "cadence_config.json"
    if not target_config.exists():
        for src_dir in candidate_sources:
            old_cfg = src_dir / "cadence_config.json"
            if old_cfg.exists() and old_cfg.resolve() != target_config.resolve():
                try:
                    shutil.copy2(old_cfg, target_config)
                    logger.info(f"Migrated legacy config from {old_cfg} to {target_config}")
                    break
                except Exception as e:
                    logger.warning(f"Could not migrate config from {old_cfg}: {e}")

# Run automatic data migration on startup
_migrate_legacy_data(_BASE, _USER_DATA_DIR)

DB_PATH          = str(_USER_DATA_DIR / "cadence.db")          # SQLite: songs + lyrics + album_art
CONFIG_PATH      = str(_USER_DATA_DIR / "cadence_config.json") # User settings
LOG_FILE         = "cadence.log"                               # RotatingFileHandler filename
LOG_DIR          = str(_USER_DATA_DIR / "logs")                 # Log directory

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

def get_album_art_dir() -> str:
    from utils.config import get_config
    base = Path(get_config().get('music_folder', _USER_DATA_DIR))
    cache_dir = base / ".album_art_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir)

def get_lyrics_dir() -> str:
    from utils.config import get_config
    base = Path(get_config().get('music_folder', _USER_DATA_DIR))
    lyrics_dir = base / ".lyrics"
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    return str(lyrics_dir)

