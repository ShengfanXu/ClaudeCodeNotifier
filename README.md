# Claude Code Desktop Notifier

当 Claude Code 需要你输入时（权限确认、选项选择等），通过 Windows Toast 通知 + 任务栏闪烁提醒你。适合离开电脑时使用。

## 安装

```bat
setup_conda.bat
```

这会创建 `claude-notifier` conda 环境并安装所有依赖。

## 启动

```bat
run.bat
```

应用启动后在系统托盘显示蓝色圆形图标，HTTP 服务监听在 `http://127.0.0.1:19800`。

## 配置 Claude Code Hook

在 Claude Code 的 `settings.json` 中添加：

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

**注意**：`matcher` 为空表示匹配所有 stop 事件。如果只想在特定场景触发，可设置更精确的 matcher。

## 自定义配置

编辑项目根目录下的 `config.json`：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `port` | HTTP 服务端口，端口被占时自动递增 | `19800` |
| `vscode_window_title_keywords` | 用于识别 VSCode 窗口的标题关键词 | `["Visual Studio Code", ".vscode"]` |
| `toast_duration` | Toast 通知持续时间：`"short"` 或 `"long"` | `"short"` |

## 工作流程

1. Claude Code 触发 Stop hook
2. Hook 发送 HTTP POST 到本程序的 `/notify` 接口
3. 程序弹出 Windows Toast 通知 + 闪烁 VSCode 任务栏按钮
4. 你看到通知，回到 VSCode 操作 Claude Code

## 退出

右键点击系统托盘图标 → Quit。
