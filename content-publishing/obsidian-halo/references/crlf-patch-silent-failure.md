# CRLF → patch 工具静默失败

## 现象

patch(old_string=..., new_string=...) 返回 `success: true`，但文件内容**没有变化**。后续操作基于旧内容继续，产生不可预测的结果（排版未生效、编号未更新、heading 未降级等）。

## 根因

Windows 上的 Markdown/脚本文件默认使用 CRLF 行尾（`\r\n`）。patch 工具的 `old_string` 匹配是**字符串精确相等**——包括换行符。如果你从 `read_file` 输出中看到的是以 `\n` 结尾的行，但文件实际存的是 `\r\n`，则：

```
old_string = "## 1. 标题\n"          # LF only, 20 chars
file_line  = "## 1. 标题\r\n"         # CR+LF, 21 chars
→ 不匹配，patch 跳过（不报错）
```

## 诊断

patch 后立即验证：

```bash
# 终端检查法
python3 -c "
with open('path/to/file.md', 'rb') as f:
    data = f.read(200)
print(repr(data))
"

# 或用 read_file 逐行确认修改行
read_file path="path/to/file.md" offset=N limit=5
```

## 修复方案

### 方案 A：execute_code + 二进制写入（推荐）

完全不经过 patch 工具的文本匹配层：

```python
path = r'D:\path\to\file.md'
with open(path, 'rb') as f:
    data = f.read()

# 直接替换字节
old = b'旧文本'
new = b'新文本'
data = data.replace(old, new)

with open(path, 'wb') as f:
    f.write(data)
```

### 方案 B：确保 old_string 含 `\r`

手动在 old_string 的换行后加 `\r`：

```
old_string = "## 1. 标题\r\n"
```

但 patch 工具的 old_string 语法不支持显式 `\r` 识别——所以方案 A 更可靠。

### 方案 C：先转换行尾

```bash
# 将 CRLF 转为 LF
sed -i 's/\r$//' path/to/file.md
# 再按常规 patch
patch ...  # 现在能匹配了
```

## 触发场景

- `export-markdown` 拉回的文件（Halo 输出默认 CRLF）
- Obsidian vault 中 Windows 上编辑的文件
- Git 未配置 `core.autocrlf = input` 时签出的文件
- `write_file` 工具写入的文件（git-bash 环境下用 `\n`，实际文件可能 `\r\n`）

## 预防

对关键操作（heading 编号、段落替换、frontmatter 修改），patch 后强制做一次验证：

```python
python3 -c "print(repr(open('path').readline()))"
# 确认第一字符不是 '\\r' 以外的意外内容
```
