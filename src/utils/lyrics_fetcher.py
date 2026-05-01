# src/utils/lyrics_fetcher.py - Lyrics Management System

"""
Advanced Lyrics System:
- Auto-fetch from online (Genius API)
- Cache locally (SQLite)
- Offline reuse
- Fallback mechanisms
- Error handling
"""

import requests
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from urllib.parse import quote
import json

from utils.paths import DB_PATH as _DEFAULT_DB, get_lyrics_dir

logger = logging.getLogger(__name__)


# ============================================================================
# LRC PARSER (Synchronized Lyrics)
# ============================================================================

class LrcParser:
    """Parse LRC (synchronized lyrics) format [mm:ss.xx] Lyrics..."""
    
    @staticmethod
    def parse(lrc_text: str) -> List[Dict]:
        """Convert LRC text into a list of timing dictionaries"""
        if not lrc_text or "[" not in lrc_text:
            return []
            
        import re
        lines = lrc_text.splitlines()
        synced_lines = []
        
        # Regex for [mm:ss.xx], [hh:mm:ss.xx], [mm:ss] etc.
        # Matches: [01:02.03], [00:01:02.03], [01:02]
        pattern = re.compile(r'\[(?:(\d+):)?(\d+):(\d+)(?:[:\.](\d+))?\](.*)')
        
        for line in lines:
            line = line.strip()
            match = pattern.match(line)
            if match:
                hrs, mins, secs, ms, text = match.groups()
                
                # Calculate absolute seconds
                total_seconds = int(mins) * 60 + int(secs)
                if hrs:
                    total_seconds += int(hrs) * 3600
                if ms:
                    ms_val = float(ms)
                    # Handle both [ss.xx] (centiseconds) and [ss.xxx] (milliseconds)
                    if len(ms) == 3:
                        total_seconds += ms_val / 1000.0
                    else:
                        total_seconds += ms_val / 100.0
                
                synced_lines.append({
                    "time": total_seconds,
                    "text": text.strip()
                })
        
        # Ensure they are sorted by time
        return sorted(synced_lines, key=lambda x: x["time"])


# ============================================================================
# LRCLIB API FETCHER (High Accuracy Source)
# ============================================================================

