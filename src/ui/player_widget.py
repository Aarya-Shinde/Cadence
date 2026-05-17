
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QStyle, QStyleOptionSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon
import logging
 
from ui.style import Colors, Fonts
from ui.icons import get_icon
from ui.truncated_label import TruncatedLabel
 
logger = logging.getLogger(__name__)
 
 
class ClickSlider(QSlider):
    """QSlider subclass that jumps to click position"""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            
            # Use the style to get the exact groove rectangle for precision
            groove_rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, 
                QStyle.SubControl.SC_SliderGroove, self
            )
            
            if self.orientation() == Qt.Orientation.Horizontal:
                slider_length = groove_rect.width()
                slider_pos = event.position().x() - groove_rect.x()
            else:
                slider_length = groove_rect.height()
                slider_pos = groove_rect.height() - (event.position().y() - groove_rect.y())
            
            if slider_length > 0:
                pos = max(0, min(slider_pos / slider_length, 1.0))
                val = self.minimum() + (self.maximum() - self.minimum()) * pos
                self.setValue(int(val))
                
                # Emit signals immediately
                self.sliderMoved.emit(self.value())
                self.valueChanged.emit(self.value())
                
        super().mousePressEvent(event)

class Icons:
    """Icons for player controls"""
    PLAY = "play"
    PAUSE = "pause"
    PREVIOUS = "previous"
    NEXT = "next"
    VOLUME = "volume"
    MUTE = "volume-mute"
    MUSIC = "music"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"
 
 
