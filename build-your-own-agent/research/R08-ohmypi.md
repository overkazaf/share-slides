# R08 — oh-my-pi (`omp`) 是什么：本地取证 + 联网核实

> 研究日期：2026-08-01
> 本地素材：`/Users/nongjiawu/playground/research/ohmypi/oh-my-pi`（HEAD `ef32694`，版本 `16.3.12`）
> 复用结论：`/Users/nongjiawu/playground/research/pi/analysis/raw/{04,05,06,06b}-*.md`
> 所有数字均在本地仓库重新点算过；联网数据均给出 API/URL 出处

---

## 0. 三层血统必须先说清楚（最容易讲错的地方）

演讲里最容易被混淆的一点：**「本地这份仓库」「oh-my-pi」「pi」是三个东西**。

| 层 | 仓库 | 关系 | 证据 |
|---|---|---|---|
| L1 上游本体 | `earendil-works/pi`（原 `badlogic/pi-mono`，作者 Mario Zechner） | agent 工具包本体 | GitHub API：`full_name = "earendil-works/pi"`，created `2025-08-09T14:03:50Z` |
| L2 深度 fork | `can1357/oh-my-pi`（`omp`，作者 Can Bölük） | pi 的**代码级深度 fork**，但**不是 GitHub 意义上的 fork** | `LICENSE` 同时保留两份版权；GitHub API `fork: false`、`parent: none` |
| L3 私有下游 fork | 本地这份 = `xia0maiiii/oh-my-pi` | `can1357/oh-my-pi` 的私有下游 fork | `FORK.md:3`；`git remote -v` → `origin = https://github.com/xia0maiiii/oh-my-pi` |

**关键澄清（务必别讲反）**：
FORK.md 里的 tier 成本模型，描述的是 **L3 相对 L2 的维护成本**，不是「omp 相对 pi 的关系」。
但它间接给了 omp↔pi 关系的最好注脚：omp 对 pi 做的正是**大量 Tier 2 级的改动**（重写核心 TS、加整套 Rust crates、换包名 scope、GitHub 层面彻底 detach），所以它才不是「pi + 插件」，而是一个独立演进的产品。

`LICENSE` 原文（本地 `LICENSE:1-4`）：

```
MIT License

Copyright (c) 2025 Mario Zechner
Copyright (c) 2025-2026 Can Bölük
```

can1357/oh-my-pi 的 README 自述（联网核实，`https://github.com/can1357/oh-my-pi/blob/main/README.md`）：
> "A coding agent with the IDE wired in." …a fork of Pi by Mario Zechner, rewritten as a coding-first surface with sessions, subagents, and extensibility.

---

## 1. 一句话定义

> **oh-my-pi（`omp`）是 Mario Zechner 的 pi 的一次「重写级深度 fork」：把一个极简 agent 工具包，改造成一个以编码为中心、自带模型知识库 / Rust 热路径 / 三层可扩展运行时的终端 agent 产品——代价是 63 万行 TS 源码 + 7 万行自研 Rust，和平均每天上百个 commit 的演进速度。**

如果要更短的一版（适合上 PPT 首页）：

> **omp = pi 的「工业化版本」：pi 证明了 4 个工具就能做 agent，omp 证明了把 agent 做到极致要付出多少工程量。**

---

## 2. FORK.md 的 tier 成本模型（精确引用）

FORK.md 是这个仓库里工程价值最高的文档。它把「维护一个高速上游的深度 fork」从英雄主义问题，转成一个**可度量、可优化的成本函数**。

### 2.1 定义（`FORK.md:15-19`，英文原文）

> ## The one rule: pick the lowest tier that works
>
> Every change has a **tier** = how much it costs to carry across an upstream sync.
> The cost of this fork is dominated by how much lands in Tier 2. **Push everything you
> can down to Tier 0.**

中译：**每个改动都有一个 tier = 它跨越一次上游同步的携带成本。本 fork 的总成本由落在 Tier 2 的量主导。把一切能下推的都下推到 Tier 0。**

### 2.2 三档定义（逐条原文）

| Tier | 原文标题（`FORK.md`） | 内涵 | 精确坐标 |
|---|---|---|---|
| **Tier 0** | `### Tier 0 — out-of-core. ZERO sync conflict. Prefer for ~everything.`（`:21`） | 「omp is *built* for out-of-core customization. These touch no upstream file, so an upstream sync **physically cannot** conflict with them.」（`:22-24`） | hooks / extensions / capability providers / SYSTEM.md / 磁盘上的 tools·commands·skills·rules·context files（`:26-40`） |
| **Tier 1** | `### Tier 1 — thin additive core seams. RARE, trivial conflict.`（`:46`） | 「When Tier 0 genuinely can't reach, add **a single line to a list/union** in core」（`:48`） | 只有 4 个坐标：`BUILTIN_TOOLS`/`HIDDEN_TOOLS`（`src/tools/index.ts`）、hook 事件 union（`src/extensibility/hooks/types.ts`）、`src/modes/rpc/rpc-types.ts`、`src/system-prompt.ts` 的 `data` 对象（`:52-56`） |
| **Tier 2** | `### Tier 2 — deep core / Rust patches. REAL conflict; manage with the discipline below.`（`:66`） | 「No seam exists: the turn loop…, prompt template *structure*, TUI internals, provider internals, `crates/*`. These are the **only** changes that need seam markers, ledger entries, and drift tests.」（`:67-70`） | `src/session/agent-session.ts`、`packages/tui`、`packages/ai`、`crates/*` |

### 2.3 最漂亮的一招：Tier 2 → Tier 1 → 0 的降级路径（`FORK.md:60-64`，原文）

> **Pro move — convert Tier 2 → Tier 1 → zero.** To do a deep-shaped change cheaply,
> add a **one-line Tier-1 seam** (a hook/dispatch call) in core, then put the real logic in
> a Tier-0 hook/extension *behind* that seam. Then **upstream the seam as a PR**. If it's
> merged, your core patch disappears forever and the logic stays private out-of-core.
> The cheapest divergence is the divergence you eliminate.

中译要点：在核心加**一行** Tier-1 seam（hook/dispatch 调用），真实逻辑放在 seam 背后的 Tier-0 扩展里；然后**把 seam 作为 PR 上游化**。合并后核心 patch 永远消失，业务逻辑始终留在私有仓库。**最便宜的分歧，是被消除掉的分歧。**

### 2.4 配套三件套

1. **Seam marker**（`FORK.md:74-91`）——所有 Tier-1/2 改动必须包在可 grep 的标记里：
   ```ts
   // >>> omp-fork(<topic>): why this exists + which upstream behavior it relies on
      ...your change...
   // <<< omp-fork(<topic>)
   ```
   一条 `grep -rn "omp-fork(" packages/ crates/` 就是**完整**的核心足迹。原文：「If a line is in core and not wrapped, it's a bug in our discipline.」
2. **分歧账本**（`FORK.md:95-104`）——8 列：`# / Tier / marker topic / 文件 / 目的 / **依赖的上游行为** / **同步后如何重新验证** / 能否上游化`。「依赖的上游行为」这一列是防语义漂移的关键元数据。
3. **漂移测试**（`FORK.md:169-174`）——原文：
   > A **clean** rebase can still silently break a Tier-2 patch: upstream refactors a function your patch calls, the types still line up, but the behavior changed. **Conflicts you see; drift you don't.**

   防御：`packages/coding-agent/test/fork-*.test.ts`，**每加一个 Tier-2 patch 就加一个漂移测试**。

### 2.5 分层的深刻之处（这句最适合上 PPT）

**这个分类不是按「改动大小」分层，而是按「与上游变更的正交性」分层。**

