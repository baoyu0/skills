# Obsidian → Halo 文章发布工作流

本仓库包含将 Obsidian 剪藏文章发布到 Halo 博客的完整工作流和 Python 脚本。

## 前置配置

1. 创建 `~/.hermes/halo-config.json`：
```json
{
  "pat": "你的Halo PAT",
  "site": "https://你的博客.com"
}
```

2. 部署 CSS（可选）：将 `references/hermes-docs-theme.md` 中的样式粘贴到 Halo 后台 → 设置 → 代码注入 → 全局 head 标签

## 工作流（6 阶段）

### Phase 0: 语言检测 & 翻译
```bash
python scripts/halo-publish.py detect "<文件路径>"
```
退出码 0 → 中文，跳过。退出码 1 → 英文，翻译 body 为简体中文后继续。

### Phase 1: 裸文上传
```bash
python scripts/halo-publish.py create "<文件路径>"
```

### Phase 2: 拉回 frontmatter
```bash
python scripts/halo-publish.py pull "<文件路径>"
```
（自动轮询 cover 就绪，无需 sleep）

### Phase 3: 自动编号
```bash
python scripts/halo-publish.py enhance "<文件路径>"
```
（自动编号 H2/H3 标题，显示结构报告）

### Phase 4: AI 优化排版
参考下方排版规则，完善 frontmatter、优化格式。

### Phase 5: 推送更新
```bash
python scripts/halo-publish.py update "<文件路径>"
```
（自动验证 HTTP 200 + title 匹配）

## 排版规则

### 层级结构
- 先清理混乱编号（`0.1-`、`1、`等），再重建规范编号：h2 → `1. `、`2. `；h3 → `1.1 `、`1.2 `
- 分析内容，并列技术项提升为 h3 子标题
- 层级连续不跳跃

### Callout 提示框
```
> **💡 提示：** 建议
> **⚠️ 注意：** 警告
> **📌 说明：** 补充
> **🔗 参考：** 链接
> **❓ 疑问：** 问题
> **✅ 结论：** 总结
```

### 代码块
- 全部标注语言：`bash`、`json`、`yaml`、`python`、`plaintext`
- 代码块前后空行

### 链接
- 描述性链接文本：`[名称](url)` ✅ 非 `[url](url)`
- 还原 nodeseek 类跳转链接

### 表格优先
- 对比类信息用表格，不用多列表

### 排版原则
- 每节 h2 开头有引导段
- 操作步骤用有序列表
- 大章节间 `---` 分隔
- 关键术语 **加粗**，路径/命令 `反引号`
- 正文不超过 120 字符/行
