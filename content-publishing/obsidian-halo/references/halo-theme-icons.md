# Halo 主题图标系统（Fluid）

> Halo 后台编辑菜单元数据时，「图标」字段填什么？——取决于主题的 `annotation-setting.yaml`。

## Fluid 主题的菜单图标机制

### 原理

Fluid 主题在 `annotation-setting.yaml` 中定义一个菜单项注释：

```yaml
apiVersion: v1alpha1
kind: AnnotationSetting
metadata:
  name: annotation-setting-fluid-menu
spec:
  targetRef:
    group: ""
    kind: MenuItem
  formSchema:
    - $formkit: "text"
      name: "icon"
      label: "图标"
```

导航模板 `navigation.html` 中这样渲染：

```html
<i th:class="${#annotations.getOrDefault(menuItem, 'icon', '')}"></i>
```

**结论**：你填入「图标」字段的值，直接作为 `<i>` 标签的 `class` 属性。不是 SVG，不是图片 URL，是 **CSS 类名**。

### 内置 iconfont

Fluid 主题使用阿里巴巴矢量图标库（iconfont）。内置图标用 `iconfont icon-xxx` 格式：

- `iconfont icon-search` — 搜索按钮
- `iconfont icon-dark` — 深色模式切换
- `iconfont icon-user-fill` — 登录
- `iconfont icon-top` — 置顶文章

要在菜单项使用，去 [iconfont.cn](https://www.iconfont.cn) 找图标 → 获取 `Font Class` → 填入字段，如 `iconfont icon-home`。

### SVG 图标不可直接填入

因为字段值被当作 CSS class 渲染为 `<i class="填入值">`，Reicon、Lucide、Heroicons 等 SVG 图标库**无法直接填入**。

## SVG 图标替代方案：JS 注入

给导航栏「首页」加 SVG 图标，在 **外观 → 代码注入 → 页脚** 加：

```html
<script>
document.addEventListener('DOMContentLoaded', function() {
  const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
  navLinks.forEach(function(link) {
    if (link.textContent.trim() === '首页' && !link.querySelector('svg')) {
      link.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px"><path d="M12 21V17"/><path d="M4.22 8.42L9.69 4.23C10.13 3.92 10.67 3.92 11.11 4.23L16.58 8.42C16.97 8.69 17.2 9.12 17.2 9.58V18C17.2 18.83 16.54 19.5 15.7 19.5H8.1C7.27 19.5 6.6 18.83 6.6 18V9.58C6.6 9.12 6.83 8.69 7.22 8.42Z"/></svg> ' + link.textContent;
    }
  });
});
</script>
```

`stroke="currentColor"` 使图标自动继承主题文字颜色（深色/浅色模式自适应）。

## Reicon 图标库速查

| 属性 | 值 |
|------|------|
| 官网 | https://reicon.dev |
| GitHub | https://github.com/dqev/reicon |
| 许可证 | MIT（免费可商用） |
| 总数 | 2700+ |
| 格式 | SVG（也可通过 `reicon-react` / `reicon-vue` / CDN） |
| 网格 | 24×24px，统一 2px stroke |
| 风格 | Outline + Filled 两种 |
| 下载 URL | `https://reicon.dev/svg/<slug>.svg`（但无法直接 HTTP GET——需走页面 JS 下载） |
| CDN（unpkg） | `https://unpkg.com/reicon-react@1.1.2/icons/<PascalCase>` — 返回 React 组件源码，内含 base64 预览和 path data |
| 图标组件名 | PascalCase：`house-2` → `House2` |

### 获取 SVG path 数据

从 unpkg 获取 React 组件源码，其中有 `O`（Outline）和 `F`（Filled）的 path 数据：

```bash
curl -sL "https://unpkg.com/reicon-react@1.1.2/icons/House2"
```

输出中包含：
```js
const House2 = createIcon('House2', {
  F: `<g transform="scale(1.33333)"><path d="..." fill="currentColor"></path></g>`,
  O: `<g transform="scale(1.33333)"><path d="..." stroke="currentColor" ...></path></g>`
});
```

然后用 `transform: scale(1.33333)` 逆运算（乘以 0.75 得到 24×24 视图），或直接构造内联 SVG。

### 快速内联 SVG（Outline 风格）

```html
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 21V17" />
  <path d="M4.22 8.42L9.69 4.23C10.13 3.92 10.67 3.92 11.11 4.23L16.58 8.42C16.97 8.69 17.2 9.12 17.2 9.58V18C17.2 18.83 16.54 19.5 15.7 19.5H8.1C7.27 19.5 6.6 18.83 6.6 18V9.58C6.6 9.12 6.83 8.69 7.22 8.42Z" />
</svg>
```