实证：`src/mcp/manager.ts` 是 1362 行、含五张状态表 + 崩溃熔断器 + epoch 取消的深度工程，但因为它住在 fork 自有目录里，**同步成本仍然是零**（`06b-omp-mcp-subsystem.md` §7）。反过来，一个 3 行的 Tier-2 patch 可能每次 sync 都要人工重解。

**当前实证胜利**：本 fork 的账本里两行都是 T0（`deploy/yf-worker/**` 与 `FORK.md`/`fork/**`/`.github/workflows/fork-sync.yml`），`grep -rn "omp-fork(" packages/ crates/` **当前返回空**——核心足迹为零。

### 2.6 上游速度到底有多快（联网实测，支撑 FORK.md 的前提假设）

FORK.md:4 说上游是「dozens of commits/day; ~800+ files change between patch releases」。实测（GitHub API，2026-08-01）：

| 指标 | 实测值 | 来源 |
|---|---|---|
| 近 7 天（2026-07-25→08-01）commit 数 | **1,159** ≈ **165 commits/天** | `GET /repos/can1357/oh-my-pi/commits?since=2026-07-25T00:00:00Z` 分页末页 |
| 默认分支累计 commit | 16,594 | 同上（不带 since） |
| 已发布 release 数 | **547** | `GET /releases?per_page=1` 分页末页 |
| tag 数 | 790 | `GET /tags?per_page=1` 分页末页 |
| 2026-07-01 之后的 release 数 | **51**（≈1.7 个/天） | `GET /releases?per_page=100` 过滤 |
| 本地 fork 落后量：`v16.3.12`(2026-07-08) → `v17.2.2`(2026-07-31) | **3,920 个 commit**（23 天） | `GET /compare/v16.3.12...v17.2.2` → `ahead_by: 3920` |

**结论**：FORK.md 说的「dozens of commits/day」是**保守说法**，实际是**百级/天**。23 天不同步就落后近 4000 个 commit——这解释了为什么 tier 模型不是洁癖而是生存需求。

---

## 3. 相对 pi 的增量创新清单

> 说明：下表「解决什么问题」是本研究的归纳；「证据路径」是本地仓库中可直接打开核对的文件。
> 「是否 pi 已有」一列基于 `04-omp-ts-packages.md` 的包级判定（✅全新 = 上游 pi-mono 无对应包）。

### 3.1 一览表

| # | 创新 | 解决什么问题（一句话） | 是否 pi 已有 | 证据路径 |
|---|---|---|---|---|
| 1 | **snapcompact** 位图帧上下文压缩 | 上下文超限时，不花一次 LLM 调用、不引入摘要幻觉，就能把历史压进 vision token | ✅ 全新包 | `packages/snapcompact/src/snapcompact.ts`(1974 行)、`crates/pi-natives/src/snapcompact.rs` |
| 2 | **hashline** 行锚定补丁语言 | 让模型的代码编辑「第一次就落地」，并在编辑前用内容指纹做乐观并发校验 | ✅ 全新包 | `packages/hashline/`(5693 行)、`src/prompt.md`、`src/grammar.lark` |
| 3 | **catalog** 模型知识独立包 | 多网关/转售商生态下「同一个模型有 20 个名字、20 套定价」的现实问题 | ✅ 全新包 | `packages/catalog/`(98,590 行)、`src/models.json`(1.84 MB) |
| 4 | **auth broker / gateway** | 容器化 / 多机 / 多账号场景下，让 refresh token 只有一个写者，客户端永远看不到 access token | ✅ 全新 | `packages/ai/src/auth-storage.ts`、`docs/auth-broker-gateway.md`(20 KB) |
| 5 | **dialect**（in-band 工具调用） | 长尾开源模型原生 tool calling 不可靠 → 用模型自己训练过的语法在 prompt 内做工具调用 | ✅ 全新 | `packages/ai/src/dialect/`（**11 种方言**，各配 `.md` 规范） |
| 6 | **mnemosyne / mnemopi** 双层记忆 | 跨 session 的长期记忆：working→episodic 巩固 + 混合召回，全本地无云 | ✅ 全新包 | `packages/mnemopi/`(19,324 行)、`docs/mnemosyne-memory-backend.md` |
| 7 | **TTSR**（Time Traveling Stream Rules） | 规则违反不是「事后骂一顿」，而是在模型写出违规 token 的瞬间打断并回滚重跑 | ✅ 全新 | `docs/ttsr-injection-lifecycle.md`(13.9 KB)、`src/prompts/system/ttsr-interrupt.md` |
| 8 | **工具两级加载 + BM25 发现** | 30+ 工具全塞进 system prompt 会吃掉大量 token 并降低选择准确率 | ✅ 全新 | `src/tools/index.ts` `DEFAULT_ESSENTIAL_TOOL_NAMES`、`search_tool_bm25` 工具 |
| 9 | **Rust natives 热路径** | grep/glob/PTY/shell/AST/文件系统隔离不是「加速」，而是**唯一实现** | ✅ 全新（pi 无 Rust） | `crates/`（7 个自研 crate，69,901 行非 vendor Rust） |
| 10 | **swarm-extension**（YAML DAG 多 agent） | 多 agent 编排从「代码里写循环」变成「YAML 声明 DAG」，且它本身就是个 Tier-0 extension | ✅ 全新包 | `packages/swarm-extension/src/swarm/{dag,pipeline,schema,state,executor,render}.ts` |
| 11 | **collab** 实时会话共享 | 把 agent session 变成可分享的多人协作对象（原生 TUI + 浏览器 guest，端到端加密） | ✅ 全新 | `src/collab/{host,guest,crypto,relay-client}.ts`、`packages/wire/`、`packages/collab-web/` |
| 12 | **advisor / watchdog** | 主 agent 会自我说服；挂第二个模型只看增量转录来做「同行评审」 | ✅ 全新 | `src/advisor/{runtime,emission-guard,advise-tool,watchdog}.ts`、`docs/advisor-watchdog.md`(20 KB) |

### 3.2 逐条展开

#### ① snapcompact —— 为什么「把文字画成图」反直觉地有效

**问题**：上下文满了怎么办？主流做法是让 LLM 写摘要（多一次调用、多一次幻觉机会、overflow 时可能连摘要都发不出去）。

**omp 的做法**：把要丢弃的历史**本地确定性地光栅化成点阵字体 PNG**，让 vision 模型直接「读图」回忆。

**为什么反直觉却有效——三个理由（全部有代码内 eval 数据佐证，`packages/snapcompact/src/snapcompact.ts:1-46` 顶部注释原文）**：

1. **计费不对称**。图像 token 的计价方式和像素/字符数不成正比，存在可套利的空档。原文：
   > "Gemini 3.x bills a fixed `media_resolution` budget per image (default 1,120 tokens) regardless of pixels, so the 2048px frame carries more chars at the same bill."

   → Gemini 每张图恒定 1120 token，**与像素无关**，所以把帧放大到 2048px 是纯白嫖。
   反过来 OpenAI 是面积计费，原文：
   > "Patch billing (32px × 1.2, 10k-patch budget at `detail: \"original\"`) is area-proportional, so resolution cannot improve chars/$ — 1568 stays."

2. **不是所有像素密度都能读——存在一个 OCR 悬崖**。原文（Anthropic 线）：
   > "On the tool-result bench, tracking the readable cell beat plain `8on16-bw` (opus-4.8 f1 .806 vs .755) and far beat the prior dense `6x12-dim` (.351, which fell below the OCR ~16px/char floor and abstained)."

   → 密到 `6x12-dim` 时 f1 掉到 **.351**（模型直接摆烂不读），而**加大字间距**的 `11on16-bw` 反而拿到 **.806**。「压得更密」在这里是负收益——这是最反直觉的一条。
   Gemini 侧同理：加行距把 gemini-3.5-flash 从 f1 **.807 → .934**。

