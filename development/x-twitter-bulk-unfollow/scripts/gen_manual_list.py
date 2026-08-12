#!/usr/bin/env python3
# 生成手动取关清单（CDP 被标记时的兜底模式）
# 用法: python3 gen_manual_list.py <handles.json> <输出.md>
# 输入 handles.json: ["handle1", "handle2", ...]
# 输出: Markdown 链接清单，用户逐个 hover 取关
import json, sys

def main():
    if len(sys.argv) < 3:
        print("用法: gen_manual_list.py <handles.json> <输出.md>")
        return
    handles = json.load(open(sys.argv[1], encoding='utf-8'))
    out_path = sys.argv[2]

    # 可选: 关联 current_users.json 补充名字/粉丝/简介
    try:
        users = json.load(open('current_users.json', encoding='utf-8'))
        by_handle = {u['s'].lower(): u for u in users}
    except:
        by_handle = {}

    lines = ['# X 手动取关清单', '']
    lines.append('操作：打开链接 → hover「正在关注」→ 变红「取消关注」→ 点击')
    lines.append('')
    lines.append('| # | 账号 | 名字 | 粉丝 | 发帖 |')
    lines.append('|---|------|------|-----:|-----:|')
    for i, h in enumerate(handles, 1):
        u = by_handle.get(h.lower(), {})
        n = (u.get('n') or '')[:18]
        lines.append(f"| {i} | [{h}](https://x.com/{h}) | {n} | {u.get('f','')} | {u.get('st','')} |")

    content = '\n'.join(lines)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已生成 {len(handles)} 个: {out_path}")

if __name__ == '__main__':
    main()
