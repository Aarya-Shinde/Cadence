
import sqlite3
from pathlib import Path
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

from utils.paths import DB_PATH as _DEFAULT_DB

class MusicDatabase:
    def __init__(self, db_path=_DEFAULT_DB):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY,
                title TEXT,
                artist TEXT,
                album TEXT,
                duration INTEGER,
                path TEXT UNIQUE,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                play_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_song(self, title, artist, album, duration, path):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO songs 
                (title, artist, album, duration, path) 
                VALUES (?, ?, ?, ?, ?)
            ''', (title, artist, album, duration, path))

            conn.commit()

            is_new = cursor.rowcount > 0  # IMPORTANT

            conn.close()
            return is_new

        except Exception as e:
            logger.error(f"Error adding song: {e}")
            return False

    # Add these methods to your MusicDatabase class

    def remove_song_by_path(self, file_path: str) -> bool:
        """Remove a song from database by file path"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM songs WHERE path = ?', (file_path,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"Error removing song: {e}")
            return False

    def song_exists_by_path(self, file_path: str) -> bool:
        """Check if a song already exists in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM songs WHERE path = ?', (file_path,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking song: {e}")
            return False

    def get_all_songs(self) -> list:
        """Get all songs from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, artist, album, duration, path, date_added FROM songs ORDER BY artist, album, title')
            columns = ['id', 'title', 'artist', 'album', 'duration', 'path', 'date_added']
            songs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            return songs
        except Exception as e:
            logger.error(f"Error fetching songs: {e}")
            return []

    def get_song_count(self) -> int:
        """Get total number of songs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM songs')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error counting songs: {e}")
            return 0

    def update_song_play_count(self, song_id: int):
        """Increment play count for a song"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE songs SET play_count = play_count + 1 WHERE id = ?', (song_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating play count: {e}")   

    def remove_song_by_id(self, song_id: int) -> bool:
        """Remove a song by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"Error removing song: {e}")
            return False

    def clear_all_songs(self):
        """Clear entire library"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM songs')
            conn.commit()
            conn.close()
            logger.info("All songs cleared from database")
        except Exception as e:
            logger.error(f"Error clearing songs: {e}")

    
        conn.commit()
        conn.close()