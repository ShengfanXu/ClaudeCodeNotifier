# Claude Code Desktop Notifier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop notification applet that alerts the user via Toast notification when Claude Code requires input, with system tray management and VSCode window activation.

**Architecture:** Four independent modules orchestrated by `main.py`. An aiohttp HTTP server runs in a daemon thread receiving hook callbacks; a notification manager spawns Windows Toasts via `winotify`; a systray manager handles tray icon/menu via `pystray`; a window activator focuses VSCode via `pywin32`. All communicate through the main orchestrator — no cross-module dependencies.

**Tech Stack:** Python 3.12 (Anaconda conda env), aiohttp, winotify, pystray, pywin32, Pillow

---

## File Structure

```
ClaudeFinishReminder/
├── config.json                        # App configuration (user-editable)
├── requirements.txt                   # pip dependencies
├── setup_conda.bat                    # One-click conda env creation
├── run.bat                            # One-click launch script
├── src/
│   ├── __init__.py                    # Empty package init
│   ├── main.py                        # Entry point, wires components, starts event loop
│   ├── config_loader.py              # Load + validate config.json, port auto-increment
│   ├── http_server.py                # aiohttp server receiving POST /notify
│   ├── notification_manager.py       # Windows Toast via winotify, click → activate VSCode
│   ├── window_activator.py           # Find + SetForegroundWindow VSCode via pywin32
│   └── systray_manager.py            # pystray icon, menu (quit, status), icon generation
└── tests/
    ├── __init__.py
    ├── test_config_loader.py
    ├── test_http_server.py
    └── test_window_activator.py
```

---

### Task 1: Create conda environment, project structure, and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `setup_conda.bat`
- Create: `run.bat`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `config.json`

- [ ] **Step 1: Create project directories**

```bash
mkdir -p src tests
```

- [ ] **Step 2: Write `requirements.txt`**

```txt
aiohttp==3.9.5
winotify==2.0.2
pystray==0.19.5
pywin32==306
Pillow==10.3.0
pytest==8.2.0
pytest-asyncio==0.23.7
```

- [ ] **Step 3: Write `setup_conda.bat`**

```bat
@echo off
echo Creating conda environment 'claude-notifier' with Python 3.12...
conda create -n claude-notifier python=3.12 -y
echo.
echo Installing pip dependencies...
conda run -n claude-notifier pip install -r requirements.txt
echo.
echo Setup complete. Use run.bat to start the app.
pause
```

- [ ] **Step 4: Write `run.bat`**

```bat
@echo off
cd /d "%~dp0"
conda run -n claude-notifier python -m src.main
pause
```

- [ ] **Step 5: Write initial `config.json`**

```json
{
    "port": 19800,
    "vscode_window_title_keywords": ["Visual Studio Code", ".vscode"],
    "toast_duration": "short"
}
```

- [ ] **Step 6: Write empty `__init__.py` files**

```bash
echo "" > src/__init__.py
echo "" > tests/__init__.py
```

- [ ] **Step 7: Run setup and verify**

```bash
cmd.exe /c setup_conda.bat
```

Expected: conda env created, all packages installed without errors.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt setup_conda.bat run.bat config.json src/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding, dependencies, and config"
```

---

### Task 2: Config loader — load and validate config.json with port auto-increment

**Files:**
- Create: `src/config_loader.py`
- Create: `tests/test_config_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config_loader.py
import json
import tempfile
import os
from src.config_loader import load_config, DEFAULT_CONFIG


