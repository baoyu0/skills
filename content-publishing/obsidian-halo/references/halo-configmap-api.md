# Halo ConfigMap API 指南

> Halo 的 ConfigMap API（`/api/v1alpha1/configmaps/system`）用于读写 Halo 系统配置，包括**代码注入（codeInjection）**、主题设置、SEO、邮件等。本文件专门记录 codeInjection CSS 回写的完整流程与陷阱。

## 适用场景

本文件由以下 SKILL 引用：
- **obsidian-halo**（本 skill）：当用户偏好要求「CSS/后台设置改完直接给代码，让用户自己复制粘贴」时，说明为什么不通过 API 操作 ConfigMap，以及用户手动操作的正确指引。
- **halo-theme-css** skill：实际执行 CSS 注入时使用。

## 核心 API

| 项目 | 值 |
|------|-----|
| Endpoint | `GET/PUT /api/v1alpha1/configmaps/system` |
| 鉴权 | `Authorization: Bearer <pat>` |
| 目标字段 | `data.codeInjection`（JSON 字符串） |
| 操作方式 | **完整替换**：GET → 解析 → 修改 → 序列化 → PUT 写回 |

### codeInjection 数据结构

`configmaps/system` 的 `data.codeInjection` 是一个 JSON 字符串，包含以下字段：

| 字段 | 用途 | 内容类型 |
|------|------|---------|
| `globalHead` | 全局 `<head>` 注入 | HTML 片段（含 `<style>`） |
| `globalFooter` | 全局页脚注入 | HTML 片段 |
| `contentHead` | 文章区 `<head>` 注入 | HTML 片段 |
| `contentFooter` | 文章区页脚注入 | HTML 片段 |

## 完整替换模式（Read-Modify-Write）

ConfigMap API 不支持部分更新（PATCH），必须**读取完整对象 → 修改目标字段 → PUT 写回整个对象**。

```bash
# ====== Step 1: GET 当前配置 ======
curl -s -H "Authorization: Bearer ${PAT}" \
  "https://jia.baoyu2023.top/api/v1alpha1/configmaps/system" \
  | python3 -c "
import sys, json
cm = json.load(sys.stdin)
ci = json.loads(cm['data']['codeInjection'])

# ====== Step 2: 修改 codeInjection ======
old_head = ci.get('globalHead', '')
new_css = '''<style>
/* 自定义表格表头金色 */
.post-content table thead {
  background: #c9942e !important;
}
</style>'''
ci['globalHead'] = old_head + '\n' + new_css

# ====== Step 3: 序列化回 data.codeInjection ======
cm['data']['codeInjection'] = json.dumps(ci, ensure_ascii=False)

# 输出供 PUT 使用
print(json.dumps(cm, ensure_ascii=False, indent=2))
" > /tmp/halo-cm-payload.json

# ====== Step 4: PUT 写回 ======
curl -X PUT \
  -H "Authorization: Bearer ${PAT}" \
  -H "Content-Type: application/json" \
  -d @/tmp/halo-cm-payload.json \
  "https://jia.baoyu2023.top/api/v1alpha1/configmaps/system"
```

## 关键陷阱

### 1. CSS 必须用 `<style>` 包裹（致命！）

Halo 代码注入的内容直接插入 HTML `<head>` 中。**裸 CSS 没有 `<style>` 包裹时，浏览器将其渲染为可见的纯文本** -- 在页面顶部或某个位置弹出 CSS 源码文字。

```css
/* ❌ 错误 -- 裸 CSS 会显示为可见文字 */
.post-content table thead { background: #c9942e; }

/* ✅ 正确 -- <style> 包裹后浏览器正确解析 */
<style>
.post-content table thead { background: #c9942e; }
</style>
```

**修复规则**：每次追加 CSS 时，确保：
- 以 `<style>` 开头
- 以 `</style>` 结尾
- 中间为完整的 CSS 规则

### 2. Python `urllib` PUT 403 vs `curl -X PUT` 200（已验证）

同一 PAT、同一 endpoint、同一 payload，Python `urllib` 和 `curl` 行为不同：

| 工具 | GET | PUT | 状态码 |
|------|-----|-----|--------|
| `curl` | ✅ 正常 | ✅ 正常 | 200 |
| Python `urllib` | ✅ 正常 | ❌ 403 | 403 Forbidden |
| Python `requests` | ✅ 正常 | ❌ 403（可能） | 403 |

```python
# ❌ 这个会返回 403
import urllib.request, json
req = urllib.request.Request(
    f"{site}/api/v1alpha1/configmaps/system",
    data=json.dumps(cm).encode('utf-8'),
    headers={
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    },
    method="PUT"
)
resp = urllib.request.urlopen(req)  # → 403 Forbidden
```

**根因**：Python 标准库 `urllib` 与 `curl` 的 HTTP 实现差异（可能是 HTTP 版本协商或 header 顺序导致 Halo 服务器鉴权逻辑分支不同）。截至 2026-07 已验证多次，**非临时网络问题**。

**修复**：ConfigMap PUT 回写始终用 `curl` 命令行，不要用 Python `urllib`。

```bash
# ✅ 正确做法
curl -X PUT \
  -H "Authorization: Bearer ${PAT}" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  "https://jia.baoyu2023.top/api/v1alpha1/configmaps/system"
```

### 3. 完整替换模式可能覆盖他人修改

因为 ConfigMap 不支持 PATCH，GET → MODIFY → PUT 期间如果有其他操作也在修改同一 ConfigMap（如 Halo 后台的代码注入编辑器），后 PUT 的会覆盖先写的。

**预防**：避免在后台编辑的同时通过 API 写入。操作前用 `GET` 确认当前值。

### 4. PAT 权限不足

ConfigMap API 需要 PAT 的 **ConfigMap 写权限**（halo 后台 Personal Center → Personal Access Token 中勾选 `ConfigMap Manage` 或类似 scope）。`Post Manage` scope 不足以写 ConfigMap。

如果返回 403 且确认已用 `curl`：
- 重新创建 PAT，勾选更完整的 scope
- 或直接用 halo CLI（`halo` 命令）替代 ConfigMap API

## 为什么 SKILL 推荐「给代码让用户自己复制粘贴」

obsidian-halo skill 的用户偏好明确写着：

> **代码注入改 CSS → 直接给代码，让用户手动复制粘贴。** ConfigMap API 回写 CSS 的风险太高（可能漏 `<style>` 包裹、纯文本暴露在页面中）。

原因总结：
1. **`<style>` 包裹容易遗漏** -- 裸 CSS 产生可见文字，影响博客外观
2. **Python `urllib` 403** -- 无法在 skill 的 Python 工作流中可靠地一步完成回写
3. **完整替换可能覆盖** -- 如果用户同时在后台编辑代码注入，API 写入可能有冲突
4. **用户确认后再执行** -- CSS 变更影响全局外观，用户偏好明确要求先列方案、用户说「好」才动手

## 正确工作流

```text
1. 在浏览器中确认当前样式效果（用 browser_console / browser_navigate）
2. 编写 CSS 修改方案（含 <style> 包裹）
3. 展示给用户确认
4. 用户确认后 → 给出完整 CSS 代码段 → 告知粘贴路径
   （Halo 后台 → 外观 → 代码注入 → 全局 head）
5. 用户粘贴后 → browser_console 验证效果
```

## 相关参考

- `references/halo-css-injection.md` -- 代码注入 CSS 的选择器、配色方案、深色模式策略
- `references/halo-mermaid-rendering.md` -- 通过 ConfigMap API 注入 Mermaid 全局样式
