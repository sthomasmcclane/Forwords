import sys
import os
import random
import subprocess
import json
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTextEdit, QFrame, QComboBox, QSpinBox, QFileDialog,
                            QMessageBox, QMenu, QAction, QInputDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor, QKeyEvent, QPainter, QTextOption

# Import shared configuration
sys.path.append(str(Path(__file__).parent / 'config'))
from shared import get_banner_colors, get_theme_colors, generate_style_prompt

# Constants
DEFAULT_FORWORDS_DIR = Path.home() / 'Forwords'
DEFAULT_MANUSCRIPTS_DIR = DEFAULT_FORWORDS_DIR / 'Manuscripts'
DEFAULT_RESOURCES_DIR = DEFAULT_FORWORDS_DIR / 'Resources'
FORWORDSRC = DEFAULT_FORWORDS_DIR / '.forwords.config'
RESOURCE_DIR = Path(__file__).parent / 'resources'

# Load shared configurations
BANNER_COLORS = get_banner_colors()
THEMES = get_theme_colors()

def load_forwordsrc():
    """Load configuration from .forwordsrc file."""
    settings = {}
    
    if FORWORDSRC.exists():
        try:
            with open(FORWORDSRC, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ':' in line:
                        key, value = line.split(':', 1)
                        settings[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error reading .forwordsrc: {e}")
    
    return settings

def save_forwordsrc(settings):
    """Save configuration to .forwordsrc file, preserving comments and formatting."""
    # Read existing file to preserve comments and formatting
    existing_lines = []
    if FORWORDSRC.exists():
        try:
            with open(FORWORDSRC, 'r') as f:
                existing_lines = f.readlines()
        except Exception as e:
            print(f"Error reading existing .forwordsrc: {e}")
    
    # Create new content with updated settings
    new_lines = []
    updated_keys = set()
    
    # Process existing lines, updating settings as we go
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and ':' in stripped:
            key, value = stripped.split(':', 1)
            key = key.strip()
            if key in settings:
                new_lines.append(f"{key}: {settings[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Add any new settings that weren't in the existing file
    for key, value in settings.items():
        if key not in updated_keys:
            new_lines.append(f"{key}: {value}\n")
    
    # Write the updated file
    try:
        with open(FORWORDSRC, 'w') as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Error writing .forwordsrc: {e}")

def check_and_install_dependencies():
    """Check for required packages and install if missing."""
    required_packages = {
        'PyQt5': 'PyQt5',
        'PyQt5.QtWidgets': 'PyQt5',
        'PyQt5.QtCore': 'PyQt5',
        'PyQt5.QtGui': 'PyQt5'
    }
    
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("Installing required packages...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user"] + missing_packages)
            print("Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print("\nError: Failed to install required packages.")
            print("Please try running these commands manually:")
            print(f"pip install --user {' '.join(missing_packages)}")
            sys.exit(1)

def initialize_resources():
    """Initialize resource files if they don't exist."""
    # Create default Forwords directory structure
    DEFAULT_FORWORDS_DIR.mkdir(exist_ok=True)
    DEFAULT_MANUSCRIPTS_DIR.mkdir(exist_ok=True)
    DEFAULT_RESOURCES_DIR.mkdir(exist_ok=True)
    
    # Note: quotes.txt is not initialized here - it should be a curated resource file
    # If quotes.txt is missing, users should create it manually with their preferred quotes
    
    # Initialize style.txt if it doesn't exist (will be overwritten each time prompt is generated)
    style_file = DEFAULT_RESOURCES_DIR / "style.txt"
    if not style_file.exists():
        with open(style_file, 'w', encoding='utf-8') as f:
            f.write("Create a light-hearted, steadily-paced story with a conversational voice in present-tense from a first-person point of view.")

check_and_install_dependencies()
initialize_resources()

class CenteredPlaceholderTextEdit(QTextEdit):
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self.placeholder_text = placeholder_text
        self.setPlaceholderText("")

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.toPlainText() == "" and not self.hasFocus():
            painter = QPainter(self.viewport())
            painter.setPen(QColor("#808080"))  # Gray color for placeholder
            option = QTextOption()
            option.setAlignment(Qt.AlignCenter)
            rect = self.viewport().rect()
            painter.drawText(rect, Qt.AlignCenter, self.placeholder_text)

class BashOutWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load configuration
        self.forwordsrc_settings = load_forwordsrc()
        
        # Set up theme and styling
        self.current_theme = self.forwordsrc_settings.get('GUI_THEME', 'light').lower()
        self.font_size_default = int(self.forwordsrc_settings.get('GUI_FONT_SIZE', 12))
        self.banner_color = self.forwordsrc_settings.get('BANNER_COLOR', 'BLUE').upper()
        
        # Set up save directory - handle both relative and absolute paths
        save_path = self.forwordsrc_settings.get('SAVE_FILE', 'manuscript.txt')
        self.save_dir, self.current_manuscript = self.parse_save_path(save_path)
        
        self.session_words = 0  # Track only new words in this session
        self.load_config()
        self.init_ui()
        self.load_initial_state()
        self.apply_theme()

    def parse_save_path(self, save_path):
        """Parse SAVE_FILE setting to determine save directory and manuscript name.
        
        Handles two scenarios:
        - Relative path (e.g., 'manuscript.txt') -> saves to ~/Forwords/manuscripts/
        - Absolute path (e.g., '/home/user/Writing/manuscript.txt') -> saves to specified location
        """
        save_path = Path(save_path).expanduser()
        
        if save_path.is_absolute():
            # Absolute path - use as specified
            save_dir = save_path.parent
            manuscript_name = save_path.stem
        else:
            # Relative path - use default Forwords structure
            save_dir = DEFAULT_MANUSCRIPTS_DIR
            manuscript_name = save_path.stem
        
        # Ensure the save directory exists
        save_dir.mkdir(parents=True, exist_ok=True)
        
        return save_dir, manuscript_name

    def load_config(self):
        """Load configuration from .forwordsrc file."""
        # Check if .forwordsrc exists - if not, prompt user for essential settings
        if not FORWORDSRC.exists():
            self.show_first_run_dialog()
            return

    def show_first_run_dialog(self):
        """Show first-run setup dialog."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Welcome to Forwords!")
        msg.setInformativeText("Forwords will create a dedicated directory at ~/Forwords/ for your writing.\n\nYou can customize the save location later by editing ~/.forwordsrc")
        msg.setWindowTitle("First Run Setup")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        # Create a basic .forwordsrc file with current settings
        self.create_default_forwordsrc()

    def create_default_forwordsrc(self):
        """Create a default .forwords.config file by copying the example."""
        example_file = Path(__file__).parent / 'docs' / 'forwords.config.example'
        if example_file.exists():
            try:
                # Copy the example file to the user's Forwords directory
                import shutil
                shutil.copy2(example_file, FORWORDSRC)
                print(f"Created default config file: {FORWORDSRC}")
            except Exception as e:
                print(f"Error copying example config: {e}")
                # Fallback to creating a basic config
                self.create_basic_config()
        else:
            # Fallback if example file doesn't exist
            self.create_basic_config()

    def create_basic_config(self):
        """Create a basic config file as fallback."""
        default_settings = {
            'SAVE_FILE': 'manuscript.txt',
            'BANNER_COLOR': 'blue',
            'DEFAULT_BANNER': 'Quote',
            'GUI_THEME': 'light',
            'GUI_FONT_SIZE': '12'
        }
        save_forwordsrc(default_settings)

    def choose_save_location(self):
        """Let user choose where to save manuscripts."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Choose Save Location",
            str(self.save_dir),
            QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.save_dir = Path(dir_path)
            self.save_dir.mkdir(parents=True, exist_ok=True)
            # Update both config files
            self.save_config()

    def save_config(self):
        """Save current configuration to .forwordsrc file."""
        # Determine the SAVE_FILE value based on current setup
        if self.save_dir == DEFAULT_MANUSCRIPTS_DIR:
            # Using default Forwords structure - save as relative path
            save_file = f"{self.current_manuscript}.txt"
        else:
            # Using custom location - save as absolute path
            save_file = str(self.save_dir / f"{self.current_manuscript}.txt")
        
        # Save user-controlled settings to .forwordsrc
        settings = {
            'SAVE_FILE': save_file,
            'BANNER_COLOR': self.banner_color,
            'GUI_THEME': self.current_theme,
            'GUI_FONT_SIZE': str(self.font_size_default)
        }
        save_forwordsrc(settings)

    def save_text(self, text):
        """Save text to the current manuscript."""
        if not self.current_manuscript:
            return
        save_file = self.save_dir / f"{self.current_manuscript}.txt"
        with open(save_file, 'a', encoding='utf-8') as f:
            f.write(text + '\n')
        
        # Increment session word count by the number of words in the saved text
        if hasattr(self, 'session_words'):
            self.session_words += self.count_words_in_text(text)
        
        # Update last sentence display
        if hasattr(self, 'last_sentence_label'):
            self.last_sentence_label.setText(f'Last sentence: {text}')
        self.update_word_count()

    def add_sentence(self):
        """Add the current text as a sentence."""
        if hasattr(self, 'input_field'):
            new_sentence = self.input_field.toPlainText().strip()
            if new_sentence:
                self.save_text(new_sentence)
                self.input_field.clear()

    def init_ui(self):
        # Set window title to show manuscript title
        self.update_window_title()
        self.setMinimumSize(600, 400)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Top bar with controls
        top_bar = QHBoxLayout()
        layout.addLayout(top_bar)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark'])
        self.theme_combo.setCurrentText(self.current_theme.capitalize())
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        top_bar.addWidget(self.theme_combo)

        # Font size controls
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel('Font Size:'))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.font_size_default)
        self.font_size_spin.valueChanged.connect(self.update_input_font)
        font_size_layout.addWidget(self.font_size_spin)
        top_bar.addLayout(font_size_layout)

        # Word count display
        self.word_count_label = QLabel('Session: 0 | Total: 0')
        top_bar.addWidget(self.word_count_label)

        # Banner display (uses DEFAULT_BANNER from .forwordsrc)
        self.banner_label = QLabel()
        self.banner_label.setAlignment(Qt.AlignCenter)
        self.banner_label.setWordWrap(True)
        self.banner_label.setMinimumHeight(40)
        self.banner_label.setMaximumHeight(80)
        layout.addWidget(self.banner_label)

        # Last sentence display
        self.last_sentence_label = QLabel('Last sentence: ')
        self.last_sentence_label.setAlignment(Qt.AlignCenter)
        self.last_sentence_label.setWordWrap(True)
        self.last_sentence_label.setMinimumHeight(30)
        layout.addWidget(self.last_sentence_label)

        # Input field
        self.input_field = CenteredPlaceholderTextEdit("Type your next sentence here...")
        self.input_field.setFont(QFont('Helvetica', self.font_size_default))
        self.input_field.textChanged.connect(self.on_text_changed)
        self.input_field.installEventFilter(self)
        layout.addWidget(self.input_field)

        # Set initial banner content based on .forwordsrc DEFAULT_BANNER setting
        self.update_banner_content()

    def update_window_title(self):
        """Update the window title to show the manuscript title."""
        title = self.current_manuscript if self.current_manuscript else 'Forwords'
        self.setWindowTitle(f'Forwords - {title}')

    def switch_manuscript(self, title):
        """Switch to a different manuscript."""
        if not title or title == self.current_manuscript:
            return
        self.save_current_state()
        self.current_manuscript = title
        self.update_window_title()
        self.load_manuscript(title)
        self.update_word_count()

    def load_manuscript(self, title):
        """Load a manuscript from file."""
        if not title:
            return
        
        file_path = self.save_dir / f"{title}.txt"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Count words in the file for total word count
                    self.total_words = self.count_words_in_text(content)
                    # Reset session word count when loading a new manuscript
                    self.session_words = 0
                self.update_word_count()
            except Exception as e:
                print(f"Error loading manuscript: {e}")
        else:
            # Create empty file if it doesn't exist
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    pass
                self.total_words = 0
                self.session_words = 0
                self.update_word_count()
            except Exception as e:
                print(f"Error creating manuscript file: {e}")

    def count_words_in_file(self, file_path):
        """Count words in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return self.count_words_in_text(content)
        except Exception as e:
            print(f"Error counting words in file: {e}")
            return 0

    def count_words_in_text(self, text):
        """Count words in text."""
        return len(text.split())

    def update_word_count(self):
        """Update the word count display."""
        if hasattr(self, 'word_count_label'):
            # Get total words from the current manuscript file
            if self.current_manuscript:
                file_path = self.save_dir / f"{self.current_manuscript}.txt"
                saved_words = self.count_words_in_file(file_path)
            
            if hasattr(self, 'word_count_label'):
                self.word_count_label.setText(f'Session: {self.session_words} | Total: {saved_words}')

    def apply_theme(self):
        if not hasattr(self, 'current_theme'):
            return
            
        theme = THEMES.get(self.current_theme, THEMES['light'])
        
        # Set window background and dialog styles
        self.setStyleSheet(f"""
            QMainWindow, QDialog {{
                background-color: {theme['window']};
                color: {theme['text']};
            }}
            QLabel {{
                color: {theme['text']};
            }}
            QTextEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_text']};
                border: 1px solid {theme['text']};
            }}
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['text']};
                padding: 5px 10px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {theme['text']};
                color: {theme['window']};
            }}
            QComboBox {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['text']};
                padding: 2px 5px;
                border-radius: 3px;
            }}
            QComboBox:hover {{
                border: 1px solid {theme['text']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                selection-background-color: {theme['text']};
                selection-color: {theme['window']};
                border: 1px solid {theme['text']};
            }}
            QSpinBox {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['text']};
                padding: 2px 5px;
                border-radius: 3px;
            }}
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_text']};
                border: 1px solid {theme['text']};
                padding: 2px 5px;
                border-radius: 3px;
            }}
            QMessageBox {{
                background-color: {theme['window']};
                color: {theme['text']};
            }}
            QMessageBox QLabel {{
                color: {theme['text']};
            }}
            QInputDialog {{
                background-color: {theme['window']};
                color: {theme['text']};
            }}
            QInputDialog QLabel {{
                color: {theme['text']};
            }}
            QInputDialog QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_text']};
                border: 1px solid {theme['text']};
                padding: 2px 5px;
                border-radius: 3px;
            }}
            QMenu {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['text']};
            }}
            QMenu::item {{
                padding: 5px 20px;
            }}
            QMenu::item:selected {{
                background-color: {theme['text']};
                color: {theme['window']};
            }}
        """)
        
        # Set banner color based on .forwordsrc setting
        if hasattr(self, 'banner_color'):
            banner_color = BANNER_COLORS.get(self.banner_color.upper(), BANNER_COLORS['BLUE'])
            if hasattr(self, 'banner_label'):
                self.banner_label.setStyleSheet(f"color: {banner_color};")
            if hasattr(self, 'last_sentence_label'):
                self.last_sentence_label.setStyleSheet(f"color: {theme['text']};")

    def change_theme(self, theme):
        """Change the application theme."""
        if hasattr(self, 'current_theme'):
            self.current_theme = theme.lower()
            self.apply_theme()
            # Always save theme changes to config
            self.save_config()

    def eventFilter(self, obj, event):
        if obj == self.input_field and event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers():
                if hasattr(self, 'add_sentence'):
                    self.add_sentence()
                return True
        return super().eventFilter(obj, event)

    def on_text_changed(self):
        """Handle text changes in the input field."""
        # Optional: Add any text change handling here
        pass

    def load_initial_state(self):
        """Load the initial state of the application."""
        # Check if we need to show first run dialog
        if not FORWORDSRC.exists():
            self.show_first_run_dialog()
        elif hasattr(self, 'current_manuscript') and self.current_manuscript:
            self.load_manuscript(self.current_manuscript)
        else:
            # Load manuscript from SAVE_FILE in .forwordsrc
            save_file = self.forwordsrc_settings.get('SAVE_FILE', str(self.save_dir / 'manuscript.txt'))
            save_path = Path(save_file).expanduser()
            self.current_manuscript = save_path.stem
            self.load_manuscript(self.current_manuscript)
        
        # Set initial banner content only if UI is ready
        if hasattr(self, 'banner_label'):
            self.update_banner_content()

    def update_banner_content(self):
        """Update the banner content based on DEFAULT_BANNER setting from .forwordsrc."""
        if hasattr(self, 'banner_label'):
            default_banner = self.forwordsrc_settings.get('DEFAULT_BANNER', 'Quote')
            if default_banner.lower() == 'quote':
                self.banner_label.setText(self.get_random_quote())
            elif default_banner.lower() == 'note':
                self.banner_label.setText(self.get_note())
            elif default_banner.lower() == 'prompt':
                self.banner_label.setText(self.get_style_prompt())

    def get_random_quote(self):
        """Get a random quote from quotes.txt. Returns helpful message if file doesn't exist."""
        # Check both default Forwords resources and app resources
        quotes_file = DEFAULT_RESOURCES_DIR / "quotes.txt"
        if not quotes_file.exists():
            quotes_file = RESOURCE_DIR / "quotes.txt"
        
        if quotes_file.exists():
            try:
                with open(quotes_file, 'r', encoding='utf-8') as f:
                    quotes = [q.strip() for q in f if q.strip()]
                    if quotes:
                        return random.choice(quotes)
                    else:
                        return "Quotes file is empty. Add some writing quotes to ~/Forwords/Resources/quotes.txt"
            except Exception as e:
                return f"Error reading quotes file: {e}"
        return "No quotes file found. Create ~/Forwords/Resources/quotes.txt with your favorite writing quotes (one per line)."

    def get_note(self):
        """Get the note from note.txt file. Prompts user to create it if missing."""
        # Check both default Forwords resources and app resources
        note_file = DEFAULT_RESOURCES_DIR / "note.txt"
        if not note_file.exists():
            note_file = RESOURCE_DIR / "note.txt"
        
        if note_file.exists():
            try:
                with open(note_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    return content if content else self.prompt_for_note()
            except Exception as e:
                print(f"Error reading note.txt: {e}")
                return self.prompt_for_note()
        else:
            return self.prompt_for_note()

    def prompt_for_note(self):
        """Prompt user to create a note when note.txt doesn't exist."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Note Banner Selected")
        msg.setInformativeText("You've selected 'Note' as your banner style, but no note.txt file exists.\n\nWould you like to create one now?\n\n(You can edit this file later at ~/Forwords/Resources/note.txt)")
        msg.setWindowTitle("Create Note")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if msg.exec_() == QMessageBox.Yes:
            note_text, ok = QInputDialog.getText(
                self, 
                'Create Note', 
                'Enter your note message:',
                QLineEdit.Normal,
                "Write something amazing today!"
            )
            if ok and note_text:
                try:
                    note_file = DEFAULT_RESOURCES_DIR / "note.txt"
                    with open(note_file, 'w', encoding='utf-8') as f:
                        f.write(note_text)
                    return note_text
                except Exception as e:
                    print(f"Error creating note.txt: {e}")
                    return "Error creating note file"
        
        return "No note set. Edit ~/Forwords/Resources/note.txt to add your message."

    def get_style_prompt(self):
        """Generate a new random writing prompt using shared components."""
        # Use the shared prompt generation
        style = generate_style_prompt()
        
        # Save to style.txt in default Forwords resources (overwrites each time for fresh prompts)
        style_file = DEFAULT_RESOURCES_DIR / "style.txt"
        try:
            with open(style_file, 'w', encoding='utf-8') as f:
                f.write(style)
        except Exception as e:
            print(f"Error writing style.txt: {e}")
        
        return style

    def update_input_font(self, size):
        """Update the font size of the input field."""
        if hasattr(self, 'input_field'):
            self.input_field.setFont(QFont('Helvetica', size))
        self.font_size_default = size
        # Always save font size changes to config
        self.save_config()

    def save_current_state(self):
        """Save the current state of the application."""
        if hasattr(self, 'current_manuscript') and self.current_manuscript:
            self.save_config()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        
        # Set application style
        app.setStyle('Fusion')
        
        # Create and show the main window
        window = BashOutWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        print("\nError: An unexpected error occurred.")
        print("Please make sure you have Python 3.6 or later installed.")
        print(f"Error details: {str(e)}")
        sys.exit(1) 