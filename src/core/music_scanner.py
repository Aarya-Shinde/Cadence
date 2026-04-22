
import logging
from pathlib import Path
from typing import List, Callable
import hashlib
import threading
from utils.metadata_reader import MetadataReader, SUPPORTED_FORMATS
from core.database import MusicDatabase

logger = logging.getLogger(__name__)

class MusicScanner:
    """Scan music folders and index songs"""
    
    def __init__(self, db: MusicDatabase):
        self.db = db
        self.is_scanning = False
    
    def get_music_files(self, folder_path: str) -> List[Path]:
        """Recursively find all music files in folder
        
        Args:
            folder_path: Path to music folder
        
        Returns:
            List of Path objects for music files
        """
        folder = Path(folder_path)
        
        if not folder.exists():
            logger.error(f"Folder not found: {folder_path}")
            return []
        
        if not folder.is_dir():
            logger.error(f"Not a directory: {folder_path}")
            return []
        
        music_files = []
        
        try:
            # Recursively search for supported formats
            for ext in SUPPORTED_FORMATS:
                music_files.extend(folder.rglob(f'*{ext}'))
            
            logger.info(f"Found {len(music_files)} music files in {folder_path}")
            return sorted(music_files)
        
        except PermissionError as e:
            logger.error(f"Permission denied accessing {folder_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")
            return []
    
    def scan_folder(self, folder_path: str, progress_callback: Callable = None):
        """Scan a folder and add new songs to database
        
        Args:
            folder_path: Path to music folder
            progress_callback: Optional function(current, total) for UI updates
        
        Returns:
            dict with results: {added: int, duplicates: int, errors: int}
        """
        if self.is_scanning:
            logger.warning("Already scanning, skipping...")
            return {'added': 0, 'duplicates': 0, 'errors': 0}
        
        self.is_scanning = True
        results = {'added': 0, 'duplicates': 0, 'removed': 0, 'errors': 0}
        
        try:
            music_files = self.get_music_files(folder_path)
            total = len(music_files)
            
            logger.info(f"Starting scan of {total} files")
            
            for index, file_path in enumerate(music_files):
                if progress_callback:
                    progress_callback(index + 1, total)
                
                # Read metadata
                metadata = MetadataReader.read_song(file_path)
                
                if not metadata:
                    results['errors'] += 1
                    logger.warning(f"Could not read metadata: {file_path}")
                    continue
                
                # Try to add to database
                is_new = self.db.add_song(
                    title=metadata['title'],
                    artist=metadata['artist'],
                    album=metadata['album'],
                    duration=metadata['duration'],
                    path=metadata['path']
                )
                
                if is_new:
                    results['added'] += 1
                    logger.debug(f"Added: {metadata['title']} by {metadata['artist']}")
                else:
                    results['duplicates'] += 1
                    logger.debug(f"Already in DB: {file_path.name}")
            
            # PASS 2: Cleanup Pass - Remove orphaned database entries
            removed = self.cleanup_orphaned_songs(folder_path)
            results['removed'] = removed
            
            logger.info(f"Scan complete. Added: {results['added']}, "
                       f"Duplicates: {results['duplicates']}, "
                       f"Removed: {results['removed']}, "
                       f"Errors: {results['errors']}")
            
            return results
        
        finally:
            self.is_scanning = False
            
    def cleanup_orphaned_songs(self, folder_path: str) -> int:
        """Find and remove songs from DB that no longer exist on disk"""
        try:
            songs = self.db.get_all_songs()
            removed_count = 0
            search_path = Path(folder_path).resolve()
            
            for song in songs:
                song_path = Path(song['path']).resolve()
                
                # Check if this song belongs to the folder we are scanning
                try:
                    if str(song_path).startswith(str(search_path)):
                        if not song_path.exists():
                            self.db.remove_song_by_id(song['id'])
                            removed_count += 1
                            logger.info(f"Deleted orphaned entry: {song['title']}")
                except Exception as e:
                    logger.error(f"Error checking file existence for {song['path']}: {e}")
                    
            return removed_count
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def scan_folder_async(self, folder_path: str, 
                         progress_callback: Callable = None,
                         completion_callback: Callable = None):
        """Run scan in background thread (non-blocking UI)
        
        Args:
            folder_path: Path to scan
            progress_callback: function(current, total) for progress updates
            completion_callback: function(results) called when done
        """
        def scan_thread():
            results = self.scan_folder(folder_path, progress_callback)
            if completion_callback:
                completion_callback(results)
        
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()
    
    def get_all_songs(self) -> List[dict]:
        """Get all songs from database"""
        return self.db.get_all_songs()
    
    def get_song_count(self) -> int:
        """Get total number of songs in database"""
        return self.db.get_song_count()


# Convenience functions
def quick_scan(folder_path: str, db: MusicDatabase):
    """Quick one-liner to scan a folder"""
    scanner = MusicScanner(db)
    return scanner.scan_folder(folder_path)