from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QFontMetrics

class TruncatedLabel(QLabel):
    """A QLabel that truncates text with an ellipsis when it gets too long."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

    def setText(self, text):
        self._text = text
        self.update()

    def text(self):
        return self._text

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._text, Qt.TextElideMode.ElideRight, self.width())
        # Draw the text with current style color
        painter.drawText(self.rect(), self.alignment(), elided)
