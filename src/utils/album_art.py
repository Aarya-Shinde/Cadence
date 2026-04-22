# src/utils/album_art.py - Album Art Extraction & Caching

"""
Album Art Management:
- Extract from audio files (ID3, FLAC, M4A)
- Cache locally (PNG/JPG)
- Display with fallbacks
- Search online if needed
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import sqlite3
from PIL import Image
from io import BytesIO
import hashlib

from utils.paths import DB_PATH as _DEFAULT_DB, ALBUM_ART_DIR as _DEFAULT_ART_DIR

logger = logging.getLogger(__name__)


# ============================================================================
# ALBUM ART EXTRACTOR
# ============================================================================

class AlbumArtExtractor:
    """Extract album art from audio files"""
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.m4a', '.wav', '.ogg'}
    
    @staticmethod
    def extract_from_mp3(file_path: str) -> Optional[bytes]:
        """Extract album art from MP3 files
        
        Args:
            file_path: Path to MP3 file
        
        Returns:
            Image bytes or None
        """
        try:
            from mutagen.id3 import ID3
            
            file_path = str(file_path)
            
            try:
                tags = ID3(file_path)
            except:
                return None
            
            # Look for APIC frames (attached picture)
            for key, frame in tags.items():
                if key.startswith("APIC"):
                    return frame.data
            
            return None
        
        except ImportError:
            logger.warning("mutagen not available for MP3 extraction")
            return None
        except Exception as e:
            logger.debug(f"Error extracting MP3 art: {e}")
            return None
    
    @staticmethod
    def extract_from_flac(file_path: str) -> Optional[bytes]:
        """Extract album art from FLAC files
        
        Args:
            file_path: Path to FLAC file
        
        Returns:
            Image bytes or None
        """
        try:
            from mutagen.flac import FLAC
            
            audio = FLAC(str(file_path))
            
            if audio.pictures:
                return audio.pictures[0].data
            
            return None
        
        except ImportError:
            logger.warning("mutagen not available for FLAC extraction")
            return None
        except Exception as e:
            logger.debug(f"Error extracting FLAC art: {e}")
            return None
    
    @staticmethod
    def extract_from_m4a(file_path: str) -> Optional[bytes]:
        """Extract album art from M4A files
        
        Args:
            file_path: Path to M4A file
        
        Returns:
            Image bytes or None
        """
        try:
            from mutagen.mp4 import MP4
            
            audio = MP4(str(file_path))
            
            # Look for covr tag (cover art)
            if "covr" in audio:
                covers = audio["covr"]
                if covers:
                    return covers[0]
            
            return None
        
        except ImportError:
            logger.warning("mutagen not available for M4A extraction")
            return None
        except Exception as e:
            logger.debug(f"Error extracting M4A art: {e}")
            return None
    
    @staticmethod
    def extract(file_path: str) -> Optional[bytes]:
        """Extract album art from any supported audio file
        
        Args:
            file_path: Path to audio file
        
        Returns:
            Image bytes or None
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.mp3':
            return AlbumArtExtractor.extract_from_mp3(file_path)
        elif suffix == '.flac':
            return AlbumArtExtractor.extract_from_flac(file_path)
        elif suffix in {'.m4a', '.aac'}:
            return AlbumArtExtractor.extract_from_m4a(file_path)
        
        return None


# ============================================================================
# ALBUM ART CACHE
# ============================================================================

