from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from pathlib import Path

# Path to the icons directory relative to this file (src/ui/icons.py)
ICON_PATH = Path(__file__).parent.parent / "assets" / "icons"

def get_icon(name: str) -> QIcon:
    """Load an SVG icon from the assets folder"""
    icon_file = ICON_PATH / f"{name}.svg"
    if not icon_file.exists():
        # Fallback or returning empty icon if not found
        return QIcon()
    return QIcon(str(icon_file))
