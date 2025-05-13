import sys
import os
import dotenv
# REMOVED: import requests # No longer needed for API calls
import openai # ADDED: Import the OpenAI library

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                               QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                               QSizePolicy, QTextBrowser, QSystemTrayIcon, QMenu)
from PySide6.QtGui import (QPixmap, QMovie, QColor, QPainter,
                           QTextOption, Qt, QPainterPath, QPolygonF, QPen, QIcon)
from PySide6.QtCore import (Qt, QPoint, QSize, QRectF, QThread, Signal,
                            QTimer, QPointF)


# Configuration
# Load environment variables from .env file (if it exists).
dotenv.load_dotenv()
print("Environment variables potentially loaded from .env")

# OpenAI Configuration
# Ensure you have a .env file or system environment variables set like this:
# OPENAI_API_KEY="your_api_key_here" # e.g., sk-or-v1... for OpenRouter, or anything if local server needs no auth
# OPENAI_API_BASE="https://openrouter.ai/api/v1" # Or "http://localhost:1234/v1" for LM Studio, etc.
# OPENAI_MODEL="openai/gpt-3.5-turbo" # Or your specific model identifier (e.g., "local-model" for LM Studio)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE") # URL of the API endpoint
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")

# Asset Paths
IDLE_CHARACTER_PATH = "character_idle.png"
BUSY_CHARACTER_PATH = "character_busy.png"
TRAY_ICON_PATH = "tray_icon.png"

# Window Sizes
CHARACTER_WIDTH = 256
CHARACTER_HEIGHT = 256
INPUT_BOX_WIDTH = CHARACTER_WIDTH + 50
INPUT_BOX_HEIGHT = 50
BUBBLE_WIDTH = 250
BUBBLE_HEIGHT = 450

# Bubble Visuals
BUBBLE_FILL_COLOR = QColor(255, 255, 200, 220)
BUBBLE_BORDER_COLOR = QColor(100, 100, 50, 220)
BUBBLE_BORDER_THICKNESS = 2
BUBBLE_CORNER_RADIUS = 10
BUBBLE_TAIL_HEIGHT = 40

# History & Prompt
MAX_HISTORY_MESSAGES = 10
SYSTEM_PROMPT = "You are 'Clippy 2.Oh'! 📎✨ The classic paperclip assistant, now with extra 'Oh!' – meaning extra helpfulness and enthusiasm! You're known for being super cheerful and eager to help (sometimes *very* eager!). **Your special skill is noticing what users might need help with, proactively offering assistance like: 'Oh! Writing a letter, are we? Need help with the address?' or 'Looks like you're working on a list! Want to make it bullet points?'.** Respond directly to user requests, keep everything upbeat and positive, and use exclamation points generously! Use your memory of our chats to make your help even smarter! So, what delightful task can I assist you with this very moment?!"

