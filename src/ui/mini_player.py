
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QFont, QIcon, QMouseEvent

from ui.style import Colors, Fonts
from ui.icons import get_icon

class MiniPlayer(QWidget):
    """Ultra-compact standalone mini player window"""
    
    restore_requested = pyqtSignal()
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    favorite_toggled = pyqtSignal()
    volume_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 100)
        self.setup_ui()
        
        self._drag_pos = QPoint()
        
    def setup_ui(self):
        self.setObjectName("miniPlayer")
        self.setStyleSheet(f"""
            QWidget#miniPlayer {{
                background-color: {Colors.BACKGROUND_PRIMARY};
                border: 1px solid {Colors.ACCENT_PRIMARY};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Top Row: Favorite + Back Button
        top_row = QHBoxLayout()
        
        self.fav_btn = QPushButton()
        self.fav_btn.setIcon(get_icon("heart", color="white"))
        self.fav_btn.setFixedSize(24, 24)
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.setStyleSheet("QPushButton { border: none; background: transparent; color: white; }")
        self.fav_btn.clicked.connect(self.favorite_toggled.emit)
        top_row.addWidget(self.fav_btn)
        
        top_row.addStretch()
        
        self.restore_btn = QPushButton("")
        self.restore_btn.setIcon(get_icon("arrow-up-right", color="white"))
        self.restore_btn.setIconSize(QSize(14, 14))
        self.restore_btn.setFixedSize(32, 28)
        self.restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {Colors.ACCENT_PRIMARY};
                border-radius: 6px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {Colors.ACCENT_PRIMARY};
            }}
            QPushButton:pressed {{
                background: {Colors.ACCENT_ACTIVE};
                border-color: {Colors.ACCENT_ACTIVE};
            }}
        """)
        self.restore_btn.clicked.connect(self.restore_requested.emit)
        top_row.addWidget(self.restore_btn)
        
        layout.addLayout(top_row)
        
        # Middle Row: Song Info + Controls
        content_row = QHBoxLayout()
        content_row.setSpacing(15)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.title_label = QLabel("Not Playing")
        self.title_label.setFont(Fonts.BODY_LARGE)
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600;")
        info_layout.addWidget(self.title_label)
        
        self.artist_label = QLabel("Select a song")
        self.artist_label.setFont(Fonts.BODY_TINY)
        self.artist_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_layout.addWidget(self.artist_label)
        
        content_row.addLayout(info_layout, 1)
        
        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        self.prev_btn = self._create_btn("previous")
        self.prev_btn.clicked.connect(self.prev_clicked.emit)
        controls_layout.addWidget(self.prev_btn)
        
        self.play_btn = self._create_btn("play")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.clicked.connect(self._on_play_pause)
        controls_layout.addWidget(self.play_btn)
        
        self.next_btn = self._create_btn("next")
        self.next_btn.clicked.connect(self.next_clicked.emit)
        controls_layout.addWidget(self.next_btn)
        
        content_row.addLayout(controls_layout)
        
        layout.addLayout(content_row)
        
        # Bottom: Slim Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1000) # Use 1000 for smooth micro-steps
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: transparent;
                border: none;
                margin: 0;
                padding: 0;
            }}
            QProgressBar::chunk {{
                background: {Colors.ACCENT_PRIMARY};
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        self.is_playing = False

    def _create_btn(self, icon_name):
        btn = QPushButton()
        btn.setIcon(get_icon(icon_name))
        btn.setFixedSize(30, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BACKGROUND_SECONDARY};
                border-radius: 15px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background: {Colors.BACKGROUND_TERTIARY};
            }}
        """)
        return btn

    def set_favorite(self, is_fav):
        self.fav_btn.setIcon(get_icon("heart-filled" if is_fav else "heart", color="white"))

    def set_song(self, title, artist, is_fav=False):
        self.title_label.setText(title)
        self.artist_label.setText(artist)
        self.set_favorite(is_fav)

    def update_progress(self, current, total):
        if total > 0:
            val = int((current / total) * 1000)
            self.progress_bar.setValue(val)

    def set_playing_state(self, playing):
        self.is_playing = playing
        self.play_btn.setIcon(get_icon("pause" if playing else "play"))

    def _on_play_pause(self):
        if self.is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def wheelEvent(self, event):
        """Handle mouse wheel for volume control"""
        delta = event.angleDelta().y()
        # Adjust volume in 5% increments
        change = 0.05 if delta > 0 else -0.05
        self.volume_changed.emit(change)
        event.accept()

    # Mouse handling for dragging the frameless window
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            self._snap_to_edges()
            event.accept()

    def _snap_to_edges(self):
        """Snap window to screen edges if close enough (20px)"""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        pos = self.pos()
        snap_dist = 20
        
        new_x = pos.x()
        new_y = pos.y()
        
        # Horizontal snap
        if abs(pos.x() - screen.left()) < snap_dist:
            new_x = screen.left()
        elif abs(pos.x() + self.width() - screen.right()) < snap_dist:
            new_x = screen.right() - self.width()
            
        # Vertical snap
        if abs(pos.y() - screen.top()) < snap_dist:
            new_y = screen.top()
        elif abs(pos.y() + self.height() - screen.bottom()) < snap_dist:
            new_y = screen.bottom() - self.height()
            
        if new_x != pos.x() or new_y != pos.y():
            self.move(new_x, new_y)

    def position_bottom_right(self):
        """Move window to bottom right of available screen area"""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        margin = 20
        x = screen.right() - self.width() - margin
        y = screen.bottom() - self.height() - margin
        self.move(x, y)