3. **零依赖 = 在 overflow 恢复路径上仍然可用**。原文：
   > "The whole pass is local and deterministic — no LLM call, no API key, no latency beyond rendering."

   → 上下文已经爆了、模型调不动的时候，摘要式压缩恰好失效，而 snapcompact 依然能跑。

**其他工程细节**：
- 帧形状按 model id 正则选择（Anthropic `11on16-bw`；Opus 4.7+/Fable/Mythos 用 1932px 贴合 4784 visual-token 上限；Gemini `8on22-bw`@2048；OpenAI `8on22-bw`@1568）
- **中央凹（foveated）归档布局**：`[文本头][HQ×3][密集LQ×N][HQ×3][文本尾]`，超预算时丢最老的密集中段——模仿「最老的细节先褪色」
- 光栅化在 Rust（`renderSnapcompactPng`）
- **它是默认压缩策略**：`packages/coding-agent/src/config/settings-schema.ts:1943` → `default: "snapcompact"`
- 同一套机制复用于 **inline imaging**：system prompt / AGENTS.md / 大 tool result 也能换成 PNG
- 安全顺序：**先脱敏 → 再光栅化 → 最后按 provider 预算裁图**（`sdk.ts:2656-2661`），保证 secret 不会被烙进图像

#### ② hashline —— 行锚定 + 内容指纹的补丁语言

**问题**：`str_replace` 式编辑在长文件/重复片段上不可靠；纯行号编辑在文件被改动后会错位。

**omp 的做法**：一套自定义 DSL，头部 `[PATH#TAG]`，`TAG` = 规范化全文内容 hash 的 **4 位十六进制**，由 `read`/`grep`/`write`/成功的 `edit` 共享 `FileSnapshotStore` 铸造。

`packages/hashline/src/prompt.md` 原文关键约束：
> "`TAG` = 4-hex snapshot tag from your latest `read`/`search`, REQUIRED on every section — no hashless form."
> "They die with the call: every applied edit mints a fresh `#TAG` and renumbers"
> "A hunk anchored on a line you never displayed is REJECTED — re-`read` first."

**解决什么**：把「盲目字符串匹配」换成**乐观并发校验**——stale anchor 直接拒绝，而不是改错地方。

**操作集**：`SWAP N.=M:` / `DEL N.=M` / `INS.PRE|POST|HEAD|TAIL` / `REM` / `MV DEST`，再加 tree-sitter 驱动的块级操作 `SWAP.BLK` / `DEL.BLK` / `INS.BLK.POST`（Markdown 的 `##` 标题被视为块开头，`DEL.BLK` 能整节删除）。

**两个加分工程**：
- 提供 `src/grammar.lark` 供 **constrained decoding**（`src/edit/index.ts` 返回 `{syntax:"lark", definition}`）——从「祈祷模型别写错语法」变成「语法上不可能写错」
- 用 `packages/typescript-edit-benchmark`（6,701 行）做实证调优：TS 源码变异生成 fixture，评测编辑工具成功率

#### ③ catalog —— 把「模型知识」从传输层剥离成独立包

**问题**：现在一个模型在 Kiro、gcli 转、Antigravity、OpenRouter 上各有一个 id，定价/thinking 能力/上下文窗口全靠猜。

**实测数据**（本地点算，`packages/catalog/src/models.json`）：
- **58 个 provider**
- **3,695 个模型条目**
- 文件 1,843,304 字节（1.84 MB）
- 包源码 98,590 行

**三个设计**：
1. **catalog half / auth half 双半边 + 编译期互锁**（`descriptors.ts` 派生 `KnownProvider`，`registry.ts` 完备性断言）→ 加一个 OpenAI 兼容网关 = 1 表项 + 1 def 文件 + 1 行数组
2. **`buildModel()` 是唯一构造入口**，设计意图明写在代码里："Request handlers read fields — they never detect, parse ids, or allocate compat per request."
3. **identity 三件套**：`classify`（家族/版本解析）、`reference`（把 `"[Kiro] claude-opus-4-8"`、`"[gcli转] gemini-3.1-pro-preview [假流]"` 这类转售商 id 用 BFS 候选队列映射回上游继承定价）、`equivalence`（build-time canonical 合并，启发式**故意很窄**）
4. `variant-collapse.ts`(1065 行) 把 effort 后缀双胞胎折叠成一个模型，**门控条件是定价完全一致**——定价不同 = 不同 SKU，合并会让计费撒谎

**AGENTS.md 里的硬规矩**（`AGENTS.md:159`）：「**NEVER edit `packages/catalog/src/models.json` directly.**」它是生成物，改要改 resolver/descriptor，回归测试要打在 resolver 上而不是 bundled JSON 上。

#### ④ auth broker / gateway

**问题**：容器化 agent 需要凭据但不该持有凭据；多账号轮换会互相踩 refresh token。

**四个设计点**（`docs/auth-broker-gateway.md`）：
1. **broker 是 OAuth refresh token 的唯一写者**——客户端快照里 `refresh` 全被替换成 `"__remote__"` 哨兵；本地快照 **AES-256-GCM 加密**，密钥 = `SHA-256(OMP_AUTH_BROKER_TOKEN)`，AAD = broker URL
2. **gateway 没有原始透传路径**——所有入站都解析成 canonical `Context` 再走 `streamSimple()`
3. **`pi-native` 自研 wire**——其他路由的 `wire→Context→wire` 往返会量化损失 service tier / cache 标记 / thinking budget，pi-native 直收 canonical 形状
4. **多账号**：`AuthCredentialEntry = AuthCredential | AuthCredential[]`，按 usage 排序轮换；usage 缓存 TTL 带 **±25% 抖动**——因为 5 条凭据同步扇出 `/usage` 必 429
5. **a/b/c 重试**：解析 → 刷新同账号 → 失效并切兄弟账号；硬约束是**只在用户可见事件发出前**重试
6. `--via=user@host` 通过 `ssh -L` 让 OAuth 回调打到本地浏览器、凭据却写在 broker 主机上

#### ⑤ dialect —— 自持 in-band 工具调用

**问题**：长尾开源模型（GLM/Kimi/MiniMax/Qwen3/DeepSeek…）的原生 function calling 要么不支持、要么不可靠，但它们**训练时见过某种特定的工具调用语法**。

**做法**：关掉 native `tools` 字段，把工具目录用**模型自己训练过的语法**渲进 system prompt，流式回来再解析成 `toolCall` block，并处理「模型编造 `<tool_response>`」的情况。

**实测 11 种方言**（本地 `ls packages/ai/src/dialect/` 点算，每种 `.ts` + `.md` 成对）：
`anthropic` / `deepseek` / `gemini` / `gemma` / `glm` / `harmony` / `hermes` / `kimi` / `minimax` / `qwen3` / `xml`

#### ⑥ mnemosyne（mnemopi）双层记忆

SQLite 本地：`working_memory` → `episodic_memory` 巩固；FTS5 三索引 + 触发器同步；向量存 `memory_embeddings.embedding_json`。

**混合打分**：`dense*w + fts*w + importance*w` × 时间衰减(72h 半衰期) × 时序 boost × 真实性权重 × 降级 tier，最后 **MMR 去冗余**。可选 **polyphonic recall**（vector / graph / fact / temporal 四声部 + RRF 融合）。

**两个值得抄的细节**：
- embedding 输入截断用**头尾各半 + 中缝**——naive `slice(0, max)` 会让所有后期 episode 拿到相同前缀向量，召回全废
- onnxruntime 被关进独立子进程，避免 Bun 关停期 NAPI finalizer 段错误

