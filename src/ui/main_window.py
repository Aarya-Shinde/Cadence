from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QMenu, QMessageBox, QFileDialog, QFrame,
    QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QSize, QVariantAnimation
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QKeySequence, QShortcut
import logging
import threading
from pathlib import Path
 
from core.database import MusicDatabase
from core.music_scanner import MusicScanner
from core.file_watcher import MusicFileWatcher
from core.audio_player import AudioPlayer
from ui.playlist_widget import PlaylistWidget
from ui.player_widget import EnhancedPlayerWidget
from ui.style import Colors, Fonts, ThemeManager, style_button
from ui.icons import get_icon
from ui.settings_dialog import SettingsDialog
from ui.lyrics_display_widget import SongDetailsPanel
from ui.download_dialog import DownloadDialog
from utils.config import get_config
from utils.updater import UpdateChecker
from utils.metadata_reader import MetadataReader
from utils.album_art import AlbumArtManager
from utils.lyrics_fetcher import LyricsManager
from utils.media_keys import MediaKeyInterceptor


logger = logging.getLogger(__name__)


class _Bridge(QObject):
    """Thread-safe signal bridge.

    Background threads cannot safely call QTimer.singleShot() in Qt 6 —
    it triggers 'QObject::setParent: Cannot set parent, new parent is in
    a different thread'.  Instead, background threads call
    bridge.invoke(callable), which emits a proper queued signal that Qt
    delivers on the main thread.
    """
    _invoke = pyqtSignal(object)   # payload = a zero-argument callable

    def __init__(self, parent=None):
        super().__init__(parent)
        self._invoke.connect(self._run, Qt.ConnectionType.QueuedConnection)

    def invoke(self, fn):
        """Call *fn* on the main GUI thread.  Safe to call from any thread."""
        self._invoke.emit(fn)

    def _run(self, fn):
        fn()

 
 
# ============================================================================
# ICONS - Unicode Music Icons
# ============================================================================
 
class Icons:
    """SVG Icon aliases"""
    
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    PREVIOUS = "previous"
    NEXT = "next"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"
    
    VOLUME = "volume"
    VOLUME_MUTE = "volume-mute"
    
    MUSIC = "music"
    FOLDER = "folder"
    SEARCH = "search"
    SETTINGS = "settings"
    INFO = "info"
    STAR = "star"
    HEART = "heart"
    TRASH = "trash"
    PLUS = "plus"
    MINUS = "minus"
    CHECK = "check"
    CLOCK = "clock"
    DOWNLOAD = "download"
    UPLOAD = "upload"
 
 
# ============================================================================
# ANIMATED HEADER BUTTON
# ============================================================================

