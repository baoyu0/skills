# Halo 官方 CLI 用法参考

`@halo-dev/cli` v1.3.0，已全局安装 + 已登录 bearer token。

## 安装与状态检查

```bash
halo --version                 # v1.3.0
halo auth current              # → 查看当前 profile
halo auth profile list         # → 列出所有 profile
```

## Profile（已配好 `default`）

```bash
halo auth login --profile default --url https://jia.baoyu2023.top --auth-type bearer --token <pat>
halo auth profile use default
```

Token 存在系统 keyring（`~/.config/halo/config.json` 存的是 profile 元数据，不含 token）。

## 文章管理

### 创建/导入（Markdown）

```bash
halo post import-markdown --file ./post.md --force
```

- frontmatter 的 `title` / `slug` / `categories` / `tags` 会被正确解析
- **总是创建新文章**，不会按 slug 匹配更新
- 创建为 draft，需要 `halo post update <uuid> --publish true` 发布
- `--force` 只在 CLI 有本地跟踪记录时避免二次确认，不影响创建新文章的行为

### 更新

```bash
halo post update <uuid> --title "新标题" --publish true
halo post update <uuid> --content "新内容" --publish true
halo post update <uuid> --categories 分类1,分类2 --tags 标签1,标签2
halo post update <uuid> --slug new-slug --cover https://...
```

- `--content` 只接受**内联文本**，不支持从文件读取
- `--publish true` 可将草稿发布（draft 修改后必须加此参数才上线）

### 导出为 Markdown

```bash
halo post export-markdown <uuid> --output ./post.md
```

- 导出的 frontmatter 含 `halo.site` / `halo.name` / `halo.publish`，可用作后续更新的锚点

### 列表与查询

```bash
halo post list --page 1 --size 20
halo post get <uuid> --json       # 需要 UUID，slug 不支持
```

### 删除

```bash
halo post delete <uuid> --force
```

## 其他命令

```bash
halo single-page list
halo single-page create --title "About" --content "# About" --publish true
halo plugin list
halo theme list
halo search --url https://jia.baoyu2023.top --keyword "关键词"
halo backup list                 # 备份管理
```

## 与 obsidian-halo publish.py 的关系

| 操作 | Python 脚本 | 官方 CLI | 建议 |
|------|-----------|---------|------|
| 创建文章 | `create` → 裸文上传 → 等 Halo 自动配图 | `import-markdown` 一步到位 | 后者更简洁，但不支持 `auto` 中的 uuid→文件追踪 |
| 更新内容 | `update` → PUT draft + publish | `update <uuid> --content` | 都需要先知道 uuid；CLI 省掉 HTTP 细节 |
| 读取封面 | `pull` → 轮询 GET | `export-markdown` → 解析 frontmatter | 后者更干净 |
| AI 增强 | `enhance` → 纯本地操作 | 无对应命令 | Python 脚本不可替代 |
| 视频清理 | `cleanup` → 纯本地操作 | 无对应命令 | Python 脚本不可替代 |

## 内置 Agent Skill 位置

```bash
/d/npm-global/node_modules/@halo-dev/cli/skills/
├── halo-cli/                        # 路由入口
├── halo-cli-auth/                   # 登录、profile
├── halo-cli-content/                # 文章管理（核心）
├── halo-cli-moderation-notifications/
├── halo-cli-operations/             # 插件、主题、附件、备份
├── halo-cli-search/                 # 公开搜索
├── halo-cli-shared/                 # 共享规则
└── README.md
```

这些 skill 尚未注册到 Hermes。需要时可用 `skill_manage action=create` 把它们的内容导入到 `~/AppData/Local/hermes/skills/halo-cli-*/`。
