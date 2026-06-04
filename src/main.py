"""Claude Code Desktop Notifier — main entry point.

Wires together the HTTP server, notification manager, systray, and
window activator. The systray runs on the main thread; the HTTP server
runs in a background asyncio event loop.
"""
import asyncio
import logging
import threading
import sys
import concurrent.futures
from typing import Optional

from aiohttp import web

from src.config_loader import load_config, find_available_port
from src.http_server import create_app, start_server, NotifyRequest
from src.notification_manager import notify_user as send_notification, set_tray_icon
from src.systray_manager import create_tray

logger = logging.getLogger(__name__)

# Thread pool for running blocking notification calls
_notify_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def main() -> None:
    """Run the desktop notifier application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting Claude Code Desktop Notifier...")

    # Load configuration
    cfg = load_config()

    # Find available port
    try:
        port = find_available_port(cfg["port"])
    except OSError as e:
        logger.fatal("No available port: %s", e)
        sys.exit(1)

    if port != cfg["port"]:
        logger.info(
            "Configured port %d occupied, using port %d", cfg["port"], port
        )

    keywords: list[str] = cfg["vscode_window_title_keywords"]
    duration: str = cfg["toast_duration"]

    # Shared shutdown signal
    shutdown_event = threading.Event()
    runner_ref: list[Optional[web.AppRunner]] = [None]

    # Define the notify handler for the HTTP server
    async def handle_notify(req: NotifyRequest) -> web.Response:
        # Run blocking notification call in thread pool to avoid
        # blocking the asyncio event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            _notify_executor,
            lambda: send_notification(
                title="Claude Code",
                message="Needs your input — return to VSCode",
                keywords=keywords,
                duration=duration,
            ),
        )
        return web.json_response({"status": "ok"})

    # Create the aiohttp app
    app = create_app(on_notify=handle_notify)

    # Run aiohttp in a background daemon thread
    def run_http_server() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            runner = loop.run_until_complete(
                start_server(app, "127.0.0.1", port)
            )
            runner_ref[0] = runner
            # Keep running until shutdown
            while not shutdown_event.is_set():
                try:
                    loop.run_until_complete(asyncio.sleep(0.5))
                except Exception:
                    break
        except Exception:
            logger.exception("HTTP server error")
        finally:
            logger.info("Shutting down HTTP server...")
            if runner_ref[0]:
                loop.run_until_complete(runner_ref[0].cleanup())
            loop.close()

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Callback for systray quit
    def on_quit() -> None:
        logger.info("Shutting down...")
        shutdown_event.set()
        _notify_executor.shutdown(wait=False)
        sys.exit(0)

    # Start systray on main thread (blocking)
    tray = create_tray(on_quit=on_quit)
    set_tray_icon(tray)

    logger.info(
        "Notifier ready on http://127.0.0.1:%d. Right-click tray icon to quit.",
        port,
    )
    tray.run()


if __name__ == "__main__":
    main()
