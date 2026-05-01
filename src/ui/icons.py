from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtSvg import QSvgRenderer
from pathlib import Path

# Path to the icons directory relative to this file (src/ui/icons.py)
ICON_PATH = Path(__file__).parent.parent / "assets" / "icons"

def get_icon(name: str, color: str = None) -> QIcon:
    """Load an SVG icon from the assets folder and optionally colorize it"""
    icon_file = ICON_PATH / f"{name}.svg"
    if not icon_file.exists():
        return QIcon()
    
    if not color:
        return QIcon(str(icon_file))
    
    # Create a pixmap and render the SVG into it
    renderer = QSvgRenderer(str(icon_file))
    pixmap = QPixmap(128, 128) # Higher res for better quality
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    
    # Use composition to apply color
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    
    return QIcon(pixmap)
