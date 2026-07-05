# CLI --content 长度限制与曲线方案

## 问题

`halo post update <UUID> --content "..."` 在 Windows Git Bash 下，正文超过约 8000 字符时会触发 `Argument list too long` 错误。这是 Windows 命令行参数长度限制，与 `halo` CLI 本身无关。

## 曲线方案

### 方案 A：只发布不改内容（推荐）

如果 `import-markdown` 已经导入了完整正文，后续发布**不需要**再次传 `--content`：

```bash
halo post update <UUID> --publish true
```

`--publish true` 单独使用时只改发布状态的 metadata，不涉及正文字段，不会触发长度限制。

### 方案 B：base64 中转（需改内容时）

```bash
# 1. Python 提取正文 → base64 文件
python3 -c "
import base64
body = open(r'D:/path/to/article.md', encoding='utf-8').read().split('---', 2)[2].strip()
open(r'C:\Users\zhaid\_halo-body.b64', 'w').write(base64.b64encode(body.encode('utf-8')).decode('ascii'))
"

# 2. Bash 解码 → halo update
BODY_B64=$(cat ~/_halo-body.b64)
BODY=$(python3 -c "import base64,sys; print(base64.b64decode(sys.argv[1]).decode())" "$BODY_B64")
halo post update <UUID> --content "$BODY" --publish true

# 3. 清理
rm -f ~/_halo-body.b64
```

### 方案 C：重删重建（只有短文章适用）

正文较短（<8000 字符）时，可直接通过 `--content` 传内联正文。
