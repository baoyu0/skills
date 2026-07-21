---
name: karing-routing
version: 1.0.0
description: "Karing 代理路由规则管理 — 为特定域名添加直连/代理路由，修复站点访问问题。"
---

# Karing 路由规则管理 Skill

## 触发条件

用户说以下任一情况时触发：
- 「xxx 网站打不开/加载慢」（代理路由问题）
- 「xxx 域名不走代理/直连」
- 「Karing 路由配置需要改」
- 已知场景：Papr RSS 403、GitHub 下载失败、Play Store 连不上

## Karing 架构速览

```
karing.exe (GUI)           ← 用户操作界面，修改 UI 配置
karingService.exe (38164)  ← sing-box 核心，实际路由引擎
```

| 配置 | 端口 | 说明 |
|------|------|------|
| HTTP/SOCKS5 代理 | `127.0.0.1:3067` | Karing 代理端口 |
| 控制 API | `127.0.0.1:3057` | sing-box 管理 API |
| 系统代理 | `127.0.0.1:3067` | Windows 系统代理层 |

**核心原则：`service_core.json` 是唯一真实来源。** `karing_routing_group.json`的 UI 外改会被 GUI 覆盖。所有手动路由修改必须写 `service_core.json`。

## 配置目录

```
C:\Users\zhaid\AppData\Roaming\Karing\karing\
├── service_core.json        ← 修改这里（路由规则的真实来源）
├── karing_routing_group.json ← 不要手动改（GUI 会覆盖）
├── karing_setting.json       ← 常规设置
└── app.log / service_core.log  ← 日志
```

## 诊断步骤

### 1. 确认问题是否路由相关

```bash
# 验证目标 IP 路由
curl -s -o /dev/null -w "HTTP %{http_code}, time %{time_total}s\n" "https://<问题域名>"

# 对比走代理 vs 不走代理
curl -s -o /dev/null -w "with proxy: %{http_code}\n" -x http://127.0.0.1:3067 "https://<问题域名>"
curl -s -o /dev/null -w "direct: %{http_code}\n" --noproxy "*" "https://<问题域名>"
```

### 2. 确认域名属于哪个路由组

查看 `service_core.json` 的 `route.rules` 数组。规则**顺序敏感** — 第一条匹配的规则生效。需在 `🌏 国外穿墙`（rule 37，匹配 `geolocation-!cn`）之类的宽泛规则**之前**插入窄规则。

## 添加路由规则

### 标准操作：在现有路由组加 `domain_suffix`

```python
import json, subprocess

config_path = r"C:\Users\zhaid\AppData\Roaming\Karing\karing\service_core.json"

# 1. 读配置
with open(config_path, "r") as f:
    cfg = json.load(f)

# 2. 找目标路由组（按 name 匹配）
route_name = "🎯 国内直连[自定义]"  # 或 "🐱 GitHub[自定义]" 等
new_domains = ["example.com", "cdn.example.com"]

for rule in cfg["route"]["rules"]:
    if rule.get("name") == route_name:
        # 找到已有的 domain_suffix 子规则
        for sub in rule.get("rules", []):
            if "domain_suffix" in sub:
                existing = set(sub["domain_suffix"])
                added = [d for d in new_domains if d not in existing]
                if not added:
                    print("全部已存在，无需添加")
                    break
                sub["domain_suffix"].extend(added)
                break
        else:
            # 路由组没有 domain_suffix 子规则，加一个
            rule.setdefault("rules", []).insert(0, {"domain_suffix": new_domains})
        break

# 3. 写回
with open(config_path, "w") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

# 4. 重启 Karing 服务
subprocess.run(["taskkill", "/F", "/IM", "karingService.exe"], capture_output=True)
# 等待几秒让 Karing GUI 自动重启服务
print("✅ 已停止 karingService.exe，Karing GUI 会自动重启")
print(f"   添加的域名: {new_domains} → {route_name}")
```

### 对应路由组速查表

| 路由组名（完整） | 出站 | 场景 |
|---|---|---|
| `🎯 国内直连[自定义]` | `direct_out` | RSS、国内 CDN、国内 API |
| `🐱 GitHub[自定义]` | `urltest_out` | GitHub Release Assets |
| `🌏 Google Play[自定义]` | `tu5-racknerd-54166a` (VPS) | Play Store |
| `🌏 国外穿墙[自定义]` | `tu5-racknerd-54166a` (VPS) | 兜底规则（匹配所有非 cn 流量） |

## 重启 Karing 服务

```bash
# 暴力重启（Karing GUI 会自动拉起 service）
taskkill /F /IM karingService.exe

# 等 3-5 秒后验证
timeout /t 3 /nobreak >nul
netstat -ano | findstr "3067"
# 确认 3067 端口恢复监听
```

## 同步更新 no_proxy 环境变量

```bash
# 编辑 ~/.bashrc，将新直连域名追加到 no_proxy
export NO_PROXY="$NO_PROXY,.newdomain.com"

# 立即生效
source ~/.bashrc
```

## 常见问题

| 问题 | 根因 | 修复 |
|------|------|------|
| Papr RSS 无法更新 | RSS 源 CDN 被 VPS IP 拦截 | 域名加入 `🎯 国内直连` 的 `domain_suffix` |
| Electron 更新连接被重置 | GitHub Release 302 到 Azure CDN | `objects.githubusercontent.com` 加入 `🐱 GitHub` |
| Play Store 无法连接 | Karing TUN 未正确路由 GMS UID | 设系统代理 `adb shell settings put global http_proxy 127.0.0.1:3067` |
| 某个网站加载极慢 | 走了国外代理绕路 | 加入 `🎯 国内直连` |

## 注意事项

- **修改 `karing_routing_group.json` 是白费功夫**：UI 重启后会覆盖外改
- **规则顺序敏感**：窄规则（特定域名）必须放在宽规则（`geolocation-!cn`）之前
- **`karingService.exe` 重启后 `karing.exe` 会自动拉起它**：不需要手动启动 service
- **`no_proxy` 只影响 git-bash/mingw 工具**：Windows 原生应用走系统代理，不受 `no_proxy` 影响
