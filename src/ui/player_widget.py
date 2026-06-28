
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QStyle, QStyleOptionSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QVariantAnimation, QEasingCurve, QPropertyAnimation, QTimer, QPointF, QRect
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QPainter
from pathlib import Path
import logging
import random
 
from ui.style import Colors, Fonts
from ui.icons import get_icon
from ui.truncated_label import TruncatedLabel
 
logger = logging.getLogger(__name__)
 
 
class StardustParticle:
    """Stardust particle constrained to travel inside the progress bar channel."""
    def __init__(self, rect):
        # Spawn randomly inside the sub-page rect
        self.x = random.uniform(rect.left(), rect.right())
        # Centered vertically in the groove
        self.y = random.uniform(rect.top() + 1, rect.bottom() - 1)
        self.vx = random.uniform(0.3, 1.2)  # travel left-to-right
        self.vy = random.uniform(-0.15, 0.15)  # subtle vertical drift
        self.size = random.uniform(1.2, 2.5)
        self.max_life = random.randint(20, 45)  # 30 FPS frames
        self.life = self.max_life
        self.color = random.choice(["#FFFFFF", Colors.ACCENT_SUBTLE, Colors.ACCENT_HOVER])

    def update(self, rect):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        
        # Keep inside vertical bounds of the groove
        if self.y < rect.top():
            self.y = rect.top()
            self.vy = -self.vy
        elif self.y > rect.bottom():
            self.y = rect.bottom()
            self.vy = -self.vy
            
        # Kill if it goes beyond the handle (right edge of sub-page)
        if self.x > rect.right():
            self.life = 0

    def is_dead(self) -> bool:
        return self.life <= 0


class ClickSlider(QSlider):
    """QSlider subclass that jumps to click position, optionally with smooth animation and internal stardust"""
    def __init__(self, orientation, animate_clicks=False, show_stardust=False, parent=None):
        super().__init__(orientation, parent)
        self.animate_clicks = animate_clicks
        self.show_stardust = show_stardust
        
        if animate_clicks:
            self._anim = QPropertyAnimation(self, b"value")
            self._anim.setDuration(180)
            self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            
        if show_stardust:
            self.particles = []
            self.particle_timer = QTimer(self)
            self.particle_timer.timeout.connect(self._update_particles)
            self.particle_timer.start(33) # ~30 FPS
            self.last_value = self.value()

    def _get_sub_page_rect(self) -> QRect:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self
        )
        handle_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self
        )
        
        if not groove_rect.isEmpty() and not handle_rect.isEmpty():
            left = groove_rect.left()
            right = handle_rect.center().x()
            top = groove_rect.top()
            height = groove_rect.height()
            return QRect(left, top, max(0, right - left), height)
        return QRect()

    def _update_particles(self):
        if not self.show_stardust:
            return
            
        rect = self._get_sub_page_rect()
        if rect.isEmpty() or rect.width() < 10:
            self.particles.clear()
            self.update()
            return
            
        # Update existing particles
        for p in self.particles:
            p.update(rect)
        self.particles = [p for p in self.particles if not p.is_dead()]
        
        # Spawn new particles randomly inside the sub-page
        if len(self.particles) < 15 and random.random() < 0.25:
            self.particles.append(StardustParticle(rect))
            
        self.update() # Repaint

    def paintEvent(self, event):
        # Draw base slider first
        super().paintEvent(event)
        
        if not self.show_stardust or not self.particles:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for p in self.particles:
            alpha = int((p.life / p.max_life) * 255)
            color = QColor(p.color)
            color.setAlpha(max(0, min(255, alpha)))
            
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            size = p.size
            # Draw beautiful diamond star shapes inside the track
            points = [
                QPointF(p.x, p.y - size),
                QPointF(p.x + size * 0.7, p.y),
                QPointF(p.x, p.y + size),
                QPointF(p.x - size * 0.7, p.y)
            ]
            painter.drawPolygon(points)
            
        painter.end()

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
                val = int(self.minimum() + (self.maximum() - self.minimum()) * pos)
                
                if self.animate_clicks:
                    self._anim.stop()
                    self._anim.setStartValue(self.value())
                    self._anim.setEndValue(val)
                    self._anim.start()
                else:
                    self.setValue(val)
                    # Emit signals immediately
                    self.sliderMoved.emit(self.value())
                    self.valueChanged.emit(self.value())
                event.accept()
                return
                
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
 
 
# ============================================================================
# ANIMATED PLAYER BUTTON
# ============================================================================

