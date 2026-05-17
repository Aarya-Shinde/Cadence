# src/ui/settings_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QSpinBox, QComboBox, QCheckBox,
    QTabWidget, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
import logging

from utils.config import get_config

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Settings dialog with tabs"""
    
    # Signal when settings change
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 500, 400)
        self.config = get_config()
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Create settings UI with tabs"""
        main_layout = QVBoxLayout()
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: Library
        library_tab = self._create_library_tab()
        self.tabs.addTab(library_tab, "Library")
        
        # Tab 2: Playback
        playback_tab = self._create_playback_tab()
        self.tabs.addTab(playback_tab, "Playback")
        
        # Tab 3: Updates
        updates_tab = self._create_updates_tab()
        self.tabs.addTab(updates_tab, "Updates")
        
        # Tab 4: UI
        ui_tab = self._create_ui_tab()
        self.tabs.addTab(ui_tab, "UI")
        
        main_layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.on_reset_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.on_save)
        button_layout.addWidget(save_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _create_library_tab(self) -> QWidget:
        """Library settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Music folder selector
        layout.addWidget(QLabel("Music Folder"))
        folder_layout = QHBoxLayout()
        self.music_folder_input = QLineEdit()
        self.music_folder_input.setReadOnly(True)
        folder_layout.addWidget(self.music_folder_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.on_browse_folder)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)
        
        layout.addSpacing(20)
        
        # Auto-scan
        layout.addWidget(QLabel("Auto-Scan Settings"))
        scan_layout = QHBoxLayout()
        scan_layout.addWidget(QLabel("Scan every"))
        
        self.scan_interval = QSpinBox()
        self.scan_interval.setMinimum(1)
        self.scan_interval.setMaximum(60)
        self.scan_interval.setSuffix(" minutes")
        scan_layout.addWidget(self.scan_interval)
        layout.addLayout(scan_layout)
        
        layout.addSpacing(20)
        
        # Sort order
        layout.addWidget(QLabel("Default Sort Order"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Artist", "Date Added", "Title"])
        layout.addWidget(self.sort_combo)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _create_playback_tab(self) -> QWidget:
        """Playback settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Volume memory
        layout.addWidget(QLabel("Volume"))
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Remember volume between sessions"))
        self.remember_volume = QCheckBox()
        self.remember_volume.setChecked(True)
        volume_layout.addWidget(self.remember_volume)
        volume_layout.addStretch()
        layout.addLayout(volume_layout)
        
        layout.addSpacing(20)
        
        # Remember playback position
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Remember song position"))
        self.remember_position = QCheckBox()
        self.remember_position.setChecked(True)
        position_layout.addWidget(self.remember_position)
        position_layout.addStretch()
        layout.addLayout(position_layout)
        
        layout.addSpacing(20)
        
        # Clear cache button
        clear_btn = QPushButton("Clear Playback Cache")
        clear_btn.setToolTip("Clears saved position and last played song")
        clear_btn.clicked.connect(self.on_clear_cache)
        layout.addWidget(clear_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _create_updates_tab(self) -> QWidget:
        """Update checking settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Auto-update check
        auto_update_layout = QHBoxLayout()
        auto_update_layout.addWidget(QLabel("Check for updates automatically"))
        self.auto_update_check = QCheckBox()
        self.auto_update_check.setChecked(True)
        auto_update_layout.addWidget(self.auto_update_check)
        auto_update_layout.addStretch()
        layout.addLayout(auto_update_layout)
        
        layout.addSpacing(20)
        
        # Update check interval
        layout.addWidget(QLabel("Check Frequency"))
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Check every"))
        self.update_interval = QSpinBox()
        self.update_interval.setMinimum(1)
        self.update_interval.setMaximum(30)
        self.update_interval.setSuffix(" days")
        interval_layout.addWidget(self.update_interval)
        interval_layout.addStretch()
        layout.addLayout(interval_layout)
        
        layout.addSpacing(20)
        
        # Manual check button
        self.check_btn = QPushButton("Check for Updates Now")
        self.check_btn.clicked.connect(self.on_check_updates)
        layout.addWidget(self.check_btn)
        
        # Update Status and Progress
        self.update_status_label = QLabel("")
        self.update_status_label.hide()
        layout.addWidget(self.update_status_label)
        
        from PyQt6.QtWidgets import QProgressBar
        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 100)
        self.update_progress.setTextVisible(False)
        self.update_progress.setFixedHeight(6)
        self.update_progress.hide()
        layout.addWidget(self.update_progress)
        
        self.install_btn = QPushButton("Install & Restart")
        self.install_btn.hide()
        self.install_btn.clicked.connect(self.on_install_update)
        layout.addWidget(self.install_btn)
        
        # Current version
        layout.addSpacing(20)
        from utils.updater import Updater
        self._updater = Updater()
        layout.addWidget(QLabel(f"Current Version: {self._updater.current_version}"))
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _create_ui_tab(self) -> QWidget:
        """UI customization tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Theme
        layout.addWidget(QLabel("Appearance"))
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        layout.addSpacing(20)
        
        # Window size
        layout.addWidget(QLabel("Window"))
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Remember window size"))
        self.remember_window_size = QCheckBox()
        self.remember_window_size.setChecked(True)
        size_layout.addWidget(self.remember_window_size)
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        layout.addSpacing(20)
        
        # Font size (future feature)
        # layout.addWidget(QLabel("Font Size"))
        # self.font_size = QSpinBox()
        # layout.addWidget(self.font_size)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def load_settings(self):
        """Load current settings into UI"""
        music_folder = self.config.get('music_folder')
        self.music_folder_input.setText(music_folder)
        
        scan_minutes = self.config.get('auto_scan_minutes')
        self.scan_interval.setValue(scan_minutes)
        
        sort_order = self.config.get('sort_order')
        sort_index = {'artist': 0, 'date_added': 1, 'title': 2}.get(sort_order, 0)
        self.sort_combo.setCurrentIndex(sort_index)
        
        remember_pos = self.config.get('remember_position', True)
        self.remember_position.setChecked(remember_pos)
        
        auto_update = self.config.get('auto_update_check', True)
        self.auto_update_check.setChecked(auto_update)
        
        update_interval = self.config.get('update_check_interval_hours', 24) // 24
        self.update_interval.setValue(update_interval)
        
        theme = self.config.get('theme', 'light')
        theme_index = {'light': 0, 'dark': 1, 'auto': 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(theme_index)
    
    def on_browse_folder(self):
        """Browse for music folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Music Folder",
            self.music_folder_input.text()
        )
        if folder:
            self.music_folder_input.setText(folder)
    
    def on_save(self):
        """Save all settings"""
        # Save settings
        self.config.set('music_folder', self.music_folder_input.text())
        self.config.set('auto_scan_minutes', self.scan_interval.value())
        self.config.set('remember_position', self.remember_position.isChecked())
        self.config.set('auto_update_check', self.auto_update_check.isChecked())
        self.config.set('update_check_interval_hours', self.update_interval.value() * 24)
        
        sort_map = {0: 'artist', 1: 'date_added', 2: 'title'}
        self.config.set('sort_order', sort_map[self.sort_combo.currentIndex()])
        
        theme_map = {0: 'light', 1: 'dark', 2: 'auto'}
        self.config.set('theme', theme_map[self.theme_combo.currentIndex()])
        
        logger.info("Settings saved")
        self.settings_changed.emit()
        self.accept()
    
    def on_reset_defaults(self):
        """Reset to default settings"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(self, "Done", "Settings reset to defaults")
    
    def on_clear_cache(self):
        """Clear playback cache"""
        self.config.set('last_played_song_id', None)
        QMessageBox.information(
            self,
            "Cache Cleared",
            "Playback cache cleared. The app will start from the beginning next time."
        )
    
    def on_check_updates(self):
        """Trigger manual update check"""
        self.check_btn.setEnabled(False)
        self.update_status_label.setText("Checking for updates...")
        self.update_status_label.setStyleSheet("color: palette(text);")
        self.update_status_label.show()
        self.update_progress.hide()
        self.install_btn.hide()
        
        import threading
        def _task():
            try:
                result = self._updater.check_for_updates()
                # Need to use signals to update UI from thread, but we can use QTimer singleShot
                from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
                QMetaObject.invokeMethod(self, "_on_check_done", Qt.ConnectionType.QueuedConnection, Q_ARG(object, result))
            except Exception as e:
                logger.error(f"Update check failed: {e}")
                QMetaObject.invokeMethod(self, "_on_check_done", Qt.ConnectionType.QueuedConnection, Q_ARG(object, None))
                
        threading.Thread(target=_task, daemon=True).start()

    from PyQt6.QtCore import pyqtSlot
    @pyqtSlot(object)
    def _on_check_done(self, result):
        if result:
            version, url = result
            self.update_status_label.setText(f"Update Available: v{version}. Downloading...")
            self.update_progress.setValue(0)
            self.update_progress.show()
            
            import threading
            def _download_task():
                def progress(downloaded, total):
                    if total > 0:
                        from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
                        QMetaObject.invokeMethod(self, "_on_download_progress", Qt.ConnectionType.QueuedConnection, Q_ARG(int, downloaded), Q_ARG(int, total))
                
                success = self._updater.download_update(url, save_path="update.zip", progress_callback=progress)
                from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
                QMetaObject.invokeMethod(self, "_on_download_done", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, success))
                
            threading.Thread(target=_download_task, daemon=True).start()
        else:
            self.update_status_label.setText("You are up to date.")
            self.check_btn.setEnabled(True)

    @pyqtSlot(int, int)
    def _on_download_progress(self, downloaded, total):
        pct = int(downloaded / total * 100)
        self.update_progress.setValue(pct)
        mb_down = downloaded / (1024*1024)
        mb_tot = total / (1024*1024)
        self.update_status_label.setText(f"Downloading: {mb_down:.1f} / {mb_tot:.1f} MB")

    @pyqtSlot(bool)
    def _on_download_done(self, success):
        self.check_btn.setEnabled(True)
        if success:
            from ui.style import Colors
            self.update_status_label.setText("Update ready to install.")
            self.update_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.update_progress.setValue(100)
            self.install_btn.show()
        else:
            from ui.style import Colors
            self.update_status_label.setText("Failed to download update.")
            self.update_status_label.setStyleSheet(f"color: {Colors.ERROR};")
            self.update_progress.hide()

    def on_install_update(self):
        """Install the downloaded update"""
        self.install_btn.setEnabled(False)
        self.update_status_label.setText("Installing... App will restart.")
        started = self._updater.install_update("update.zip")
        if started is False:
            self.update_status_label.setText("Cannot auto-update when running from source.")
            from ui.style import Colors
            self.update_status_label.setStyleSheet(f"color: {Colors.ERROR};")