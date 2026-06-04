"""Notification manager: clickable popup + tray balloon + VSCode flash.

Priority: clickable popup (tkinter) > tray balloon > Windows Toast.
Popup: clicking it activates VSCode. Auto-dismisses after ~8 seconds.
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
    logger.info("Tray icon registered")


# Messages by reason
_REASON_MESSAGES = {
    "elicitation": ("Claude Code", "Needs your choice — click to open VSCode"),
    "permission": ("Claude Code", "Needs your permission — click to open VSCode"),
    "stop_hook": ("Claude Code", "Task completed — click to open VSCode"),
    "": ("Claude Code", "Needs your attention — click to open VSCode"),
}


def notify_user(
    title: str = "Claude Code",
    message: str = "Needs your attention",
    keywords: Optional[list[str]] = None,
    reason: str = "",
) -> bool:
    """Send notification: popup (primary) + VSCode flash.

    If popup fails, falls back to tray balloon, then Windows Toast.

    Returns True if at least one notification channel succeeded.
    """
    if keywords is None:
        keywords = ["Visual Studio Code", ".vscode"]

    if reason and reason in _REASON_MESSAGES:
        title, message = _REASON_MESSAGES[reason]

    # 1. Clickable popup (primary — supports click-to-VSCode)
    popup_ok = _send_popup(title, message, keywords)

    # 2. VSCode window flash (immediate attention)
    window_ok = activate_window(keywords)
    if window_ok:
        logger.info("VSCode window flashed")
    else:
        logger.debug("VSCode window not found")

    # 3. Fallback: tray balloon (if popup failed)
    if not popup_ok:
        _send_tray_balloon(title, message)

    return popup_ok or window_ok


def _send_popup(
    title: str, message: str, keywords: list[str]
) -> bool:
    """Show clickable tkinter popup. Returns True on success."""
    try:
        from src.popup_notifier import show_popup_threadsafe

        return show_popup_threadsafe(
            title=title,
            message=message,
            keywords=keywords,
            timeout_ms=8000,
        )
    except Exception:
        logger.debug("Popup not available, trying fallback")
        return False


def _send_tray_balloon(title: str, message: str) -> bool:
    """Send a balloon notification from the system tray icon."""
    with _tray_lock:
        icon = _tray_icon

    if icon is None:
        logger.debug("Tray icon not available")
        return False

    try:
        icon.notify(message, title)
        logger.info("Tray balloon sent: %s", title)
        return True
    except Exception:
        logger.exception("Tray balloon failed")
        return False
