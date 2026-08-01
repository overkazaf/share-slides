# R05 · Loop Engineering / Graph Engineering / Workflow 编排的原理

> 采集时间：2026-08-01。每条事实后附可核查 URL。凡未能从一手来源确认的，标注「**待核实**」。
> 引号内英文为**原文逐字引用**；中文为笔者转述。
> 日期口径统一标注：`[博客发布日]` / `[arXiv v1 预印本日]` / `[版本发布日]`。

---

## 0. 一页速览：可直接上 PPT 的硬事实

| # | 事实 | 数字 / 名称 | 口径与出处 |
|---|---|---|---|
| 1 | Anthropic 对 workflow / agent 的定义边界 | workflow = "orchestrated through **predefined code paths**"；agent = "LLMs **dynamically direct their own processes** and tool usage" | [博客发布日] 2024-12-19，[Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) |
| 2 | 多 agent 的 token 代价 | agent ≈ chat 的 **4×**；multi-agent ≈ chat 的 **15×** | [博客发布日] 2025-06-13，[Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) |
| 3 | 多 agent 的收益 | 内部 research eval 上，Opus 4 lead + Sonnet 4 subagents 比单体 Opus 4 高 **90.2%** | 同上 |
| 4 | 性能方差归因 | BrowseComp 上 **token 用量单独解释 80% 方差** | 同上 |
| 5 | OpenAI Agents SDK 默认轮数上限 | `DEFAULT_MAX_TURNS = 10`，超限抛 `MaxTurnsExceeded` | 源码 [run_config.py:43](https://github.com/openai/openai-agents-python/blob/main/src/agents/run_config.py) |
| 6 | METR 时间跨度倍增周期 | 全历史 **~7 个月**（196 天）；**2023 后 131 天**；**2024 后 89 天** | [博客发布日] 2026-01-29，[Time Horizon 1.1](https://metr.org/blog/2026-1-29-time-horizon-1-1/) |
| 7 | 当前最强模型 50% 时间跨度 | Claude Opus 4.5 = **320 分钟**；GPT-5 = 214 分钟（TH1.1 口径） | 同上 |
| 8 | LangGraph 时间旅行两种语义 | **replay**（重放）与 **fork**（分叉），基于 `checkpoint_id` | [Use time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel) |
| 9 | Claude Code 会话存储 | append-only **JSONL**：`~/.claude/projects/<project>/<session-id>.jsonl` | [Manage sessions](https://code.claude.com/docs/en/sessions) |
| 10 | Cognition 2026 年立场更新 | "Multi-agent systems work best today when **writes stay single-threaded** and the additional agents contribute **intelligence rather than actions**." | [博客发布日] 2026-04-22，[Multi-Agents: What's Actually Working](https://cognition.com/blog/multi-agents-working) |

---

## 1. Agent Loop 的最小骨架

### 1.1 三份一手定义（可交叉印证）

**(A) Anthropic / Claude Code —「三阶段」表述**

> "When you give Claude a task, it works through three phases: **gather context**, **take action**, and **verify results**. These phases blend together."
> —— [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)

同页把 Claude Code 定位为 **agentic harness**：
> "Claude Code serves as the **agentic harness** around Claude: it provides the tools, context management, and execution environment that turn a language model into a capable coding agent."

**(B) Claude Agent SDK —「五步循环」表述**（最接近伪代码）

> 1. **Receive prompt.** … 2. **Evaluate and respond.** … 3. **Execute tools.** … 4. **Repeat.** "Steps 2 and 3 repeat as a cycle. **Each full cycle is one turn.** Claude continues calling tools and processing results **until it produces a response with no tool calls**." 5. **Return result.**
> —— [How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop)

**(C) OpenAI Agents SDK —「三步循环」表述**

> 1. "We call the LLM for the current agent, with the current input."
> 2. "The LLM produces its output. If the LLM returns a `final_output`, the loop ends… If the LLM does a **handoff**, we update the current agent and input, and re-run the loop. If the LLM produces **tool calls**, we run those tool calls, append the results, and re-run the loop."
> 3. "If we exceed the `max_turns` passed, we raise a `MaxTurnsExceeded` exception."
>
> final output 判定规则："The rule for whether the LLM output is considered as a 'final output' is that it **produces text output with the desired type, and there are no tool calls**."
> —— [Running agents](https://openai.github.io/openai-agents-python/running_agents/)

**(D) OpenAI《A practical guide to building agents》— 通用抽象**

> "Every orchestration approach needs the concept of a 'run', typically implemented as a **loop that lets agents operate until an exit condition is reached**. Common exit conditions include **tool calls, a certain structured output, errors, or reaching a maximum number of turns**."
> —— PDF 第 14 页，[a-practical-guide-to-building-agents.pdf](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)（落地页 [openai.com](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)；发布日 **2025-04-17**，见 [MarkTechPost 报道](https://www.marktechpost.com/2025/04/17/openai-releases-a-practical-guide-to-building-llm-agents-for-real-world-applications/)，PDF 内文未印日期，**待核实**官方声明日）

### 1.2 判停条件分类表（合并四家口径）

| 类别 | 触发条件 | 一手依据 |
|---|---|---|
| **自然终止**：无 tool_call | 模型返回纯文本、无工具调用 | Claude Agent SDK："until it produces a response with no tool calls"；OpenAI SDK："there are no tool calls" |
| **显式 done 工具 / 结构化终值** | 调用 final-output 工具或产出指定 output type | OpenAI 指南："A final-output tool is invoked, defined by a specific output type" |
| **达到 max turns** | `max_turns` / `maxTurns` 上限 | OpenAI SDK `DEFAULT_MAX_TURNS = 10`（[run_config.py:43](https://github.com/openai/openai-agents-python/blob/main/src/agents/run_config.py)）；Claude Agent SDK **默认无上限**（"No limit"），超限返回 `error_max_turns`（[agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)） |
| **预算上限**（较少被提及但很实用） | `max_budget_usd` / `maxBudgetUsd`，超限返回 `error_max_budget_usd`；子 agent 的花费**计入总额** | [agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) |
| **用户中断 / steering** | Esc 立即取消当前工具调用；或输入文本不打断，等当前动作结束后插入 | [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)："Press `Esc` to stop Claude immediately… Type a correction and press `Enter` to send it without stopping the running tool." |
| **错误终止** | API 失败、请求取消 → `error_during_execution` | [agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) |
| **宿主关闭** | `SystemMessage` subtype `worker_shutting_down`："the loop will end after the current turn because the host is exiting" | 同上 |
| **结构化输出重试耗尽** | `error_max_structured_output_retries` | 同上 |

> **PPT 可用的一句话**：Claude Agent SDK 的 `ResultMessage.subtype` 就是一张现成的「判停枚举」：`success` / `error_max_turns` / `error_max_budget_usd` / `error_during_execution` / `error_max_structured_output_retries`。且**只有 `success` 携带 `result` 字段**，其余四种都没有——这本身就是「判停必须结构化」的最佳论据。（[agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)）

### 1.3 Loop Engineering 的官方分类学（2026 年新料）

Anthropic 官方博客 [Loop engineering: getting started with loops](https://claude.com/blog/getting-started-with-loops)，[博客发布日] **2026-06-30**，作者 **Delba de Oliveira、Michael Segner**。把「loop」定义为 *agents repeating cycles of work until a stop condition is met*，并按**触发方式 / 退出条件 / 使用原语 / 适用任务**四轴分成四类：

| 循环类型 | 触发 | 退出条件 | 适用 |
|---|---|---|---|
| **Turn-based loops** | 用户 prompt | Claude 判定任务完成或需要更多上下文 | 短任务、非周期性；每轮把控制权交回人 |
| **Goal-based loops**（`/goal`） | 人工实时 prompt | 目标达成 或 达到最大轮数 | 有**可验证退出标准**的任务；人定义成功条件，evaluator 检查进度 |
| **Time-based loops**（`/loop`、`/schedule`） | 指定时间间隔 | 取消 或 工作完成 | 周期性 / 依赖外部状态的工作 |
| **Proactive loops** | 事件或调度触发，**无人实时参与** | 单任务达标即退出，routine 持续到被禁用 | 定义良好的周期性工作流 |

> 官方给的实践建议原文要点："Start simple, encode **verification as skills**, use **deterministic success criteria**, and **monitor token usage** carefully."

### 1.4 一个真实的双层循环实现：pi（本地源码，可作为「我们自己的骨架」）

本地仓库 `/Users/nongjiawu/playground/research/pi/pi-mono`，workspace 版本 **0.83.0**。核心文件 `packages/agent/src/agent-loop.ts`（793 行，无状态纯函数）。已在源码中核实的关键行：

- `agent-loop.ts:171` `let hasMoreToolCalls = true;`
- `agent-loop.ts:174` `while (hasMoreToolCalls || pendingMessages.length > 0) {`
- `agent-loop.ts:206` `hasMoreToolCalls = false;`
- `agent-loop.ts:216` `hasMoreToolCalls = !executedToolBatch.terminate;`
- `agent-loop.ts:248` `await config.shouldStopAfterTurn?.({...})`

控制流骨架（摘自本仓库既有分析 `analysis/raw/01-pi-agent-ai-core.md`，行号已抽样复核）：

```
OUTER while(true):                       // 处理 follow-up（agent 已停止后追加任务）
  hasMoreToolCalls = true
  INNER while (hasMoreToolCalls || pendingMessages.length > 0):   // assistant→tool→assistant 链 + steering 插队
    ├─ 注入 pendingMessages（运行中插队 = steering）
    ├─ message = await streamAssistantResponse(...)
    ├─ if stopReason ∈ {error, aborted}: emit(agent_end); RETURN
    ├─ toolCalls = message.content.filter(type === "toolCall")
    ├─ if toolCalls.length > 0:
    │    ├─ if stopReason === "length" → failToolCallsFromTruncatedMessage()   // 输出被截断→全部返错让模型重发
    │    └─ else → executeToolCalls()
    │    hasMoreToolCalls = !batch.terminate
    ├─ snapshot = await config.prepareNextTurn(...)   // 下一轮才生效的 model/tools/thinking 切换
    ├─ if await config.shouldStopAfterTurn(...): RETURN
    └─ pendingMessages = await config.getSteeringMessages() ?? []
  followUps = await config.getFollowUpMessages() ?? []
  if followUps.length: pendingMessages = followUps; continue OUTER
  break
```

**值得讲的三个设计点**：
1. **双层 while 把三种排队语义做进内核**：steer（运行中插队）/ follow-up（停止后追加）/ next-turn（下一轮生效的配置切换）。`QueueMode = "all" | "one-at-a-time"`。
2. **`terminate` 语义严格**：只有批次中**每个** tool result 都 `terminate === true` 才提前结束（`shouldTerminateToolBatch`）。
3. **Turn Snapshot（save point 语义）**：`createTurnState()` 每轮开始冻结 `{messages, model, tools, thinkingLevel, …}`；运行中 `setModel()` 不影响进行中的请求，在 `prepareNextTurn` 重建快照时才生效。

### 1.5 错误恢复策略（六类，均有一手依据）

| 策略 | 说明 | 出处 |
|---|---|---|
| **错误进流不 throw** | pi 的 `StreamFunction` 契约：一旦被调用**不得抛异常**，所有失败编码为 `stopReason: "error" \| "aborted"` 的 `AssistantMessage`。收益：错误状态天然可持久化、可重放、可进对话历史（模型能看见自己上次失败了） | 本地源码 `packages/ai/src/types.ts:314-324`、`packages/agent/src/types.ts:28-32` |
| **孤儿 tool_call 补合成 result** | 中断后历史里会留下「有 tool_call 无 tool_result」的空洞。pi 在 `transform-messages.ts` 第二遍扫描给孤儿 tool call 补 `"No result provided"` 的错误 result——这是 abort 后还能继续对话的关键 | 本地源码 `packages/ai/src/api/transform-messages.ts:156+` |
| **截断即失败重发** | `stopReason === "length"` 时，工具参数可能不完整 → 把整批 tool call 标记失败让模型重发，而不是拿半截 JSON 去执行 | 本地源码 `agent-loop.ts:213` |
| **持久执行 + 断点续跑** | "we need to **durably execute code** and handle errors along the way… we built systems that can **resume from where the agent was when the errors occurred**" | [Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system) |
| **把错误交给模型自适应** | "letting the agent know when a tool is failing and letting it adapt works surprisingly well" | 同上 |
| **彩虹发布（rainbow deployments）** | "We use **rainbow deployments** to avoid disrupting running agents, by gradually shifting traffic from old to new versions while keeping both running simultaneously." —— 长跑 agent 不能被滚动重启打断 | 同上 |

补充：12-Factor Agents 的 **Factor 9「Compact Errors into Context Window」**主张把错误压缩后回灌上下文，而不是原样堆栈刷屏（[humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)）。

Anthropic 关于 debug 难度的原文（做「错误恢复为什么难」的引子很好用）：
> "Agents make dynamic decisions and are **non-deterministic between runs, even with identical prompts**. This makes debugging harder." / "minor system failures can be **catastrophic for agents**"（因为 agent 是**有状态**的长跑进程）
> —— [Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)

---

## 2. Anthropic《Building Effective Agents》：五种 workflow 模式 + agent 定义边界

**出处**：[Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)，[博客发布日] **2024-12-19**。
（注：网页标题为 "Building **Effective AI Agents**"，业内常引作 "Building Effective Agents"；HN 讨论帖 [42470541](https://news.ycombinator.com/item?id=42470541) 同期。另有 PDF 版 [resources.anthropic.com](https://resources.anthropic.com/building-effective-ai-agents)。）

### 2.1 定义边界（必须准确引用）

> **Agentic systems** 是伞形概念，下分两类：
> - **Workflows** are "systems where LLMs and tools are orchestrated through **predefined code paths**."
> - **Agents** are "systems where LLMs **dynamically direct their own processes and tool usage**, maintaining control over how they accomplish tasks."

**基础构件**：**Augmented LLM** = "an LLM enhanced with augmentations such as **retrieval, tools, and memory**."

### 2.2 五种 workflow 模式（确切名称 + 适用场景，逐字）

| # | 确切名称 | 定义 / 机制（原文） | "When to use"（原文） |
|---|---|---|---|
| 1 | **Prompt chaining** | 把任务拆成顺序步骤，每次 LLM 调用处理上一步输出，中间可插**programmatic checkpoints**（gate）做校验 | "ideal for situations where the task can be easily and cleanly decomposed into **fixed subtasks**." |
| 2 | **Routing** | "classifies an input and directs it to a **specialized followup task**." | "works well for complex tasks where there are **distinct categories that are better handled separately**." |
| 3 | **Parallelization** —— 两个变体：<br>· **Sectioning**：'Breaking a task into **independent subtasks** run in parallel.'<br>· **Voting**：'Running the **same task multiple times** to get diverse outputs.' | 同左 | "effective when the divided subtasks can be **parallelized for speed**, or when **multiple perspectives or attempts** are needed." |
| 4 | **Orchestrator-workers** | "a **central LLM dynamically breaks down tasks**, delegates them to worker LLMs, and **synthesizes** their results." | "well-suited for complex tasks where you **can't predict the subtasks** needed." |
| 5 | **Evaluator-optimizer** | "one LLM call generates a response while another provides **evaluation and feedback in a loop**." | "particularly effective when we have **clear evaluation criteria**, and when **iterative refinement** provides measurable value." |

**Agents（非 workflow）**："can be used for **open-ended problems** where it's difficult or impossible to **predict the required number of steps**."

### 2.3 取舍原文（PPT 金句）

> "Agentic systems often **trade latency and cost for better task performance**."
> "**workflows offer predictability and consistency** for well-defined tasks, whereas **agents are the better option when flexibility and model-driven decision-making are needed at scale**."

> ⚠️ 讲稿提醒：常见误引是把 orchestrator-workers 说成「multi-agent」。Anthropic 原文把它归为 **workflow**，与第 5 节的 multi-agent 研究系统是**两个不同层级**的东西——orchestrator-workers 的编排骨架仍写在代码里，只是子任务的**划分**交给了中心 LLM。

---

## 3. Graph Engineering：LangGraph 的状态图模型

**一手文档**：[docs.langchain.com/oss/python/langgraph](https://docs.langchain.com/oss/python/langgraph/graph-api)

### 3.1 四个原语（逐字定义）

| 原语 | 官方定义 |
|---|---|
| **State** | "A shared data structure that represents the **current snapshot** of your application… typically defined using a shared **state schema**." |
| **Nodes** | "**Functions** that encode the logic of your agents. They receive the current state as input, perform some computation or side-effect, and **return an updated state**." |
| **Edges** | "Functions that determine **which Node to execute next** based on the current state. They can be **conditional branches or fixed transitions**." |
| 一句话总结 | "**nodes do the work, edges tell what to do next**." / "Nodes and Edges are nothing more than functions—they can contain an LLM or **just good ol' code**." |

### 3.2 执行模型：super-step（Pregel / BSP）

> "A **super-step** can be considered a single iteration over the graph nodes. **Nodes that run in parallel are part of the same super-step**, while nodes that run sequentially belong to **separate super-steps**."
> "The graph execution **terminates when all nodes are inactive and no messages are in transit**."
> —— [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)

> 这一句是「Graph Engineering 到底解决了什么」的核心：**它把「什么时候算一轮结束」从模型的判断变成了图算法的不动点判定**。

### 3.3 Checkpoint / 持久化：它真正解决的四件事

[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) 官方列出的用途：**conversation continuity（会话续跑）/ human-in-the-loop workflows / time travel / fault tolerance**。原文：
> 持久化 "matters when an agent needs to **continue a conversation, resume after an interruption, recover from a failure, or remember information across interactions**."
> Checkpointer 的职责是 "persist a **thread's** graph state as **checkpoints**."

**Durability 三档**（性能 vs 一致性权衡，`durability` 参数）：
- `"exit"`：仅在图执行退出时落盘（最快、最不耐崩）
- `"async"`：下一步执行的同时**异步**落盘
- `"sync"`：下一步开始前**同步**落盘（最耐崩、开销最大）
—— [LangChain Reference: Durability](https://reference.langchain.com/python/langgraph/types/Durability)

### 3.4 Human-in-the-loop 断点

[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) 要点：
- `interrupt()` 在 node 内调用 → 运行时捕获异常 → **通过 checkpointer 保存状态** → 无限期挂起。
- **"A checkpointer is mandatory."** `thread_id` 是持久游标：复用则从 checkpoint 续跑，换新 ID 则重新开始。
- 恢复用 `Command(resume=...)`，resume 值成为原 `interrupt()` 调用的返回值。
- 官方列的四种 HITL 模式：**approval workflows**（关键动作前暂停）/ **review and edit**（人改 LLM 输出或 tool call）/ **tool interrupts**（在工具函数内部暂停批准）/ **input validation**（无效输入重问）。
- ⚠️ **最重要的坑**："**Nodes re-execute from the beginning on resume.** Any code before the `interrupt()` call runs again, so **side effects must be idempotent**."

### 3.5 时间旅行：replay vs fork

[Use time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)：
> "**Replay past executions and fork to explore alternative paths** in LangGraph."

| 操作 | 步骤 | 语义 |
|---|---|---|
| **Replay** | ① `get_state_history()` 找 checkpoint → ② 选定 `checkpoint_id` → ③ 带该 config 调 `invoke()` | ⚠️ "Replay **re-executes nodes**—it doesn't just read from cache. LLM calls, API requests, and interrupts **fire again and may return different results**." |
| **Fork** | ① 对旧 checkpoint 调 `update_state()` 写入新值 → ② `invoke(None, fork_config)` | "creates a **new checkpoint that branches** from the specified point. The **original execution history remains intact**." fork 点之后的 node 用新 state 重跑，之前的结果保持缓存 |

### 3.6 DAG 编排 vs 自主循环：怎么讲这个取舍

| 维度 | DAG / 状态图（LangGraph、Airflow 式） | 自主循环（Claude Code / pi 式） |
|---|---|---|
| 谁决定下一步 | **边（代码）**，`nodes do the work, edges tell what to do next` | **模型**，"LLMs dynamically direct their own processes"（Anthropic 定义） |
| 终止判定 | 图不动点：所有 node inactive 且无消息在途 | 无 tool_call / done 工具 / max_turns / 预算 / 中断 |
| 可复现性 | 高（super-step 边界 + checkpoint 可精确重放到某点） | 低（"non-deterministic between runs, even with identical prompts"） |
| 断点粒度 | node 边界（`interrupt()`） | turn 边界（save point / checkpoint） |
| 代价 | 图要人写；步骤数不可预测时会爆炸 | latency & cost（Anthropic：agentic systems "trade latency and cost for better task performance"） |
| 适用 | 子任务**可预测**、有固定结构 | "open-ended problems where it's difficult or impossible to **predict the required number of steps**" |

> 注意 LangGraph 并非纯 DAG：它支持环（cycle），本质是 Pregel 消息传递模型；把它简单说成 "DAG 编排" 是**不准确**的。准确说法是「**显式状态图 + 超步执行 + 可 checkpoint**」。

---

## 4. 会话树（session tree）：append-only 事件日志 + 分支 / fork / rewind

### 4.1 为什么是 append-only 事件日志

三点价值（可直接做 PPT 三栏）：
1. **可复现**：日志本身就是完整状态，任意时刻可重建。
2. **可回溯**：错了不用从头开始——回到某个 entry 继续。
3. **可并行探索**：同一祖先长出多条分支，互不污染。

### 4.2 Claude Code：JSONL 事件日志 + `/rewind` + `/branch`

**存储**（[Manage sessions](https://code.claude.com/docs/en/sessions)）：
> "By default, transcripts are stored as **JSONL** at `~/.claude/projects/<project>/<session-id>.jsonl` … **Each line is a JSON object** for a message, tool use, or metadata entry."
> ⚠️ 官方警告："The entry format is **internal** to Claude Code and **changes between versions**, so scripts that parse these files directly can break on any release."

**Checkpointing / `/rewind`**（[Checkpointing](https://code.claude.com/docs/en/checkpointing)）：
- 何时建 checkpoint：**"Every user prompt creates a new checkpoint"**；仅保留会话内**最近 100 个** checkpoint 的文件快照。
- 触发方式：`/rewind`，或在输入框为空时**连按两次 `Esc`**。
- 六个动作（原文）：**Restore code and conversation** / **Restore conversation** / **Restore code** / **Summarize from here** / **Summarize up to here** / **Never mind**。
- 保留期：随 session 一起 **30 天**后删除，可用 `cleanupPeriodDays` 调整。
- **限制**（讲稿必提，很有说服力）：
  - **Bash 命令改动不追踪**——`rm/mv/cp` 造成的改动 rewind 不回来。
  - **Subagent 的编辑不在本 session 的 checkpoint 内**（除前台 `context: fork` 的 skill 外），需用 git 回退。
  - 外部改动不追踪；**symlink / hardlink 路径跳过不还原**，会提示 `Restored the code, but skipped N files`。
  - 官方定位："Think of checkpoints as **'local undo'** and **Git as 'permanent history'**."

**版本溯源**：`/rewind` 随 **Claude Code v2.0.0** 发布，changelog 原文 "`/rewind` a conversation to undo code changes"（[CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)）。v2.0.0 与 Claude Sonnet 4.5 同日发布，[版本发布日] **2025-09-29**（见 [Boris Cherny 的发布串](https://www.threads.com/@boris_cherny/post/DPMaIxFEa41/)；官方博客口径**待核实**具体页面）。
2026-06-25 的 v2.1.191 起，`/rewind` 可以**跨 `/clear` 恢复到清空前的会话**（[Checkpointing · Rewind past a cleared conversation](https://code.claude.com/docs/en/checkpointing)）。

**Branch / Fork**（[Manage sessions · Branch a session](https://code.claude.com/docs/en/sessions)）：
> "Branching **creates a copy of the conversation so far and switches you into it, leaving the original intact**."
- 命令：会话内 `/branch [name]`；命令行 `claude --continue --fork-session`。
- "The `/branch` confirmation prints **two session IDs**: the new branch you are now in and the original."
- 会话选择器里 "Sessions created with `/branch` or `--fork-session` get their own session IDs and appear as separate rows"，同源的会被**归组**（`→` 展开）。
- 官方对 rewind vs branch 的区分原文：
  > "Summarize keeps you in the **same session** and compresses context, like a targeted `/compact`. To **branch off and try a different approach while preserving the original session intact**, use `/branch` or `claude --continue --fork-session`."
- resume vs fork 的一句话（[How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)）：
  > "Resuming … reopens it under the **same session ID** and appends new messages… **Forking** with `--fork-session` or `/branch` **copies the history into a new session ID**, leaving the original unchanged."

### 4.3 pi：真正的**树形** session（本地源码）

pi 不是「线性日志 + 分支拷贝」，而是**日志本身就是树**。已核实的源码位置：

| 事实 | 位置 |
|---|---|
| session entry 带 `parentId: string \| null` | `packages/agent/src/harness/types.ts:378` |
| harness 的树导航 API `navigateTree()`，要求 `phase === "idle"` 否则抛 `AgentHarnessError("busy")` | `packages/agent/src/harness/agent-harness.ts:842,847` |
| fork：从目标节点向上读到 root 或 compaction 点 | `packages/agent/src/harness/session/fork.ts:22` `reader.readPathToRootOrCompaction(target.parentId)` |
| 追加 entry 时 `parentId: this.leafId` —— 典型的**指向父节点的 append-only 树** | `packages/agent/src/harness/session/session.ts:339` |
| 分支摘要沿 parent 链回溯 | `packages/agent/src/harness/compaction/branch-summarization.ts:95` |
| JSONL store（默认后端） | `packages/agent/src/harness/session/jsonl-store.ts` |

**SQLite 后端的 schema**（本仓库 `analysis/raw/03-pi-protocol-server-storage.md`，源自 `migrations/001_initial.sql`）：
- `sessions(id, created_at, cwd, **parent_session_id**, metadata, **active_leaf_id**)` —— 连 session 之间都成树。
- `session_entries(session_id, id, entry_seq, **parent_id**, type, timestamp, payload)`，UNIQUE(session_id, entry_seq)。**存的是树，不是线性日志。**
- **11 种 entry 类型**：`message`、`thinking_level_change`、`model_change`、`active_tools_change`、`compaction`、`branch_summary`、`custom`、`custom_message`、`label`、`session_info`、`leaf`。
  → 讲稿点：**「换模型」「改 thinking 档位」「换工具集」本身就是事件**，所以整条历史可以精确重放，而不只是消息序列。
- `branch_entries(session_id, branch_id, entry_id, entry_seq)` 是**分支物化表**：切换/分叉生成新 `branch_id`（uuidv7），把整条路径逐行插入。代价 O(路径长度)，且旧 branch 行不回收（已知单调增长问题）。
- 全文检索 `session_search_fts` 用 **FTS5 + trigram** 分词（支持中文/代码任意子串），`bm25()` 排序。
- 并发：单连接 + `SerialOperationQueue` 全局串行；跨进程只靠 WAL 锁 + `busy_timeout=5000`。
- Phase 状态机：`"idle" | "turn" | "compaction" | "branch_summary" | "retry"`。

**pi harness 的持久化时序**（`agent-harness.ts` 的 `handleAgentEvent`）：`message_end` → 立即 `session.appendMessage`；`turn_end` → flush `pendingSessionWrites` → 发 `save_point`；`agent_end` → flush → `phase = "idle"` → 发 `settled`。扩展在忙时发起的写入排队，只在 save point 落盘，**保证 transcript 顺序纯净**。

> 三者的谱系可以这样画：**Cursor = 文件快照**（只回滚代码）→ **Claude Code = 快照 + 线性 JSONL + 拷贝式分支** → **pi = 天然树形事件日志（parentId）+ 物化分支表 + 树导航 API**。

### 4.4 Cursor checkpoints

[Cursor Docs · Checkpoints](https://cursor.com/docs/agent/chat/checkpoints)：
> "Checkpoints save **snapshots of your codebase** during an Agent session"（捕获 "the state of all modified files"）。
> "Agent **automatically creates them before making significant changes**."
> 恢复：点击 chat timeline 上的任一 checkpoint 预览，再 restore 把所有文件回滚到该状态；也可用 previous request 上的 "Restore Checkpoint" 按钮。
> 明确定位："Checkpoints are stored **locally and separate from Git**. Only use them for **undoing Agent changes**; use **Git for permanent version control**."

> ⚠️ 与 Claude Code 的差别：Cursor 的 checkpoint 是**代码快照**导向；Claude Code 的 `/rewind` 把**代码**与**对话**拆成两个可独立回滚的维度（Restore code / Restore conversation / 两者都要）。这一点值得在 PPT 上对比。

---

## 5. Multi-agent / Subagent：两方观点都要写

### 5.1 支持方：Anthropic《How we built our multi-agent research system》

[博客发布日] **2025-06-13**，[anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)

**架构**：
> "multi-agent architecture with an **orchestrator-worker pattern**, where a **lead agent** coordinates the process while delegating to **specialized subagents that operate in parallel**."

**核心数字（务必用原口径）**：

| 指标 | 数值 | 原文 |
|---|---|---|
| token 放大 | agent ≈ **4×** chat；multi-agent ≈ **15×** chat | "agents typically use about **4× more tokens** than chat interactions, and multi-agent systems use about **15× more tokens** as chats" |
| 效果提升 | **90.2%** | "a multi-agent system with **Claude Opus 4 as the lead agent** and **Claude Sonnet 4 subagents** outperformed **single-agent Claude Opus 4 by 90.2%** on our internal research eval" |
| 方差归因 | **80%** | "**token usage by itself explains 80% of the variance**, with the number of tool calls and the model choice as the two other explanatory factors"（BrowseComp 分析） |
| 并行工具调用提速 | **最高 90%** | "Parallel tool calling transforms speed and performance… **cut research time by up to 90%** for complex queries" |

> ⚠️ **口径提醒（很容易被听众抓错）**：
> - 「4×/15×」是**相对 chat 交互**的粗略倍数（原文用 "about"），**不是** multi-agent 相对 single-agent 的倍数。若要说后者，正确的推算是 15/4 ≈ **3.75 倍**，但这属于二次推导，**原文没有这个数字**，上台请标注为推算。
> - 「90.2%」是**内部 research eval** 上的相对提升，不是公开 benchmark。
> - 「80% 方差」的语境是 **BrowseComp**。

**主要收益 = 上下文隔离**：
> "Multi-agent systems excel at valuable tasks that involve **heavy parallelization**, **information that exceeds single context windows**, and **interfacing with numerous complex tools**."
> "Subagents act as **intelligent filters**"，靠 "**separation of concerns**—distinct tools, prompts, and exploration trajectories—which **reduces path dependency** and enables thorough, independent investigations."
> "Each subagent needs an **objective**, an **output format**, **guidance on the tools and sources** to use, and **clear task boundaries**."

**何时不该用**：
> "some domains that require **all agents to share the same context** or involve **many dependencies between agents** are **not a good fit** for multi-agent systems today… **most coding tasks involve fewer truly parallelizable tasks than research**."

**长跑手段**：
> "Agents can **spawn fresh subagents with clean contexts** while maintaining continuity through **careful handoffs**"；上下文快满时可以 "retrieve stored context like the research plan from their **memory** rather than losing previous work when reaching the context limit."

### 5.2 反对方：Cognition《Don't Build Multi-Agents》

作者 **Walden Yan**（Cognition，Devin 团队），[博客发布日] **2025-06-12**（页面标注 `06.12.25`）。
原址 `cognition.ai/blog/dont-build-multi-agents` 已 **301 重定向**到 [cognition.com/blog/dont-build-multi-agents](https://cognition.com/blog/dont-build-multi-agents)（引用请用新址）。

> 时间线彩蛋：Cognition 06-12、Anthropic 06-13，**两篇立场相反的文章相隔 24 小时**——这是讲这一节最好的开场。

**两条原则（逐字）**：
- **Principle 1**: "**Share context, and share full agent traces, not just individual messages**"
- **Principle 2**: "**Actions carry implicit decisions, and conflicting decisions carry bad results**"

**Flappy Bird 反例（原文）**：把"做一个 Flappy Bird 克隆"拆给并行子 agent 后——
> "**Subagent 1 actually mistook your subtask and started building a background that looks like Super Mario Bros. Subagent 2 built you a bird, but it doesn't look like a game asset.**"

**对现有框架的批评（逐字）**：OpenAI **Swarm** 和 Microsoft **AutoGen** 这类库
> "actively push concepts which I believe to be **the wrong way of building agents**. Namely, using **multi-agent architectures**."

**主张的替代方案**：
1. **单线程线性 agent**（连续上下文）；
2. 长任务上下文溢出时，用 "a new LLM model whose key purpose is to **compress a history of actions & conversation into key details, events, and decisions**"（**专门的压缩模型**，而非拆多 agent）。

**对 Claude Code subagent 的观察（原文，很关键）**：
> "It **never does work in parallel** with the subtask agent, and the subtask agent is usually **only tasked with answering a question, not writing any code**."
> → 潜台词：Claude Code 的 subagent 是**只读的信息过滤器**，不是并行的写作者。这与 Anthropic 自己在 5.1 说的 "Subagents act as intelligent filters" 完全一致——**两派其实在这一点上并不冲突**。

### 5.3 2026 年的收敛：Cognition 自己更新了立场

**《Multi-Agents: What's Actually Working》**，作者仍是 **Walden Yan**，[博客发布日] **2026-04-22**，[cognition.com/blog/multi-agents-working](https://cognition.com/blog/multi-agents-working)

> "A lot has changed since then" —— "we've begun to **deploy multi-agent systems that actually work in practice**."

**现在认为能用的三种模式**：
1. **Code-Review Loop**：评审 agent **不共享**编码 agent 的上下文，反而能抓到 bug——"**clean context leads to a notable improvement in capabilities when using a generator-verifier loop**"（与 Principle 1 的表面矛盾，作者自己点名是「反直觉」）。
2. **Smart Friend Pattern**：弱模型在难点上调用更强模型求助。
3. **Manager-Child Delegation**：管理者拆解任务并派生子 agent，但**需要大量 context engineering**。

**仍然不работает 的**：
> "the **unstructured-swarm** approach, arbitrary networks of agents negotiating with each other, is **mostly a distraction**"；并行**写**的 agent 依然有问题。

**统一原则（本节最佳收尾金句）**：
> "**Multi-agent systems work best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions.**"

### 5.4 第三方裁判：LangChain

**《How and when to build multi-agent systems》**，作者 **Harrison Chase**，[博客发布日] **2025-06-16**（即两篇对撞后第 3 天），[langchain.com/blog](https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems)

核心论断：多 agent 失败的根因是 **context engineering 没做好**，而非"多 agent"本身。
最有用的一刀切判据：
> "**read actions are inherently more parallelizable than write actions**."
文中引 Anthropic 的失败案例：一个 subagent 在查 2021 年汽车芯片危机，另外 2 个重复地在查 2025 年供应链，缺乏有效分工。

### 5.5 落到产品：Claude Code 的两级并行（2026 现状）

[Sub-agents](https://code.claude.com/docs/en/sub-agents) vs [Agent teams](https://code.claude.com/docs/en/agent-teams)（官方对比表逐字）：

| | **Subagents** | **Agent teams** |
|---|---|---|
| Context | "Own context window; **results return to the caller**" | "Own context window; **fully independent**" |
| Communication | "Report results back to the **main agent only**" | "Teammates **message each other directly**" |
| Coordination | "Main agent manages all work" | "**Shared task list** with self-coordination" |
| Best for | "Focused tasks where **only the result matters**" | "Complex work requiring **discussion and collaboration**" |
| Token cost | "**Lower**: results summarized back to main context" | "**Higher**: each teammate is a separate Claude instance" |

Agent teams 关键事实：
- **实验性、默认关闭**：需设 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`。文档以 **v2.1.178** 为基准描述。
- 组件四件套：**Team lead / Teammates / Task list / Mailbox**。mailbox 是 JSON 文件：`~/.claude/teams/{team-name}/inboxes/{agent-name}.json`；team config `~/.claude/teams/{team-name}/config.json`；task list `~/.claude/tasks/{team-name}/`。团队名 = `session-` + session ID 前 8 位。
- 官方建议规模：**"Start with 3-5 teammates for most workflows."**；**"Having 5-6 tasks per teammate"**；"**Three focused teammates often outperform five scattered ones.**"
- 任务认领用**文件锁**防竞态。
- 已知限制（讲稿好料）：**`/resume` 和 `/rewind` 不恢复 in-process teammates**；不能嵌套团队；一个 session 只能有一个 team；lead 身份固定不可转移。
- 成本："Agent teams **use significantly more tokens** than a single session… token usage **scales with the number of active teammates**."

**上下文隔离作为主要收益（官方原话）**：
> "[Subagents](https://code.claude.com/docs/en/sub-agents) get their own **fresh context, completely separate** from your main conversation. Their work **doesn't bloat your context**. When done, they **return a summary**. **This isolation is why subagents help with long sessions.**"
> —— [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)

Anthropic 的 context engineering 博客给出了**具体数量级**：
> Sub-agent "returns only a **condensed, distilled summary** of its work (often **1,000-2,000 tokens**)."
> —— [博客发布日] **2025-09-29**，[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

同篇还提供了「为什么必须隔离」的机理表述：
> "LLMs have an '**attention budget**' … **Every new token introduced depletes this budget** by some amount."
> "As the number of tokens in the context window increases, the model's ability to **accurately recall information** from that context **decreases**."（即 **context rot**）
> 目标："Find the **smallest set of high-signal tokens** that maximize the likelihood of your desired outcome."
三种长任务技术：**Compaction** / **Structured note-taking** / **Sub-agent architectures**。

---

## 6. 确定性编排 vs 模型自主：可判断的准则清单

### 6.1 官方给的两条基线

**Anthropic**（[BEA](https://www.anthropic.com/engineering/building-effective-agents)）：
> "**workflows offer predictability and consistency for well-defined tasks**, whereas **agents are the better option when flexibility and model-driven decision-making are needed at scale**."
> 通用建议：找到最简单的方案，"only increasing complexity when needed"。

**OpenAI Agents SDK**（[Orchestrating multiple agents](https://openai.github.io/openai-agents-python/multi_agent/)）：
- **Orchestrating via LLM**："Allowing the LLM to make decisions: this uses the intelligence of an LLM to **plan, reason, and decide on what steps to take**." → 适合开放式任务。
- **Orchestrating via code**："Determining the flow of agents **via your code**" → 更**确定、可预测**（速度/成本/表现）。
  官方列的代码编排四招：① 用 **structured outputs** 产出可被代码检查的数据；② 把上一个 agent 的输出**变换成**下一个的输入（链式）；③ 在 **loop + evaluator** 里跑直到达标；④ `asyncio.gather` **并行**。

### 6.2 可执行的判断清单（综合多个一手来源，每条注明依据）

**→ 用代码写死（确定性编排），当：**

| # | 判据 | 依据 |
|---|---|---|
| D1 | 子任务**可以被清晰、固定地拆分** | Anthropic prompt chaining："task can be easily and cleanly decomposed into **fixed subtasks**" |
| D2 | 输入存在**明确的类别划分**，不同类别处理方式差异大 | Anthropic routing："distinct categories that are better handled separately" |
| D3 | 需要**可复现 / 可审计**（合规、金融、回归测试） | LangGraph super-step + checkpoint 提供确定的重放边界；反例见 Anthropic "non-deterministic between runs, even with identical prompts" |
| D4 | 需要**成本 / 延迟可预算** | OpenAI："make tasks more **deterministic and predictable** regarding **speed, cost, and performance**" |
| D5 | 动作有**外部副作用且不可回滚**（DB 写、部署、支付） | Claude Code 文档："Actions that affect remote systems (databases, APIs, deployments) **can't be checkpointed**, which is why Claude asks before running commands with external side effects."（[How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)） |
| D6 | 写操作需要**串行化**以避免冲突决策 | Cognition 2026："**writes stay single-threaded**"；LangChain："read actions are inherently more parallelizable than write actions" |
| D7 | 已有**明确的评估标准**且迭代能带来可测量收益 → 用 evaluator-optimizer 这种**有骨架**的循环 | Anthropic："clear evaluation criteria… iterative refinement provides measurable value" |

**→ 交给模型决策（自主循环），当：**

| # | 判据 | 依据 |
|---|---|---|
| A1 | **无法预测所需步骤数** | Anthropic："open-ended problems where it's difficult or impossible to **predict the required number of steps**" |
| A2 | **无法预测子任务是什么** → orchestrator-workers | Anthropic："complex tasks where you **can't predict the subtasks** needed" |
| A3 | 任务是**广度优先探索**，方向彼此独立 | Anthropic multi-agent："**breadth-first** queries… multiple independent directions"（LangChain 转述同源） |
| A4 | 信息量**超出单个上下文窗口** | Anthropic："information that **exceeds single context windows**" |
| A5 | 任务**价值足够高**，付得起 token 账单 | Anthropic："the value of the task is high enough to pay for the increased performance" |
| A6 | 需要在规模上**灵活适配**，写死规则会爆炸 | Anthropic："flexibility and model-driven decision-making are needed **at scale**" |

**→ 明确不要上多 agent，当：**

| # | 判据 | 依据 |
|---|---|---|
| N1 | 所有 agent **必须共享同一份上下文** | Anthropic："domains that require **all agents to share the same context**… are **not a good fit**" |
| N2 | agent 之间**依赖繁多** | Anthropic："involve **many dependencies between agents**" |
| N3 | 任务是**写代码**（可并行部分远少于 research） | Anthropic："most **coding tasks** involve **fewer truly parallelizable tasks** than research" |
| N4 | 会出现**并行写同一批文件** | Claude Code agent-teams 文档："Two teammates editing the same file **leads to overwrites**." |
| N5 | 是「无结构 swarm / 任意 agent 互相协商」 | Cognition 2026："the **unstructured-swarm** approach… is **mostly a distraction**" |

**→ 拆多 agent 的正向信号（OpenAI 的两条具体判据，很实用）：**

| # | 判据 | 原文 |
|---|---|---|
| S1 | **Complex logic** | "When prompts contain **many conditional statements (multiple if-then-else branches)**, and prompt templates get difficult to scale, consider dividing each logical segment across separate agents." |
| S2 | **Tool overload** | "The issue is **not solely the number of tools, but their similarity or overlap**. Some implementations successfully manage **more than 15 well-defined, distinct tools** while others struggle with **fewer than 10 overlapping tools**." |
| 前置条件 | 先把单 agent 做到极致 | "Our general recommendation is to **maximize a single agent's capabilities first**." / 结论章："starting with a **single agent** and evolving to multi-agent systems **only when needed**." |
| 不换框架的降复杂度手段 | **prompt templates + policy variables** | "use a **single flexible base prompt that accepts policy variables**… update variables rather than rewriting entire workflows." |
| —— | 均出自 [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) 第 16–17、32 页 | |

**OpenAI 的多 agent 两种拓扑（准确名称）**：
> **Manager (agents as tools)**："A central 'manager' agent coordinates multiple specialized agents **via tool calls**."
> **Decentralized (agents handing off to agents)**："Multiple agents operate as **peers, handing off tasks** to one another based on their specializations."
> 统一视角："Multi-agent systems can be modeled as **graphs, with agents represented as nodes**. In the manager pattern, **edges represent tool calls**; in the decentralized pattern, **edges represent handoffs** that transfer execution between agents."

**OpenAI 对 agent 的定义边界（与 Anthropic 对照）**：
> "**Agents are systems that independently accomplish tasks on your behalf.**"
> "Applications that integrate LLMs but **don't use them to control workflow execution**—think **simple chatbots, single-turn LLMs, or sentiment classifiers**—are **not agents**."
> "It leverages an LLM to manage workflow execution and make decisions. It **recognizes when a workflow is complete** and can proactively **correct its actions** if needed. In case of failure, it can **halt execution and transfer control back to the user**."

### 6.3 补充判据：12-Factor Agents（工程侧 checklist）

[humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)，作者 **Dex Horthy**（HumanLayer）。12 条标题逐字：

1. Natural Language to Tool Calls
2. Own your prompts
3. Own your context window
4. Tools are just structured outputs
5. Unify execution state and business state
6. Launch/Pause/Resume with simple APIs
7. Contact humans with tool calls
8. **Own your control flow**
9. Compact Errors into Context Window
10. **Small, Focused Agents**
11. Trigger from anywhere, meet users where they are
12. Make your agent a stateless reducer

对纯循环的批评（原文）：
> agent 循环 = "LLM determines the next step in the workflow, outputting structured json ('tool calling'), deterministic code executes the tool call, the result is appended to the context window, repeat until done."
> 但 "at the end of the day, this approach **just doesn't work as well as we want it to**." —— 大家做到 **70-80%** 质量线，然后发现 "**80% isn't good enough** for most customer-facing features"，只能推倒重来。

**Factor 10 的量化主张**（很适合做 PPT 上的一条准则）：
> 每个 agent 保持 "**3-10, maybe 20 steps max**"；理由是 "**As context grows, LLMs are more likely to get lost or lose focus.**"
> 面向未来的论证：模型变强后，可以**逐步扩大** agent 的作用域，而不必推倒重构。
> —— [factor-10-small-focused-agents.md](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md)

> ⚠️ 该仓库的 star 数（约 23.5k）与最后 push 时间（2025-09）来自二手搜索结果，**待核实**，上台不要用。

---

## 7. Agentic RL / 长任务能力：模型侧 2025–2026 的进展

### 7.1 METR「任务时长翻倍」研究 —— 确切结论与日期

**论文**：arXiv **2503.14499**
- **v1 提交日 [arXiv 预印本日]：2025-03-18**；v2：2025-03-30；**v3：2026-02-25**；**v4：2026-07-10**（[arxiv.org/abs/2503.14499](https://arxiv.org/abs/2503.14499)）
- ⚠️ **标题有变更**：当前 arXiv 页面标题为「**Measuring AI Ability to Complete Long Software Tasks**」；社区广泛引用的旧名是「Measuring AI Ability to Complete Long Tasks」。**引用时请用当前标题并注明版本**。
- **作者**：Thomas Kwa、Ben West、Joel Becker、Amy Deng… Elizabeth Barnes、Lawrence Chan（共 26 位署名）
- **配套博客 [博客发布日]：2025-03-19**，[metr.org/blog/2025-03-19-…](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)

**摘要中的确切结论（逐字）**：
> "we propose a new metric: **50%-task-completion time horizon**. This is **the time humans typically take to complete tasks that AI models can complete with 50% success rate**."
> "On these tasks, current frontier AI models such as **Claude 3.7 Sonnet have a 50% time horizon of around 50 minutes**."
> "frontier AI time horizon has been **doubling approximately every seven months since 2019**, though **the trend may have accelerated in 2024**."

博客版表述（更常被引用）：
> "the length of tasks … that generalist frontier model agents can complete autonomously with **50% reliability** has been **doubling approximately every 7 months for the last 6 years**"

**方法**：对 170 个任务（RE-Bench + HCAST + 66 个新的短任务 SWAA）先用领域专家人类计时，再评测 2019–2025 间发布的 13 个前沿模型。

> ⚠️ 极易讲错的三点：
> 1. 这是 **50% 成功率**下的时间跨度，**不是**「AI 能连续工作 50 分钟」。
> 2. 「7 个月」是**全历史拟合**（2019 起），原文自己就说 2024 后**可能加速**。
> 3. 任务域是**软件工程 / 网安 / 通用推理**，不是所有工作。

### 7.2 METR Time Horizon 1.1（2026 年更新，务必用这一版数字）

[博客发布日] **2026-01-29**，[metr.org/blog/2026-1-29-time-horizon-1-1/](https://metr.org/blog/2026-1-29-time-horizon-1-1/)

**方法学变化**：
- 任务集从 **170 → 228** 个（新增 73、移除 15、更新 53）；**8 小时以上的长任务从 14 → 31** 个。
- 评测基建从自研 **Vivaria** 迁移到 UK AI Security Institute 的开源 **Inspect** 框架。

**倍增时间（TH1.1 口径）**：

| 拟合窗口 | TH1.1 | 对比 TH1.0 |
|---|---|---|
| 全历史（hybrid 方法） | **196 天（≈7 个月）** | 与 TH1.0 一致 |
| **2023 年以来** | **131 天** | TH1.0 为 165 天 → 快约 20% |
| **2024 年以来** | **89 天** | TH1.0 为 109 天 |

**单模型 50% 时间跨度（TH1.1）**：

| 模型 | TH1.1 估计 | 相对 TH1.0 变化 |
|---|---|---|
| **Claude Opus 4.5** | **320 分钟**（≈5.3 小时） | +11% |
| **GPT-5** | **214 分钟** | +55% |
| **o3** | **121 分钟** | +29% |
| **Claude Opus 4** | **101 分钟** | +18% |

**METR 自己的谨慎结论**：确实有加速迹象，但部分变化来自新任务集**难度分布不同**，而非纯粹的能力加速。

### 7.3 METR Frontier Risk Report（2026-05-19）—— 最新一手数据

[metr.org/blog/2026-05-19-frontier-risk-report/](https://metr.org/blog/2026-05-19-frontier-risk-report/)（覆盖 2026 年 2–3 月）

- **测量天花板已到**（原文脚注）："The **TH 1.1 suite can't reliably measure time horizons above 16 hours**, but the **50% time horizon point estimate of the most capable shared model was between 16 and 20 hours**."
- 正文表述："their measured time horizon was **over two full-time-equivalent days**, though we are increasingly **uncertain about the point estimate due to saturation**."
- 引入新基准 **MirrorCode**（与 Epoch AI 合作的**软件复现**基准）："public models in Feb–Mar 2026 had **several times longer time horizons** on the software reimplementation tasks in **MirrorCode-Early** than they did on the broader **Time Horizon 1.1** suite."
- 反向结论同样重要：在考察**战略判断 / 隐蔽性**的基准上，agent 表现"significantly weaker"。
- 时间跨度追踪页 [metr.org/time-horizons](https://metr.org/time-horizons/) 最后更新 **2026-05-08**，页面明写 "**Measurements above 16 hrs are unreliable with our current task suite.**"

> ⚠️ **待核实**：首轮抓取时该页摘要提到 "Opus 4.6 / GPT-5.2 / GPT-5.4" 等具体型号与 16–20 小时的对应关系；二轮精确抓取只确认了 "the **most capable shared model**" 这一匿名表述。**上台请只说「最强的受测模型 50% 时间跨度点估计在 16–20 小时之间（TH1.1 口径，已接近该套件测量上限）」，不要点名具体型号**，除非二次核对原文。
>
> ⚠️ 另需注意：**TH1.1 与 MirrorCode 口径不可互换**。MirrorCode 上的时长「数倍于」TH1.1，因为任务性质更单一（复现已有软件）。

### 7.4 Agentic RL：模型侧为什么能变长

**综述**：《**The Landscape of Agentic Reinforcement Learning for LLMs: A Survey**》，arXiv **2509.02547**
- **v1 [arXiv 预印本日]：2025-09-02**；**v5：2026-04-17**；25 位作者（Guibin Zhang、Hejia Geng、Xiaohang Yu、Zhenfei Yin 等）；综述 **500+** 篇文献。
- 核心框架性论断（逐字）：
  > "The emergence of **agentic reinforcement learning (Agentic RL)** marks a **paradigm shift** from conventional reinforcement learning applied to large language models (LLM RL), reframing LLMs from **passive sequence generators** into **autonomous, decision-making agents** embedded in complex, dynamic worlds."
  > 形式化对照：传统 LLM-RL 处理的是 "**degenerate single-step Markov Decision Processes (MDPs)**"；Agentic RL 处理的是 "**temporally extended, partially observable Markov decision processes (POMDPs)**"。
  > 六大能力轴：**planning、tool use、memory、reasoning、self-improvement、perception**。RL "serves as the critical mechanism for transforming these capabilities from **static, heuristic modules** into **adaptive, robust agentic behavior**."
- 链接：[arxiv.org/abs/2509.02547](https://arxiv.org/abs/2509.02547)

> 讲稿串联：**单步 MDP → 长时程 POMDP** 这一句，正好把第 1 节的「循环骨架」和第 7 节的「模型能跑更久」缝在一起——**harness 把单步模型包成多步 agent；Agentic RL 则把多步这件事直接训进模型里**。

**其他可选引用（均只做了检索级核实，具体数字请勿直接引用，标记为待核实）**：
- AgentGym-RL（[arXiv 2509.08755](https://arxiv.org/abs/2509.08755)）：多轮 RL 训练长时程决策 agent 的统一框架。
- Reinforcement Learning for Long-Horizon Multi-Turn Search Agents（[arXiv 2510.24126](https://arxiv.org/abs/2510.24126)）。

---

## 8. 待核实清单（上台前请二次确认）

| # | 项目 | 现状 |
|---|---|---|
| 1 | METR 2026-05 报告中 16–20 小时对应的**具体模型名** | 二轮抓取只确认 "the most capable shared model"。**建议匿名表述** |
| 2 | Claude Code v2.0.0 的**官方发布公告页面** | changelog 已确认包含 `/rewind`；日期 2025-09-29 来自 Boris Cherny 发布串与二手报道 |
| 3 | OpenAI《A practical guide to building agents》的**官方发布日** | PDF 内文无日期；2025-04-17 来自 MarkTechPost 等二手报道 |
| 4 | 12-factor-agents 的 star 数 / 最后更新时间 | 二手搜索结果，未在 GitHub 页面直接确认 |
| 5 | 「multi-agent 是 single-agent 的 ~3.75 倍 token」 | **原文没有这个数字**，是 15÷4 的推算，标注清楚再用 |
| 6 | pi 的 SQLite schema 细节（11 种 entry 类型、branch_entries 单调增长） | 来自本仓库 `analysis/raw/03-*.md`；`parentId`/`fork.ts`/`navigateTree` 已在源码直接核实，schema 细节未逐条复核 migrations 文件 |
| 7 | Agentic RL 相关论文（7.4 末尾两篇）的具体结论数字 | 仅检索级确认，未读原文 |

---

## 9. 参考链接总表

**Anthropic**
- Building Effective AI Agents（2024-12-19）https://www.anthropic.com/engineering/building-effective-agents
- How we built our multi-agent research system（2025-06-13）https://www.anthropic.com/engineering/multi-agent-research-system
- Effective context engineering for AI agents（2025-09-29）https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Loop engineering: getting started with loops（2026-06-30）https://claude.com/blog/getting-started-with-loops
- How Claude Code works https://code.claude.com/docs/en/how-claude-code-works
- Checkpointing https://code.claude.com/docs/en/checkpointing
- Manage sessions https://code.claude.com/docs/en/sessions
- Agent teams https://code.claude.com/docs/en/agent-teams
- Sub-agents https://code.claude.com/docs/en/sub-agents
- Agent SDK · How the agent loop works https://code.claude.com/docs/en/agent-sdk/agent-loop
- CHANGELOG https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md

**OpenAI**
- A practical guide to building agents（PDF）https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- 落地页 https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
- Agents SDK · Running agents https://openai.github.io/openai-agents-python/running_agents/
- Agents SDK · Orchestrating multiple agents https://openai.github.io/openai-agents-python/multi_agent/
- 源码 `DEFAULT_MAX_TURNS = 10` https://github.com/openai/openai-agents-python/blob/main/src/agents/run_config.py

**LangChain / LangGraph**
- Graph API（State/Node/Edge/super-step）https://docs.langchain.com/oss/python/langgraph/graph-api
- Persistence https://docs.langchain.com/oss/python/langgraph/persistence
- Interrupts（HITL）https://docs.langchain.com/oss/python/langgraph/interrupts
- Use time travel（replay / fork）https://docs.langchain.com/oss/python/langgraph/use-time-travel
- Durability 三档 https://reference.langchain.com/python/langgraph/types/Durability
- How and when to build multi-agent systems（Harrison Chase，2025-06-16）https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems

**Cognition**
- Don't Build Multi-Agents（Walden Yan，2025-06-12）https://cognition.com/blog/dont-build-multi-agents
- Multi-Agents: What's Actually Working（Walden Yan，2026-04-22）https://cognition.com/blog/multi-agents-working

**METR**
- 博客（2025-03-19）https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/
- 论文 arXiv 2503.14499 https://arxiv.org/abs/2503.14499
- Time Horizon 1.1（2026-01-29）https://metr.org/blog/2026-1-29-time-horizon-1-1/
- Frontier Risk Report（2026-05-19）https://metr.org/blog/2026-05-19-frontier-risk-report/
- Time horizons tracker（更新至 2026-05-08）https://metr.org/time-horizons/

**其他**
- 12-Factor Agents（Dex Horthy / HumanLayer）https://github.com/humanlayer/12-factor-agents
- Factor 10 https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md
- Agentic RL Survey arXiv 2509.02547 https://arxiv.org/abs/2509.02547
- Cursor Checkpoints https://cursor.com/docs/agent/chat/checkpoints

**本地一手材料**
- `/Users/nongjiawu/playground/research/pi/pi-mono`（workspace 0.83.0）
- `/Users/nongjiawu/playground/research/pi/analysis/raw/01-pi-agent-ai-core.md`
- `/Users/nongjiawu/playground/research/pi/analysis/raw/03-pi-protocol-server-storage.md`
