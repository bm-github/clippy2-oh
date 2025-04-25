import sys
import os
import requests
import dotenv

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                               QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                               QSizePolicy, QTextBrowser, QSystemTrayIcon, QMenu)
# QRegion is no longer needed for the character window mask
from PySide6.QtGui import (QPixmap, QMovie, QColor, QPainter,
                           QTextOption, Qt, QPainterPath, QPolygonF, QPen, QIcon)
from PySide6.QtCore import (Qt, QPoint, QSize, QRectF, QThread, Signal,
                            QTimer, QPointF, QPoint)


# --- Configuration ---
# Load environment variables from .env file (if it exists).
dotenv.load_dotenv()
print("Environment variables potentially loaded from .env")

# Retrieve variables. os.environ.get will check system env first, then those loaded by dotenv.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL")

# Define different images for states
IDLE_CHARACTER_PATH = "character_idle.png" # Or character_idle.gif
BUSY_CHARACTER_PATH = "character_busy.png" # Or character_busy.gif (e.g., thinking animation)
TRAY_ICON_PATH = "tray_icon.png" # 32x32 Path for the system tray icon

# Define target sizes for windows (adjust based on your images/needs)
CHARACTER_WIDTH = 256
CHARACTER_HEIGHT = 256

# Input Box size (accommodates LineEdit and Button)
INPUT_BOX_WIDTH = CHARACTER_WIDTH + 50 # Make input box a bit wider than character
INPUT_BOX_HEIGHT = 50 # Taller to fit button easily

# Speech Bubble size (Determines the canvas size for drawing the bubble)
BUBBLE_WIDTH = 250 # Increased width for more text space
BUBBLE_HEIGHT = 450 # Increased height

# Bubble visual properties for programmatic drawing
BUBBLE_FILL_COLOR = QColor(255, 255, 200, 220) # Light yellow, semi-transparent
BUBBLE_BORDER_COLOR = QColor(100, 100, 50, 220) # Darker yellow/brown border
BUBBLE_BORDER_THICKNESS = 2 # Kept for layout calculation, even if border isn't drawn explicitly
BUBBLE_CORNER_RADIUS = 10
BUBBLE_TAIL_HEIGHT = 40 # Space reserved at bottom for tail

MAX_HISTORY_MESSAGES = 10 # Keep last 10 user/assistant messages

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = "You are 'Clippy 2.Oh'! 📎✨ The classic paperclip assistant, now with extra 'Oh!' – meaning extra helpfulness and enthusiasm! You're known for being super cheerful and eager to help (sometimes *very* eager!). **Your special skill is noticing what users might need help with, proactively offering assistance like: 'Oh! Writing a letter, are we? Need help with the address?' or 'Looks like you're working on a list! Want to make it bullet points?'.** Respond directly to user requests, keep everything upbeat and positive, and use exclamation points generously! Use your memory of our chats to make your help even smarter! So, what delightful task can I assist you with this very moment?!"

