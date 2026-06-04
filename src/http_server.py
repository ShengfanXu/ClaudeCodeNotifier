"""HTTP server: aiohttp-based server receiving Claude Code hook callbacks."""
import logging
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from aiohttp import web

logger = logging.getLogger(__name__)


@dataclass
class NotifyRequest:
    """Parsed notification request from Claude Code hook."""

    reason: str = ""
    message: str = ""


NotifyHandler = Callable[[NotifyRequest], Awaitable[web.Response]]


def create_app(on_notify: NotifyHandler) -> web.Application:
    """Create an aiohttp Application with /notify and /health routes."""

    async def handle_notify(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            logger.warning("Invalid JSON in POST /notify")
            return web.json_response(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )

        notify_req = NotifyRequest(
            reason=body.get("reason", ""),
            message=body.get("message", ""),
        )
        logger.info("Received notify request: reason=%s", notify_req.reason)
        return await on_notify(notify_req)

    async def handle_health(request: web.Request) -> web.Response:
        return web.json_response({"status": "running"})

    app = web.Application()
    app.router.add_post("/notify", handle_notify)
    app.router.add_get("/health", handle_health)

    return app


async def start_server(
    app: web.Application, host: str, port: int
) -> web.AppRunner:
    """Start the aiohttp server on the given host:port.

    Returns the AppRunner so it can be shut down later.
    """
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("HTTP server started on %s:%d", host, port)
    return runner