class AnimatedPlayerButton(QPushButton):
    """Custom player control button with hover scale and background animations."""
    def __init__(self, icon_name: str, tooltip: str = "", base_size: int = 32, icon_size: int = 18, is_checkable: bool = False, is_play_btn: bool = False, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.is_checkable = is_checkable
        self.is_play_btn = is_play_btn
        self.setCheckable(is_checkable)
        self.setFixedSize(base_size, base_size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
            
        self.base_icon_size = icon_size
        self.current_icon_size = icon_size
        
        # Determine background behavior
        if self.is_play_btn:
            self.current_bg = QColor(Colors.ACCENT_PRIMARY)
        else:
            self.current_bg = QColor(0, 0, 0, 0)
            
        # Load icon
        self.update_icon()
        
        # Animation for icon scaling
        self.icon_anim = QVariantAnimation(self)
        self.icon_anim.setDuration(120)
        self.icon_anim.valueChanged.connect(self._animate_icon_size)
        
        # Animation for background color fade
        self.bg_anim = QVariantAnimation(self)
        self.bg_anim.setDuration(150)
        self.bg_anim.valueChanged.connect(self._animate_bg_color)
        
        self.update_style()
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked):
        self.update_icon()
        self.update_style()

    def setChecked(self, checked):
        super().setChecked(checked)
        self.update_icon()
        self.update_style()

    def update_icon(self):
        name = self.icon_name
        
        # Color rules
        if self.is_play_btn:
            color = Colors.BACKGROUND_PRIMARY
        elif name == "heart-filled":
            color = Colors.ERROR  # Red for favorite
        elif self.isChecked():
            color = Colors.ACCENT_PRIMARY
        else:
            color = Colors.TEXT_SECONDARY
            
        self.setIcon(get_icon(name, color=color))
        self.setIconSize(QSize(self.current_icon_size, self.current_icon_size))

    def _animate_icon_size(self, value):
        self.current_icon_size = value
        self.setIconSize(QSize(value, value))

    def _animate_bg_color(self, color):
        self.current_bg = color
        self.update_style()

    def update_style(self):
        if self.is_play_btn:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {Colors.ACCENT_HOVER},
                        stop:1 {Colors.ACCENT_PRIMARY});
                    border: none;
                    border-radius: {self.width() // 2}px;
                }}
                QPushButton:pressed {{
                    background-color: {Colors.ACCENT_ACTIVE};
                }}
            """)
        else:
            bg_rgba = f"rgba({self.current_bg.red()}, {self.current_bg.green()}, {self.current_bg.blue()}, {self.current_bg.alphaF()})"
            
            if self.isChecked():
                self.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(177, 156, 217, 0.15);
                        border-radius: 6px;
                        border: 1px solid rgba(177, 156, 217, 0.3);
                    }}
                """)
            else:
                self.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_rgba};
                        border-radius: 6px;
                        border: 1px solid transparent;
                    }}
                """)

    def enterEvent(self, event):
        self.icon_anim.stop()
        self.icon_anim.setStartValue(self.current_icon_size)
        self.icon_anim.setEndValue(self.base_icon_size + 4)
        self.icon_anim.start()
        
        if not self.isChecked() and not self.is_play_btn:
            self.bg_anim.stop()
            self.bg_anim.setStartValue(self.current_bg)
            self.bg_anim.setEndValue(QColor(Colors.BACKGROUND_TERTIARY))
            self.bg_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.icon_anim.stop()
        self.icon_anim.setStartValue(self.current_icon_size)
        self.icon_anim.setEndValue(self.base_icon_size)
        self.icon_anim.start()
        
        if not self.isChecked() and not self.is_play_btn:
            self.bg_anim.stop()
            self.bg_anim.setStartValue(self.current_bg)
            self.bg_anim.setEndValue(QColor(0, 0, 0, 0))
            self.bg_anim.start()
        super().leaveEvent(event)
 
 
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
        self.setStyleSheet("QWidget { background: transparent; }")
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 6, 16, 12)
        main_layout.setSpacing(12)  # Balanced spacing
        
        # ===== PROGRESS SECTION (Top) =====
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)
        
        self.time_label = QLabel("0:00")
        self.time_label.setFont(Fonts.BODY_TINY)
        self.time_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; min-width: 32px;")
        progress_layout.addWidget(self.time_label)
        
        self.progress_slider = ClickSlider(Qt.Orientation.Horizontal, show_stardust=True)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        left_layout.setSpacing(12)
        # Album art placeholder - Main Cadence desktop icon
        self.album_art_label = QLabel()
        self.album_art_label.setFixedSize(48, 48)
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_path = Path(__file__).parent.parent / "assets" / "desktop icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.album_art_label.setPixmap(scaled)
        else:
            self.album_art_label.setPixmap(get_icon(Icons.MUSIC).pixmap(32, 32))
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
        
        self.now_playing_title = TruncatedLabel("No song playing")
        self.now_playing_title.setFont(Fonts.BODY_LARGE)
        self.now_playing_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500;")
        self.now_playing_title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(self.now_playing_title)
        
        self.now_playing_artist = TruncatedLabel("Select a song to play")
        self.now_playing_artist.setFont(Fonts.BODY_SMALL)
        self.now_playing_artist.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.now_playing_artist.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(self.now_playing_artist)
        
        left_layout.addLayout(info_layout, 1)  # Allow metadata to expand
        
        controls_layout.addWidget(left_widget, 1) # Expand this side to match right side (1:1 ratio)
        
        # Center: Playback controls
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(20)
        
        self.prev_btn = AnimatedPlayerButton(Icons.PREVIOUS, "Previous Track (Shift+P)", base_size=36, icon_size=16)
        self.prev_btn.clicked.connect(self.previous_clicked.emit)
        center_layout.addWidget(self.prev_btn)
        
        self.play_btn = AnimatedPlayerButton(Icons.PLAY, "Play (Space)", base_size=48, icon_size=22, is_play_btn=True)
        self.play_btn.clicked.connect(self._on_play_pause)
        center_layout.addWidget(self.play_btn)
        
        self.next_btn = AnimatedPlayerButton(Icons.NEXT, "Next Track (Shift+N)", base_size=36, icon_size=16)
        self.next_btn.clicked.connect(self.next_clicked.emit)
        center_layout.addWidget(self.next_btn)
        
        controls_layout.addWidget(center_widget)
        
        # Right: Volume controls
        right_widget = QWidget()
        volume_layout = QHBoxLayout(right_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(6)
        volume_layout.addStretch()
        
        # Favorite button (now in utility group next to shuffle)
        self.fav_btn = AnimatedPlayerButton("heart", tooltip="Mark as Favorite", base_size=36, icon_size=16)
        self.fav_btn.clicked.connect(self.favorite_toggled.emit)
        volume_layout.addWidget(self.fav_btn)
        
        self.shuffle_btn = AnimatedPlayerButton(Icons.SHUFFLE, "Shuffle", base_size=36, icon_size=16, is_checkable=True)
        self.shuffle_btn.clicked.connect(self._on_shuffle_click)
        volume_layout.addWidget(self.shuffle_btn)
        
        self.repeat_btn = AnimatedPlayerButton(Icons.REPEAT, "Repeat", base_size=36, icon_size=16, is_checkable=True)
        self.repeat_btn.clicked.connect(self._on_repeat_click)
        volume_layout.addWidget(self.repeat_btn)
        
        volume_layout.addSpacing(10)
        
        self.volume_icon = AnimatedPlayerButton(Icons.VOLUME, "Mute/Unmute", base_size=36, icon_size=16)
        self.volume_icon.clicked.connect(self._on_volume_icon_clicked)
        volume_layout.addWidget(self.volume_icon)
        
        self.last_volume = 80 # Default for unmuting
        
        self.volume_slider = ClickSlider(Qt.Orientation.Horizontal, animate_clicks=True)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.volume_slider.setStyleSheet(self._get_volume_style())
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_text = QLabel("80%")
        self.volume_text.setFont(Fonts.BODY_TINY)
        self.volume_text.setFixedWidth(35)
        self.volume_text.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        volume_layout.addWidget(self.volume_text)
        
        controls_layout.addWidget(right_widget, 1) # Expand to match left side width (1:1 ratio)
        
        main_layout.addLayout(controls_layout)
        self.setLayout(main_layout)
        

    
    def _get_progress_style(self) -> str:
        """Get progress slider styling — Spotify-style with interactive hover accent"""
        return f"""
            QSlider {{
                outline: none;
            }}
            QSlider::groove:horizontal {{
                height: 7px;
                background: {Colors.BACKGROUND_TERTIARY};
                border-radius: 3px;
                border: none;
            }}

            QSlider::handle:horizontal {{
                background: {Colors.TEXT_PRIMARY};
                border: none;
                width: 12px;
                height: 12px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 6px;
            }}

            QSlider:hover::groove:horizontal {{
                height: 9px;
                background: {Colors.BORDER_LIGHT};
                border-radius: 4px;
            }}

            QSlider:hover::handle:horizontal {{
                background: {Colors.TEXT_PRIMARY};
                border: none;
                width: 16px;
                height: 16px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 8px;
            }}

            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ACCENT_SUBTLE},
                    stop:1 {Colors.ACCENT_PRIMARY});
                border-radius: 3px;
            }}

            QSlider:hover::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ACCENT_PRIMARY},
                    stop:1 {Colors.ACCENT_HOVER});
                border-radius: 4px;
            }}

            QSlider::add-page:horizontal {{
                background: {Colors.BACKGROUND_TERTIARY};
                border-radius: 3px;
            }}
            
            QSlider:hover::add-page:horizontal {{
                border-radius: 4px;
            }}
        """
    
    def _get_volume_style(self) -> str:
        """Get volume slider styling — interactive hover pill style"""
        return f"""
            QSlider {{
                outline: none;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {Colors.BORDER_LIGHT};
                border-radius: 3px;
                border: none;
            }}

            QSlider::handle:horizontal {{
                background: {Colors.TEXT_PRIMARY};
                border: none;
                width: 12px;
                height: 12px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 6px;
            }}

            QSlider:hover::groove:horizontal {{
                height: 8px;
                background: {Colors.BACKGROUND_TERTIARY};
                border-radius: 4px;
            }}

            QSlider:hover::handle:horizontal {{
                background: {Colors.TEXT_PRIMARY};
                border: none;
                width: 16px;
                height: 16px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 8px;
            }}

            QSlider::sub-page:horizontal {{
                background: {Colors.ACCENT_PRIMARY};
                border-radius: 3px;
            }}

            QSlider:hover::sub-page:horizontal {{
                background: {Colors.ACCENT_HOVER};
                border-radius: 4px;
            }}

            QSlider::add-page:horizontal {{
                background: {Colors.BORDER_LIGHT};
                border-radius: 3px;
            }}
            
            QSlider:hover::add-page:horizontal {{
                border-radius: 4px;
            }}
        """
    
    def set_now_playing(self, title: str, artist: str, is_favorite: bool = False):
        """Update now playing display"""
        self.now_playing_title.setText(title)
        self.now_playing_artist.setText(artist)
        self.update_favorite_state(is_favorite)
        
    def update_favorite_state(self, is_favorite: bool):
        """Update the heart icon state"""
        self.fav_btn.icon_name = "heart-filled" if is_favorite else "heart"
        self.fav_btn.update_icon()
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
            self.volume_icon.icon_name = Icons.MUTE
        else:
            self.volume_icon.icon_name = Icons.VOLUME
        self.volume_icon.update_icon()

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
            self.play_btn.icon_name = Icons.PAUSE
            self.play_btn.setToolTip("Pause (Space)")
        else:
            self.play_btn.icon_name = Icons.PLAY
            self.play_btn.setToolTip("Play (Space)")
        self.play_btn.update_icon()
    
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