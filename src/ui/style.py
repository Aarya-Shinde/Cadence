# src/ui/style.py - Enhanced Dark Theme with Pastel Purple & Midnight Black

"""
Modern Music Player UI with:
- Midnight black backgrounds (#0A0E27, #0F1328)
- Pastel purple accents (#B19CD9, #9A7BB8)
- Smooth transitions and animations
- Professional typography
- Modern icon support
"""

from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt

# ============================================================================
# COLOR PALETTES - Midnight Black + Pastel Purple
# ============================================================================

class Colors:
    """Modern color palette - Midnight Black + Pastel Purple"""
    
    # BACKGROUNDS
    BACKGROUND_PRIMARY = "#0A0E27"      # Deepest midnight black
    BACKGROUND_SECONDARY = "#0F1328"    # Dark midnight
    BACKGROUND_TERTIARY = "#16192C"     # Medium midnight (hover)
    BACKGROUND_ACCENT = "#1C1F3A"       # Accent background
    
    # ACCENTS - Pastel Purple
    ACCENT_PRIMARY = "#B19CD9"          # Main pastel purple
    ACCENT_HOVER = "#C9AFF0"            # Lighter pastel (hover)
    ACCENT_ACTIVE = "#9A7BB8"           # Darker pastel (active/pressed)
    ACCENT_SUBTLE = "#7D5FA8"           # Deep purple (subtle accents)
    
    # TEXT
    TEXT_PRIMARY = "#F5F5F7"            # Near white
    TEXT_SECONDARY = "#A8A8AF"          # Light gray
    TEXT_TERTIARY = "#7A7A85"           # Medium gray
    TEXT_MUTED = "#565660"              # Dark gray
    
    # BORDERS & DIVIDERS
    BORDER_COLOR = "#1C1F3A"            # Main border
    BORDER_LIGHT = "#2A2E45"            # Light border
    BORDER_ACCENT = "#B19CD9"           # Purple border
    
    # SEMANTIC COLORS
    SUCCESS = "#6BCB77"                 # Green
    WARNING = "#FFD93D"                 # Yellow
    ERROR = "#FF6B6B"                   # Red
    INFO = "#A8D8FF"                    # Light blue
    
    # TRANSPARENCY
    OVERLAY_DARK = "rgba(10, 14, 39, 0.95)"
    OVERLAY_MEDIUM = "rgba(15, 19, 40, 0.85)"
    OVERLAY_LIGHT = "rgba(177, 156, 217, 0.1)"


class Fonts:
    """Typography system with proper hierarchy"""
    
    @staticmethod
    def get_font(weight="regular", size=11, italic=False) -> QFont:
        """Get system font with specified properties"""
        font = QFont("Segoe UI", size)
        
        # Weight
        if weight == "light":
            font.setWeight(QFont.Weight.Light)
        elif weight == "regular":
            font.setWeight(QFont.Weight.Normal)
        elif weight == "medium":
            font.setWeight(QFont.Weight.Medium)
        elif weight == "semibold":
            font.setWeight(QFont.Weight.DemiBold)
        elif weight == "bold":
            font.setWeight(QFont.Weight.Bold)
        
        # Italic
        if italic:
            font.setItalic(True)
        
        return font
    
    # Typography hierarchy
    DISPLAY = get_font("bold", 28)          # Page titles
    HEADING_LARGE = get_font("bold", 22)    # Section headings
    HEADING_MEDIUM = get_font("semibold", 16)  # Subsections
    HEADING_SMALL = get_font("semibold", 13)   # Card titles
    
    BODY_LARGE = get_font("regular", 12)    # Primary content
    BODY_REGULAR = get_font("regular", 11)  # Default text
    BODY_SMALL = get_font("regular", 10)    # Secondary text
    BODY_TINY = get_font("regular", 9)      # Captions
    
    # Special styles
    MONO = QFont("Consolas", 10)            # Code/monospace
    BUTTON = get_font("medium", 11)         # Button text
    LABEL = get_font("medium", 10)          # Labels


# ============================================================================
# MAIN STYLESHEET - Midnight Black + Pastel Purple
# ============================================================================

