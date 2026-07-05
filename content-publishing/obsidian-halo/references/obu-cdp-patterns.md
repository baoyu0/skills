# obu (Open Browser Use) CDP 模式参考

> 用于访问 X/Twitter（需要登录态）的浏览器自动化工具。obu 连接到用户的真实 Chrome。

## 基本命令

```bash
obu open-tab --url "<URL>"     # 打开新标签页
obu tabs                        # 列出当前会话的标签页
obu navigate --tab-id <ID> --url "<URL>"  # 导航
obu cdp --tab-id <ID> --method <M> --params '<JSON>'  # 发 CDP 命令
obu run -c '<action plan>'      # 运行动作计划
obu claim-tab                   # 接管已有标签页
obu finalize-tabs '[]'          # 清理会话
```

## CDP 关键模式

### 构建 `--params` JSON（避免 bash 引号地狱）

```bash
# ❌ 不要手工写 JSON 字符串——引号嵌套必出错
# ✅ 用 python3 生成：
P=$(python3 -c "import json; print(json.dumps({'expression':'document.querySelectorAll(\"video\").length','returnByValue':True}))")
obu cdp --tab-id "$TAB" --method Runtime.evaluate --params "$P"
```

### 解析 CDP 输出（跨多行 JSON）

obu CDP 输出是**多行 JSON 对象**，不能逐行解析。需要大括号平衡累加：

```python
buf = ""
depth = 0
for ch in stdout:
    buf += ch
    if ch == "{": depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0 and buf.startswith("{"):
            d = json.loads(buf)
            # 处理 d —— 可能有 "id"（响应）或无 "id"（CDP 事件）
            buf = ""
```

**不要在管道中用 `tail -1`**——obu CDP 输出经过管道后会丢失。直接 Python `json.load(sys.stdin)` 或 `> 文件` 后读取。

### open-tab 响应格式（注意与 CDP 不同）

```json
{"navigate": {...}, "tab": {"active": true, "id": 12345, "title": "", "url": ""}}
```

**没有 `"id"` 字段**，与 `Runtime.evaluate` 等 CDP 命令不同。且为跨多行 JSON，不能逐行解析。

### Tab cleanup（**必须！必须在 `finally` 无条件执行**）

obu 打开的 Chrome 标签页不会自动关闭。必须显式清理，否则 Chrome 积累大量孤儿标签页。

⚠️ **关键规则**：`finalize-tabs` 不能加 `if tab_id:` 条件。即使脚本在 `open-tab` 返回 tab_id 之前就崩溃，Chrome 里仍然有一个已打开的标签页。`finalize-tabs` 会清理整个 `obu-cli` session 中的所有标签页。

**推荐做法：**
```python
try:
    # ... obu 操作 ...
    tab_id = ...
finally:
    # 无条件执行，不管 tab_id 是否获取成功
    subprocess.run(["C:/Program Files/Git/bin/bash.exe", "-c",
                    '"/d/npm-global/obu" finalize-tabs --keep "[]"'])
```

```bash

obu CDP 输出通过 `|` 管道传给 Python 时，git-bash / MSYS2 的管道实现有时会丢失数据或产生 UTF-8 解码错误。可靠做法是保存到文件再读取：

```python
import tempfile, os, subprocess, json, time

tmp = os.path.join(tempfile.gettempdir(), f"obu_cdp_{os.getpid()}_{time.time_ns()}.json")
cmd = f'"/d/npm-global/obu" cdp --tab-id {tab_id} --method Runtime.evaluate --params {shlex.quote(params)} > "{tmp}" 2>&1'
subprocess.run(["C:/Program Files/Git/bin/bash.exe", "-c", cmd], capture_output=True, timeout=30)
with open(tmp) as f:
    stdout = f.read()
os.remove(tmp)
```

注意：`/tmp/` 路径在 MSYS2 下会被重定向到实际 Windows temp 目录（如 `C:\Users\<user>\AppData\Local\Temp\`），但 Python 的 `tempfile.gettempdir()` 返回 Windows 原生路径，安全可靠。

不要在 obu CDP 的管道中用 `tail -1`——obu 的 stdout 在管道中直接断流。

### Python 子进程调用

`obu` 是 `#!/bin/sh` 脚本，不是 Win32 可执行文件。Python `subprocess` 不能直接调：
```python
# ❌ 这样不行
subprocess.run(["obu", "tabs"])
# ✅ 通过 git-bash 调用
subprocess.run(["C:/Program Files/Git/bin/bash.exe", "-c", "obu tabs"])
# 或者直接用 terminal 工具（git-bash 环境）执行
```

注意 `shutil.which("obu")` 能找到 `obu.CMD`（Windows 的 .CMD 包装器），但这不代表 `subprocess.run(["obu"])` 能工作。

## 常用 CDP 方法

| 方法 | 用途 | 示例 |
|------|------|------|
| `Runtime.evaluate` | 执行 JS，返回值 | 查询 DOM、播放视频、获取性能数据 |
| `Input.dispatchMouseEvent` | 模拟鼠标点击 | 点播放按钮、交互式元素 |
| `Input.dispatchKeyEvent` | 模拟键盘 | Enter 确认焦点元素 |
| `DOM.getDocument` | 获取 DOM 树 | 遍历页面结构 |
| `DOM.querySelector` | 按选择器找元素 | 定位特定 DOM 节点 |
| `Network.enable` | 开启网络请求跟踪 | 拦截 CDN URL |
| `Fetch.enable` | 请求拦截 | 捕获 fetch/XHR 请求 |
| `Page.close` | 关闭标签页 | 清理 |

### Input.dispatchMouseEvent 模式

```bash
# 先获取元素中心坐标 (Runtime.evaluate 返回 "x,y")
RC=$(obu cdp --tab-id "$TAB" --method Runtime.evaluate \
  --params "$(python3 -c "import json; print(json.dumps({'expression':'...getBoundingClientRect()...','returnByValue':True}))")" ...)
X=$(echo "$RC" | cut -d, -f1)
Y=$(echo "$RC" | cut -d, -f2)

# 分多次点击（某些播放器需要双击）
for i in 1 2 3; do
  obu cdp --tab-id "$TAB" --method Input.dispatchMouseEvent \
    --params "$(python3 -c "import json; print(json.dumps({'type':'mousePressed','x':$X,'y':$Y,'button':'left','clickCount':1}))" 2>/dev/null)"
  sleep 0.1
  obu cdp --tab-id "$TAB" --method Input.dispatchMouseEvent \
    --params "$(python3 -c "import json; print(json.dumps({'type':'mouseReleased','x':$X,'y':$Y,'button':'left','clickCount':1}))" 2>/dev/null)"
  sleep 0.5
done
```

## 已知限制

1. **Session 跨进程**：obu 默认 session `obu-cli`。在多进程（多个 `bash -c`）间共享 tab：打开 tab 的进程和其他进程共用同一个 session ID 即可访问相同 tab。
2. **MSE 视频流**：X Article 的视频通过 MSE（MediaSource Extension）流式加载，`<source src="blob:...">`。真实 CDN URL 不会出现在 performance API 或 DOM 中。需通过 Network 域拦截请求，或覆盖 `window.fetch`。
3. **Autoplay 策略**：浏览器阻止自动播放有声视频。需 `v.muted=true` 才能调用 `v.play()`。或者模拟用户点击播放按钮 overlay。
4. **Click 不触发 React 事件**：CDP `Input.dispatchMouseEvent` 发送原生事件，但 React 可能绑定在更高层元素。查找 `aria-label="播放"` 的 `<button>` 直接点击更可靠。