class TestLoadConfig:
    """Tests for config loading and validation."""

    def test_loads_valid_config(self):
        cfg = {"port": 19900, "vscode_window_title_keywords": ["Test"], "toast_duration": "long"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            path = f.name
        try:
            result = load_config(path)
            assert result["port"] == 19900
            assert result["vscode_window_title_keywords"] == ["Test"]
            assert result["toast_duration"] == "long"
        finally:
            os.unlink(path)

    def test_missing_file_returns_defaults(self):
        result = load_config("nonexistent_file.json")
        assert result == DEFAULT_CONFIG

    def test_missing_fields_filled_with_defaults(self):
        cfg = {"port": 12345}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            path = f.name
        try:
            result = load_config(path)
            assert result["port"] == 12345
            assert result["vscode_window_title_keywords"] == DEFAULT_CONFIG["vscode_window_title_keywords"]
            assert result["toast_duration"] == DEFAULT_CONFIG["toast_duration"]
        finally:
            os.unlink(path)

    def test_invalid_json_returns_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            result = load_config(path)
            assert result == DEFAULT_CONFIG
        finally:
            os.unlink(path)


class TestFindAvailablePort:
    """Tests for port auto-increment logic."""

    def test_returns_configured_port(self):
        from src.config_loader import find_available_port
        # We can't easily test actual port binding, but test the function exists
        # and returns an integer
        port = find_available_port(27345, max_attempts=3)
        assert isinstance(port, int)
        # A high ephemeral port should almost always be free
        assert port == 27345 or port in range(27346, 27348)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n claude-notifier pytest tests/test_config_loader.py -v
```

Expected: FAIL — module `src.config_loader` not found.

- [ ] **Step 3: Write `src/config_loader.py`**

```python
"""Config loader: reads config.json, fills defaults, finds available port."""
import json
import socket
import os
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "port": 19800,
    "vscode_window_title_keywords": ["Visual Studio Code", ".vscode"],
    "toast_duration": "short",
}

CONFIG_FILE_NAME = "config.json"


def _resolve_config_path(filename: str | None = None) -> str:
    """Resolve config file path relative to this source file's directory."""
    if filename:
        return filename
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(src_dir)
    return os.path.join(project_dir, CONFIG_FILE_NAME)


def load_config(filename: str | None = None) -> dict[str, Any]:
    """Load configuration from JSON file, filling missing keys with defaults.

    Returns DEFAULT_CONFIG if the file is missing or unparseable.
    """
    path = _resolve_config_path(filename)
    cfg = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            cfg.update(file_cfg)
    except (json.JSONDecodeError, OSError):
        pass
    return cfg


