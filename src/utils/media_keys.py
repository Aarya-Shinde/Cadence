# src/utils/media_keys.py
import logging
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class MediaKeyInterceptor(QObject):
    """Listens for global media keys and emits Qt signals safely to the main thread"""
    
    play_pause_pressed = pyqtSignal()
    next_pressed = pyqtSignal()
    prev_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.listener = None
    
    def start(self):
        """Start listening for media keys in the background"""
        if self.listener:
            return
            
        def on_press(key):
            try:
                if key == keyboard.Key.media_play_pause:
                    logger.debug("Global Media Key Detected: Play/Pause")
                    self.play_pause_pressed.emit()
                elif key == keyboard.Key.media_next:
                    logger.debug("Global Media Key Detected: Next")
                    self.next_pressed.emit()
                elif key == keyboard.Key.media_previous:
                    logger.debug("Global Media Key Detected: Previous")
                    self.prev_pressed.emit()
            except Exception as e:
                logger.error(f"Error handling media key: {e}")
                
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()
        logger.info("Global media key listener active in background")
        
    def stop(self):
        """Stop the background listener"""
        if self.listener:
            self.listener.stop()
            self.listener = None