STYLESHEET = f"""
/* ========== GLOBAL STYLES ========== */

* {{
    background-color: {Colors.BACKGROUND_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
    border: none;
    margin: 0;
    padding: 0;
}}

QMainWindow {{
    background-color: {Colors.BACKGROUND_PRIMARY};
}}

QWidget {{
    background-color: {Colors.BACKGROUND_PRIMARY};
}}

/* ========== MENU BAR ========== */

QMenuBar {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    color: {Colors.TEXT_PRIMARY};
    padding: 6px 12px;
    border-bottom: 1px solid {Colors.BORDER_LIGHT};
    spacing: 20px;
    font-size: 11pt;
}}

QMenuBar::item {{
    padding: 4px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.ACCENT_PRIMARY};
}}

QMenu {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    border: 1px solid {Colors.BORDER_LIGHT};
    border-radius: 8px;
    padding: 6px 0;
    margin: 4px 0;
}}

QMenu::item {{
    padding: 8px 16px;
    margin: 2px 4px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.ACCENT_PRIMARY};
}}

QMenu::separator {{
    height: 1px;
    background: {Colors.BORDER_COLOR};
    margin: 4px 8px;
}}

/* ========== BUTTONS ========== */

QPushButton {{
    background-color: {Colors.ACCENT_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 11pt;
}}

QPushButton:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

QPushButton:pressed {{
    background-color: {Colors.ACCENT_ACTIVE};
}}

QPushButton:disabled {{
    background-color: {Colors.TEXT_TERTIARY};
    color: {Colors.TEXT_MUTED};
    opacity: 0.5;
}}

/* Secondary Button */
QPushButton#secondaryBtn {{
    background-color: transparent;
    border: 1.5px solid {Colors.ACCENT_PRIMARY};
    color: {Colors.ACCENT_PRIMARY};
    padding: 6px 14px;
}}

QPushButton#secondaryBtn:hover {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    border-color: {Colors.ACCENT_HOVER};
    color: {Colors.ACCENT_HOVER};
}}

/* Icon Button */
QPushButton#iconBtn {{
    background-color: transparent;
    border: none;
    padding: 8px 8px;
    color: {Colors.TEXT_SECONDARY};
    font-size: 16pt;
}}

QPushButton#iconBtn:hover {{
    color: {Colors.ACCENT_PRIMARY};
    background-color: {Colors.BACKGROUND_TERTIARY};
    border-radius: 6px;
}}

QPushButton#iconBtn:pressed {{
    color: {Colors.ACCENT_ACTIVE};
}}

/* Play Button - Larger */
QPushButton#playBtn {{
    background-color: {Colors.ACCENT_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
    border: none;
    border-radius: 50%;
    padding: 12px;
    min-width: 56px;
    min-height: 56px;
    font-size: 20pt;
    font-weight: bold;
}}

QPushButton#playBtn:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

QPushButton#playBtn:pressed {{
    background-color: {Colors.ACCENT_ACTIVE};
}}

/* ========== SLIDERS ========== */

QSlider::groove:horizontal {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    border-radius: 4px;
    height: 6px;
    margin: 6px 0;
    border: 0.5px solid {Colors.BORDER_COLOR};
}}

QSlider::handle:horizontal {{
    background-color: {Colors.ACCENT_PRIMARY};
    border: 2px solid {Colors.TEXT_PRIMARY};
    border-radius: 50%;
    width: 14px;
    height: 14px;
    margin: -4px 0;
}}

QSlider::handle:horizontal:hover {{
    background-color: {Colors.ACCENT_HOVER};
    width: 18px;
    height: 18px;
    margin: -6px 0;
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ACCENT_PRIMARY},
        stop:1 {Colors.ACCENT_HOVER});
    border-radius: 4px;
}}

/* ========== TEXT INPUTS ========== */

QLineEdit {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11pt;
    selection-background-color: {Colors.ACCENT_PRIMARY};
}}

QLineEdit:focus {{
    border: 1.5px solid {Colors.ACCENT_PRIMARY};
    background-color: {Colors.BACKGROUND_SECONDARY};
}}

QLineEdit::placeholder {{
    color: {Colors.TEXT_TERTIARY};
}}

/* ========== TABLES ========== */

QTableWidget {{
    background-color: {Colors.BACKGROUND_PRIMARY};
    alternate-background-color: {Colors.BACKGROUND_SECONDARY};
    gridline-color: {Colors.BORDER_COLOR};
    border: none;
    selection-background-color: {Colors.BACKGROUND_TERTIARY};
}}

QTableWidget::item {{
    padding: 8px 6px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.ACCENT_PRIMARY};
}}

QTableWidget::item:hover {{
    background-color: {Colors.BACKGROUND_ACCENT};
}}

QHeaderView::section {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    color: {Colors.TEXT_SECONDARY};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER_LIGHT};
    font-weight: 500;
    font-size: 10pt;
}}

QHeaderView::section:hover {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.ACCENT_PRIMARY};
}}

/* ========== SCROLLBARS ========== */

QScrollBar:vertical {{
    background-color: {Colors.BACKGROUND_PRIMARY};
    width: 12px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.BORDER_LIGHT};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.ACCENT_PRIMARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {Colors.BACKGROUND_PRIMARY};
    height: 12px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {Colors.BORDER_LIGHT};
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {Colors.ACCENT_PRIMARY};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
}}

/* ========== LABELS ========== */

QLabel {{
    color: {Colors.TEXT_PRIMARY};
    background-color: transparent;
}}

QLabel#heading {{
    font-size: 18pt;
    font-weight: bold;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#subheading {{
    font-size: 12pt;
    font-weight: 600;
    color: {Colors.ACCENT_PRIMARY};
}}

QLabel#muted {{
    color: {Colors.TEXT_TERTIARY};
    font-size: 10pt;
}}

/* ========== SPINBOX ========== */

QSpinBox {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_COLOR};
    border-radius: 4px;
    padding: 4px;
}}

QSpinBox:focus {{
    border: 1px solid {Colors.ACCENT_PRIMARY};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    border: none;
    width: 20px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {Colors.ACCENT_PRIMARY};
}}

/* ========== COMBOBOX ========== */

QComboBox {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_COLOR};
    border-radius: 4px;
    padding: 6px;
}}

QComboBox:focus {{
    border: 1px solid {Colors.ACCENT_PRIMARY};
    background-color: {Colors.BACKGROUND_SECONDARY};
}}

QComboBox::drop-down {{
    border: none;
    background-color: transparent;
}}

QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.ACCENT_PRIMARY};
    border: 1px solid {Colors.BORDER_COLOR};
    border-radius: 4px;
}}

/* ========== CHECKBOXES ========== */

QCheckBox {{
    color: {Colors.TEXT_PRIMARY};
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1.5px solid {Colors.BORDER_LIGHT};
    background-color: transparent;
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT_PRIMARY};
    background-color: {Colors.BACKGROUND_TERTIARY};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT_PRIMARY};
    border-color: {Colors.ACCENT_PRIMARY};
}}

/* ========== DIALOGS ========== */

QDialog {{
    background-color: {Colors.BACKGROUND_SECONDARY};
}}

QFileDialog {{
    background-color: {Colors.BACKGROUND_PRIMARY};
}}

/* ========== MESSAGE BOX ========== */

QMessageBox {{
    background-color: {Colors.BACKGROUND_SECONDARY};
}}

QMessageBox QLabel {{
    color: {Colors.TEXT_PRIMARY};
}}

QMessageBox QPushButton {{
    min-width: 60px;
}}

/* ========== STATUSBAR ========== */

QStatusBar {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    color: {Colors.TEXT_SECONDARY};
    border-top: 1px solid {Colors.BORDER_LIGHT};
    padding: 4px 8px;
}}

QStatusBar::item {{
    border: none;
    padding: 4px 8px;
}}

/* ========== TAB WIDGET ========== */

QTabWidget::pane {{
    border: 1px solid {Colors.BORDER_LIGHT};
    border-radius: 6px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    color: {Colors.TEXT_SECONDARY};
    padding: 8px 16px;
    margin: 4px 2px;
    border-radius: 4px 4px 0 0;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {Colors.ACCENT_PRIMARY};
    color: {Colors.TEXT_PRIMARY};
}}

QTabBar::tab:hover {{
    background-color: {Colors.BACKGROUND_ACCENT};
    color: {Colors.ACCENT_PRIMARY};
}}

/* ========== TOOLTIP ========== */

QToolTip {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_LIGHT};
    border-radius: 4px;
    padding: 6px 8px;
}}

/* ========== PROGRESS BAR ========== */

QProgressBar {{
    background-color: {Colors.BACKGROUND_TERTIARY};
    border: 1px solid {Colors.BORDER_COLOR};
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ACCENT_PRIMARY},
        stop:1 {Colors.ACCENT_HOVER});
    border-radius: 3px;
}}

/* ========== FRAMES & CONTAINERS ========== */

QFrame {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    border: none;
}}

QFrame#card {{
    background-color: {Colors.BACKGROUND_SECONDARY};
    border: 1px solid {Colors.BORDER_LIGHT};
    border-radius: 8px;
    padding: 12px;
}}

QFrame#card:hover {{
    border-color: {Colors.ACCENT_PRIMARY};
}}
"""


