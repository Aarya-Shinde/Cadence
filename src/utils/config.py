# src/utils/config.py

import json
import logging
from pathlib import Path
from typing import Any, Dict

from utils.paths import CONFIG_PATH as _DEFAULT_CONFIG

logger = logging.getLogger(__name__)

class Config:
    """Manages application settings"""
    
    def __init__(self, config_file: str = _DEFAULT_CONFIG):
        self.config_file = Path(config_file)
        self.settings = {}
        self.defaults = {
            'music_folder': str(Path.home() / "Music"),
            'auto_scan_minutes': 5,
            'theme': 'light',  # or 'dark'
            'volume': 0.8,
            'window_width': 1200,
            'window_height': 800,
            'auto_update_check': True,
            'update_check_interval_hours': 24,
            'last_update_check': '2024-01-01',
            'sort_order': 'artist',  # artist, date_added, title
            'remember_position': True,
            'last_played_song_id': None,
        }
        
        self.load()
    
    def load(self):
        """Load settings from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved = json.load(f)
                    self.settings = {**self.defaults, **saved}
                logger.info(f"Config loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self.settings = self.defaults.copy()
        else:
            # First run - use defaults
            self.settings = self.defaults.copy()
            self.save()
            logger.info("Config file created with defaults")
    
    def save(self):
        """Save settings to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.debug(f"Config saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default=None) -> Any:
        """Get setting by key"""
        return self.settings.get(key, default if default is not None else self.defaults.get(key))
    
    def set(self, key: str, value: Any):
        """Set setting by key"""
        self.settings[key] = value
        self.save()
        logger.debug(f"Config: {key} = {value}")
    
    def get_all(self) -> Dict:
        """Get all settings"""
        return self.settings.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.defaults.copy()
        self.save()
        logger.info("Config reset to defaults")


# Global config instance
_config = None

def get_config() -> Config:
    """Get or create global config"""
    global _config
    if _config is None:
        _config = Config()
    return _config