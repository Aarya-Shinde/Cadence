
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
from mutagen.id3 import ID3
import logging

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}

class MetadataReader:
    """Extract metadata from audio files"""
    
    @staticmethod
    def get_duration(file_path):
        """Get duration in seconds"""
        try:
            if file_path.suffix.lower() == '.mp3':
                audio = MP3(file_path)
            elif file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
            elif file_path.suffix.lower() == '.wav':
                audio = WAVE(file_path)
            elif file_path.suffix.lower() in {'.m4a', '.aac'}:
                audio = MP4(file_path)
            else:
                return 0
            
            return int(audio.info.length) if audio.info.length else 0
        except Exception as e:
            logger.warning(f"Could not read duration for {file_path}: {e}")
            return 0
    
    @staticmethod
    def get_tags(file_path):
        """Extract ID3/metadata tags"""
        try:
            if file_path.suffix.lower() == '.mp3':
                # Try ID3v2 first, then ID3v1
                audio = MP3(file_path, ID3=ID3)
                tags = audio if audio.tags else None
                
                return {
                    'title': str(tags.get('TIT2', 'Unknown Title')) if tags else 'Unknown Title',
                    'artist': str(tags.get('TPE1', 'Unknown Artist')) if tags else 'Unknown Artist',
                    'album': str(tags.get('TALB', 'Unknown Album')) if tags else 'Unknown Album',
                }
            
            elif file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
                return {
                    'title': audio.get('title', ['Unknown Title'])[0],
                    'artist': audio.get('artist', ['Unknown Artist'])[0],
                    'album': audio.get('album', ['Unknown Album'])[0],
                }
            
            elif file_path.suffix.lower() in {'.m4a', '.aac'}:
                audio = MP4(file_path)
                return {
                    'title': str(audio.get('\xa9nam', ['Unknown Title'])[0]) if '\xa9nam' in audio else 'Unknown Title',
                    'artist': str(audio.get('\xa9ART', ['Unknown Artist'])[0]) if '\xa9ART' in audio else 'Unknown Artist',
                    'album': str(audio.get('\xa9alb', ['Unknown Album'])[0]) if '\xa9alb' in audio else 'Unknown Album',
                }
            
            else:
                return None
        
        except Exception as e:
            logger.warning(f"Could not read tags from {file_path}: {e}")
            return None
    
    @staticmethod
    def parse_filename(file_path):
        """Fallback: Parse title from filename if tags missing
        
        Supports: "Artist - Title.mp3" or just "Title.mp3"
        """
        filename = file_path.stem  # Remove extension
        
        if ' - ' in filename:
            parts = filename.split(' - ', 1)
            return {
                'artist': parts[0].strip(),
                'title': parts[1].strip(),
                'album': 'Unknown Album'
            }
        else:
            return {
                'artist': 'Unknown Artist',
                'title': filename.strip(),
                'album': 'Unknown Album'
            }
    
    @staticmethod
    def read_song(file_path):
        """Read complete metadata for a song
        
        Returns:
            dict with keys: title, artist, album, duration (in seconds), path
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            logger.warning(f"Unsupported format: {file_path.suffix}")
            return None
        
        # Try to read tags first
        tags = MetadataReader.get_tags(file_path)
        
        # Fallback to filename parsing if no tags
        if not tags:
            logger.debug(f"No tags found for {file_path.name}, using filename")
            tags = MetadataReader.parse_filename(file_path)
        
        duration = MetadataReader.get_duration(file_path)
        
        return {
            'title': tags['title'],
            'artist': tags['artist'],
            'album': tags['album'],
            'duration': duration,
            'path': str(file_path.absolute())
        }


# Helper function for easy imports
def read_music_file(file_path):
    """Convenience function"""
    return MetadataReader.read_song(file_path)