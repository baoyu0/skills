---
name: windows-triage
version: 1.0.0
description: "Windows 10 25H2 Insider 环境故障诊断框架 — 错误码映射 + 根因分析树 + 已知问题速查"
---

# Windows-Triage — 环境故障诊断框架

## 问题

你的 Windows 10 25H2 Insider Preview（build 26200.8737）环境有大量已知的兼容性问题和回归缺陷。每次报错都需要重新做完整的根因分析链——从错误码查到二进制完整性，再到第三方进程干扰，再到 Insider 已知问题。

本 skill 将这个过程结构化，让常见错误一次命中。

## 诊断流程

```
报错信息
   │
   ▼
① 错误码速查表 ──── 命中已知问题 → 直接修复
   │
   未命中
   ▼
② 诊断决策树
   ├── 检查二进制完整性（chkdsk / sfc / DISM）
   ├── 检查第三方进程干扰（msconfig 二分法）
   ├── 检查环境变量污染（PATH / PYTHONPATH）
   └── 检查 Python 库兼容性
   │
   仍未解决
   ▼
③ 隔离测试 → 确认根因 → 修复 → 记录
```

## ① 错误码速查表

| 错误码 | 已知根因 | 怎么验证 | 修复 |
|--------|---------|---------|------|
| `WinError 448` | Windows 25H2 将 HF Hub symlink 视为「不受信任的装入点」 | OmniVoice 日志第一行 `scan_cache_dir failed (448)` | `HF_HUB_DISABLE_SYMLINKS=1` |
| `OSError 1455` | 4.3GB+ safetensors mmap 失败，虚拟地址空间碎片化 | 加载 VoxCPM2 4.3GB 模型时崩溃 | 自定义 heap-reader（替换 `safetensors.torch.load_file()`） |
| `0xc0000142` (where.exe) | 第三方进程在关机时调用 where.exe，DLL 已部分卸载 | 事件查看器 → Windows 日志 → 应用程序，搜 `0xc0000142` | msconfig 二分法定位（先禁 NVIDIA Container、Xbox Game Bar） |
| `net::ERR_CONNECTION_CLOSED` | Karing 路由未覆盖 Azure CDN 域名 | Electron 更新时下载失败 | `karing-route add "🐱 GitHub" <域名>` |
| `FileNotFoundError: [WinError 2]` | subprocess 找不到 chmod/npm 等 | Python 脚本报找不到文件 | 用绝对路径或通过 git-bash 运行 |
| `Can't open file 'C:\\c\\...'` | MSYS 路径转换多加了一层 `c\` | 脚本报 `can't open file 'C:\\c\\Users\\...'` | 用 `C:/` 绝对路径，不用 `/c/` |
| `ERR_BLOCKED_BY_CLIENT` | chrome-extension:// URL 被沙箱限制 | obu 打开扩展链接失败 | 分析 GitHub 源码代替自动化 |
| `403 (urllib)` vs `curl OK` | Python urllib Halo PUT 差异 | 同一 PAT，`curl -X PUT` 成功但 `urlopen()` 403 | ConfigMap PUT 用 curl |
| `exit 124` timeout | 命令因等待交互而 hang（rebase 触发 vim） | | 设 `GIT_EDITOR=true` |

## ② 诊断决策树

### 第 1 步：错误归属

```bash
# 4xx → 网络/代理问题 → 用 karing-routing skill
# 0xc0000xxx → 系统级别 → 走本 skill 第 2 步
# WinError NNN → Windows API 调用 → 速查表
# Python OSError → 环境路径 → 走第 3 步
# npm/npx 报错 → Node.js → 走第 4 步
```

### 第 2 步：系统级故障

```bash
chkdsk C: /scan
sfc /scannow
DISM /Online /Cleanup-Image /CheckHealth
# 检查 build: winver
```

### 第 3 步：环境变量污染

```bash
# 用 python3 避免 MSYS tr 分隔问题
python3 -c "import os; [print(p) for p in os.environ['PATH'].split(';') if 'python' in p.lower()]"
python3 -c "import os; [print(p) for p in os.environ['PATH'].split(';') if 'npm' in p.lower()]"
echo $PYTHONPATH
```

### 第 4 步：Python 库兼容性

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda)"
# cuDNN 9 vs cuDNN 8（CTranslate2 需要 cuDNN 8）
```

### 第 5 步：第三方进程干扰

NVIDIA Container、Xbox Game Bar、Karing TUN → msconfig 二分法禁用。

## ③ 已知 Insider 回归清单

| 特性 | 表现 | 验证 | 状态 |
|------|------|------|------|
| HF Hub symlink | `scan_cache_dir` 448 | OmniVoice 启动日志 | ⚠️ 需 `HF_HUB_DISABLE_SYMLINKS=1` |
| where.exe 关机崩溃 | 0xc0000142 | 事件查看器 | ⚠️ 分析第三方进程 |
| PyTorch cuDNN | cuDNN 9 vs 8 冲突 | faster-whisper 加载失败 | ⚠️ 换 pytorch-whisper |
| git-bash PATH | `$HOME` 畸变 | `can't open file` | ✅ 用绝对路径 |
| MSYS 正斜杠 | subprocess 不认 `D:/` | 路径错误 | ✅ 用 `D:\` 反斜杠 |

## ④ 修复模板

```bash
# 环境变量
echo 'export HF_HUB_DISABLE_SYMLINKS=1' >> ~/.bashrc

# 进程重启
taskkill /F /IM "karingService.exe"

# subprocess 路径
# ❌ subprocess.run("npm install", shell=True)
# ✅ subprocess.run("npm install", shell=True, executable="C:/Program Files/Git/bin/bash.exe")
```
