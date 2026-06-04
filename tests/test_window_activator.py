# tests/test_window_activator.py
from src.window_activator import find_window_by_title_keywords


class TestFindWindowByTitleKeywords:
    """Tests for window title matching logic."""

    def test_matches_single_keyword(self):
        titles = ["Visual Studio Code", "Notepad", "cmd.exe"]
        result = find_window_by_title_keywords(titles, ["Visual Studio Code"])
        assert result == "Visual Studio Code"

    def test_matches_any_keyword(self):
        titles = ["cmd.exe", "test.vscode - Explorer"]
        result = find_window_by_title_keywords(
            titles, ["Visual Studio Code", ".vscode"]
        )
        assert result == "test.vscode - Explorer"

    def test_case_insensitive_match(self):
        titles = ["VISUAL STUDIO CODE"]
        result = find_window_by_title_keywords(titles, ["visual studio code"])
        assert result == "VISUAL STUDIO CODE"

    def test_returns_none_when_no_match(self):
        titles = ["Notepad", "Calculator"]
        result = find_window_by_title_keywords(
            titles, ["Visual Studio Code", ".vscode"]
        )
        assert result is None

    def test_empty_keywords_returns_none(self):
        titles = ["Visual Studio Code"]
        result = find_window_by_title_keywords(titles, [])
        assert result is None

    def test_empty_titles_returns_none(self):
        result = find_window_by_title_keywords([], ["Visual Studio Code"])
        assert result is None

    def test_partial_match_within_title(self):
        titles = ["main.go - Visual Studio Code - Insiders"]
        result = find_window_by_title_keywords(titles, ["Visual Studio Code"])
        assert result == "main.go - Visual Studio Code - Insiders"
