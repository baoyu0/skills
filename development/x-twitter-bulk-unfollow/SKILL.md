---
name: x-twitter-bulk-unfollow
description: X 关注列表审计与批量取关。关注数满需腾空间时用。
version: 2.0.0
---

# X/Twitter 关注审计与批量取关

**背景**：X 官方写 API 付费（$200+/月），社区 CLI/MCP 只读或要 key。可行路径 = 内部 GraphQL API（读）+ obu CDP UI 自动化（写）+ 手动清单（兜底）。实测 7500 关注：抓取 ~15 分钟，取关 50 个 ~8 分钟。

## 完整工作流（五阶段）

```
① 抓全量（GraphQL）→ ② 本地筛选（多轮）→ ③ CDP 可用性检测 → ④ 取关（自动/手动）→ ⑤ 只读验证
```

数据落盘后可反复分析，不用重新抓取。**用户手动操作后必须重新抓取验证**（快照会过时）。

## 一、读：抓全量关注列表（GraphQL API）

### 1. 前置：从页面提取 bearer token 和 queryId

X 会轮换公共 bearer token。每次新会话先提取（页面上下文 fetch main.js）：

```js
// 页面上下文执行（obu cdp Runtime.evaluate），脚本在 scripts/gettoken.js
const r = await fetch('https://abs.twimg.com/responsive-web/client-web/main.cec9b1ca.js');
const t = await r.text();
// bearer: t.indexOf('AAAAAAAA') 处截取 ~200 字符
// queryId: 搜 'operationName:"Following"' 附近 regex /queryId:"([A-Za-z0-9_-]+)"/
```

2026-08 实测：
- 新 bearer（旧 token 已失效返回 401）: `AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA`
- Following queryId: `b8XpwALENnJdFSHchkK6rw`（会变，需重新提取）
- Unfollow queryId **不在 main.js**（懒加载 chunk），别浪费时间找，取关走 UI 流程

### 2. Following API 请求

```
GET https://x.com/i/api/graphql/<Following_queryId>/Following?variables=<encoded>
```

variables 必须带 `features` 对象（19 个 feature switch，见 scripts/fetch2.js），否则 403。
Headers 必须有：`authorization: Bearer <token>`、`x-csrf-token`（从 cookie ct0 取）、`x-twitter-auth-type: OAuth2Session`。

**2026 新字段结构**（旧 legacy 字段已拆散）：
- screen_name/name/created_at → `u.core`
- followers → `u.relationship_counts.followers`（不是 followers_count！）
- tweets → `u.tweet_counts.tweets`（不是 count！）
- blue → `u.is_blue_verified`
- description → `u.profile_bio.description`
- protected → `u.privacy.protected`

### 3. 分页 + 限流

- 每页 count=100 实际返回 ~50 用户；cursor 取 `cursorType === 'Bottom'` 的 entry
- 分页深度上限 ~7500（X 硬限制，抓满后 cursor 循环 → `CURSOR_STUCK`）
- **429 限流**：触发后等 90-180s。规避策略：每批只抓 2-4 页，页间隔 800ms，每 10 批冷却 30s
- 断点续传：数据存 `window.__xf` + `window.__xcursor`，每批调用 append（见 scripts/fetch2.js）
- 去重：按 screen_name 小写 Set（见 scripts/dedup2.js）

### 4. 数据导出（CDP 返回值限制）

- window 数据分块读回：`JSON.stringify(window.__xuniq.slice(start, start+400))`（见 scripts/getchunk.js）
- CDP 返回 JSON 结构：`j['result']['result']['value']`（两层 result！）
- emoji 会被截断成 surrogate → 保存时 `s.encode('utf-8', errors='replace')`
- **p.json 会被并发脚本覆盖**：多个脚本共用 p.json 临时文件时互相踩，改用独立文件名（pf.json/pd.json/pg.json）

## 二、写：批量取关（obu CDP UI 自动化）

**为什么不用 API**：Unfollow queryId 在懒加载 chunk 里找不到，UI 流程验证过更稳。