class AlbumArtCache:
    """Manage album art cache"""
    
    def __init__(self, cache_dir: str = _DEFAULT_ART_DIR, 
                 db_path: str = _DEFAULT_DB):
        """Initialize album art cache
        
        Args:
            cache_dir: Directory to cache images
            db_path: Database path
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize album art table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS album_art (
                    id INTEGER PRIMARY KEY,
                    song_id INTEGER NOT NULL,
                    album TEXT,
                    artist TEXT,
                    cache_path TEXT,
                    source TEXT,
                    width INTEGER,
                    height INTEGER,
                    hash TEXT UNIQUE,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Album art database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing album art DB: {e}")
    
    def save_art(self, song_id: int, album: str, artist: str, 
                 image_data: bytes, source: str = "file") -> Optional[str]:
        """Save album art to cache
        
        Args:
            song_id: Song ID
            album: Album name
            artist: Artist name
            image_data: Image bytes
            source: Source (file, online, manual)
        
        Returns:
            Cache path or None
        """
        try:
            # Validate image
            try:
                img = Image.open(BytesIO(image_data))
            except:
                logger.warning("Invalid image data")
                return None
            
            # Resize if too large (keep aspect ratio)
            max_size = (500, 500)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Calculate hash to avoid duplicates
            image_hash = hashlib.md5(image_data).hexdigest()
            
            # Check if already cached
            if self._get_by_hash(image_hash):
                logger.debug(f"Image already in cache: {image_hash}")
                return None
            
            # Save image
            filename = f"{song_id}_{artist}_{album}.png"
            # Clean filename
            filename = "".join(c for c in filename if c.isalnum() or c in " -._")
            
            cache_path = self.cache_dir / filename
            img.save(str(cache_path), "PNG")
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO album_art
                (song_id, album, artist, cache_path, source, width, height, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (song_id, album, artist, str(cache_path), source, img.width, img.height, image_hash))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Album art saved: {cache_path}")
            return str(cache_path)
        
        except Exception as e:
            logger.error(f"Error saving album art: {e}")
            return None
    
    def get_art(self, song_id: int) -> Optional[str]:
        """Get cached album art path
        
        Args:
            song_id: Song ID
        
        Returns:
            Cache path or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cache_path FROM album_art WHERE song_id = ? LIMIT 1
            """, (song_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and Path(row[0]).exists():
                return row[0]
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting album art: {e}")
            return None
    
    def _get_by_hash(self, image_hash: str) -> Optional[str]:
        """Get cache path by image hash
        
        Args:
            image_hash: MD5 hash of image
        
        Returns:
            Cache path or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT cache_path FROM album_art WHERE hash = ?", (image_hash,))
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
        except:
            return None
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM album_art")
            count = cursor.fetchone()[0]
            
            # Calculate total size
            total_size = sum(
                Path(p).stat().st_size 
                for p in self.cache_dir.glob("*") 
                if Path(p).is_file()
            )
            
            conn.close()
            
            return {
                "cached_images": count,
                "cache_size_mb": total_size / (1024 * 1024),
                "cache_dir": str(self.cache_dir),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def clear_cache(self) -> bool:
        """Clear all cached images"""
        try:
            # Delete files
            for file in self.cache_dir.glob("*"):
                if file.is_file():
                    file.unlink()
            
            # Clear database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM album_art")
            conn.commit()
            conn.close()
            
            logger.info("Album art cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# ============================================================================
# INTEGRATED ALBUM ART MANAGER
# ============================================================================

class AlbumArtManager:
    """High-level album art management"""
    
    def __init__(self, cache_dir: str = _DEFAULT_ART_DIR,
                 db_path: str = _DEFAULT_DB):
        """Initialize manager
        
        Args:
            cache_dir: Cache directory
            db_path: Database path
        """
        self.extractor = AlbumArtExtractor()
        self.cache = AlbumArtCache(cache_dir, db_path)
    
    def get_art(self, song_id: int, file_path: str, 
                album: str = "Unknown", artist: str = "Unknown",
                auto_extract: bool = True) -> Optional[str]:
        """Get album art, extracting if necessary
        
        Args:
            song_id: Song ID
            file_path: Audio file path
            album: Album name
            artist: Artist name
            auto_extract: Auto-extract if not cached
        
        Returns:
            Cache path or None
        """
        # Try cache first
        cached = self.cache.get_art(song_id)
        if cached:
            return cached
        
        # Extract if requested
        if auto_extract:
            image_data = self.extractor.extract(file_path)
            if image_data:
                return self.cache.save_art(song_id, album, artist, image_data)
        
        return None
    
    def get_art_async(self, song_id: int, file_path: str,
                     album: str = "Unknown", artist: str = "Unknown",
                     callback=None):
        """Get album art asynchronously
        
        Args:
            song_id: Song ID
            file_path: Audio file path
            album: Album name
            artist: Artist name
            callback: Callback function
        """
        import threading
        
        def extract_thread():
            result = self.get_art(song_id, file_path, album, artist)
            if callback:
                callback(result)
        
        thread = threading.Thread(target=extract_thread, daemon=True)
        thread.start()
    
    def get_placeholder_art(self, size: int = 256) -> bytes:
        """Generate placeholder album art
        
        Args:
            size: Image size
        
        Returns:
            PNG bytes
        """
        try:
            # Create placeholder image
            img = Image.new('RGB', (size, size), color='#1C1F3A')
            
            # Add text
            try:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                # Simple text - no font needed, uses default
                draw.text((size//2-20, size//2-10), "♫", fill='#B19CD9')
            except:
                pass
            
            # Convert to bytes
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error creating placeholder: {e}")
            return None