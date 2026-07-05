# H3 子节插入技术

## 问题

auto-number 后文章有了 H2 章节，但 H3=0（扁平目录）。需要在各 H2 章节内插入 `### X.Y 子节`。

## 核心方法：`execute_code` + `str.replace` 内容匹配

**绝对不要用行号定位**——line number 在后续编辑中会漂移。正确做法是用内容中**唯一的一段字符串**作为插入锚点。

### 第一步：分析文章，确定每个 H3 的位置

阅读 auto-number 后的文件，为每个 H2 章节规划 H3：
- 每个 H2 至少拆 2 个 H3
- H3 编号 = 父 H2 编号.1、父 H2 编号.2 等
- 自然拆分点：列举项前、主题切换的过渡句、长章中间

### 第二步：找到每个插入点的唯一锚点

H3 应插在两段相邻正文之间。锚点用**该处的完整两段**确保唯一性：

```python
# ✅ 正确：用前后文片段确保唯一
content = content.replace(
    # old = 插入点附近的两段连续文本
    '情况 A 的完整描述段落。\n\n'
    '情况 B 的完整描述段落。',
    # new = old 中间插入 H3
    '情况 A 的完整描述段落。\n\n'
    '### X.Y 子节标题\n\n'
    '情况 B 的完整描述段落。'
)

# ❌ 错误：锚点太短，可能匹配多处
content = content.replace('情况 A 的完整描述段落。', '...')

# ❌ 错误：用行号定位，编辑后漂移
lines.insert(42, '### X.Y 子节标题')
```

### 第三步：执行并验证

```python
# 把所有 str.replace 放在一个 execute_code 里
# 最后写回 + 验证
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# 验证
import re
headings = re.findall(r'^(#{1,4}) .+', content, re.MULTILINE)
for h in headings:
    print(h)
```

### 常见锚点选择模式

| 插入场景 | 锚点模式 |
|----------|----------|
| 列表前 | 列表前一句 + 列表第一项 |
| 代码块前 | 代码块前一句 + 代码块语言标注行 |
| 分段主题切换 | 上一段完整段 + 下一段首句 |
| 列举项间 | 第 N 项文字 + 第 N+1 项文字 |
| 「第一/第二」格式 | `我建议先做 5 个模块。\n\n第一...` |

<<<<<<< HEAD
=======
### 第四步：Post-replace 清理

`str.replace` 把 `**粗体**` 转为 `### H3` 后，可能产生两种格式问题：

**问题 A：列表中的粗体 → `- ### H3` 破碎标记**

原文中 `- **概念名：说明**` 替换为 `- ### 1.1 概念名：说明`。`- ###` 是无效的 markdown（列表项内嵌 H3），Halo 不会正确渲染。

**修复**：
```python
content = re.sub(r'^- ### (\d+\.\d+) ', r'### \1 ', content, flags=re.MULTILINE)
```

**问题 B：H3 和正文在同一行**

原文 `**标题** 后面跟着正文` 替换为 `### 1.1 标题 后面跟着正文`。heading 和文本在同一行，破坏结构。

**修复**：替换时在 heading 后加 `\n\n`，或二遍扫描：
```python
# 方案1：替换时自带换行（推荐）
content = content.replace('**标题** 后面', '### 1.1 标题\n\n后面', 1)

# 方案2：替换后统一修复（适用于批量 replace）
for i in range(1, 9):
    content = re.sub(rf'(### 3\.{i} [^\n]+?) ', r'\1\n\n', content, count=1)
```

**检测方法**：
```python
bad = [l for l in content.split('\n') 
       if re.match(r'^### \d+\.\d+ .{20,}', l) and len(l) > 65]
print(f"⚠️ {len(bad)} H3s still inline" if bad else "✅ All H3s clean")
```

### 问题 C：粗体污染 H3 heading

原文中的粗体标注 `**执行结果**` 在替换后可能污染 `###` 标记。

**场景**：文章中有 `**执行结果**：Fable 5 分析了...`，你写替换锚点为：

```python
# ❌ 错误：锚点包含粗体闭合标记前的纯文本
old = "执行结果**：Fable 5 分析了最近 39 次会话"
new = "### 2.2 执行结果与关键判断\n\n**执行结果**：Fable 5 分析了最近 39 次会话"
# 结果：**### 2.2 执行结果与关键判断 ← 粗体污染 H3！
```

**根因**：原始文本 `**执行结果**：` 中闭合 `**` 落在锚点 `执行结果**` 的匹配范围内。替换把匹配到的 `**执行结果**` 整体换成 `### 2.2 执行结果与关键判断\n\n**执行结果**`，导致 `**` 跑到 `###` 前面。

**修复**：
1. 替换前检查锚点附近有无 `**` 干扰：
   ```python
   idx = content.find(old)
   print(f"Before: {content[max(0,idx-5):idx]!r}")  # 有 '**' 则需调整
   ```
2. 改用不受粗体标记干扰的锚点（用下一段的关键内容）：
   ```python
   # ✅ 正确：用粗体后的唯一内容做锚点
   old = "分析了最近 39 次会话，按杠杆作用分为三个批次"
   new = "### 2.2 执行结果与关键判断\n\n**执行结果**：Fable 5 分析了最近 39 次会话"
   ```