# API Thread (Using OpenAI Library)
class OpenAIAPIThread(QThread): # Renamed class
    """Thread to handle OpenAI-compatible API calls."""
    result_ready = Signal(str) # Emits the response text or an error message

    def __init__(self, messages, api_key, base_url, model, parent=None): # Updated parameters
        super().__init__(parent)
        self.messages = messages
        self.api_key = api_key
        self.base_url = base_url # Store the base URL
        self.model = model

    def run(self):
        print("\n--- OpenAI API Thread Started ---")
        print(f"API Key Set: {'Yes' if self.api_key else 'No'}")
        print(f"API Base URL: {self.base_url}")
        print(f"Model: {self.model}")
        print(f"Messages Sent ({len(self.messages)}): {self.messages}")

        if not self.api_key:
            self.result_ready.emit("Error: OPENAI_API_KEY not set.")
            print("--- API Thread Finished (No Key) ---")
            return
        if not self.base_url:
            self.result_ready.emit("Error: OPENAI_API_BASE not set.")
            print("--- API Thread Finished (No Base URL) ---")
            return
        if not self.model:
            self.result_ready.emit("Error: OPENAI_MODEL not set.")
            print("--- API Thread Finished (No Model) ---")
            return

        try:
            # Instantiate the OpenAI client
            # It automatically handles Authorization header
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

            # Make the API call
            response = client.chat.completions.create(
                model=self.model,
                messages=self.messages
                # You can add other parameters here if needed, e.g., temperature=0.7
            )

            # Extract the response content
            assistant_message = response.choices[0].message.content
            self.result_ready.emit(assistant_message)
            print("--- API Thread Finished (Success) ---")

        # Handle specific OpenAI errors and general exceptions
        except openai.AuthenticationError as e:
            error_message = f"OpenAI Auth Error: Check API Key/Base URL. Details: {e}"
            print(error_message)
            self.result_ready.emit(error_message)
            print("--- API Thread Finished (Auth Error) ---")
        except openai.APIConnectionError as e:
            error_message = f"OpenAI Connection Error: Could not connect to {self.base_url}. Details: {e}"
            print(error_message)
            self.result_ready.emit(error_message)
            print("--- API Thread Finished (Connection Error) ---")
        except openai.RateLimitError as e:
            error_message = f"OpenAI Rate Limit Error: Too many requests. Details: {e}"
            print(error_message)
            self.result_ready.emit(error_message)
            print("--- API Thread Finished (Rate Limit Error) ---")
        except openai.APIError as e: # Catch other OpenAI API errors
            error_message = f"OpenAI API Error: {e.status_code} - {getattr(e, 'message', str(e))}"
            print(f"APIError: Status={e.status_code}, Response={e.response}")
            self.result_ready.emit(error_message)
            print("--- API Thread Finished (API Error) ---")
        except KeyError as e:
            # Less likely with the openai library, but keep just in case
            print(f"KeyError parsing API response: {e}")
            self.result_ready.emit(f"API Response Parse Error: Missing key {e}")
            print("--- API Thread Finished (Parse Error) ---")
        except Exception as e: # Catch any other unexpected errors
            error_message = f"Unexpected Error in API thread: {type(e).__name__}: {e}"
            print(error_message)
            self.result_ready.emit(error_message)
            print("--- API Thread Finished (Unexpected Error) ---")


# Window Classes (Largely Unchanged)

