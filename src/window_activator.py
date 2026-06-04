"""Window activator: find and bring VSCode window to the foreground.

Uses pywin32 to enumerate windows and activate the target window.
"""
import logging
from typing import Optional

import win32gui
import win32con
import win32process
import win32api

logger = logging.getLogger(__name__)


def find_window_by_title_keywords(
    titles: list[str], keywords: list[str]
) -> Optional[str]:
    """Return the first title that contains any of the keywords (case-insensitive).

    Returns None if no title matches.
    """
    if not keywords or not titles:
        return None
    lower_keywords = [kw.lower() for kw in keywords]
    for title in titles:
        lower_title = title.lower()
        if any(kw in lower_title for kw in lower_keywords):
            return title
    return None


def _enum_visible_windows() -> list[dict[str, object]]:
    """Enumerate all visible top-level windows using pywin32.

    Returns a list of dicts with 'title' and 'hwnd' keys.
    """
    windows: list[dict[str, object]] = []

    def callback(hwnd: int, _extra: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title.strip():
            return True
        windows.append({"title": title, "hwnd": hwnd})
        return True

    win32gui.EnumWindows(callback, None)
    return windows


def activate_window(keywords: list[str]) -> bool:
    """Find a VSCode window and bring it to the foreground.

    Uses AttachThreadInput to work around Windows foreground restrictions.
    """
    all_windows = _enum_visible_windows()
    titles = [str(w["title"]) for w in all_windows]
    matched_title = find_window_by_title_keywords(titles, keywords)

    if matched_title is None:
        logger.debug("No VSCode window found among %d windows", len(titles))
        return False

    # Find the matching window handle
    target_hwnd = None
    for w in all_windows:
        if w["title"] == matched_title:
            target_hwnd = w["hwnd"]
            break

    if target_hwnd is None:
        return False

    hwnd = int(target_hwnd)
    logger.info("Found VSCode window: %s (hwnd=%s)", matched_title, hwnd)

    try:
        # Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Attach foreground privilege using common technique:
        # 1. Get current foreground window's thread
        # 2. Attach our input to it
        # 3. Set foreground window
        # 4. Detach
        current_foreground = win32gui.GetForegroundWindow()
        current_thread = win32process.GetWindowThreadProcessId(
            current_foreground
        )[0]
        our_thread = win32api.GetCurrentThreadId()

        if current_thread != our_thread:
            win32process.AttachThreadInput(our_thread, current_thread, True)

        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetFocus(hwnd)

        # Brief flash to attract attention
        win32gui.FlashWindow(hwnd, True)

        if current_thread != our_thread:
            win32process.AttachThreadInput(our_thread, current_thread, False)

        logger.info("VSCode window activated")
        return True

    except Exception as e:
        logger.warning("Failed to activate window: %s", e)
        return False
