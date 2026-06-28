# src/ui/visualizer.py

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QFontMetrics, QPainterPath
import random
import math

from ui.style import Colors

class AudioVisualizer(QWidget):
    """
    A Magical Stardust & Floating Music Note Audio Visualizer.
    - Particles (stardust dots and music notes) rise from the bottom and fall from the top.
    - 8 simulated frequency bands control the speeds, size, and brightness of the particles.
    - Particles are grouped horizontally in columns corresponding to their frequency band.
    - Music notes light up when active and fade out/disappear completely when music stops.
    - Enhanced depth field and sway dynamics give a premium floating stardust feel.
    """
    
    def __init__(self, parent=None, density=120):
        super().__init__(parent)
        self.density = density
        self.is_playing = False
        
        # Enable dynamic vertical scaling to match the lyrics widget height
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        self.song_title = ""
        self.song_artist = ""
        self.bpm_factor = 1.0
        
        self.particles = []
        self.freqs = [0.1] * 8  # 8 simulated frequency bands
        self.counter = 0
        self.notes_fade = 0.0   # Fade factor for notes (0.0 = invisible, 1.0 = fully visible)
        
        self.init_particles()
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(25) # Smooth 40 FPS updates
        
    def set_song_info(self, title: str, artist: str):
        """Update the overlay song title and artist name"""
        self.song_title = title if title else "Unknown"
        self.song_artist = artist if artist else ""
        
        # Determine pseudo-BPM from title/artist to get a stable, unique tempo for each song
        combined = f"{self.song_title}-{self.song_artist}"
        h_val = abs(hash(combined))
        bpm = 75 + (h_val % 75)  # Range: 75 to 150 BPM
        self.bpm_factor = bpm / 100.0  # 0.75 to 1.5 multiplier
        
        self.update()
        
    def init_particles(self):
        """Generate the initial set of stardust particles"""
        self.particles = []
        for _ in range(self.density):
            self.particles.append(self.create_particle(random_y=True))
            
    def create_particle(self, random_y=False):
        """Create a single particle associated with a frequency band and direction"""
        band = random.randint(0, 7)
        direction = random.choice([-1, 1])  # -1: rising, 1: falling
        
        # Horizontal positioning based on frequency band columns
        col_width = 1.0 / 8
        col_x = (band + random.uniform(0.1, 0.9)) * col_width
        
        # Spawn vertical height
        if random_y:
            y = random.uniform(0.0, 1.0)
        else:
            y = 1.0 if direction == -1 else 0.0
            
        # Spawn music notes only for rising particles, using symbols that do not look like 'J'
        is_note = (direction == -1) and (random.random() < 0.12)
        note_char = random.choice(['♫', '♬', '♭', '♮']) if is_note else ''
        
        # Base size and speed offsets to create vertical depth - experimental uniform size
        size_base = random.uniform(1.6, 2.4) if is_note else random.uniform(1.0, 1.5)
        depth_factor = random.uniform(0.85, 1.15)
        
        # 8% chance for a stardust dot to be a supergiant star
        is_supergiant = (not is_note) and (random.random() < 0.08)
        
        return {
            'x_ratio': col_x,         # 0.0 to 1.0
            'y_ratio': y,             # 0.0 to 1.0
            'direction': direction,   # -1: rising, 1: falling
            'band': band,
            'is_note': is_note,
            'is_supergiant': is_supergiant,
            'char': note_char,
            'depth': depth_factor,    # 1.0 = normal, <1.0 = far/slower, >1.0 = close/faster
            'size': size_base * depth_factor,
            'speed': random.uniform(0.005, 0.013) * depth_factor,
            'speed_offset': random.uniform(0.0, 2.0 * math.pi),
            'color': (
                # Bass bands (left): deep purple / violet theme colors
                random.choice([
                    QColor(Colors.ACCENT_PRIMARY),  # Violet
                    QColor(160, 130, 255)           # Deep purple-lavender
                ]) if band < 3 else (
                    # Mid bands (middle): lavender / white / pastel purple
                    random.choice([
                        QColor(215, 200, 255),          # Lavender
                        QColor(Colors.ACCENT_SUBTLE),   # Pastel Purple
                        QColor(255, 255, 255)           # White
                    ]) if band < 6 else
                    # Treble bands (right): bright white and rare gold/cyan sparkles
                    (QColor(255, 223, 128) if random.random() < 0.05 else
                     (QColor(128, 235, 255) if random.random() < 0.08 else
                      QColor(255, 255, 255)))
                )
            ),
            'alpha_mod': random.uniform(0.8, 1.0) if is_note else random.uniform(0.5, 0.9)
        }
        
    def set_playing(self, playing):
        self.is_playing = playing
        
    def update_animation(self):
        if not self.isVisible():
            return
            
        self.counter += 1
        
        # Smoothly transition notes visibility based on play state
        if self.is_playing:
            self.notes_fade = min(1.0, self.notes_fade + 0.04) # Fade in
        else:
            self.notes_fade = max(0.0, self.notes_fade - 0.03) # Fade out
            
        # 1. Update simulated frequency bands
        if self.is_playing:
            for i in range(8):
                if i < 3:  # Bass bands (0, 1, 2)
                    beat = 0.7 * (1.0 if self.counter % 12 < 4 else 0.2)
                    target = 0.2 + beat + random.uniform(0.0, 0.15)
                elif i < 6:  # Mid bands (3, 4, 5)
                    target = 0.15 + 0.5 * math.sin(self.counter * 0.12 + i) + random.uniform(0.0, 0.15)
                else:  # Treble bands (6, 7)
                    target = 0.1 + 0.65 * random.uniform(0.0, 1.0)
                    
                target = max(0.05, min(1.0, target))
                # Smooth frequency values
                self.freqs[i] += (target - self.freqs[i]) * 0.25
        else:
            # Idle decay to quiet breathing wave
            for i in range(8):
                target = 0.03 + 0.02 * math.sin(self.counter * 0.05 + i)
                self.freqs[i] += (target - self.freqs[i]) * 0.1
                
        # 2. Update particles
        bass_energy = (self.freqs[0] + self.freqs[1] + self.freqs[2]) / 3.0
        bpm_mult = self.bpm_factor if hasattr(self, 'bpm_factor') else 1.0
        bass_boost = max(0.0, (bass_energy - 0.4) * 0.8)
        
        for p in self.particles:
            band_val = self.freqs[p['band']]
            
            # Particle speed is driven by the frequency amplitude, depth factor, BPM, and bass boost
            v_speed = p['speed'] * bpm_mult * (0.5 + 2.0 * band_val + bass_boost)
            p['y_ratio'] += p['direction'] * v_speed
            
            # No horizontal sway for a strictly uniform, clean vertical stream
            pass
            
            # Recycle particles that flow off-screen
            if p['direction'] == -1 and p['y_ratio'] <= 0.0:
                p['y_ratio'] = 1.0
                p['x_ratio'] = (p['band'] + random.uniform(0.1, 0.9)) * (1.0 / 8)
            elif p['direction'] == 1 and p['y_ratio'] >= 1.0:
                p['y_ratio'] = 0.0
                p['x_ratio'] = (p['band'] + random.uniform(0.1, 0.9)) * (1.0 / 8)
                
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 1. Clear background to dark primary color
        painter.fillRect(self.rect(), QColor(Colors.BACKGROUND_PRIMARY))
        
        # Calculate bass energy for beat flashes and particle flares
        bass_energy = (self.freqs[0] + self.freqs[1] + self.freqs[2]) / 3.0
        bass_flash = max(0.0, (bass_energy - 0.45) * 110)
        
        # 2. Draw Stardust Particles and Music Notes
        for p in self.particles:
            px = p['x_ratio'] * w
            py = p['y_ratio'] * h
            
            # Map vertical position to frequency value
            band_val = self.freqs[p['band']]
            
            # Check if this particle is a supergiant star
            is_supergiant = p.get('is_supergiant', False)
            
            # Instant size pulsing: stars expand instantly with their column's frequency amplitude
            s = p['size'] * (0.7 + 1.5 * band_val)
            if is_supergiant:
                flare_scale = 1.0 + max(0.0, (bass_energy - 0.3) * 1.6)
                s = s * flare_scale
            s = max(0.5, min(9.0, s))
            
            # Twinkling effect + beat flash brightness boost
            twinkle = 160 + 95 * math.sin(self.counter * 0.18 + p['speed_offset'])
            alpha = int((twinkle + bass_flash) * p['alpha_mod'] * (0.65 + 0.35 * band_val))
            alpha = max(15, min(255, alpha))
            
            color = QColor(p['color'])
            color.setAlpha(alpha)
            
            if p['is_note']:
                # Calculate final alpha for note (with fade-out multiplier)
                note_alpha = int(alpha * self.notes_fade)
                if note_alpha < 10:
                    continue  # Skip drawing if fully faded out
                    
                # If note frequency band is highly active, make it glow brighter and larger
                if band_val > 0.6:
                    draw_color = QColor(255, 255, 255, note_alpha) # Pure glowing white
                    font_size = int(8 + 5 * band_val)
                else:
                    draw_color = QColor(color.red(), color.green(), color.blue(), note_alpha)
                    font_size = int(7 + 4 * band_val)
                
                painter.setPen(draw_color)
                
                font = QFont("Segoe UI", font_size)
                font.setBold(True)
                painter.setFont(font)
                
                # Center text layout
                fm = painter.fontMetrics()
                tx = px - fm.horizontalAdvance(p['char']) / 2
                ty = py + fm.height() / 2 - fm.descent()
                painter.drawText(QPointF(tx, ty), p['char'])
            else:
                # Shape stardust as beautiful 4-point curved sparkles instead of simple round dots
                painter.setPen(Qt.PenStyle.NoPen)
                
                if is_supergiant:
                    # Draw supergiant star: soft larger halo glow path first
                    halo_alpha = int(alpha * 0.45)
                    if halo_alpha > 15:
                        halo_color = QColor(255, 255, 255, halo_alpha)
                        painter.setBrush(QBrush(halo_color))
                        
                        halo_s = s * 2.0
                        halo_path = QPainterPath()
                        halo_path.moveTo(px, py - halo_s)
                        halo_path.quadTo(px, py, px + halo_s, py)
                        halo_path.quadTo(px, py, px, py + halo_s)
                        halo_path.quadTo(px, py, px - halo_s, py)
                        halo_path.quadTo(px, py, px, py - halo_s)
                        painter.drawPath(halo_path)
                    
                    # Draw main bright supergiant core star on top
                    painter.setBrush(QBrush(QColor(255, 255, 255, min(255, int(alpha * 1.25)))))
                    path = QPainterPath()
                    path.moveTo(px, py - s)
                    path.quadTo(px, py, px + s, py)
                    path.quadTo(px, py, px, py + s)
                    path.quadTo(px, py, px - s, py)
                    path.quadTo(px, py, px, py - s)
                    painter.drawPath(path)
                else:
                    # Draw normal stardust particle
                    painter.setBrush(QBrush(color))
                    if s > 1.2:
                        # 4-point curved sparkle shape path
                        path = QPainterPath()
                        path.moveTo(px, py - s)
                        path.quadTo(px, py, px + s, py)
                        path.quadTo(px, py, px, py + s)
                        path.quadTo(px, py, px - s, py)
                        path.quadTo(px, py, px, py - s)
                        painter.drawPath(path)
                    else:
                        # Draw tiny stars as small points
                        painter.drawEllipse(QPointF(px, py), s, s)
                    
                    # Subtle glow aura for larger particles
                    if s > 2.0:
                        halo_color = QColor(color)
                        halo_color.setAlpha(int(alpha * 0.25))
                        painter.setBrush(QBrush(halo_color))
                        painter.drawEllipse(QPointF(px, py), s * 2.2, s * 2.2)
                    
        # 3. Draw Song Details Overlay
        # Centered horizontally, vertically spaced
        cx = w / 2
        cy = h / 2
        
        # Song Title
        title_font = QFont("Segoe UI", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        fm_title = QFontMetrics(title_font)
        
        # Elide long title names
        elided_title = fm_title.elidedText(self.song_title, Qt.TextElideMode.ElideRight, w - 40)
        
        # Title text color (white with slightly muted alpha for non-aggressive visual weight)
        painter.setPen(QColor(255, 255, 255, 220))
        tx = cx - fm_title.horizontalAdvance(elided_title) / 2
        ty = cy - 6
        painter.drawText(QPointF(tx, ty), elided_title)
        
        # Song Artist
        if self.song_artist:
            artist_font = QFont("Segoe UI", 8)
            painter.setFont(artist_font)
            fm_artist = QFontMetrics(artist_font)
            
            elided_artist = fm_artist.elidedText(self.song_artist, Qt.TextElideMode.ElideRight, w - 40)
            
            # Subtle lavender theme accent color
            c_accent = QColor(Colors.ACCENT_SUBTLE)
            painter.setPen(QColor(c_accent.red(), c_accent.green(), c_accent.blue(), 200))
            
            ax = cx - fm_artist.horizontalAdvance(elided_artist) / 2
            ay = cy + 22
            painter.drawText(QPointF(ax, ay), elided_artist)
