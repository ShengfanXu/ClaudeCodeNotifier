"""Notification manager: spawn Windows Toast notifications via winotify.

When a notification is triggered, it simultaneously:
1. Sends a Windows Toast notification as a visual reminder
2. Immediately flashes the VSCode taskbar button to attract attention
"""
import logging
import threading
from typing import Optional

from winotify import Notification

from src.window_activator import activate_window

logger = logging.getLogger(__name__)

APP_ID = "ClaudeCodeNotifier"


def notify_user(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    duration: str = "short",
) -> bool:
    """Send a Windows Toast and flash the VSCode taskbar button.

    Call this from any thread — it's thread-safe.

    Returns True if at least one action (toast or window activation) succeeded.
    """
    if keywords is None:
        keywords = ["Visual Studio Code", ".vscode"]

    toast_ok = _send_toast(title, message, duration)
    window_ok = activate_window(keywords)

    if window_ok:
        logger.info("VSCode window flashed — user should see it")
    else:
        logger.debug("VSCode window not found — toast notification is the fallback")

    return toast_ok or window_ok


def _send_toast(title: str, message: str, duration: str) -> bool:
    """Send a Windows Toast notification. Returns True on success."""
    try:
        toast = Notification(
            app_id=APP_ID,
            title=title,
            msg=message,
            duration=duration,
        )
        toast.show()
        logger.info("Toast notification sent: %s", title)
        return True
    except Exception:
        logger.exception("Failed to send toast notification")
        return False


def notify_user_threadsafe(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    duration: str = "short",
) -> bool:
    """Send a notification from any thread.

    winotify uses COM which may need STA threading. This wrapper
    spawns a short-lived thread to avoid blocking the caller.
    """
    result_holder: list[bool] = []

    def _do_notify() -> None:
        result_holder.append(notify_user(title, message, keywords, duration))

    thread = threading.Thread(target=_do_notify, daemon=True)
    thread.start()
    thread.join(timeout=5)

    return result_holder[0] if result_holder else False