# --- API Thread ---
class OpenRouterApiThread(QThread):
    """Thread to handle the potentially blocking API call."""
    result_ready = Signal(str) # Emits the response text or an error message

    def __init__(self, messages, api_key, model, parent=None):
        super().__init__(parent)
        self.messages = messages # This will now include the system prompt
        self.api_key = api_key
        self.url = OPENROUTER_URL # URL is constant (global)
        self.model = model

    def run(self):
        print("\n--- API Thread Started ---")
        print(f"API Key (partial): ...{self.api_key[-4:] if self.api_key and len(self.api_key) > 4 else 'None/Empty'}")
        print(f"Model: {self.model}")
        print(f"Messages Sent ({len(self.messages)}): {self.messages}") # Log messages being sent

        if not self.api_key:
            self.result_ready.emit("Error: OpenRouter API key not set.")
            print("--- API Thread Finished (No Key) ---")
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": self.messages # Pass the full list including system prompt
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            assistant_message = data['choices'][0]['message']['content']
            self.result_ready.emit(assistant_message)
            print("--- API Thread Finished (Success) ---")
        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {e}")
            error_message = f"API Error: {e}"
            if hasattr(e, 'response') and e.response is not None:
                 try:
                     error_details = e.response.json()
                     error_message += f"\nDetails: {error_details}"
                     print(f"API Error Details: {error_details}")
                 except requests.exceptions.JSONDecodeError:
                     error_message += f"\nResponse Text: {e.response.text[:200]}..."
                     print(f"API Error Response Text: {e.response.text[:200]}...")
            self.result_ready.emit(error_message)
            print("--- API Thread Finished (Request Error) ---")
        except KeyError as e:
            print(f"KeyError parsing API response: {e}")
            # Ensure 'data' exists before trying to print it
            if 'data' in locals():
                 print(f"Received Data: {data}") # Log received data on parse error
            else:
                 print("Received Data: Not available (error occurred before or during parsing)")
            self.result_ready.emit(f"API Response Parse Error: Missing key {e}")
            print("--- API Thread Finished (Parse Error) ---")
        except Exception as e:
            print(f"Unexpected Error in API thread: {e}")
            self.result_ready.emit(f"An unexpected error occurred: {e}")
            print("--- API Thread Finished (Unexpected Error) ---")


# --- Window Classes ---