### 已验证流程（每个用户 ~10s，脚本 scripts/batch_fast.sh）

```bash
# 1. 导航必须用 obu navigate（window.location.href 会导致 CDP target 断开）
obu navigate --tab-id <TAB> --session-id "<SID>" --url "https://x.com/<handle>"

# 2. 轮询等待: pathname == handle && readyState == complete && [data-testid$="-unfollow"] 存在
# 3. 关键坑：必须 mouseMoved 再 click（React 需要 hover 状态）
# 4. 确认菜单 [data-testid="confirmationSheetConfirm"] 弹出后，同样 mouseMoved+click
# 5. 验证: [data-testid$="-unfollow"] 消失 = 成功（uf:false）
```

- 按钮定位：profile 页 `[data-testid$="-unfollow"]`，data-testid 自带 user_id（`<id>-unfollow`）
- 会话用完必须 `obu finalize-tabs --session-id <SID> --keep '[]'`
- 批量用 `terminal(background=true, notify_on_complete=true)` 后台跑
- **batch_fast.sh 优化**：每用户只尝试 2 次 + FAIL 集中最后重试（比每用户 6 次快 3 倍）

## 三、质量筛选（避免误伤）

**分层执行策略**（按信号强度从强到弱）：
1. **第一层：铁板信号**（零误伤）— 名字/简介明写 互fo/互关/回关/follow back/FO必回 的涨粉号。中文互fo号是关注列表最大水分，可放心批量取关
2. **第二层：明确引流**（低误伤）— 荐股带单（"有偿问诊/带单/加飞书/加微信诊股"）、赌博平台、挖矿推广、色情（绳模/媚黑/腿照营业/成人动漫）、移民中介、邪教（心灵法门）
3. **第三层：关键词信号**（高误伤，必须人工甄别）— 财经/营销/成人关键词命中后逐个看简介确认

**误伤保护**（按优先级）：
- 蓝标认证保留
- 发帖 > 2000 保留（活跃真人）
- 简介含价值关键词保留：founder/创始人/openai/anthropic/google/microsoft/apple/huggingface/harvard/mit/stanford/berkeley/cuhk/postdoc/phd/professor/engineering/engineer/developer/researcher/开源/作者/building/github.com/vc/investor/sre
- 手动保护名单：开源项目作者、大厂从业者（OpenManus、Apache PMC、Google GDE、OpenAI/HF/Apple 工程师）、用户正在用的工具官方号（Tolaria）、学术界（CUHK PhD、大学教授）
- **自动关键词的经典误伤**：'裸'→"裸辞"、'色'→"色即是空"、'福利'→"人民的福利"（政治语录）、'约'→"约会"、'股'→个人炒股记录号、'投资'→个人理财记录号。中文语义陷阱极多，命中后必须看原文再决定

**真正低质量信号**：零发帖、发帖<20 且粉丝<700 且新注册、老号（≤2020）无成长、互关引流号、广告号（发帖<5 简介纯 promo）、荐股带单、赌博/挖矿、色情擦边、废弃号（"已搬家到 @xxx"）、邪教传教

## 四、手动清单模式（CDP 被标记时的兜底）

**触发条件**：CDP 注入无效（见坑表）时，生成链接清单让用户手动取关。

**流程**：
1. 从 current_users.json 筛选候选（脚本见 references/手动清单生成）
2. 生成 Markdown 清单：链接 + 名字 + 粉丝 + 发帖 + 简介（分批次，每批 ≤50）
3. 用户手动操作：打开链接 → hover「正在关注」→ 变红「取消关注」→ 点击
4. 手动后**必须重新抓取全量验证**（不能信"我清完了"的说法，实际可能漏）

实测：53 个手动清单，用户清完后验证 48/53 移除，5 个遗漏补清。手动 50 个约 10 分钟。

## 五、只读验证（区分假 FAIL / 真剩余）