def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """Find an available TCP port starting from `start_port`.

    Tries up to `max_attempts` successive ports.
    Returns the first available port, or raises OSError if none found.
    """
    port = start_port
    for offset in range(max_attempts):
        candidate = port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", candidate))
                return candidate
            except OSError:
                continue
    raise OSError(
        f"No available port in range {start_port}-{start_port + max_attempts - 1}"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n claude-notifier pytest tests/test_config_loader.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/config_loader.py tests/test_config_loader.py
git commit -m "feat: add config loader with defaults and port auto-increment"
```

---

### Task 3: Window activator — find and focus VSCode window via pywin32

**Files:**
- Create: `src/window_activator.py`
- Create: `tests/test_window_activator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_window_activator.py
from src.window_activator import find_window_by_title_keywords, activate_window


class TestFindWindowByTitleKeywords:
    """Tests for window title matching logic."""

    def test_matches_single_keyword(self):
        titles = ["Visual Studio Code", "Notepad", "cmd.exe"]
        result = find_window_by_title_keywords(titles, ["Visual Studio Code"])
        assert result == "Visual Studio Code"

    def test_matches_any_keyword(self):
        titles = ["cmd.exe", "test.vscode - Explorer"]
        result = find_window_by_title_keywords(titles, ["Visual Studio Code", ".vscode"])
        assert result == "test.vscode - Explorer"

    def test_case_insensitive_match(self):
        titles = ["VISUAL STUDIO CODE"]
        result = find_window_by_title_keywords(titles, ["visual studio code"])
        assert result == "VISUAL STUDIO CODE"

    def test_returns_none_when_no_match(self):
        titles = ["Notepad", "Calculator"]
        result = find_window_by_title_keywords(titles, ["Visual Studio Code", ".vscode"])
        assert result is None

    def test_empty_keywords_returns_none(self):
        titles = ["Visual Studio Code"]
        result = find_window_by_title_keywords(titles, [])
        assert result is None

    def test_empty_titles_returns_none(self):
        result = find_window_by_title_keywords([], ["Visual Studio Code"])
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n claude-notifier pytest tests/test_window_activator.py -v
```

Expected: FAIL — module `src.window_activator` not found.

- [ ] **Step 3: Write `src/window_activator.py`**

```python
"""Window activator: find and bring VSCode window to the foreground."""
import subprocess
from typing import Optional


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


def _enum_windows_via_powershell() -> list[dict[str, str]]:
    """Enumerate all visible main windows via PowerShell.

    Returns a list of dicts with 'title' and 'pid' keys.
    """
    ps_script = """
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    using System.Text;
    public class WinAPI {
        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
        [DllImport("user32.dll")]
        public static extern IntPtr GetWindow(IntPtr hWnd, uint uCmd);
        [DllImport("user32.dll")]
        public static extern bool IsIconic(IntPtr hWnd);
    }
"@
Add-Type -AssemblyName System.Windows.Forms
$windows = [System.Windows.Forms.Application]::OpenForms
[System.Diagnostics.Process]::GetProcesses() | ForEach-Object {
    $h = $_.MainWindowHandle
    if ($h -ne [IntPtr]::Zero -and [WinAPI]::IsWindowVisible($h)) {
        [PSCustomObject]@{ title = $_.MainWindowTitle; pid = $_.Id }
    }
}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        windows = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(None, 1)
            if len(parts) == 2 and parts[1].isdigit():
                windows.append({"title": parts[0], "pid": parts[1]})
        return windows
    except (subprocess.TimeoutExpired, OSError):
        return []


def activate_window(keywords: list[str]) -> bool:
    """Find and activate (bring to foreground) a VSCode window.

    Searches visible windows for titles matching any of the keywords.
    Uses PowerShell + Win32 SetForegroundWindow via a small C# snippet.

    Returns True if a matching window was found and activated.
    """
    all_windows = _enum_windows_via_powershell()
    titles = [w["title"] for w in all_windows if w["title"]]
    matched_title = find_window_by_title_keywords(titles, keywords)
    if matched_title is None:
        return False

    # Use PowerShell to find the window handle and bring it to foreground
    activate_script = f"""
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class WinAPI {{
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
        [DllImport("user32.dll")]
        public static extern bool IsIconic(IntPtr hWnd);
    }}
"@
    $title = "{matched_title}"
    $h = [WinAPI]::FindWindow($null, $title)
    if ($h -ne [IntPtr]::Zero) {{
        if ([WinAPI]::IsIconic($h)) {{
            [WinAPI]::ShowWindow($h, 9)
        }}
        [WinAPI]::SetForegroundWindow($h)
    }}
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", activate_script],
            capture_output=True,
            timeout=5,
        )
        return True
    except (subprocess.TimeoutExpired, OSError):
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n claude-notifier pytest tests/test_window_activator.py -v
```

Expected: all tests PASS (pure logic tests, no VSCode window required).

- [ ] **Step 5: Commit**

```bash
git add src/window_activator.py tests/test_window_activator.py
git commit -m "feat: add window activator for VSCode focus"
```

---

### Task 4: Notification manager — Windows Toast with click callback

**Files:**
- Create: `src/notification_manager.py`

- [ ] **Step 1: Write `src/notification_manager.py`**

```python
"""Notification manager: spawn Windows Toast notifications via winotify.

Toast click calls the window activator to bring VSCode to the foreground.
"""
import logging
import threading
from typing import Optional, Callable

from winotify import Notification

from src.window_activator import activate_window

logger = logging.getLogger(__name__)

APP_ID = "ClaudeCodeNotifier"


def send_toast(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    on_activate: Optional[Callable[[], None]] = None,
    duration: str = "short",
) -> bool:
    """Send a Windows Toast notification.

    When the user clicks the toast body, `on_activate` is called.
    By default, this activates the VSCode window.

    Returns True if the toast was sent successfully.
    """
    if keywords is None:
        keywords = ["Visual Studio Code", ".vscode"]

    def default_on_activate() -> None:
        logger.info("Toast clicked — activating VSCode window")
        success = activate_window(keywords)
        if success:
            logger.info("VSCode window activated")
        else:
            logger.warning("VSCode window not found")

    handler = on_activate or default_on_activate

    try:
        toast = Notification(
            app_id=APP_ID,
            title=title,
            msg=message,
            duration=duration,
        )
        toast.add_actions(
            label="Open VSCode",
            launch="activate",
        )
        toast.on_activated = lambda _: handler()
        toast.show()
        logger.info("Toast notification sent: %s", title)
        return True
    except Exception:
        logger.exception("Failed to send toast notification")
        return False