作用域：`mnemopi.scoping` = `global` / `per-project`（默认）/ `per-project-tagged`。本地 embedding `BAAI/bge-base-en-v1.5`(768d) 或 `intfloat/multilingual-e5-large`(1024d)。

#### ⑦ TTSR —— Time Traveling Stream Rules

**问题**：规则（「不许 `git push --force`」「不许改 lockfile」）写在 system prompt 里，模型照样违反，而你只能在事后发现。

**做法**（`docs/ttsr-injection-lifecycle.md`）：
1. `turn_start` → `ttsrManager.resetBuffer()`
2. 流式期间实时匹配 `text_delta` / `thinking_delta` / `toolcall_delta`：regex 或 **ast-grep 结构匹配**。对 `edit`/`write` 这类暴露 `matcherDigest` 的工具，用**重建的源码快照**做 `checkAstSnapshot`（native `astMatch` 引擎、内存匹配、Smart strictness）——即匹配「这次编辑之后代码会长成什么样」而不是「模型此刻写了什么字符」
3. 命中且规则允许打断 → **立即 `agent.abort()`**（不等扩展回调）
4. 重试：`contextMode: "discard"` 时用 `agent.replaceMessages(...slice(0, targetAssistantIndex))` **丢弃被打断的半截输出**，注入 `ttsr-interrupt.md` 生成的系统中断消息，`agent.continue()` 重跑本轮

**非打断命中**分两路：tool 源命中桶入 `#perToolTtsrInjections`，工具真出结果时把提醒**前置**为 tool result 的首个 text block；text/thinking 源命中队列化，在成功的 assistant 消息后作为 follow-up 注入。

注入抑制状态以 `ttsr_injection` entry **跨 resume 持久化**。

#### ⑧ 工具两级加载 + BM25 发现

**问题**：30 个内置工具 + MCP 工具全塞进 system prompt，既吃 token 又降低模型的工具选择准确率。

**做法**（`packages/coding-agent/src/tools/index.ts`）：初始只暴露 **6 个 essential 工具**——代码里的常量原文：

```ts
export const DEFAULT_ESSENTIAL_TOOL_NAMES: readonly string[] = [
	"read", "bash", "edit", "write", "glob", "eval",
] as const;
```

其余 discoverable 工具由模型自己通过 `search_tool_bm25` 检索并按需激活。

**一个 load-bearing 的坑（代码注释里写明）**：
> "a named tool_choice (e.g. the eager `todo` prelude) must reference a tool present in the request, or the provider rejects it with 400."

→ 所以过滤器保留了 `forceActive` 逃生舱。

**MCP 侧同款机制**：`mcp.discoveryMode`（默认 false）开启后 MCP 工具默认隐藏，仅经 tool-discovery 暴露，`mcp.discoveryDefaultServers` 白名单常驻。

**本地点算的工具清单**（`src/tools/index.ts`）：
- `BUILTIN_TOOLS` = **30 个**：read / bash / edit / ast_grep / ast_edit / ask / debug / eval / ssh / github / glob / grep / lsp / inspect_image / browser / checkpoint / rewind / task / job / irc / todo / web_search / search_tool_bm25 / write / memory_edit / retain / recall / reflect / learn / manage_skill
- `HIDDEN_TOOLS` = **5 个**：yield / report_finding / report_tool_issue / resolve / goal

> 注：上游 README 自称「32 built-in tools」（v17.2.2），本地 v16.3.12 点算为 30 + 5 隐藏。版本差导致，非矛盾。

#### ⑨ Rust natives 热路径

**准入规则是双向的**（`docs/porting-to-natives.md`），这点很少见。准入条件：热路径在渲染循环/紧 UI 更新/大批量操作、JS 分配占主导、已有 JS baseline 可并排跑基准、CPU-bound 或可放到 libuv/Tokio 的 I/O。

**同时文档记录了「移回 JS」的案例**：`sanitizeText` 从 `text.rs` 移出，回到纯 JS 的 `packages/utils/src/sanitize-text.ts`，理由两条——JS 版在实测负载上 competitive，且保留 Rust 副本会强迫每个调用方（包括 `pi-utils` 这样的基础包）都拉进 natives 依赖。规则原文：「**如果 native 更慢，不要切调用点。**」

**四类真正被 Rust 化的工作**：
1. **进程替代**——grep / rg / coreutils / bash 全部进程内化。基准 `packages/natives/bench/grep.ts` 是原生 `grep()` vs `Bun.spawn(["rg", …])` 的对照，带 2× 并发场景（并发下 spawn 成本占主导）。顺带解决三个正确性问题：输出能落到命令自己的重定向 fd、相对路径按 shell 的 cwd 解析、取消可协作式生效
2. **系统调用密集**——macOS `getattrlistbulk` / Linux `SYS_getdents64` / Windows `NtQueryDirectoryFile`，而不是 `ignore::WalkBuilder`
3. **CPU-bound 转换**——tiktoken（rayon 并行，「避免 per-element napi crossing」）、syntect、tree-sitter（55 个 grammar）、SIXEL、HTML→Markdown
4. **TUI 热路径**——ANSI 宽度/截断/换行直接在 UTF-16 slice 上操作；Kitty 键盘协议用 `phf` 编译期完美哈希做 O(1) 查表

**有实测依据的反直觉决策**：macOS 上**故意不**向 `getattrlistbulk` 请求 size+mtime——代码注释 "measurably slows the bulk scan (~+50% walk time on APFS)"，有 `crates/pi-walker/tests/perf.rs` 基准佐证。

**`pi-iso`——写时复制工作区隔离**（不是安全沙箱）：8 种 backend（APFS clonefile / btrfs / zfs / FICLONE reflink / overlayfs / ProjFS / Windows block-clone / rcopy 兜底），给 subagent 一个可写的 `merged` 视图而不深拷贝。`task` 工具的 isolated 子代理就靠 `isoResolve/isoStart/isoStop`。

#### ⑩ swarm-extension —— YAML DAG 多 agent

`packages/swarm-extension/README.md` 原文：
> "Multi-agent orchestration for oh-my-pi. Define agent workflows in YAML — pipelines, parallel fan-outs, sequential chains, or any DAG — and run them unattended until completion."
> "The orchestrator manages lifecycle and ordering; agents communicate through the shared workspace filesystem."

**解决什么**：把多 agent 编排从「在代码里写 orchestration 循环」降级成「写一个 YAML」，且无人值守可跑到完成（standalone runner **无超时**）。

**架构意义大于功能意义**：它同时是 **Tier-0 extension** 和**独立 CLI `omp-swarm`**——是全仓唯一用 `workspace:*` + `peerDependencies` 而非 `catalog:` 协议的包，因为它要作为**外部** extension 被宿主加载。这是「扩展面表达力上限」的活证据。

模块：`src/swarm/{dag,pipeline,schema,state,executor,render}.ts`（包总计 1,179 行 src）。

#### ⑪ collab —— 实时会话共享

**做什么**（`docs/collab.md` 原文）：
> "`/collab` shares your running session with other omp instances in real time. Guests render the **same session natively in their own TUI** — streaming assistant text, tool-call cards, footer state (cwd, model, context %, cost), ctrl+o expansion, `/dump` — **no terminal mirroring**."

**关键点**：不是 tmux/asciinema 式的终端镜像，而是**事件级复制**——guest 用自己的 TUI 重新渲染同一个 session，且可以 prompt 和打断 agent（host 机器跑 agent 和所有工具）。

