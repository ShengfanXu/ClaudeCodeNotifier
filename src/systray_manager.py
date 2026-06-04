"""System tray manager: icon, right-click menu, quit handler."""
import logging
from typing import Callable, Optional

from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)

# Icon dimensions for system tray
ICON_SIZE = 64
ICON_COLOR = (66, 133, 244)  # Blue
ICON_DIM_COLOR = (158, 158, 158)  # Gray for error/paused state


def _generate_icon(
    color: tuple[int, int, int] = ICON_COLOR,
) -> Image.Image:
    """Generate a simple circular icon for the system tray."""
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    padding = 4
    draw.ellipse(
        [padding, padding, ICON_SIZE - padding, ICON_SIZE - padding],
        fill=color,
    )
    return image


def create_tray(
    on_quit: Callable[[], None],
    icon_color: tuple[int, int, int] = ICON_COLOR,
) -> pystray.Icon:
    """Create a pystray Icon with right-click menu.

    Args:
        on_quit: Called when the user selects "Quit" from the menu.
        icon_color: RGB tuple for the tray icon color.

    Returns:
        A pystray.Icon instance (not yet running).
    """
    icon_image = _generate_icon(icon_color)

    # Use a mutable container so the inner function can reference the tray
    tray_ref: list[Optional[pystray.Icon]] = [None]

    def _quit_action() -> None:
        logger.info("Quit selected from tray menu")
        tray = tray_ref[0]
        if tray:
            tray.stop()
        on_quit()

    menu = pystray.Menu(
        pystray.MenuItem(
            "Claude Code Notifier",
            None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit_action),
    )

    tray = pystray.Icon(
        name="claude_code_notifier",
        icon=icon_image,
        title="Claude Code Notifier",
        menu=menu,
    )

    tray_ref[0] = tray
    return tray
