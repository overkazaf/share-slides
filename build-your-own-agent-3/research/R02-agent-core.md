# R02 — omp agent 内核取证：harness / 主循环 / 会话树 / 子代理

> 取证对象：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi`（HEAD `09a7c8656`）
> 对比基准：`/Users/overkazaf/playground/research/pi/pi-mono`（HEAD `583f153d5`，2026-08-01）
> 证据等级：`[A]` = 本地代码亲自读到并给出 `文件:行号`；`[B]` = 仓库内 README/docs 核实；`[C]` = 推测（只出现在文末「存疑区」）
> 除非特别标注，`packages/...` 指 omp 仓库；pi 仓库路径显式写 `pi-mono/`。

---

## 0. 结论先行（六句话）

1. **omp 的主循环不是状态机，是一个「双层 while + 一堆可注入钩子」的协程**。pi 的 `runLoop` 275 行、8 个钩子；omp 的 `runLoopBody` 500 行、约 40 个钩子。结构骨架同源（outer/inner 双 while、steering/follow-up 队列），但内部几乎逐行重写。`[A]`
2. **最本质的架构差异是「切包」**：pi 把 harness（AgentHarness、session store、tools、prompt）放在 `packages/agent/src/harness/`（8108 行）；omp 把 `packages/agent` 清成纯内核（loop + telemetry + compaction + pause + append-only context，14873 行，**无 harness 目录**），harness 整体搬进 `packages/coding-agent`（`AgentSession`，单文件 8814 行）。`[A]`
3. **错误恢复被拆成两层**：循环内负责「协议层」恢复（Harmony 泄漏、流截断、工具调用配对），会话层 `TurnRecovery`（1787 行）负责「策略层」重试（模型 fallback 链、空回复重试、限流退避）。pi 完全没有第二层。`[A]`
4. **会话是树，不是线性**：`id`/`parentId` + leaf 指针，追加式 JSONL，分支 = 移动 leaf 指针（从不删改历史）。树本身继承自 pi 的**老**会话实现（`coding-agent/src/core/session-manager.ts`，1712 行）；omp 把它炸成 69 个文件并加上多存储后端、定宽标题槽、终端面包屑、blob store。同时 omp **没有**跟进 pi 后来在 `packages/agent/src/harness/session/` 做的 SDK 化重构。`[A]`
5. **子代理不是「函数调用」，是「进程内的 agent 集群」**：有全局 `AgentRegistry`（状态机 `running/idle/parked/aborted`）、`AgentLifecycleManager`（idle→park→revive）、`IrcBus`（agent 间邮箱），并发上限 `task.maxConcurrency` 默认 **32**。**上游 pi 完全没有子代理系统**——这 ~430 KB 是 omp 净新增。`[A]`
6. **两个名字最唬人的包，实际都比名字朴素**：`metaharness` 不是「harness 的 harness」，是**跨 benchmark 的统一实验管理器 + Harbor runner**（研究工具，零反向依赖，`private: true`）；`swarm-extension` 是 **1795 行的 YAML DAG 编排器**，无并发上限、无重试、无节点间数据传递、模型无法自主触发。`[A][B]`

---

## 1. 主循环：长什么样、怎么判停、怎么处理 abort / 错误 / 工具失败

### 1.1 入口与骨架

三个导出入口，都返回 `EventStream<AgentEvent, AgentMessage[]>`：

| 函数 | 位置 | 语义 |
|---|---|---|
| `agentLoop(prompts, ...)` | `packages/agent/src/agent-loop.ts:516` | 追加新 prompt 后开跑 `[A]` |
| `agentLoopContinue(...)` | `packages/agent/src/agent-loop.ts:552` | 不追加消息、从当前 context 续跑（重试用）`[A]` |
| `agentLoopDetailed` / `agentLoopContinueDetailed` | `agent-loop.ts:673` / `:692` | 同上，额外捕获结构化结果 `[A]` |

内部：`runLoop`（`agent-loop.ts:882`，只负责包一层 OTEL span）→ `runLoopBody`（`agent-loop.ts:962`，真正的循环体，约 500 行）。`[A]`

骨架与 pi 完全同构——**双层 while**：

```
// packages/agent/src/agent-loop.ts:1026-1030
while (true) {                                  // 外层：等 follow-up / aside 唤醒
    let hasMoreToolCalls = true;
    while (hasMoreToolCalls || pendingMessages.length > 0) {   // 内层：一个 turn
```

对照 pi `pi-mono/packages/agent/src/agent-loop.ts:170-174`，注释文字都几乎一样（`// Outer loop: continues when queued follow-up messages arrive after agent would stop`）。这是**继承而非重写的部分**。`[A]`

### 1.2 「状态」在哪里

**循环本身没有显式状态枚举**，状态是几个局部变量的组合（`agent-loop.ts:1010-1023`）：

```ts
let harmonyRetryAttempt = 0;
let harmonyTruncateResumeCount = 0;
let pausedTurnContinuations = 0;
let hostToolChoice: ToolChoice | undefined;
let softRequiredTool: string | undefined;
let directiveResolvedForTurn = false;
let turnOpen = false;              // ← turn_start 是否已发出，决定异常时补不补 turn_start
```

对外暴露的「状态」是事件流（`packages/agent/src/types.ts:841-862`）：`agent_start / agent_end / turn_start / turn_end / message_start|update|end / tool_execution_start|update|end`。与 pi 事件集**完全一致**，仅两处增量：`tool_execution_start` 多了 `intent` 字段（`types.ts:860`），`agent_end` 多了 `telemetry` + `coverage`（`types.ts:845-850`）。`[A]`

真正的显式状态机在**上一层**：`AgentStatus = "running" | "idle" | "parked" | "aborted"`（`packages/coding-agent/src/registry/agent-registry.ts:23`）。`[A]`

### 1.3 判停条件（穷举）

内层 while 的 `hasMoreToolCalls` 由这些分支决定（`agent-loop.ts:1280-1391`）：

| 条件 | 行为 | 位置 |
|---|---|---|
| `stopReason` 为 `error` / `aborted` | 立刻补齐 tool_result 占位 → `agent_end` 返回 | `:1213-1255` |
| `stopReason` 为 `toolUse` 或 **`stop`** 且有 toolCall | 执行工具，继续 | `:1280-1281` |
| `stopReason === "length"`（被 max_tokens 截断） | **不执行**，每个 toolCall 配一个占位结果，但 `hasMoreToolCalls = true` 让模型重发 | `:1349-1367` |
| deadline 到期 | 停，所有未跑工具标 `aborted` | `:1283-1286`, `:1352` |
| soft tool requirement 未满足 | 不执行绕道工具，全部标 skipped，下一轮强制 `tool_choice` | `:1301-1331` |
| `signal.reason === TERMINAL_TOOL_RESULT_ABORT_REASON` | 停（子代理 yield 提交结果） | `:1372-1374` |
| `stopDetails.type === "pause_turn"`（Codex `end_turn:false`） | 重新采样，上限 `MAX_PAUSED_TURN_CONTINUATIONS = 8` | `:98`, `:1378-1391` |

**这段注释值得单独上 slide**（`agent-loop.ts:1257-1269`，omp 独有，pi 无此逻辑）——它解释了为什么 `stop` 也要跑工具：

```
// `stop_reason` is provider metadata that never goes back on the wire, so it
// does not gate continuation validity ... (adaptive/interleaved-thinking Opus
// routinely emits tool calls under `end_turn`; verified against the live
// Anthropic API). ... `length` (max_tokens) is the one reason we must NOT run.
```

外层 while 的退出：调 `onBeforeYield()`，然后重新 drain 三个队列（late steering / asides / follow-ups），都空才 `break`（`agent-loop.ts:1427-1447`）。`[A]`

### 1.4 abort 的分层设计（omp 最精细的一块）

omp 把「abort」拆成 **4 条独立信号**（`agent-loop.ts:2231-2247`）：

```ts
const steeringAbortController = new AbortController();   // 用户插话
const ircAbortController = new AbortController();        // peer agent 消息
const steeringSoftController = new AbortController();    // 协作式软信号（不杀任何东西）
const nonInterruptibleSignal = signal ?? new AbortController().signal;   // 只看外部 abort
const interruptibleSignal = AbortSignal.any([signal, steering, irc]);
```

分派规则（`agent-loop.ts:2239-2247` 注释 + `:2263-2282` 实现）：

- 工具声明 `interruptible: true`（纯等待类，如 `hub wait`、`vibe`）→ 收 `interruptibleSignal`，可被 steering/IRC 硬杀。
- 其余工具（如 `bash`）→ **只**收外部 signal。queued steering **永远不会**硬杀一个已经产生副作用的前台工具。
- 所有工具通过 `ctx.toolCall.steeringSignal` 收到**协作式**软信号（`agent-loop.ts:2486`），可以自愿让路（例如 bash 自动转后台）。

这条规则的收益写在 `:2566-2575`：工具跑完了就保留真实结果，不因为 abort 落地而伪造成 "skipped"，避免丢弃已发生的副作用（代码里直接引用 issue #4752）。`[A]`

另外还有**进程级暂停闸门** `AgentPauseGate`（`packages/agent/src/pause.ts:25`），在两个动作边界轮询：模型调用前（`agent-loop.ts:1042`）、每个工具启动前（`agent-loop.ts:2405`）。语义是「冻结不中止」——已在飞的流和已启动的工具跑完再停；run 自己的 abort 仍能立刻解除 park。pi 无此机制。`[A]`

### 1.5 错误恢复（循环内）

| 场景 | 处理 | 位置 |
|---|---|---|
| GPT-5 Harmony 协议泄漏 | 检测 → 能救则「截断续跑」（上限 2 次），不能救则丢弃 partial + 重采样（上限 2 次，且温度 +0.05），仍失败则抛错 | `:1168-1196`, `:1594` |
| 流传输瞬时错误但工具调用已完整 | `recoverTransientErrorToolTurn` 把 `stopReason: "error"` **改写成 `"toolUse"`**，让这一轮工具照常执行；前提：所有 toolCall 名字都在 tool 列表里、且不是 refusal/sensitive | `:1909-1952` |
| 流中断时有半截 toolCall | `retainCompletedToolCalls` 只保留 `toolcall_end` 已到达的调用，其余丢弃并打 `stream_interrupted_after_content` 标记 | `:1882-1907` |
| 工具返回畸形结果（JS 扩展） | `coerceToolResult` 归一化；`afterToolCall` 钩子的返回值也要再过一次同样的归一（`:2536-2542`，注释点名这是同一类风险） | `:436`, `:2506-2508` |
| 工具批次跑完仍有 record 没产出结果 | 尾扫（tail sweep）统一补 skipped 结果，保证 tool_use/tool_result 严格配对 | `:2698-2708` |

对照 pi：pi 只有一个 `failToolCallsFromTruncatedMessage`（`pi-mono/.../agent-loop.ts:381`）处理 `length` 截断，其余恢复逻辑**全无**。`[A]`

### 1.6 工具失败回灌

三种「合成」结果，都会真的进 context 和会话历史：

- `createAbortedToolResult`（`agent-loop.ts:2807`）：abort/error/length/skipped 占位。
- `createSkippedToolResult`（`agent-loop.ts:2847`）：被 steering/IRC 打断而未启动。
- `createSyntheticToolResultMessage` + `isSyntheticToolResultMessage`（`agent-loop.ts:2778` / `:2745`）：**omp 独有**，给合成结果打可识别标记（`SyntheticToolResultDetails`，`:2730`），下游 compaction / retry 能区分「模型真的看到过的结果」和「我们补的」。`[A]`

soft tool requirement 的回灌文案值得引（`agent-loop.ts:1318`）：

```
`Not executed: call the \`${softRequiredTool}\` tool to resolve the pending action before using other tools.`
```

上限 `MAX_SOFT_TOOL_ESCALATIONS = 3`（`agent-loop.ts:106`），超了直接抛错，注释说明理由是「避免无界强制循环」。`[A]`

### 1.7 工具并发模型

pi：全局二选一 `config.toolExecution: "sequential" | "parallel"`，任一工具声明 `executionMode: "sequential"` 就整批串行（`pi-mono/.../agent-loop.ts:419-425`）。`[A]`

omp：**逐工具的 shared/exclusive 调度**，且可按参数动态决定（`packages/agent/src/types.ts:757`）：

```ts
concurrency?: "shared" | "exclusive" | ((args) => "shared" | "exclusive");
interruptible?: boolean | ((args) => boolean);
```

调度器是一个手写的「屏障链」（`agent-loop.ts:2660-2686`）：

```ts
const start = concurrency === "exclusive"
    ? Promise.all([lastExclusive, ...sharedTasks])   // exclusive 等前面所有人
    : lastExclusive;                                 // shared 只等上一个 exclusive
const task = start.then(() => runTool(record, index));
if (concurrency === "exclusive") { lastExclusive = task; sharedTasks = []; }
else sharedTasks.push(task);
```

即：shared 工具彼此并行，exclusive 工具是批次内的写屏障。这是本篇里**最容易被小项目直接抄走**的一段。`[A]`

### 1.8 steering 的事件驱动化

pi 只在 turn 边界 poll `getSteeringMessages()`。omp 在工具批次执行期间还开了一个 watcher（`agent-loop.ts:2629-2659`），优先用事件驱动的 `waitForSteeringMessages(signal)`，只有 IRC 队列（无唤醒回调）才退回 `setInterval(STEERING_INTERRUPT_POLL_MS)`，该常量为 250ms（`agent-loop.ts:155`）。并且明确写了「检测必须是非消费性的（`hasSteeringMessages` 只 peek）」，避免消息被 poll 走后卡在一个马上就要 abort 的 run 里（`agent-loop.ts:2318-2321`、`:1402-1407`）。`[A]`

---

## 2. 与上游 pi AgentLoop 的逐点对比

### 2.0 体量与切包

| | pi-mono | omp | 说明 |
|---|---|---|---|
| `packages/agent/src` 总行数 | 10368 | **14873** | `[A]` |
| 其中 `harness/` | 8108 | **0（无此目录）** | omp 内核纯化 `[A]` |
| `agent-loop.ts` | 792 | **2869** | 3.6× `[A]` |
| `agent.ts` | 577 | **1650** | `[A]` |
| `types.ts` | 437 | **862** | `[A]` |
| `packages/coding-agent/src` | 56431 | **398480** | 7× `[A]` |

pi 的 `AgentHarness`（`pi-mono/packages/agent/src/harness/agent-harness.ts:173`，1185 行）在 omp 中的对应物是 `AgentSession`（`packages/coding-agent/src/session/agent-session.ts`，8814 行）。**这是一次「把 harness 从内核包踢出去」的重构**。`[A]`

### 2.1 保留（几乎逐行同源）

- 双层 while 骨架、`pendingMessages` 注入点、`getSteeringMessages` / `getFollowUpMessages` 语义。`agent-loop.ts:1026-1030` vs `pi-mono/.../agent-loop.ts:170-174` `[A]`
- `EventStream` + `createAgentStream()`（以 `agent_end` 为终止判定）：`agent-loop.ts:584-589` vs `pi-mono/.../agent-loop.ts:145-150`，**代码完全一致**。`[A]`
- `agentLoopContinue` 的两条前置校验（空 context、末尾不能是 assistant）及其英文注释，一字不差：`agent-loop.ts:544-564` vs `pi-mono/.../agent-loop.ts:56-76`。`[A]`
- `AgentEvent` 事件集合（omp 仅加 `intent` / `telemetry` / `coverage` 三个字段）。`[A]`

### 2.2 删除（pi 有、omp 无）

在 `packages/agent/src/` 全文 grep 结果为 0 次：`[A]`

| pi 的东西 | pi 位置 | omp 的替代 |
|---|---|---|
| `shouldStopAfterTurn` 钩子 | `pi-mono/.../types.ts:217` | 由 `beforeModelCall` 返回 `{stop:true}` 承担（`agent-loop.ts:1104-1140`） |
| `prepareNextTurn` 钩子（换模型/思考档） | `pi-mono/.../types.ts:224` | 拆成 `getModel()` / `getReasoning()` / `getServiceTier()` / `getCwd()` 等一组「每次调用现取」的 getter（`types.ts:417-456`） |
| `config.toolExecution` 全局并发模式 | `pi-mono/.../types.ts:263` | 逐工具 `concurrency`（见 §1.7） |
| `AgentTool.executionMode` | `pi-mono/.../agent-loop.ts:420` | 同上 |
| `failToolCallsFromTruncatedMessage` | `pi-mono/.../agent-loop.ts:381` | 内联进主循环的 `length` 分支（`agent-loop.ts:1349-1367`） |
| `AgentToolResult.terminate` + `shouldTerminateToolBatch` | `pi-mono/.../agent-loop.ts:582` | 换成 abort-reason 信号 `TERMINAL_TOOL_RESULT_ABORT_REASON`（`agent-loop.ts:153`），由会话层触发（`agent-session.ts:2004`） |
| `runAgentLoop` / `runAgentLoopContinue` 导出 | `pi-mono/.../agent-loop.ts:95,120` | 合并为私有 `runLoop` |
| `AgentEventSink` 类型（`emit` 回调） | `pi-mono/.../agent-loop.ts:25` | 直接 `stream.push(...)`，去掉一层 async 间接 |

**语义变化提醒**：pi 用 `emit` 是 `await` 的（`await emit({...})`），omp 改成同步 `stream.push`。这意味着 omp 的事件消费者不能靠 emit 背压来串行化，得自己排队——`AgentSession.#handleAgentEvent` 因此显式维护 `#postPromptTasksPromise`（`agent-session.ts:1995-1998` 注释）。`[A]`

### 2.3 重写（结构层面的改造）

| 点 | pi | omp |
|---|---|---|
| **turn 开启时机** | 先 `emit(turn_start)` 再干活 | 延后到 provider 准备成功之后才开 turn（`turnOpen` 标志，`agent-loop.ts:1094-1146`），失败时才补发。目的是让 gate-stop 不产生空 turn |
| **assistant 消息可变性** | 直接把 provider 的 partial 对象塞进 context | 全程 `snapshotAssistantMessage`（`agent-loop.ts:368`）做不可变快照，`message` 与 `assistantMessageEvent.partial` **共用同一个快照**以省一次深拷贝（`:1794-1797` 注释） |
| **工具调用准备（validate + beforeToolCall）** | 在执行前逐个做（`pi-mono/.../agent-loop.ts:600`） | 提前到 `message_end` **之前**做，结果写回 toolCall block，用 `WeakMap<AssistantMessage, Map>` 缓存（`agent-loop.ts:2085`, `:1762-1767`）。理由写在注释里：让 UI、持久化、provider replay、调度、执行**看到同一份被钩子改写过的参数** |
| **中断检测** | 无 | 见 §1.4，4 条信号 + 事件驱动 watcher |
| **停止判定** | `stopReason === "toolUse"` 才跑工具 | `toolUse` 或 `stop` 都跑（§1.3） |
| **provider 调用参数** | 静态 config | `prepareProviderCall`（`agent-loop.ts:1487`）+ 一批 per-call getter，支持运行中改模型/思考档/service tier/cwd |
| **API key** | `getApiKey(provider)` 返回 string | `getApiKey(model)` 返回 `ApiKey`（可为 resolver），且 `resolveApiKeyOnce` + `seedApiKeyResolver`（`agent-loop.ts:1586-1588`），配合多凭据轮询 |

### 2.4 新增（omp 有、pi 无）

**钩子数量**：pi `AgentLoopConfig` 8 个可选钩子（`pi-mono/.../types.ts:173-271`：`convertToLlm` / `transformContext` / `getApiKey` / `shouldStopAfterTurn` / `prepareNextTurn` / `getSteeringMessages` / `getFollowUpMessages` / `beforeToolCall`）。omp 约 40 个（`packages/agent/src/types.ts:142-526`）。`[A]`

按主题分组的新增钩子：

- **队列**：`hasSteeringMessages`（非消费 peek，`:249`）、`waitForSteeringMessages`（事件驱动，`:257`）、`hasIrcInterrupts`（`:266`）、`getAsideMessages`（`:286`）、`onBeforeYield`（`:293`）、`interruptMode`（`:142`）
- **模型/供应商**：`getModel` `:425`、`getReasoning` `:417`、`getDisableReasoning` `:434`、`getServiceTier` `:445`、`getCwd` `:456`、`metadataResolver` `:161`、`transformProviderContext` `:212`
- **工具**：`getToolContext` `:299`、`transformToolCallArguments` `:325`、`resolveFallbackTool` `:332`、`afterToolCall` `:513`、`getToolChoice` `:396`、`onToolChoiceRejected` `:409`
- **上下文**：`syncContextBeforeModelCall` `:309`、`transformAssistantMessage` `:502`、`appendOnlyContext` `:375`
- **可观测**：`telemetry` `:526`、`onTurnEnd` `:488`、`onAssistantMessageEvent` `:381`、`onHarmonyLeak` `:386`
- **其它**：`deadline` `:151`、`sessionId` `:148`、`dialect` `:354`、`intentTracing` `:339`、`pruneToolDescriptions` `:345`、`abortOnFabricatedToolResult` `:366`、`softToolRequirementState` `:402`

新增的**模块**（`packages/agent/src/index.ts`）：`[A]`

| 模块 | 行数 | 作用 |
|---|---|---|
| `telemetry.ts` | 2078 | OTEL span（`invoke_agent` / `chat` / `execute_tool`）+ GenAI 语义属性 |
| `run-collector.ts` | 631 | 每次 run 的聚合器，`agent_end` 直接带 `AgentRunSummary` + `AgentRunCoverage`，消费方不必解析 span |
| `compaction/`（13 文件） | 5667 | pi 对应目录仅 1287 行（3 文件）；omp 多出 v2 流式压缩、OpenAI 专用路径、pruning、shake、tool-protection、message-cache |
| `append-only-context.ts` | 348 | 冻结 system prompt + tool spec 字节序列，让 provider prefix cache 命中率最大化 |
| `pause.ts` | 107 | 进程级暂停闸门 |
| `proxy.ts` / `replay-policy.ts` / `thinking.ts` / `tokenizer.ts` / `utils/yield.ts` | — | pi 亦有 proxy；其余为新增 |

其中 `append-only-context.ts:1-14` 的自述最适合上 slide：

```
 * 1. **StablePrefix** — system prompt + tool specs are computed once and frozen.
 * 2. **AppendOnlyLog** — messages only grow; prior turns are never re-serialized.
 *    Combined with a stable prefix, only the user's new message delta is a
 *    cache miss each turn.
```

**Intent tracing**（`agent-loop.ts:770-861`）：omp 会往每个工具的 JSON Schema 里注入一个 `i`（"concise intent"）必填字段，把模型的调用意图和参数一起拿到，用于 UI 与 telemetry。实现里处理了 `anyOf`/`oneOf` 联合 schema 的分支注入（`:800-812`，注释解释了为什么不能加在 root）。可用 `PI_NO_INTENT=1` 关掉（`:837`）。pi 无此功能。`[A]`

### 2.5 错误恢复的第二层：`TurnRecovery`（omp 独有）

`packages/coding-agent/src/session/turn-recovery.ts:168` `class TurnRecovery`，1787 行。pi 的 `packages/coding-agent` 里没有任何 retry/recovery 文件（`find -iname "*retry*" -o -iname "*recovery*"` 为空）；pi 的重试只在 compaction/branch-summary 上（`pi-mono/.../agent-harness.ts:276-281`）。`[A]`

`TurnRecovery` 管的东西：

- 空回复重试：`EMPTY_STOP_MAX_RETRIES = 3`（`turn-recovery.ts:64`）
- 非预期停止重试：`UNEXPECTED_STOP_MAX_RETRIES = 3`、`UNEXPECTED_STOP_TIMEOUT_MS = 4000`（`:62-63`），配 `unexpected-stop-classifier.ts`
- 模型 fallback 链：`retry-fallback-chains.ts`，`#tryRetryModelFallback`（`:1128`）、`#maybeRestoreRetryFallbackPrimary`（`:1234`）
- 限流退避：`calculateRateLimitBackoffMs` / `parseRateLimitReason`（`:19`）
- 「思考循环」重定向：注入 `thinking-loop-redirect.md` 提示（`:29`）
- 重试成功后回标历史里那条错误消息：`#markPendingRecoveredRetryErrors`（`:450`）

**层次划分很干净**：循环内只处理「这一次 HTTP 流本身坏了」，会话层处理「这个模型/这个策略不行，换一个再来」。`[A]`

---

## 3. 会话模型：树 + JSONL + 五种分支手法

### 3.0 血统澄清（讲之前必须先说清）

pi 仓库里有**两套**会话实现：`[A]`

| | 位置 | 行数 | 性质 |
|---|---|---|---|
| 老的 | `pi-mono/packages/coding-agent/src/core/session-manager.ts` | 1712（单文件） | 应用级，`getTree()` / `branch()` / v1→v2 迁移已具备（`:230`, `:1210`, `:1308`） |
| 新的 | `pi-mono/packages/agent/src/harness/session/`（8 文件） | ~1400 | SDK 级抽象：`SessionReader`/`SessionStore`/`SessionRepository`/`SessionSearch` |

**omp 继承的是老的那套，并把单文件炸成 69 个文件**（`packages/coding-agent/src/session/*.ts`，其中 `session-manager.ts` 约 2600 行）。omp 全仓 grep `SessionTreeEntry`（新套的核心类型）**零命中**——它**没有**跟进上游的 SDK 化重构，而是沿着老路径继续加厚。这是全篇最需要小心的对比点。`[A]`

### 3.1 是树

每条 entry 带 `id` + `parentId`，一个可变 leaf 指针选出活跃路径（`packages/coding-agent/src/session/session-entries.ts:56-61`）：`[A]`

```ts
export interface SessionEntryBase {
	type: string;
	id: string;
	parentId: string | null;
	timestamp: string;
}
```

**没有 branch id**——「分支」就是 root→leaf 这条路径本身。派生索引在私有类 `SessionEntryIndex`（`session-manager.ts:200-294`）：`#entriesById` / `#children` / `#labels` / `#leaf` / `#usage`。`pathTo()`（`:280-293`）沿 `parentId` 上溯并带 `seen` 环检测。`[A]`

entry 类型联合有 14 种（`session-entries.ts:239-253`）：`message` / `compaction` / `branch_summary` / `custom` / `custom_message` / `label` / `title_change` / `ttsr_injection` / `session_init` / `mode_change` / `credential_pin` / `thinking_level_change` / `model_change` / `service_tier_change`。`[A]`

另有**第二条树轴**：`SessionHeader.parentSession`（`session-entries.ts:41`）把整个会话文件链到来源会话。即：**文件内是 entry 树，文件间是 session 树**。`[A]`

`/tree` 的 UI 语义见 `docs/tree.md`（`[B]`）：按 timestamp 升序排子节点、活跃路径打点、多 root 时挂虚拟根。

### 3.2 存储：JSONL 是正典，SQL/Redis 只是「装 JSONL 文本的柜子」

路径（`[A][B]`）：

```
~/.omp/agent/sessions/<encodedCwdDir>/<ISO时间戳>_<sessionId>.jsonl
```

- 根目录 `packages/utils/src/dirs.ts:769-771`；文件名 `session-manager.ts:1284`。
- cwd 编码 `session-paths.ts:33-59`：home 内 → `-<相对路径打横线>`；temp 内 → `-tmp-<...>`；其余退回 legacy `--<绝对路径>--`。旧目录有单向在线迁移（`session-paths.ts:65-101`）。`docs/session.md` 是这一节的官方说明（`[B]`）。

存储抽象 `SessionStorage`（`session-storage.ts:46-80`），五个实现：`FileSessionStorage`（默认，`:186`）、`MemorySessionStorage`（`:644`）、`IndexedSessionStorage`（抽象，`indexed-session-storage.ts:91`）、`SqlSessionStorage`（`sql-session-storage.ts:235`，adapter = `postgres|mysql|sqlite`，`:13`）、`RedisSessionStorage`（`redis-session-storage.ts:98`）。**SQLite 存的是整段 JSONL 文本，不是关系化的 entry 表**。`[A]`

读侧按文件大小分流（`session-loader.ts:23`）：

```ts
const STREAM_LOAD_THRESHOLD_BYTES = 8 * 1024 * 1024;
```

小文件走 `parseJsonlLenient`（`:50-57`），大文件走 `Bun.JSONL.parseChunk` 字节流并**跳过畸形行**（`:60-92`）。对照上游新套：`jsonl-store.ts:64-127` 每行严格校验、抛带行号的 `SessionError`，还拒绝重复 id（`:159-163`）。**omp 选了「宽容」，上游新套选了「严格」**——这是可以摆在一起讲的设计取舍。`[A]`

**omp 独有的小机关：可变标题槽。** JSONL 物理第一行可能不是 JSON，而是一条 256 字节定宽 padding 的标题记录（`SESSION_TITLE_SLOT_BYTES = 256`，`session-entries.ts:7`；`SessionTitleSlotEntry` 带 `pad` 字段，`:16-23`）。解析前先剥掉（`session-loader.ts:110-120`），于是**改标题不用重写整个文件**。同时还追加一条 `title_change` 审计 entry（`session-entries.ts:146-152`）。`[A]`

### 3.3 分支/回溯的五种手法

| 手法 | 位置 | 语义 |
|---|---|---|
| `branch(id)` | `session-manager.ts:2197-2205` | 就地移动 leaf，下一次 append 自动成为兄弟节点。**从不修改或删除已有 entry** |
| `resetLeaf()` | `session-manager.ts:2207-2209` | leaf 置 null，下次 append 建新 root |
| `branchWithSummary(...)` | `session-manager.ts:2211-2228` | 同上 + 追加 `BranchSummaryEntry`，让被抛弃的那条路径以摘要形式留在 LLM 上下文里 |
| `createBranchedSession(leafId)` | `session-manager.ts:2230-2298` | 把 root→leafId 物化成**新文件**，重建 label 映射，写 `parentSession` |
| `fork()` / `static forkFrom()` | `session-manager.ts:1267-1308` / `:2352-2391` | 整份拷贝成新文件；**保留 provider prompt cache 身份**：`providerPromptCacheKey: header.providerPromptCacheKey ?? parentSessionId`（`:1294`） |

核心的 `branch` 只有 6 行，很适合上 slide（`session-manager.ts:2197-2205`）：`[A]`

```ts
	/**
	 * Move the leaf to an earlier entry so the next append forms a new branch.
	 * Existing entries are never modified or deleted.
	 */
	branch(branchFromId: string): void {
		if (!this.#index.has(branchFromId)) throw new Error(`Entry ${branchFromId} not found`);
		this.#setLeaf(branchFromId);
	}
```

**「编辑早先的消息」**是上面几件的组合，入口 `AgentSession.branch(entryId)`（`agent-session.ts:7448`）：抽出被选中 user 消息的文本/图片回填编辑器（`:7460-7461`，这就是「编辑」的可供性）→ 触发可取消的 `session_before_branch` 扩展钩子（`:7466-7476`）→ flush bash + 会话写、摘掉 advisor 录制器（`:7482-7494`）→ 目标无 parent 则 `newSession({parentSession})`，否则 `createBranchedSession(selectedEntry.parentId)`（`:7496-7500`，注意是 **`.parentId`**，即分叉到被选消息**之前**）→ `agent.replaceMessages(sessionContext.messages)` 重建活跃状态（`:7528`）。`[A]`

**坏轮次丢弃**也走同一套：`turn-recovery.ts:777-808` 的 `discardAssistantTurn()` 把 leaf 重新指到被丢弃轮次的 parent，这样重载时坏轮次不会复现：`[A]`

```ts
		this.#host.withBashBranchTransition(() => {
			if (branchEntry.parentId === null) {
				this.#host.sessionManager.resetLeaf();
			} else {
				this.#host.sessionManager.branch(branchEntry.parentId);
			}
		});
```

**上游新套在这一点上比 omp 更「有类型」**：`pi-mono/packages/agent/src/harness/session/fork.ts:4-23` 定义了 `SessionForkSelection = {kind:"all"} | {kind:"through_entry"} | {kind:"before_user_message"}`，并且校验 `before_user_message` 的目标真的是 user 消息，否则抛 `SessionError("invalid_fork_target")`。omp 没有这个类型，语义硬编码成 `agent-session.ts:7499` 那一行 `.parentId`。`[A]`

### 3.4 恢复（`--continue`）：全量加载 + 全量重放，不是懒加载

CLI：`packages/coding-agent/src/cli/args.ts:230`（`--continue` / `-c`），预解析在 `main.ts:701`，`--continue <id>` 解析在 `main.ts:1290-1291`。`[A]`

选哪个 session 走 `SessionManager.continueRecent(cwd, ...)`（`session-manager.ts:2487+`），**面包屑优先而非 mtime 优先**：`[A]`

1. 读 `~/.omp/agent/terminal-sessions/<terminalId>` 面包屑（`session-paths.ts:198-222`）——这让同一台机器上多个终端各自 `--continue` 各自的会话。
2. 面包屑标 `fresh` 且文件从未落盘（懒 `/new`）→ 直接开新会话，不复活 `/new` 之前的历史（`session-manager.ts:2505-2509`）。
3. 陈旧面包屑修复：子代理留下的、指向 artifact 子节点的面包屑，重新指回交互父会话（`:2513`）。
4. 项目被移动：原 cwd 不存在且当前目录没有自己的会话 → `open()` + `moveTo()` 重新落位（`:2542-2555`）。
5. 都不中 → `findMostRecentSession`。

复水 `setSessionFile()`（`session-manager.ts:1195-1245`）：整文件读入 → `migrateToCurrentVersion`（`CURRENT_SESSION_VERSION = 3`，`session-entries.ts:5`）→ `resolveBlobRefsInEntries` 从 `~/.omp/agent/blobs` 把图片 blob 重新灌回 → cwd 采纳（仅当目录仍在）→ 重建索引 → `sanitizeLoadedOpenAIResponsesReplayMetadata()` 清掉过期的 OpenAI Responses replay 元数据并强制重写（`:1244`）。`[A]`

LLM 上下文是**推导出来的、不存储**：`buildSessionContext(entries, leafId, ...)`（`session-context.ts:157+`）沿 leaf 路径回溯，在最近一条 `compaction` entry 处截断，并把 `branch_summary` 的文字拼回去。`leafId === null` 刻意返回零条消息（`:173-183`）。`[A]`

除消息外一起复水的还有：thinking level、service tier、按角色的模型、注入的 TTSR 规则、mode（`session-context.ts:175-182`），以及 **credential pin**（`session-manager.ts:2090`）——重新钉住同一个 OAuth 账号，好让 provider 的 prompt cache 保持热（理由写在 `session-entries.ts:168-177`）。`[A]`

### 3.5 omp 相对上游新套的增删（一句一条）

**omp 新增**：SQL/Redis 存储后端；定宽可变标题槽；终端面包屑（含 `fresh` 懒 `/new` 标记）；内容寻址 blob store；`session_init` 子代理复活契约 entry（`session-entries.ts:186-205`）；`credential_pin` / `ttsr_injection` / `mode_change` / `label` 等新 entry 类型；多根工作区 `additionalDirectories`（`:40`）；`moveTo()` 迁移；跨 fork 保持 prompt cache 身份；外部 harness 导入（`claude-session-store.ts` / `codex-session-store.ts`，对应 `--from-claude` / `--from-codex`）；`peekSessionInit()` 无锁 header 窥视（`session-manager.ts:2433-2485`）。`[A]`

**omp 未采纳（上游新套有）**：`SessionReader`/`SessionStore`/`SessionRepository` 三件套抽象；`SessionForkSelection` 代数；游标分页读（`array-session-reader.ts:42-47`）；严格 `SessionError` 分类；`search-backend.ts`；`keyed-operation-queue.ts`（含 `DEFAULT_MAX_CONCURRENT_OPERATIONS = 4`）；`compaction.retainedTail`。`[A]`

---

## 4. 子代理：不是函数调用，是进程内的 agent 集群

代码在 `packages/coding-agent/src/task/`（25 个 .ts，`executor.ts` 3298 行 / 123 KB，`index.ts` 1519 行，`render.ts` 1830 行）。`[A]`

### 4.1 上游 pi 完全没有这套东西

`[A]`

- `pi-mono/packages/coding-agent/src/` 下**没有 `task/` 目录**。
- 对 `subagent|spawnAgent|Task tool` 全文 grep（pi 的 `packages/coding-agent/src` + `packages/agent/src`）→ **零文件命中**。
- 对 `agents/*.md|\.claude/agents` grep 整个 `pi-mono/packages` → **零命中**，上游没有 markdown agent 定义加载器。

**这 ~430 KB 的 `task/` 子系统是 omp 净新增。** 这是本篇「omp vs pi」最大的一块面积。

### 4.2 上下文隔离：一个真的 AgentSession，不是消息数组切片

`[A]`

会话构造（`task/executor.ts:2835-2840`）：

```ts
			const sessionManagerPromise = sessionFile
				? SessionManager.open(sessionFile, undefined, undefined, {
						initialCwd: effectiveCwd,
						suppressBreadcrumb: true,
					})
				: Promise.resolve(SessionManager.inMemory(effectiveCwd));
```

`suppressBreadcrumb: true` 就是防止子代理抢走终端的 `--continue` 面包屑（呼应 §3.4 第 3 条）。

**system prompt 不是原样继承**——agent markdown 的正文被拼进一个子代理模板，插在默认 prompt 的**倒数第二段**（`executor.ts:2955-2970`）：

```ts
				systemPrompt: defaultPrompt => {
					const subagentPrompt = prompt.render(subagentSystemPromptTemplate, {
						agent: agent.systemPrompt, context: options.context?.trim() ?? "",
						planReference: ..., worktree: worktree ?? "",
						outputSchema: normalizedOutputSchema,
						ircPeers: ircEnabled ? renderIrcPeerRoster(id) : "", ircSelfId: ...,
					});
					return defaultPrompt.length === 0 ? [subagentPrompt]
						: [...defaultPrompt.slice(0, -1), subagentPrompt, defaultPrompt[defaultPrompt.length - 1]];
				},
```

**唯一跨界的会话上下文是显式的 `options.context` 字符串和 `planReference`——父代理的 transcript 不过去。** `[A]`

工具：由 agent 定义的 `toolNames` 决定（`executor.ts:2943`）；`restrictToolNames` 硬关 MCP 并丢掉预载的扩展/自定义工具（`:2878-2880`, `:2953-2954`）；父代理专属工具再剥一层（`:3054-3062`，注释说 `todo` 是「parent-owned bookkeeping」）。`[A]`

**继承的**是：cwd（或独立 worktree）、settings（`createSubagentSettings`，`:822`）、模型注册表/鉴权、contextFiles/skills/rules/workspaceTree、`taskDepth`、telemetry 父子关系（`:2888-2915`），以及**父代理的 `ArtifactManager`——故意共享，让整棵树只有一个 artifact ID 空间**（`:2998-3000`，理由在 `artifacts.ts:33-36`）。`[A]`

三层额外隔离：git worktree 文件系统隔离（`task/worktree.ts`、`isolation-runner.ts`、设置 `task.isolation.mode`）、子进程隔离（`subprocess-tool-registry.ts`）、递归 spawn 白名单（`spawn-policy.ts:19-57`，frontmatter `spawns:` 支持 `"*"` / `""` / CSV；`DEFAULT_SPAWN_AGENT = "task"`，`:2`）。`[A]`

整份契约会写进 `session_init` entry 供忠实复活（`executor.ts:3064-3073`，类型 `session-entries.ts:186-205`）。`[A]`

### 4.3 结果回传：强制 `yield` 工具 + JSON Schema 校验

`[A]`

子代理**必须**带 `yield` 工具（`requireYieldTool: true`，`executor.ts:2947`）。工具实现在 `packages/coding-agent/src/tools/yield.ts`，文件头就写明：

```
 * Result submission tool for subagent output.
 * Subagents can call this tool incrementally or terminally depending on `type`.
```

- `YieldItem`（`task/types.ts:379-393`）：`data` / `status` / `error` / `type`——**`type` 是字符串表示终结 yield，是非空数组表示增量 yield**（`:383-384`）；`useLastTurn` 表示用最后一条 assistant 文本代替 `data`（`:385-386`）。
- 折叠逻辑单独放在 `task/yield-assembly.ts`，**刻意零依赖**，好让 TUI 渲染器能独立组装增量 yield（`:1-10`）。
- Schema 校验在 `task/structured-subagent.ts`，模式 `"permissive" | "strict"`（`types.ts:17`），重试预算 `MAX_YIELD_RETRIES = 3`（`executor.ts:1784`）、`MAX_YIELD_TOOL_ERRORS = 6`（`:865`）。

父代理拿到的是 `SingleResult`（`types.ts:470-535`），远不止一段文本：`structuredOutput` / `exitCode` / `stderr` / `truncated` / `durationMs` / `tokens` / `requests` / `contextTokens` / `usage` / `resolvedModel` + `resolvedModelIsFallback` / `aborted` + `abortReason` / `retryFailure` / 以及隔离产物 `patchPath` / `branchName` / `branchBaseSha` / `nestedPatches`。`[A]`

输出同时落盘成 artifact，可用 `agent://<id>` 寻址（`executor.ts:2120-2121`，每轮重写 `:2425-2426`）。截断上限 `MAX_OUTPUT_BYTES = 500000`、`MAX_OUTPUT_LINES = 5000`（`types.ts:53,56`）。`[A]`

**终结 yield 怎么让循环停下**：会话层监听 `tool_execution_end`，识别出终结 yield 后调 `agent.abort(TERMINAL_TOOL_RESULT_ABORT_REASON)`（`agent-session.ts:2000-2005`），主循环在 `agent-loop.ts:1372-1374` 看到这个特定 reason 就把 `hasMoreToolCalls` 置 false——**用一个 Symbol 当带内信令，既停住循环又不污染用户 abort 语义**。`[A]`

### 4.4 并发上限

**有，`task.maxConcurrency`，默认 32。** `[A]`

`packages/coding-agent/src/config/settings-schema.ts:4559-4561`：`"task.maxConcurrency": { type: "number", default: 32, ... }`

执行者是**每个 TaskTool 实例（即每个会话）一个** `Semaphore`（`task/index.ts:630-638`）：

```ts
	#getSpawnSemaphore(): Semaphore {
		const max = this.session.settings.get("task.maxConcurrency");
		if (this.#spawnSemaphore) { this.#spawnSemaphore.resize(max); }
		else { this.#spawnSemaphore = new Semaphore(max); }
		return this.#spawnSemaphore;
	}
```

`Semaphore` 在 `task/parallel.ts:141-215`，三个非显然的性质各自对应一个真实 bug（注释里直接写了 issue 号）：`[A]`

- `0` / 非有限 = **无限制** → `Number.POSITIVE_INFINITY`（`:136-148`，#3305）
- `acquire(signal)` 在 abort 时要把废弃的 waiter 从队列里摘掉，否则后来的 `release()` 会唤醒一个死等待者，**永久性地缩小有效并发**（`:151-183`，#3464）
- `resize()` 就地改而不是换实例，让在飞的槽位继续计数（`:197-214`）

**第二条正交的上限**是 per-provider 的：`wrapStreamFnWithProviderConcurrency`（`task/provider-concurrency.ts:76-99`）只括住 HTTP 流本身，**不能括住整个 agent 生命周期**——那样任何比上限更宽的 spawn 树都会死锁（`:1-12`，#3749）。目前只给 `ollama-cloud` 配了（`:19-21`）。`[A]`

未找到硬性的 spawn **深度**上限；`MAX_NESTED_TASK_RENDER_DEPTH = 8`（`task/render.ts:62`）只是渲染深度。深度实际由 `spawns:` 白名单约束。`[A]`

### 4.5 agent 定义：markdown + frontmatter

`[A]`

`parseAgent(filePath, content, source, level)`（`task/agents.ts:105-125`）：frontmatter → 字段，正文 → `systemPrompt`。类型 `AgentDefinition`（`types.ts:359-376`）：`name` / `description` / `systemPrompt` / `tools?` / `spawns?` / `model?` / `thinkingLevel?` / `output?` / `blocking?` / `autoloadSkills?` / `readSummarize?` / `prewalk?`。

内置 agent 用 Bun 文本导入在构建期嵌入（`agents.ts:9-16`）：`scout` / `designer` / `reviewer` / `security-reviewer` / `librarian` / `task`，外加一个合成的 `sonic`（复用 `task.md` 但换 `@smol` 模型 + `Effort.Medium`，`:44-75`）。

发现路径（`task/discovery.ts:1-19`）：`~/.omp/agent/agents/*.md`（用户）→ `.omp/agents/*.md`（项目）→ 每个 OMP 扩展根的 `agents/`→ Claude Code **marketplace 插件**的 `agents/`（`:107-118`）。优先级 first-wins，按 name 去重（`:70-138`）；单个文件解析失败只 warn 不致命（`:51-55`）。

**`.claude/agents` 是刻意不读的**（`discovery.ts:13-16`）——这条注释很适合讲「跨 harness 兼容的边界在哪」：

```
 * Direct cross-harness roots such as .claude/agents are intentionally skipped
 * because their frontmatter schema is not the OMP task-agent contract.
```

### 4.6 比「子代理」更进一步：agent 集群

这是 omp 真正超出「Task 工具」范式的部分。`[A]`

**全局注册表**（`packages/coding-agent/src/registry/agent-registry.ts:1-40`，217 行）：进程内所有 agent（主会话 + 每个子代理）按稳定 id 登记，**带真正的状态机**（`:17-23`）：

```
 * - `running`: a turn is in flight.
 * - `idle`: live AgentSession in memory, awaiting work. Finished agents are idle, not removed.
 * - `parked`: session disposed; AgentRef + sessionFile retained, revivable.
 * - `aborted`: hard-killed, terminal.
```

`AgentKind = "main" | "sub" | "advisor"`（`:31`）——advisor 也按子代理方式持久化以做用量归因，但对 agent 可见的花名册隐藏。

**生命周期管理器**（`registry/agent-lifecycle.ts`，455 行）：idle 超 TTL → park（销毁 live session，保留 `AgentRef` + `sessionFile`）→ 按需 revive。park/revive 之间的并发被显式 gate 住并按 id 合并（`:12-20` 注释），且每次操作绑定到确切的 `AgentRef`，防止旧的 revive 覆盖新的同 id ref（`:18-20`）。`[A]`

**agent 间邮箱** `IrcBus`（`packages/coding-agent/src/irc/bus.ts:1-16`，`MAILBOX_CAP = 100`，`:47`）：

```
 * Replaces the old auto-reply model: a `send` never blocks on the recipient
 * generating anything. ... parked agents are revived through the
 * AgentLifecycleManager, idle agents are woken with a real turn, and busy
 * agents receive the message as a non-interrupting aside at the next step boundary
```

**这就闭合回了 §1 的循环**：IRC 消息以「非中断 aside」的形式，经 `getAsideMessages` 钩子在下一个 step 边界注入。三个 aside 生产者一起注册在 `agent-session.ts:1140-1147`：`[A]`

```ts
		this.agent.setAsideMessageProvider(() => {
			const thunks: AsideMessage[] = this.#irc.drainPending().map(record => () => record);
			thunks.push(...this.yieldQueue.drainLazy());          // advisor 的评审意见
			thunks.push(() => this.#todo.takeMidRunNudge());      // 中途 todo 对账
			return thunks;
		});
```

注意 aside 是**惰性 thunk**——在注入那一刻才求值，返回 null 就丢弃（`agent-loop.ts:945-960`），这样「被更新的编辑取代的过时诊断」可以在最后一刻自我撤回。这是很讲究的一处设计。`[A]`

**advisor**（`packages/coding-agent/src/advisor/runtime.ts:22-32`）是第二个 Agent 实例，只读主 transcript、通过 `enqueueAdvice` 把评审意见塞进 YieldQueue → aside → 主循环。它的 `AdvisorAgent` 接口特意只要 `prompt` / `abort` / `reset` / `rollbackTo` / `state`，注释说明「provider/stream 失败从不 reject `prompt()`，所以要读 `state.error` 判断」（`:17-21`）。`[A]`

---

## 5. metaharness：到底是什么

**结论：名字唬人，实质是「跨 benchmark 的统一实验管理器 + Harbor runner」，不是 harness 的抽象层。** `[A][B]`

### 5.1 自我定位

`packages/metaharness/README.md:1-6`（`[B]`）：

> One manager for repository benchmarks. Harbor, TypeScript edit, and SnapCompact runs use the same experiment → run → trace model, SQLite store, REST/SSE API, and dashboard. Benchmark-native artifacts remain on disk; adapters normalize their live progress, scores, token usage, costs, and traces.

三种 benchmark 硬编码在 `packages/metaharness/src/store.ts:19`：`[A]`

```ts
export type BenchmarkKind = "harbor" | "edit" | "snapcompact";
```

**「meta」的准确含义是 meta-over-harnesses**：它自己不定义任务、不写 verifier、不评分，评分由各 benchmark 原生产物给出（Harbor 的 `result.json`、edit 的 `result.json`、snapcompact 的 `records.jsonl`）；metaharness 只做 adapter 归一化 + 存储 + 编排 + 可视化。归一化的分发口只有 3 行（`packages/metaharness/src/benchmarks.ts:243-248`）：`[A]`

```ts
export function readBenchmarkSnapshot(benchmark: BenchmarkKind, jobDir: string): BenchmarkSnapshot {
	if (benchmark === "edit") return readEditSnapshot(jobDir);
	if (benchmark === "snapcompact") return readSnapcompactSnapshot(jobDir);
	const trials = readTrials(jobDir);
	...
}
```

同时它**内含**一个真正的 harness：`packages/metaharness/src/runner.ts`（Harbor / terminal-bench 2 的完整 runner）。所以准确说法是 **runner + manager 二合一**。`[A]`

### 5.2 它怎么驱动 agent（三条路径）

| 路径 | 机制 | 证据 |
|---|---|---|
| **A. Harbor** | 把 repo **只读 bind-mount 进任务容器**，容器内用 linux `bun` 直接跑 `packages/coding-agent/src/cli.ts` 的 headless 模式 | `packages/metaharness/agent/omp_local.py:353`（`cli = f"{self._source_dir}/packages/coding-agent/src/cli.ts"`）、`:554-560`（`--print --mode json --provider … --no-session`）`[A]` |
| **B. TypeScript edit** | **进程内**直接 `createAgentSession`（默认），或可选 RPC 子进程 | `packages/metaharness/adapters/edit/runner.ts:1131-1145`；`packages/typescript-edit-benchmark/src/in-process-client.ts:1-19` `[A]` |
| **C. SnapCompact** | 外部 Python：`uv run src/adapters/snapcompact.py` | `packages/metaharness/src/server.ts:409-412` `[A]` |

注意层级：Harbor 路径下 metaharness **不直接调 AgentLoop**，链路是 `harbor run` → Harbor 调 `OmpLocal.run()` → 容器内 `omp` CLI → 其内部才是 AgentLoop。`packages/agent`（`@oh-my-pi/pi-agent-core`）在 metaharness 里基本只作 **type-only import**（`adapters/edit/runner.ts:16`）。`[A]`

三个值得讲的工程细节：`[A][B]`

1. **改 TS 不用重新构建**：源码挂载 + 容器内直跑 `.ts`，「TS edits apply to the next trial with no rebuild」（README:14-19）。
2. **凭据永不进容器**：生成 `models.yml` 把 provider `baseUrl` 指向宿主 pm2 auth-gateway，凭据在宿主侧解析（README:25-27；`src/runner.ts:1587-1598` 含健康检查）。
3. **文件系统是 source of truth，SQLite 只是可查询镜像**：`src/store.ts:1-8` 明说；`discover()`（`:325`）会自动收编历史 CLI 跑出来的 job 目录。DB 在 `<jobsDir>/_manager/metaharness.sqlite`（`:190`），WAL + busy 重试（`:167-181`）。

### 5.3 统计口径的严谨性（最能体现"研究工具"气质的一段）

`packages/metaharness/src/experiments.ts:92-96`：`[A]`

```ts
// Every observed stat is computed over DECIDED trials only — numerator and
// denominator from the same population. `run.costUsd` includes in-flight
// trials' accumulating spend, so dividing it by the decided count wildly
// overstates $/task early in a run; per-trial trace costs don't.
const decided = traces.filter(t => t.status === "pass" || t.status === "fail" || t.status === "error");
```

实验/臂（arm）的切分则是零配置的命名约定（`experiments.ts:58-68`）：experiment id = job 名第一个 `-` 之前的部分，arm = 其余部分。`[A]`

### 5.4 它不在生产路径上

- `"private": true`，version 停在 `0.0.1`（`packages/metaharness/package.json:3,6`）`[A]`
- **零反向依赖**：全仓（排除 node_modules）对 `pi-metaharness` 的引用只有它自己的 package.json，加上根 `package.json:114` 的 dev 脚本 `"meta"`。coding-agent / agent / tui 均不 import 它。`[A]`
- 运行前置是开发者机器专属：宿主 pm2 auth-gateway、`harbor` CLI、Docker 或 macOS 26+ Apple `container`、`uv`。`[A]`
- README 自己标注安全边界：「The repo is visible (read-only) inside task containers … don't point it at untrusted tasks」（README:145-146）`[B]`

**给听众的一句话**：metaharness 是 omp 团队自己的「模型/harness A/B 实验台」，把 benchmark 从「跑一次看个数」升级成「experiment → arm → run → trace 四层可查询模型」。它值得抄的不是代码，是**这套数据模型**和「跑分脚本要有 schema」的态度。

---

## 6. swarm-extension：YAML 声明式 DAG

**结论：1795 行的小工具。是真的 DAG 调度器（Kahn 环检测 + wave 分层），但刻意不做数据流、不做重试、不做并发限制，也不让模型自主触发。它和「主循环自主决策」几乎完全正交——边界不是模糊的，是被硬切开的。** `[A][B]`

### 6.1 Schema：手写解析，无 zod

`packages/swarm-extension/src/swarm/schema.ts:5-21`：`[A]`

```ts
interface RawSwarmAgentConfig { role: string; task: string; extra_context?: string;
	reports_to?: string[]; waits_for?: string[]; model?: string; }
interface RawSwarmConfig { name: string; workspace: string; mode?: string;
	target_count?: number; model?: string; agents: Record<string, RawSwarmAgentConfig>; }
```

- 解析用 `Bun.YAML.parse` + 命令式校验（`schema.ts:57-114`），**没用 zod/arktype/typebox**——尽管扩展 API 三个都提供（`packages/coding-agent/src/extensibility/extensions/types.ts:1112-1119`）。`[A]`
- 顶层 key 必须是 `swarm`（`schema.ts:59-61`）；`name` 限制为 `/^[a-zA-Z0-9._-]+$/`（`schema.ts:55,67-69`），因为它会变成目录 `.swarm_<name>`（`state.ts:47`）——路径穿越防护。`[A]`
- `mode` 默认 `sequential`（不是 pipeline，`schema.ts:77`）；`target_count` 默认 1，且非 pipeline 模式禁止 ≠1（`schema.ts:109,152-154`）。`[A]`
- **仓库内没有任何 `.yaml` 样例文件**，示例只存在于 README（`README.md:278-296`）。`[A]`

### 6.2 调度：Kahn 环检测 + wave 分层

`packages/swarm-extension/src/swarm/dag.ts`：`[A]`

- `buildDependencyGraph`（`:17-50`）：边来自三处——显式 `waits_for`（`:25-31`）、`reports_to` 反转（A reports_to B ⇒ **B 依赖 A**，`:34-40`）、以及**仅当整图无显式依赖时**按 YAML 声明顺序串成链（`:43-47`）。**坑**：任何一条显式依赖都会让隐式链对**所有** agent 失效（`hasExplicitDeps`, `:52-57`）。
- `detectCycles`（`:63-98`）：Kahn 算法。
- `buildExecutionWaves`（`:106-146`）：反复剥离就绪节点成 wave，`wave.sort()` 保证确定性（`:135`），空 wave 抛 `Deadlock:`（`:128-132`）。

执行器 `PipelineController`（`pipeline.ts:45-213`）：wave 之间严格串行，wave 内 `Promise.all` 全并行（`pipeline.ts:155-156`）。

**并发上限：无。** `Promise.all(wave.map(...))` 无界——50 个并行节点就是 50 个并发子会话。宿主的信号量帮不上：`task.maxConcurrency`（默认 **32**，`packages/coding-agent/src/config/settings-schema.ts:4559-4561`；信号量 `packages/coding-agent/src/task/index.ts:631-638`）只在 `task` 工具的 spawn 路径上 acquire，而 swarm 直接调 `runSubprocess`（`executor.ts:66`），绕过了它。`[A]`

### 6.3 节点如何调 agent、如何传数据

`packages/swarm-extension/src/swarm/executor.ts:41-103`：`[A]`

- **每节点每轮一个全新隔离会话**。现场合成 `AgentDefinition`（`:51-56`），id 为 `swarm-<swarm>-<agent>-<iteration>`（`:49`）——第 N+1 轮是不同 session，无上下文继承。README 明说「Agents start fresh each iteration」（`README.md:428`，`[B]`）。
- system prompt = `You are a ${role}.` + 可选 `extra_context`（`:105-111`）；user prompt = 原样 `task` 字符串（`:70`）。
- cwd = 共享 workspace（`:67`），LSP 关闭（`:77`），会话 JSONL 落 `<workspace>/.swarm_<name>/context/`（`:78`）。
- 不指定 `tools` ⇒ 拿到完整默认工具集。

**节点间零数据传递**：无变量插值、无模板、无结果回填。`SingleResult.output` 只用于退出码聚合（`pipeline.ts:99-106`）。README 直言（`README.md:398`，`[B]`）：

> It does **not** pass data between them. Agents communicate through files in the shared workspace.

所以 `reports_to` 名字虽像数据流，实际**只是一条排序边**（`dag.ts:33-40`）。`[A]`

### 6.4 与「主循环自主决策」的边界

**边界是硬的：模型没有一等公民的触发入口。** `[A]`

- 扩展只注册了一个 slash command：`pi.registerCommand("swarm", ...)`（`packages/swarm-extension/src/extension.ts:25-64`）。
- **全包 `pi.registerTool` 一次都没调用**——尽管 API 支持（`.../extensions/types.ts` 中 `registerTool` 注释为 "Register a tool that the LLM can call"）。
- slash command 的 context 被文档标注为「session control methods only safe in **user-initiated** commands」（`.../extensions/types.ts:486-487`）。
- 结果回灌是单向且不触发轮次的：完成后 push 一条 `swarm-result` 自定义消息，`{ triggerTurn: false }`（`extension.ts:181-194`）——模型能看到摘要，但 swarm 永远不会自己起一轮。

**但有个未设防的口子**：`omp-swarm` 是全局安装的 bin（`package.json:23-25`），模型有 `bash`，理论上可以 shell 出去启动 swarm，包括 README 推荐的 `nohup … & disown` 形式（`README.md:25-26`）——那会完全脱离会话生命周期和 abort 信号。这是意外通路，不是设计。`[A]`

### 6.5 错误处理：几乎没有

`[A]`

- **零重试**：`pipeline.ts` / `executor.ts` / `dag.ts` 无任何 retry/backoff。只有宿主 agent 循环自带的 provider 级重试（作用于单个节点内部）。
- **节点失败不剪枝下游**：per-agent try/catch 把异常转成 `exitCode: 1` 的合成结果（`pipeline.ts:159-192`），`Promise.all` 永不 reject；wave 在启动前一次性算好（`extension.ts:106`），之后不重算——依赖全挂的节点照样执行，只是磁盘上没有它要的输入。
- **pipeline 模式下第 N 轮失败，第 N+1 轮照跑**（`pipeline.ts:72-107` 无 error break）。
- **TUI 启动的 swarm 没有取消路径**：`handleRun` 从不传 `signal`（`extension.ts:147-152`）；`cli.ts:78-91` 同。扩展也未订阅任何生命周期事件，会话结束不会拆除在飞的 swarm。
- **可恢复性是宣传而非实现**：`state.ts:5` 声称支持 resume，`StateTracker.load()`（`:113-122`）只被只读的 `/swarm status` 调用（`extension.ts:208`）；`handleRun` 永远调 `init()`（`extension.ts:118`）把所有 agent 重置为 pending。重跑 = 从头再来。
- 部分结果始终保留：`.swarm_<name>/state/pipeline.json` 每次变更即写（`state.ts:89-99,124-126`），加 append-only 日志。

### 6.6 扩展注册机制

`packages/swarm-extension/package.json:45-49`：`[A]`

```json
"omp": { "extensions": ["./src/extension.ts"] }
```

加载器读 `pkg.omp ?? pkg.pi`（`packages/coding-agent/src/extensibility/extensions/loader.ts:396-403`），用户在 `~/.omp/config.json` 的 `extensions` 数组里 opt-in（`README.md:33-39`，`[B]`）。扩展主体是 `(pi: ExtensionAPI) => void` 默认导出（`extension.ts:22`）。扩展宿主在 `packages/coding-agent/src/extensibility/extensions/`：`loader.ts`(624) / `runner.ts`(1396) / `wrapper.ts`(394) / `types.ts`(1571)。`[A]`

swarm 只用到 API 表面的一小角（`setLabel` / `registerCommand` / `logger` / `pi.settings` / `sendMessage` / `ctx.ui.notify` / `ctx.ui.setWidget`），订阅 **0** 个生命周期事件。`[A]`

### 6.7 测试覆盖

唯一的测试（`packages/swarm-extension/test/swarm/executor.test.ts:36-67`）mock 掉 `runSubprocess`，只断言一个回归。**`dag.ts` 的拓扑排序、环检测、wave 构建零测试覆盖。** 无 e2e、无 YAML fixture。`[A]`

---

## 7. 最适合上 slide 的 5 个发现

1. **「主循环」不是状态机，是钩子密度**。pi `AgentLoopConfig` 8 个钩子 / `runLoop` 275 行；omp 约 40 个钩子 / `runLoopBody` 500 行。骨架（双层 while）一模一样，差别全在「哪些决定被外包给宿主」。（`pi-mono/packages/agent/src/types.ts:173-271` vs `packages/agent/src/types.ts:142-526`）`[A]`

2. **abort 不是一个布尔，是四条信号**。硬杀（外部）/ 可打断工具（steering + IRC）/ 协作软信号（`ctx.steeringSignal`）/ 进程级暂停闸门。核心规则一句话：**排队的用户插话永远不会硬杀一个已经产生副作用的前台工具**。（`agent-loop.ts:2231-2247`、`pause.ts:1-19`）`[A]`

3. **逐工具的 shared/exclusive 并发调度，13 行搞定**。pi 是全局二选一；omp 让每个工具声明（甚至按参数动态决定）自己是 shared 还是 exclusive，exclusive 充当批次内写屏障。这是全篇最容易被小项目直接抄走的一段。（`agent-loop.ts:2660-2686`、`types.ts:757`）`[A]`

4. **错误恢复分两层，界限清晰**。循环内只管「这次 HTTP 流本身坏了」（Harmony 泄漏 / 半截 toolCall / 瞬时流错误改写 `stopReason` 为 `toolUse`）；会话层 `TurnRecovery`（1787 行，pi 完全没有）管「这个模型不行，换一个再来」（fallback 链 / 空回复重试 3 次 / 限流退避）。（`agent-loop.ts:1909-1952` vs `session/turn-recovery.ts:62-64,168`）`[A]`

5. **两个名字最唬人的包，实质都比名字朴素**——这条最有记忆点。`metaharness` 不是「harness 的 harness」，是跨 3 种 benchmark 的实验管理器（`private:true`、零反向依赖、归一化分发口只有 3 行）；`swarm-extension` 是 1795 行的 YAML DAG，**无并发上限、零重试、节点间零数据传递、模型无法自主触发、`dag.ts` 零测试覆盖**。反过来讲，真正有料的是不显山露水的 `AgentRegistry` + `IrcBus`：agent 有 `running/idle/parked/aborted` 状态机，能被 park 掉再复活，彼此还能发消息。（`metaharness/src/benchmarks.ts:243-248`、`swarm-extension/src/swarm/pipeline.ts:155`、`registry/agent-registry.ts:17-23`、`irc/bus.ts:1-16`）`[A]`

---

## 8. 存疑区（`[C]`）

1. `[C]` metaharness 疑似由 `packages/terminal-bench` 重命名而来：`docs/user-facing-packages.md:26-36` 仍描述 `packages/terminal-bench`（bin `tb2`），该目录在当前树已不存在，功能描述与 `src/runner.ts` 高度重合。未在 git history 中直接核实。
2. `[C]` swarm-extension 的 peerDep 写 `"@oh-my-pi/pi-coding-agent": "^16"` 而自身版本 `17.2.3`（`package.json:4,40`）。若 loader 不强制 peer range 则无害；未在 `loader.ts` 找到强制逻辑。
3. `[C]` 模型通过 `bash` 调 `omp-swarm` 是否被权限策略拦截：未找到任何针对 `omp-swarm` 的 allow/deny 条目。
4. `[C]` metaharness 当前是否活跃使用：未查看 `runs/` 目录内容与数据库真实记录。
5. `[C]` `docs/porting-from-pi-mono.md` 记录的上游同步点是 `b21b42d03`（2026-03-22），而对比基准 pi HEAD 为 2026-08-01。因此本文「pi 有 / omp 无」的判断，个别项可能是**上游在 3 月之后才加的**，而非 omp 主动删除。已逐条 grep 确认 omp 侧确实为 0 命中，但「omp 是主动删还是没跟上」这一动机层面无法从代码判定。

---

6. `[C]` 子代理没有硬性 spawn 深度上限：`MAX_NESTED_TASK_RENDER_DEPTH = 8`（`task/render.ts:62`）只是渲染深度，`taskDepth` 只被用于功能门控。推测实际深度由 `spawns:` 白名单约束，未找到常量。

---

## 9. 引用来源

- omp 代码：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi`（HEAD `09a7c8656`）
- pi 代码：`/Users/overkazaf/playground/research/pi/pi-mono`（HEAD `583f153d5`，2026-08-01）
- omp 仓库内文档：`docs/porting-from-pi-mono.md`、`docs/session.md`、`docs/tree.md`、`docs/task-agent-discovery.md`、`docs/user-facing-packages.md`、`packages/metaharness/README.md`、`packages/swarm-extension/README.md`