**支撑设计**：
- `packages/wire`（444 行、**零依赖**的协议常量包）定义 `WireMessage`/`SessionEntry`/`AgentEvent`/`GuestFrame`/`HostFrame`、`COLLAB_PROTO=3`、AES-GCM 房间密钥常量
- 端到端加密：房间密钥在 URL **fragment** 里（`my.omp.sh/#<roomId>.<key>`），relay 看不到明文
- `packages/collab-web`（8,106 行）是浏览器 guest；`gen:tool-views` 生成 HTML 导出用的工具渲染器
- 链接形态支持 8 种解析路径（自建 relay、`ws://localhost` 本地、web UI 与 relay 分离部署…），递归解析

#### ⑫ advisor / watchdog —— 挂第二个模型做同行评审

**问题**：主 agent 会自我说服（「我已经修好了」），而人不在旁边。

**做法**（`docs/advisor-watchdog.md`）：可选的第二个模型挂在 session 上，**每个主 turn 结束后只看增量转录**，用自己的工具审视工作区，通过 `advise` 把意见注入主 session。

**隔离设计**：独立 `Agent` 实例 + 独立 `ToolSession`（id 后缀 `-advisor`），**不共享**主 agent 的文件快照 / seen-lines / 冲突状态 / 摘要缓存 / edit·yield 能力。默认工具池只读 `read`/`grep`/`glob` + `advise`。

**三档 severity**：`nit`（非打断）/ `concern` / `blocker`（**打断式 steering**）。渲染为 `<advisory severity="..." guidance="weigh, don't blindly obey">`——主 agent 的 system prompt 从不提及 advisory，这个 tag 是唯一线索。`advisor.immuneTurns`（默认 3）限制打断频率。

**最值得抄的一段：`AdvisorEmissionGuard`**（`src/advisor/emission-guard.ts`）在 `enqueueAdvice` 边界用代码强制执行「每次更新最多一条 advise、绝不重复」：
1. 归一化（小写、NFKC、非字母数字折叠成单空格、trim）——`"Stop."` / `"*Stop*"` / `"  stop  "` 都归到 `stop`
2. **内容空洞短语过滤**（`stop`/`done`/`complete`/`lgtm`/`nothing to add` 静默丢弃——**沉默才是「无意见」的正确表达**）
3. 全 session 精确文本去重（FIFO 环，默认 4096）
4. 每 advisor `prompt()` 周期最多一条

**抑制对模型不可见**（`AdviseTool` 仍返回 `Recorded.`），以免模型换个说法绕过去重。

**已知刀口**：advisor 的工具池**不经过 approval wrapper**——`WATCHDOG.yml` 授予 mutating 工具时直接可用。这是文档明确记录的信任边界。

### 3.3 未在题目列表里但同样重要的三项（建议在演讲里提一句）

| 创新 | 解决什么问题 | 证据 |
|---|---|---|
| **Capability Provider 注册表** | 把「配置发现」从散落各处的 `if (exists('.claude/...'))` 提升为带优先级仲裁、可诊断（`_shadowed`）、可按 provider 关停的注册表；一次性兼容 10 家 agent 的磁盘约定（`.omp`/`.claude`/`.codex`/`.gemini`/`.cursor`/`.windsurf`/`.cline`/`.opencode`/`.github`/`.vscode`），**15 类抽象能力** | `src/capability/`、`src/discovery/helpers.ts` 的 `SOURCE_PATHS` |
| **RPC 反向子协议**（host tools / host URI schemes） | 让「agent 在容器里、能力在宿主上」成为一等公民——宿主用 `set_host_tools` 反向注册工具，agent 调用时弹回宿主执行 | `docs/rpc.md`、`deploy/yf-worker/` |
| **append-only session 树 + 可变 leaf 指针** | 压缩不再「视觉重启对话」；branch 只移 leaf 不写 entry；13 种 entry 类型 + 4 个 schema 版本迁移 | `docs/session.md`、`src/session/session-context.ts` |

---

## 4. 规模对比数据（可直接上表格）

> 全部由本研究在本地 `v16.3.12` 重新点算（命令：`find … | xargs wc -l`）。

### 4.1 总量卡片（适合做 PPT 大字）

| 维度 | 数值 |
|---|---|
| TypeScript/TSX **源码**（`packages/*/src`，排除测试） | **630,753 行** |
| TypeScript/TSX **全量**（含测试、生成代码） | **1,039,493 行** |
| 测试代码 | **388,486 行** / **1,568 个测试文件** |
| Rust **自研**（`crates/pi-*`，排除 vendor） | **69,901 行** |
| Rust **含 vendor**（brush-core + 12 个 uu-*） | **138,157 行** |
| Bun workspace 包 | **16 个** |
| Rust crate（自研） | **7 个** + vendor |
| 设计文档 | **121 篇 Markdown / 27,073 行** |
| Prompt 文件（`*/prompts/*.md`） | **226 个** |
| 内置工具 | **30 个**（+5 隐藏） |
| 模型目录 | **58 provider / 3,695 模型 / 1.84 MB** |
| 版本号 | TS 与 Rust **共用同一个版本号** `16.3.12` |

### 4.2 TS 包明细（src 行数，排除测试）

| 包 | 目录 | src 行数 | 相对 pi 是否全新 | 职责一句话 |
|---|---|---:|:---:|---|
| `@oh-my-pi/pi-coding-agent` | `coding-agent` | **336,468** | 否（体量约 5×） | 产品主体：CLI/TUI/session 树/30 工具/MCP/LSP/扩展/collab/advisor |
| `@oh-my-pi/pi-catalog` | `catalog` | **98,590** | ✅ 全新 | 模型目录（含 6 家转售商的生成式 protobuf 客户端） |
| `@oh-my-pi/pi-ai` | `ai` | **85,793** | 否（膨胀约 2×，零官方 SDK） | 统一 LLM API / 14 种 wire / auth broker / dialect |
| `@oh-my-pi/pi-mnemopi` | `mnemopi` | **19,324** | ✅ 全新 | Mnemosyne 双层记忆引擎 |
| `@oh-my-pi/pi-tui` | `tui` | **22,525** | 否（渲染器重写） | append-only 提交式差分渲染器 |
| `@oh-my-pi/pi-utils` | `utils` | **19,645** | 否（大幅扩张） | CLI 框架 / logger / dirs / Handlebars |
| `@oh-my-pi/pi-agent-core` | `agent` | **13,052** | 否（compaction/telemetry 新增） | 通用 agent 执行引擎 |
| `@oh-my-pi/omp-stats` | `stats` | **10,036** | ✅ 全新 | 本地可观测性 dashboard |
| `@oh-my-pi/collab-web` | `collab-web` | **8,106** | ✅ 全新 | collab 浏览器 guest |
| `@oh-my-pi/typescript-edit-benchmark` | — | **6,701** | ✅ 全新 | 编辑工具成功率评测 |
| `@oh-my-pi/hashline` | `hashline` | **5,693** | ✅ 全新 | 行锚定补丁语言（零 workspace 依赖） |
| `@oh-my-pi/snapcompact` | `snapcompact` | **1,974** | ✅ 全新 | 位图帧上下文压缩 |
| `@oh-my-pi/pi-natives` | `natives` | **0**（src 为空，全是生成物） | 否（重写） | Rust N-API 绑定的 TS 侧 |
| `@oh-my-pi/swarm-extension` | `swarm-extension` | **1,179** | ✅ 全新 | YAML DAG 多 agent 编排 |
| `@oh-my-pi/terminal-bench` | — | **1,223** | ✅ 全新 | Terminal-Bench 2 跑分器 |
| `@oh-my-pi/pi-wire` | `wire` | **444** | ✅ 全新 | 零依赖协议常量包 |

**9/16 个包是相对 pi 全新的。**

