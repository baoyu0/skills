# Halo 代码注入 CSS 指南

> Halo 后台「外观 → 代码注入 → 全局 head」中粘贴自定义 CSS 来定制博客外观。这是跨主题持久化的方式——换主题不丢配置。

## 首要原则：最小注入

> **只注入主题没有的东西，不和主题打架。** 背景色、深色模式、间距、滚动条、打印样式这些主题自己管得好的，别碰。

每次打算写 CSS 时先问自己：
- 这个样式主题没有吗？→ 才需要注入
- 会不会和主题的 CSS 变量冲突？→ 如果主题已有 `--body-bg-color`，直接覆盖它比写 `body { background }` 更稳妥
- 选择器类名确认过吗？→ 先上浏览器检查实际 DOM

## Fluid 主题文章区类名：`.post-content`，不是 `.markdown-body`

**这是最容易踩的坑。**

| 你直觉想用的选择器 | 实际正确的选择器 |
|---|---|
| `.markdown-body` ❌ | `.post-content` ✅ |
| `article` ❌（会影响首页列表） | `.post-content` ✅（只限文章详情页） |

验证方法（在浏览器控制台执行）：
```javascript
document.querySelector('article')?.className
// → "post-content mx-auto"  ✅
document.querySelector('.markdown-body')
// → 存在但在别的容器里，不是文章区 ❌
```

**为什么不用 `article`？** Fluid 主题首页的文章卡片也是 `<article>`，`article a` 会把首页链接也染成金色。

**教训**：每次写 CSS 选择器之前，先打开一篇博客文章，在控制台查 `document.querySelector('article')?.className` 确认真实类名。

## 表格金色表头（日夜通用）

让主题管表格底色，注入只负责表头金色。这样日间和夜间模式都正常：

```css
.post-content table thead {
  background: #c9942e !important;
  border: none !important;
}
.post-content table thead th {
  color: #ffffff !important;
  font-weight: 700 !important;
  padding: 11px 14px !important;
  border: none !important;
}
/* 表身：让主题自己管背景色 */
.post-content table tbody td {
  padding: 10px 14px !important;
  border-bottom: 1px solid #e8e6e0 !important;
}
```

**关键**：不给 `table` / `tbody` / `tr` 写 `background` 或 `color`——主题会处理夜间的深色适配。

## 核心陷阱

### 1. `prefers-color-scheme` 跟着操作系统走，不是跟着 Color Toggle

```css
/* ❌ 如果用户 Windows 是深色模式，日间模式永远切不回来 */
@media (prefers-color-scheme: dark) {
  :root { --bg-body: #18181b; }
}
```

`prefers-color-scheme` 检测的是**操作系统主题**（Windows 设置 → 个性化 → 颜色 → 选择默认应用模式），**不是**博客的 Color Toggle 按钮。用户点了 Color Toggle 但系统是深色 → 页面仍是深色。

**修复方案 A（推荐）：同时支持系统偏好 + 手动覆盖**

```css
:root { --bg-body: #ffffff; }  /* 默认浅色 */

/* 手动暗色优先于系统 */
:root[data-theme="dark"],
:root.dark {
  --bg-body: #18181b;
}

/* 系统暗色模式（仅在无手动设置时生效） */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]):not(.light) {
    --bg-body: #18181b;
  }
}
```

**修复方案 B（最直接）：放弃系统偏好，全手动控制**

```css
:root { --bg-body: #ffffff; }        /* 日间 */
:root.dark { --bg-body: #18181b; }  /* 夜间 */
```

然后给 Color Toggle 按钮加一小段 JS：`document.documentElement.classList.toggle('dark')`。

### 2. 注入 `<style>` 的 `!important` 可能被主题覆盖

Halo 的代码注入 `<style>` 在 DOM `<head>` 中，但主题 CSS（`main.css`）通常用 `link` 加载在之后。**即使你加了 `!important`，如果主题用了 `background` 简写属性（不是 `background-color`），简写会覆盖单属性。**

```css
/* 主题可能这样写： */
body { background: var(--body-bg-color); }  /* 简写，会覆盖 background-color */

/* 你的注入要这样写才能赢： */
body { background: var(--bg-body) !important; }  /* ⚠️ 用简写对简写 */
```

更稳妥的做法：**不要对抗主题的 `background`，而是覆盖主题变量本身**。Fluid 主题的 body 背景来自 `--body-bg-color` 变量。直接改这个变量比覆盖 `body` 选择器更可靠：

```css
:root {
  --body-bg-color: #ffffff;   /* 覆盖主题变量 */
  --bg-body: #ffffff;
}
/* 深色模式：覆盖主题变量 */
:root.dark {
  --body-bg-color: #18181b;
  --bg-body: #18181b;
}
```

### 3. 安全实验：用 `:root:not()` 隔离主题修改

修改主题 CSS 变量时，用 `:root:not()` 确保不会意外污染其他选择器：

```css
/* 只对根元素生效，不影响子元素 */
:root:not(.dark) { --body-bg-color: #ffffff; }
:root.dark       { --body-bg-color: #18181b; }
```

## 注入 CSS 架构建议

| 层 | 内容 | 位置 |
|---|---|---|
| **变量层** | 主题色、中性色、字体、圆角变量 `:root` | 注入 CSS 头部 |
| **覆盖层** | 覆盖主题已有的 CSS 变量（如 `--body-bg-color`） | 变量层之后 |
| **深色模式层** | `@media (prefers-color-scheme)` 或 `.dark` | 变量层之后 |
| **排版层** | `h1-h6`、`p`、`blockquote`、`code`、`table` 样式 | 中间 |
| **增强层** | `:focus-visible`、`prefers-reduced-motion`、`@media print` | 尾部 |

## 验收方法

部署后打开博客页面，在 `browser_console` 中验证：

```javascript
JSON.stringify({
  bgBody: getComputedStyle(document.body).backgroundColor,
  bodyBgVar: getComputedStyle(document.documentElement).getPropertyValue('--bg-body').trim(),
  h1: document.querySelectorAll('h1').length,
  h2: document.querySelectorAll('h2').length,
  h3: document.querySelectorAll('h3').length,
  stylesheets: document.styleSheets.length
})
```

## 字体加载优化

霞鹜文楷中文全包 5-15MB，必须做非阻塞加载：

```html
<!-- 延迟加载 + font-display: swap -->
<link rel="stylesheet" href="...lxgw-wenkai-webfront/style.min.css"
      media="print" onload="this.media='all'">
<style>
@font-face {
  font-family: 'LXGW WenKai';
  src: local('LXGW WenKai'), local('霞鹜文楷');
  font-display: swap;
}
</style>
```

## 相关工具

- **Color Toggle 调试**：`document.documentElement.className` 检查当前主题状态
- **CSS 变量检查**：`getComputedStyle(document.documentElement).getPropertyValue('--变量名')`
- **主题 CSS 扫描**：`document.styleSheets` 遍历找到覆盖了你的选择器
