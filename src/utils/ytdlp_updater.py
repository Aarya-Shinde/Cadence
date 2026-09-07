import os
import sys
import logging
import requests
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

def get_user_ytdlp_path() -> Path:
    """Returns path to the user-writable yt-dlp binary inside AppData (no admin rights needed)."""
    if sys.platform == "win32":
        local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        bin_dir = Path(local_app_data) / "Cadence" / "bin"
        executable_name = "yt-dlp.exe"
    else:
        bin_dir = Path.home() / ".local" / "share" / "Cadence" / "bin"
        executable_name = "yt-dlp"

    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir / executable_name

def download_latest_ytdlp_binary() -> bool:
    """
    Downloads the latest official yt-dlp binary directly into AppData.
    This works reliably in frozen MSI/PyInstaller environments without needing UAC/Admin rights.
    """
    target_path = get_user_ytdlp_path()
    temp_path = target_path.with_suffix(".tmp")
    logger.info(f"Downloading latest yt-dlp binary to: {target_path}")

    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" if sys.platform == "win32" \
          else "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if sys.platform != "win32":
            temp_path.chmod(0o755)

        if target_path.exists():
            try:
                target_path.unlink()
            except Exception:
                pass
                
        temp_path.rename(target_path)

        clear_yt_dlp_cache()
        logger.info("Successfully downloaded and updated yt-dlp binary!")
        return True

    except Exception as e:
        logger.error(f"Failed to download latest yt-dlp binary: {e}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return False

def clear_yt_dlp_cache():
    """Clears local yt-dlp cache using the updated binary if available or python fallback."""
    binary_path = get_user_ytdlp_path()
    if binary_path.exists():
        try:
            subprocess.run([str(binary_path), "--rm-cache-dir"], capture_output=True, timeout=10)
            logger.info("yt-dlp binary cache cleared.")
            return
        except Exception as e:
            logger.warning(f"Could not clear cache via binary: {e}")

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            ydl.cache.remove()
        logger.info("yt-dlp library cache cleared.")
    except Exception as e:
        logger.warning(f"Could not clear yt-dlp cache: {e}")