def send_toast_threadsafe(
    title: str = "Claude Code",
    message: str = "Needs your input",
    keywords: Optional[list[str]] = None,
    duration: str = "short",
) -> bool:
    """Send a toast from any thread.

    winotify uses COM which may require STA threading. This wrapper
    ensures the toast is created on a suitable thread.
    """
    result_holder: list[bool] = []

    def _do_send() -> None:
        result_holder.append(send_toast(title, message, keywords, duration=duration))

    thread = threading.Thread(target=_do_send, daemon=True)
    thread.start()
    thread.join(timeout=5)

    return result_holder[0] if result_holder else False
```

- [ ] **Step 2: Commit**

```bash
git add src/notification_manager.py
git commit -m "feat: add notification manager with Windows Toast"
```

---

### Task 5: HTTP server — aiohttp server receiving POST /notify

**Files:**
- Create: `src/http_server.py`
- Create: `tests/test_http_server.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_http_server.py
import pytest
from aiohttp import web
from src.http_server import create_app, NotifyRequest


class TestNotifyRequest:
    """Tests for request parsing."""

    def test_notify_request_from_dict(self):
        req = NotifyRequest(reason="stop_hook", message="Test message")
        assert req.reason == "stop_hook"
        assert req.message == "Test message"

    def test_notify_request_defaults(self):
        req = NotifyRequest()
        assert req.reason == ""
        assert req.message == ""


class TestCreateApp:
    """Tests for the aiohttp app and routes."""

    @pytest.mark.asyncio
    async def test_notify_endpoint_returns_200(self, aiohttp_client):
        received = []

        async def handler(req: NotifyRequest):
            received.append(req)
            return web.json_response({"status": "ok"})

        app = create_app(on_notify=handler)
        client = await aiohttp_client(app)

        resp = await client.post("/notify", json={"reason": "stop_hook"})
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        assert len(received) == 1
        assert received[0].reason == "stop_hook"

    @pytest.mark.asyncio
    async def test_notify_endpoint_invalid_json(self, aiohttp_client):
        app = create_app(on_notify=lambda req: web.json_response({"status": "ok"}))
        client = await aiohttp_client(app)

        resp = await client.post("/notify", data="not json")
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_health_endpoint(self, aiohttp_client):
        app = create_app(on_notify=lambda req: web.json_response({"status": "ok"}))
        client = await aiohttp_client(app)

        resp = await client.get("/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "running"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n claude-notifier pytest tests/test_http_server.py -v
```

Expected: FAIL — module `src.http_server` not found.

- [ ] **Step 3: Write `src/http_server.py`**

```python
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


async def start_server(app: web.Application, host: str, port: int) -> web.AppRunner:
    """Start the aiohttp server on the given host:port.

    Returns the AppRunner so it can be shut down later.
    """
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("HTTP server started on %s:%d", host, port)
    return runner
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n claude-notifier pytest tests/test_http_server.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/http_server.py tests/test_http_server.py
git commit -m "feat: add aiohttp server with /notify and /health endpoints"
```

---

### Task 6: Systray manager — system tray icon and menu

**Files:**
- Create: `src/systray_manager.py`

- [ ] **Step 1: Write `src/systray_manager.py`**

```python
"""System tray manager: icon, right-click menu, quit handler."""
import logging
import threading
from typing import Callable, Optional

from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)

# Icon dimensions for system tray
ICON_SIZE = 64
ICON_COLOR = (66, 133, 244)   # Blue
ICON_DIM_COLOR = (158, 158, 158)  # Gray for error/paused state


def _generate_icon(color: tuple[int, int, int] = ICON_COLOR) -> Image.Image:
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

    menu = pystray.Menu(
        pystray.MenuItem(
            "Claude Code Notifier",
            None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Quit",
            lambda: _quit_tray(tray_ref[0], on_quit),
        ),
    )

    tray_ref: list[Optional[pystray.Icon]] = [None]

    def _quit_tray(icon: Optional[pystray.Icon], quit_callback: Callable[[], None]) -> None:
        logger.info("Quit selected from tray menu")
        if icon:
            icon.stop()
        quit_callback()

    tray = pystray.Icon(
        name="claude_code_notifier",
        icon=icon_image,
        title="Claude Code Notifier",
        menu=menu,
    )

    tray_ref[0] = tray
    return tray