class LrcLibFetcher:
    """Fetch lyrics from LRCLIB (Specialized lyrics DB)"""
    
    def __init__(self):
        self.base_url = "https://lrclib.net/api"
        self.timeout = 8
        self.session = requests.Session()

    def fetch_lyrics(self, title: str, artist: str) -> Optional[Dict]:
        """Fetch lyrics using specialized lookup"""
        try:
            params = {
                "track_name": title,
                "artist_name": artist,
            }
            response = self.session.get(
                f"{self.base_url}/get",
                params=params, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                # PRIORITY: Use synced lyrics for synchronization feature!
                lyrics_text = data.get("syncedLyrics") or data.get("plainLyrics")
                if lyrics_text:
                    logger.info(f"LRCLIB Match: '{data.get('trackName')}' (Synced: {bool(data.get('syncedLyrics'))})")
                    return {
                        "lyrics": lyrics_text,
                        "source": "lrclib",
                        "title": data.get("trackName"),
                        "artist": data.get("artistName")
                    }
            return None
        except Exception as e:
            logger.debug(f"LRCLIB fetch failed: {e}")
            return None

# ============================================================================
# GENIUS API LYRICS FETCHER
# ============================================================================

class GeniusLyricsFetcher:
    """Fetch lyrics from Genius API"""
    
    def __init__(self, genius_token: Optional[str] = None):
        """
        Initialize Genius fetcher
        
        Args:
            genius_token: Genius API token (optional, fallback to free search)
        """
        self.genius_token = genius_token
        self.base_url = "https://api.genius.com"
        self.search_url = "https://genius.com/api/search"
        self.timeout = 10
        self.session = requests.Session()
        
        if genius_token:
            self.session.headers.update({
                "Authorization": f"Bearer {genius_token}"
            })
    
    def fuzzy_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0.0 to 1.0)"""
        from difflib import SequenceMatcher
        if not s1 or not s2: return 0.0
        return SequenceMatcher(None, s1, s2).ratio()

    def _clean_query(self, text: str) -> str:
        """Deep clean of search terms for accurate matching"""
        import re
        if not text: return ""
        
        # 1. Standardize (lowercase, remove smart quotes/dashes)
        text = text.lower()
        text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
        text = text.replace('–', '-').replace('—', '-')
        
        # 2. Remove common junk in brackets/parentheses
        text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
        
        # 3. Strip clutter words often found in YouTube titles
        clutter = [
            'official music video', 'official video', 'official audio', 
            'lyrics', 'lyric video', 'hq', 'hd', '4k', 'm/v', 'mv', 'amv',
            'remastered', 'visualizer', 'feat.', 'ft.', 'prod.', 'audio',
            'cover', 'karaoke', 'instrumental', '1080p', '720p', 'high quality'
        ]
        next_text = text
        for word in clutter:
            next_text = next_text.replace(word, ' ')
        
        # 4. Strip punctuation and special symbols
        text = re.sub(r'[^\w\s\']', ' ', next_text)
            
        # 5. Clean extra whitespace
        return ' '.join(text.split()).strip()

    def search_song(self, title: str, artist: str) -> Optional[Dict]:
        """Search with fuzzy multi-pass matching, optimized for AMVs/YT Titles"""
        try:
            # 1. Detect if artist is missing or generic (common in YT downloads)
            is_generic_artist = not artist or artist.lower() in ["unknown artist", "unknown", "youtube", "yt user", "various artists"]
            
            # 2. Extract potential artist/title from filename if it's an AMV style title
            # Example: "YOASOBI - IDOL [AMV]" -> Artist: YOASOBI, Title: IDOL
            p_title = title
            p_artist = artist
            
            if is_generic_artist and (" - " in title or " | " in title):
                # Try common splitters
                for sep in [" - ", " | ", " : "]:
                    if sep in title:
                        parts = title.split(sep, 1)
                        p_artist = parts[0].strip()
                        p_title = parts[1].strip()
                        break
            
            # Clean both
            target_title = self._clean_query(p_title)
            target_artist = self._clean_query(p_artist)
            
            # Prepare search queries to try in order
            search_queries = []
            
            # Full query
            if target_artist and target_artist != "unknown":
                search_queries.append(f"{target_title} {target_artist}")
            
            # Just title (often has everything on YT)
            search_queries.append(target_title)
            
            # If AMV, try removing 'amv' specific words
            amv_clean = target_title.replace("amv", "").replace("anime", "").replace("edit", "").strip()
            if amv_clean != target_title:
                search_queries.append(f"{amv_clean} {target_artist}")
            
            for query in search_queries:
                if not query: continue
                
                logger.debug(f"Searching Pass: {query}")
                params = {"q": query}
                response = self.session.get(self.search_url, params=params, timeout=self.timeout)
                if response.status_code != 200: continue
                
                hits = response.json().get("response", {}).get("hits", [])
                if not hits: continue
                
                # Verification Loop
                for hit in hits[:6]:
                    result = hit.get("result", {})
                    res_title_full = result.get("title", "")
                    res_artist_full = result.get("primary_artist", {}).get("name", "")
                    
                    res_title = self._clean_query(res_title_full).replace(' ', '')
                    res_artist = self._clean_query(res_artist_full).replace(' ', '')
                    
                    t_title = target_title.replace(' ', '')
                    t_artist = target_artist.replace(' ', '')
                    
                    # Fuzzy Scores
                    t_score = self.fuzzy_similarity(target_title, self._clean_query(res_title_full))
                    a_score = self.fuzzy_similarity(target_artist, self._clean_query(res_artist_full))
                    
                    # Check if artist name appears in the title (common for YT/Genius hits)
                    artist_in_title = target_artist.lower() in res_title_full.lower() if target_artist else False
                    
                    # REFINED MATCH CRITERIA (Avoid Spanish/Translated hits)
                    # 1. Title match must be very high
                    # 2. Artist match must be high OR artist must be in title
                    is_match = False
                    
                    # Penalize translated hits if they weren't requested
                    is_translated = any(word in res_title_full.lower() for word in [" (spanish", " (traducción", " (english", " lyrics"])
                    
                    if t_score > 0.85 and a_score > 0.85:
                        is_match = True
                    elif t_score > 0.9 and (a_score > 0.6 or artist_in_title):
                        is_match = True
                    elif t_score > 0.95 and a_score > 0.4:
                        is_match = True
                    
                    # If it's translated but the original artist matches 100%, it might be a hit, 
                    # but we prefer non-translated
                    if is_match and is_translated and a_score < 0.95:
                        logger.debug(f"Skipping likely translated hit: {res_title_full}")
                        is_match = False
                        
                    if is_match:
                        logger.info(f"Genius Match Found: '{res_title_full}' by {res_artist_full}")
                        return {
                            "id": result.get("id"),
                            "title": result.get("title"),
                            "artist": result.get("primary_artist", {}).get("name"),
                            "url": result.get("url"),
                            "lyrics_url": result.get("url"),
                        }
            
            return None
        
        except requests.RequestException as e:
            logger.error(f"Error searching Genius: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in search_song: {e}")
            return None
    
    def fetch_lyrics(self, genius_url: str) -> Optional[str]:
        """Fetch lyrics from Genius URL using web scraping
        
        Args:
            genius_url: Genius song URL
        
        Returns:
            Lyrics text or None
        """
        try:
            response = self.session.get(
                genius_url,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse HTML to extract lyrics
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find lyrics container
            # Note: Genius uses different selectors, this is a common pattern
            lyrics_divs = soup.find_all("div", {"data-lyrics-container": "true"})
            
            if not lyrics_divs:
                # Fallback selector
                lyrics_divs = soup.find_all("div", class_="Lyrics__Container")
            
            if not lyrics_divs:
                logger.warning(f"Could not find lyrics on page: {genius_url}")
                return None
            
            # Combine all lyrics divs
            lyrics_text = ""
            for div in lyrics_divs:
                lyrics_text += div.get_text(separator="\n") + "\n"
            
            return lyrics_text.strip() if lyrics_text else None
        
        except ImportError:
            logger.warning("BeautifulSoup not installed. Install with: pip install beautifulsoup4")
            return None
        except requests.RequestException as e:
            logger.error(f"Error fetching lyrics: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching lyrics: {e}")
            return None


# ============================================================================
# LOCAL LYRICS CACHE
# ============================================================================

class LyricsCache:
    """Manage local lyrics cache in SQLite"""
    
    def __init__(self, db_path: str = _DEFAULT_DB):
        """Initialize cache
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize lyrics table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lyrics (
                    id INTEGER PRIMARY KEY,
                    song_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    lyrics TEXT,
                    source TEXT,
                    genius_url TEXT,
                    synced BOOLEAN DEFAULT 0,
                    local_path TEXT,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE,
                    UNIQUE(song_id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Lyrics database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing lyrics DB: {e}")
    
    def save_lyrics(self, song_id: int, title: str, artist: str, 
                   lyrics: str, source: str = "genius", 
                   genius_url: str = None) -> bool:
        """Save lyrics to cache
        
        Args:
            song_id: Song ID from songs table
            title: Song title
            artist: Artist name
            lyrics: Lyrics text
            source: Source (genius, genius-synced, local, etc.)
            genius_url: Genius song URL
        
        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO lyrics 
                (song_id, title, artist, lyrics, source, genius_url, date_updated)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (song_id, title, artist, lyrics, source, genius_url))
            
            conn.commit()
            conn.close()
            logger.info(f"Lyrics saved for: {title} by {artist}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving lyrics: {e}")
            return False
    
    def get_lyrics(self, song_id: int) -> Optional[Dict]:
        """Get lyrics from cache
        
        Args:
            song_id: Song ID
        
        Returns:
            Dict with lyrics info or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, artist, lyrics, source, genius_url, synced, local_path
                FROM lyrics
                WHERE song_id = ?
            """, (song_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "title": row[1],
                "artist": row[2],
                "lyrics": row[3],
                "source": row[4],
                "genius_url": row[5],
                "synced": bool(row[6]),
                "local_path": row[7],
            }
        
        except Exception as e:
            logger.error(f"Error getting lyrics: {e}")
            return None
    
    def save_local_lyrics(self, song_id: int, title: str, artist: str,
                         lyrics: str, local_path: str = None) -> bool:
        """Save lyrics as local file
        
        Args:
            song_id: Song ID
            lyrics: Lyrics text
            local_path: Path to save lyrics file
        
        Returns:
            True if saved
        """
        try:
            if not local_path:
                lyrics_dir = Path(get_lyrics_dir())
                lyrics_dir.mkdir(exist_ok=True, parents=True)
                
                # Sanitize name
                clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
                clean_artist = "".join([c for c in artist if c.isalnum() or c in (' ', '-', '_')]).strip()
                
                extension = ".lrc" if "[" in lyrics else ".txt"
                filename = f"{clean_artist} - {clean_title}{extension}"
                local_path = str(lyrics_dir / filename)
            
            # Save to file
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(lyrics)
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE lyrics
                SET local_path = ?, source = 'local'
                WHERE song_id = ?
            """, (local_path, song_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Lyrics saved locally: {local_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving local lyrics: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics
        
        Returns:
            Dict with cache stats
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM lyrics")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM lyrics WHERE lyrics IS NOT NULL")
            with_lyrics = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM lyrics WHERE synced = 1")
            synced = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM lyrics WHERE local_path IS NOT NULL")
            local = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_entries": total,
                "with_lyrics": with_lyrics,
                "synced": synced,
                "local_files": local,
            }
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


# ============================================================================
# INTEGRATED LYRICS MANAGER
# ============================================================================

class LyricsManager:
    """High-level lyrics management"""
    
    def __init__(self, db_path: str = _DEFAULT_DB, 
                 genius_token: Optional[str] = None):
        """Initialize lyrics manager"""
        self.cache = LyricsCache(db_path)
        self.lrclib = LrcLibFetcher()
        self.genius = GeniusLyricsFetcher(genius_token)
        self.is_fetching = False
    
    def get_lyrics(self, song_id: int, title: str, artist: str,
                  auto_fetch: bool = True) -> Optional[Dict]:
        """Get lyrics from cache or fetch online
        
        Args:
            song_id: Song ID
            title: Song title
            artist: Artist name
            auto_fetch: Automatically fetch if not cached
        
        Returns:
            Dict with lyrics or None
        """
        # Try cache first
        cached = self.cache.get_lyrics(song_id)
        if cached and cached.get("lyrics"):
            logger.info(f"Loaded lyrics from cache: {title}")
            return cached
        
        # Fetch online if requested
        if auto_fetch and not self.is_fetching:
            return self.fetch_and_cache(song_id, title, artist)
        
        return None
    
    def fetch_and_cache(self, song_id: int, title: str, artist: str) -> Optional[Dict]:
        """Fetch lyrics from multi-sources and save to cache"""
        if self.is_fetching: return None
        
        try:
            self.is_fetching = True
            lyrics = None
            source = "unknown"
            url = None
            
            # PASS 1: Try LRCLIB (Specialized Music DB - High Accuracy)
            logger.debug(f"Attempting LRCLIB fetch for: {title}")
            lrc_info = self.lrclib.fetch_lyrics(title, artist)
            if lrc_info:
                lyrics = lrc_info["lyrics"]
                source = "lrclib"
                logger.info(f"Successfully fetched lyrics from LRCLIB: {title}")
            
            # PASS 2: Fallback to Genius (General Search)
            if not lyrics:
                logger.debug(f"Attempting Genius fetch for: {title}")
                song_info = self.genius.search_song(title, artist)
                if song_info:
                    url = song_info["url"]
                    lyrics = self.genius.fetch_lyrics(song_info["lyrics_url"])
                    if lyrics:
                        source = "genius"
                        logger.info(f"Successfully fetched lyrics from Genius: {title}")
            
            if lyrics:
                # Save to cache
                self.cache.save_lyrics(
                    song_id, title, artist, lyrics,
                    source=source, genius_url=url
                )
                # Also save locally with nice filename
                self.cache.save_local_lyrics(song_id, title, artist, lyrics)
                
                self.is_fetching = False
                return {
                    "id": song_id,
                    "title": title,
                    "artist": artist,
                    "lyrics": lyrics,
                    "source": source,
                    "url": url,
                }
            
            self.is_fetching = False
            return None
        
        except Exception as e:
            logger.error(f"Error fetching and caching lyrics: {e}")
            self.is_fetching = False
            return None
    
    def delete_lyrics(self, song_id: int):
        """Remove lyrics for a specific song from cache"""
        self.cache.save_lyrics(song_id, "", "", "", source="empty")
        logger.info(f"Cleared cache for song {song_id}")

    def fetch_async(self, song_id: int, title: str, artist: str,
                   callback=None, force: bool = False):
        """Fetch lyrics asynchronously
        
        Args:
            song_id: Song ID
            title: Song title
            artist: Artist name
            callback: Function to call with results
            force: If True, bypass cache logic (already handled by caller usually)
        """
        import threading
        
        if force:
            self.delete_lyrics(song_id)

        def fetch_thread():
            # Use get_lyrics which checks cache FIRST before network
            result = self.get_lyrics(song_id, title, artist, auto_fetch=True)
            if callback:
                callback(result)
        
        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()
    
    def clear_cache(self) -> bool:
        """Clear all cached lyrics
        
        Returns:
            True if cleared
        """
        try:
            conn = sqlite3.connect(self.cache.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lyrics")
            conn.commit()
            conn.close()
            logger.info("Lyrics cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def export_lyrics(self, output_dir: str = "lyrics_export") -> int:
        """Export all cached lyrics to files
        
        Args:
            output_dir: Directory to export to
        
        Returns:
            Number of files exported
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            conn = sqlite3.connect(self.cache.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT song_id, title, artist, lyrics FROM lyrics WHERE lyrics IS NOT NULL")
            rows = cursor.fetchall()
            conn.close()
            
            count = 0
            for song_id, title, artist, lyrics in rows:
                filename = f"{artist} - {title}.txt"
                # Clean filename
                filename = "".join(c for c in filename if c.isalnum() or c in " -._")
                
                filepath = output_path / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"{title}\n{artist}\n\n{lyrics}")
                
                count += 1
            
            logger.info(f"Exported {count} lyrics files to {output_dir}")
            return count
        
        except Exception as e:
            logger.error(f"Error exporting lyrics: {e}")
            return 0


# ============================================================================
# SIMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example usage
    manager = LyricsManager()
    
    # Get lyrics (auto-fetch if not cached)
    lyrics = manager.get_lyrics(1, "Blinding Lights", "The Weeknd")
    
    if lyrics:
        print(f"Found lyrics for: {lyrics['title']}")
        print(f"Source: {lyrics['source']}")
        print(f"First 200 chars: {lyrics['lyrics'][:200]}...")
    else:
        print("No lyrics found")
    
    # Get cache stats
    stats = manager.cache.get_cache_stats()
    print(f"Cache stats: {stats}")