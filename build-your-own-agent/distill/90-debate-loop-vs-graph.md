# 新页素材 ·「Loop Engineering 派 vs Graph Engineering 派之争」

> 用途：为 deck 补一页**真正的方法论之争**。现有 P15（s10-loop）与 P16（s11-graph）把两者讲成互补，
> 本页要把它们讲成**对立的两套工程假设**，并给出讲者的立场。
> 建议插在 P16 之后（即现有「向后是一棵树，向前是一张图」之后、P18 Context Engineering 之前）。
>
> **取证规则**：每条主张后附一手来源 URL；无法回溯到一手来源的一律标「**待核实**」，不得上页。
> 已比对 `NOTES.md` 第三节「被打回、故意没上页」清单 —— 本文**未使用**其中任何一条。
> 已比对 R05 §8 待核实清单 —— 12-factor-agents 的 star 数 / 更新时间**未使用**；
> 「multi-agent ≈ single-agent 的 3.75 倍」这个二次推算**未使用**。

---

## 1. 争的到底是什么

### 1.1 先否掉两个常见的错误框架

**错误框架 A：「循环 vs DAG」。**
这是本页最容易讲错、也最容易被懂行的人当场拆穿的地方。LangGraph **不是 DAG**：它支持环（cycle），
本质是 Pregel / BSP 消息传递模型。把它叫「DAG 编排」在技术上是错的。
准确说法是「**显式状态图 + 超步执行 + 可 checkpoint**」。
（依据：R05 §3.6 明确警告；一手定义见 [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)）

> ⚠️ 顺带：现有 P16（`slides/s11-graph.html`）右半屏标题写的就是 "Orchestration DAG"、对比框写的是「DAG 编排」。
> 新页如果要立「这不是 DAG」，**要么同步改 P16 的措辞，要么在新页显式承认前一页是简化说法**。
> 二选一，不能两页自相矛盾。

**错误框架 B：「模型决定下一步 vs 代码决定下一步」（题面给的候选框架）。**
这个框架**方向对，但不是分歧的根**，因为两端都不纯，它是连续谱而不是二值：

- LangGraph 的 edges 是「Functions that determine **which Node to execute next** based on the current state.
  They can be **conditional branches or fixed transitions**」——条件边完全可以由 LLM 的输出驱动。
  而且官方明写 "Nodes and Edges are nothing more than functions—they can contain an LLM or **just good ol' code**."
  → 图派并不排斥模型决策。
  （[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)）
- 反过来，Anthropic 的 **orchestrator-workers** 里「拆成几个子任务」完全由中心 LLM 现场决定
  （"a **central LLM dynamically breaks down tasks**"），但 Anthropic 仍把它归类为 **workflow 而不是 agent**，
  因为编排骨架写在代码里。
  （[Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)，2024-12-19）

所以「谁决定下一步」是**表层现象**。拿它当分歧点，会被反问「那 conditional edge 算谁决定的」而卡住。

### 1.2 建议采用的框架（三层，逐层收紧）

> **争的是：运行的「权威状态」是什么，因此「可停、可续、可重放、可审计」的最小单位在哪。**

| 层 | Loop 派 | Graph 派 |
|---|---|---|
| ① 权威状态是什么 | **append-only 的消息 / 事件历史**（transcript 即状态） | **显式的 state schema**，与消息历史分离；transcript 只是其中一个字段 |
| ② 最小可恢复单位 | **turn / save point** | **super-step / node 边界 + checkpoint** |
| ③ 「一轮什么时候结束」谁说了算 | **模型**：没有 tool_call 了就结束 | **图算法**：所有 node inactive 且无消息在途 |

第 ③ 条是整场争论的引爆点，R05 §3.2 一句话点破：
> **它把「什么时候算一轮结束」从模型的判断，变成了图算法的不动点判定。**

一手依据（两侧各一句，可直接上页并列）：
- Loop 侧：Claude Agent SDK —— "Claude continues calling tools and processing results
  **until it produces a response with no tool calls**."
  （[How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop)）
- Graph 侧：LangGraph —— "The graph execution **terminates when all nodes are inactive
  and no messages are in transit**."
  （[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)）

**一句话把分歧说死**：
> 循环派认为「做完了」是一个**模型能判断的语义问题**；
> 图派认为「做完了」必须是一个**运行时能判定的结构问题**。
> 剩下所有争执（可复现、恢复粒度、成本、HITL 接入点）都是这一条的推论。

---

## 2. Loop 派的主张（6 条，每条附一手来源）

**这一派是谁**：Anthropic（BEA 的 agent 定义 / Claude Code / Claude Agent SDK / 2026 的 Loop engineering 博客）、
OpenAI Agents SDK 与《A practical guide to building agents》、pi（本地源码取证）、
Cognition 早期立场（单线程线性 agent）。

### L1 · 定义即立场：开放式问题只能这么做

> Agents are "systems where LLMs **dynamically direct their own processes and tool usage**,
> maintaining control over how they accomplish tasks."
> 适用边界："can be used for **open-ended problems** where it's difficult or impossible to
> **predict the required number of steps**."
> —— [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)，2024-12-19

