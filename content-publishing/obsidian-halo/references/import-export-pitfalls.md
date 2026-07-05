# import/export 的 `halo.name` 与覆盖陷阱

## 陷阱 1：`halo.name` 导致 import-markdown --force 跳过

`halo post import-markdown --file <path> --force` 如果 frontmatter 中有 `halo.name`，会**跳过文件解析，直接返回旧的 UUID**。

- 即使旧文章已被删除，它仍然返回旧 UUID
- 本地对文件的任何修改都不会被导入
- 返回的旧 UUID 在 Halo 端指向不存在的文章

**原因**：`--force` 的设计意图是幂等——检测到已 import 过的文章，就不再重复创建。但它只查 frontmatter，不验证 Halo 端的状态。

**复现步骤**：
1. 发布文章 A → `halo post export-markdown` → frontmatter 写入 `halo.name: xxx`
2. 本地修改文件 + 删除文章 A
3. `halo post import-markdown --force` → 看到新 UUID，以为成功了
4. 实际内容未更新（旧内容被跳过），或者新 UUID 指向空文章
5. 再将 `export-markdown` → 旧内容覆盖本地文件

**正确流程**：删掉 frontmatter 中的 `halo.name`（和整个 `halo:` 区块）→ import → publish → export 拉回新 UUID。

## 陷阱 2：export-markdown 覆盖本地修改

`halo post export-markdown <UUID> --output <path>` 会用 Halo 端的内容**完全替换**本地文件。

如果 import/update 未正确执行（如被 `halo.name` 跳过），export 会把**旧或空的内容**拉回来，覆盖你的本地修改。

**安全流程**：
1. Import/update → 用 `halo post get <UUID>` 确认内容正确
2. 用浏览器或 curl 确认页面渲染正确
3. 最后才 `export-markdown` 同步回本地
