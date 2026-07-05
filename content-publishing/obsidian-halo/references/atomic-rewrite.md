# 原子重写（Atomic Rewrite）准则

> 当链式 patch 超过 3 次仍未解决问题时，改用 `write_file` 一次性写入完整正确内容。

## 信号

出现以下任一情况，立即停止 patch：

- 3 次以上的 `patch`/`str.replace` 仍未修复所有 heading 问题
- 某次 replace 后发现了新问题（而非解决旧问题）
- 同一个章节被反复修改超过 2 次
- 需要同时修复「双重编号 + 标题合并 + 章节顺序」三个独立问题

## 做法

```python
from hermes_tools import write_file

content = """--- 完整 frontmatter 保持不变 ---

## 1. 完整章节
### 1.1 正确 H3（带 \n\n 与正文分离）

正文段落内容...

## 2. 下一个章节
### 2.1 子节
### 2.2 子节

...
"""

# 从前面的 read_file 获取现有 frontmatter 拼接
# 只重写正文部分，frontmatter 保持原样

write_file(path, content)
```

## 原理

- `patch` 是在未知上下文中做已知修改——不精确
- `str.replace` 是全局精确匹配——但谁能保证 old_string 真的唯一？
- `write_file` 是已知全部内容的确定性操作——结果可预测

## 验证

写完立即用 `search_files pattern="^#{1,4}"` 检查 heading 完整性。
