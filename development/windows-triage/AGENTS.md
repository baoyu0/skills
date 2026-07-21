# AGENTS.md — Windows-Triage

Windows 10 25H2 Insider 环境故障诊断框架 — 错误码映射 + 根因分析树 + 已知问题速查。

## 诊断流程

```
报错信息 → ① 错误码速查表（命中→直接修复）→ ② 诊断决策树 → ③ 隔离测试 → 记录
```

---

## ① 错误码速查表

| 错误码 | 根因 | 快速修复 |
|--------|------|----------|
| `WinError 448` | 25H2 将 HF Hub symlink 视为不受信任装入点 | `HF_HUB_DISABLE_SYMLINKS=1` |
| `OSError 1455` | 4.3GB+ safetensors mmap 失败 | 自定义 heap-reader 替换 `safetensors.torch.load_file()` |
| `0xc0000142` (where.exe) | 关机时第三方进程调用 where.exe | msconfig 二分法禁用 |
| `net::ERR_CONNECTION_CLOSED` | Karing 未覆盖 Azure CDN | `karing-route add "🐱 GitHub" <域名>` |
| `FileNotFoundError` | subprocess 找不到 MSYS 工具 | 用绝对路径或 git-bash 运行 |
| `Can't open file 'C:\\c\\...'` | MSYS 路径转换多加一层 `c\` | 用 `C:/` 绝对路径 |
| `exit 124` timeout | 命令因等待交互而 hang | 设 `GIT_EDITOR=true` |

## ② 诊断决策树

### 错误归属

- `4xx` → 网络/代理 → 走 karing-routing skill
- `0xc0000xxx` → 系统级别 → 走下面第 2 步
- `WinError NNN` → Windows API → 查速查表
- `npm/npx` 报错 → Node.js 环境

### 系统级检查

```bash
chkdsk C: /scan && sfc /scannow && DISM /Online /Cleanup-Image /CheckHealth
```

### 环境变量污染

```bash
python3 -c "import os; [print(p) for p in os.environ['PATH'].split(';') if 'python' in p.lower()]"
```

### 第三方进程干扰

NVIDIA Container、Xbox Game Bar、Karing TUN → msconfig 二分法禁用。

## ③ 已知 Insider 回归

- HF Hub symlink 448 错误 ⚠️
- where.exe 关机崩溃 ⚠️
- PyTorch cuDNN 9 vs 8 冲突 ⚠️
- git-bash PATH 畸变 ✅ 用绝对路径
- MSYS 正斜杠 ✅ 用 `D:\`