```

- [ ] **Step 2: Commit**

```bash
git add src/systray_manager.py
git commit -m "feat: add system tray manager with icon and menu"
```

---

### Task 7: Main entry point — wire all components together

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Write `src/main.py`**

```python
"""Claude Code Desktop Notifier — main entry point.

Wires together the HTTP server, notification manager, systray, and
window activator. The systray runs on the main thread; the HTTP server
runs in a background asyncio loop.
"""
import asyncio
import logging
import threading
import signal
import sys
from typing import Optional

from aiohttp import web

from src.config_loader import load_config, find_available_port
from src.http_server import create_app, start_server, NotifyRequest
from src.notification_manager import send_toast_threadsafe
from src.systray_manager import create_tray

logger = logging.getLogger(__name__)


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
        logger.info("Configured port %d occupied, using port %d", cfg["port"], port)

    keywords: list[str] = cfg["vscode_window_title_keywords"]
    duration: str = cfg["toast_duration"]

    # Shared state
    shutdown_event = threading.Event()
    runner_ref: list[Optional[web.AppRunner]] = [None]

    # Define the notify handler for the HTTP server
    async def handle_notify(req: NotifyRequest) -> web.Response:
        send_toast_threadsafe(
            title="Claude Code",
            message="Needs your input — return to VSCode",
            keywords=keywords,
            duration=duration,
        )
        return web.json_response({"status": "ok"})

    # Create the aiohttp app
    app = create_app(on_notify=handle_notify)

    # Run aiohttp in a background thread
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
            if runner_ref[0]:
                loop.run_until_complete(runner_ref[0].cleanup())
            loop.close()

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Callbacks for systray
    def on_quit() -> None:
        logger.info("Shutting down...")
        shutdown_event.set()
        sys.exit(0)

    # Start systray on main thread (blocking)
    tray = create_tray(on_quit=on_quit)

    logger.info("Notifier ready on port %d. Right-click tray icon to quit.", port)
    tray.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add main entry point wiring all components"
```

---

### Task 8: Verify manual end-to-end flow

- [ ] **Step 1: Launch the application**

```bash
conda run -n claude-notifier python -m src.main
```

Expected: console logs startup message, tray icon appears in system tray.

- [ ] **Step 2: Simulate a Claude Code hook call**

In a separate terminal:

```bash
curl -X POST http://localhost:19800/notify -H "Content-Type: application/json" -d "{\"reason\":\"stop_hook\"}"
```

Expected: Windows Toast notification appears with "Claude Code" title and "Needs your input" message.

- [ ] **Step 3: Click the toast notification**

Expected: VSCode window (if open) comes to the foreground.

- [ ] **Step 4: Verify health endpoint**

```bash
curl http://localhost:19800/health
```

Expected: `{"status": "running"}`

- [ ] **Step 5: Test tray quit**

Right-click tray icon → Quit.

Expected: application exits cleanly, tray icon disappears.

- [ ] **Step 6: Test port auto-increment**

First, note the port in config.json. Open a second instance:

```bash
conda run -n claude-notifier python -m src.main
```

Expected: second instance logs "Configured port 19800 occupied, using port 19801".

---

### Task 9: Claude Code Hook Configuration Instructions

**No code files — documentation only.**

- [ ] **Step 1: Document hook configuration**

The user adds this to their Claude Code `settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "command": "curl -s -X POST http://localhost:19800/notify -H \"Content-Type: application/json\" -d \"{\\\"reason\\\":\\\"stop_hook\\\"}\""
      }
    ]
  }
}
```

Note: Adjust the port if `config.json` uses a non-default port.

The `matcher: ""` means this hook fires for every stop event. To only fire for prompts (not final exits), the user can experiment with more specific matchers as needed.

- [ ] **Step 2: Commit**

```bash
git commit --allow-empty -m "docs: add Claude Code hook configuration guide"
```
