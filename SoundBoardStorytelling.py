import sys
import os
import json
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QLineEdit, QSlider, 
    QMessageBox, QStyle, QInputDialog, QGridLayout, 
    QTextEdit, QSizePolicy, QScrollArea, QMenu, QFrame,
    QGraphicsDropShadowEffect
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl, QSize, QMimeData, QPoint, QBuffer, QPropertyAnimation, QEasingCurve, QTimer, QByteArray
from PySide6.QtGui import QDrag, QAction, QPixmap, QPainter, QImage, QColor, QTextCursor, QFont, QPalette, QBrush, QLinearGradient, QIcon, QRadialGradient

# --- Configuration ---
CONFIG_FILE = "soundboard_config.json"
SOUNDS_DIR = "sounds"
SUPPORTED_FORMATS = ('.mp3', '.wav', '.ogg')
COLUMNS = 4 

# --- Aesthetics & Ultra Luxury Styles ---
# Deep Cosmic Palette
BG_DARK_1 = "#090910"
BG_DARK_2 = "#151525"
ACCENT_CYAN = "#00f2ff"  # Electric Cyan
ACCENT_PINK = "#ff0099"  # Cyber Pink (for stops/alerts)
TEXT_MAIN = "#ffffff"
TEXT_DIM = "rgba(255, 255, 255, 0.6)"

STYLESHEET = f"""
QMainWindow {{
    background-color: {BG_DARK_1};
}}

QLabel {{
    color: {TEXT_MAIN};
    font-family: 'Segoe UI', sans-serif;
}}

/* Header Header */
QPushButton#STOP_BTN {{
    background-color: rgba(255, 0, 80, 0.1);
    color: #ff5577;
    border: 1px solid rgba(255, 0, 80, 0.5);
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}}
QPushButton#STOP_BTN:hover {{
    background-color: rgba(255, 0, 80, 0.3);
    border: 1px solid #ff0055;
    box-shadow: 0 0 15px #ff0055;
}}

QPushButton#SAVE_BTN {{
    background-color: rgba(0, 242, 255, 0.05);
    color: {ACCENT_CYAN};
    border: 1px solid rgba(0, 242, 255, 0.3);
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}}
QPushButton#SAVE_BTN:hover {{
    background-color: rgba(0, 242, 255, 0.15);
    border: 1px solid {ACCENT_CYAN};
    box-shadow: 0 0 15px {ACCENT_CYAN};
}}

/* Sliders - Futuristic Groove */
QSlider::groove:horizontal {{
    border: 1px solid rgba(255,255,255,0.1);
    height: 4px; 
    background: rgba(0, 0, 0, 0.5);
    margin: 2px 0;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_CYAN};
    border: 2px solid {BG_DARK_1};
    width: 16px;
    height: 16px;
    margin: -6px 0; 
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #005c99, stop:1 {ACCENT_CYAN});
    border-radius: 2px;
}}

/* Scroll Area - Invisible */
QScrollArea {{ background: transparent; border: none; }}
/* QWidget#GridContainer handled in class */

/* Text Ambienter - The Parchment of the Future */
QTextEdit {{
    background-color: rgba(20, 20, 35, 0.6);
    color: #eeeeee;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top: 1px solid rgba(0, 242, 255, 0.3); /* Top accent line */
    border-radius: 4px;
    padding: 20px;
    font-family: 'Georgia', serif; 
    font-size: 16px; 
    line-height: 1.8;
    selection-background-color: rgba(0, 242, 255, 0.3);
}}
"""