**检测方法**：发布后用 `halo post get --json` 检查 raw 中的 heading 行：
```bash
halo post get <UUID> --json 2>&1 | python3 -c "
import sys, json
raw = json.loads(sys.stdin.read())['content']['raw']
print('⚠️ 粗体污染' if '**###' in raw else '✅ 干净')
"
```

>>>>>>> 240cdd8 (docs: batch H3 insertion guide, Chinese quote trap, execute_code size check)
### 注意事项

- **每个 `str.replace` 的 old 必须在全文唯一**。如果有多处相同，用更长 context 区分
- **每个 replace 前用 `if old in content` 做 fail-fast 断言**——匹配失败时立即打印实际附近文本：

  ```python
  hint = old[:30]
  if old not in content:
      idx = content.find(hint)
      print(f"❌ Not found: {old[:40]!r}")
      if idx >= 0:
          actual = content[idx-10:idx+len(old)+10]
          print(f"   Actual nearby: {actual!r}")
      continue  # 跳过失败的 replace，不中断其他
  ```

- **多个 replace 按文件从前到后的顺序写**——前面的 replace 不改变后面匹配的位置。但由于后续 replace 作用于已替换的整体内容，如果 old 字符串在前一步被修改了，第二步的锚点必须用第一步后的新内容。
- **一个 `execute_code` 内完成所有 replace + 写回 + 验证**，不要分多次
- 写完立即 `search_files pattern="^#{1,4} "` 确认所有 H2 章节都有预期的 H3 子节，无重复编号
- 如果某个 replace 匹配失败（旧文本已被改过或含特殊字符），标记并跳过，最后手动补

<<<<<<< HEAD
### 与 patch 的区别
=======
### 问题 D：str.replace 匹配多个位置造成 H3 重复

当 `content.replace(old, new)` 的 `old` 锚点不够唯一时，它会替换所有匹配位置。例如章节开头相似的叙述句被两章共用时，一个 replace 会在两个地方都插入 H3。

**根因**：auto-number 后各章节的第一句可能相似——「最直接的证据来自...」「回顾这几个月用下来...」「三者解耦后...」这些短语跨章节重复。

**修复**：
1. 每个 replace 前用 `content.count(old)` 确认只出现 1 次：
   ```python
   count = content.count(old)
   if count == 0:
       print(f"❌ Not found: {old[:40]!r}")
       continue
   elif count > 1:
       print(f"⚠️  Found {count} times, need longer context: {old[:40]!r}")
       # 扩展 old 字符串使其唯一
       continue
   content = content.replace(old, new, 1)
   ```

2. 或者强制只替换第一处：`content.replace(old, new, 1)`

3. 替换后用 `search_files` 检查是否有重复编号

**检测方法**：H3 插入完成后立即 `search_files pattern="^#{1,4} "`。如果有两个 `### 4.1` 或两个 `### 5.1`，说明某个 replace 匹配了多个位置。

## 与 patch 的区别
>>>>>>> 240cdd8 (docs: batch H3 insertion guide, Chinese quote trap, execute_code size check)

| 工具 | 适用场景 |
|------|----------|
| `str.replace` in execute_code | 批量插入多个 H3，纯新增内容 |
| `patch` | 精确替换小段内容，删除/修改少量文字 |
| `re.sub` | 全局模式替换（如清理「第 X 步」前缀） |
<<<<<<< HEAD
| `write_file` 全量重写 | 正文结构需要大幅重建时 |
=======
| `re.search` + re.MULTILINE + re.escape | 匹配含 `\.` 等特殊字符的标题，用 group(1) 提取标题内容做精确替换 |
| `write_file` 全量重写 | 正文结构需要大幅重建时 |

### 用正则匹配含转义符的标题

auto-number 后，`## 1\. 标题` 格式的标题变成 `## 3. 1\. 标题`（双重编号）。plain `str.replace` 常因 `\.` 的转义问题匹配失败（陷阱 57）。用 `re.search` 按模式查找后精确替换：

```python
import re

# 找到含 `\\.` 的 H2 标题并转为 H3
for old_dot, new_prefix in [('1\\.', '3.1 '), ('2\\.', '3.2 '),
                              ('3\\.', '3.3 '), ('4\\.', '3.4 ')]:
    pattern = rf'^## \d+\. {re.escape(old_dot)} (.+)$'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        title = match.group(1)
        old_line = f'## {match.group(0)[3:].strip()}'
        content = content.replace(old_line, f'### {new_prefix}{title}')
        print(f"✅ → ### {new_prefix}{title[:30]}")
    else:
        print(f"❌ No match for {old_dot}")
```

关键点：`re.MULTILINE` 使 `^` 匹配行首；`re.escape()` 自动处理 `\.` 的转义；`group(1)` 提取标题文本做精确 replace。
>>>>>>> 240cdd8 (docs: batch H3 insertion guide, Chinese quote trap, execute_code size check)