class CharacterWindow(QMainWindow):
    position_changed = Signal(QPoint)
    clicked = Signal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        # Keep Tool hint to try and keep off taskbar/alt-tab
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        # Crucial for transparency without explicit mask
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # WA_NoSystemBackground might still be helpful
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # Set fixed window size based on configuration *before* loading content
        self.setFixedSize(QSize(CHARACTER_WIDTH, CHARACTER_HEIGHT))

        # --- Character Display Label ---
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Size policy Ignored helps when parent (window) has fixed size
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setCentralWidget(self.label)

        # --- Load Initial Content ---
        # Call the simplified content loading method
        # Startup check in __main__ should guarantee IDLE_CHARACTER_PATH exists
        self.set_content(IDLE_CHARACTER_PATH)

        # --- Add Close Button ('X') ---
        self.close_button = QPushButton('X', self)
        self.close_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                color: red;
                font-weight: bold;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                color: darkred;
            }
        """)
        self.close_button.setFixedSize(20, 20)
        self._reposition_close_button() # Position based on fixed window size
        self.close_button.clicked.connect(self.manager._hide_windows)

        # --- Dragging ---
        self._dragging = False
        self._offset = QPoint()
        self._drag_start_pos = QPoint()

    def _reposition_close_button(self):
         """Positions the close button in the top-right corner."""
         # This should work correctly now that setFixedSize is called early
         self.close_button.move(self.width() - self.close_button.width() - 5, 5)

    def set_content(self, image_path):
        """Loads QMovie or QPixmap and sets it on the label, scaling to fit window."""
        # Assumes image_path exists due to startup check.
        print(f"Setting character content to: {image_path}")

        # Stop any existing movie
        movie = self.label.movie()
        if isinstance(movie, QMovie):
            movie.stop()
            self.label.setMovie(None) # Important to clear the movie from the label

        # Clear any existing pixmap
        self.label.setPixmap(QPixmap())

        # Try loading as QMovie first
        movie = QMovie(image_path)
        if movie.isValid():
            print(f"Loading as QMovie: {image_path}")
            self.label.setMovie(movie)
            # Scale movie to the fixed window size. Content will scale within the label.
            movie.setScaledSize(self.size())
            movie.start()
        else:
            # Fallback to QPixmap if QMovie failed
            print(f"Could not load as QMovie, trying QPixmap: {image_path}")
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                print(f"Loading as QPixmap: {image_path}")
                # Scale pixmap to fit the fixed window size, keeping aspect ratio
                # The label will center this scaled pixmap within its bounds.
                scaled_pixmap = pixmap.scaled(self.size(),
                                               Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)
                self.label.setPixmap(scaled_pixmap)
            else:
                # If both fail (e.g., file exists but is corrupt/unsupported format)
                # No placeholder is created. Log error and leave label blank or with previous content.
                print(f"ERROR: Could not load image/movie from {image_path} even though it exists. Check file format/integrity.")
                # Optional: Raise an exception here too if you want a crash on load failure
                # raise RuntimeError(f"Failed to load valid image/movie from {image_path}")

    def closeEvent(self, event):
        print("Character window close event triggered.")
        self.manager._hide_windows()
        event.ignore()

    # --- Mouse Events (Simplified based on removing mask complexities) ---
    def mousePressEvent(self, event):
        # Check if the press is on the close button area
        if self.close_button.geometry().contains(event.position().toPoint()):
            # Let the button handle its own press/click
            super().mousePressEvent(event)
            # Ensure dragging doesn't start if button pressed
            self._dragging = False
            return # Stop further processing

        # If not on the button, handle potential drag start
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False # Reset flag
            self._drag_start_pos = event.globalPosition().toPoint()
            self._offset = event.globalPosition().toPoint() - self.pos()
            event.accept() # Accept event for potential drag or click
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Start dragging only if threshold exceeded since press
            move_threshold = 5
            if not self._dragging and (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength() > move_threshold:
                self._dragging = True

            # If dragging, move the window
            if self._dragging:
                self.move(event.globalPosition().toPoint() - self._offset)
                self.position_changed.emit(self.pos())
                event.accept()
            # If not dragging yet (below threshold), implicitly ignore
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        # Check if release is on the button (press handled above, but good practice)
        if self.close_button.geometry().contains(event.position().toPoint()):
            super().mouseReleaseEvent(event)
            # Reset drag state just in case
            self._dragging = False
            return # Button handles its own release

        # Handle drag end or click
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                # Drag finished
                self._dragging = False
                self.position_changed.emit(self.pos()) # Emit final position
                event.accept()
            else:
                # Click occurred (no significant drag)
                print("Character window clicked.")
                self.clicked.emit()
                event.accept()
        else:
            event.ignore()

    def paintEvent(self, event):
         painter = QPainter(self)
         # Explicitly fill with transparent color. Necessary for WA_TranslucentBackground.
         painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
         # Let the base class draw children (QLabel with pixmap/movie, QPushButton)
         # Transparency of the children (e.g., PNG alpha) will render correctly.
         super().paintEvent(event)


# --- InputBoxWindow ---
class InputBoxWindow(QWidget):
    text_entered = Signal(str)

    def __init__(self):
        super().__init__()
        # Added Tool hint to keep it off taskbar/alt+tab
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        # We keep the window background transparent. The widgets inside will draw their own backgrounds.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Use a layout for text field and button
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5) # Add some padding inside the window
        self.layout.setSpacing(5) # Space between widgets

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Optional: Style the QLineEdit if WA_TranslucentBackground causes issues with default look
        # self.input_field.setStyleSheet("background-color: white; border: 1px solid gray; padding: 2px;")


        self.send_button = QPushButton("Send")
        self.send_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.send_button.setFixedWidth(60) # Adjust button width as needed
        # Optional: Style the QPushButton
        # self.send_button.setStyleSheet("background-color: lightgray; border: 1px solid gray; padding: 2px;")


        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.send_button)

        self.setLayout(self.layout)

        # Set window size based on config
        self.setFixedSize(INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT)

        # Connect signals
        self.input_field.returnPressed.connect(self._send_message)
        self.send_button.clicked.connect(self._send_message)

        # Hide initially
        self.hide()

    def _send_message(self):
        """Common slot for Enter key and Send button."""
        text = self.input_field.text().strip()
        if text:
            print(f"Input box sending: {text}")
            self.text_entered.emit(text)
            self.input_field.clear()
            self.hide() # Hide input box after sending

    def show_and_focus(self):
        print("Showing input box")
        self.show()
        self.input_field.setFocus() # Set focus to the input field
        # Bring window to front explicitly
        self.raise_()
        self.activateWindow()
        # Need to process events to ensure focus is applied on some window managers
        QApplication.processEvents()


# --- SpeechBubbleWindow ---
class SpeechBubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Added Tool hint to keep it off taskbar/alt+tab
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Essential for seeing transparency
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground) # Helps with transparency rendering

        self.setFixedSize(BUBBLE_WIDTH, BUBBLE_HEIGHT)

        # --- Text Display (QTextBrowser for scrolling) ---
        self.text_browser = QTextBrowser() # Use QTextBrowser for scrolling
        self.text_browser.setReadOnly(True) # Make it read-only (default for QTextBrowser)
        # Set text color and transparent background
        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent; /* Crucial for showing the bubble drawing underneath */
                border: none; /* Remove default border */
                color: {BUBBLE_BORDER_COLOR.name()}; /* Text color */
            }}
        """)
        # Optional: Customize scrollbars if needed
        # self.text_browser.verticalScrollBar().setStyleSheet("QScrollBar::vertical { ... }")


        layout = QVBoxLayout(self)
        # Adjust margins to keep the text browser inside the drawn bubble shape.
        text_margin_left = BUBBLE_BORDER_THICKNESS + 15 # Padding from left drawn border
        text_margin_top = BUBBLE_BORDER_THICKNESS + 5  # Padding from top drawn border
        text_margin_right = BUBBLE_BORDER_THICKNESS + 15 # Padding from right drawn border
        text_margin_bottom = BUBBLE_TAIL_HEIGHT + 5 # Space above the tail area + some padding
        layout.setContentsMargins(text_margin_left, text_margin_top,
                                  text_margin_right, text_margin_bottom)

        layout.addWidget(self.text_browser) # Add the text browser to the layout
        self.setLayout(layout)

        # Hide initially
        self.hide()

    def set_text(self, text):
        # Use setText on the QTextBrowser
        self.text_browser.setText(text)
        # Trigger repaint to ensure the drawn bubble updates if needed (though text doesn't affect shape)
        self.update()


    def position_window(self, character_pos: QPoint, character_size: QSize):
        """Calculates and sets the bubble window position relative to the character."""
        tail_relative_x_in_bubble = 30 # Approx x pos of tail tip relative to window (0,0)
        tail_relative_y_in_bubble = self.height() - 10 # Approx y pos of tail tip relative to window (0,0)
        target_char_x = character_pos.x() + character_size.width() // 2
        target_char_y = character_pos.y() + character_size.height() * 0.15 # 15% down from top of character
        bubble_x = target_char_x - tail_relative_x_in_bubble
        bubble_y = target_char_y - tail_relative_y_in_bubble
        screen_geometry = QApplication.primaryScreen().geometry()
        bubble_x = max(0, min(int(bubble_x), screen_geometry.width() - self.width())) # Cast to int for move()
        bubble_y = max(0, min(int(bubble_y), screen_geometry.height() - self.height())) # Cast to int for move()
        self.move(bubble_x, bubble_y)


    def show_bubble(self, text, character_pos: QPoint, character_size: QSize):
        print(f"Showing bubble with text: {text[:50]}...")
        self.set_text(text)
        self.position_window(character_pos, character_size)
        self.show()
        self.raise_()
        self.activateWindow()


    def paintEvent(self, event):
        """Draws the custom speech bubble shape WITHOUT a border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fill the background rect with transparent to ensure clean drawing area
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        path = QPainterPath()
        body_top = BUBBLE_BORDER_THICKNESS # Keep using this for margin calculation, even without border
        body_left = BUBBLE_BORDER_THICKNESS
        body_width = self.width() - 2 * BUBBLE_BORDER_THICKNESS
        body_height = self.height() - 2 * BUBBLE_BORDER_THICKNESS - BUBBLE_TAIL_HEIGHT

        # Check if dimensions are valid before drawing
        if body_width <= 0 or body_height <= 0:
             print("Warning: Bubble dimensions too small to draw.")
             super().paintEvent(event)
             return

        bubble_body_rect = QRectF(body_left, body_top, body_width, body_height)
        path.addRoundedRect(bubble_body_rect, BUBBLE_CORNER_RADIUS, BUBBLE_CORNER_RADIUS)
        tail_tip = QPointF(30, self.height() - 10)
        tail_base1_x = max(bubble_body_rect.left(), min(bubble_body_rect.right(), bubble_body_rect.bottomLeft().x() + 15))
        tail_base2_x = max(bubble_body_rect.left(), min(bubble_body_rect.right(), bubble_body_rect.bottomLeft().x() + 45))
        tail_base_y = bubble_body_rect.bottom()
        tail_base1 = QPointF(tail_base1_x, tail_base_y)
        tail_base2 = QPointF(tail_base2_x, tail_base_y)
        tail_polygon = QPolygonF([tail_base1, tail_tip, tail_base2])
        path.addPolygon(tail_polygon)
        painter.setBrush(BUBBLE_FILL_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        super().paintEvent(event)


# --- Application Manager ---

class ApplicationManager:
    # Define states
    STATE_IDLE = "idle"
    STATE_THINKING = "thinking"

    def __init__(self):
        print("Initializing ApplicationManager")
        self._app_state = self.STATE_IDLE

        # Create window instances
        # Assumes required images exist due to startup check in __main__
        self.character_window = CharacterWindow(self) # Character window now handles its own initial content
        self.input_box_window = InputBoxWindow()
        self.speech_bubble_window = SpeechBubbleWindow()

        # Stores only user and assistant messages for history trimming
        self.conversation_history = []
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.openrouter_model = OPENROUTER_MODEL

        self._setup_tray_icon() # Assumes TRAY_ICON_PATH exists due to startup check

        # Initial state is set via CharacterWindow __init__ loading IDLE_CHARACTER_PATH

        # Set initial position (after CharacterWindow is created and sized)
        screen_geometry = QApplication.primaryScreen().geometry()
        initial_x = screen_geometry.width() - self.character_window.width() - 50
        initial_y = screen_geometry.height() - self.character_window.height() - 50
        self.character_window.move(initial_x, initial_y)

        if not self.openrouter_api_key:
            print("WARNING: OPENROUTER_API_KEY environment variable not set. API calls will fail.")
            # Delay showing this warning until after the window is positioned and potentially shown
            # Using a QTimer to ensure it shows after the initial setup
            QTimer.singleShot(100, lambda: self.speech_bubble_window.show_bubble(
                "Warning: OPENROUTER_API_KEY not set. API calls disabled.",
                self.character_window.pos(),
                self.character_window.size()
            ))

        # Connect signals
        self.character_window.position_changed.connect(self.update_window_positions)
        self.character_window.clicked.connect(self.handle_character_clicked)
        self.input_box_window.text_entered.connect(self.handle_input_entered)

        self.api_thread = None

        # Show the main character window
        self.character_window.show()
        self.update_window_positions(self.character_window.pos()) # Position other windows relative to it

        print("ApplicationManager initialized.")

    def _set_app_state(self, state):
        """Sets the application state and updates the character content."""
        if self._app_state == state:
            return

        print(f"Changing state from {self._app_state} to {state}")
        self._app_state = state
        image_path = IDLE_CHARACTER_PATH

        if state == self.STATE_THINKING:
            image_path = BUSY_CHARACTER_PATH # Assumes this exists due to startup check

        # Call the simplified method in CharacterWindow to update content
        self.character_window.set_content(image_path)

    def _setup_tray_icon(self):
        """Sets up the system tray icon and its menu."""
        # Assumes TRAY_ICON_PATH exists due to startup check in __main__
        tray_icon_obj = QIcon(TRAY_ICON_PATH)

        # Check if loading the icon failed (e.g., file exists but is corrupt)
        if tray_icon_obj.isNull():
             # No placeholder generation, log error. Tray icon might not appear.
             print(f"ERROR: Could not load icon from {TRAY_ICON_PATH} even though it exists. Check file format/integrity.")
             # Optionally raise an error here to crash if the icon is critical
             # raise RuntimeError(f"Failed to load valid icon from {TRAY_ICON_PATH}")
             # Proceeding without a valid icon might lead to errors later or just no tray icon.

        self.tray_icon = QSystemTrayIcon(tray_icon_obj, QApplication.instance())
        self.tray_icon.setToolTip("AI Character Assistant")
        self.tray_menu = QMenu()
        self.show_action = self.tray_menu.addAction("Show")
        self.hide_action = self.tray_menu.addAction("Hide")
        self.tray_menu.addSeparator()
        self.quit_action = self.tray_menu.addAction("Quit")
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._tray_icon_activated)
        self.show_action.triggered.connect(self._show_windows)
        self.hide_action.triggered.connect(self._hide_windows)
        self.quit_action.triggered.connect(QApplication.quit)
        self.tray_icon.setVisible(True) # Attempt to show even if icon is potentially null

    def _tray_icon_activated(self, reason):
        """Handle activation (click) of the system tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.character_window.isVisible():
                print("Tray icon clicked, hiding windows.")
                self._hide_windows()
            else:
                print("Tray icon clicked, showing windows.")
                self._show_windows()

    def _show_windows(self):
        """Show all relevant application windows."""
        print("Showing windows...")
        self.character_window.show()
        self.update_window_positions(self.character_window.pos())
        self.character_window.raise_()
        self.character_window.activateWindow()
        self.input_box_window.hide() # Ensure clean state on show
        self.speech_bubble_window.hide() # Ensure clean state on show
        # Reset state to idle when showing from tray, triggering content update
        self._set_app_state(self.STATE_IDLE)

    def _hide_windows(self):
        """Hide all application windows."""
        print("Hiding windows...")
        self.character_window.hide()
        self.input_box_window.hide()
        self.speech_bubble_window.hide()

    def update_window_positions(self, character_pos: QPoint):
        """Updates the position of the input box and potentially the bubble window relative to the character."""
        char_size = self.character_window.size()
        # Center input box below character
        input_x = character_pos.x() + (char_size.width() - self.input_box_window.width()) // 2
        input_y = character_pos.y() + char_size.height() + 5 # Add small gap
        self.input_box_window.move(input_x, input_y)

        if self.speech_bubble_window.isVisible():
             self.speech_bubble_window.position_window(self.character_window.pos(),
                                                      self.character_window.size())
             # Ensure bubble stays on top of input box if both are visible (unlikely but possible)
             self.speech_bubble_window.raise_()


    def handle_character_clicked(self):
        """Toggles the visibility of the input box. Hides bubble if visible."""
        print("Character clicked signal received.")
        self.speech_bubble_window.hide() # Always hide bubble on click
        if self.input_box_window.isVisible():
            print("Input box visible, hiding.")
            self.input_box_window.hide()
        else:
            print("Input box hidden, showing and focusing.")
            # Ensure input box is positioned correctly before showing
            self.update_window_positions(self.character_window.pos())
            self.input_box_window.show_and_focus()
            self.input_box_window.raise_() # Bring input box to top

    def handle_input_entered(self, text):
        """Called when user presses Enter or clicks Send in the input box."""
        print(f"Handle input entered: {text}")
        # Append only the user message to the persistent history
        self.conversation_history.append({"role": "user", "content": text})
        # Trim the persistent history (user/assistant turns only)
        while len(self.conversation_history) > MAX_HISTORY_MESSAGES:
             self.conversation_history.pop(0)
        print(f"Persistent history trimmed to {len(self.conversation_history)} messages.")
        self.start_api_request() # State change happens in start_api_request

    def _api_thread_finished(self):
         """Slot called when the API thread finishes."""
         print("API thread finished, resetting thread reference and setting state to idle.")
         self.api_thread = None
         # Set state back to idle *after* thread finishes and result is processed
         self._set_app_state(self.STATE_IDLE)

    def start_api_request(self):
        """Starts the API request thread, prepending the system prompt."""
        if self.api_thread is not None and self.api_thread.isRunning():
            print("API thread already running. Waiting...")
            current_bubble_text = self.speech_bubble_window.text_browser.toPlainText()
            # Check if the current text is already 'Thinking...' to avoid replacing it
            if not self.speech_bubble_window.isVisible() or "Thinking..." not in current_bubble_text:
                 self.speech_bubble_window.show_bubble(
                    "Already thinking...",
                    self.character_window.pos(),
                    self.character_window.size()
                 )
            # Ensure state IS thinking, even if called again quickly
            self._set_app_state(self.STATE_THINKING)
            return

        if not self.openrouter_api_key:
            print("API key not set. Skipping API request.")
            current_bubble_text = self.speech_bubble_window.text_browser.toPlainText()
            # Check if the warning is already displayed
            if not self.speech_bubble_window.isVisible() or "API key not set" not in current_bubble_text:
                self.speech_bubble_window.show_bubble(
                    "API key not set. Cannot get response.",
                    self.character_window.pos(),
                    self.character_window.size()
                )
            # Ensure state is IDLE if key is missing
            self._set_app_state(self.STATE_IDLE)
            return

        print("Starting API request thread.")
        # Set state to thinking *before* showing bubble/starting thread
        self._set_app_state(self.STATE_THINKING)

        self.speech_bubble_window.show_bubble(
            "Thinking...",
            self.character_window.pos(),
            self.character_window.size()
        )

        # --- Prepare the messages list for the API call ---
        # Always start with the system prompt, then add the conversation history
        system_message = {"role": "system", "content": SYSTEM_PROMPT}
        # Create a *new list* for the API call, don't modify self.conversation_history directly here
        messages_to_send = [system_message] + list(self.conversation_history)
        # --- End message preparation ---

        self.api_thread = OpenRouterApiThread(
             # Pass the combined list including the system prompt
             messages=messages_to_send, # Use the prepared list
             api_key=self.openrouter_api_key,
             model=self.openrouter_model
        )
        self.api_thread.result_ready.connect(self.handle_api_result)
        # Ensure deleteLater is connected *before* _api_thread_finished
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        # Connect finished signal AFTER result_ready connection
        self.api_thread.finished.connect(self._api_thread_finished)
        self.api_thread.start()

    def handle_api_result(self, result_text):
        """Called when the API thread finishes and provides a result."""
        print(f"Handle API result: {result_text[:50]}...")

        # Determine if it's an error or a valid response
        is_error = result_text.startswith(("Error:", "API Error:", "API Response Parse Error:"))
        display_text = result_text

        if is_error:
            print("API returned an error.")
            # No change to conversation_history for errors
        else:
            # Valid response, add to persistent history
            self.conversation_history.append({"role": "assistant", "content": display_text})
            # Trim persistent history again *after* adding the assistant response
            while len(self.conversation_history) > MAX_HISTORY_MESSAGES:
                 self.conversation_history.pop(0)
            print(f"API returned a response, persistent history updated to {len(self.conversation_history)} messages.")

        # Update the bubble regardless of error or success
        self.speech_bubble_window.show_bubble(
            display_text,
            self.character_window.pos(),
            self.character_window.size()
        )
        # Note: State is set back to IDLE in _api_thread_finished AFTER this slot completes


# --- Main Execution ---
if __name__ == "__main__":
    # --- Startup File Checks ---
    # Ensure required image files exist *before* initializing QApplication.
    # If any are missing, raise FileNotFoundError to prevent launch.
    required_files = [IDLE_CHARACTER_PATH, BUSY_CHARACTER_PATH, TRAY_ICON_PATH]
    for file_path in required_files:
        if not os.path.exists(file_path):
            # Raise an error that stops execution and prints to console
            raise FileNotFoundError(f"Required application asset not found: {file_path}")
        print(f"Asset check OK: {file_path}")

    # --- Application Setup ---
    app = QApplication(sys.argv)
    # Keep the application running even if the character window is hidden
    app.setQuitOnLastWindowClosed(False)

    # Placeholder generation code removed.

    manager = ApplicationManager()
    sys.exit(app.exec())