from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen
import random
import math

from ui.style import Colors

class AudioVisualizer(QWidget):
    """
    A Dual-Layer Cinematic Waveform Visualizer.
    - Features a foreground 'Beat' wave and a background 'Atmosphere' shadow.
    - Mirrored vertical layout (SoundCloud/Spotify Pro style).
    - Dynamic color shifts with high-density pill bars.
    """
    
    def __init__(self, parent=None, density=140):
        super().__init__(parent)
        self.density = density
        # Two layers of history
        self.foreground = [0.05] * density
        self.background = [0.03] * density
        
        self.is_playing = False
        self.setFixedHeight(80) # Reduced height to prevent window growth
        
        self.color_transition = 0.0
        self.beat_impact = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(25) # Faster for buttery smoothness
        
        self.counter = 0
        
    def set_playing(self, playing):
        self.is_playing = playing
            
    def update_animation(self):
        if not self.isVisible():
            return
            
        self.counter += 1
        
        # Smooth color transition
        target_color = 1.0 if self.is_playing else 0.0
        self.color_transition += (target_color - self.color_transition) * 0.06
        
        if self.is_playing:
            # 1. Beat Detection Simulation
            if self.counter % 8 == 0:
                self.beat_impact = random.uniform(0.5, 0.9)
            else:
                self.beat_impact *= 0.88
                
            # 2. Foreground (Sharp Beat)
            noise = random.uniform(0.0, 0.2)
            wave_f = (math.sin(self.counter * 0.15) + 1) * 0.1
            new_f = max(0.1, wave_f + self.beat_impact + noise)
            
            # 3. Background (Slow Atmosphere)
            wave_b = (math.sin(self.counter * 0.05) + 1) * 0.15
            new_b = max(0.05, wave_b + (self.beat_impact * 0.3))
        else:
            new_f = 0.04 + (math.sin(self.counter * 0.04) + 1) * 0.02
            new_b = 0.02 + (math.sin(self.counter * 0.02) + 1) * 0.01
            
        # Shift histories
        self.foreground.pop(0)
        self.foreground.append(new_f)
        
        self.background.pop(0)
        self.background.append(new_b)
        
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        mid_y = h / 2
        
        bar_gap = 1
        bar_width = (w - (self.density - 1) * bar_gap) / self.density
        
        # Color definitions
        white_bg = QColor(255, 255, 255, 40) # Very faint
        purple_bg = QColor(Colors.ACCENT_PRIMARY)
        purple_bg.setAlpha(60) # Faint purple for background layer
        
        white_fg = QColor(255, 255, 255, 180)
        purple_fg = QColor(Colors.ACCENT_PRIMARY)
        
        def interpolate_color(c1, c2, factor):
            r = int(c1.red() + (c2.red() - c1.red()) * factor)
            g = int(c1.green() + (c2.green() - c1.green()) * factor)
            b = int(c1.blue() + (c2.blue() - c1.blue()) * factor)
            a = int(c1.alpha() + (c2.alpha() - c1.alpha()) * factor)
            return QColor(r, g, b, a)

        color_bg = interpolate_color(white_bg, purple_bg, self.color_transition)
        color_fg = interpolate_color(white_fg, purple_fg, self.color_transition)
        
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 1. DRAW BACKGROUND LAYER (Atmosphere)
        for i in range(self.density):
            val = self.background[i]
            bar_h = val * h * 0.9
            x = i * (bar_width + bar_gap)
            y = mid_y - (bar_h / 2)
            
            painter.setBrush(color_bg)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), bar_width/2, bar_width/2)
            
        # 2. DRAW FOREGROUND LAYER (The Beat)
        for i in range(self.density):
            val = self.foreground[i]
            bar_h = max(3.0, val * h * 0.6)
            x = i * (bar_width + bar_gap)
            y = mid_y - (bar_h / 2)
            
            # Add a vertical gradient to the foreground bars
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0, color_fg.lighter(120))
            grad.setColorAt(1, color_fg.darker(110))
            
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), bar_width/2, bar_width/2)