class AnimatedHeaderButton(QPushButton):
    """A custom button for the header with smooth scale and background color hover animations."""
    def __init__(self, icon_name: str, tooltip: str = "", is_checkable: bool = False, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.is_checkable = is_checkable
        self.setCheckable(is_checkable)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
            
        self.current_icon_size = 16
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
        if self.icon_name == "heart":
            name = "heart-filled" if self.isChecked() else "heart"
            
        if self.isChecked():
            color = Colors.BACKGROUND_PRIMARY
        else:
            color = Colors.ACCENT_PRIMARY
            
        self.setIcon(get_icon(name, color=color))
        self.setIconSize(QSize(self.current_icon_size, self.current_icon_size))

    def _animate_icon_size(self, value):
        self.current_icon_size = value
        self.setIconSize(QSize(value, value))

    def _animate_bg_color(self, color):
        self.current_bg = color
        self.update_style()

    def update_style(self):
        bg_rgba = f"rgba({self.current_bg.red()}, {self.current_bg.green()}, {self.current_bg.blue()}, {self.current_bg.alphaF()})"
        
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.ACCENT_PRIMARY};
                    border-radius: 6px;
                    border: none;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_rgba};
                    border-radius: 6px;
                    border: 1px solid transparent;
                }}
                QPushButton:hover {{
                    border-color: {Colors.BORDER_LIGHT};
                }}
            """)

    def enterEvent(self, event):
        if not self.isChecked():
            self.icon_anim.stop()
            self.icon_anim.setStartValue(self.current_icon_size)
            self.icon_anim.setEndValue(20)
            self.icon_anim.start()
            
            self.bg_anim.stop()
            self.bg_anim.setStartValue(self.current_bg)
            self.bg_anim.setEndValue(QColor(Colors.BACKGROUND_TERTIARY))
            self.bg_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.isChecked():
            self.icon_anim.stop()
            self.icon_anim.setStartValue(self.current_icon_size)
            self.icon_anim.setEndValue(16)
            self.icon_anim.start()
            
            self.bg_anim.stop()
            self.bg_anim.setStartValue(self.current_bg)
            self.bg_anim.setEndValue(QColor(0, 0, 0, 0))
            self.bg_anim.start()
        super().leaveEvent(event)


# ============================================================================
# MAIN WINDOW
# ============================================================================
 
class MainWindow(QMainWindow):
    """Cadence"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cadence")
        self.setWindowIcon(get_icon(Icons.MUSIC))

        # ── Config ──────────────────────────────────────────────────
        self.config = get_config()

        # Restore saved window size
        w = self.config.get('window_width', 1400)
        h = self.config.get('window_height', 900)
        self.setGeometry(100, 100, w, h)
        
        # Apply theme
        ThemeManager.apply_theme(self)
        
        # Initialize components
        self.db = MusicDatabase()
        self.scanner = MusicScanner(self.db)
        self.watcher = MusicFileWatcher(self.db)
        self.player = AudioPlayer()

        # ── Lyrics & Album Art managers ───────────────────────────────
        self.lyrics_manager = LyricsManager()
        self.album_art_manager = AlbumArtManager()

        # Thread-safe bridge: routes background-thread callbacks → main thread
        self._bridge = _Bridge(self)
        
        # State
        self.current_song = None
        self.current_index = -1
        self.playlist = []
        self.show_only_favorites = False
        self.music_folder = self.config.get('music_folder')
        
        # Setup UI
        self.setup_ui()
        self.setup_menus()
        self.connect_signals()
        
        # Restore saved volume
        saved_volume = self.config.get('volume', 0.8)
        self.player.set_volume(saved_volume)
        self.player_widget.volume_slider.setValue(int(saved_volume * 100))

        # Load data
        self.load_playlist()
        
        # Setup Global Media Keys
        self.media_keys = MediaKeyInterceptor()
        self.media_keys.play_pause_pressed.connect(self._on_play_pause_toggle)
        self.media_keys.next_pressed.connect(self.on_next)
        self.media_keys.prev_pressed.connect(self.on_previous)
        self.media_keys.start()
        
        # Position update timer
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position_display)
        self.position_timer.start(100)

        # Setup Keyboard Shortcuts
        self._setup_local_shortcuts()


        # ── Background update check ──────────────────────────────────
        self._start_update_check()
        
        logger.info("Application started with enhanced UI")
    
    def setup_ui(self):
        """Create main UI with improved layout"""
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== HEADER =====
        self.header = self._create_header()
        main_layout.addWidget(self.header)
        
        # ===== MAIN CONTENT =====
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Song details panel (album art + lyrics)
        self.details_panel = SongDetailsPanel()
        self.details_panel.fetch_lyrics.connect(self.on_fetch_lyrics)
        self.details_panel.retry_lyrics.connect(lambda sid, t, a: self.on_fetch_lyrics(sid, t, a, force=True))
        self.details_panel.retry_art.connect(self.on_retry_art)
        content_layout.addWidget(self.details_panel, 1)
        
        # Playlist
        self.playlist_widget = PlaylistWidget()
        content_layout.addWidget(self.playlist_widget, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # ===== PLAYER =====
        player_section = self._create_player_section()
        main_layout.addWidget(player_section)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def _create_header(self) -> QFrame:
        """Create app header with logo and status"""
        header = QFrame()
        header.setFrameShape(QFrame.Shape.NoFrame)
        header.setObjectName("header")
        header.setStyleSheet(f"""
            QFrame#header {{
                background-color: {Colors.BACKGROUND_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
                padding: 6px 16px;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(12)
        
        # Logo (Text only using custom Musical Tone font)
        logo_label = QLabel("Cadence")
        logo_label.setFont(Fonts.LOGO_FONT)
        logo_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.ACCENT_PRIMARY};
                letter-spacing: 0.5px;
            }}
        """)
        layout.addWidget(logo_label)
        
        # Spacer for more space between logo and menu
        layout.addSpacing(20)
        
        # Unified Menu button next to logo
        self.menu_btn = QPushButton("Menu ▾")
        self.menu_btn.setFont(Fonts.BODY_MEDIUM)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setFixedHeight(30)
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                color: {Colors.TEXT_SECONDARY};
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 500;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background: {Colors.BACKGROUND_TERTIARY};
                border-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.ACCENT_PRIMARY};
            }}
            QPushButton::menu-indicator {{
                image: none;
            }}
        """)
        layout.addWidget(self.menu_btn)
        
        # Spacer
        layout.addSpacing(10)
        
        # Status
        self.status_label = QLabel("Ready to play music")
        self.status_label.setFont(Fonts.BODY_SMALL)
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)

        layout.addStretch()
        
        # Song count
        self.song_count_label = QLabel()
        self.song_count_label.setFont(Fonts.BODY_SMALL)
        self.song_count_label.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        layout.addWidget(self.song_count_label)

        # Download button
        self.header_download_btn = AnimatedHeaderButton("download", tooltip="Download Song")
        self.header_download_btn.clicked.connect(self.on_download_song)
        layout.addWidget(self.header_download_btn)
        
        # View Favorites toggle button
        self.view_favs_btn = AnimatedHeaderButton("heart", tooltip="Show Favorites Only", is_checkable=True)
        self.view_favs_btn.clicked.connect(self.on_toggle_favorites_view)
        layout.addWidget(self.view_favs_btn)
        
        # Toggle playlist button
        self.toggle_playlist_btn = AnimatedHeaderButton("library", tooltip="Toggle Playlist View")
        self.toggle_playlist_btn.clicked.connect(self.on_toggle_playlist)
        layout.addWidget(self.toggle_playlist_btn)
        
        # Compact mode toggle button
        self.mini_mode_btn = AnimatedHeaderButton("arrow-down-left", tooltip="Switch to Compact Mode", is_checkable=True)
        self.mini_mode_btn.clicked.connect(self.on_toggle_mini_mode)
        layout.addWidget(self.mini_mode_btn)
        
        header.setLayout(layout)
        return header
    
    def _create_player_section(self) -> QFrame:
        """Create player controls section"""
        container = QFrame()
        container.setFrameShape(QFrame.Shape.NoFrame)
        container.setObjectName("playerSection")
        container.setStyleSheet(f"""
            QFrame#playerSection {{
                background-color: {Colors.BACKGROUND_SECONDARY};
                border-top: 1px solid {Colors.BORDER_LIGHT};
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(14)
        
        # ===== PLAYER WIDGET =====
        self.player_widget = EnhancedPlayerWidget()
        layout.addWidget(self.player_widget)
        
        container.setLayout(layout)
        return container
    
    def setup_menus(self):
        """Configure the unified dropdown menu in the header"""
        # Hide standard menu bar to save vertical space
        self.menuBar().hide()
        
        # Create the unified menu
        self.main_menu = QMenu(self)
        
        scan_action = self.main_menu.addAction("Scan Music Folder")
        scan_action.triggered.connect(self.on_scan_folder)
        self.addAction(scan_action)  # Add to window so shortcut works
        
        settings_action = self.main_menu.addAction("Settings")
        settings_action.triggered.connect(self.on_open_settings)
        self.addAction(settings_action)
        
        self.main_menu.addSeparator()
        
        about_action = self.main_menu.addAction("About")
        about_action.triggered.connect(self.on_about)
        self.addAction(about_action)

        # Connect button to show the menu
        self.menu_btn.setMenu(self.main_menu)
    
    def connect_signals(self):
        """Connect all signals"""
        # Player signals
        self.player_widget.play_clicked.connect(self.on_play)
        self.player_widget.pause_clicked.connect(self.on_pause)
        self.player_widget.next_clicked.connect(self.on_next)
        self.player_widget.previous_clicked.connect(self.on_previous)
        self.player_widget.volume_changed.connect(self.on_volume_changed)
        self.player_widget.progress_seek.connect(self.on_seek)
        self.player_widget.favorite_toggled.connect(self.on_player_favorite_toggled)
        
        # Playlist signals
        self.playlist_widget.song_double_clicked.connect(self.on_song_selected)
        self.playlist_widget.song_delete_clicked.connect(self.on_delete_song)
        self.playlist_widget.song_favorite_toggled.connect(self.on_favorite_toggled)
        
        # Audio player signals
        self.player.on_track_ended = self.on_track_ended
        self.player.on_position_changed = self._update_position_callback
    
    def load_playlist(self):
        """Load songs from database"""
        all_songs = self.db.get_all_songs()
        
        if self.show_only_favorites:
            self.playlist = [s for s in all_songs if s.get('favorite')]
            self.status_label.setText(f"Viewing Favorites ({len(self.playlist)})")
        else:
            self.playlist = all_songs
            self.status_label.setText("Library")
            
        self.playlist_widget.load_songs(self.playlist)
        
        count = len(self.playlist)
        self.song_count_label.setText(f"{count} songs")
        
        logger.info(f"Loaded {count} songs")
    
    def on_song_selected(self, song: dict):
        """Play selected song and load album art / lyrics"""
        self.current_song = song
        self.current_index = next(
            (i for i, s in enumerate(self.playlist) if s['id'] == song['id']),
            -1
        )
        
        success = self.player.load(song['path'])
        if success:
            self.on_play()
            is_fav = bool(song.get('favorite', 0))
            self.player_widget.set_now_playing(song['title'], song['artist'], is_fav)
            
            # Sync with MiniPlayer
            if hasattr(self, 'mini_player'):
                self.mini_player.set_song(song['title'], song['artist'], is_fav)
                
            self.player_widget.set_total_duration(song['duration'])
            self.playlist_widget.highlight_song(song['id'])
            
            # Update status
            self.status_label.setText(f"Now playing: {song['title']}")

            # ── Album art (async, non-blocking) ──────────────────────
            def _load_art():
                art_path = self.album_art_manager.get_art(
                    song['id'],
                    song.get('file_path', ''),
                    song.get('title', 'Unknown'),
                    song.get('album', 'Unknown'),
                    song.get('artist', 'Unknown'),
                    auto_extract=True
                )
                # Marshal to GUI thread via proper queued signal
                self._bridge.invoke(lambda p=art_path: self.details_panel.set_song(song, p))

            threading.Thread(target=_load_art, daemon=True).start()

            logger.info(f"Playing: {song['title']}")
        else:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not play: {song['title']}\n\nThe file may have been moved or deleted."
            )

    def on_fetch_lyrics(self, song_id: int, title: str, artist: str, force: bool = False):
        """Fetch lyrics asynchronously (called by SongDetailsPanel signal)"""
        if force:
            self.status_label.setText(f"Refreshing lyrics for {title}...")
            
        def _on_result(lyrics_data):
            # Always run UI updates on the main thread
            if lyrics_data and lyrics_data.get('lyrics'):
                lyr = lyrics_data['lyrics']
                self._bridge.invoke(lambda t=lyr: self.details_panel.set_lyrics(t))
                if force:
                    self._bridge.invoke(lambda: self.status_label.setText(f"Lyrics updated for {title}"))
            else:
                self._bridge.invoke(lambda t=title: self.details_panel.lyrics_display.set_not_found(t))
                if force:
                    self._bridge.invoke(lambda: self.status_label.setText(f"No new lyrics found for {title}"))

        self.lyrics_manager.fetch_async(song_id, title, artist, _on_result, force=force)

    def on_retry_art(self, song_id: int, title: str, artist: str, file_path: str):
        """Fetch album art from online forcefully"""
        self.status_label.setText(f"Refreshing album art for {title}...")
        
        song = self.current_song
        if not song or song.get('id') != song_id:
            return
            
        def _load_art():
            art_path = self.album_art_manager.get_art(
                song['id'],
                song.get('file_path', ''),
                song.get('title', 'Unknown'),
                song.get('album', 'Unknown'),
                song.get('artist', 'Unknown'),
                auto_extract=True,
                force_online=True
            )
            
            def _update_ui(p):
                if p:
                    self.details_panel.set_song(song, p)
                    self.status_label.setText(f"Album art updated for {title}")
                else:
                    self.status_label.setText(f"No new album art found for {title}")
                    
            self._bridge.invoke(lambda p=art_path: _update_ui(p))

        threading.Thread(target=_load_art, daemon=True).start()
    
    def on_play(self):
        """Resume playback"""
        if not self.current_song and self.playlist:
            # Play first song if none selected
            self.current_index = 0
            self.on_song_selected(self.playlist[0])
            return

        if self.player.play():
            self.player_widget.set_playing_state(True)
            self.details_panel.visualizer.set_playing(True)
            if hasattr(self, 'mini_player'):
                self.mini_player.set_playing_state(True)
            if hasattr(self, 'tray_play_action'):
                self.tray_play_action.setText("Pause")
    
    def on_pause(self):
        """Pause playback"""
        self.player.pause()
        self.player_widget.set_playing_state(False)
        self.details_panel.visualizer.set_playing(False)
        if hasattr(self, 'mini_player'):
            self.mini_player.set_playing_state(False)
        if hasattr(self, 'tray_play_action'):
            self.tray_play_action.setText("Play")
        self.status_label.setText(" Paused")
        
    def _on_play_pause_toggle(self):
        """Toggle play/pause from global media keys"""
        if self.player.is_playing:
            self.on_pause()
        else:
            self.on_play()
    
    def on_next(self, auto_next: bool = False):
        """Next button clicked or track automatically ended"""
        if not self.playlist:
            return
            
        # If it ended naturally and repeat is on, play it again
        if auto_next and getattr(self.player_widget, 'is_repeat', False):
            if self.current_song:
                self.player.seek(0)
                self.on_play()
            return
            
        import random
        if getattr(self.player_widget, 'is_shuffle', False):
            if len(self.playlist) > 1:
                next_index = self.current_index
                while next_index == self.current_index:
                    next_index = random.randint(0, len(self.playlist) - 1)
                self.current_index = next_index
            self.on_song_selected(self.playlist[self.current_index])
        else:
            if self.current_index < len(self.playlist) - 1:
                self.current_index += 1
                self.on_song_selected(self.playlist[self.current_index])
            else:
                self.player.stop()
                self.player_widget.set_playing_state(False)
                self.status_label.setText("End of playlist")
    
    def on_previous(self):
        """Previous button clicked"""
        if not self.playlist:
            return
            
        import random
        if getattr(self.player_widget, 'is_shuffle', False):
            if len(self.playlist) > 1:
                next_index = self.current_index
                while next_index == self.current_index:
                    next_index = random.randint(0, len(self.playlist) - 1)
                self.current_index = next_index
            self.on_song_selected(self.playlist[self.current_index])
        else:
            if self.current_index > 0:
                self.current_index -= 1
                self.on_song_selected(self.playlist[self.current_index])
    
    def on_volume_changed(self, volume: float):
        """Volume changed (absolute)"""
        self.player.set_volume(volume)
        self.config.set('volume', volume)
        
    def on_mini_volume_changed(self, delta: float):
        """Handle relative volume change from MiniPlayer scroll"""
        current = self.config.get('volume', 0.8)
        new_vol = max(0.0, min(1.0, current + delta))
        self.on_volume_changed(new_vol)
        # Update main slider too
        self.player_widget.volume_slider.setValue(int(new_vol * 100))
    
    def on_seek(self, seconds: float):
        """Progress seek"""
        self.player.seek(seconds)
    
    def on_track_ended(self):
        """Track ended naturally"""
        self._bridge.invoke(lambda: self.on_next(auto_next=True))
    
    def _update_position_callback(self, position: float):
        """Position update callback"""
        pass
    
    def _update_position_display(self):
        """Update position and lyrics sync"""
        if self.player.is_playing:
            position = self.player.get_current_position()
            duration = self.player.get_duration()
            
            self.player_widget.update_progress(position)
            
            # Sync with MiniPlayer
            if hasattr(self, 'mini_player') and self.mini_player.isVisible():
                self.mini_player.update_progress(position, duration)
                
            # SYNC LYRICS: Update lyrics highlighter
            self.details_panel.update_time(position)
    
    def on_open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def on_download_song(self):
        """Open the download dialog"""
        folder = self.music_folder or self.config.get('music_folder') or "downloads"
        dialog = DownloadDialog(self, default_folder=folder)
        dialog.download_finished.connect(self._on_download_finished)
        dialog.exec()

    def _on_download_finished(self, folder: str):
        """Rescan after a successful download and reload playlist"""
        self.status_label.setText("Adding downloaded song to library…")
        self.scanner.scan_folder_async(
            folder,
            completion_callback=lambda r: self._bridge.invoke(lambda res=r: self._after_download_scan(res))
        )

    def _after_download_scan(self, results: dict):
        self.load_playlist()
        added = results.get('added', 0)
        self.status_label.setText(
            f"Added {added} new song{'s' if added != 1 else ''} from download"
            if added else "Library up to date"
        )

    def _on_settings_changed(self):
        """React to settings being saved"""
        # Re-apply volume from config
        new_volume = self.config.get('volume', 0.8)
        self.player.set_volume(new_volume)
        self.player_widget.volume_slider.setValue(int(new_volume * 100))
        logger.info("Settings applied")

    def _setup_local_shortcuts(self):
        """Define local application shortcuts"""
        # Play/Pause (Space)
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self._on_local_play_pause)

        # Seek Backward (Left Arrow)
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.left_shortcut.activated.connect(lambda: self.on_seek(max(0, self.player.get_current_position() - 10)))

        # Seek Forward (Right Arrow)
        self.right_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.right_shortcut.activated.connect(lambda: self.on_seek(self.player.get_current_position() + 10))

        # Previous Track (Shift+P or Media Prev)
        self.prev_shortcut = QShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_P), self)
        self.prev_shortcut.activated.connect(self.on_previous)

        # Next Track (Shift+N or Media Next)
        self.next_shortcut = QShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_N), self)
        self.next_shortcut.activated.connect(self.on_next)

        # Navigation (Up/Down) - Handled by table if focused, but added globally for convenience
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.up_shortcut.activated.connect(self._on_local_up)

        self.down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.down_shortcut.activated.connect(self._on_local_down)

        # Enter to Play Selected
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.enter_shortcut.activated.connect(self._on_local_enter)
        
        self.enter_shortcut_2 = QShortcut(QKeySequence(Qt.Key.Key_Enter), self)
        self.enter_shortcut_2.activated.connect(self._on_local_enter)

    def _on_local_play_pause(self):
        # Ignore if typing in search bar
        if not isinstance(self.focusWidget(), QLineEdit):
            self._on_play_pause_toggle()

    def _on_local_up(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            row = self.playlist_widget.table.currentRow()
            if row > 0:
                self.playlist_widget.table.selectRow(row - 1)
                self.playlist_widget.table.setCurrentCell(row - 1, 0)

    def _on_local_down(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            row = self.playlist_widget.table.currentRow()
            if row < self.playlist_widget.table.rowCount() - 1:
                self.playlist_widget.table.selectRow(row + 1)
                self.playlist_widget.table.setCurrentCell(row + 1, 0)

    def _on_local_enter(self):
        if not isinstance(self.focusWidget(), QLineEdit):
            song = self.playlist_widget.get_selected_song()
            if song:
                self.on_song_selected(song)


    def on_scan_folder(self):
        """Scan music folder"""
        default_dir = self.config.get('music_folder') or str(Path.home() / "Music")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Music Folder",
            default_dir
        )
        
        if not folder:
            return
        
        self.music_folder = folder
        self.config.set('music_folder', folder)   # persist choice
        self.status_label.setText(f"Scanning {Path(folder).name}...")
        
        def on_complete(results):
            # Called from scanner background thread — marshal everything to main thread
            def _show_result():
                msg = (f"Folder Scan Complete\n\n"
                      f"✓ Songs Added: {results['added']}\n"
                      f"◯ Duplicates Found: {results['duplicates']}\n"
                      f"🗑 Songs Removed: {results.get('removed', 0)}\n"
                      f"✗ Errors: {results['errors']}")
                QMessageBox.information(self, "Scan Complete", msg)
                self.load_playlist()
                self.status_label.setText("Ready to play music")
            self._bridge.invoke(_show_result)
        
        self.scanner.scan_folder_async(
            folder,
            completion_callback=on_complete
        )
        
        if not self.watcher.is_watching():
            self.watcher.start_watching(
                folder,
                rescan_callback=lambda r: self._bridge.invoke(self.load_playlist)
            )

    
    def on_clear_library(self):
        """Clear all songs"""
        reply = QMessageBox.question(
            self,
            "Clear Library",
            "Are you sure? This will remove all songs from the library.\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_all_songs()
            self.load_playlist()
            self.player.stop()
            self.current_song = None
            self.status_label.setText("Library cleared")

    def on_delete_song(self, song: dict):
        """Handle deleting a single song from the playlist"""
        reply = QMessageBox.question(
            self,
            "Delete Song",
            f"Are you sure you want to delete '{song['title']}'?\nThis will remove it from the library.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # First, completely stop playback and clear UI if this song is currently playing
            # This is critical to release the file handle lock!
            if self.current_song and self.current_song.get('id') == song['id']:
                self.player.stop()
                self.details_panel.clear_song()
                self.current_song = None
                
            # Delete file
            reply2 = QMessageBox.question(
                self,
                "Delete File",
                "Do you also want to permanently delete the actual audio file from your hard drive?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply2 == QMessageBox.StandardButton.Yes:
                try:
                    import os
                    if song.get('path'):
                        os.remove(song.get('path'))
                except Exception as e:
                    logger.error(f"Failed to delete file {song.get('path')}: {e}")
            
            # Remove from DB
            self.db.remove_song_by_id(song['id'])
            self.load_playlist()
            self.status_label.setText(f"Deleted '{song['title']}'")

    def on_favorite_toggled(self, song: dict):
        """Handle favorite toggle from playlist or mini player"""
        new_val = self.db.toggle_favorite(song['id'])
        song['favorite'] = new_val
        
        # If this is the currently playing song, update the player bar too
        if self.current_song and self.current_song['id'] == song['id']:
            self.current_song['favorite'] = new_val
            self.player_widget.update_favorite_state(new_val)
            if hasattr(self, 'mini_player'):
                self.mini_player.set_favorite(new_val)
            
        self.load_playlist() # Refresh list to respect filters

    def on_player_favorite_toggled(self):
        """Handle favorite toggle from player bar"""
        if self.current_song:
            new_val = self.db.toggle_favorite(self.current_song['id'])
            self.current_song['favorite'] = new_val
            self.player_widget.update_favorite_state(new_val)
            if hasattr(self, 'mini_player'):
                self.mini_player.set_favorite(new_val)
            
            self.load_playlist() # Refresh list to respect filters

    def on_toggle_favorites_view(self, checked: bool):
        """Toggle between all songs and favorites only"""
        self.show_only_favorites = checked
        self.load_playlist()
        
        if checked:
            self.status_label.setText("Showing only favorite songs")
        else:
            self.status_label.setText("Showing all songs")

    def on_toggle_mini_mode(self, checked: bool):
        """Switch to standalone MiniPlayer window"""
        if checked:
            if not hasattr(self, 'mini_player'):
                from ui.mini_player import MiniPlayer
                self.mini_player = MiniPlayer()
                self.mini_player.restore_requested.connect(self._restore_from_mini)
                self.mini_player.play_clicked.connect(self.on_play)
                self.mini_player.pause_clicked.connect(self.on_pause)
                self.mini_player.next_clicked.connect(self.on_next)
                self.mini_player.prev_clicked.connect(self.on_previous)
                self.mini_player.favorite_toggled.connect(lambda: self.on_favorite_toggled(self.current_song) if self.current_song else None)
                self.mini_player.volume_changed.connect(self.on_mini_volume_changed)
            
            # Sync current song/state
            if self.current_song:
                self.mini_player.set_song(
                    self.current_song['title'], 
                    self.current_song['artist'],
                    bool(self.current_song.get('favorite', 0))
                )
            self.mini_player.set_playing_state(self.player.is_playing)
            
            # Show mini, hide main
            self.hide()
            self.mini_player.show()
            self.mini_player.position_bottom_right()
        else:
            if hasattr(self, 'mini_player'):
                self.mini_player.hide()
            self.show()

    def _restore_from_mini(self):
        """Callback to return from mini mode to full UI"""
        self.mini_mode_btn.setChecked(False)
        self.on_toggle_mini_mode(False)
        self.activateWindow()

    def on_toggle_playlist(self):
        """Toggle visibility of the playlist to expand the album art/lyrics view"""
        is_visible = self.playlist_widget.isVisible()
        self.playlist_widget.setVisible(not is_visible)
        
        # Update button tooltip
        self.toggle_playlist_btn.setToolTip("Show Playlist" if is_visible else "Hide Playlist")
    
    def on_check_updates_manual(self):
        """Manual update check triggered from Help menu"""
        self.status_label.setText("Checking for updates...")
        
        def _check():
            checker = UpdateChecker(self.config)
            checker.updater.check_for_updates()  # run check
            result = checker.updater.check_for_updates()
            self._bridge.invoke(lambda r=result: self._on_update_result(r, manual=True))
        
        threading.Thread(target=_check, daemon=True).start()

    def _start_update_check(self):
        """Run automatic update check in background on startup"""
        def _check():
            checker = UpdateChecker(
                self.config,
                check_interval_hours=self.config.get('update_check_interval_hours', 24)
            )
            checker.check_and_notify(
                callback=lambda ver, url: self._bridge.invoke(
                    lambda v=ver, u=url: self._on_update_result((v, u), manual=False)
                )
            )
        threading.Thread(target=_check, daemon=True).start()

    def _on_update_result(self, result, manual: bool = False):
        """Handle update check result — always called on the GUI thread"""
        if result:
            version, url = result
            reply = QMessageBox.question(
                self,
                "Update Available",
                f"Version {version} is available.\n\nWould you like to visit the download page?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes and url:
                import webbrowser
                webbrowser.open(url)
        elif manual:
            QMessageBox.information(self, "No Updates", "You are already on the latest version.")
        self.status_label.setText("Ready to play music")

    def on_about(self):
        """Show about dialog"""
        about_text = """
Cadence Music Player v1.0

A beautiful, modern music player for your collection.
For personal use only. 
A Gift to every music lover

Built with PyQt6 and pygame-mixer

© 2026 • All Rights Reserved
        """.strip()
        
        QMessageBox.about(self, "About Cadence", about_text)

    def on_download_song(self):
        """Show the search & download dialog"""
        dialog = DownloadDialog(self, default_folder=self.music_folder or "downloads")
        
        # When a download completes, automatically rescan that folder
        def _on_complete(folder):
            self.status_label.setText("Adding new music to library...")
            self.scanner.scan_folder_async(
                folder,
                completion_callback=lambda results: self._bridge.invoke(self.load_playlist)
            )
            
        dialog.download_finished.connect(_on_complete)
        dialog.show()
    
    def closeEvent(self, event):
        """Save state and clean up on close"""
        # Persist window size
        self.config.set('window_width', self.width())
        self.config.set('window_height', self.height())
        # Persist last played song
        if self.current_song:
            self.config.set('last_played_song_id', self.current_song.get('id'))
        self.player.stop()
        self.watcher.stop_watching()
        event.accept()
        logger.info("Application closed")