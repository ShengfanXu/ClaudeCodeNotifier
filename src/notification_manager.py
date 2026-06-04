"""Notification manager: sends desktop notifications and flashes VSCode.

Primary method: pystray balloon tip (reliable, no COM registration).
Fallback: winotify Windows Toast (if tray icon not available).
"""
import logging
import threading
from typing import Optional

from src.window_activator import activate_window

logger = logging.getLogger(__name__)

# Module-level reference to tray icon, set by main.py at startup
_tray_icon: Optional["pystray.Icon"] = None
_tray_lock = threading.Lock()


def set_tray_icon(icon: "pystray.Icon") -> None:
    """Register the tray icon for balloon notifications. Called from main.py."""
    global _tray_icon
    with _tray_lock:
        _tray_icon = icon
    logger.info("Tray icon registered for notifications")


def notify_user(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    duration: str = "short",
) -> bool:
    """Send a notification and flash VSCode.

    Uses tray balloon as the primary notification channel,
    with Windows Toast as fallback.

    Returns True if at least one action succeeded.
    """
    if keywords is None:
        keywords = ["Visual Studio Code", ".vscode"]

    balloon_ok = _send_tray_balloon(title, message)
    window_ok = activate_window(keywords)

    if window_ok:
        logger.info("VSCode window flashed — user should see it")
    else:
        logger.debug("VSCode window not found")

    return balloon_ok or window_ok


def _send_tray_balloon(title: str, message: str) -> bool:
    """Send a balloon notification from the system tray icon."""
    with _tray_lock:
        icon = _tray_icon

    if icon is None:
        logger.warning("Tray icon not available, falling back to Toast")
        return _send_toast_fallback(title, message)

    try:
        icon.notify(message, title)
        logger.info("Tray balloon sent: %s", title)
        return True
    except Exception:
        logger.exception("Tray balloon failed, falling back to Toast")
        return _send_toast_fallback(title, message)


def _send_toast_fallback(title: str, message: str) -> bool:
    """Fallback: use winotify Toast notification."""
    try:
        from winotify import Notification

        toast = Notification(
            app_id="ClaudeCodeNotifier",
            title=title,
            msg=message,
            duration="short",
        )
        toast.show()
        logger.info("Toast fallback sent: %s", title)
        return True
    except Exception:
        logger.exception("Toast fallback also failed")
        return False