# --- Icon Generation ---
def get_base64_icon(icon_type="play", color=ACCENT_CYAN):
    """Creates a base64 icon. Types: 'play', 'stop'"""
    # Increased size for better high-DPI visibility
    size = 24 
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    
    center_x = size // 2
    center_y = size // 2

    if icon_type == "play":
        # Triangle
        p1 = QPoint(center_x - 4, center_y - 6)
        p2 = QPoint(center_x - 4, center_y + 6)
        p3 = QPoint(center_x + 6, center_y)
        painter.drawPolygon([p1, p2, p3])
        
    elif icon_type == "stop":
        # Square/Pause bars
        # Let's do a compact stop square for clarity
        rect_size = 10
        painter.drawRoundedRect(center_x - rect_size//2, center_y - rect_size//2, rect_size, rect_size, 2, 2)
        
    painter.end()
    
    buffer = QBuffer()
    buffer.open(QBuffer.WriteOnly)
    pixmap.save(buffer, "PNG")
    return buffer.data().toBase64().data().decode()

# Precompute icons vars (Initialized later)
ICON_PLAY = None
ICON_STOP = None

def init_global_icons():
    """Initialize icons after QApplication is created"""
    global ICON_PLAY, ICON_STOP
    ICON_PLAY = get_base64_icon("play", ACCENT_CYAN)
    ICON_STOP = get_base64_icon("stop", ACCENT_PINK) 

SOUND_CUE_HTML_FORMAT = (
    '<a href="cue:{path}" style="text-decoration: none;">'
    '<img src="data:image/png;base64,{base64_icon}" width="24" height="24" '
    'style="vertical-align: middle; margin: 0 2px;" title="{name}" />'
    '</a>'
)

# --- 1. Custom Sound Button Widget ---

class SoundButtonWidget(QWidget):
    """A luxury button-like widget for the sound grid."""
    
    def __init__(self, full_path, relative_path, display_name, parent=None):
        super().__init__(parent)
        self.full_path = full_path
        self.relative_path = relative_path
        self.display_name = display_name
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(f"Drag to reorder or insert ->\n{os.path.basename(full_path)}")

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(self.full_path))
        self.player.playbackStateChanged.connect(self._on_playback_changed)
        self.player.errorOccurred.connect(self._handle_error)
        
        # --- UI Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # Inner container for Glassmorphism
        self.container = QFrame()
        self.container.setObjectName("InnerContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(15, 12, 15, 12)
        
        self.name_label = QLabel(self.display_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #fff;")
        self.name_label.setWordWrap(True)
        
        # Bottom decorative bar / progress
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(2)
        self.status_bar.setStyleSheet("background-color: rgba(255,255,255,0.1); border-radius: 1px;")
        
        self.container_layout.addWidget(self.name_label)
        self.container_layout.addStretch()
        self.container_layout.addWidget(self.status_bar)

        self.layout.addWidget(self.container)

        self.setMinimumSize(QSize(140, 95))
        self.setMaximumHeight(110)
        
        # --- Shadows & Effects ---
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(self.shadow)
        
        self.update_style(active=False)
        self.volume = 100

    def update_style(self, active=False):
        if active:
            # Active: Glowing Border, Cyan Tint
            border = f"1px solid {ACCENT_CYAN}"
            bg = "rgba(0, 242, 255, 0.1)"
            s_color = QColor(ACCENT_CYAN)
            s_color.setAlpha(100)
            self.shadow.setColor(s_color)
            self.shadow.setBlurRadius(40)
            self.status_bar.setStyleSheet(f"background-color: {ACCENT_CYAN}; box-shadow: 0 0 10px {ACCENT_CYAN};")
        else:
            # Idle: Glassy
            border = "1px solid rgba(255, 255, 255, 0.1)" 
            bg = "rgba(40, 40, 60, 0.4)" 
            self.shadow.setColor(QColor(0, 0, 0, 100))
            self.shadow.setBlurRadius(20)
            self.status_bar.setStyleSheet("background-color: rgba(255,255,255,0.1);")

        self.container.setStyleSheet(f"""
            QFrame#InnerContainer {{
                background-color: {bg};
                border: {border};
                border-radius: 12px;
            }}
            QFrame#InnerContainer:hover {{
                background-color: rgba(60, 60, 80, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        """)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: #1a1a2e; color: white; border: 1px solid #333; }}
            QMenu::item {{ padding: 5px 20px; }}
            QMenu::item:selected {{ background-color: {ACCENT_CYAN}; color: black; }}
        """)
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(self.rename_sound)
        menu.addAction(rename_action)
        menu.exec(self.mapToGlobal(pos))

    def rename_sound(self):
        new_name, ok = QInputDialog.getText(
            self, "Rename Sound", "New Display Name:", QLineEdit.Normal, self.display_name
        )
        if ok and new_name:
            self.display_name = new_name
            self.name_label.setText(new_name)

    def _on_playback_changed(self, state):
        is_playing = (state == QMediaPlayer.PlayingState)
        self.update_style(active=is_playing)
        mw = self.window()
        if isinstance(mw, SoundBoardApp):
             mw.update_text_icon_state(self.relative_path, is_playing)

    def _handle_error(self):
        print(f"Error: {self.player.errorString()}")

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.stop()
        else:
            self.player.play()

    def set_volume(self, volume):
        self.volume = volume
        self.audio_output.setVolume(volume / 100.0)

    def stop(self):
        self.player.stop()

    def get_config_data(self):
        return {"path": self.relative_path, "display_name": self.display_name}
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
             self.toggle_playback()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton): return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance(): return

        drag = QDrag(self)
        mime_data = QMimeData()
        
        icon_b64 = ICON_PLAY
        if not icon_b64:
             icon_b64 = get_base64_icon("play", ACCENT_CYAN)

        # 1. HTML Data for Text Editor
        cue_html = SOUND_CUE_HTML_FORMAT.format(
            base64_icon=icon_b64,
            path=self.relative_path, 
            name=self.display_name
        )
        mime_data.setHtml(cue_html)
        
        # 2. Reorder Data for Grid (Custom Type)
        mime_data.setData("application/x-sound-path", QByteArray(self.relative_path.encode('utf-8')))
        
        drag.setMimeData(mime_data)
        
        pixmap = self.container.grab()
        drag.setPixmap(pixmap.scaled(QSize(100, 60), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(50, 30))
        
        drag.exec(Qt.MoveAction)


# --- 2. Sound Grid Container (Drag Target) ---

class SoundGridContainer(QWidget):
    """Container that accepts drops for reordering."""
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setAcceptDrops(True)
        self.setObjectName("GridContainer")
        # Layout will be assigned externally
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-sound-path"):
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-sound-path"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-sound-path"):
            path_bytes = event.mimeData().data("application/x-sound-path")
            src_path = bytes(path_bytes).decode('utf-8')
            
            target_index = -1
            layout = self.layout()
            if layout:
                pos = event.position().toPoint()
                closest_dist = 999999
                
                # Iterate through widgets to find insertion point
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if widget:
                        geo = widget.geometry()
                        # If inside the widget, take that index
                        if geo.contains(pos):
                            target_index = i
                            break
                        
                        # Else find closest
                        center = geo.center()
                        dist = (pos - center).manhattanLength()
                        if dist < closest_dist:
                            closest_dist = dist
                            target_index = i
            
            if target_index >= 0:
                self.app.reorder_sounds(src_path, target_index)
                event.acceptProposedAction()


# --- 3. The Text Ambienter Widget ---

class TextAmbienterWidget(QTextEdit):
    """Text editor that accepts sound cue drops and handles playback."""
    def __init__(self, soundboard_app, parent=None):
        super().__init__(parent)
        self.soundboard_app = soundboard_app
        self.setAcceptDrops(True)
        self.setPlaceholderText("The universe is silent. Drag sound crystals here to begin your story...")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasHtml() and 'href="cue:' in event.mimeData().html():
             event.acceptProposedAction()
             return
        event.ignore()

    def dropEvent(self, event):
        cursor = self.cursorForPosition(event.position().toPoint())
        cursor.insertText(" ")
        cursor.insertHtml(event.mimeData().html())
        cursor.insertText(" ")
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            anchor_url = self.anchorAt(event.position().toPoint()) 
            if anchor_url and anchor_url.startswith("cue:"):
                rel_path = anchor_url.removeprefix("cue:")
                self.soundboard_app.play_sound(rel_path)
                event.accept()
                return 
        super().mousePressEvent(event)

    def set_icon_state(self, rel_path, is_playing):
        html = self.toHtml()
        search_pattern = re.compile(
            f'(<a href="cue:{re.escape(rel_path)}"[^>]*>.*?<img src="data:image/png;base64,)([^"]*)(".*?</a>)', 
            re.DOTALL
        )
        target_icon = ICON_STOP if is_playing else ICON_PLAY
        if not target_icon: return 
        new_html = search_pattern.sub(f'\\1{target_icon}\\3', html)
        if new_html != html:
            cursor = self.textCursor()
            vscroll = self.verticalScrollBar().value()
            self.setHtml(new_html)
            self.setTextCursor(cursor)
            self.verticalScrollBar().setValue(vscroll)


# --- 4. Main Application ---

class SoundBoardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎧 Universe Storyteller")
        self.resize(1100, 850)
        self.available_widgets = {} 
        self.sound_order = [] # List of relative paths in order
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.setStyleSheet(STYLESHEET)
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        self.main_layout.addWidget(content_widget)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("UNIVERSE STORYTELLER")
        title_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; letter-spacing: 4px; color: {ACCENT_CYAN};")
        subtitle_lbl = QLabel("INTERACTIVE NARRATIVE SYSTEM")
        subtitle_lbl.setStyleSheet("font-size: 10px; letter-spacing: 2px; color: rgba(255,255,255,0.4);")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(150)
        self.volume_slider.valueChanged.connect(self._set_global_volume)
        self.stop_all_btn = QPushButton("STOP ALL")
        self.stop_all_btn.setObjectName("STOP_BTN")
        self.stop_all_btn.setCursor(Qt.PointingHandCursor)
        self.stop_all_btn.clicked.connect(self._stop_all_sounds)
        self.save_btn = QPushButton("SAVE")
        self.save_btn.setObjectName("SAVE_BTN")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_config)

        controls_layout.addWidget(QLabel("MASTER VOL"))
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addWidget(self.stop_all_btn)
        controls_layout.addWidget(self.save_btn)
        header_layout.addLayout(controls_layout)
        content_layout.addLayout(header_layout)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.5 {ACCENT_CYAN}, stop:1 transparent); opacity: 0.5;")
        content_layout.addWidget(divider)

        # 3. Sound Grid Container
        self.grid_container_widget = SoundGridContainer(self) 
        self.sound_grid_layout = QGridLayout(self.grid_container_widget)
        self.sound_grid_layout.setContentsMargins(10, 10, 10, 10)
        self.sound_grid_layout.setSpacing(20)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.grid_container_widget)
        scroll_area.setMaximumHeight(350)
        scroll_area.setMinimumHeight(200)
        content_layout.addWidget(scroll_area)
        
        # 4. Text Area
        self.text_ambienter = TextAmbienterWidget(self)
        content_layout.addWidget(self.text_ambienter)

        # 5. Footer
        self.footer_label = QLabel()
        self.footer_label.setStyleSheet("color: rgba(255,255,255,0.2); font-size: 10px;")
        abs_path = os.path.abspath(SOUNDS_DIR)
        self.footer_label.setText(f"NEXUS CONNECTED: {abs_path}")
        content_layout.addWidget(self.footer_label)

    # --- Core Logic ---

    def _scan_sounds_directory(self):
        sound_files = []
        if not os.path.exists(SOUNDS_DIR):
            try: os.makedirs(SOUNDS_DIR)
            except OSError: pass
            
        for root, _, files in os.walk(SOUNDS_DIR):
            for file in files:
                if file.lower().endswith(SUPPORTED_FORMATS):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, SOUNDS_DIR)
                    sound_files.append((full_path, rel_path))
        return sound_files

    def _load_config(self):
        scanned_sounds = self._scan_sounds_directory()
        scanned_map = {rel: full for full, rel in scanned_sounds}
        self.sound_order = [] 

        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            self.volume_slider.setValue(config.get('volume', 100))
            self.text_ambienter.setHtml(config.get('text_html', ''))
            
            # Load stored order
            for item in config.get('sounds', []):
                rel_path = item['path']
                if rel_path in scanned_map:
                    self.sound_order.append(rel_path)
                    
                    # Create widget if not exists
                    if rel_path not in self.available_widgets:
                        self._create_sound_widget(scanned_map[rel_path], rel_path, item['display_name'])
                    else:
                        # Just update name if needed
                        self.available_widgets[rel_path].display_name = item['display_name']
                        self.available_widgets[rel_path].name_label.setText(item['display_name'])

        except (FileNotFoundError, json.JSONDecodeError):
            pass
            
        # Add new sounds
        for full, rel in scanned_sounds:
            if rel not in self.sound_order:
                self.sound_order.append(rel)
                if rel not in self.available_widgets:
                     # Use filename as default display name
                     display_name = os.path.splitext(os.path.basename(rel))[0]
                     self._create_sound_widget(full, rel, display_name)
        
        self.refresh_grid_layout()

    def _create_sound_widget(self, full_path, rel_path, display_name):
        widget = SoundButtonWidget(full_path, rel_path, display_name)
        widget.set_volume(self.volume_slider.value())
        self.available_widgets[rel_path] = widget

    def refresh_grid_layout(self):
        # Clear layout (remove from layout but don't delete widget)
        for i in reversed(range(self.sound_grid_layout.count())):
            item = self.sound_grid_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None) # Detach from layout
                
        # Re-add in order
        for index, rel_path in enumerate(self.sound_order):
            widget = self.available_widgets.get(rel_path)
            if widget:
                # IMPORTANT: Widget must be reparented to the container
                widget.setParent(self.grid_container_widget)
                widget.show() # Ensure visible
                
                row = index // COLUMNS
                col = index % COLUMNS
                self.sound_grid_layout.addWidget(widget, row, col)

    def reorder_sounds(self, src_path, target_index):
        if src_path not in self.sound_order: return
        
        # Calculate current logical index
        old_index = self.sound_order.index(src_path)
        if old_index == target_index: return
        
        # Move item
        item = self.sound_order.pop(old_index)
        
        # Adjust target index if shifting
        # Note: drop index is spatial, insert index is logical.
        self.sound_order.insert(target_index, item)
        
        self.refresh_grid_layout()

    def _save_config(self):
        data = {
            "volume": self.volume_slider.value(),
            "text_html": self.text_ambienter.toHtml(), 
            "sounds": []
        }
        
        # Save based on ORDER list
        for rel_path in self.sound_order:
            widget = self.available_widgets.get(rel_path)
            if widget:
                data["sounds"].append(widget.get_config_data())
            
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        
        self.statusBar().showMessage("SYSTEM STATE SAVED", 2000)

    def _set_global_volume(self, value):
        for widget in self.available_widgets.values():
            widget.set_volume(value)

    def _stop_all_sounds(self):
        for widget in self.available_widgets.values():
            widget.stop()

    def play_sound(self, rel_path):
        widget = self.available_widgets.get(rel_path)
        if widget:
            widget.toggle_playback()
            
    def update_text_icon_state(self, rel_path, is_playing):
        self.text_ambienter.set_icon_state(rel_path, is_playing)

    def closeEvent(self, event):
        self._stop_all_sounds()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_global_icons() 
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    window = SoundBoardApp()
    window.show()
    sys.exit(app.exec())