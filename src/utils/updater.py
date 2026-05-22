# src/utils/updater.py

import requests
import json
import logging
import hashlib
import shutil
import zipfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)

# Files that MUST be present inside the update zip for the update to be
# considered valid.  Paths are relative to the root of the zip.
_REQUIRED_FILES = [
    "Cadence/_internal/bin/ffmpeg.exe",
    "Cadence/_internal/bin/ffprobe.exe",
    "Cadence/Cadence.exe",
]


class Updater:
    """Handle app updates with a robust, atomic, rollback-safe protocol."""

    def __init__(self, current_version: str = "1.0.3"):
        self.current_version = current_version
        self.remote_version_url = (
            "https://api.github.com/repos/Aarya-Shinde/Cadence/releases/latest"
        )
        self.timeout = 10  # seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_updates(self) -> Optional[Tuple[str, str]]:
        """Check if a new version is available from GitHub Releases.

        Returns:
            Tuple of (new_version, download_url) or None if no update.
        """
        try:
            response = requests.get(self.remote_version_url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            remote_version = data.get("tag_name", "").lstrip("v")

            if not remote_version:
                logger.warning("No version info in remote release")
                return None

            if self._is_newer(remote_version, self.current_version):
                assets = data.get("assets", [])
                download_url = None
                sha256_url = None

                for asset in assets:
                    name = asset.get("name", "")
                    if name in ("Cadence.zip", "Cadence-Windows.zip"):
                        download_url = asset.get("browser_download_url")
                    # Look for an accompanying checksum file
                    if name in ("Cadence.zip.sha256", "Cadence-Windows.zip.sha256"):
                        sha256_url = asset.get("browser_download_url")

                if download_url:
                    logger.info(f"New version available: {remote_version}")
                    return (remote_version, download_url, sha256_url)
                else:
                    logger.warning("No matching asset found in latest release")
                    return None
            else:
                logger.info(f"Already on latest version: {self.current_version}")
                return None

        except requests.RequestException as e:
            logger.warning(f"Could not check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking updates: {e}")
            return None

    def download_update(
        self,
        download_url: str,
        sha256_url: Optional[str] = None,
        progress_callback=None,
    ) -> Optional[Path]:
        """Download the update zip to a secure temp file and verify it.

        Args:
            download_url:      Direct URL to the update .zip.
            sha256_url:        Optional URL to a .sha256 checksum file.
            progress_callback: Callable(downloaded_bytes, total_bytes).

        Returns:
            Path to the verified zip file, or None on failure.
        """
        try:
            # Download to a named temp file so we always know where it is
            tmp_fd, tmp_path_str = tempfile.mkstemp(
                suffix=".zip", prefix="cadence_update_"
            )
            tmp_path = Path(tmp_path_str)
            os.close(tmp_fd)

            logger.info(f"Downloading update from {download_url} → {tmp_path}")

            response = requests.get(download_url, timeout=60, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            sha256 = hashlib.sha256()

            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        sha256.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            logger.info(f"Download complete: {downloaded} bytes")

            # --- Checksum verification ----------------------------------
            if sha256_url:
                try:
                    logger.info("Verifying checksum...")
                    chk_resp = requests.get(sha256_url, timeout=10)
                    chk_resp.raise_for_status()
                    expected_hash = chk_resp.text.strip().split()[0].lower()
                    actual_hash = sha256.hexdigest().lower()
                    if actual_hash != expected_hash:
                        logger.error(
                            f"Checksum mismatch! expected={expected_hash} got={actual_hash}"
                        )
                        tmp_path.unlink(missing_ok=True)
                        return None
                    logger.info("Checksum verified ✓")
                except Exception as e:
                    logger.warning(f"Could not verify checksum (skipping): {e}")
            else:
                logger.warning(
                    "No sha256 asset found for this release — skipping checksum verification."
                )

            # --- Structural validation of zip ---------------------------
            if not self._validate_zip(tmp_path):
                tmp_path.unlink(missing_ok=True)
                return None

            return tmp_path

        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

    def install_update(self, zip_path) -> bool:
        """Atomic install: backup → extract to staging → swap → restart.

        The entire sequence is handed off to a detached batch script so
        the running process can exit cleanly before files are replaced.

        Args:
            zip_path: Path (str or Path) to the downloaded, verified zip.

        Returns:
            True if the batch script was launched; False if we are not
            running as a frozen (PyInstaller) executable.
        """
        if not getattr(sys, "frozen", False):
            logger.warning(
                "Cannot auto-update when running from source code. Skipping installation."
            )
            return False

        current_exe = Path(sys.executable).resolve()
        app_dir = current_exe.parent          # e.g. …\Cadence\
        zip_path = Path(zip_path).resolve()

        staging_dir = app_dir / "_update_staging"
        backup_dir  = app_dir / "_update_backup"
        batch_path  = app_dir / "_do_update.bat"

        # Write the batch update script
        batch_content = self._build_batch_script(
            zip_path=zip_path,
            app_dir=app_dir,
            staging_dir=staging_dir,
            backup_dir=backup_dir,
            exe_name=current_exe.name,
        )
        batch_path.write_text(batch_content, encoding="utf-8")
        logger.info(f"Update batch script written to {batch_path}")

        # Launch the script detached so it survives our process exit
        subprocess.Popen(
            ["cmd.exe", "/C", str(batch_path)],
            cwd=str(app_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )

        logger.info("Update script launched — exiting application.")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_zip(self, zip_path: Path) -> bool:
        """Ensure the zip is not corrupt and contains all required files."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad = zf.testzip()
                if bad:
                    logger.error(f"Corrupt zip — first bad file: {bad}")
                    return False

                names = set(zf.namelist())
                for required in _REQUIRED_FILES:
                    if required not in names:
                        logger.error(
                            f"Update zip is missing required file: {required}"
                        )
                        return False

            logger.info("Zip structure validated ✓")
            return True

        except zipfile.BadZipFile as e:
            logger.error(f"Bad zip file: {e}")
            return False
        except Exception as e:
            logger.error(f"Zip validation error: {e}")
            return False

    @staticmethod
    def _build_batch_script(
        zip_path: Path,
        app_dir: Path,
        staging_dir: Path,
        backup_dir: Path,
        exe_name: str,
    ) -> str:
        """Generate a robust, self-cleaning batch update script with rollback."""
        return f"""@echo off
setlocal enabledelayedexpansion
title Cadence Updater

echo ============================================================
echo  Cadence Auto-Updater
echo ============================================================
echo.

:: Wait for the main application process to fully exit
echo [1/7] Waiting for Cadence to close...
timeout /t 3 /nobreak >nul

:: Clean up any leftover staging/backup dirs from a previous failed attempt
echo [2/7] Cleaning previous staging data...
if exist "{staging_dir}" rmdir /s /q "{staging_dir}"
if exist "{backup_dir}"  rmdir /s /q "{backup_dir}"

:: Extract update zip into a staging folder FIRST (never touch live files yet)
echo [3/7] Extracting update to staging area...
mkdir "{staging_dir}"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try {{ Expand-Archive -LiteralPath '{zip_path}' -DestinationPath '{staging_dir}' -Force; exit 0 }} catch {{ Write-Error $_; exit 1 }}"

if %errorlevel% neq 0 (
    echo ERROR: Extraction failed. Aborting update.
    rmdir /s /q "{staging_dir}" 2>nul
    goto :cleanup_and_exit
)

:: Validate that all critical files are present in the staged content
echo [4/7] Validating staged content...
if not exist "{staging_dir}\\Cadence\\Cadence.exe" (
    echo ERROR: Cadence.exe not found in extracted update. Aborting.
    rmdir /s /q "{staging_dir}" 2>nul
    goto :cleanup_and_exit
)
if not exist "{staging_dir}\\Cadence\\_internal\\bin\\ffmpeg.exe" (
    echo ERROR: ffmpeg.exe not found in extracted update. Aborting.
    rmdir /s /q "{staging_dir}" 2>nul
    goto :cleanup_and_exit
)

:: -----------------------------------------------------------------------
:: CLEAN SWAP — rename old _internal out atomically, move new one in.
:: This guarantees NO stale .dll, .pyd, or old Python runtime files survive.
:: -----------------------------------------------------------------------
echo [5/7] Performing clean swap of _internal folder...

:: Step A: Rename old _internal to _internal_old (instant same-volume rename)
if exist "{app_dir}\\_internal" (
    move /y "{app_dir}\\_internal" "{app_dir}\\_internal_old" >nul
    if %errorlevel% neq 0 (
        echo ERROR: Could not rename old _internal folder. Is Cadence still running?
        rmdir /s /q "{staging_dir}" 2>nul
        goto :cleanup_and_exit
    )
)

:: Step B: Move new _internal from staging into the live app folder
move /y "{staging_dir}\\Cadence\\_internal" "{app_dir}\\_internal" >nul
if %errorlevel% neq 0 (
    echo ERROR: Could not move new _internal into place. Attempting rollback...
    if exist "{app_dir}\\_internal_old" (
        move /y "{app_dir}\\_internal_old" "{app_dir}\\_internal" >nul
    )
    rmdir /s /q "{staging_dir}" 2>nul
    echo Rollback complete. Please restart Cadence manually.
    goto :cleanup_and_exit
)

:: Step C: Replace Cadence.exe
copy /y "{staging_dir}\\Cadence\\Cadence.exe" "{app_dir}\\Cadence.exe" >nul
if %errorlevel% neq 0 (
    echo WARNING: Could not replace Cadence.exe. _internal was updated successfully.
)

:: Step D: Delete the old _internal — zero stale files remain
echo [6/7] Removing old installation files...
if exist "{app_dir}\\_internal_old" (
    rmdir /s /q "{app_dir}\\_internal_old"
)

:: Clean up staging and the downloaded zip
echo [7/7] Cleaning up temporary files...
rmdir /s /q "{staging_dir}" 2>nul
del /f /q "{zip_path}"       2>nul

echo.
echo ============================================================
echo  Update complete! Launching Cadence...
echo ============================================================
echo.
timeout /t 1 /nobreak >nul
start "" "{app_dir}\\{exe_name}"
goto :eof

:cleanup_and_exit
echo.
echo The update was not applied. Your current version is unchanged.
echo Please restart Cadence manually.
timeout /t 5 /nobreak >nul

:eof
del "%~f0"
"""

    @staticmethod
    def _is_newer(version1: str, version2: str) -> bool:
        """Return True if version1 > version2 (e.g. '1.0.2' > '1.0.1')."""
        try:
            v1 = [int(x) for x in version1.split(".")]
            v2 = [int(x) for x in version2.split(".")]
            while len(v1) < len(v2):
                v1.append(0)
            while len(v2) < len(v1):
                v2.append(0)
            return v1 > v2
        except Exception:
            return False


# ---------------------------------------------------------------------------

class UpdateChecker:
    """Periodic update checker (runs in a background thread)."""

    def __init__(self, config, check_interval_hours: int = 24):
        self.config = config
        self.updater = Updater()
        self.check_interval_hours = check_interval_hours

    def should_check(self) -> bool:
        if not self.config.get("auto_update_check"):
            return False
        last_check_str = self.config.get("last_update_check")
        try:
            last_check = datetime.fromisoformat(last_check_str)
            elapsed = datetime.now() - last_check
            return elapsed >= timedelta(hours=self.check_interval_hours)
        except Exception:
            return True  # Can't parse → assume we need to check

    def check_and_notify(self, callback=None):
        """Check for updates and call callback(version, download_url, sha256_url) if found."""
        if not self.should_check():
            logger.debug("Update check not needed yet")
            return

        self.config.set("last_update_check", datetime.now().isoformat())

        result = self.updater.check_for_updates()
        if result and callback:
            version, url, sha256_url = result
            callback(version, url, sha256_url)