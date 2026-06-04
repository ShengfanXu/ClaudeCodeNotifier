"""Window activator: find and bring VSCode window to the foreground.

Uses PowerShell to enumerate windows and pywin32 to flash/activate them.
"""
import subprocess
import logging
from typing import Optional

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
    public static extern bool IsIconic(IntPtr hWnd);
}
"@
$processes = Get-Process | Where-Object { $_.MainWindowTitle -ne '' }
foreach ($p in $processes) {
    $h = $p.MainWindowHandle
    if ($h -ne [IntPtr]::Zero -and [WinAPI]::IsWindowVisible($h)) {
        Write-Output "$($p.MainWindowTitle)|$($p.Id)"
    }
}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        windows: list[dict[str, str]] = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                parts = line.rsplit("|", 1)
                if len(parts) == 2:
                    windows.append({"title": parts[0], "pid": parts[1]})
        return windows
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("Failed to enumerate windows: %s", e)
        return []


def activate_window(keywords: list[str]) -> bool:
    """Find and activate (bring to foreground) a VSCode-compatible window.

    Searches visible windows for titles matching any of the keywords.
    Uses PowerShell to flash the window and bring it to the foreground.

    Returns True if a matching window was found and activation was attempted.
    """
    all_windows = _enum_windows_via_powershell()
    titles = [w["title"] for w in all_windows if w["title"]]
    matched_title = find_window_by_title_keywords(titles, keywords)

    if matched_title is None:
        logger.debug("No VSCode window found among %d windows", len(titles))
        return False

    logger.info("Found VSCode window: %s", matched_title)

    # Escape single quotes in the title for PowerShell
    escaped_title = matched_title.replace("'", "''")

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
    [DllImport("user32.dll")]
    public static extern bool FlashWindowEx(ref FLASHWINFO pfwi);
    [StructLayout(LayoutKind.Sequential)]
    public struct FLASHWINFO {{
        public uint cbSize;
        public IntPtr hwnd;
        public uint dwFlags;
        public uint uCount;
        public uint dwTimeout;
    }}
}}
"@
$title = '{escaped_title}'
$h = [WinAPI]::FindWindow($null, $title)
if ($h -ne [IntPtr]::Zero) {{
    # Restore if minimized
    if ([WinAPI]::IsIconic($h)) {{
        [WinAPI]::ShowWindow($h, 9)  # SW_RESTORE
    }}
    # Flash taskbar button to attract attention
    $flash = New-Object WinAPI+FLASHWINFO
    $flash.cbSize = [System.Runtime.InteropServices.Marshal]::SizeOf($flash)
    $flash.hwnd = $h
    $flash.dwFlags = 0x00000003  # FLASHW_TRAY | FLASHW_CAPTION
    $flash.uCount = 3
    $flash.dwTimeout = 0
    [WinAPI]::FlashWindowEx([ref]$flash)
    # Try to bring to foreground
    [WinAPI]::SetForegroundWindow($h)
}}
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", activate_script],
            capture_output=True,
            timeout=5,
        )
        return True
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("Failed to activate window: %s", e)
        return False