# ============================================================================
# WIDGET-SPECIFIC STYLES
# ============================================================================

class WidgetStyles:
    """Custom styles for specific widget combinations"""
    
    @staticmethod
    def now_playing_display() -> str:
        """Style for now playing song display"""
        return f"""
            QLabel {{
                background-color: {Colors.BACKGROUND_ACCENT};
                border: 1px solid {Colors.BORDER_COLOR};
                border-left: 3px solid {Colors.ACCENT_PRIMARY};
                border-radius: 6px;
                padding: 12px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12pt;
                font-weight: 500;
            }}
        """
    
    @staticmethod
    def playlist_header() -> str:
        """Style for playlist header"""
        return f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 13pt;
                font-weight: 600;
                padding: 8px 0;
            }}
        """
    
    @staticmethod
    def song_card() -> str:
        """Style for song card items"""
        return f"""
            QWidget {{
                background-color: {Colors.BACKGROUND_SECONDARY};
                border: 1px solid {Colors.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
            }}
            
            QWidget:hover {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                border-color: {Colors.ACCENT_PRIMARY};
            }}
        """
    
    @staticmethod
    def info_badge() -> str:
        """Style for info badges"""
        return f"""
            QLabel {{
                background-color: {Colors.BACKGROUND_TERTIARY};
                color: {Colors.ACCENT_PRIMARY};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9pt;
                font-weight: 500;
            }}
        """


# ============================================================================
# THEME MANAGER
# ============================================================================

class ThemeManager:
    """Manage and apply themes"""
    
    @staticmethod
    def apply_theme(app):
        """Apply the dark theme with pastel purple accents
        
        Args:
            app: QApplication instance
        """
        app.setStyleSheet(STYLESHEET)
    
    @staticmethod
    def get_color(color_name: str) -> QColor:
        """Get a color by name
        
        Args:
            color_name: Name of color in Colors class
        
        Returns:
            QColor instance
        """
        if hasattr(Colors, color_name):
            return QColor(getattr(Colors, color_name))
        return QColor(Colors.TEXT_PRIMARY)
    
    @staticmethod
    def get_font(font_name: str) -> QFont:
        """Get a font by name
        
        Args:
            font_name: Name of font in Fonts class
        
        Returns:
            QFont instance
        """
        if hasattr(Fonts, font_name):
            return getattr(Fonts, font_name)
        return Fonts.BODY_REGULAR


# ============================================================================
# COLOR & FONT UTILITIES
# ============================================================================

def style_button(button, style_type="primary"):
    """Quickly style a button
    
    Args:
        button: QPushButton instance
        style_type: "primary", "secondary", "icon"
    """
    if style_type == "secondary":
        button.setObjectName("secondaryBtn")
    elif style_type == "icon":
        button.setObjectName("iconBtn")


def style_label(label, label_type="normal"):
    """Quickly style a label
    
    Args:
        label: QLabel instance
        label_type: "heading", "subheading", "muted"
    """
    if label_type == "heading":
        label.setObjectName("heading")
    elif label_type == "subheading":
        label.setObjectName("subheading")
    elif label_type == "muted":
        label.setObjectName("muted")