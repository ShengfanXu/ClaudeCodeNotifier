# tests/test_config_loader.py
import json
import tempfile
import os
from src.config_loader import load_config, DEFAULT_CONFIG


class TestLoadConfig:
    """Tests for config loading and validation."""

    def test_loads_valid_config(self):
        cfg = {
            "port": 19900,
            "vscode_window_title_keywords": ["Test"],
            "toast_duration": "long",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(cfg, f)
            path = f.name
        try:
            result = load_config(path)
            assert result["port"] == 12345
            assert result["vscode_window_title_keywords"] == DEFAULT_CONFIG[
                "vscode_window_title_keywords"
            ]
            assert result["toast_duration"] == DEFAULT_CONFIG["toast_duration"]
        finally:
            os.unlink(path)

    def test_invalid_json_returns_defaults(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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

        port = find_available_port(27345, max_attempts=3)
        assert isinstance(port, int)
        assert port == 27345 or port in range(27346, 27348)
