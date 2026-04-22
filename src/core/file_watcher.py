
import logging
from pathlib import Path
from typing import Callable
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from core.music_scanner import MusicScanner
from core.database import MusicDatabase

logger = logging.getLogger(__name__)

class MusicFolderHandler(FileSystemEventHandler):
    """Handle file system events in music folder"""
    
    def __init__(self, scanner: MusicScanner, rescan_callback: Callable = None):
        self.scanner = scanner
        self.rescan_callback = rescan_callback
        self.last_scan_time = 0
        self.debounce_seconds = 2  # Wait 2 seconds before rescanning
    
    def on_created(self, event):
        """Called when a file is created"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's a music file
        if file_path.suffix.lower() in {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}:
            logger.info(f"New file detected: {file_path.name}")
            self._trigger_rescan()
    
    def on_deleted(self, event):
        """Called when a file is deleted"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if file_path.suffix.lower() in {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}:
            logger.info(f"File deleted: {file_path.name}")
            # Remove from database
            self.scanner.db.remove_song_by_path(str(file_path.absolute()))
            if self.rescan_callback:
                self.rescan_callback({'removed': 1})
    
    def on_modified(self, event):
        """Called when a file is modified - ignore to avoid spam"""
        # File modifications can trigger multiple events, so we ignore them
        # to prevent unnecessary rescans
        pass
    
    def _trigger_rescan(self):
        """Debounced rescan trigger"""
        current_time = time.time()
        
        # Only rescan if 2+ seconds since last scan
        if current_time - self.last_scan_time >= self.debounce_seconds:
            self.last_scan_time = current_time
            logger.debug("Triggering rescan due to file changes")
            
            # Rescan just to pick up new files
            results = self.scanner.scan_folder(
                self.scanner.watched_folder
            )
            
            if self.rescan_callback:
                self.rescan_callback(results)


class MusicFileWatcher:
    """Monitor music folder for changes"""
    
    def __init__(self, db: MusicDatabase):
        self.db = db
        self.scanner = MusicScanner(db)
        self.observer = None
        self.watched_folder = None
    
    def start_watching(self, folder_path: str, 
                      rescan_callback: Callable = None):
        """Start watching a music folder
        
        Args:
            folder_path: Path to music folder
            rescan_callback: function(results) called when changes detected
        """
        folder = Path(folder_path)
        
        if not folder.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            return False
        
        self.watched_folder = folder_path
        self.scanner.watched_folder = folder_path
        
        # Create and configure the event handler
        handler = MusicFolderHandler(self.scanner, rescan_callback)
        
        # Create and start the observer
        self.observer = Observer()
        self.observer.schedule(handler, str(folder), recursive=True)
        self.observer.start()
        
        logger.info(f"Started watching folder: {folder_path}")
        return True
    
    def stop_watching(self):
        """Stop watching the folder"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching folder")
    
    def is_watching(self) -> bool:
        """Check if currently watching"""
        return self.observer is not None and self.observer.is_alive()