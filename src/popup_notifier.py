"""Popup notifier: a small always-on-top tkinter window that activates VSCode on click.

More reliable than Windows Toast — no COM registration needed.
Auto-closes after a timeout.
"""
import logging
import threading
import tkinter as tk
from typing import Optional

from src.window_activator import activate_window

logger = logging.getLogger(__name__)

# Colors
BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
ACCENT_COLOR = "#4285f4"
DIM_COLOR = "#888888"


def show_popup(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    timeout_ms: int = 8000,
) -> bool:
    """Show a clickable popup window.

    Clicking the popup activates VSCode and closes the popup.
    The popup auto-closes after `timeout_ms` milliseconds.

    Must be called from the main thread (uses tkinter).
    Returns True if the popup was shown.
    """
    if keywords is None:
        keywords = ["Visual Studio Code", ".vscode"]

    try:
        _create_and_run_popup(title, message, keywords, timeout_ms)
        return True
    except Exception:
        logger.exception("Failed to show popup")
        return False


def _create_and_run_popup(
    title: str,
    message: str,
    keywords: list[str],
    timeout_ms: int,
) -> None:
    """Create and run the tkinter popup (blocks until dismissed)."""
    root = tk.Tk()
    root.title("")
    root.configure(bg=BG_COLOR)

    # Window styling: frameless, always on top
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    # Dimensions
    width = 320
    height = 100

    # Position: bottom-right corner of screen
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    margin = 20
    x = screen_w - width - margin
    y = screen_h - height - margin - 40  # 40px above taskbar
    root.geometry(f"{width}x{height}+{x}+{y}")

    # Rounded-rectangle border via a canvas
    canvas = tk.Canvas(
        root,
        width=width,
        height=height,
        bg=BG_COLOR,
        highlightthickness=0,
    )
    canvas.pack(fill="both", expand=True)

    # Draw a subtle border
    radius = 8
    canvas.create_rectangle(
        2, 2, width - 2, height - 2,
        fill=BG_COLOR,
        outline=ACCENT_COLOR,
        width=2,
    )

    # Title text
    canvas.create_text(
        width // 2, 22,
        text=title,
        fill=ACCENT_COLOR,
        font=("Segoe UI", 11, "bold"),
    )

    # Message text
    canvas.create_text(
        width // 2, 52,
        text=message,
        fill=FG_COLOR,
        font=("Segoe UI", 10),
    )

    # Hint text
    canvas.create_text(
        width // 2, 78,
        text="Click to open VSCode  •  auto-dismiss",
        fill=DIM_COLOR,
        font=("Segoe UI", 8),
    )

    dismissed = threading.Event()
    keywords_copy = list(keywords)

    def on_click(event: tk.Event) -> None:
        """Handle click: activate VSCode and close."""
        if dismissed.is_set():
            return
        dismissed.set()
        logger.info("Popup clicked — activating VSCode")
        activate_window(keywords_copy)
        root.destroy()

    def on_timeout() -> None:
        """Auto-dismiss after timeout."""
        if not dismissed.is_set():
            dismissed.set()
            logger.debug("Popup auto-dismissed")
            root.destroy()

    # Bind click to the entire window
    canvas.bind("<Button-1>", on_click)
    root.bind("<Button-1>", on_click)

    # Auto-dismiss timer
    root.after(timeout_ms, on_timeout)

    # Show and block until dismissed
    root.mainloop()


def show_popup_threadsafe(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    timeout_ms: int = 8000,
) -> bool:
    """Show popup from any thread. Returns after the popup closes."""
    result_holder: list[bool] = []

    def _run() -> None:
        result_holder.append(
            show_popup(title, message, keywords, timeout_ms)
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_ms / 1000 + 2)

    return result_holder[0] if result_holder else False