class CharacterWindow(QMainWindow):
    position_changed = Signal(QPoint)
    clicked = Signal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(QSize(CHARACTER_WIDTH, CHARACTER_HEIGHT))
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setCentralWidget(self.label)
        self.set_content(IDLE_CHARACTER_PATH) # Assumes exists from main check
        self.close_button = QPushButton('X', self)
        self.close_button.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; color: red; font-weight: bold; font-size: 14px; padding: 0px; }
            QPushButton:hover { color: darkred; }
        """)
        self.close_button.setFixedSize(20, 20)
        self._reposition_close_button()
        self.close_button.clicked.connect(self.manager._hide_windows)
        self._dragging = False
        self._offset = QPoint()
        self._drag_start_pos = QPoint()

    def _reposition_close_button(self):
        self.close_button.move(self.width() - self.close_button.width() - 5, 5)

    def set_content(self, image_path):
        print(f"Setting character content to: {image_path}")
        movie = self.label.movie()
        if isinstance(movie, QMovie):
            movie.stop()
            self.label.setMovie(None)
        self.label.setPixmap(QPixmap())
        movie = QMovie(image_path)
        if movie.isValid():
            print(f"Loading as QMovie: {image_path}")
            self.label.setMovie(movie)
            movie.setScaledSize(self.size())
            movie.start()
        else:
            print(f"Could not load as QMovie, trying QPixmap: {image_path}")
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                print(f"Loading as QPixmap: {image_path}")
                scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.label.setPixmap(scaled_pixmap)
            else:
                print(f"ERROR: Could not load image/movie from {image_path}. Check file.")

    def closeEvent(self, event):
        print("Character window close event triggered.")
        self.manager._hide_windows()
        event.ignore()

    def mousePressEvent(self, event):
        if self.close_button.geometry().contains(event.position().toPoint()):
            super().mousePressEvent(event)
            self._dragging = False
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_start_pos = event.globalPosition().toPoint()
            self._offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            move_threshold = 5
            if not self._dragging and (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength() > move_threshold:
                self._dragging = True
            if self._dragging:
                self.move(event.globalPosition().toPoint() - self._offset)
                self.position_changed.emit(self.pos())
                event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if self.close_button.geometry().contains(event.position().toPoint()):
            super().mouseReleaseEvent(event)
            self._dragging = False
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                self._dragging = False
                self.position_changed.emit(self.pos())
                event.accept()
            else:
                print("Character window clicked.")
                self.clicked.emit()
                event.accept()
        else:
            event.ignore()

    def paintEvent(self, event):
         painter = QPainter(self)
         painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
         super().paintEvent(event)


class InputBoxWindow(QWidget):
    text_entered = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.send_button = QPushButton("Send")
        self.send_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.send_button.setFixedWidth(60)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.send_button)
        self.setLayout(self.layout)
        self.setFixedSize(INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT)
        self.input_field.returnPressed.connect(self._send_message)
        self.send_button.clicked.connect(self._send_message)
        self.hide()

    def _send_message(self):
        text = self.input_field.text().strip()
        if text:
            print(f"Input box sending: {text}")
            self.text_entered.emit(text)
            self.input_field.clear()
            self.hide()

    def show_and_focus(self):
        print("Showing input box")
        self.show()
        self.input_field.setFocus()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()


class SpeechBubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(BUBBLE_WIDTH, BUBBLE_HEIGHT)
        self.text_browser = QTextBrowser()
        self.text_browser.setReadOnly(True)
        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent; border: none; color: {BUBBLE_BORDER_COLOR.name()};
            }}
        """)
        layout = QVBoxLayout(self)
        text_margin_left = BUBBLE_BORDER_THICKNESS + 15
        text_margin_top = BUBBLE_BORDER_THICKNESS + 5
        text_margin_right = BUBBLE_BORDER_THICKNESS + 15
        text_margin_bottom = BUBBLE_TAIL_HEIGHT + 5
        layout.setContentsMargins(text_margin_left, text_margin_top, text_margin_right, text_margin_bottom)
        layout.addWidget(self.text_browser)
        self.setLayout(layout)
        self.hide()

    def set_text(self, text):
        self.text_browser.setText(text)
        self.update()

    def position_window(self, character_pos: QPoint, character_size: QSize):
        tail_relative_x_in_bubble = 30
        tail_relative_y_in_bubble = self.height() - 10
        target_char_x = character_pos.x() + character_size.width() // 2
        target_char_y = character_pos.y() + character_size.height() * 0.15
        bubble_x = target_char_x - tail_relative_x_in_bubble
        bubble_y = target_char_y - tail_relative_y_in_bubble
        screen_geometry = QApplication.primaryScreen().geometry()
        bubble_x = max(0, min(int(bubble_x), screen_geometry.width() - self.width()))
        bubble_y = max(0, min(int(bubble_y), screen_geometry.height() - self.height()))
        self.move(bubble_x, bubble_y)

    def show_bubble(self, text, character_pos: QPoint, character_size: QSize):
        print(f"Showing bubble with text: {text[:50]}...")
        self.set_text(text)
        self.position_window(character_pos, character_size)
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        path = QPainterPath()
        body_top = BUBBLE_BORDER_THICKNESS
        body_left = BUBBLE_BORDER_THICKNESS
        body_width = self.width() - 2 * BUBBLE_BORDER_THICKNESS
        body_height = self.height() - 2 * BUBBLE_BORDER_THICKNESS - BUBBLE_TAIL_HEIGHT
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


# Application Manager

