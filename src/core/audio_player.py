import pygame
import logging
from pathlib import Path
from typing import Callable, Optional
import threading
import time
import os
import ctypes

logger = logging.getLogger(__name__)

def _prevent_sleep(prevent: bool):
    """Prevent or allow Windows from sleeping and turning off display"""
    if os.name == 'nt':
        try:
            # ES_CONTINUOUS = 0x80000000
            # ES_SYSTEM_REQUIRED = 0x00000001
            # ES_DISPLAY_REQUIRED = 0x00000002
            if prevent:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception as e:
            logger.debug(f"Could not set thread execution state: {e}")

class AudioPlayer:
    """Audio playback engine using pygame-mixer"""
    
    def __init__(self):
        # Initialize pygame mixer
        try:
            pygame.mixer.init()
            logger.info("Pygame mixer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")
            raise
        
        # State variables
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.current_duration = 0
        self.current_position = 0
        self.volume = 0.8  # 0.0 to 1.0
        
        # Callbacks
        self.on_track_ended = None
        self.on_position_changed = None
        
        # Background thread for position tracking
        self.position_thread = None
        self.should_track_position = False
    
    def load(self, file_path: str) -> bool:
        """Load an audio file
        
        Args:
            file_path: Path to audio file
        
        Returns:
            True if loaded successfully
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Stop current playback
            if self.is_playing or self.is_paused:
                self.stop()
            
            # Load the file
            pygame.mixer.music.load(str(file_path))
            self.current_file = str(file_path)
            self.is_playing = False
            self.is_paused = False
            
            # Get duration (mutagen for accuracy)
            try:
                from mutagen.mp3 import MP3
                from mutagen.flac import FLAC
                
                if file_path.suffix.lower() == '.mp3':
                    audio = MP3(file_path)
                elif file_path.suffix.lower() == '.flac':
                    audio = FLAC(file_path)
                else:
                    # For other formats, we'll update during playback
                    self.current_duration = 0
                    return True
                
                self.current_duration = int(audio.info.length) if audio.info.length else 0
            except Exception as e:
                logger.warning(f"Could not get duration: {e}")
                self.current_duration = 0
            
            logger.info(f"Loaded: {file_path.name} ({self.current_duration}s)")
            return True
        
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return False
    
    def play(self) -> bool:
        """Start playback
        
        Returns:
            True if playing
        """
        try:
            if not self.current_file:
                logger.warning("No file loaded")
                return False
            
            if self.is_paused:
                # Resume from pause
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.is_playing = True
                logger.debug("Resumed playback")
            else:
                # Start from beginning
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.current_position = 0
                logger.debug("Started playback")
            
            # Start position tracking thread
            self._start_position_tracking()
            _prevent_sleep(True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error playing: {e}")
            return False
    
    def pause(self) -> bool:
        """Pause playback
        
        Returns:
            True if paused
        """
        try:
            if not self.is_playing:
                return False
            
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            self._stop_position_tracking()
            _prevent_sleep(False)
            logger.debug("Paused playback")
            return True
        
        except Exception as e:
            logger.error(f"Error pausing: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop playback
        
        Returns:
            True if stopped
        """
        try:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_position = 0
            self._stop_position_tracking()
            _prevent_sleep(False)
            logger.debug("Stopped playback")
            return True
        
        except Exception as e:
            logger.error(f"Error stopping: {e}")
            return False
    
    def seek(self, seconds: float) -> bool:
        """Seek to a position in the song
        
        Args:
            seconds: Position in seconds
        
        Returns:
            True if seeked successfully
        """
        try:
            if seconds < 0 or seconds > self.current_duration:
                return False
            
            if self.is_playing or self.is_paused:
                was_playing = self.is_playing
                current_file = self.current_file
                
                # Nuclear seek: Stop, Load, Play(start)
                # This is the most compatible way for MP3s in pygame-mixer
                pygame.mixer.music.stop()
                pygame.mixer.music.load(current_file)
                pygame.mixer.music.play(0, seconds)
                
                self.current_position = seconds
                
                if not was_playing:
                    pygame.mixer.music.pause()
                    self.is_paused = True
                    self.is_playing = False
                else:
                    self.is_playing = True
                    self.is_paused = False
                    # Make sure thread is running
                    self._start_position_tracking()
            else:
                self.current_position = seconds
            
            logger.info(f"Seeked to {seconds:.1f}s (Forced Reload)")
            return True
        
        except Exception as e:
            logger.error(f"Error seeking: {e}")
            return False
    
    def set_volume(self, volume: float):
        """Set volume level
        
        Args:
            volume: 0.0 (mute) to 1.0 (max)
        """
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp 0-1
            pygame.mixer.music.set_volume(volume)
            self.volume = volume
            logger.debug(f"Volume set to {volume:.1%}")
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
    
    def get_volume(self) -> float:
        """Get current volume level"""
        return self.volume
    
    def is_playing_track(self) -> bool:
        """Check if currently playing"""
        return self.is_playing
    
    def is_paused_track(self) -> bool:
        """Check if currently paused"""
        return self.is_paused
    
    def get_current_position(self) -> float:
        """Get current playback position in seconds
        
        Note: This is approximate for pygame-mixer
        """
        return self.current_position
    
    def get_duration(self) -> float:
        """Get total duration of current track"""
        return self.current_duration
    
    def _start_position_tracking(self):
        """Start background thread to track position"""
        if self.should_track_position:
            return
        
        self.should_track_position = True
        
        def track_position():
            while self.should_track_position:
                if self.is_playing:
                    # Update position approximately
                    self.current_position += 0.1  # Update every 100ms
                    
                    # Check if track ended
                    if not pygame.mixer.music.get_busy():
                        self._on_track_ended()
                        break
                    
                    # Notify UI of position change
                    if self.on_position_changed:
                        self.on_position_changed(self.current_position)
                
                time.sleep(0.1)
        
        self.position_thread = threading.Thread(target=track_position, daemon=True)
        self.position_thread.start()
    
    def _stop_position_tracking(self):
        """Stop position tracking thread"""
        self.should_track_position = False
    
    def _on_track_ended(self):
        """Handle track ending"""
        self.is_playing = False
        self.current_position = 0
        self._stop_position_tracking()
        _prevent_sleep(False)
        
        if self.on_track_ended:
            self.on_track_ended()
        
        logger.info("Track ended")
    
    def __del__(self):
        """Cleanup on exit"""
        _prevent_sleep(False)
        try:
            pygame.mixer.quit()
        except:
            pass