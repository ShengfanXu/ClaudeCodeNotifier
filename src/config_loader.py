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
