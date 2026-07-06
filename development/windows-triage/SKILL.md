---
name: windows-triage
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

| 错误码 | 已知根因 | 修复 |
|--------|---------|------|
| `WinError 448` | Windows 25H2 将 HF Hub symlink 视为「不受信任的装入点」，`scan_cache_dir()` 失败 | `HF_HUB_DISABLE_SYMLINKS=1` |
| `OSError 1455` | 4.3GB+ safetensors mmap 失败，Windows 虚拟地址空间碎片化 | 自定义 heap-reader（替换 `load_file()`） |
| `0xc0000142` (where.exe) | 第三方进程在关机时调用 where.exe，DLL 已部分卸载 | msconfig 二分法定位（先禁 NVIDIA Container、Xbox Game Bar） |
| `net::ERR_CONNECTION_CLOSED` (Electron) | Karing 路由未覆盖 Azure CDN 域名 | 加 `domain_suffix` 到 Karing 路由组 |
| `FileNotFoundError: [WinError 2]` | subprocess 找不到 chmod/npm 等，PATH 不含 git-bash 工具 | 用绝对路径或通过 git-bash 运行 |
| `Can't open file 'C:\\c\\...'` | MSYS 路径转换：`/c/` → `C:/` 被 git-bash 展开后多加了一层 | 用 `C:/` 绝对路径，避开 MSYS 自动转换 |
| Chrome 扩展 `ERR_BLOCKED_BY_CLIENT` | chrome-extension:// URL 被沙箱限制 | 分析 GitHub 源码，不用浏览器自动化 |
| `Playwright 安装失败` | Playwright 下载浏览器时 Proxy 问题 | 已弃用 Playwright，用 obu 替代 |
| `Argument list too long` | Windows 命令行长度限制 ~8K | 用文件传参替代 `--content` |
| `403 Forbidden (urllib)` vs `curl 正常` | Python urllib HTTP 实现差异 | ConfigMap PUT 用 curl 不用 Python |

## ② 诊断决策树

### 第 1 步：错误归属

```bash
# 报错码归类
# 4xx → 网络/代理问题 → 用 karing-routing skill
# 0xc0000xxx → 系统级别 → 走本 skill 第 2 步
# WinError NNN → Windows API 调用 → 走本 skill 速查表
# Python OSError/FileNotFound → 环境路径问题 → 走第 3 步
# npm/npx 报错 → Node.js 工具链 → 走第 4 步
```

### 第 2 步：系统级故障

```bash
# 二进制完整性
chkdsk C: /scan
sfc /scannow
DISM /Online /Cleanup-Image /CheckHealth

# 检查是否为 Insider 已知问题
# → 搜索 Microsoft Feedback Hub / Windows Insider 论坛
# → 检查 build 版本: winver
```

### 第 3 步：环境变量污染

```bash
# 检查 PATH（常见问题：多个 Python、npm prefix 冲突）
echo $PATH | tr ':' '\n' | grep -i python
echo $PATH | tr ':' '\n' | grep -i npm

# 检查 PYTHONPATH（Hermes venv 残留）
echo $PYTHONPATH

# 检查 MSYS 路径转换问题
# 症状：C:\ 变成了 C:\c\ 或丢失驱动器字母
# 修复：用 C:/ 绝对路径，不用 /c/ 或 ~/
```

### 第 4 步：Python 库兼容性

```bash
# cuDNN 版本冲突
python -c "import torch; print(torch.__version__); print(torch.version.cuda)"

# Windows 25H2 + PyTorch 2.8+ 已知问题
# cuDNN 9 vs cuDNN 8（CTranslate2 需要 cuDNN 8）
# 修复：用 pytorch-whisper 替代 faster-whisper，或手动装 cuDNN 8
```

### 第 5 步：第三方进程干扰

```bash
# 已知干扰进程
# - NVIDIA Container（频繁唤醒、占用 where.exe）
# - Xbox Game Bar（关机时崩溃）
# - Karing TUN 驱动（与某些 VPN 冲突）
# 
# 隔离方法：msconfig → 选择性启动 → 二分法禁用服务
```

## ③ 修复模板

### 环境变量设置

```bash
# 持久化环境变量
# 方案 A：添加到 ~/.bashrc
echo 'export HF_HUB_DISABLE_SYMLINKS=1' >> ~/.bashrc

# 方案 B：写 .env 文件（OmniVoice 用）
echo 'HF_HUB_DISABLE_SYMLINKS=1' >> ~/.config/omnivoice/env

# 方案 C：Windows 系统环境变量（持久化）
# setx HF_HUB_DISABLE_SYMLINKS 1
```

### 进程重启

```bash
# 查找并重启进程
tasklist | grep -i "<process_name>"
taskkill /F /IM "<process_name>.exe"
# 等待服务自动重启或手动启动
```

### 路径修复

```bash
# Python subprocess 路径问题
# ❌ 错误：subprocess.run("npm install", shell=True)  # cmd.exe 不认
# ✅ 正确：subprocess.run("npm install", shell=True, executable="C:/Program Files/Git/bin/bash.exe")

# 或者用完整路径
npm_path = subprocess.run(["where", "npm"], capture_output=True, text=True).stdout.strip()
subprocess.run([npm_path, "install"])
```

## 已知 Windows 25H2 Insider 回归清单

| 特性 | 表现 | 状态 |
|------|------|------|
| HF Hub symlink | `scan_cache_dir()` 抛出 WinError 448 | ⚠️ 需 `HF_HUB_DISABLE_SYMLINKS=1` |
| where.exe 关机崩溃 | 0xc0000142 事件日志 | ⚠️ 需分析第三方进程 |
| PyTorch cuDNN | cuDNN 9 不兼容 CTranslate2 cuDNN 8 | ⚠️ 需降级或换后端 |
| git-bash PATH 解析 | `$HOME` 畸变为 `C:\c\Users\...` | ✅ 已知，用绝对路径规避 |
| MSYS2 正斜杠 | `subprocess` 不识别 `D:/` | ✅ 已知，用 `D:\` 反斜杠 |

## 使用方式

```bash
# 查错误码
# → 搜索速查表

# 完整诊断
# → 跟我说「xxx 报错了，帮我排查」
# → 我走本 skill 的诊断树
```