**论证力**：如果步数无法预先枚举，图就没法画完；画不完的图退化成「一个装着 agent loop 的节点」。

### L2 · 循环骨架已经跨厂商收敛，不需要图来表达

三份独立一手定义几乎一致 —— 这本身就是「骨架够用」的证据：

| 来源 | 循环形状 | 判停原文 |
|---|---|---|
| Claude Agent SDK | 五步（receive → evaluate → execute tools → repeat → return），"**Each full cycle is one turn**" | "until it produces a response with **no tool calls**" |
| OpenAI Agents SDK | 三步（call LLM → final_output / handoff / tool calls → max_turns 检查） | "produces text output with the desired type, and **there are no tool calls**" |
| OpenAI 通用抽象 | "a **loop that lets agents operate until an exit condition is reached**" | exit conditions = "tool calls, a certain structured output, errors, or reaching a maximum number of turns" |

来源：[agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) ·
[Running agents](https://openai.github.io/openai-agents-python/running_agents/) ·
[A practical guide to building agents (PDF p.14)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)

> 口径提醒：该 PDF 的官方发布日在 R05 §8 标为**待核实**（2025-04-17 来自二手报道，PDF 内文无日期）。
> 上页引这段话可以，**不要标日期**。

### L3 · 判停不是玄学，是可枚举的结构化枚举（最好用的一条反驳）

Claude Agent SDK 的 `ResultMessage.subtype` 就是一张现成的判停枚举：
`success` / `error_max_turns` / `error_max_budget_usd` / `error_during_execution` / `error_max_structured_output_retries`，
且**只有 `success` 携带 `result` 字段**。
另有预算判停 `max_budget_usd`（子 agent 花费**计入总额**）。
（[agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)）

OpenAI 侧是硬编码的轮数上限：`DEFAULT_MAX_TURNS = 10`，超限抛 `MaxTurnsExceeded`。
（源码 [run_config.py](https://github.com/openai/openai-agents-python/blob/main/src/agents/run_config.py)）

**论证力**：图派说「循环没有边界」是不成立的 —— 循环有五类可枚举的边界，只是边界画在**预算与错误**上，
而不是画在**结构**上。

### L4 · 时间旅行不是图的专利：loop 派把它做在 transcript 层

| 能力 | Loop 派的实现 | 一手依据 |
|---|---|---|
| 事件日志 | Claude Code append-only **JSONL**，`~/.claude/projects/<project>/<session-id>.jsonl`，"**Each line is a JSON object**" | [Manage sessions](https://code.claude.com/docs/en/sessions) |
| 回退 | `/rewind`；**"Every user prompt creates a new checkpoint"**；仅保留最近 **100 个**；六个动作：Restore code and conversation / Restore conversation / Restore code / Summarize from here / Summarize up to here / Never mind | [Checkpointing](https://code.claude.com/docs/en/checkpointing) |
| 分叉 | `/branch` —— "creates a copy of the conversation so far and switches you into it, **leaving the original intact**" | [Manage sessions](https://code.claude.com/docs/en/sessions) |
| 真·树形日志 | pi 的 session entry 带 `parentId`（`packages/agent/src/harness/types.ts:378`）；`navigateTree()` 要求 `phase === "idle"` 否则抛 `busy`（`harness/agent-harness.ts:842,847`）；fork 沿 parent 链读到 root 或 compaction 点（`harness/session/fork.ts:22`） | 本地源码 pi-mono @ `4488ad5` |
| 「换模型/换 thinking 档/换工具集」本身也是事件 | 所以整条历史可精确重放，而不只是消息序列 | pi SQLite schema，11 种 entry 类型（R05 §4.3；schema 细节在 R05 §8 标为**未逐条复核 migrations**） |

**论证力**：graph 派最常打的牌是 checkpoint / time travel。这一条说明 loop 派有同构能力，
只是落在**历史层**而不是**状态层**。

### L5 · 错误交给模型自适应，在探索型任务上比交给图更有效

> "letting the agent know when a tool is failing and letting it adapt **works surprisingly well**"
> —— [Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)，2025-06-13

工程配套（pi 的做法，本地源码）：
- **错误进流不 throw**：`StreamFunction` 契约规定一旦被调用不得抛异常，所有失败编码为
  `stopReason: "error" | "aborted"` 的 `AssistantMessage`（`packages/ai/src/types.ts:314-324`、
  `packages/agent/src/types.ts:28-32`）。
  → 收益：错误状态天然可持久化、可重放、可进对话历史，**模型能看见自己上次失败了**。
- **孤儿 tool_call 补合成 result**：中断后给「有 tool_call 无 tool_result」的空洞补
  `"No result provided"`（`packages/ai/src/api/transform-messages.ts:156+`）—— 这是 abort 后还能继续对话的关键。
- **截断即整批失败重发**：`stopReason === "length"` 时把整批 tool call 标记失败让模型重发，
  而不是拿半截 JSON 去执行（`agent-loop.ts:213`）。

### L6 · 官方已经把 loop 本身工程化了（2026 年新料，最能反击「循环=放养」）

Anthropic [Loop engineering: getting started with loops](https://claude.com/blog/getting-started-with-loops)，
[博客发布日] **2026-06-30**，作者 Delba de Oliveira、Michael Segner。按触发 / 退出条件分四类：

| 循环类型 | 触发 | 退出条件 |
|---|---|---|
| Turn-based | 用户 prompt | Claude 判定完成或需要更多上下文 |
| **Goal-based**（`/goal`） | 人工实时 prompt | **目标达成** 或 达到最大轮数 |
| Time-based（`/loop`、`/schedule`） | 时间间隔 | 取消 或 工作完成 |
| Proactive | 事件/调度，无人实时参与 | 单任务达标即退出 |

官方实践建议原文：
> "Start simple, encode **verification as skills**, use **deterministic success criteria**,
> and **monitor token usage** carefully."

**论证力**：这是 loop 派对「退出条件不可控」的正面回应 —— 把 verifier 做成 skill，
把成功标准做成确定性判据。**这一条同时是第 7 节反驳我方立场的弹药**（见后）。

### L6′ · 派内异见（诚实起见要提一句）

12-Factor Agents（Dex Horthy / HumanLayer）的 **Factor 8 就叫「Own your control flow」**，
对纯循环的批评原文：
> agent 循环 = "LLM determines the next step … repeat until done"，
> 但 "at the end of the day, this approach **just doesn't work as well as we want it to**"
> —— 大家做到 **70-80%** 质量线，然后发现 "**80% isn't good enough** for most customer-facing features"。

**Factor 10「Small, Focused Agents」的量化主张**：每个 agent 保持 "**3-10, maybe 20 steps max**"，
理由 "As context grows, LLMs are more likely to get lost or lose focus."
—— [12-factor-agents](https://github.com/humanlayer/12-factor-agents) ·
[factor-10](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md)

> ⚠️ 只引标题与这两段原文。该仓库的 star 数 / 最后 push 时间在 R05 §8 是**待核实**，**不要上页**。

---

## 3. Graph 派的主张（6 条）

**这一派是谁**：LangChain / LangGraph（唯一有完整一手规范的一方）、OpenAI「Orchestrating via code」那半边、
Anthropic 自己的 workflow 五模式（BEA 里的 workflow 半边其实站在这边）。

> **措辞纪律**：全程说「**显式状态图 + 超步执行 + 可 checkpoint**」，
> **不要说「DAG 编排」**（LangGraph 支持环，是 Pregel 消息传递模型）。R05 §3.6 明确点名这是不准确的。

### G1 · 控制流是一等公民的数据结构，不是涌现物

四原语的逐字定义（[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)）：

| 原语 | 官方定义 |
|---|---|
| **State** | "A shared data structure that represents the **current snapshot** of your application… typically defined using a shared **state schema**." |
| **Nodes** | "**Functions** that encode the logic of your agents. They receive the current state as input, perform some computation or side-effect, and **return an updated state**." |
| **Edges** | "Functions that determine **which Node to execute next** based on the current state. They can be **conditional branches or fixed transitions**." |
| 一句话 | "**nodes do the work, edges tell what to do next**." |

**论证力**：控制流是可读、可 diff、可 code review 的代码，而不是要从 transcript 里考古出来的东西。

### G2 · 终止是不动点判定，不是模型的自我评价（graph 派最硬的一条）

> "A **super-step** can be considered a single iteration over the graph nodes.
> **Nodes that run in parallel are part of the same super-step**, while nodes that run sequentially
> belong to **separate super-steps**."
> "The graph execution **terminates when all nodes are inactive and no messages are in transit**."
> —— [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)

配套的反面证据（loop 派自承）：
> "Agents make dynamic decisions and are **non-deterministic between runs, even with identical prompts**.
> This makes debugging harder." / "minor system failures can be **catastrophic for agents**"
> —— [Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)

### G3 · Checkpointer 一次解决四件事，且性能-一致性是显式旋钮

官方列的四个用途：**conversation continuity / human-in-the-loop workflows / time travel / fault tolerance**。
> 持久化 "matters when an agent needs to **continue a conversation, resume after an interruption,
> recover from a failure, or remember information across interactions**."
> Checkpointer 的职责是 "persist a **thread's** graph state as **checkpoints**."
> —— [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

**Durability 三档**（`durability` 参数，[Reference](https://reference.langchain.com/python/langgraph/types/Durability)）：
- `"exit"` 仅在图执行退出时落盘（最快、最不耐崩）
- `"async"` 下一步执行的同时异步落盘
- `"sync"` 下一步开始前同步落盘（最耐崩、开销最大）

**论证力**：loop 派的落盘时机是实现细节（pi：`message_end` 立即落盘、`turn_end` flush + `save_point`）；
graph 派把它变成了一个**可配置、可写进 SLA 的参数**。这条对合规场景杀伤力很大。

### G4 · HITL 有精确的接入点，而不是「按 Esc」

[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)：
- `interrupt()` 在 **node 内任意位置**调用 → 运行时捕获 → 通过 checkpointer 保存状态 → **无限期挂起**。
- **"A checkpointer is mandatory."** `thread_id` 是持久游标。
- 恢复用 `Command(resume=...)`，resume 值成为原 `interrupt()` 调用的返回值。
- 官方四种模式：**approval workflows** / **review and edit** / **tool interrupts** / **input validation**。
- ⚠️ 官方自承的坑（讲稿必提，这是 graph 派最贵的代价）：
  > "**Nodes re-execute from the beginning on resume.** Any code before the `interrupt()` call runs again,
  > so **side effects must be idempotent**."

### G5 · 时间旅行有两种精确语义 —— 但官方自己拆了自己的台

[Use time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)：

| 操作 | 步骤 | 语义 |
|---|---|---|
| **Replay** | `get_state_history()` → 选 `checkpoint_id` → 带该 config 调 `invoke()` | ⚠️ "Replay **re-executes nodes**—it doesn't just read from cache. LLM calls, API requests, and interrupts **fire again and may return different results**." |
| **Fork** | 对旧 checkpoint 调 `update_state()` → `invoke(None, fork_config)` | "creates a **new checkpoint that branches** from the specified point. The **original execution history remains intact**." |

> **这一条是全页最锋利的素材**：graph 派自己在文档里写明 replay **不保证结果一致**。
> 所以「图更可复现」这句话必须收窄成「图的**控制流边界**可复现」，而不是「运行结果可复现」。
> 上页时把这句原文摆出来，比任何二手评论都有说服力。

### G6 · 成本与延迟可预算（这是 graph 派最实际的卖点）

> **Orchestrating via code**："Determining the flow of agents **via your code**" → 更
> "**deterministic and predictable** regarding **speed, cost, and performance**"。
> 官方给的四招：① structured outputs 供代码检查 ② 上一个 agent 的输出变换成下一个的输入
> ③ loop + evaluator 跑到达标 ④ `asyncio.gather` 并行。
> —— [Orchestrating multiple agents](https://openai.github.io/openai-agents-python/multi_agent/)

对照 loop 派自承的代价（Anthropic 官方，同一篇多次引用）：
- "Agentic systems often **trade latency and cost for better task performance**."（BEA）
- agent ≈ chat 的 **4×** token；multi-agent ≈ chat 的 **15×**（multi-agent 博客）
- BrowseComp 上 **token 用量单独解释 80% 方差**（同上）

> ⚠️ 口径：4×/15× 是**相对 chat 交互**的粗略倍数（原文用 "about"），
> **不是** multi-agent 相对 single-agent 的倍数。相除得到的 3.75× 是二次推算，**原文没有，不要用**。

---

## 4. 五个真正的分歧点

> 「真分歧」= 两派对同一个可观测现象做出**不相容的预测**。每条都写清：各自主张 + 什么证据能裁决 +
> 目前证据够不够。

### D1 · 可复现性 / 可审计性的载体是什么

| | 主张 |
|---|---|
| **Loop 派** | transcript **就是**全部状态；重放 transcript 即重放系统。pi 把「换模型 / 换 thinking 档 / 换工具集」也做成 entry，所以整条历史可精确重放（R05 §4.3） |
| **Graph 派** | transcript 不是状态，**state schema 才是**；且 super-step + checkpoint 提供**确定的重放边界**（R05 §3.6 对比表「可复现性：高 vs 低」） |

**不相容的预测**：给一段已经跑完的执行，能否在**不重新调用 LLM** 的前提下，重建「当时为什么走这条路」。

**什么证据能裁决**：
- 已有的、指向 graph 派的证据：Anthropic 自承 "non-deterministic between runs, even with identical prompts"。
- 已有的、指向 loop 派的**反证**：LangGraph 官方自承 "Replay **re-executes nodes**… LLM calls…
  **fire again and may return different results**" —— **图的重放同样不保证结果一致**。
- **能真正裁决的实验**：同一任务两派各跑 N 次，比较的不是最终答案的方差，而是「**决策点集合**的方差」
  （走过哪些分支、调用了哪些工具、顺序如何）。
- **现状**：两派都没有公开做过这个对照实验 → **待核实 / 目前无一手数据可判**。上页时必须承认这一点。

**结论**：这一条**分歧真实，但两派的自我宣称都被自家文档打了折**。可复现性的差别在**结构层**，不在**结果层**。

---

### D2 · 失败恢复的粒度，以及副作用的原子性

| | 最小恢复单位 | 一手依据 |
|---|---|---|
| **Loop 派** | **turn / save point**。Claude Code：每个 user prompt 一个 checkpoint，仅留最近 100 个。pi：`message_end` 立即落盘，`turn_end` flush 后发 `save_point` | [Checkpointing](https://code.claude.com/docs/en/checkpointing)；pi `agent-harness.ts` 的 `handleAgentEvent` |
| **Graph 派** | **super-step / node 边界**，且落盘时机可配（exit / async / sync） | [Durability](https://reference.langchain.com/python/langgraph/types/Durability) |

**不相容的预测**：恢复时**会不会重复不可回滚的副作用**。

两派都在文档里承认自己会：
- Graph：**"Nodes re-execute from the beginning on resume… side effects must be idempotent."**
  （[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)）
- Loop：Claude Code checkpoint **不追踪 bash 命令改动**（`rm/mv/cp` rewind 不回来）；
  **subagent 的编辑不在本 session 的 checkpoint 内**；symlink / hardlink 路径跳过不还原；
  官方定位 "Think of checkpoints as **'local undo'** and **Git as 'permanent history'**."
  （[Checkpointing](https://code.claude.com/docs/en/checkpointing)）
  更狠的一条：**"Actions that affect remote systems (databases, APIs, deployments) can't be checkpointed,
  which is why Claude asks before running commands with external side effects."**
  （[How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)）

**什么证据能裁决**：一个**可观测且可当场量的属性** ——
「单个恢复单位（node / turn）内部，包含几个不可回滚的外部写？」
- 若为 0 或 1 → 两派等价，选谁都行。
- 若 ≥2 → 恢复单位太粗，必须往下切。graph 派能切到 node 且能开 `durability="sync"`；
  loop 派只能靠工具级审批把外部写挡在 turn 之外。

**结论**：**这是五条里最实、最能当场判定的一条**。建议做本页的主论点之一。

---

### D3 · 成本与 token 用量

| | 主张 |
|---|---|
| **Loop 派** | 承认贵，但主张贵得值：agentic systems "**trade latency and cost for better task performance**"；且已有预算判停（`max_budget_usd`）与轮数上限（`DEFAULT_MAX_TURNS = 10`） |
| **Graph 派** | via code 更 "**deterministic and predictable** regarding speed, cost, and performance"；而且能把不需要模型的节点换成 "just good ol' code" |

**已有的硬数字（全部来自 loop 派自曝，注意口径）**：
- agent ≈ chat 的 **4×**；multi-agent ≈ chat 的 **15×**
- BrowseComp 上 **token 用量单独解释 80% 方差**
- 收益侧：内部 research eval 上，Opus 4 lead + Sonnet 4 subagents 比单体 Opus 4 高 **90.2%**
  （**Anthropic 内部评测，不是公开 benchmark**）
—— 全部出自 [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)

**什么证据能裁决**：同一任务、同一模型、同一工具集下的「**成功一次的单位 token 成本**」对照。

**现状**：**没有任何公开的 loop-vs-graph 同任务成本对照数据** → **待核实**。
上面那些数字全是「agent vs chat」「multi-agent vs single-agent」，**不是「loop vs graph」**。
上页时如果借这些数字暗示 graph 更便宜，就是偷换口径，会被抓。

**诚实的讲法**：token 这条**目前无法裁决**。可讲的只有一句结构性判断 ——
图能把「不需要模型的那一步」换成纯代码，循环不能（循环里每一步都要经过一次模型判断），
这是**机制层面的成本差**，但**没有数字**。

---

### D4 · 能不能处理无法预先枚举的探索

| | 主张 |
|---|---|
| **Loop 派** | 只有循环能做："**open-ended problems** where it's difficult or impossible to **predict the required number of steps**"；"complex tasks where you **can't predict the subtasks** needed" |
| **Graph 派** | 图支持环 + 条件边，理论上能表达任意控制流；代价是「图要人写，步骤数不可预测时会爆炸」（R05 §3.6） |

**不相容的预测**：当工作清单**只能在运行中被发现**时，图会不会退化成
「**一个装着 agent loop 的节点**」——即图的表达力在这里是不是名义上的。

**什么证据能裁决**：看真实系统的收敛形态。而这一点已经有一手证据，且**对两派都不利**：
> OpenAI：**"Multi-agent systems can be modeled as graphs, with agents represented as nodes.**
> In the manager pattern, **edges represent tool calls**; in the decentralized pattern,
> **edges represent handoffs**."
> —— [A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)

即：**图的节点里装 agent，agent 的工具调用就是图的边** —— 两派已经互相内嵌了。

**结论**：这一条**分歧真实但正在消解**。可讲的结论是：
探索阶段没法画图，**但探索的产出正是一张图**（先用 agent 探索出工作清单，再用图批量执行）。
现有 P16 底部已经写了这句「现实里几乎总是混合」，新页可以把它升级成「这是分歧的**解**，不是和稀泥」。

---

### D5 · Human-in-the-loop 的接入点在哪

| | 卡点位置 | 一手依据 |
|---|---|---|
| **Graph 派** | **node 内任意位置**（`interrupt()`），checkpointer 强制，四种官方模式，`Command(resume=)` 恢复；代价是 node 从头重跑、副作用必须幂等 | [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) |
| **Loop 派** | **turn 边界 + 工具调用前**。Esc 立即取消当前工具调用；输入文本**不打断**，等当前动作结束后插入（steering）。pi 把 steer / follow-up / next-turn **三种排队语义做进内核**（`QueueMode = "all" \| "one-at-a-time"`） | [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)；pi `agent-loop.ts:174` 双层 while |

**不相容的预测**：「在关键动作前暂停等人批准」，**需不需要一张图**。

**裁决证据（已存在，倾向 loop 派）**：
Claude Code 的做法是在**动作层**要求批准，理由写在官方文档里 ——
外部副作用「can't be checkpointed」，所以在执行前问人。
pi 侧有对等机制：`tool_call` 钩子可 **block**（`{ block?, reason? }`），
且参数校验与权限钩子**始终串行执行**，只有 `execute` 并发（`agent-loop.ts:489-554`）。

**结论**：这一条**分歧比看上去小**。真正的差别只在一处：
**graph 能在「一个动作的中间」卡点，loop 只能在「动作之间」卡点。**
若你的审批点恰好落在一个 node 的中段（例如「算完了，写库之前」），图才不可替代。

---

## 5. 哪些是伪分歧

### F1 ·「DAG vs 循环」—— 术语错误，不是观点分歧 ⭐ 最值得上页

LangGraph 支持环，是 Pregel 消息传递模型，**它不是 DAG**（R05 §3.6）。
而 loop 派也**不是「没有图」**：pi 的 session 本身就是树（entry 带 `parentId`），
Claude Code 的 `/branch` 与 `--fork-session` 就是图操作。

> **两边都是图。区别只在于：一边把图画在「未来的执行」上，一边把图画在「过去的历史」上。**
>
> 这句话可以直接做本页的 takeaway。它同时解释了为什么 P16 的标题
> 「向后是一棵树，向前是一张图」其实已经摸到了这个分歧，只是没点破。

### F2 ·「谁决定下一步」—— 是连续谱，不是二值

- LangGraph 的 conditional edge 可以由 LLM 输出驱动，且 node "can contain an LLM"。
- Anthropic 的 orchestrator-workers 由中心 LLM 动态拆解，**却仍被归为 workflow**。
→ 用这个轴吵架必然吵不出结果。

### F3 · checkpoint / time travel 不是 graph 独有

| 语义 | Graph 派 | Loop 派 |
|---|---|---|
| 重放到某点 | `replay`（`checkpoint_id`） | `/rewind`（Restore conversation / code / 两者） |
| 分叉且保留原路径 | `fork`（"original execution history remains intact"） | `/branch`（"leaving the original intact"）、pi `navigateTree()` / `fork.ts` |
| 强制前提 | "A checkpointer is mandatory." | append-only，"从不原地改写" |

甚至还有第三种落法：Cursor 的 checkpoint 是**纯代码快照**
（"Checkpoints save **snapshots of your codebase**"，"stored **locally and separate from Git**"）——
[Cursor Docs · Checkpoints](https://cursor.com/docs/agent/chat/checkpoints)。
→ 说明这是**同一族能力的三种落点**（graph state / transcript / 文件系统），不是两派的分野。

### F4 ·「结构化输出」两派都用

OpenAI 代码编排的第一招就是 structured outputs 供代码检查；
而 loop 派的判停规则本身就是 "produces text output with **the desired type**, and there are no tool calls"。
同一个机制，两边都当自己的论据用。

### F5 · evaluator / verifier 循环 —— 三处独立来源指向同一结构，是**收敛点**不是分歧

1. Anthropic BEA 把 **evaluator-optimizer** 列为 workflow：
   "one LLM call generates a response while another provides **evaluation and feedback in a loop**"，
   适用条件 "clear evaluation criteria… iterative refinement provides measurable value"。
2. Anthropic 2026 Loop engineering 的 **goal-based loops**：
   "encode **verification as skills**, use **deterministic success criteria**"。
3. Cognition 2026 的 **Code-Review Loop**：
   "**clean context leads to a notable improvement in capabilities when using a generator-verifier loop**"
   （[Multi-Agents: What's Actually Working](https://cognition.com/blog/multi-agents-working)，2026-04-22）。

> 这一条与 deck 现有的 P22 / P23 / P25「评审方不共享上下文」的三次交叉验证是同一条线，
> **新页应该主动接上**（讲稿 04-ch3b P25「别漏了说」已经要求把这三处串起来讲，现在是第四处）。

### F6 ·「可复现」这个词两边说的不是同一件事

Graph 派说的是**结构 / 边界可复现**（且官方自承 replay 会重新调 LLM、结果可能不同）；
Loop 派说的是**历史可完整重建**。用同一个词吵，是术语问题不是观点问题。

---

## 6. 收敛判据（给定一个具体任务，怎么选）

> 设计成 **5 个可观测问题，按顺序问，命中即停**。每条都绑定一手依据，不是拍脑袋。

| # | 可观测问题 | 命中 → 选谁 | 依据 |
|---|---|---|---|
| **Q1** | 开工前能否**枚举出工作清单**（子任务是什么、大概几步）？ | **不能 → Loop** | "impossible to **predict the required number of steps**" / "can't predict the subtasks needed"（BEA） |
| **Q2** | 有没有一个**比模型便宜的自动 verifier**（测试 / 编译 / schema 校验 / diff / 静态检查）？ | **有 → 有骨架的循环**（evaluator-optimizer 或 goal-based loop），既不是纯放养循环，也不用整张图 | BEA evaluator-optimizer "clear evaluation criteria"；Loop engineering "**deterministic success criteria**" |
| **Q3** | 单个恢复单位（一个 node / 一个 turn）内部，含**几个不可回滚的外部写**？ | **≥2 → Graph**（node 边界 + `durability="sync"`）；**0–1 → Loop 够用**（turn 边界 + 工具级审批） | Durability 三档；Claude Code "Actions that affect remote systems… **can't be checkpointed**" |
| **Q4** | 人工卡点落在**动作之间**，还是**一个动作的中段**？ | **中段 → Graph**（`interrupt()` 可在 node 内任意位置）；**动作之间 → Loop 够用**（`tool_call` 钩子 block / Esc / steering） | Interrupts 四种模式；pi `tool_call` 钩子 `{block?, reason?}` |
| **Q5** | 要不要向**第三方**（合规 / 审计 / 客户）证明「这一步为什么发生」？ | **要 → Graph**（控制流本身是可读代码，不用从 transcript 考古）；**只需自己复盘 → Loop**（append-only transcript 够） | "nodes do the work, **edges tell what to do next**"；对照 "non-deterministic between runs, even with identical prompts" |

**把五问压成一句可背的判据**：

> **看「谁能廉价地判定这一步对不对」，以及「一步之内能砸坏多少东西」。**
> 判定者便宜（有自动 verifier）→ 循环能自己收敛；
> 判定者昂贵（只能是人、或必须留痕给合规）→ 把控制流搬进代码，因为你要审的是**控制流本身**，不是结果。
> 而只要一个恢复单位里塞了两个以上不可回滚的外部写，**不管选哪派，先把单位切小**。

---

## 7. 一句话立场 + 最强反驳

### 7.1 主推立场（建议上页）

> **「Loop 和 Graph 不是两种架构，是两种『可停可续的最小单位』的选择：循环选 turn，图选 node。
> 该选哪个，取决于你有没有一个比模型更便宜的判定者 —— 有 verifier 就用循环，
> verifier 只能是人或合规，就用图。因为图的真正作用不是让 agent 更聪明，是让人能在正确的位置插进去。」**

**为什么这个立场站得住**：
- 它不站队，但**不和稀泥**：它给出了一个可当场判定的量（verifier 的有无与成本）。
- 它避开了两个伪分歧（DAG 措辞、谁决定下一步）。
- 它与 deck 全场主张同源：「模型决定能力上限，harness 决定你能兑现多少」——
  verifier 与卡点位置都是 harness 的事，不是模型的事。
- 它有一手依据兜底：Anthropic 自己就把 "deterministic success criteria" 当作 goal-based loop 的前提条件。

### 7.2 备用短版（若版面只够一行）

> **两边都是图。区别只在于：图画在「未来的执行」上，还是画在「过去的历史」上。**

### 7.3 最强反驳（必须自己先说出来，否则会被问倒）

> **「verifier 的有无不是任务的固有属性，而是工程投入的函数。」**
>
> Anthropic 官方给的建议原文就是 "**encode verification as skills**" ——
> 也就是说 verifier 是**可以被造出来**的。那么「没有 verifier，所以上图」
> 很可能只是「**我还没写 verifier**」的托词。
> 而一旦 verifier 造出来了，图的主要收益（可预测的退出条件）就被循环拿走了 ——
> 于是这个立场会自我塌缩成「永远选循环」。

**对反驳的回应（准备好，但只在被问到时说）**：
verifier 造不出来的那一类，恰恰是图不可替代的地方 —— 因为那里要卡的不是「**对不对**」，而是「**准不准**」。
一手证据：Claude Code 明说外部副作用「can't be checkpointed，which is why Claude asks before running」——
**注意它没有说「所以我们写个 verifier」，它说的是「所以我们问人」**。
「问人」这件事的接入点在哪，就是 loop 与 graph 唯一无法互相替代的分歧（见 D5）。

**第二个可能被问到的**：
> 「你说图更适合审计，可 LangGraph 自己说 replay 会重新调 LLM、结果可能不同啊？」

老实答：对，所以我说的是**控制流可审计**，不是**结果可复现**。
两派谁都给不了结果可复现 —— Anthropic 说 "non-deterministic between runs, even with identical prompts"，
LangGraph 说 "may return different results"。**这一点上没有赢家，我不替任何一方吹。**

---

## 8. 上页素材（一页放得下的最短版本）

### 8.1 标题候选（三选一）

1. **「Loop 派 vs Graph 派：争的不是数据结构，是『可停可续的最小单位』」**
2. **「两边都是图 —— 一边画在未来，一边画在过去」**
3. **「谁说了算『这一轮结束了』」**

（推荐 ①：它直接把伪分歧挡在门外；② 适合做 takeaway 而不是标题。）

### 8.2 页面正文 —— 9 条短句（每条 ≤ 22 字，可直接排版）

1. 争的**不是**「循环 vs DAG」—— LangGraph 本来就支持环。
2. 真分歧：权威状态是 **transcript**，还是**显式 state**。
3. 于是「一轮何时结束」有两个答案。
4. 循环派：**模型说没有 tool_call 了**。
5. 图派：**所有 node inactive、无消息在途**。
6. 循环派的判停是 **5 种可枚举的 subtype**，不是玄学。
7. 图派的 HITL 有代价：**resume 时 node 从头重跑，副作用必须幂等**。
8. 图派自己承认：**replay 会重新调 LLM，结果可能不同**。
9. 循环派自己承认：**identical prompts 之间也不确定**。

### 8.3 底部 takeaway（一句，加粗）

> **有便宜的 verifier 就用循环；verifier 只能是人或合规，就用图。**
> 图的真正作用不是让 agent 更聪明，是**让人能在正确的位置插进去**。

### 8.4 可选的「五个真分歧」小卡（若版面够，用 5 个 8 字标签）

`可审计的载体` · `恢复的粒度` · `token 的账` · `无法枚举的探索` · `人插在哪一刀`

其中 **`token 的账` 必须标注「无一手对照数据」**，否则会被抓（见 D3）。

### 8.5 页脚引用（逐字，可直接粘进 `<span class="src">`）

```
出处 · Anthropic《Building Effective AI Agents》2024-12-19 anthropic.com/engineering/building-effective-agents
     · LangGraph Graph API（super-step / 终止判定）docs.langchain.com/oss/python/langgraph/graph-api
     · LangGraph Interrupts（"A checkpointer is mandatory."）· Use time travel（replay / fork）
     · Claude Agent SDK · agent-loop（判停枚举）code.claude.com/docs/en/agent-sdk/agent-loop
     · OpenAI Agents SDK · Orchestrating multiple agents openai.github.io/openai-agents-python/multi_agent/
     · Anthropic《Loop engineering》2026-06-30 claude.com/blog/getting-started-with-loops
     · 证据 · pi-mono @4488ad5 packages/agent/src/agent-loop.ts（双层 while / 4 个判停点）
```

（若页脚放不下，最低限度必须保留：**BEA + LangGraph Graph API + agent-loop 三条**，
因为本页三个核心引文分别出自这三处。）

---

## 9. 与现有页面的衔接与冲突检查

| 项 | 说明 |
|---|---|
| **插入位置** | P16（s11-graph）之后。P16 讲「树 + 图是两种能力」，新页讲「这其实是两套对立的工程假设」——递进关系成立 |
| **⚠️ 必须处理的冲突** | P16 里写了「向前 · 编排图 **Orchestration DAG**」「**DAG 编排**」「路径：你写死，模型填节点」。新页若立「LangGraph 不是 DAG」，**必须在讲稿里点一句**：P16 说的 DAG 是**狭义的确定性编排**（如 swarm-extension 的 YAML DAG，那确实是 DAG），而 LangGraph 属于更一般的显式状态图。**这两个不是同一个东西，不点破就是自相矛盾** |
| **与 P22（s16-workflow）不重复** | P22 是 Anthropic 五模式的**词汇表**，不含争论。新页是**争论**。不冲突，但新页里 orchestrator-workers「被归为 workflow」这条与 P22 重合，讲的时候可以说「上上页那条分类，现在派上用场了」 |
| **与 P23（s17-multiagent）的关系** | P23 是「多智能体之争」（Cognition vs Anthropic）。新页是**另一场**争论，维度不同（控制流归属 vs 并发写归属）。**两页并列会很有力**：一场关于「要不要多个 agent」，一场关于「控制流该不该写死」。建议在新页开场说一句「这是第二场对撞」 |
| **章节页数影响** | CH3 从 12 页变 13 页，`NOTES.md` 第二节的结构表（37 页 / 7 章）与「时间不够时的取舍」需同步更新。新页建议列入**可砍**清单还是**必保**清单，由讲者定 |
| **色板** | 按 OUTLINE 语义色：Loop 侧用绿 `#34d399`（内核/循环/执行），Graph 侧用琥珀 `#fbbf24` 或紫 `#a78bfa`（编排/状态）；「两派都自承的弱点」用玫红 `#fb7185` |

---

## 10. 本页的「待核实」清单（上台前自查）

| # | 项 | 状态 | 处理 |
|---|---|---|---|
| 1 | **loop vs graph 的同任务成本 / 成功率对照** | **不存在公开数据** | D3 必须明说「这条无法裁决」。不要用 4×/15×/90.2% 暗示 graph 更便宜 —— 那是 agent-vs-chat 与 multi-vs-single 的口径 |
| 2 | **「决策点方差」对照实验** | 两派都没做过 | D1 只能说「能裁决它的实验尚不存在」 |
| 3 | OpenAI《A practical guide to building agents》发布日 | R05 §8 标待核实（2025-04-17 为二手） | 引用原文可以，**不标日期** |
| 4 | 12-factor-agents 的 star 数 / 最后 push | R05 §8 标待核实 | **不上页**。只引 Factor 8 / Factor 10 的标题与原文 |
| 5 | pi SQLite schema 的 11 种 entry 类型细节 | R05 §8 标「未逐条复核 migrations」 | 若上页只说「pi 的 session entry 带 `parentId`，是树不是线」（这条已在源码直接核实：`harness/types.ts:378`、`fork.ts:22`、`navigateTree`），不要展开 schema 细节 |
| 6 | pi 行号 | 随上游漂移 | 引用**必须带 commit 短 hash `4488ad5`** |
| 7 | LangGraph 各文档页的版本 / 抓取日 | R05 采集时间 2026-08-01 | 页脚不标日期即可，或统一标「文档抓取 2026-08」 |
