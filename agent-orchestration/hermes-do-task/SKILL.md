---
name: do-task
description: "一键任务执行：plan → subagent execute → verify → handoff。串联 writing-plans + subagent-driven-development + handoff 为单次 workflow。"
---

# Do-Task: 一键任务执行

## 触发条件

用户给出一个**中等复杂度以上**的任务时自动启用此工作流。判断标准：任务涉及 **多文件修改 / 多步骤 / 需要规划和验证**。

**不触发**的场景（直接执行，不走流程）：
- 单文件编辑（改配置、修 typo）
- 已有明确计划只需执行的
- 用户明确说 "直接做" / "不用 plan"

## 工作流

### Phase 1：分析任务

快速判断任务复杂度，决定是否走完整流程。如果需要，简短告知用户：「这个任务我打算走 plan → 执行 → handoff 三步，开始？」

### Phase 2：Plan

加载 `software-development/writing-plans` 技能的要求：

1. 理解需求（必要时问 1-2 个精准问题，不反复问）
2. 拆分为子任务（每个 2-5 分钟）
3. 包含精确文件路径 + 完整代码 + 验证命令
4. 保存到 `.hermes/plans/YYYY-MM-DD_task-slug.md`

**如用户有明确完工标准，逐个写明在 plan 中。**

### Phase 3：Execute

加载 `software-development/subagent-driven-development` 技能的要求，逐任务 dispatch：

1. **实现 subagent** — 带着完整任务上下文 dispatch
2. **Spec 审核 subagent** — 检查实现是否符合 plan 要求
3. **Code quality 审核 subagent** — 代码质量把关
4. 审核不通过 → 修复 → 重审 → 通过后才进入下一任务

### Phase 4：Verify

所有任务完成后执行最终检查：
- 跑测试 / 验证命令
- 确认改动的完整性
- 列出改动文件清单

### Phase 5：Handoff

加载 `handoff` skill，生成交接文档：
- 本次做了什么
- 遗留事项 / 下一步建议
- 计划文件路径
- 脱敏

保存到系统临时目录，并告知用户路径。

## 工作流快照

```
任务输入
  ↓ 判断复杂度
[简单] → 直接执行
[中等+] →
  ↓ Phase 1 告知用户
  ↓ Phase 2 Plan → .hermes/plans/*.md
  ↓ Phase 3 Execute → subagent per task
  ↓ Phase 4 Verify
  ↓ Phase 5 Handoff → temp/handoff-*.md
  ↓ 报告完成
```

## 约束

- 每个 phase 开始前简短告知用户
- task 中需要用户决策的（如命名、接口设计），先问再继续
- 用户说 "继续" / "ok" 视为授权，不需要每个步骤打扰
- handoff 在用户可能不会立刻继续工作时才做，否则跳过
