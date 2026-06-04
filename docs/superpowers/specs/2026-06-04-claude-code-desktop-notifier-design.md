# Claude Code Desktop Notifier — Design Spec

**Date**: 2026-06-04
**Type**: New project
**Platform**: Windows 11

## Overview

A lightweight desktop notification applet that alerts the user when Claude Code (running in VSCode) is waiting for user input. The user can step away from the IDE and get notified via a Windows Toast notification when Claude Code needs their attention.

## Core Workflow

1. Claude Code encounters a situation requiring user input (permission prompt, AskUserQuestion, etc.)
2. Claude Code fires a **Stop hook** defined in its `settings.json`
3. The hook sends an HTTP POST request to the desktop notifier app
4. The notifier pops a **Windows Toast notification**
5. The user clicks the notification → VSCode window is brought to the foreground
6. The user responds to Claude Code

## Architecture

```
┌─────────────┐  HTTP POST   ┌──────────────────┐
│ Claude Code │ ───────────► │  桌面提醒小程序    │
│  (Hook)     │              │                  │
└─────────────┘              │  ┌────────────┐  │
                             │  │ HTTP Server │  │
                             │  │ (aiohttp)   │  │
                             │  └─────┬──────┘  │
                             │        │         │
                             │  ┌─────▼──────┐  │
                             │  │ Notifier   │  │
                             │  │ (WinRT)    │──│──► Windows Toast
                             │  └─────┬──────┘  │
                             │        │         │
                             │  ┌─────▼──────┐  │
                             │  │ Systray    │  │
                             │  │ (pystray)  │  │
                             │  └────────────┘  │
                             └──────────────────┘
```

## Components

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| HTTP Server | Receive POST requests from Claude Code Hook, parse trigger reason | `aiohttp` |
| Notification Manager | Invoke Windows Toast API, handle click events | `winsdk` (WinRT) |
| Systray Manager | System tray icon, right-click menu (quit, pause notifications) | `pystray` |
| Window Activator | Bring VSCode window to foreground on notification click | `pywin32` |

## Data Flow

```
Claude Code Stop Hook
    │
    ▼
POST http://localhost:19800/notify
Body: { "reason": "user_input_required" }
    │
    ▼
Notification Manager → Windows Toast pops
    │
    ▼ (user clicks notification)
Window Activator → Find VSCode window → SetForegroundWindow()
```

## Claude Code Configuration

In Claude Code's `settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "command": "curl -X POST http://localhost:19800/notify -H \"Content-Type: application/json\" -d \"{\\\"reason\\\":\\\"stop_hook\\\"}\""
      }
    ]
  }
}
```

## App Configuration

```json
// config.json (next to the main script)
{
  "port": 19800,
  "vscode_window_title_keywords": ["Visual Studio Code", ".vscode"],
  "toast_duration": "short"
}
```

| Field | Purpose |
|-------|---------|
| `port` | HTTP server port; auto-increments if occupied (19801, 19802, …) |
| `vscode_window_title_keywords` | Keywords to match VSCode window by title |
| `toast_duration` | `"short"` or `"long"` for Toast display duration |

## Error Handling

| Scenario | Handling |
|----------|----------|
| HTTP port occupied | Auto-try next port (19801, 19802...), log to console |
| HTTP request arrives while service down | Silent failure — curl times out, Claude Code continues normally |
| Toast API call fails | Degrade: write to temp file, tray icon changes color to indicate error |
| VSCode window not found on click | Notification still pops, click silently ignored, no error surfaced |
| Long idle (no requests) | Tray keeps running, no heartbeat — keep it simple |

## Notification Behavior

- **Single notification** per event, no repeat
- Click: activate VSCode window
- Dismiss/timeout: no further action

## Environment

- **Python**: Anaconda virtual environment (created during implementation)
- **Platform**: Windows 11, x64
- **Primary packages**: `aiohttp`, `winsdk`, `pystray`, `pywin32`, `pillow`

## Testing

| Type | Scope |
|------|-------|
| Manual (primary) | Launch app, simulate curl POST, verify Toast + click-to-focus |
| Unit tests | HTTP request parsing, config loading, window title matching logic |
| Skipped | WinRT Toast API calls, systray UI interaction — high cost, low value to test |

## Out of Scope

- Monitoring Claude Code status via process/window/log scanning
- Repeat/recurring notifications
- Preview of the Claude Code prompt content in the notification
- Remote/mobile notifications
- Multi-monitor-specific behavior
