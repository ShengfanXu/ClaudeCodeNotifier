# Claude Code Desktop Notifier

当 Claude Code 需要你输入或完成任务时，通过**桌面弹窗** + **系统托盘气泡** + **VSCode 闪烁**提醒你。

## 功能

| 触发场景 | 弹窗内容 | 效果 |
|----------|----------|------|
| 弹出选项/确认框 | "Needs your choice" | 弹窗 + VSCode 闪烁 |
| 权限许可请求 | "Needs your permission" | 弹窗 + VSCode 闪烁 |
| 任务完成 | "Task completed" | 弹窗 + VSCode 闪烁 |

**弹窗是蓝色的浮动窗口**，出现在屏幕右下角：
- **点击弹窗** → 自动跳转到 VSCode
- 8 秒后自动消失

## 安装

```bat
setup_conda.bat
```

创建 `claude-notifier` conda 环境，安装所有依赖。

## 启动

```bat
run.bat
```

系统托盘出现蓝色圆形图标。托盘右键菜单可退出。

## Hook 配置（全局生效）

已在 `~/.claude/settings.json` 配置了三个 hook，对所有项目生效：

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "shell": "bash",
        "command": "curl -s -X POST http://localhost:19800/notify -H \"Content-Type: application/json\" -d \"{\\\"reason\\\":\\\"stop_hook\\\"}\""
      }]
    }],
    "Elicitation": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "shell": "bash",
        "command": "curl -s -X POST http://localhost:19800/notify -H \"Content-Type: application/json\" -d \"{\\\"reason\\\":\\\"elicitation\\\"}\""
      }]
    }],
    "PermissionRequest": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "shell": "bash",
        "command": "curl -s -X POST http://localhost:19800/notify -H \"Content-Type: application/json\" -d \"{\\\"reason\\\":\\\"permission\\\"}\""
      }]
    }]
  }
}
```

| Hook | 触发时机 |
|------|----------|
| `Stop` | Claude Code 完成当前轮次 |
| `Elicitation` | 弹出选择对话框 |
| `PermissionRequest` | 弹出权限确认 |

## 自定义配置

编辑 `config.json`：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `port` | HTTP 服务端口（被占时自动递增） | `19800` |
| `vscode_window_title_keywords` | VSCode 窗口标题关键词 | `["Visual Studio Code", ".vscode"]` |
| `toast_duration` | 保留字段 | `"short"` |

## 通知机制（优先级从高到低）

1. **可点击弹窗**（tkinter）— 点击跳转 VSCode，8 秒自动消失
2. **托盘气泡**（pystray）— 从系统托盘弹出
3. **VSCode 闪烁** — 任务栏按钮闪烁

## 已知问题

- tkinter 弹窗在部分远程桌面/虚拟机环境下可能不显示，自动降级到托盘气泡
- 修改 hook 配置后需重启 Claude Code 会话生效

## 退出

右键托盘图标 → Quit，或直接关闭终端窗口。
