
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QLineEdit, QLabel, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from ui.icons import get_icon
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class PlaylistWidget(QWidget):
    """Song list display widget"""
    
    # Signals
    song_double_clicked = pyqtSignal(dict)  # Emit song dict
    song_right_clicked = pyqtSignal(dict, object)  # Song dict and mouse position
    song_delete_clicked = pyqtSignal(dict)  # Emitted when delete button clicked
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.songs = []
        self.filtered_songs = []
    
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
        self.table.setColumnWidth(5, 60)   # Actions
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Connect signals
        self.table.itemDoubleClicked.connect(self._on_song_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_right_click)
        
        main_layout.addWidget(self.table)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
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
            
            # Actions (Delete button)
            from PyQt6.QtWidgets import QPushButton
            delete_btn = QPushButton()
            delete_btn.setIcon(get_icon("trash"))
            delete_btn.setToolTip("Delete Song")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 60, 60, 0.2);
                    border-radius: 4px;
                }
            """)
            delete_btn.clicked.connect(lambda checked, s=song: self.song_delete_clicked.emit(s))
            self.table.setCellWidget(row, 5, delete_btn)
            
            # Store song data in row
            for col in range(6):
                item = self.table.item(row, col)
                if item:
                    item.song_data = song
        
        self.status_label.setText(f"Showing {len(self.filtered_songs)} songs")
    
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
        """Highlight a song by ID"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item.song_data['id'] == song_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break