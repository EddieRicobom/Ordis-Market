"""
Ordis Market - Enhanced UI with Sound Effects & Loading Messages
Version 2.0

Improved interface with:
- 5-second loading message intervals
- Characteristic Ordis sounds on process start/complete/error
- Enhanced visual feedback
- Better loading state indicators
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QProgressBar, QTableWidget)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl, QEventLoop
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtGui import QFont, QColor
import random
from pathlib import Path

from ordis_messages import (
    get_random_loading_message,
    get_random_completion_message,
    get_random_error_message,
    SoundEffects
)


class SoundManager:
    """Manages Ordis sound effects playback."""
    
    def __init__(self):
        """Initialize sound manager."""
        self.sounds = {}
        self.audio_output = QAudioOutput()
        self.current_player = None
        self.sounds_enabled = True
        self.load_sounds()
    
    def load_sounds(self):
        """Load or generate sound effects."""
        sounds_dir = Path("sounds")
        
        # Try to load existing sounds
        sound_files = {
            "activate": sounds_dir / "ordis_activate.wav",
            "complete": sounds_dir / "ordis_complete.wav",
            "error": sounds_dir / "ordis_error.wav",
            "click": sounds_dir / "ordis_click.wav",
            "notification": sounds_dir / "ordis_notification.wav",
        }
        
        for name, path in sound_files.items():
            if path.exists():
                self.sounds[name] = str(path)
        
        # If sounds don't exist, generate them
        if len(self.sounds) < 5:
            try:
                from sound_generator import SoundGenerator
                generator = SoundGenerator()
                self.sounds = generator.generate_all()
            except Exception as e:
                print(f"Warning: Could not generate sounds: {e}")
                self.sounds_enabled = False
    
    def play_sound(self, sound_name: str):
        """
        Play a sound effect.
        
        Args:
            sound_name: Name of sound to play (activate, complete, error, click, notification)
        """
        if not self.sounds_enabled or sound_name not in self.sounds:
            return
        
        try:
            sound_path = self.sounds[sound_name]
            player = QMediaPlayer()
            player.setAudioOutput(self.audio_output)
            player.setSource(QUrl.fromLocalFile(sound_path))
            player.play()
            
            # Keep reference to prevent garbage collection
            self.current_player = player
        except Exception as e:
            print(f"Warning: Could not play sound {sound_name}: {e}")
    
    def play_start(self):
        """Play process start sound."""
        self.play_sound("activate")
    
    def play_complete(self):
        """Play process complete sound."""
        self.play_sound("complete")
    
    def play_error(self):
        """Play error sound."""
        self.play_sound("error")
    
    def play_click(self):
        """Play button click sound."""
        self.play_sound("click")


class LoadingDialog(QDialog):
    """Enhanced loading dialog with animated messages and sounds."""
    
    task_complete = Signal()
    
    def __init__(self, parent=None, title: str = "Processing"):
        """
        Initialize loading dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.message_index = 0
        self.sound_manager = SoundManager()
        
        self.init_ui()
        self.start_message_rotation()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Processing Market Data")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Loading message (changes every 5 seconds)
        self.message_label = QLabel(get_random_loading_message())
        self.message_label.setStyleSheet("""
            QLabel {
                color: #b89968;
                font-size: 11px;
                padding: 15px;
                border: 1px solid #333333;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
        """)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 4px;
                background-color: #1a1a1a;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #b89968;
            }
        """)
        self.progress.setMaximum(0)  # Indeterminate progress
        layout.addWidget(self.progress)
        
        # Status info
        self.status_label = QLabel("Starting analysis...")
        self.status_label.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #b89968;
                border: 1px solid #b89968;
                border-radius: 4px;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)
    
    def start_message_rotation(self):
        """Start rotating loading messages every 5 seconds."""
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.rotate_message)
        self.message_timer.start(5000)  # 5 seconds
        
        # Play startup sound
        self.sound_manager.play_start()
    
    def rotate_message(self):
        """Change to next loading message."""
        self.message_label.setText(get_random_loading_message())
    
    def set_status(self, status: str):
        """Update status message."""
        self.status_label.setText(status)
    
    def finish_with_success(self):
        """Complete loading with success."""
        self.message_timer.stop()
        self.message_label.setText(get_random_completion_message())
        self.progress.setMaximum(100)
        self.progress.setValue(100)
        
        # Play completion sound
        self.sound_manager.play_complete()
        
        # Close after sound plays
        QTimer.singleShot(1000, self.accept)
    
    def finish_with_error(self, error_msg: str = ""):
        """
        Complete loading with error.
        
        Args:
            error_msg: Error message to display
        """
        self.message_timer.stop()
        self.message_label.setText(get_random_error_message())
        self.message_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 11px;
                padding: 15px;
                border: 1px solid #ff6b6b;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
        """)
        
        if error_msg:
            self.status_label.setText(f"Error: {error_msg}")
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 10px;")
        
        # Play error sound
        self.sound_manager.play_error()


class EnhancedTableWidget(QTableWidget):
    """Enhanced table with visual improvements and sound feedback."""
    
    def __init__(self, *args, **kwargs):
        """Initialize enhanced table widget."""
        super().__init__(*args, **kwargs)
        self.sound_manager = SoundManager()
        self.setup_styling()
    
    def setup_styling(self):
        """Apply enhanced styling."""
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                alternate-background-color: #252525;
                gridline-color: #333333;
            }
            QTableWidget::item {
                padding: 4px;
                border-right: 1px solid #333333;
                border-bottom: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #b89968;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #b89968;
                padding: 4px;
                border-right: 1px solid #333333;
                border-bottom: 1px solid #333333;
            }
        """)
        
        self.alternatingRowColors()
    
    def mouseDoubleClickEvent(self, event):
        """Play sound on interaction."""
        self.sound_manager.play_click()
        super().mouseDoubleClickEvent(event)


class LoadingMessageRotator:
    """Utility for managing loading message rotation."""
    
    def __init__(self, label_widget, interval_ms: int = 5000):
        """
        Initialize rotator.
        
        Args:
            label_widget: QLabel to update
            interval_ms: Message rotation interval in milliseconds
        """
        self.label = label_widget
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_message)
        self.interval = interval_ms
    
    def start(self):
        """Start message rotation."""
        self.timer.start(self.interval)
    
    def stop(self):
        """Stop message rotation."""
        self.timer.stop()
    
    def next_message(self):
        """Show next loading message."""
        self.label.setText(get_random_loading_message())


if __name__ == "__main__":
    # Test UI components
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Test loading dialog
    dialog = LoadingDialog(title="Ordis Market Analysis")
    dialog.set_status("Fetching market prices...")
    
    # Simulate completion after 10 seconds
    QTimer.singleShot(10000, dialog.finish_with_success)
    
    dialog.exec()
