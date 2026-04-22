import sys
from PyQt6.QtWidgets import QApplication

# ── Bootstrap logging & config FIRST so all modules inherit them ──
from utils.logger import setup_logging
from utils.config import get_config

setup_logging()
config = get_config()

from ui.style import ThemeManager
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    ThemeManager.apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
