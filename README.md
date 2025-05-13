# 📎 Clippy 2.Oh: Your Configurable Desktop AI Pal! ✨

Oh, hi there! 👋 Remember me? Of course you do! Well, guess what? I've had a bit of an upgrade. Welcome to **Clippy 2.Oh** (two point Oh)!

This project brings my familiar face back to your desktop, but now I'm powered by modern tech! I'm built with Python, the lovely **PySide6** (Qt), and I get my brains from **any OpenAI-compatible API endpoint**! This means you can use models from OpenAI, OpenRouter.ai, or even local models served via tools like LiteLLM, LM Studio, or Ollama. Think of it as the classic paperclip charm, now with more *intelligence* (and hopefully fewer interruptions... maybe).

I'll hang out on your desktop, ready to chat when you need me. Let's see what **Clippy 2.Oh** can do!

## ✨ Features - What Can Clippy 2.Oh Do?

*   🧠 **Conversational AI** via any OpenAI-compatible API (ChatBot-style - I've been studying!)
*   🎞️ **Animated character** (with idle and thinking states - gotta look busy!)
*   💬 **Custom speech bubble UI** with tail (Just like you remember, but fancier!)
*   ⌨️ **Click-to-chat input box** (Tap me, let's talk!)
*   🖱️ **Draggable, floating character window** (Put me wherever you need assistance... or just company!)
*   🪟 **System tray integration** (Show / Hide / Quit - I promise I'll go away if you ask nicely!)
*   💚 **Positive personality** via a custom system prompt - Feel free to tweak my attitude!

---

## 🛠️ Requirements - What You'll Need

To bring **Clippy 2.Oh** to life, make sure you have:

1.  **Python 3.7+**
2.  **Required Libraries:** Install 'em easily!
    ```bash
    pip install -r requirements.txt
    # (Or manually: pip install PySide6 openai python-dotenv)
    ```

---

## ⚙️ Setup & Configuration - Let's Get Me Running!

Ready for your very own **Clippy 2.Oh**? Follow these steps:

1.  **Clone the Repository:**
    ```bash
    # Make sure you grab the right code!
    # TODO: Replace with your actual repository URL if different
    git clone https://github.com/bm-github/clippy2-oh.git
    cd clippy2-oh
    ```
2.  **Install Dependencies:** (If you skipped the step above)
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure AI Access (Super Important! ✨):**
    *   You need access to an OpenAI-compatible API endpoint. This could be the official OpenAI API, OpenRouter.ai, or a local server running a model.
    *   Create a file named `.env` right here in the main project folder. (You can copy `env.example` to `.env` and then edit it).
    *   Add the following variables, configuring them for your chosen API:
        ```dotenv
        # .env file contents
        # --- REQUIRED ---
        OPENAI_API_KEY="YOUR_API_KEY_HERE"    # Your API key (or placeholder like "NA" if your local service doesn't require one but the script expects a value)
        OPENAI_API_BASE="YOUR_API_BASE_URL"   # The base URL for the API.
                                              # Examples:
                                              # "https://api.openai.com/v1" (for official OpenAI)
                                              # "https://openrouter.ai/api/v1" (for OpenRouter)
                                              # "http://localhost:1234/v1" (for LM Studio - check your port)
                                              # "http://localhost:11434/v1" (for Ollama, if using an OpenAI-compatible proxy/endpoint - check your setup)
        OPENAI_MODEL="YOUR_MODEL_NAME_HERE"   # The specific model name you want to use
                                              # Examples:
                                              # "gpt-3.5-turbo", "gpt-4" (for OpenAI)
                                              # "mistralai/mistral-7b-instruct", "google/gemini-pro" (for OpenRouter)
                                              # "local-model" (often used for LM Studio, refers to the loaded model)
        ```
    *   **`OPENAI_API_KEY`**, **`OPENAI_API_BASE`**, and **`OPENAI_MODEL`** are **REQUIRED**. If any of these are not set, API calls will fail, and I'll let you know in a bubble!

4.  **Character Assets:** 🖼️
    *   Make sure you have these files in the same folder (or change the hardcoded paths in `clippy2-oh.py`):
        *   `character_idle.png` (or `character_idle.gif`)
        *   `character_busy.png` (or `character_busy.gif`)
        *   `tray_icon.png` (a little 32x32 guy for the system tray)
---

## 🚀 Usage - How to Chat With Clippy 2.Oh!

It's super easy:

1.  **Run the Script (Windowless Mode!):**
    ```bash
    # On Windows/Mac, 'pythonw clippy2-oh.py' often prevents an extra console window!
    pythonw clippy2-oh.py
    # If 'pythonw' isn't found or you want the console, just use 'python':
    # python clippy2-oh.py
    ```
2.  **Say Hello!** I should pop up on your screen (probably bottom-right, classic spot!). If you missed API config, I'll probably show a warning bubble.
3.  **Click Me!** The input box appears below me. Let's chat!
4.  **Ask Away!** Type your question or prompt, press `Enter` or click `Send`.
5.  **Thinking...** I'll change my look (`busy`) and show a "Thinking..." bubble while I consult the AI (my new brain!). 🤔
6.  **Voilà!** My (or the AI's) response appears in the speech bubble! Hopefully helpful!
7.  **Move Me Around!** Click and drag me anywhere you like. I'm flexible!
8.  **Use the Tray!** Remember the system tray icon 📎 for hiding, showing, or quitting. Easy peasy.

---

## 💡 Customisation & Notes - Make Clippy 2.Oh Your Own!

Want to tinker with **Clippy 2.Oh**? Go for it!

*   **Appearance:** Swap out `character_idle.png`/`.gif`, `character_busy.png`/`.gif`, and `tray_icon.png` with your own images! (Check `CHARACTER_WIDTH`/`HEIGHT` in the script for size hints). Maybe give me a party hat?
*   **Personality:** Edit the `SYSTEM_PROMPT` variable near the top of `clippy2-oh.py`. This is where you tell the AI how to act! Make me sassy, serious, or super-duper helpful! ✨
*   **AI Brain:** Change `OPENAI_MODEL` and `OPENAI_API_BASE` (and `OPENAI_API_KEY` if needed) in your `.env` file to try different AI models or providers. Experiment with my intelligence!
*   **Sizes & Colors:** Adjust constants like `BUBBLE_WIDTH`, `BUBBLE_FILL_COLOR`, etc., at the beginning of `clippy2-oh.py`. Match your desktop theme!
*   **History Limit:** Just FYI, I only remember the last `MAX_HISTORY_MESSAGES` (default: 10) messages between us. My memory isn't *infinite*... yet!
*   **Look & Feel:** All the windows are frameless and transparent for that sleek, modern overlay vibe. **2.Oh** style!

---

## Contributing - Want to Help Make Clippy 2.Oh Even Better?

It looks like you're trying to improve the code! That's the **2.Oh** spirit! Feel free to fork this repository, make your awesome changes, and submit a pull request. I'd love to see what brilliant ideas you have! ✨

---

📎 Happy chatting! Let me know if **Clippy 2.Oh** can assist you!

---
*\* Results may vary. Annoyance levels not guaranteed to be lower than original Microsoft Clippy, but hey, I'm trying! Use with caution and a sense of humor.*