class EnhancedPlayerWidget(QWidget):
    """Modern player widget with icons and transitions"""
    
    # Signals
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    volume_changed = pyqtSignal(float)
    progress_seek = pyqtSignal(float)
    shuffle_toggled = pyqtSignal(bool)
    repeat_toggled = pyqtSignal(bool)
    favorite_toggled = pyqtSignal() # Emitted when heart in player bar is clicked
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # State
        self.is_playing = False
        self.current_time = 0
        self.total_time = 0
        self.is_seeking = False
        self.is_shuffle = False
        self.is_repeat = False
    
    def setup_ui(self):
        """Create enhanced player UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 8, 16, 12)
        main_layout.setSpacing(12)  # Balanced spacing
        
        # ===== PROGRESS SECTION (Top) =====
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)
        
        self.time_label = QLabel("0:00")
        self.time_label.setFont(Fonts.BODY_TINY)
        self.time_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; min-width: 32px;")
        progress_layout.addWidget(self.time_label)
        
        self.progress_slider = ClickSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.setStyleSheet(self._get_progress_style())
        self.progress_slider.sliderMoved.connect(self._on_progress_seek)
        self.progress_slider.sliderPressed.connect(self._on_progress_pressed)
        self.progress_slider.sliderReleased.connect(self._on_progress_released)
        progress_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("0:00")
        self.duration_label.setFont(Fonts.BODY_TINY)
        self.duration_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; min-width: 32px; text-align: right;")
        progress_layout.addWidget(self.duration_label)
        
        main_layout.addLayout(progress_layout)
        
        # ===== CONTROL ROW (Bottom) =====
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Left side: Now playing info
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        # Album art placeholder
        self.album_art_label = QLabel()
        self.album_art_label.setPixmap(get_icon(Icons.MUSIC).pixmap(32, 32))
        self.album_art_label.setFixedSize(48, 48)
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                border-radius: 4px;
                color: {Colors.ACCENT_PRIMARY};
                padding: 8px;
            }}
        """)
        left_layout.addWidget(self.album_art_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Title and Favorite button in a row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.now_playing_title = TruncatedLabel("No song playing")
        self.now_playing_title.setFont(Fonts.BODY_LARGE)
        self.now_playing_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500;")
        self.now_playing_title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        title_row.addWidget(self.now_playing_title)
        
        # Favorite button (now after title)
        self.fav_btn = QPushButton()
        self.fav_btn.setIcon(get_icon("heart"))
        self.fav_btn.setIconSize(QSize(28, 28))
        self.fav_btn.setFixedSize(40, 40)
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {Colors.TEXT_TERTIARY};
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT_PRIMARY};
            }}
        """)
        self.fav_btn.clicked.connect(self.favorite_toggled.emit)
        title_row.addWidget(self.fav_btn)
        title_row.addStretch()
        
        info_layout.addLayout(title_row)
        
        self.now_playing_artist = TruncatedLabel("Select a song to play")
        self.now_playing_artist.setFont(Fonts.BODY_SMALL)
        self.now_playing_artist.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.now_playing_artist.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        info_layout.addWidget(self.now_playing_artist)
        
        left_layout.addLayout(info_layout)
        left_layout.addStretch()
        
        controls_layout.addWidget(left_widget, 1) # Expand this side to match right side
        
        # Center: Playback controls
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(20)
        
        self.prev_btn = self._create_control_button(Icons.PREVIOUS, "Previous Track (Shift+P)")
        self.prev_btn.clicked.connect(self.previous_clicked.emit)
        center_layout.addWidget(self.prev_btn)
        
        self.play_btn = self._create_play_button()
        self.play_btn.clicked.connect(self._on_play_pause)
        center_layout.addWidget(self.play_btn)
        
        self.next_btn = self._create_control_button(Icons.NEXT, "Next Track (Shift+N)")
        self.next_btn.clicked.connect(self.next_clicked.emit)
        center_layout.addWidget(self.next_btn)
        
        controls_layout.addWidget(center_widget)
        
        # Right: Volume controls
        right_widget = QWidget()
        volume_layout = QHBoxLayout(right_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(6)
        volume_layout.addStretch()
        
        self.shuffle_btn = self._create_toggle_button(Icons.SHUFFLE, "Shuffle")
        self.shuffle_btn.clicked.connect(self._on_shuffle_click)
        volume_layout.addWidget(self.shuffle_btn)
        
        self.repeat_btn = self._create_toggle_button(Icons.REPEAT, "Repeat")
        self.repeat_btn.clicked.connect(self._on_repeat_click)
        volume_layout.addWidget(self.repeat_btn)
        
        volume_layout.addSpacing(10)
        
        self.volume_icon = QPushButton()
        self.volume_icon.setIcon(get_icon(Icons.VOLUME))
        self.volume_icon.setIconSize(QSize(18, 18))
        self.volume_icon.setFixedSize(28, 28)
        self.volume_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_icon.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {Colors.TEXT_TERTIARY}; }}
            QPushButton:hover {{ color: {Colors.ACCENT_PRIMARY}; }}
        """)
        self.volume_icon.clicked.connect(self._on_volume_icon_clicked)
        volume_layout.addWidget(self.volume_icon)
        
        self.last_volume = 80 # Default for unmuting
        
        self.volume_slider = ClickSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.setStyleSheet(self._get_volume_style())
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_text = QLabel("80%")
        self.volume_text.setFont(Fonts.BODY_TINY)
        self.volume_text.setFixedWidth(35)
        self.volume_text.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        volume_layout.addWidget(self.volume_text)
        
        controls_layout.addWidget(right_widget, 1) # Expand to match left side width
        
        main_layout.addLayout(controls_layout)
        self.setLayout(main_layout)
        
    def _create_toggle_button(self, icon_name: str, tooltip: str) -> QPushButton:
        """Create a toggleable mode button (shuffle/repeat)"""
        btn = QPushButton()
        btn.setIcon(get_icon(icon_name))
        btn.setIconSize(QSize(18, 18))
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {Colors.TEXT_TERTIARY};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                color: {Colors.ACCENT_PRIMARY};
                background-color: rgba(144, 98, 248, 0.15);
            }}
        """)
        return btn
    
    def _create_control_button(self, icon_name: str, tooltip: str) -> QPushButton:
        """Create control button (Previous/Next)"""
        btn = QPushButton()
        btn.setIcon(get_icon(icon_name))
        btn.setIconSize(QSize(22, 22))
        btn.setFixedSize(44, 44)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_COLOR};
                border-radius: 6px;
                padding: 0;
                font-size: 16pt;
            }}
            
            QPushButton:hover {{
                background-color: {Colors.BACKGROUND_ACCENT};
                border-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.ACCENT_PRIMARY};
            }}
            
            QPushButton:pressed {{
                background-color: {Colors.ACCENT_ACTIVE};
                border-color: {Colors.ACCENT_ACTIVE};
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        return btn
    
    def _create_play_button(self) -> QPushButton:
        """Create large play/pause button"""
        btn = QPushButton()
        btn.setIcon(get_icon(Icons.PLAY))
        btn.setIconSize(QSize(28, 28))
        btn.setFixedSize(56, 56)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Colors.ACCENT_HOVER},
                    stop:1 {Colors.ACCENT_PRIMARY});
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 28px;
                padding: 0;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Colors.ACCENT_HOVER},
                    stop:1 {Colors.ACCENT_HOVER});
            }}
            
            QPushButton:pressed {{
                background-color: {Colors.ACCENT_ACTIVE};
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn
    
    def _get_progress_style(self) -> str:
        """Get progress slider styling — Spotify-style with purple accent"""
        return f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {Colors.BACKGROUND_TERTIARY};
                border-radius: 2px;
                border: none;
            }}

            QSlider::handle:horizontal {{
                background: {Colors.ACCENT_PRIMARY};
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}

            QSlider::handle:horizontal:hover {{
                background: {Colors.ACCENT_HOVER};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}

            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ACCENT_SUBTLE},
                    stop:1 {Colors.ACCENT_PRIMARY});
                border-radius: 2px;
            }}

            QSlider::add-page:horizontal {{
                background: {Colors.BACKGROUND_TERTIARY};
                border-radius: 2px;
            }}
        """
    
    def _get_volume_style(self) -> str:
        """Get volume slider styling — thin pill style with purple accent"""
        return f"""
            QSlider::groove:horizontal {{
                height: 3px;
                background: {Colors.BORDER_LIGHT};
                border-radius: 1px;
                border: none;
            }}

            QSlider::handle:horizontal {{
                background: {Colors.ACCENT_PRIMARY};
                border: none;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }}

            QSlider::handle:horizontal:hover {{
                background: {Colors.ACCENT_HOVER};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}

            QSlider::sub-page:horizontal {{
                background: {Colors.ACCENT_PRIMARY};
                border-radius: 1px;
            }}

            QSlider::add-page:horizontal {{
                background: {Colors.BORDER_LIGHT};
                border-radius: 1px;
            }}
        """
    
    def set_now_playing(self, title: str, artist: str, is_favorite: bool = False):
        """Update now playing display"""
        self.now_playing_title.setText(title)
        self.now_playing_artist.setText(artist)
        self.update_favorite_state(is_favorite)
        
    def update_favorite_state(self, is_favorite: bool):
        """Update the heart icon state"""
        self.fav_btn.setIcon(get_icon("heart-filled" if is_favorite else "heart"))
        self.fav_btn.setToolTip("Unfavorite" if is_favorite else "Mark as Favorite")
    
    def set_total_duration(self, seconds: int):
        """Set total song duration"""
        self.total_time = seconds
        self.progress_slider.setMaximum(1000)
        self.duration_label.setText(self._format_time(seconds))
    
    def update_progress(self, current_time: float):
        self.current_time = current_time
        if not self.is_seeking and self.total_time > 0:
            value = int((current_time / self.total_time) * 1000)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(value)
            self.progress_slider.blockSignals(False)
        
        self.time_label.setText(self._format_time(current_time))
    
    def _on_play_pause(self):
        """Handle play/pause click"""
        if self.is_playing:
            self.pause_clicked.emit()
            self.is_playing = False
        else:
            self.play_clicked.emit()
            self.is_playing = True
    
    def _on_progress_seek(self, value):
        if self.total_time > 0:
            seconds = (value / 1000.0) * self.total_time
            self.progress_seek.emit(seconds)
            self.time_label.setText(self._format_time(seconds))

    def _on_progress_pressed(self):
        self.is_seeking = True

    def _on_progress_released(self):
        self.is_seeking = False
        self._on_progress_seek(self.progress_slider.value())
    
    def _on_volume_changed(self, value):
        """Handle volume change"""
        volume = value / 100.0
        self.volume_changed.emit(volume)
        self.volume_text.setText(f"{value}%")
        self.update_volume_icon(volume)
        
    def update_volume_icon(self, volume: float):
        """Update volume icon based on level"""
        if volume <= 0:
            self.volume_icon.setIcon(get_icon("volume-mute"))
        else:
            self.volume_icon.setIcon(get_icon("volume"))

    def _on_volume_icon_clicked(self):
        """Toggle mute"""
        current = self.volume_slider.value()
        if current > 0:
            self.last_volume = current
            self.volume_slider.setValue(0)
        else:
            self.volume_slider.setValue(self.last_volume)
        
    def _on_shuffle_click(self):
        """Toggle shuffle"""
        self.is_shuffle = self.shuffle_btn.isChecked()
        self.shuffle_toggled.emit(self.is_shuffle)
        
    def _on_repeat_click(self):
        """Toggle repeat"""
        self.is_repeat = self.repeat_btn.isChecked()
        self.repeat_toggled.emit(self.is_repeat)
    
    def set_playing_state(self, is_playing: bool):
        """Update play/pause button"""
        self.is_playing = is_playing
        if is_playing:
            self.play_btn.setIcon(get_icon(Icons.PAUSE))
            self.play_btn.setToolTip("Pause (Space)")
        else:
            self.play_btn.setIcon(get_icon(Icons.PLAY))
            self.play_btn.setToolTip("Play (Space)")
    
    def wheelEvent(self, event):
        """Handle mouse wheel for volume control anywhere on the player bar"""
        delta = event.angleDelta().y()
        change = 5 if delta > 0 else -5
        current = self.volume_slider.value()
        self.volume_slider.setValue(max(0, min(100, current + change)))
        event.accept()

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as MM:SS"""
        if seconds < 0:
            return "0:00"
        
        total_secs = int(seconds)
        minutes = total_secs // 60
        secs = total_secs % 60
        return f"{minutes}:{secs:02d}"