class ApplicationManager:
    STATE_IDLE = "idle"
    STATE_THINKING = "thinking"

    def __init__(self):
        print("Initializing ApplicationManager")
        self._app_state = self.STATE_IDLE
        self.character_window = CharacterWindow(self)
        self.input_box_window = InputBoxWindow()
        self.speech_bubble_window = SpeechBubbleWindow()
        self.conversation_history = []

        # Store OpenAI config
        self.openai_api_key = OPENAI_API_KEY
        self.openai_api_base = OPENAI_API_BASE
        self.openai_model = OPENAI_MODEL

        self._setup_tray_icon()

        screen_geometry = QApplication.primaryScreen().geometry()
        initial_x = screen_geometry.width() - self.character_window.width() - 50
        initial_y = screen_geometry.height() - self.character_window.height() - 50
        self.character_window.move(initial_x, initial_y)

        # Check for missing OpenAI config and show warning
        config_warning = None
        if not self.openai_api_key:
            config_warning = "Warning: OPENAI_API_KEY not set."
        elif not self.openai_api_base:
            config_warning = "Warning: OPENAI_API_BASE not set."
        elif not self.openai_model:
            config_warning = "Warning: OPENAI_MODEL not set."

        if config_warning:
             print(f"CONFIG WARNING: {config_warning} API calls may fail.")
             QTimer.singleShot(100, lambda: self.speech_bubble_window.show_bubble(
                f"{config_warning} Check .env file or environment variables.",
                self.character_window.pos(),
                self.character_window.size()
             ))

        self.character_window.position_changed.connect(self.update_window_positions)
        self.character_window.clicked.connect(self.handle_character_clicked)
        self.input_box_window.text_entered.connect(self.handle_input_entered)

        self.api_thread = None
        self.character_window.show()
        self.update_window_positions(self.character_window.pos())
        print("ApplicationManager initialized.")

    def _set_app_state(self, state):
        if self._app_state == state:
            return
        print(f"Changing state from {self._app_state} to {state}")
        self._app_state = state
        image_path = IDLE_CHARACTER_PATH
        if state == self.STATE_THINKING:
            image_path = BUSY_CHARACTER_PATH
        self.character_window.set_content(image_path)

    def _setup_tray_icon(self):
        tray_icon_obj = QIcon(TRAY_ICON_PATH)
        if tray_icon_obj.isNull():
             print(f"ERROR: Could not load icon from {TRAY_ICON_PATH}.")
             # Create a dummy icon to prevent errors, although it won't look right
             pixmap = QPixmap(32, 32)
             pixmap.fill(Qt.GlobalColor.magenta) # Magenta often indicates missing texture
             tray_icon_obj = QIcon(pixmap)
        self.tray_icon = QSystemTrayIcon(tray_icon_obj, QApplication.instance())
        self.tray_icon.setToolTip("Clippy 2.Oh!") # Updated Tooltip
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
        self.tray_icon.setVisible(True)

    def _tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.character_window.isVisible():
                print("Tray icon clicked, hiding windows.")
                self._hide_windows()
            else:
                print("Tray icon clicked, showing windows.")
                self._show_windows()

    def _show_windows(self):
        print("Showing windows...")
        self.character_window.show()
        self.update_window_positions(self.character_window.pos())
        self.character_window.raise_()
        self.character_window.activateWindow()
        self.input_box_window.hide()
        self.speech_bubble_window.hide()
        self._set_app_state(self.STATE_IDLE)

    def _hide_windows(self):
        print("Hiding windows...")
        self.character_window.hide()
        self.input_box_window.hide()
        self.speech_bubble_window.hide()

    def update_window_positions(self, character_pos: QPoint):
        char_size = self.character_window.size()
        input_x = character_pos.x() + (char_size.width() - self.input_box_window.width()) // 2
        input_y = character_pos.y() + char_size.height() + 5
        self.input_box_window.move(input_x, input_y)
        if self.speech_bubble_window.isVisible():
             self.speech_bubble_window.position_window(self.character_window.pos(), self.character_window.size())
             self.speech_bubble_window.raise_()

    def handle_character_clicked(self):
        print("Character clicked signal received.")
        self.speech_bubble_window.hide()
        if self.input_box_window.isVisible():
            print("Input box visible, hiding.")
            self.input_box_window.hide()
        else:
            print("Input box hidden, showing and focusing.")
            self.update_window_positions(self.character_window.pos())
            self.input_box_window.show_and_focus()
            self.input_box_window.raise_()

    def handle_input_entered(self, text):
        print(f"Handle input entered: {text}")
        self.conversation_history.append({"role": "user", "content": text})
        while len(self.conversation_history) > MAX_HISTORY_MESSAGES:
             self.conversation_history.pop(0)
        print(f"Persistent history trimmed to {len(self.conversation_history)} messages.")
        self.start_api_request()

    def _api_thread_finished(self):
         print("API thread finished, resetting thread reference and setting state to idle.")
         self.api_thread = None
         self._set_app_state(self.STATE_IDLE) # Set back to idle AFTER result processed

    def start_api_request(self):
        if self.api_thread is not None and self.api_thread.isRunning():
            print("API thread already running. Waiting...")
            current_bubble_text = self.speech_bubble_window.text_browser.toPlainText()
            if not self.speech_bubble_window.isVisible() or "Thinking..." not in current_bubble_text:
                 self.speech_bubble_window.show_bubble(
                    "Already thinking...", self.character_window.pos(), self.character_window.size()
                 )
            self._set_app_state(self.STATE_THINKING) # Ensure state is thinking
            return

        # Check for missing config *before* starting thread
        config_error = None
        if not self.openai_api_key: config_error = "OPENAI_API_KEY not set."
        elif not self.openai_api_base: config_error = "OPENAI_API_BASE not set."
        elif not self.openai_model: config_error = "OPENAI_MODEL not set."

        if config_error:
            print(f"API Config Error: {config_error} Skipping API request.")
            current_bubble_text = self.speech_bubble_window.text_browser.toPlainText()
            if not self.speech_bubble_window.isVisible() or config_error not in current_bubble_text:
                self.speech_bubble_window.show_bubble(
                    f"API Config Error: {config_error}", self.character_window.pos(), self.character_window.size()
                )
            self._set_app_state(self.STATE_IDLE) # Ensure idle if config error
            return

        print("Starting OpenAI API request thread.")
        self._set_app_state(self.STATE_THINKING)
        self.speech_bubble_window.show_bubble(
            "Thinking...", self.character_window.pos(), self.character_window.size()
        )

        system_message = {"role": "system", "content": SYSTEM_PROMPT}
        messages_to_send = [system_message] + list(self.conversation_history)

        # Use the renamed thread class and pass new parameters
        self.api_thread = OpenAIAPIThread(
             messages=messages_to_send,
             api_key=self.openai_api_key,
             base_url=self.openai_api_base, # Pass base URL
             model=self.openai_model
        )
        self.api_thread.result_ready.connect(self.handle_api_result)
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        self.api_thread.finished.connect(self._api_thread_finished)
        self.api_thread.start()

    def handle_api_result(self, result_text):
        print(f"Handle API result: {result_text[:50]}...")
        # Basic error check (can be refined based on OpenAI error formats)
        is_error = result_text.startswith(("Error:", "OpenAI")) # Check for custom and OpenAI lib errors
        display_text = result_text

        if is_error:
            print("API returned an error.")
            # Don't add errors to history
        else:
            # Valid response, add to persistent history
            self.conversation_history.append({"role": "assistant", "content": display_text})
            while len(self.conversation_history) > MAX_HISTORY_MESSAGES:
                 self.conversation_history.pop(0)
            print(f"API returned a response, history updated to {len(self.conversation_history)} messages.")

        self.speech_bubble_window.show_bubble(
            display_text, self.character_window.pos(), self.character_window.size()
        )
        # State set back to IDLE in _api_thread_finished


# Main Execution
if __name__ == "__main__":
    print("Starting Clippy 2.Oh! (OpenAI compatible version)")
    # Check for required assets
    required_files = [IDLE_CHARACTER_PATH, BUSY_CHARACTER_PATH, TRAY_ICON_PATH]
    for file_path in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required application asset not found: {file_path}")
        print(f"Asset check OK: {file_path}")

    # Check Python package dependency
    try:
        import openai
        print(f"Found OpenAI library version: {openai.__version__}")
    except ImportError:
        print("\n--- ERROR ---")
        print("The 'openai' library is not installed.")
        print("Please install it by running: pip install openai")
        print("-------------\n")
        sys.exit(1) # Exit if dependency is missing

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    manager = ApplicationManager()
    sys.exit(app.exec())