# src/core/downloader.py
import yt_dlp
from pathlib import Path
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class DownloadProgress:
    """Holds the current download state"""
    def __init__(self):
        self.status: str = "idle"          # idle | downloading | processing | done | error
        self.percent: float = 0.0
        self.speed: str = ""
        self.eta: str = ""
        self.filename: str = ""
        self.error: str = ""


class MusicDownloader:
    """Download audio from YouTube and convert to MP3 via yt-dlp + FFmpeg"""

    def __init__(self, output_folder: str):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download_song(
        self,
        query: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> Optional[Path]:
        """Search YouTube for *query* and download the best audio as MP3.

        Args:
            query: Free-text search string, e.g. "Shape of You Ed Sheeran"
            progress_callback: Called on every yt-dlp progress event with a
                               DownloadProgress instance.  Runs on the download
                               thread — marshal to the GUI thread yourself.

        Returns:
            Path to the saved MP3 on success, None on failure.
        """
        state = DownloadProgress()
        result_path: Optional[Path] = None

        def _hook(d: dict):
            nonlocal result_path
            if d["status"] == "downloading":
                state.status = "downloading"
                state.percent = float(
                    d.get("downloaded_bytes", 0) /
                    max(d.get("total_bytes") or d.get("total_bytes_estimate") or 1, 1)
                    * 100
                )
                state.speed = d.get("_speed_str", "")
                state.eta   = d.get("_eta_str", "")
                state.filename = Path(d.get("filename", "")).stem

            elif d["status"] == "finished":
                state.status  = "processing"
                state.percent = 100.0
                # yt-dlp gives us the pre-conversion filename; swap extension
                raw = Path(d.get("filename", ""))
                result_path = raw.with_suffix(".mp3")

            if progress_callback:
                progress_callback(state)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(self.output_folder / "%(title)s.%(ext)s"),
            "ffmpeg_location": r"D:\ffmpeg\ffmpeg-8.1-essentials_build\bin",
            "noplaylist": True,
            "restrictfilenames": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_hook],
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
                {
                    "key": "EmbedThumbnail",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Searching for best official match: {query}")
                
                # Fetch top 5 results to find the most "legit" one
                search_info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                
                if not search_info or 'entries' not in search_info or not search_info['entries']:
                    raise Exception("No search results found")
                
                entries = search_info['entries']
                best_entry = entries[0]
                max_score = -1000
                
                for entry in entries:
                    title = entry.get('title', '').lower()
                    uploader = entry.get('uploader', '').lower()
                    
                    # Scoring logic
                    score = 0
                    
                    # Priority for official tags
                    if "official" in title: score += 100
                    if "video" in title: score += 50
                    if "audio" in title: score += 60
                    
                    # Channel reputation
                    if uploader.endswith("- topic"): score += 80 # Topic channels are usually official audio
                    if "vevo" in uploader: score += 90
                    
                    # Penalties for unwanted types
                    if "lyric" in title: score -= 150
                    if "karaoke" in title: score -= 200
                    if "cover" in title: score -= 150
                    if "remix" in title and "remix" not in query.lower(): score -= 100
                    if "live" in title and "live" not in query.lower(): score -= 80
                    
                    # Prefer exact title matches if possible (vague check)
                    query_words = query.lower().split()
                    match_count = sum(1 for w in query_words if w in title)
                    score += match_count * 10
                    
                    if score > max_score:
                        max_score = score
                        best_entry = entry
                
                logger.info(f"Selected: '{best_entry['title']}' by {best_entry['uploader']} (Score: {max_score})")
                
                # Perform the actual download on the best match
                ydl.download([best_entry['webpage_url']])

            state.status = "done"
            if progress_callback:
                progress_callback(state)

            logger.info(f"Download complete → {result_path}")
            return result_path

        except Exception as exc:
            state.status = "error"
            state.error  = str(exc)
            if progress_callback:
                progress_callback(state)
            logger.error(f"Download failed for '{query}': {exc}")
            return None