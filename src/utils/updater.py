# src/utils/updater.py

import requests
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import subprocess
import sys

logger = logging.getLogger(__name__)

class Updater:
    """Handle app updates"""
    
    def __init__(self, current_version: str = "1.0.0"):
        self.current_version = current_version
        self.remote_version_url = "https://raw.githubusercontent.com/yourusername/music-player/main/version.json"
        self.download_url = "https://github.com/yourusername/music-player/releases/download"
        self.timeout = 5  # seconds
    
    def check_for_updates(self) -> Optional[Tuple[str, str]]:
        """Check if a new version is available
        
        Returns:
            Tuple of (new_version, download_url) or None if no update
        """
        try:
            # Fetch version info from GitHub
            response = requests.get(
                self.remote_version_url,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            remote_version = data.get('version')
            
            if not remote_version:
                logger.warning("No version info in remote file")
                return None
            
            # Compare versions
            if self._is_newer(remote_version, self.current_version):
                logger.info(f"New version available: {remote_version}")
                return (remote_version, data.get('download_url'))
            else:
                logger.info(f"Already on latest version: {self.current_version}")
                return None
        
        except requests.RequestException as e:
            logger.warning(f"Could not check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking updates: {e}")
            return None
    
    def download_update(self, download_url: str, save_path: str = "music_player_update.exe") -> bool:
        """Download new version
        
        Args:
            download_url: URL to download from
            save_path: Where to save the .exe
        
        Returns:
            True if downloaded successfully
        """
        try:
            logger.info(f"Downloading update from {download_url}")
            
            response = requests.get(
                download_url,
                timeout=30,
                stream=True
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Could emit progress here
                        progress = (downloaded / total_size * 100) if total_size else 0
                        logger.debug(f"Downloaded {progress:.1f}%")
            
            logger.info(f"Update downloaded to {save_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return False
    
    def install_update(self, update_path: str):
        """Replace current exe with update and restart
        
        Args:
            update_path: Path to new .exe file
        """
        try:
            # On Windows, we need to:
            # 1. Save current exe path
            # 2. Start the update .exe
            # 3. Update .exe replaces the original
            # 4. Restart original
            
            current_exe = Path(sys.executable)
            
            # Create a batch script to handle the replacement
            batch_script = Path("update.bat")
            
            batch_content = f'''
@echo off
timeout /t 2 /nobreak
move /Y "{update_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
'''
            
            batch_script.write_text(batch_content)
            
            # Start the batch script (detached)
            subprocess.Popen(
                str(batch_script),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            logger.info("Update script started, exiting...")
            sys.exit(0)
        
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
    
    @staticmethod
    def _is_newer(version1: str, version2: str) -> bool:
        """Check if version1 > version2
        
        Example: "1.0.1" > "1.0.0" = True
        """
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad with zeros
            while len(v1_parts) < len(v2_parts):
                v1_parts.append(0)
            while len(v2_parts) < len(v1_parts):
                v2_parts.append(0)
            
            return v1_parts > v2_parts
        except:
            return False


class UpdateChecker:
    """Periodic update checker (can run in background)"""
    
    def __init__(self, config, check_interval_hours: int = 24):
        self.config = config
        self.updater = Updater()
        self.check_interval_hours = check_interval_hours
    
    def should_check(self) -> bool:
        """Check if enough time has passed since last check"""
        if not self.config.get('auto_update_check'):
            return False
        
        last_check_str = self.config.get('last_update_check')
        try:
            last_check = datetime.fromisoformat(last_check_str)
            elapsed = datetime.now() - last_check
            return elapsed >= timedelta(hours=self.check_interval_hours)
        except:
            return True  # Check if can't parse last check time
    
    def check_and_notify(self, callback=None):
        """Check for updates and call callback if found
        
        Args:
            callback: Function(version, download_url) to call if update found
        """
        if not self.should_check():
            logger.debug("Update check not needed yet")
            return
        
        # Update last check time
        self.config.set('last_update_check', datetime.now().isoformat())
        
        result = self.updater.check_for_updates()
        if result and callback:
            version, url = result
            callback(version, url)