脚本 scripts/verify.sh 模式：导航到 handle → 查 `[data-testid$="-unfollow"]` 状态：
- `uf:false` + `fb:true` = 已取关（ALREADY_UNFOLLOWED，假 FAIL）
- `uf:true` = 仍在关注（STILL_FOLLOWING，真剩余）
- `EVAL_FAIL` = obu 偶发失败，重跑

**关键坑：verify 脚本的 SESSION 必须匹配 TAB 所属的 session**（跨 session 调用全 EVAL_FAIL，踩过 3 次）。TAB 是 open-tab 返回的 id，SESSION 是 open-tab 时指定的名字。

## 坑汇总

| 坑 | 现象 | 解决 |
|----|------|------|
| 旧 bearer token | 401 code 32 | 从 main.js 重新提取 |
| 缺 features 参数 | 403 空响应 | variables 带 features 对象 |
| 字段名变了 | followers 全 0 | relationship_counts.followers / tweet_counts.tweets |
| 429 | STATUS:429 | 等 90-180s + 降速 |
| JS 导航 | CDP target 断开 | 用 obu navigate |
| 无 mouseMoved | 点击无效/菜单不弹 | mouseMoved → pressed → released |
| 确认菜单延迟 | NO_BTN | 轮询 5s × 重试 |
| emoji surrogate | json.dump 报错 | errors='replace' |
| p.json 并发覆盖 | 表达式被换 | 各脚本独立临时文件名 |
| verify session 错 | 全 EVAL_FAIL | SESSION 匹配 TAB 所属 session |
| 快照过时 | 验证出现已移除/新增 | 每次操作后重新抓取 |
| **X 取关风控** | 连续取关后点击无任何反应（无菜单/无确认框/按钮不变） | **立即停止**，等 12-24h 冷却。硬刷会升级为账号级限制 |
| **CDP 注入被标记** | 连续 ~375 个自动化后，CDP 鼠标/键盘/JS 点击全部无效（0 网络请求），但用户手动同账号成功 | 会话级检测。无多 profile 可换时：①手动清单模式 ②等标记冷却（时间未知）③新 Chrome profile（不同指纹） |

**风控阈值实测（2026-08）**：连续 ~65 个后开始出现 FAIL（点击无反应）= 风控前兆，立即停。**安全节奏：单批 ≤40-50 个 + 每批间休息 10-15 分钟 + 单日 ≤150**。连续两天操作后阈值降低（200 → 65 → 40），需要更长冷却。单会话自动化总量 ≤300-350 个，达到后改手动。

**风控/标记解除检测**（恢复前先测，1 分钟）：打开任意 profile → 点击 `[data-testid$="-unfollow"]` → 查 `[data-testid=confirmationSheetConfirm]` 或 `uf:false`。弹出/变 false = 恢复，可继续；NO_BTN 且 hook fetch 无 graphql 请求 = 未恢复，继续等。

## 参考脚本（scripts/）

- `batch_fast.sh` — 批量取关（2 次尝试 + FAIL 集中重试），改 INPUT_FILE/SESSION_NAME/TAB_ID/LOG_FILE 即可
- `gettoken.js` — 提取 bearer + queryId
- `fetch2.js` — 批量抓取（断点续传 + 429 降速）
- `dedup2.js` — 去重生成 __xuniq
- `getchunk.js` — 分块导出
- `btnpos.js` / `coords.js` — 按钮/确认菜单定位
- `verify.sh` — 只读验证 uf 状态
- `manual_click.js` — 生成手动清单

## 工作目录

`C:/Users/zhaid/x-following-audit/`：
- `current_users.json` — 当前全量快照（最新）
- `all_users.json` — 旧快照（对比用）
- `new_follows.json` — 新增关注（对比旧快照）
- `unfollow_*.json` — 各轮执行清单
- `进度存档.md` — 跨会话接续状态
- `手动取关清单.md` — 手动模式清单

**执行节奏**：抓全量（1 次）→ 筛选（多轮）→ 取关（自动/手动）→ 验证（只读）。用户手动操作后必须重新抓取验证。