### 4.3 Rust crate 明细（`.rs` 行数）

| Crate | 行数 | 职责 |
|---|---:|---|
| `pi-shell` | **38,059**（其中 minimizer 约 30k） | 嵌入式 bash（brush fork）+ 进程树管理 + 输出 minimizer + coreutils builtin 宿主 |
| `pi-natives` | **16,417** | 唯一的 napi-rs cdylib，聚合全部能力 |
| `pi-walker` | **6,092** | 并行 FS 遍历 + 进程内扫描缓存（自研 gitignore 匹配） |
| `pi-iso` | **4,052** | 跨平台写时复制工作区隔离 PAL（8 种 backend） |
| `pi-ast` | **3,269** | tree-sitter 摘要 / 块边界（55 个 grammar crate） |
| `pi-uu-grep` | **2,458** | 用 ripgrep 库从零实现的进程内 `grep`/`rg` builtin |
| `pi-uutils-ctx` | **389** | thread-local stdio/cwd/env/cancel 垫片 |
| `crates/vendor/*` | **67,421** | brush-core / brush-builtins + 12 个 `uu_*` |

TS 侧公开面：**48 个函数 + 5 个 class + 10 个 enum**，`index.d.ts` 1,615 行，全仓 41 个 TS 文件 import。

### 4.4 文档规模

| 目录 | 篇数 |
|---|---:|
| `docs/*.md`（顶层） | **73** |
| `docs/tools/*.md` | **33** |
| `docs/toolconv/*.md` | **9** |
| `docs/skills/*.md` | **6** |
| **合计** | **121 篇 / 27,073 行** |

单篇最大：`docs/environment-variables.md`（65 KB）、`docs/settings.md`（38.7 KB）、`docs/models.md`（32.5 KB）、`docs/compaction.md`（26.2 KB）。

### 4.5 与 pi 的公开体量对照（联网数据，2026-08-01）

| | `earendil-works/pi`（原 badlogic/pi-mono） | `can1357/oh-my-pi` |
|---|---:|---:|
| GitHub star | **81,525** | **20,918** |
| fork | **10,065** | **1,985** |
| 仓库创建 | 2025-08-09 | 2025-12-31 |
| npm 主包 | `@earendil-works/pi-coding-agent` **v0.83.0** | `@oh-my-pi/pi-coding-agent` **v17.2.2** |
| npm 周下载（2026-07-24→30） | **1,599,276** | **77,961** |
| 已发版本数（npm） | — | **569** |

> **注意口径**：pi 的 star/下载量领先一个数量级，但 pi 是 OpenClaw 等下游产品的引擎（分发被放大）；omp 是终端用户产品。两者不是同一赛道的直接竞品，**不要在 PPT 上做「谁赢了」的对比**，只做「体量参照」。

---

## 5. 联网核实：can1357/oh-my-pi 的公开信息

**核实时间：2026-08-01。数据源：GitHub REST API（`gh api`）与 npm registry API。**

| 项 | 值 | 出处 |
|---|---|---|
| 仓库是否公开 | **是，公开** | `https://github.com/can1357/oh-my-pi` |
| 是否 GitHub 意义的 fork | **不是**（`fork: false`，`parent: none`、`source: none`）——是**代码级 fork、仓库级独立** | `GET /repos/can1357/oh-my-pi` |
| 许可证 | **MIT**（`license.spdx_id = "MIT"`），LICENSE 同时保留 Mario Zechner (2025) 与 Can Bölük (2025-2026) 双版权 | API + 本地 `LICENSE` |
| 描述 | `⌥  AI Coding agent for the terminal — hash-anchored edits, optimized tool harness, LSP, Python, browser, subagents, and more` | API |
| 主页 | `https://omp.sh` | API |
| Star | **20,918** | API |
| Fork | **1,985** | API |
| Watchers (subscribers) | **62** | API |
| Open issues | **879** | API |
| 贡献者数 | **329** | `GET /contributors?per_page=1` 分页末页 = 329 |
| 仓库创建时间 | **2025-12-31T14:01:28Z** | API |
| 最近 push | **2026-08-01T00:11:43Z**（研究当天仍在活跃） | API |
| 最新 release | **v17.2.2**，发布于 **2026-07-31T19:36:09Z** | `GET /releases/latest` |
| 累计 release | **547** | `GET /releases?per_page=1` 末页 |
| 累计 tag | **790** | `GET /tags?per_page=1` 末页 |
| 主语言 | TypeScript | API |
| Topics | ai-agent, ai-coding-agent, anthropic, bun, claude, cli, coding-assistant, llm, mcp, multi-provider, openai, rust, terminal, tui, typescript | API |
| npm 包 | `@oh-my-pi/pi-coding-agent`，latest **17.2.2**（2026-07-31T19:39:52Z），首发 2026-01-02T21:58:02Z，**569 个版本**，MIT | `https://registry.npmjs.org/@oh-my-pi%2Fpi-coding-agent` |
| npm 周下载 | **77,961**（2026-07-24→2026-07-30） | `https://api.npmjs.org/downloads/point/last-week/@oh-my-pi/pi-coding-agent` |
| npm 月下载 | **280,636**（2026-07-01→07-30） | `https://api.npmjs.org/downloads/point/last-month/@oh-my-pi/pi-coding-agent` |
| 开发速度 | 近 7 天 **1,159 commit**（≈165/天）；2026-07 发了 **51 个 release**（≈1.7/天） | `GET /commits?since=…`、`GET /releases` |

**README 自称的能力指标**（`https://github.com/can1357/oh-my-pi/blob/main/README.md`，对应 v17.2.2）：
- 40+ LLM providers、32 built-in tools
- 14 LSP operations、28 DAP operations
- ~55,000 lines of Rust core
- 真调试器集成（lldb / dlv / debugpy）、Python/Bun kernel、并行 subagent、collab 分享链接 + 二维码
- 25 web search backends、Puppeteer 真浏览器自动化、GitHub as a filesystem

> **口径提醒**：README 说「~55k lines of Rust core」，而本地 v16.3.12 点算自研 Rust（排除 vendor、排除 tests/benches）是 **69,901 行**。版本不同 + 统计口径不同（是否含 vendor / tests / 生成代码）都可能造成差异。**上 PPT 建议用「约 7 万行自研 Rust（本地 v16.3.12 实测）」并注明口径**，或直接引用 README 的「~55k」并注明是官方口径。

**社区规模判断**：329 位贡献者 + 879 个 open issue + 2 万 star + 每周 7.8 万 npm 下载——这不是个人玩具项目，是有真实社区的活跃开源产品；但相对 pi（8.1 万 star、每周 160 万下载）仍是小一号的生态。

---

## 6. 对「打造自己的 agent」的启发

### 6.1 强烈建议借鉴的通用模式（跟规模无关，小项目也适用）

