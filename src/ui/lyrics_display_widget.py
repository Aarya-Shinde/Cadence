# src/ui/lyrics_display_widget.py - Lyrics & Album Art Display

"""
Beautiful Lyrics & Album Art Display:
- Large album art display
- Scrolling lyrics with highlighting
- Real-time sync (future)
- Fallback UI when lyrics not available
- Load indicator for fetching
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QPixmap, QColor
from PyQt6.QtCore import QEasingCurve
from pathlib import Path
import logging

from ui.style import Colors, Fonts
from ui.icons import get_icon

logger = logging.getLogger(__name__)


# ============================================================================
# ALBUM ART DISPLAY
# ============================================================================

class AlbumArtDisplay(QWidget):
    """Display album art with fallback"""
    
    def __init__(self, size: int = 200):
        super().__init__()
        self.size = size
        self.art_label = QLabel()
        self.art_label.setFixedSize(size, size)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                border: 2px solid {Colors.ACCENT_PRIMARY};
                border-radius: 12px;
                padding: 0;
                color: {Colors.ACCENT_PRIMARY};
                font-size: 80pt;
            }}
        """)
        
        # Set placeholder
        self.set_placeholder()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.art_label)
        self.setLayout(layout)
    
    def set_image(self, image_path: str) -> bool:
        """Set album art from file
        
        Args:
            image_path: Path to image file
        
        Returns:
            True if loaded successfully
        """
        try:
            if not Path(image_path).exists():
                return False
            
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return False
            
            # Scale to size
            scaled = pixmap.scaledToWidth(
                self.size,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.art_label.setPixmap(scaled)
            logger.info(f"Album art loaded: {image_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading album art: {e}")
            return False
    
    def set_placeholder(self):
        """Set placeholder image"""
        self.art_label.setText("♫")
    
    def clear(self):
        """Clear image"""
        self.set_placeholder()


# ============================================================================
# LYRICS DISPLAY
# ============================================================================

# ============================================================================
# LYRICS DISPLAY (Synchronized & Stylish)
# ============================================================================

class LyricsLine(QLabel):
    """A single line of lyrics with highlighting"""
    def __init__(self, text: str):
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setFont(Fonts.BODY_LARGE)
        self.set_active(False)
        self.id = -1
        
    def set_active(self, active: bool):
        """Toggle active state with stylish coloring"""
        if active:
            # Active: White and bold (Spotify high-light)
            self.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-weight: 700;
                    font-size: 16pt;
                    padding: 8px 0;
                    background: transparent;
                }}
            """)
        else:
            # Inactive: Faded grey
            self.setStyleSheet(f"""
                QLabel {{
                    color: rgba(255, 255, 255, 0.4);
                    font-weight: 400;
                    font-size: 14pt;
                    padding: 6px 0;
                    background: transparent;
                }}
            """)

class LyricsDisplay(QWidget):
    """Modern synchronized lyrics scroller"""
    
    retry_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.synced_data = [] # List of {'time': s, 'text': t}
        self.line_widgets = []
        self.current_line_idx = -1
        self.is_synced = False
        self.setup_ui()
    
    def setup_ui(self):
        """Create high-end lyrics interface with Spotify-style fades"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroller Container Frame (allows overlays)
        container = QFrame()
        container.setObjectName("LyricsContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Scroller
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent;")
        
        # 2. Content
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(30, 200, 30, 200) # Large vertical margins for centering
        self.content_layout.setSpacing(12)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.content)
        container_layout.addWidget(self.scroll)
        
        # 3. Apply Gradient Overlays (Spotify Style)
        container.setStyleSheet(f"""
            QFrame#LyricsContainer {{
                background-color: {Colors.BACKGROUND_SECONDARY};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER_COLOR};
            }}
        """)
        
        main_layout.addWidget(container, 1)
        
        # Sync Status & Retry (Bottom bar)
        footer = QHBoxLayout()
        footer.setContentsMargins(15, 10, 15, 10)
        
        self.status_label = QLabel("⦿ Ready")
        self.status_label.setFont(Fonts.BODY_TINY)
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        footer.addWidget(self.status_label)
        
        footer.addStretch()
        
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setIcon(get_icon("trash")) # Or refresh if we had one, trash/reset works
        self.retry_btn.setToolTip("Wrong lyrics? Click to re-fetch")
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.setFixedWidth(80)
        self.retry_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 9pt;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: white;
                border: 1px solid {Colors.ACCENT_PRIMARY};
            }}
        """)
        self.retry_btn.clicked.connect(self.retry_requested.emit)
        footer.addWidget(self.retry_btn)
        
        main_layout.addLayout(footer)
        
        self.setLayout(main_layout)
        
    def set_lyrics(self, title: str, artist: str, lyrics_text: str):
        """Load and parse lyrics (Detects if LRC or plain)"""
        # Clear existing
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self.content_layout.removeItem(item)
                
        self.line_widgets = []
        self.synced_data = []
        self.current_line_idx = -1
        
        # 1. Add Track Header (Title & Artist)
        title_item = QLabel(title)
        title_item.setFont(Fonts.HEADING_LARGE)
        title_item.setWordWrap(True)
        title_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_item.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        self.content_layout.addWidget(title_item)
        
        artist_item = QLabel(artist)
        artist_item.setFont(Fonts.BODY_LARGE)
        artist_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
        artist_item.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; margin-bottom: 30px;")
        self.content_layout.addWidget(artist_item)
        
        from utils.lyrics_fetcher import LrcParser
        parsed = LrcParser.parse(lyrics_text)
        
        if parsed:
            # Synchronized mode
            self.synced_data = parsed
            self.is_synced = True
            self.status_label.setText("⦿ Synced")
            for i, line in enumerate(parsed):
                widget = LyricsLine(line['text'])
                widget.id = i
                self.line_widgets.append(widget)
                self.content_layout.addWidget(widget)
        else:
            # Plain text mode
            self.is_synced = False
            self.status_label.setText("Plain Text")
            for line in lyrics_text.splitlines():
                if line.strip():
                    widget = LyricsLine(line.strip())
                    widget.set_active(True) # All visible
                    self.content_layout.addWidget(widget)
                    self.line_widgets.append(widget)
                    
        # Add stretch at start/end to allow centering
        self.content_layout.addStretch()
        
        # Force layout update so widget positions are calculated immediately
        self.content.adjustSize()
        
        # Reset to beginning
        QTimer.singleShot(100, lambda: self.update_time(0))

    def update_time(self, current_time: float):
        """Update active line based on music progress"""
        if not self.is_synced or not self.synced_data:
            return
            
        new_idx = -1
        for i, line in enumerate(self.synced_data):
            if current_time >= line['time']:
                new_idx = i
            else:
                break
        
        if new_idx != self.current_line_idx and new_idx < len(self.line_widgets):
            try:
                # Deactivate old
                if self.current_line_idx >= 0 and self.current_line_idx < len(self.line_widgets):
                    self.line_widgets[self.current_line_idx].set_active(False)
                
                # Activate new
                self.current_line_idx = new_idx
                if new_idx >= 0:
                    widget = self.line_widgets[new_idx]
                    widget.set_active(True)
                    self._scroll_to_widget(widget)
            except RuntimeError:
                # Widget was likely deleted during a song change
                pass
                
    def _scroll_to_widget(self, widget: QWidget):
        """Smoothly scroll to the active line and center it"""
        scroll_bar = self.scroll.verticalScrollBar()
        
        # We need a small delay or check to ensure layout is updated
        # Pos is relative to self.content
        target_y = widget.pos().y()
        
        # Center target: target_y - (scroll_area_height / 2) + (widget_height / 2)
        v_height = self.scroll.viewport().height()
        if v_height <= 0: v_height = self.scroll.height() # Fallback
        
        center_offset = (v_height - widget.height()) / 2
        target_pos = target_y - center_offset
        
        # Ensure it stays within bounds
        target_pos = max(0, min(target_pos, scroll_bar.maximum()))
        
        # Animation for smooth scroll
        if hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.State.Running:
            self.anim.stop()
            
        self.anim = QPropertyAnimation(scroll_bar, b"value")
        self.anim.setDuration(400)
        self.anim.setStartValue(scroll_bar.value())
        self.anim.setEndValue(int(target_pos))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def set_loading(self):
        """Show loading state"""
        self.status_label.setText("Loading...")
        
        # STOP SYNC IMMEDIATELY
        self.is_synced = False
        self.synced_data = []
        self.current_line_idx = -1
        
        # Clear content and show one loading label
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.line_widgets = []
        
        loader = LyricsLine("Fetching synced lyrics...")
        loader.set_active(True)
        self.content_layout.addWidget(loader)
        
    def set_not_found(self, title: str = ""):
        """Show not found state"""
        self.status_label.setText("Not found")
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        msg = LyricsLine(f"No synced lyrics found for '{title}'")
        msg.set_active(True)
        self.content_layout.addWidget(msg)
        
    def clear(self):
        """Clear lyrics"""
        self.set_lyrics("", "", "")
        self.status_label.setText("Ready")


# ============================================================================
# COMBINED DISPLAY WIDGET
# ============================================================================

class SongDetailsPanel(QWidget):
    """Combined album art and lyrics display"""
    
    fetch_lyrics = pyqtSignal(int, str, str)  # song_id, title, artist
    retry_lyrics = pyqtSignal(int, str, str)  # song_id, title, artist
    
    def __init__(self):
        super().__init__()
        self._current_song_id = -1
        self.setup_ui()
    
    def setup_ui(self):
        """Create UI layout"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(16)
        
        # Left: Album art
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        
        self.album_art = AlbumArtDisplay(size=280)
        left_layout.addWidget(self.album_art)
        
        # Song info
        self.info_frame = QFrame()
        self.info_frame.setFixedWidth(280)  # Match album art width
        self.info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                border-radius: 12px;
                padding: 8px 12px;
            }}
        """)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.song_title = QLabel("No song")
        self.song_title.setFont(Fonts.HEADING_SMALL)
        self.song_title.setWordWrap(True)
        self.song_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600;")
        info_layout.addWidget(self.song_title)
        
        self.song_artist = QLabel("")
        self.song_artist.setFont(Fonts.BODY_SMALL)
        self.song_artist.setWordWrap(True)
        self.song_artist.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(self.song_artist)
        
        self.song_album = QLabel("")
        self.song_album.setFont(Fonts.BODY_SMALL)
        self.song_album.setWordWrap(True)
        self.song_album.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        info_layout.addWidget(self.song_album)
        
        self.info_frame.setLayout(info_layout)
        left_layout.addWidget(self.info_frame)
        left_layout.addStretch()
        
        main_layout.addLayout(left_layout)
        
        # Right: Lyrics
        self.lyrics_display = LyricsDisplay()
        self.lyrics_display.retry_requested.connect(self._on_retry_requested)
        main_layout.addWidget(self.lyrics_display, 1)
        
        self.setLayout(main_layout)
    
    def _on_retry_requested(self):
        """Forward retry request with current song info"""
        if self._current_song_id != -1:
            self.retry_lyrics.emit(
                self._current_song_id,
                self.song_title.text(),
                self.song_artist.text()
            )
    
    def set_song(self, song_info: dict, art_path: str = None):
        """Set song and load lyrics/art
        
        Args:
            song_info: Dict with title, artist, album, id
            art_path: Path to album art
        """
        # Update info
        self._current_song_id = song_info.get("id", -1)
        self.song_title.setText(song_info.get("title", "Unknown"))
        self.song_artist.setText(song_info.get("artist", "Unknown Artist"))
        self.song_album.setText(song_info.get("album", "Unknown Album"))
        
        # Load album art
        if art_path:
            self.album_art.set_image(art_path)
        else:
            self.album_art.set_placeholder()
        
        # Show loading for lyrics
        self.lyrics_display.set_loading()
        
        # Emit signal to fetch lyrics
        self.fetch_lyrics.emit(
            song_info.get("id", -1),
            song_info.get("title", ""),
            song_info.get("artist", "")
        )
    
    def set_lyrics(self, lyrics_text: str):
        """Set lyrics content"""
        if not lyrics_text:
            self.lyrics_display.set_not_found(self.song_title.text())
            return
        
        self.lyrics_display.set_lyrics(
            self.song_title.text(),
            self.song_artist.text(),
            lyrics_text
        )
        
    def update_time(self, seconds: float):
        """Update lyrics sync"""
        self.lyrics_display.update_time(seconds)
    
    def clear(self):
        """Clear content"""
        self.song_title.setText("No song")
        self.song_artist.setText("")
        self.song_album.setText("")
        self.album_art.clear()
        self.lyrics_display.clear()