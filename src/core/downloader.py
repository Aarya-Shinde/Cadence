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

    def search(self, query: str) -> list[dict]:
        """Search YouTube for *query* and return top 5 results, scored and sorted.
        Supports YouTube Music and regular YouTube search.
        
        Returns:
            List of dictionary entries from yt-dlp.
        """
        # Match filter: avoid live streams and extremely long compilations (>10 mins)
        # unless the user explicitly searched for them.
        def _filter(info, *, incomplete):
            title = info.get('title', '').lower()
            query_lower = query.lower()
            if info.get('is_live'):
                return 'Is a live stream'
            if "live" not in query_lower and "live" in title:
                # yt-dlp doesn't strictly filter title with match_filter, but we can return a string to reject
                # We will handle title filtering in our scoring logic instead.
                pass
            duration = info.get('duration')
            if duration and duration > 600 and "compilation" not in query_lower and "full album" not in query_lower:
                return 'Video is too long (> 10 mins)'
            return None

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "match_filter": _filter,
            "extract_flat": False,
            "ignoreerrors": True,  # Prevent the whole search from crashing if one result is unavailable
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Searching for: {query}")
            
            is_url = query.startswith("http://") or query.startswith("https://")
            
            try:
                if is_url:
                    search_info = ydl.extract_info(query, download=False)
                    if not search_info: return []
                    # extract_info on a URL might return a single entry or playlist entries
                    entries = search_info.get('entries', [search_info])
                else:
                    # Append negative keywords to avoid junk versions
                    # We only append them if the user didn't explicitly ask for them
                    negatives = []
                    q_lower = query.lower()
                    if "live" not in q_lower: negatives.append("-live")
                    if "remix" not in q_lower: negatives.append("-remix")
                    if "cover" not in q_lower: negatives.append("-cover")
                    if "karaoke" not in q_lower: negatives.append("-karaoke")
                    
                    search_term = query + " " + " ".join(negatives)
                    
                    # Use regular YouTube search since ytsearchmusic isn't supported in all versions
                    search_info = ydl.extract_info(f"ytsearch5:{search_term}", download=False)
                    if not search_info or 'entries' not in search_info or not search_info['entries']:
                        return []
                    
                    entries = search_info['entries']
                    
            except Exception as e:
                logger.error(f"yt-dlp extract_info failed: {e}")
                return []
            
            # Score and sort the valid entries
            valid_entries = []
            for entry in entries:
                if not entry: continue
                title = entry.get('title', '').lower()
                uploader = entry.get('uploader', '').lower()
                
                score = 0
                
                # Boost verified channels massively
                if entry.get('channel_is_verified') or entry.get('uploader_is_verified'):
                    score += 150
                
                # Channel reputation
                if uploader.endswith("- topic"): score += 150
                if "vevo" in uploader: score += 150
                
                # Priority for official tags
                if "official" in title: score += 100
                if "video" in title: score += 50
                if "audio" in title: score += 60
                
                # Penalties for unwanted types
                if "lyric" in title: score -= 200
                if "karaoke" in title: score -= 200
                if "cover" in title: score -= 200
                if "remix" in title and "remix" not in query.lower(): score -= 100
                if "live" in title and "live" not in query.lower(): score -= 80
                
                # View count bonus (logarithmic so 1 billion views doesn't blindly override everything)
                # e.g., 100k views = 5 * 15 = +75 points
                #       1M views = 6 * 15 = +90 points
                #       1B views = 9 * 15 = +135 points
                views = entry.get('view_count') or 0
                if views > 0:
                    import math
                    score += int(math.log10(views) * 15)
                
                query_words = query.lower().split()
                match_count = sum(1 for w in query_words if w in title)
                score += match_count * 10
                
                entry['_score'] = score
                valid_entries.append(entry)
            
            valid_entries.sort(key=lambda x: x.get('_score', 0), reverse=True)
            return valid_entries

    def download_song(
        self,
        url: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> Optional[Path]:
        """Download the best audio as MP3 from the given YouTube URL.

        Args:
            url: YouTube video URL.
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
                logger.info(f"Downloading: {url}")
                ydl.download([url])

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
            logger.error(f"Download failed for '{url}': {exc}")
            return None