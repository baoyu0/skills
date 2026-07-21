# AGENTS.md — Karing 路由规则管理

Karing 代理路由规则管理 — 为特定域名添加直连/代理路由，修复站点的网络访问问题。

## 触发场景

- 网站打不开 / 加载慢（路由问题）
- 域名不走代理 / 不该走代理
- Papr RSS 403、GitHub 下载失败、Play Store 连不上

## 关键架构

| 组件 | 说明 |
|------|------|
| `karing.exe` (GUI) | 用户操作界面 |
| `karingService.exe` | sing-box 核心，实际路由引擎 |
| 代理端口 | `127.0.0.1:3067` (HTTP/SOCKS5) |
| 控制 API | `127.0.0.1:3057` |
| 配置文件 | `%APPDATA%\Karing\karing\service_core.json` |

**核心原则：`service_core.json` 是唯一真实来源。** `karing_routing_group.json` 的 UI 外改会被 GUI 覆盖。

---

## 诊断步骤

```bash
# 对比走代理 vs 直连的响应
curl -s -o /dev/null -w "proxy: %{http_code}\n" -x http://127.0.0.1:3067 "https://<域名>"
curl -s -o /dev/null -w "direct: %{http_code}\n" --noproxy "*" "https://<域名>"
```

## 添加路由规则

修改 `service_core.json` 的 `route.rules` 数组。规则顺序敏感 — 窄规则（特定域名）必须放在宽规则（如 `geolocation-!cn`）之前。

### 路由组速查

| 路由组名 | 出站 | 场景 |
|----------|------|------|
| `🎯 国内直连[自定义]` | `direct_out` | RSS、国内 CDN、国内 API |
| `🐱 GitHub[自定义]` | `urltest_out` | GitHub Release Assets |
| `🌏 Google Play[自定义]` | VPS | Play Store |

## 重启服务

```bash
taskkill /F /IM karingService.exe     # Karing GUI 会自动拉起
# 验证: netstat -ano | findstr "3067"
```
