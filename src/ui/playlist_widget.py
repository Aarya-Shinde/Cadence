
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QLineEdit, QLabel, QMenu, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QVariantAnimation
from PyQt6.QtGui import QFont, QColor, QIcon
from ui.style import Colors
from ui.icons import get_icon
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PlaylistActionButton(QPushButton):
    """Button in playlist actions with hover scaling and color changes"""
    def __init__(self, icon_name, hover_bg_color, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.hover_bg_color = hover_bg_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(20, 20)
        
        self.icon_size = 12
        self.update_icon()
        
        self.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg_color};
            }}
        """)
        
        # Micro-animation for icon size scaling
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(100)
        self.anim.valueChanged.connect(self._animate_icon)
        
    def update_icon(self):
        self.setIcon(get_icon(self.icon_name))
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        
    def _animate_icon(self, value):
        self.icon_size = value
        self.setIconSize(QSize(value, value))
        
    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.icon_size)
        self.anim.setEndValue(15)  # scale up from 12 to 15
        self.anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.icon_size)
        self.anim.setEndValue(12)  # scale down to 12
        self.anim.start()
        super().leaveEvent(event)


class PlaylistWidget(QWidget):
    """Song list display widget"""
    
    # Signals
    song_double_clicked = pyqtSignal(dict)  # Emit song dict
    song_right_clicked = pyqtSignal(dict, object)  # Song dict and mouse position
    song_delete_clicked = pyqtSignal(dict)  # Emitted when delete button clicked
    song_favorite_toggled = pyqtSignal(dict)  # Emitted when heart clicked
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.songs = []
        self.filtered_songs = []
        self.current_playing_id = -1
    
    def setup_ui(self):
        """Create UI components"""
        main_layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 5, 0, 10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title, artist, or album...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setClearButtonEnabled(True)
        
        # Add search icon to line edit
        search_action = self.search_input.addAction(get_icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        
        # Song table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Title", "Artist", "Album", "Duration", "Date Added", "Actions"
        ])
        
        # Configure table
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 250)  # Title
        self.table.setColumnWidth(1, 150)  # Artist
        self.table.setColumnWidth(2, 150)  # Album
        self.table.setColumnWidth(3, 80)   # Duration
        self.table.setColumnWidth(4, 120)  # Date Added
        self.table.setColumnWidth(5, 85)   # Actions (widened for two buttons)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Connect signals
        self.table.itemDoubleClicked.connect(self._on_song_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_right_click)
        
        main_layout.addWidget(self.table)
        
        # Status bar removed to save space
        
        self.setLayout(main_layout)
    
    def load_songs(self, songs: List[Dict]):
        """Load songs into the table
        
        Args:
            songs: List of song dicts with id, title, artist, album, duration, date_added
        """
        self.songs = songs
        self.filtered_songs = songs
        self._update_table()
    
    def _update_table(self):
        """Refresh table with current songs"""
        self.table.setRowCount(0)
        
        for row, song in enumerate(self.filtered_songs):
            self.table.insertRow(row)
            is_playing = (song['id'] == self.current_playing_id)
            
            # Title
            title_item = QTableWidgetItem(song['title'])
            self.table.setItem(row, 0, title_item)
            
            # Artist
            artist_item = QTableWidgetItem(song['artist'])
            self.table.setItem(row, 1, artist_item)
            
            # Album
            album_item = QTableWidgetItem(song['album'])
            self.table.setItem(row, 2, album_item)
            
            # Duration
            duration = int(song['duration'])
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            duration_item = QTableWidgetItem(duration_str)
            self.table.setItem(row, 3, duration_item)
            
            # Date Added
            date_item = QTableWidgetItem(str(song['date_added']))
            self.table.setItem(row, 4, date_item)
            
            # Actions cell (Fav + Delete)
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Favorite button
            is_fav = bool(song.get('favorite', 0))
            fav_btn = PlaylistActionButton(
                "heart-filled" if is_fav else "heart",
                "rgba(160, 130, 255, 0.2)"
            )
            fav_btn.setToolTip("Mark as Favorite" if not is_fav else "Unfavorite")
            fav_btn.clicked.connect(lambda checked, s=song: self.song_favorite_toggled.emit(s))
            actions_layout.addWidget(fav_btn)
            
            # Delete button
            delete_btn = PlaylistActionButton(
                "trash",
                "rgba(255, 60, 60, 0.2)"
            )
            delete_btn.setToolTip("Delete Song")
            delete_btn.clicked.connect(lambda checked, s=song: self.song_delete_clicked.emit(s))
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 5, actions_widget)
            
            # Store song data in row items for easy access & style text
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.song_data = song
                    if is_playing:
                        item.setForeground(QColor(Colors.ACCENT_PRIMARY))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        item.setForeground(QColor(Colors.TEXT_PRIMARY) if col == 0 else QColor(Colors.TEXT_SECONDARY))
                        font = item.font()
                        font.setBold(False)
                        item.setFont(font)
        
        pass
    
    def _on_song_double_clicked(self, item):
        """Handle double-click on song"""
        song_data = item.song_data
        self.song_double_clicked.emit(song_data)
    
    def _on_right_click(self, position):
        """Handle right-click context menu"""
        item = self.table.itemAt(position)
        if item:
            song_data = item.song_data
            self.song_right_clicked.emit(song_data, position)
    
    def _on_search(self, query: str):
        """Filter songs by search query"""
        query = query.lower()
        
        self.filtered_songs = [
            song for song in self.songs
            if query in song['title'].lower()
            or query in song['artist'].lower()
            or query in song['album'].lower()
        ]
        
        self._update_table()
    
    def get_selected_song(self) -> Dict:
        """Get currently selected song"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            return self.filtered_songs[current_row]
        return None
    
    def highlight_song(self, song_id: int):
        """Highlight a song by ID and style its row text"""
        self.current_playing_id = song_id
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0) # Title column
            if item and hasattr(item, 'song_data'):
                is_playing = (item.song_data['id'] == song_id)
                
                # Highlight in table selection
                if is_playing:
                    self.table.selectRow(row)
                    self.table.scrollToItem(item)
                
                # Apply foreground colors/bold font to indicate playing state
                for col in range(5):
                    col_item = self.table.item(row, col)
                    if col_item:
                        if is_playing:
                            col_item.setForeground(QColor(Colors.ACCENT_PRIMARY))
                            font = col_item.font()
                            font.setBold(True)
                            col_item.setFont(font)
                        else:
                            col_item.setForeground(QColor(Colors.TEXT_PRIMARY) if col == 0 else QColor(Colors.TEXT_SECONDARY))
                            font = col_item.font()
                            font.setBold(False)
                            col_item.setFont(font)