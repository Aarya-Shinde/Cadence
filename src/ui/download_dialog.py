# src/ui/download_dialog.py
"""
Polished download dialog with:
- Search input
- Real-time progress bar + status text
- Cancel / Close control
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import logging

from ui.style import Colors, Fonts

logger = logging.getLogger(__name__)


class DownloadDialog(QDialog):
    """Modal dialog for searching and downloading a song"""

    # Emitted when a download finishes successfully so the main window
    # can rescan/reload.  Payload = folder that was downloaded into.
    download_finished = pyqtSignal(str)
    
    # Internal signals for thread-safe UI updates
    _progress_update = pyqtSignal(object)
    _task_done = pyqtSignal(object, str)

    def __init__(self, parent=None, default_folder: str = "downloads"):
        super().__init__(parent)
        self.default_folder = default_folder
        self._is_downloading = False

        self.setWindowTitle("Download Music")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._setup_ui()
        
        # Connect internal signals
        self._progress_update.connect(self._apply_progress)
        self._task_done.connect(self._on_done)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel("Download Music")
        title.setFont(Fonts.HEADING_SMALL)
        title.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Search YouTube and download as MP3")
        subtitle.setFont(Fonts.BODY_SMALL)
        subtitle.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        layout.addWidget(subtitle)

        # ── Search row ─────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('e.g.  "Shape of You Ed Sheeran"')
        self.search_input.setFont(Fonts.BODY_REGULAR)
        self.search_input.returnPressed.connect(self._on_download)
        search_row.addWidget(self.search_input, 1)

        self.download_btn = QPushButton("Download")
        self.download_btn.setFixedWidth(100)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self._on_download)
        search_row.addWidget(self.download_btn)

        layout.addLayout(search_row)

        # ── Divider ────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {Colors.BORDER_LIGHT};")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # ── Progress area ──────────────────────────────────────────────
        self.status_label = QLabel("Enter a song name and press Download.")
        self.status_label.setFont(Fonts.BODY_SMALL)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {Colors.BACKGROUND_TERTIARY};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ACCENT_SUBTLE},
                    stop:1 {Colors.ACCENT_PRIMARY});
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        self.speed_label = QLabel("")
        self.speed_label.setFont(Fonts.BODY_TINY)
        self.speed_label.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        layout.addWidget(self.speed_label)

        # ── Close button ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setFixedWidth(90)
        self.close_btn.setObjectName("secondaryBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_download(self):
        query = self.search_input.text().strip()
        if not query or self._is_downloading:
            return

        self._is_downloading = True
        self.download_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self._set_status(f'Searching for "{query}"…', Colors.TEXT_SECONDARY)
        self.speed_label.setText("")

        # Import here to avoid circular at module load time
        from core.downloader import MusicDownloader
        import threading

        folder = self.default_folder or "downloads"
        downloader = MusicDownloader(folder)

        def _on_progress(state):
            # Emit signal to main thread
            self._progress_update.emit(state)

        def _task():
            result = downloader.download_song(query, progress_callback=_on_progress)
            self._task_done.emit(result, folder)

        threading.Thread(target=_task, daemon=True).start()

    def _apply_progress(self, state):
        """Update UI from a DownloadProgress snapshot (main thread)."""
        if state.status == "downloading":
            pct = min(int(state.percent), 99)
            self.progress_bar.setValue(pct)
            filename = state.filename or "…"
            self._set_status(f"Downloading:  {filename}", Colors.TEXT_SECONDARY)
            parts = []
            if state.speed:
                parts.append(state.speed)
            if state.eta:
                parts.append(f"ETA {state.eta}")
            self.speed_label.setText("  ·  ".join(parts))

        elif state.status == "processing":
            self.progress_bar.setValue(100)
            self._set_status("Converting to MP3…", Colors.ACCENT_PRIMARY)
            self.speed_label.setText("")

        elif state.status == "error":
            self._set_status(f"Error: {state.error}", Colors.ERROR)
            self.speed_label.setText("")

    def _on_done(self, result_path, folder: str):
        """Called on main thread after download thread completes."""
        self._is_downloading = False
        self.download_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.close_btn.setEnabled(True)

        if result_path:
            self.progress_bar.setValue(100)
            self._set_status("✓ Download complete!", Colors.SUCCESS)
            self.speed_label.setText(str(result_path))
            self.download_finished.emit(str(folder))
            # Reset for another download after a short pause
            QTimer.singleShot(3000, self._reset)
        else:
            self.progress_bar.setValue(0)
            self._set_status(
                "Download failed. Is FFmpeg installed and on PATH?",
                Colors.ERROR
            )

    def _reset(self):
        self.search_input.clear()
        self.progress_bar.setValue(0)
        self._set_status("Enter a song name and press Download.", Colors.TEXT_SECONDARY)
        self.speed_label.setText("")

    def _set_status(self, text: str, color: str):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")