| # | 模式 | 为什么通用 | omp 的实例 |
|---|---|---|---|
| 1 | **把「定制成本」变成一等公民的度量** | 不问「这个改动大不大」，而问「这个改动落在哪一 tier」。**一个能用 Tier-0 表达的丑陋方案，胜过一个需要 Tier-2 的优雅方案。** | FORK.md 的 tier 模型 |
| 2 | **扩展点的价值 = 它把多少 Tier-2 需求降级为 Tier-0** | 设计扩展点时的唯一评价标准。反过来说，「加了很多 hook 但没人能只靠 hook 做完一件真事」= 扩展点失败 | `context` 事件能重写整个消息流；`before_provider_request` 能替换请求负载；`session.compacting` 能完全接管压缩 |
| 3 | **分歧必须可 grep、可验证、可归零** | `seam marker`(可见) + `账本`(有主) + `漂移测试`(可验证) + `上游化 PR`(可归零)，四者缺一，fork 就退化成「每次同步都是一次考古」 | `grep -rn "omp-fork("` |
| 4 | **prompt 一律放 `.md` 文件，代码里绝不拼字符串** | prompt 是产品的一部分，应该可 diff、可 review、可被非工程师改。且 `.md` 用 text loader 导入后，**改 prompt 不需要重新构建** | `AGENTS.md:40`「Prompts: never build prompts in code」；226 个 prompt md；`bunfig.toml` 把 `.md` 注册为 text loader |
| 5 | **eval 数字写进代码注释** | 让「为什么选这个参数」和参数本身住在一起。半年后没人记得为什么是 1932px，除非注释里写着 f1=.806 vs .755 | `packages/snapcompact/src/snapcompact.ts:1-46` |
| 6 | **性能优化必须双向论证** | 「移到 Rust」的文档同时记录「移回 JS」的案例和规则「如果 native 更慢，不要切调用点」。没有退出机制的优化会变成技术债 | `docs/porting-to-natives.md` + `sanitizeText` 回退案例 |
| 7 | **把 provider 缓存成本纳入协议设计** | 极罕见的做法。`resolve` 工具的软强制机制只发一次提醒、**不动 `tool_choice`**，理由写在代码里：旧设计每周期 bust 两次 provider message cache | `src/tools/resolve.ts` + `SoftToolRequirement` |
| 8 | **压缩/摘要之外的第三条路：确定性本地变换** | snapcompact 的真正启发不是「画成图」，而是「**先问有没有不调 LLM 的做法**」。零 LLM 调用 = 在 overflow 恢复路径上仍可用 | `packages/snapcompact` |
| 9 | **编辑工具要有并发校验，不能盲改** | 内容指纹（4-hex tag）+ stale anchor 直接拒绝，比「string replace 找不到就报错」强一个数量级 | `packages/hashline` |
| 10 | **给约束加一个执行边界，而不是只写进 prompt** | `AdvisorEmissionGuard` 在代码层强制「最多一条、绝不重复」，且抑制对模型不可见——避免模型换个说法绕过去。TTSR 同理：规则在流式层执行，不指望模型自觉 | `src/advisor/emission-guard.ts`、TTSR |
| 11 | **「沉默」要能被表达** | advisor 把 `stop`/`done`/`lgtm`/`nothing to add` 静默丢弃——**沉默才是「无意见」的正确表达**。很多 agent 系统强迫每一步都输出点什么，是噪声之源 | 同上 |
| 12 | **配置发现要有优先级仲裁 + 可诊断的遮蔽** | 被遮蔽项打 `_shadowed=true` 保留在 `all` 里供诊断。这解决了「我明明写了配置为什么不生效」这个所有 agent 工具的头号 FAQ | `src/capability/index.ts` |
| 13 | **工具目录按需加载** | 6 个 essential + BM25 检索激活。工具越多，这个模式收益越大 | `DEFAULT_ESSENTIAL_TOOL_NAMES` |
| 14 | **反向工具协议（host tools）** | 「agent 在容器里、能力在宿主上」是所有生产部署都会遇到的形态。做成一等公民而不是 hack | `docs/rpc.md` 的 `set_host_tools` |

### 6.2 建议先看看再抄的（收益/成本比高度依赖场景）

| 项 | 判断 |
|---|---|
| **catalog 独立包（3695 模型/1.84MB）** | 只有当你要同时接**多个转售商/网关**、且要精确计费时才值。只接 3 家官方 provider 的话，一个 200 行的常量表就够。**但「模型知识与传输层分离」这个分层思想值得抄。** |
| **11 种 dialect** | 只有当你必须支持长尾开源模型/自建推理端点时才值。用商业 API 的话原生 tool calling 已经够用。**但「原生工具调用不可靠时可以降级到 in-band」这个逃生舱值得留。** |
| **Rust natives** | 如果你的 agent 不做大规模 grep / 不内嵌 shell / 不做 TUI 差分渲染，收益远小于成本（跨平台构建、崩溃恢复边界、napi panic 处理、Windows 线程预探测…全是长尾复杂度）。**但「进程内化外部命令」的三个正确性收益（重定向 fd / cwd 解析 / 协作式取消）值得单独评估。** |
| **advisor 第二模型** | 双倍成本。适合无人值守长跑，不适合交互式。 |

### 6.3 我判断属于过度工程的部分（讲这段会很有记忆点）

> 前提声明：这些设计在 omp 自己的场景（无人值守 red-team worker、支持 58 家 provider、日均 165 commit）里**都是合理的**。「过度工程」是指**对绝大多数自建 agent 而言**收益不抵成本。

| # | 判断 | 理由与证据 |
|---|---|---|
| 1 | **`agent-session.ts` 单文件 16,151 行** | 这是「turn loop 语义 = Tier 2」的代价被内化成了单点复杂度。任何人想改 turn loop 都要先读一个 1.6 万行的文件。**架构上把它列为 Tier 2 是承认，不是解决。** |
| 2 | **minimizer 子系统约 30,000 行 Rust，且默认 inert** | 24 个 Rust filter 模块（git 2842 行、jvm 3117 行、docker 1702 行…）+ 67 个 TOML，只为压缩 shell 输出，而且**默认不生效，必须显式 opt-in**。同样的效果 90% 可以用「截断 + 存 artifact + 给个链接」达成——而 omp **本来就有** artifact 机制。 |
| 3 | **两套 grep 实现并存**（`pi-uu-grep` 与 `pi-natives/src/grep.rs`，无共享代码） | 语义分叉（POSIX grep 语义 vs 结构化 API）是刻意的、有理由的，但代价是同一份 ripgrep 库被消费两次、两套取消机制、两套退出契约。`pi-uu-grep` 还伪报 `version = "15.1.0"` 骗探测。 |
| 4 | **hooks 与 extensions 两套并存** | `docs/hooks.md` 说默认 CLI 运行时**只初始化 extension runner**，`--hook` 是 `--extension` 的别名，hook 工厂被当 extension 模块加载。`src/extensibility/hooks/*` 是**保留的 legacy 子系统**。新项目直接做一套。 |
| 5 | **plan mode 同时有内建实现和 extension 实现** | 作为「扩展面表达力上限」的活证据很漂亮，但作为产品是两份要同步维护的实现（`src/plan-mode/` + `examples/extensions/plan-mode.ts` 549 行）。 |
| 6 | **388,486 行测试 / 1,568 个测试文件** | 相对 630,753 行源码，测试量是 0.62×。这个比例本身健康，但配合 `AGENTS.md` 里长达 15 条的测试禁令（禁 `mock.module()`、禁 source-grep、禁占位测试、禁跨抽象层重复覆盖…）说明**测试质量退化过、且退化成本很高**。小项目直接从第一天定这些规矩，比事后写 15 条禁令便宜。 |
| 7 | **文档 121 篇 27,073 行，且已出现代码/文档漂移** | 已确认的漂移至少 5 处（`fs-scan-cache-architecture.md` 说实现在 `crates/pi-natives/src/fs_cache.rs`，实际已移到 `crates/pi-walker/src/cache.rs`；cache key 说 5 个维度实际 13 个字段全参与；说用 `ignore::WalkBuilder` 实际是平台原生 syscall…）。**文档越多，漂移越贵。** |
| 8 | **`disabledProviders` 同时管 discovery provider 和 model provider** | 命名空间碰撞，`docs/context-files.md` 自己点出来了。是「概念太多导致命名撞车」的典型症状。 |

**一句话总结这一节（适合做 PPT 结论）**：

> **omp 值得抄的是「方法论」（tier 成本模型、扩展点评价标准、eval 写进注释、约束要有执行边界），不是「零件」（catalog / natives / minimizer）。零件是它的场景逼出来的，方法论才是可迁移的。**

---

## 7. 待核实 / 已知分歧清单

| # | 分歧 | 说明 | 处理建议 |
|---|---|---|---|
| 1 | Rust 行数：README「~55k」vs 本地实测「69,901」 | 版本差（README 对应 v17.2.2，本地 v16.3.12）+ 口径差（是否含 vendor/tests/生成代码）。本地 `crates/pi-*` 排除 `tests/`/`benches/` 后 = 69,901；含 vendor = 138,157 | PPT 上写「约 7 万行自研 Rust（本地 v16.3.12 实测，排除 vendor）」并注明口径 |
| 2 | 内置工具数：README「32」vs 本地实测「30 + 5 隐藏」 | v16.3.12 → v17.2.2 之间新增了工具 | 说「30+ 内置工具（v16.3.12 实测）」或直接引 README 的 32 并注明版本 |
| 3 | `04-omp-ts-packages.md` 说「docs/ 78 篇」 | 本研究点算 `docs/*.md` 顶层 = **73** 篇，全部子目录合计 = **121** 篇。78 可能是把子目录条目算进去了 | 用本研究的 73 / 121 |
| 4 | 「pi-mono 现 @earendil-works」 | GitHub API 显示 `badlogic/pi-mono` 已重定向到 `earendil-works/pi`；npm 同时存在 `@mariozechner/pi-coding-agent`（周下载 578,720）和 `@earendil-works/pi-coding-agent` v0.83.0（周下载 1,599,276，首发 2026-05-07） | 迁移的确切时间点与原因**未核实**，PPT 上只说「pi 现在的仓库是 `earendil-works/pi`」 |
| 5 | `can1357/oh-my-pi` 的 contributor = 329 | 用 `GET /contributors?per_page=1` 的分页末页数推出，含 bot（如 dependabot）与 AI 提交账号的可能性未排除 | 说「300+ 贡献者」更稳 |
| 6 | GitHub compare API 的 `files_changed` = 300 | GitHub compare 端点单次最多返回 300 个文件，这是**截断值不是真值**。FORK.md 说的「~800+ files change between patch releases」未能独立核实 | **不要在 PPT 上用这个 300** |
| 7 | 上游 tag 可变 | FORK.md:114-118 记录实测 `v15.10.8` 从 `74d4f009` 被 force-move 到 `c69ba70a`。这是 FORK.md 作者的观察记录，本研究**未独立复现** | 引用时注明「据 FORK.md 记录」 |
| 8 | 「omp 是 pi 的 fork」的性质 | GitHub API `fork: false`，即它不是通过 GitHub Fork 按钮创建的。但 LICENSE 双版权 + README 自述 + 包名 `pi-*` 前缀 + `docs/porting-from-pi-mono.md`（21.8 KB）都确证代码血缘 | 表述用「代码级深度 fork，仓库层面独立」，不要说「GitHub fork」 |
| 9 | omp.sh 官网 | WebFetch 返回 403，未能核实站点内容 | 只引用 GitHub README |

---

## 8. 最适合上 PPT 的 5 条硬事实

1. **tier 成本模型的定义（FORK.md:17-19 原文）**：
   > "Every change has a **tier** = how much it costs to carry across an upstream sync. The cost of this fork is dominated by how much lands in Tier 2. **Push everything you can down to Tier 0.**"
   —— **它不是按「改动大小」分层，而是按「与上游变更的正交性」分层**。实证：1362 行含熔断器的 MCP manager 因为住在自有目录，同步成本为零；3 行的 turn-loop patch 每次 sync 都要人工重解。

2. **上游速度实测（GitHub API，2026-08-01）**：`can1357/oh-my-pi` 近 7 天 **1,159 个 commit（≈165/天）**，2026 年 7 月发布 **51 个 release**；本地 fork 停在 `v16.3.12`（2026-07-08），到最新 `v17.2.2`（2026-07-31）**落后 3,920 个 commit——只用了 23 天**。

3. **snapcompact 的反直觉 eval（代码注释原文）**：把历史画成点阵 PNG 让 vision 模型读图，**零 LLM 调用、零 API key、零网络**。而「压得更密」是负收益——密集 `6x12-dim` 在 opus-4.8 上 f1 只有 **.351**（低于 OCR ~16px/char 下限，模型直接摆烂），加大字间距的 `11on16-bw` 拿到 **.806**。Gemini 因为每图恒定 1120 token 计费**与像素无关**，所以帧放大到 2048px 是纯白嫖。

4. **规模对照（本地 v16.3.12 实测）**：**630,753 行 TS 源码 + 388,486 行测试 + 69,901 行自研 Rust + 121 篇设计文档（27,073 行）+ 226 个 prompt 文件**；16 个包中 **9 个是相对 pi 全新的**；模型目录 **58 provider / 3,695 模型 / 1.84 MB**。

5. **公开信息核实（2026-08-01）**：`can1357/oh-my-pi` 公开、**MIT**、**20,918 star / 1,985 fork / 329 贡献者 / 879 open issue**，最新 release **v17.2.2（2026-07-31）**，累计 **547 个 release**；npm `@oh-my-pi/pi-coding-agent` 周下载 **77,961**。它**不是 GitHub 意义上的 fork**（`fork: false`），而是代码级深度 fork——LICENSE 同时保留 Mario Zechner (2025) 与 Can Bölük (2025-2026) 双版权。

---

## 9. 引用来源

**本地素材**
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/FORK.md`（tier 模型全文，175 行）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/AGENTS.md`（开发规约，259 行）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/LICENSE`（双版权）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/packages/snapcompact/src/snapcompact.ts:1-46`（eval 数据）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/packages/hashline/src/prompt.md`（补丁语言规范）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/packages/coding-agent/src/tools/index.ts`（工具清单 + essential 常量）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/packages/coding-agent/src/config/settings-schema.ts:1943`（`default: "snapcompact"`）
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/packages/swarm-extension/README.md`
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/docs/collab.md`
- `/Users/nongjiawu/playground/research/ohmypi/oh-my-pi/docs/`（121 篇）

**已有深度分析（本研究复用其结论）**
- `/Users/nongjiawu/playground/research/pi/analysis/raw/04-omp-ts-packages.md`
- `/Users/nongjiawu/playground/research/pi/analysis/raw/05-omp-rust-natives.md`
- `/Users/nongjiawu/playground/research/pi/analysis/raw/06-omp-extensibility.md`
- `/Users/nongjiawu/playground/research/pi/analysis/raw/06b-omp-mcp-subsystem.md`

**联网来源（2026-08-01 核实）**
- [github.com/can1357/oh-my-pi](https://github.com/can1357/oh-my-pi)
- [oh-my-pi README](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- [oh-my-pi Releases](https://github.com/can1357/oh-my-pi/releases)
- GitHub REST API：`GET /repos/can1357/oh-my-pi`、`/releases/latest`、`/releases`、`/tags`、`/commits`、`/contributors`、`/compare/v16.3.12...v17.2.2`
- [npm @oh-my-pi/pi-coding-agent](https://www.npmjs.com/package/@oh-my-pi/pi-coding-agent) + `registry.npmjs.org` / `api.npmjs.org` 下载量端点
- [github.com/badlogic](https://github.com/badlogic)（pi 作者 Mario Zechner）
- GitHub REST API：`GET /repos/badlogic/pi-mono`（重定向至 `earendil-works/pi`）
- [npm @mariozechner/pi-coding-agent](https://www.npmjs.com/package/@mariozechner/pi-coding-agent)
