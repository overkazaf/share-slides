# P03：产品路径 `AgentSession` vs SDK 路径 `AgentHarness`

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库本地路径 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95`（短 `583f153`） | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/agent/package.json:2`、`packages/coding-agent/package.json:2`（`"version": "0.83.0"`） |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，**每一条都在本 commit 上用 Read/sed 实际打开验证过**。
> 行号会随上游提交漂移 —— PPT 引用时必须带短 hash `583f153`。
>
> 本文是对 `build-your-own-agent/research/R10-pi-code-forensics.md` 第 0 节的**复核与深化**。复核结论：R10 的主体结论在新 commit 上仍然成立，但**有一条需要更正**（见 §1.3）。

---

## 0. 一页话结论

pi 这个 monorepo 里同时存在**两个完全独立的顶层 agent 编排类**，它们**共享同一个底层循环函数**，但**各自重写了持久化、工具集、扩展机制、错误模型、事件模型**：

| | **产品路径** | **SDK 路径** |
|---|---|---|
| 顶层类 | `AgentSession` | `AgentHarness` |
| 文件 | `packages/coding-agent/src/core/agent-session.ts` | `packages/agent/src/harness/agent-harness.ts` |
| 类声明行 | `:303`（`export class AgentSession {`） | `:173`（`export class AgentHarness<`） |
| 类结束行 | `:3332`（文件末） | `:1185`（文件末） |
| 类体行数 | **3030 行**（303→3332） | **1013 行**（173→1185） |
| 中间层 | 经 `Agent`（`packages/agent/src/agent.ts:171`，类体 407 行） | **无中间层，直接调 `runAgentLoop`** |
| 谁在用 | `pi` CLI 二进制（`packages/coding-agent/src/cli.ts`） | **仓库内零生产消费者**（只有自己的测试/文档） |

**共享内核**：`packages/agent/src/agent-loop.ts` 的 `runAgentLoop()`（`:95`）。两条路径在这一行汇合，详见 §2。

---

## 1. 两个顶层类：文件、行号、行数、谁在用

### 1.1 硬数字（`wc -l` + `awk` 实测）

```bash
$ wc -l packages/coding-agent/src/core/agent-session.ts \
        packages/agent/src/harness/agent-harness.ts \
        packages/agent/src/agent.ts \
        packages/agent/src/agent-loop.ts
    3332 packages/coding-agent/src/core/agent-session.ts
    1185 packages/agent/src/harness/agent-harness.ts
     577 packages/agent/src/agent.ts
     792 packages/agent/src/agent-loop.ts

$ grep -n "export class AgentSession\|export class AgentHarness\|export class Agent\b" \
    packages/coding-agent/src/core/agent-session.ts \
    packages/agent/src/harness/agent-harness.ts \
    packages/agent/src/agent.ts
packages/agent/src/harness/agent-harness.ts:173:export class AgentHarness<
packages/agent/src/agent.ts:171:export class Agent {
packages/coding-agent/src/core/agent-session.ts:303:export class AgentSession {

# 类体结束行（第一个顶格 `}` ）
$ awk 'NR>303 && /^}/ {print "AgentSession ends at", NR; exit}' packages/coding-agent/src/core/agent-session.ts
AgentSession ends at 3332
$ awk 'NR>173 && /^}/ {print "AgentHarness ends at", NR; exit}' packages/agent/src/harness/agent-harness.ts
AgentHarness ends at 1185
$ awk 'NR>171 && /^}/ {print "Agent ends at", NR; exit}' packages/agent/src/agent.ts
Agent ends at 577

# 类内一级方法数（顶格一个 tab 缩进的 `name(` / `async name(`）
$ grep -c "^	\(async \)\?[a-zA-Z_][a-zA-Z0-9_]*(" packages/coding-agent/src/core/agent-session.ts
46
$ grep -c "^	\(async \)\?[a-zA-Z_][a-zA-Z0-9_]*(" packages/agent/src/harness/agent-harness.ts
31

# 两个包的整体体量
$ find packages/agent/src/harness -name '*.ts' | xargs wc -l | tail -1
    8108 total
$ find packages/coding-agent/src -name '*.ts' | xargs wc -l | tail -1
   56431 total
```

即：**harness 子树 8108 行 vs coding-agent 全包 56431 行，约 1:7**。

### 1.2 `AgentSession` 的消费者（22 个源文件）

```bash
$ grep -rln "AgentSession" packages/*/src packages/*/*/src
```

输出 22 个文件，跨 **4 个包**：

- `packages/coding-agent/src/` —— 16 个：`cli.ts` / `main.ts` / `index.ts` / `core/{agent-session,agent-session-runtime,agent-session-services,sdk,index,bash-executor}.ts` / `core/extensions/wrapper.ts` / `core/tools/tool-definition-wrapper.ts` / `modes/{print-mode}.ts` / `modes/interactive/{interactive-mode,components/footer}.ts` / `modes/rpc/{rpc-mode,rpc-client}.ts`
- `packages/server/src/legacy/` —— 5 个：`rpc-process.ts` / `supervisor.ts` / `handler.ts` / `ipc/protocol.ts` / `ipc/server.ts`
- `packages/evals/src/pi-harness.ts` —— 1 个

唯一的实例化点（全仓仅 1 处）：

```bash
$ grep -rn "new AgentSession(" packages/coding-agent/src/ packages/*/src
packages/coding-agent/src/core/sdk.ts:376:	const session = new AgentSession({
```

同文件 `sdk.ts:294` 是全仓唯一的 `new Agent(`：

```bash
$ grep -rn "new Agent(" packages/coding-agent/src/
packages/coding-agent/src/core/sdk.ts:294:	agent = new Agent({
```

### 1.3 ⚠️ 需要更正 R10 的一条：`AgentHarness` **在仓库里没有任何生产消费者**

R10 第 0 节写「谁在用：`packages/evals`（`src/pi-harness.ts`）」。**这是子串误判**——`grep "AgentHarness"` 命中的是 evals 里的类型名 `PiCodingAgentHarnessOptions` / 函数名 `createPiCodingAgentHarness`，它里面的 "AgentHarness" 只是 `...CodingAgent` + `Harness...` 拼在一起的巧合。

用词边界重跑：

```bash
$ grep -rn "\bAgentHarness\b" packages/*/src packages/*/*/src | grep -v "^packages/agent/src/harness/"
# （无输出，exit 1）
```

再看 evals 到底 import 了什么：

```bash
$ grep -rn 'AgentHarness' packages/evals/
packages/evals/README.md:39:  ... Pi-specific evals use `createPiCodingAgentHarness(...)` from `src/pi-harness.ts` ...
packages/evals/src/extensions.eval.ts:5:import { createPiCodingAgentHarness, type PiCodingAgentInput } from "./pi-harness.ts";
packages/evals/src/smoke.eval.ts:3:import { createPiCodingAgentHarness } from "./pi-harness.ts";
```

而 `packages/evals/src/pi-harness.ts` 出现在上面 §1.2 的 `AgentSession` 消费者列表里 —— **evals 走的是产品路径 `AgentSession`，不是 `AgentHarness`**。

`packages/protocol/src/schemas.ts:37` 里的那一处只是一行注释，不是引用：

```ts
/** Matches AgentHarnessPhase so adapters do not need a second phase vocabulary. */
```

全仓 `AgentHarness`（词边界）的所有 `.ts`/`.md` 命中文件：

```bash
$ grep -rn --include='*.ts' --include='*.md' -l 'AgentHarness' packages
packages/agent/src/harness/{agent-harness,types,tools/{bash,read,edit,write}}.ts   # 自身实现
packages/agent/test/harness/{agent-harness.test,agent-harness-stream.test,tools.test,tool-context.types}.ts  # 自身测试
packages/agent/test/scratch/simple.ts                                              # 自身 scratch
packages/agent/docs/{harness,harness-v2,agent-harness,durable-harness,hooks,models,observability}.md  # 自身文档
packages/agent/CHANGELOG.md
packages/evals/{README.md,src/{pi-harness,extensions.eval,smoke.eval}.ts}          # ← 全是 PiCodingAgentHarness 子串误判
packages/protocol/src/schemas.ts                                                    # ← 一行注释
```

而 `new AgentHarness(` 在全仓的 src 里**一次都没出现**（`agent-harness.ts` 里的 20 多处 `new AgentHarnessError(` 是另一个类）：

```bash
$ grep -rn "new AgentHarness" packages/*/src packages/*/*/src
# 全部命中都是 `new AgentHarnessError(...)`：agent-harness.ts:145,146,147,148,230,545,551,674,686,694,710,716,732,738,750,757,785,790,795,803,847,854,878,890,1118
```

它是通过 `packages/agent/src/index.ts:6` 导出给外部使用者的：

```ts
export * from "./harness/agent-harness.ts";
```

**结论**：`AgentHarness` 是一个**只对外发布、仓库内自己都还没用上**的 SDK 层。这一点比 R10 原来的描述更极端，也更值得上 PPT。

---

## 2. 共享的底层内核：在哪一行汇合

两条路径都收敛到 **`packages/agent/src/agent-loop.ts` 的 `runAgentLoop()`（`:95`）**。

`runAgentLoop` 的签名与体（`agent-loop.ts:95-117`，实测）：

```ts
export async function runAgentLoop(
	prompts: AgentMessage[],
	context: AgentContext,
	config: AgentLoopConfig,
	emit: AgentEventSink,
	signal: AbortSignal | undefined,
	streamFn: StreamFn,
): Promise<AgentMessage[]> {                                    // :102
	const newMessages: AgentMessage[] = [...prompts];
	const currentContext: AgentContext = { ...context, messages: [...context.messages, ...prompts] };
	await emit({ type: "agent_start" });                          // :109
	await emit({ type: "turn_start" });                           // :110
	for (const prompt of prompts) { await emit({type:"message_start",message:prompt}); await emit({type:"message_end",message:prompt}); }
	await runLoop(currentContext, newMessages, config, signal, emit, streamFn ?? getDefaultStreamFn());  // :115
	return newMessages;                                           // :116
}
```

真正的双层 while 在私有的 `runLoop()`（`agent-loop.ts:155`）里。

**两个调用点，各一处：**

| 路径 | import | 调用点 |
|---|---|---|
| 产品 | `packages/agent/src/agent.ts:10`<br>`import { runAgentLoop, runAgentLoopContinue } from "./agent-loop.ts";` | `agent.ts:403`（`runPromptMessages` 内）<br>`agent.ts:416`（`runContinuation` 内） |
| SDK | `packages/agent/src/harness/agent-harness.ts:11`<br>`import { runAgentLoop } from "../agent-loop.ts";` | `agent-harness.ts:658`（`executeTurn` 内） |

产品路径（`agent.ts:401-411`）：

```ts
await this.runWithLifecycle(async (signal) => {          // :401，runWithLifecycle 定义在 :471
	await runAgentLoop(
		messages,
		this.createContextSnapshot(),                      // :405
		this.createLoopConfig(options),                    // :406
		(event) => this.processEvents(event),              // :407
		signal,
		this.streamFunction,
	);
});
```

SDK 路径（`agent-harness.ts:657-664`）：

```ts
return await runAgentLoop(
	messages,
	this.createContext(turnState, beforeResult?.systemPrompt),   // :660
	this.createLoopConfig(getTurnState, setTurnState),           // :661
	(event) => this.handleAgentEvent(event, signal),             // :662
	signal,
	this.createStreamFn(getTurnState),                           // :664
);
```

**一个可上 PPT 的细节**：同一个函数、同样 6 个参数，两边的用法却不同 ——
产品路径**丢弃返回值**（`await runAgentLoop(...)`，`agent.ts:403`，状态靠 `this._state.messages` 累积）；
SDK 路径**接住返回值**（`agent-harness.ts:679` `const newMessages = await runResultPromise;`，然后 `:680-685` 从尾部倒着找最后一条 `assistant` 消息作为 `prompt()` 的返回值，找不到就 `throw new AgentHarnessError("invalid_state", "AgentHarness prompt completed without an assistant message")`，`:686`）。

即：**产品路径是事件驱动的（fire-and-observe），SDK 路径是请求-响应的（`prompt(): Promise<AssistantMessage>`）**。

`packages/agent/src/index.ts` 把三层一起导出（`:3` `export * from "./agent.ts"` / `:5` `export * from "./agent-loop.ts"` / `:6` `export * from "./harness/agent-harness.ts"`），使用者可以选任意一层入场。

---

## 3. 五件事逐项对照

### 3.1 会话持久化

| | 产品路径 | SDK 路径 |
|---|---|---|
| 实现文件 | `packages/coding-agent/src/core/session-manager.ts`（**1712 行**，`wc -l`） | `packages/agent/src/harness/session/`（**9 个文件，3118 行**） |
| I/O 模型 | **同步 `node:fs`** | **异步 + 可注入 `FileSystem` 抽象** |
| 具体证据 | `session-manager.ts:5,10,14` import `appendFileSync` / `openSync` / `writeFileSync`；写点在 `:981,984,1021,1030,1033,1040,1620,1625` | `jsonl-store.ts:262` `appendEntry(...): Promise<void>`；`:277` `await this.fs.appendFile(...)` |
| 文件系统抽象 | 无（直接打 `node:fs`） | `JsonlSessionStoreFileSystem = Pick<FileSystem, "absolutePath"\|"joinPath"\|"readTextFile"\|"readTextLines"\|"writeFile"\|"appendFile"\|"listDir"\|"exists"\|"createDir"\|"remove">`（`jsonl-store.ts:24-34`）；`FileSystem` 定义在 `harness/types.ts:291`，`ExecutionEnv extends FileSystem, Shell` 在 `:373` |
| 后端数量 | **1 种**（本地 JSONL） | **3 种**：JSONL（`jsonl-store.ts`，438 行）、内存（`memory-store.ts`，130 行）、SQLite（独立包 `packages/storage/sqlite-node`） |
| 并发控制 | 无 | `KeyedOperationQueue`（`harness/session/keyed-operation-queue.ts`，69 行），`jsonl-store.ts:38` `DEFAULT_MAX_CONCURRENT_OPERATIONS = 4` |
| header 版本 | `version?: number`（可选，v1 老会话没有） | **硬编码 `version: 3`**（`jsonl-store.ts:42`，`interface SessionHeader { type: "session"; version: 3; ... }`） |
| entry 类型数 | **9 种**（`session-manager.ts:144-152`） | **11 种**（`harness/types.ts:453-464`），多出 `ActiveToolsChangeEntry` 与 `LeafEntry` |

两边的 entry 联合类型（实测原文）：

```ts
// packages/coding-agent/src/core/session-manager.ts:144
export type SessionEntry =
	| SessionMessageEntry | ThinkingLevelChangeEntry | ModelChangeEntry
	| CompactionEntry | BranchSummaryEntry | CustomEntry
	| CustomMessageEntry | LabelEntry | SessionInfoEntry;

// packages/agent/src/harness/types.ts:453
export type SessionTreeEntry =
	| MessageEntry | ThinkingLevelChangeEntry | ModelChangeEntry
	| ActiveToolsChangeEntry            // ★ 多
	| CompactionEntry | BranchSummaryEntry | CustomEntry
	| CustomMessageEntry | LabelEntry | SessionInfoEntry
	| LeafEntry;                        // ★ 多：把「当前叶子」也持久化
```

> `LeafEntry` 是 SDK 路径为「崩溃后恢复」准备的：产品路径的 `leafId` 只活在内存里（`session-manager.ts` 的 `this.leafId`，重启靠 `_buildIndex()` 重建），SDK 路径把它写进文件。

### 3.2 内置工具集

| | 产品路径 | SDK 路径 |
|---|---|---|
| 目录 | `packages/coding-agent/src/core/tools/` | `packages/agent/src/harness/tools/` |
| 数量 | **7 个** | **4 个** |
| 权威定义 | `core/tools/index.ts:83-84` | `harness/tools/index.ts:1-23`（导出列表） |

```ts
// packages/coding-agent/src/core/tools/index.ts:83-84
export type ToolName = "read" | "bash" | "edit" | "write" | "grep" | "find" | "ls";
export const allToolNames: Set<ToolName> = new Set(["read", "bash", "edit", "write", "grep", "find", "ls"]);
```

```bash
$ cat -n packages/agent/src/harness/tools/index.ts
# :7  createBashTool   (from "./bash.ts")
# :10 createEditTool   (from "./edit.ts")
# :15 createReadTool   (from "./read.ts")
# :22 type ExecutionToolContext (from "./tool-context.ts")
# :23 createWriteTool  (from "./write.ts")
```

**关键差异不是数量，是工厂函数怎么拿到文件系统**。同一个 `read` 工具，两边的签名：

```ts
// 产品路径 packages/coding-agent/src/core/tools/read.ts:203-205
export function createReadToolDefinition(
	cwd: string,                                    // ★ 直接吃一个 cwd 字符串
	options?: ReadToolOptions,
): ToolDefinition<typeof readSchema, ReadToolDetails | undefined> {

// SDK 路径 packages/agent/src/harness/tools/read.ts:45-47
export function createReadTool<TContext extends ExecutionToolContext = ExecutionToolContext>(
	options?: ReadToolOptions,                      // ★ 没有 cwd
): AgentHarnessTool<TContext, typeof readSchema, ReadToolDetails | undefined> {
```

SDK 版把环境从**第 5 个 execute 参数**里解构出来（`harness/tools/read.ts:53-55`）：

```ts
async execute(_toolCallId, { path, offset, limit }, signal, _onUpdate, { env }) {   // :53
	const absolutePath = await resolveReadToolPath(env, path, signal);               // :54
	const bytes = getOrThrow(await env.readBinaryFile(absolutePath, signal));        // :55
```

`env` 的类型（`harness/tools/tool-context.ts:1-6`，整文件 6 行）：

```ts
import type { ExecutionEnv } from "../types.ts";
/** Filesystem and shell context required by the built-in execution tools. */
export interface ExecutionToolContext {
	env: ExecutionEnv;
}
```

> 上 PPT 的点：**产品路径的工具绑死本地进程的 fs/shell；SDK 路径的工具对 `ExecutionEnv` 编程，所以同一份 `read`/`bash`/`edit`/`write` 可以跑在远端容器、内存 FS 或沙箱里。**这是两边工具实现无法合并的真正原因（description 字符串两边一字不差，`coding-agent/.../read.ts:212` 与 `harness/tools/read.ts:51` 完全相同）。

### 3.3 扩展机制

| | 产品路径 | SDK 路径 |
|---|---|---|
| 扩展面 | `ExtensionAPI` 接口 | `AgentHarness` 实例方法 |
| 定义位置 | `packages/coding-agent/src/core/extensions/types.ts:1193` | `packages/agent/src/harness/agent-harness.ts:1157`（`subscribe`）+ `:1170`（`on`） |
| 钩子数 | **33 个 `on()` 重载** | **22 个事件类型** |
| 加载器 | 有：`extensions/loader.ts`（jiti 动态 import 用户 `.ts`） | **无**，调用方自己 `harness.on(...)` |
| 层规模 | `core/extensions/` 5 个文件 **3893 行**（`types.ts` 独占 1713 行） | 无独立目录 |

计数命令：

```bash
$ grep -c "^	on(" packages/coding-agent/src/core/extensions/types.ts
33
$ grep -n "export interface ExtensionAPI" packages/coding-agent/src/core/extensions/types.ts
1193:export interface ExtensionAPI {
$ wc -l packages/coding-agent/src/core/extensions/*.ts
   1713 packages/coding-agent/src/core/extensions/types.ts
     45 packages/coding-agent/src/core/extensions/wrapper.ts
   ...
   3893 total
```

SDK 侧的 22 项在 `AgentHarnessEventResultMap`（`harness/types.ts:816-838`，逐行实测）：

```ts
export type AgentHarnessEventResultMap = {
	before_agent_start: BeforeAgentStartResult | undefined;        // ★ 可改流程
	context: ContextResult | undefined;                             // ★
	before_provider_request: BeforeProviderRequestResult | undefined; // ★
	before_provider_payload: BeforeProviderPayloadResult | undefined; // ★
	after_provider_response: undefined;
	tool_call: ToolCallResult | undefined;                          // ★
	tool_result: ToolResultPatch | undefined;                       // ★
	session_before_compact: SessionBeforeCompactResult | undefined; // ★
	session_compact: undefined;
	session_before_tree: SessionBeforeTreeResult | undefined;       // ★
	session_tree: undefined;
	retry_scheduled: undefined;  retry_attempt_start: undefined;  retry_finished: undefined;
	model_update: undefined;  thinking_level_update: undefined;
	resources_update: undefined;  tools_update: undefined;  queue_update: undefined;
	save_point: undefined;  abort: undefined;  settled: undefined;
};
```

**22 项里 8 项返回非 `undefined` 类型（可改流程），14 项是纯通知。**

注册 API 的形态差异（`agent-harness.ts:1157-1182`）：

```ts
subscribe(listener: (event: AgentHarnessEvent<...>, signal?: AbortSignal) => Promise<void>|void): () => void  // :1157 —— 全量被动订阅
on<TType extends keyof AgentHarnessEventResultMap>(                                                            // :1170 —— 按类型的可拦截钩子
	type: TType,
	handler: (event: Extract<AgentHarnessOwnEvent, {type: TType}>) => Promise<AgentHarnessEventResultMap[TType]> | AgentHarnessEventResultMap[TType],
): () => void
```

两者都返回 unsubscribe 闭包（`:1166` `return () => handlers!.delete(...)`、`:1181` 同）。

产品路径的 33 项包含 SDK 没有的 UI/生命周期项：`project_trust` / `resources_discover` / `session_start` / `session_info_changed` / `session_before_switch` / `session_before_fork` / `session_shutdown` / `model_select` / `thinking_level_select` / `user_bash` / `input` / `message_start` / `message_update` / `message_end` / `tool_execution_start` / `tool_execution_update` / `tool_execution_end` / `agent_settled` 等。

> 差别的本质：**产品路径的扩展点里塞了大量「跟人交互」的事件（`input`、`model_select`、`user_bash`），SDK 路径一个都没有。**

### 3.4 错误处理

| | 产品路径 | SDK 路径 |
|---|---|---|
| 错误类型 | **无自定义 Error 类**（`grep -rn "class .*Error" agent-session.ts` 无输出），抛裸 `Error` | `AgentHarnessError`（`harness/types.ts:258`），带 9 值 `code` |
| turn 级自动重试 | **有** | **无** |
| compaction/summary 重试 | 有 | 有 |
| context overflow 自救 | **有**（一次） | 无 |
| 自动压缩触发 | **有** | **无** |

`AgentHarnessError` 全文（`harness/types.ts:246-266`）：

```ts
export type AgentHarnessErrorCode =
	| "busy" | "invalid_state" | "invalid_argument" | "session"
	| "hook" | "auth" | "compaction" | "branch_summary" | "unknown";

/** Public AgentHarness failure with a stable top-level classification. */
export class AgentHarnessError extends Error {
	public code: AgentHarnessErrorCode;
	constructor(code: AgentHarnessErrorCode, message: string, cause?: Error) {
		super(message, cause === undefined ? undefined : { cause });
		this.name = "AgentHarnessError";
		this.code = code;
	}
}
```

`agent-harness.ts:145-148` 的归一化函数把子系统错误映射进来：

```ts
if (cause instanceof SessionError) return new AgentHarnessError("session", cause.message, cause);
if (cause instanceof CompactionError) return new AgentHarnessError("compaction", cause.message, cause);
if (cause instanceof BranchSummaryError) return new AgentHarnessError("branch_summary", cause.message, cause);
return new AgentHarnessError(fallbackCode, cause.message, cause);
```

SDK 路径还有一处**双重失败的聚合**（`agent-harness.ts:665-675`）——重试上报本身也失败时用 `AggregateError` 包住两个错因：

```ts
} catch (error) {
	try { return await this.emitRunFailure(activeTurnState.model, error, signal.aborted, signal); }
	catch (failureError) {
		const cause = new AggregateError([toError(error), toError(failureError)], "Agent run failed and failure reporting failed");
		throw new AgentHarnessError("unknown", cause.message, cause);
	}
}
```

产品路径的重试（`agent-session.ts`）：

- `_isRetryableError()` `:2635-2639`，**明确排除 context overflow**：
  ```ts
  // Context overflow is handled by compaction, not retry.
  if (isContextOverflow(message, this.model?.contextWindow ?? 0)) return false;   // :2637
  return isRetryableAssistantError(message);                                       // :2638
  ```
- `_prepareRetry()` `:2674-2700`，指数退避：`const delayMs = settings.baseDelayMs * 2 ** (this._retryAttempt - 1);`（`:2691`）；上限 `settings.maxRetries`（`:2682`）
- overflow 只救一次：`private _overflowRecoveryAttempted = false;`（`:327`），置位在 `:2003`，判定在 `:1990`，复位在 `:599`、`:651`
- 自动压缩：`_checkCompaction()` `:1953`，被 `:1096` 和 `:1201` 调用，末尾 `:2038` `if (shouldCompact(contextTokens, contextWindow, settings))`

SDK 路径的重试**只覆盖两种摘要操作**（`agent-harness.ts:276-282`）：

```ts
private retryCallbacks(operation: "compaction" | "branch_summary"): RetryCallbacks {   // :276 ★ 只有这两个字面量
```

调用点仅 `:815`（compaction）与 `:886`（branch summary）。

**自动压缩的判定式在 SDK 路径里一次都没被调用**（决定性证据）：

```bash
$ grep -n "shouldCompact" packages/agent/src/harness/agent-harness.ts packages/coding-agent/src/core/agent-session.ts
packages/coding-agent/src/core/agent-session.ts:63:	shouldCompact,
packages/coding-agent/src/core/agent-session.ts:2038:		if (shouldCompact(contextTokens, contextWindow, settings)) {
# agent-harness.ts：零命中
```

SDK 侧只有显式 `async compact(customInstructions?: string): Promise<CompactResult>`（`agent-harness.ts:783`），且第一行就是忙态门禁（`:785`）：

```ts
if (this.phase !== "idle") throw new AgentHarnessError("busy", "compact() requires idle harness");
```

> 上 PPT 的点：**压缩算法是共享的纯函数（`DEFAULT_COMPACTION_SETTINGS` 两边同源），但「什么时候压」的决策产品路径自己做、SDK 路径原样交还给宿主。**

**并发模型也不同**：SDK 路径有显式相态机

```ts
// packages/agent/src/harness/types.ts:575
export type AgentHarnessPhase = "idle" | "turn" | "compaction" | "branch_summary" | "retry";
```

`"busy"` 守卫遍布 `agent-harness.ts:694, 710, 732, 785, 847`。产品路径没有 phase 枚举，用布尔 `_isAgentRunActive`（`agent-session.ts:1062`）+ `waitForIdle()`；底层 `Agent.prompt()` 用 `this.activeRun` 判忙并抛裸 `Error`（`agent.ts:340-343`）：

```ts
if (this.activeRun) {
	throw new Error("Agent is already processing a prompt. Use steer() or followUp() to queue messages, or wait for completion.");
}
```

### 3.5 事件模型

| | 产品路径 | SDK 路径 |
|---|---|---|
| 类型名 | `AgentSessionEvent`（`agent-session.ts:139-179`） | `AgentHarnessEvent`（`harness/types.ts:764-766`） |
| 构成 | `Exclude<AgentEvent, {type:"agent_end"}>` **+ 16 个自有变体** | `AgentEvent` **+ `AgentHarnessOwnEvent`（22 个）** |
| 对 `agent_end` 的处理 | **改写**：排除内核版，自己发带 `willRetry` 的版本 | 原样透传 |
| 监听器签名 | `(event) => void`（**同步**，`:184`） | `(event, signal?) => Promise<void> \| void`（**可 await**，`agent-harness.ts:1158`） |

产品路径的类型头（`agent-session.ts:139-146`，这是最能说明问题的 8 行）：

```ts
export type AgentSessionEvent =
	| Exclude<AgentEvent, { type: "agent_end" }>        // ★ 把内核的 agent_end 剔掉
	| {
			type: "agent_end";
			messages: AgentMessage[];
			willRetry: boolean;                          // ★ 换成自己的、多一个 willRetry 字段
	  }
	| { type: "agent_settled" }
```

其余自有变体（`:147-179`）：`queue_update` / `compaction_start` / `compaction_end` / `entry_appended` / `session_info_changed` / `thinking_level_changed` / `auto_retry_start` / `auto_retry_end` / `summarization_retry_scheduled` / `summarization_retry_attempt_start`（两个重载：`branchSummary` 与 `compaction`）/ `summarization_retry_finished` / `bash_execution_update`。

SDK 路径（`harness/types.ts:764-766`）是**纯加法**：

```ts
export type AgentHarnessEvent<TSkill extends Skill = Skill, TPromptTemplate extends PromptTemplate = PromptTemplate> =
	| AgentEvent                                        // ★ 内核事件原样保留
	| AgentHarnessOwnEvent<TSkill, TPromptTemplate>;    // ★ 22 个自有事件叠加
```

`AgentHarnessOwnEvent`（`:737-761`）列全 22 项：`QueueUpdateEvent` / `SavePointEvent` / `AbortEvent` / `SettledEvent` / `BeforeAgentStartEvent` / `ContextEvent` / `BeforeProviderRequestEvent` / `BeforeProviderPayloadEvent` / `AfterProviderResponseEvent` / `ToolCallEvent` / `ToolResultEvent` / `SessionBeforeCompactEvent` / `SessionCompactEvent` / `SessionBeforeTreeEvent` / `SessionTreeEvent` / `RetryScheduledEvent` / `RetryAttemptStartEvent` / `RetryFinishedEvent` / `ModelUpdateEvent` / `ThinkingLevelUpdateEvent` / `ResourcesUpdateEvent` / `ToolsUpdateEvent`。

> 上 PPT 的点：**同一个内核事件流，产品路径选择「重写 `agent_end` 让 UI 知道还要不要转圈」，SDK 路径选择「一个字节都不改，只往后加」。这是两种截然不同的兼容性哲学。**

---

## 4. 为什么会存在两套 —— 找到了直接的文档证据

**结论：`AgentHarness` 是 `AgentSession` 的规划中的继任者，切换排期在 pi 2.0，当前 0.83.0 处于「两套并存」的过渡态。**

### 证据 A：`packages/agent/docs/models.md:789-793`（标题就叫「Current interim state」）

```
Current interim state:

- `AgentHarness` already accepts a `Models` instance and uses it for turn streaming, compaction, and branch summaries.
- coding-agent does not use `AgentHarness` yet; `AgentSession` still drives the low-level `Agent` with a `streamFn`.
- coding-agent still uses legacy `AuthStorage` + `ModelRegistry` and imports old global pi-ai APIs through `@earendil-works/pi-ai/compat`.
```

第二条是全仓最直白的一句话：**"coding-agent does not use `AgentHarness` yet"**。

### 证据 B：`packages/agent/docs/models.md:860`（Phase 9 段落）

> coding-agent replaces AuthStorage and ModelRegistry's internals with `FileCredentialStore` + a `MutableModels` collection. **AgentSession itself stays (AgentHarness adoption is pi 2.0)**; only its model/auth substrate swaps.

括号里点名了版本号：**AgentHarness adoption is pi 2.0**。

### 证据 C：`packages/agent/docs/models.md:936-938`（Phase 10，标题 "compat deletion (pi 2.0 era, separate)"）

```
### Phase 10 — compat deletion (pi 2.0 era, separate)

- [ ] AgentSession -> AgentHarness; the registry facade dies in favor of harness `Models`.
```

**是个未勾选的 `[ ]`**。同文档 `:848` 的已完成项也复述了同一事实：

> - [x] Everything else originally sketched here is gated on coding-agent actually streaming through a `Models` instance — **coding-agent's `AgentSession` drives the low-level `Agent` via `streamFn`, not the harness** — and moved to Phase 9.

### 证据 D：harness 的两份设计文档标题就是「计划」

```bash
$ wc -l packages/agent/docs/*.md
    506 packages/agent/docs/agent-harness.md
    212 packages/agent/docs/durable-harness.md
   1827 packages/agent/docs/harness-v2.md
   2390 packages/agent/docs/harness.md
    445 packages/agent/docs/hooks.md
    964 packages/agent/docs/models.md
    376 packages/agent/docs/observability.md
```

- `harness.md:1` —— `# Durable AgentHarness plan`
- `harness-v2.md:1` —— `# Durable AgentHarness design`
- `agent-harness.md:5` —— "This document describes the current direction and implemented behavior. **Some extension/session-facade details are planned and called out explicitly.**"

**harness 的文档（4217 行，两份 plan/design）比它的实现（agent-harness.ts 1185 行）还多 3.5 倍**，这本身就是「设计先行、尚未落地」的量化信号。

### 证据 E：`AgentHarness` 想解决而 `AgentSession` 解决不了的问题，写在 `harness.md:5-11` 的 Goals 里

```
- **Durable runs.** An accepted prompt is a durable operation. After a process crash, a new process
  restores the session and resumes the run from the last safe boundary.
- **Correct branch semantics.** ... a crash between records must leave either a valid pre-operation
  state or one that recovery completes — never a half-moved cursor or a summary on the wrong branch.
- **Harness API.** Passive events to observe execution; awaited hooks to transform harness behavior.
- **Observability.** Everything is instrumentable — down to provider request/response internals ...
- **UI model.** Atomic snapshot plus live event stream. No event replay; reconnect means new snapshot.
- **Single writer, parallel refs.** ... a session hosts one or more **refs** — named movable leaf
  pointers, each running at most one operation at a time, in parallel with its siblings ...
- **Old sessions load.** Existing session files open unchanged and restore as idle.
```

`harness-v2.md:24` 把「多租户」这个动机说得更直白：

> **Lanes.** A session hosts one or more lanes. ... **Example: a Slack channel is a session; each thread is a lane.** Interactive pi uses one lane and does not show the concept in its UI.

`harness-v2.md:3` 的兼容性政策也说明了它敢重写的底气：

> **Compatibility policy.** Old coding-agent v3 JSONL sessions must open and restore idle. **This is the only backward-compatibility requirement.** All other formats and APIs in `packages/agent/src/harness` ... may break. We do not write migrations, schema versioning, or conversion paths for anything else.

**综上，「为什么两套」的完整答案（有据可查、不需要猜）**：

1. `AgentSession` 是**先长出来的产品实现**，绑死本地 fs、本地 TUI、单会话单进程；
2. `AgentHarness` 是**为「崩溃可恢复 + 多 lane 并行 + 可替换存储 + 可远程执行环境」重新设计的下一代编排层**；
3. 两者刻意共享 `runAgentLoop` 这一个内核，是为了让新层不必重做 LLM 循环；
4. 切换动作被明确排到 **pi 2.0**，当前 0.83.0 的 harness **在仓库内只有测试在用**。

**没找到的**：我**没有**在任何代码注释或文档中找到「为什么不直接把 AgentSession 重构成 AgentHarness、而要另起一个类」的正面解释。上面的第 3、4 条是从 Goals/Compatibility policy 反推的，属于我的推断，不是原文断言。

---

## 5. `pi` 二进制从入口到进入循环的完整调用链

`pi` 的 bin 映射（`packages/coding-agent/package.json:9-11`）：

```json
"bin": {
	"pi": "dist/cli.js"
},
```

`dist/cli.js` 的源是 `packages/coding-agent/src/cli.ts`（整文件 **20 行**，全文如下，行号实测）：

```ts
#!/usr/bin/env node                                                   // :1
import { APP_NAME } from "./config.ts";                               // :8
import { configureHttpDispatcher } from "./core/http-dispatcher.ts";  // :9
import { main } from "./main.ts";                                     // :10
process.title = APP_NAME;                                             // :12
process.env.PI_CODING_AGENT = "true";                                 // :13
process.emitWarning = (() => {}) as typeof process.emitWarning;       // :14
configureHttpDispatcher();                                            // :18
main(process.argv.slice(2));                                          // :20
```

### 逐跳调用链（14 跳，交互模式）

| # | 跳 | 位置 |
|---|---|---|
| 1 | shell 执行 `pi` → `dist/cli.js` | `packages/coding-agent/package.json:10` |
| 2 | `main(process.argv.slice(2))` | `packages/coding-agent/src/cli.ts:20` |
| 3 | `export async function main(args, options?)` | `packages/coding-agent/src/main.ts:521` |
| 4 | `createAgentSessionServices({...})` —— 装配 settings/extensions/resourceLoader/modelRuntime | `main.ts:686` → 实现 `core/agent-session-services.ts:134` |
| 5 | `createAgentSessionFromServices({services, sessionManager, ...})` | `main.ts:769` → 实现 `core/agent-session-services.ts:200` |
| 6 | `return createAgentSession({...})` | `core/agent-session-services.ts:203` |
| 7 | `export async function createAgentSession(options)` | `core/sdk.ts:169` |
| 8 | **`agent = new Agent({ initialState: {...} })`** ← 全仓唯一 | `core/sdk.ts:294` |
| 9 | **`const session = new AgentSession({ agent, sessionManager, ... })`** ← 全仓唯一 | `core/sdk.ts:376` |
| 10 | `const runtime = await createAgentSessionRuntime(createRuntime, {...})` | `main.ts:793` → 实现 `core/agent-session-runtime.ts` |
| 11 | `const interactiveMode = new InteractiveMode(runtime, {...})` | `main.ts:872`（类定义 `modes/interactive/interactive-mode.ts:348`） |
| 12 | `await interactiveMode.run()` | `main.ts:902`（方法定义 `interactive-mode.ts:891`） |
| 13 | 主交互 while：`const userInput = await this.getUserInput(); await this.session.prompt(userInput);` | `interactive-mode.ts:973`（首条消息走 `:951`，`--message` 批量走 `:961`） |
| 14 | `async prompt(text, options?)` | `core/agent-session.ts:1114` |
| 15 | `await this._runAgentPrompt(messages)` | `core/agent-session.ts:1264`（另一入口 `:1451`） |
| 16 | `await this.agent.prompt(messages)` | `core/agent-session.ts:1064`（在 `_runAgentPrompt`，定义 `:1061`） |
| 17 | `async prompt(input, images?)` → `await this.runPromptMessages(messages)` | `packages/agent/src/agent.ts:339` → `:346` |
| 18 | `await this.runWithLifecycle(async (signal) => {...})` | `agent.ts:401`（`runWithLifecycle` 定义 `:471`） |
| 19 | **`await runAgentLoop(messages, snapshot, config, emit, signal, streamFn)`** | `agent.ts:403` |
| 20 | `await runLoop(currentContext, newMessages, config, signal, emit, streamFn)` | `packages/agent/src/agent-loop.ts:115` |
| 21 | **双层 while 主循环** | `agent-loop.ts:155`（`async function runLoop(`） |

非交互模式的两个分叉（同在 `main.ts`）：

- `--mode rpc` → `await runRpcMode(runtime)`（`main.ts:869`）
- print 模式 → `const exitCode = await runPrintMode(runtime, {...})`（`main.ts:904`）

三条都在第 10 跳的 `runtime` 之后分叉，第 13 跳之后完全重合。

`_runAgentPrompt` 的完整体（`agent-session.ts:1061-1070`，注意 `while` 里的 `continue()`）：

```ts
private async _runAgentPrompt(messages: AgentMessage | AgentMessage[]): Promise<void> {
	this._isAgentRunActive = true;
	try {
		await this.agent.prompt(messages);                    // :1064
		while (await this._handlePostAgentRun()) {             // :1065  ★ 重试/压缩后继续
			await this.agent.continue();                        // :1066
		}
	} finally { ... }
```

> 这个 `while` 就是产品路径「压缩后自动续跑 / 重试后自动续跑」的实现位置 —— **它在 `runAgentLoop` 之外**，所以 SDK 路径天然没有。

---

## 6. 对「自己造 harness 的人」的启发

> **以下整节是我的判断，不是从代码里读出的事实。**事实部分已在 §1–§5 给完，本节是解读。请在 PPT 上明确区分。

### 6.1 我认为「好」的三点（判断）

**（a）把「LLM 循环」压缩成一个 6 参数的纯函数，是这套分层能成立的唯一原因。**（判断）

事实支撑：`runAgentLoop(prompts, context, config, emit, signal, streamFn)`（`agent-loop.ts:95-101`）不持有任何状态、不碰文件系统、不知道 UI 存在。正因如此，`AgentSession`（3030 行，绑死本地 fs + TUI）与 `AgentHarness`（1013 行，对 `ExecutionEnv` 编程）能在**零改动**地复用同一份 792 行循环。

我的判断：如果你自己造 harness，**第一件事是把循环函数的签名压到不含任何 I/O**。判断循环层是否干净的一个可操作标准：它能不能同时被一个「同步写本地文件的 CLI」和一个「异步写 SQLite 的服务端」调用而不改一行。pi 在这一点上通过了。

**（b）事件是加法、不是改写 —— SDK 层的做法更可持续。**（判断）

事实支撑：`AgentHarnessEvent = AgentEvent | AgentHarnessOwnEvent`（`harness/types.ts:764-766`）是纯并集；`AgentSessionEvent` 用 `Exclude<AgentEvent, {type:"agent_end"}>`（`agent-session.ts:140`）剔掉内核事件再自己发一个同名但字段不同的版本。

我的判断：产品路径的做法立刻带来一个隐蔽成本 —— 任何同时看这两种事件流的代码（比如 `packages/protocol`）都要处理「`agent_end` 有两个不兼容的形状」。`protocol/src/schemas.ts:37` 的那行注释（"Matches AgentHarnessPhase so adapters do not need a second phase vocabulary."）说明团队已经在为「两套词汇表」付协调成本了。**自己造的时候，宁可让上层多一个 `agent_end_final` 事件，也别改内核事件的形状。**

**（c）`ExecutionEnv` 抽象是把工具从本地进程里解耦出来的最小代价。**（判断）

事实支撑：`ExecutionToolContext { env: ExecutionEnv }`（`harness/tools/tool-context.ts:4-6`，整文件 6 行）+ `execute(..., { env })`（`harness/tools/read.ts:53`）。两边 `read` 的 description 字符串一字不差，唯一的差别就是 `cwd: string` 参数变成了 `env` 上下文。

我的判断：**这个改动的收益（可换沙箱/远端/内存 FS）远大于成本（多一层 Result 包装 `getOrThrow(await env.readBinaryFile(...))`）。**如果你打算做的 agent 有任何可能要跑在容器或远端，从第一天就用 env 抽象，别用 cwd。

### 6.2 我认为「坏」的三点（判断）

**（a）0.83.0 上并存两套是净负债，不是净资产。**（判断）

事实支撑：harness 侧 8108 行代码 + 4217 行 plan/design 文档，**生产消费者为零**（§1.3）；产品路径的 56431 行还在照旧演进。Phase 10 的 `[ ] AgentSession -> AgentHarness` 未勾选（`models.md:938`）。

我的判断：这已经不是「过渡态」而是**长期分叉**。同一个 `read` 工具两份实现、`SessionEntry` 两个 9/11 项的联合类型、`compaction` 两份触发逻辑、`Skill` 两个结构（一个有 `content` 一个没有），每一处都是未来合并时的迁移债。对小团队来说这是**明确的反面教材**：**不要在旧层还在高速演进的时候把新层写到 8000 行还不接线。** 更安全的做法是让新层先吃掉旧层的一个真实场景（哪怕只是 `--mode rpc`），拿真流量验证抽象。

**（b）3030 行的 `AgentSession` 说明「产品层」缺一次拆分。**（判断）

事实支撑：单类 3030 行、46 个一级方法，同时管着 system prompt 重建（`:1021`）、压缩触发（`:1953`）、重试退避（`:2674`）、工具注册表（`:2596` 附近）、bash 执行消息缓冲（`_flushPendingBashMessages`）、扩展命令展开（`_tryExecuteExtensionCommand`）。

我的判断：这是典型的「God object 沿着功能自然生长」。harness 用 phase 状态机（`"idle"|"turn"|"compaction"|"branch_summary"|"retry"`，`harness/types.ts:575`）+ 忙态守卫替代了 `AgentSession` 里散落的布尔标志（`_isAgentRunActive`、`_overflowRecoveryAttempted`、`_retryAttempt`），**这个方向是对的**。造自己的 harness 时，把「当前在干什么」做成显式枚举而不是若干布尔，是低成本高回报的。

**（c）「重试/压缩后续跑」放在循环外面（`_runAgentPrompt` 的 `while`，`agent-session.ts:1065-1067`）是个设计裂缝。**（判断）

事实支撑：内核 `runAgentLoop` 返回后，产品层用 `while (await this._handlePostAgentRun()) { await this.agent.continue(); }` 继续；SDK 层没有这个 while，所以 SDK 层根本没有自动重试和自动压缩（§3.4 的 `shouldCompact` 零命中即证）。

我的判断：**「一次 prompt 到底要不要自动续跑」是编排层最核心的语义，把它留在内核外面导致两条路径的「一次 prompt」含义不同** —— 产品路径的 `prompt()` 可能触发 N 次 LLM 往返（压缩 + 重试 + 续跑），SDK 路径的 `prompt()` 只是一次 `runAgentLoop`。这种同名不同义是最贵的那种不一致。如果我来造，会把「continuation policy」做成传给循环的一个回调（pi 其实已经有 `config.shouldStopAfterTurn`、`config.getFollowUpMessages` 这样的钩子），而不是让每个宿主自己在外面写 while。

### 6.3 一句话带走（判断）

**分层本身是对的（纯函数循环 + 可替换编排层），但 pi 在 0.83.0 上展示的是「分层的账单先到、收益还没到」的中间状态。** 抄它的循环设计，别抄它的并存策略。

---

## 附：本文用到的全部 grep / shell 命令原文

```bash
cd /Users/overkazaf/playground/research/pi/pi-mono

# 基线
git log -1 --date=iso --format='%H%n%ad%n%s'
grep '"version"' packages/agent/package.json packages/coding-agent/package.json

# 两个顶层类
wc -l packages/coding-agent/src/core/agent-session.ts packages/agent/src/harness/agent-harness.ts \
      packages/agent/src/agent.ts packages/agent/src/agent-loop.ts
grep -n "export class AgentSession\|export class AgentHarness\|export class Agent\b" \
      packages/coding-agent/src/core/agent-session.ts packages/agent/src/harness/agent-harness.ts packages/agent/src/agent.ts
awk 'NR>303 && /^}/ {print "AgentSession ends at", NR; exit}' packages/coding-agent/src/core/agent-session.ts
awk 'NR>173 && /^}/ {print "AgentHarness ends at", NR; exit}' packages/agent/src/harness/agent-harness.ts
awk 'NR>171 && /^}/ {print "Agent ends at", NR; exit}' packages/agent/src/agent.ts
grep -c "^	\(async \)\?[a-zA-Z_][a-zA-Z0-9_]*(" packages/coding-agent/src/core/agent-session.ts
grep -c "^	\(async \)\?[a-zA-Z_][a-zA-Z0-9_]*(" packages/agent/src/harness/agent-harness.ts
find packages/agent/src/harness -name '*.ts' | xargs wc -l | tail -1
find packages/coding-agent/src -name '*.ts' | xargs wc -l | tail -1

# 谁在用（★ 关键：R10 的更正就来自这两条）
grep -rln "AgentSession" packages/*/src packages/*/*/src
grep -rln "AgentHarness" packages/*/src packages/*/*/src           # 含 PiCodingAgentHarness 子串误判
grep -rn  "\bAgentHarness\b" packages/*/src packages/*/*/src | grep -v "^packages/agent/src/harness/"   # 无输出
grep -rn --include='*.ts' --include='*.md' -l 'AgentHarness' packages
grep -rn 'AgentHarness' packages/evals/
grep -n  'AgentHarness' packages/protocol/src/schemas.ts
grep -rn "new AgentSession(" packages/coding-agent/src/ packages/*/src
grep -rn "new Agent(" packages/coding-agent/src/
grep -rn "new AgentHarness" packages/*/src packages/*/*/src

# 共享内核
grep -n "agent-loop\|runAgentLoop\|agentLoop" packages/agent/src/agent.ts
grep -n "agent-loop\|runAgentLoop" packages/agent/src/harness/agent-harness.ts
grep -n "^async function runLoop" packages/agent/src/agent-loop.ts
cat -n packages/agent/src/index.ts

# 持久化
wc -l packages/coding-agent/src/core/session-manager.ts packages/agent/src/harness/session/*.ts
grep -n "appendFileSync\|writeFileSync\|openSync\|readFileSync" packages/coding-agent/src/core/session-manager.ts
grep -n "append\|writeFile\|fs\." packages/agent/src/harness/session/jsonl-store.ts
grep -n "export interface FileSystem\|export interface ExecutionEnv\|export interface SessionStore\|export interface SessionReader" packages/agent/src/harness/types.ts
ls packages/storage/
grep -n "export type SessionTreeEntry" packages/agent/src/harness/types.ts
grep -n "export type SessionEntry =" packages/coding-agent/src/core/session-manager.ts

# 工具集
grep -n "export type ToolName\|export const allToolNames" packages/coding-agent/src/core/tools/index.ts
cat -n packages/agent/src/harness/tools/index.ts
grep -n "export function createReadToolDefinition" packages/coding-agent/src/core/tools/read.ts
grep -n "export function createReadTool" packages/agent/src/harness/tools/read.ts

# 扩展机制
grep -c "^	on(" packages/coding-agent/src/core/extensions/types.ts
grep -n "export interface ExtensionAPI" packages/coding-agent/src/core/extensions/types.ts
wc -l packages/coding-agent/src/core/extensions/*.ts
grep -n "AgentHarnessEventResultMap" packages/agent/src/harness/types.ts
grep -n "	subscribe(\|	on(" packages/agent/src/harness/agent-harness.ts

# 错误 / 重试 / 压缩
grep -n "class AgentHarnessError\|AgentHarnessErrorCode" packages/agent/src/harness/types.ts
grep -rn "class .*Error" packages/coding-agent/src/core/agent-session.ts        # 无输出
grep -n "isRetryableAssistantError\|_overflowRecoveryAttempted\|_checkCompaction\|abortRetry\|maxAttempts" packages/coding-agent/src/core/agent-session.ts
grep -n "retry\|Retry" packages/agent/src/harness/agent-harness.ts
grep -n "async compact(" packages/agent/src/harness/agent-harness.ts
grep -n "shouldCompact" packages/agent/src/harness/agent-harness.ts packages/coding-agent/src/core/agent-session.ts
grep -n "AgentHarnessPhase" packages/agent/src/harness/types.ts

# 事件模型
grep -n "export type AgentSessionEvent\|AgentSessionEventListener" packages/coding-agent/src/core/agent-session.ts
grep -n "export type AgentHarnessEvent\b\|AgentHarnessOwnEvent" packages/agent/src/harness/types.ts

# 为什么两套
grep -rni "agentsession" packages/agent/docs/ packages/agent/README.md packages/agent/CHANGELOG.md
wc -l packages/agent/docs/*.md packages/agent/README.md

# CLI 调用链
grep -n -A5 '"bin"' packages/coding-agent/package.json
cat -n packages/coding-agent/src/cli.ts
grep -n "export async function main\|InteractiveMode\|runPrintMode\|createAgentSessionFromServices\|createAgentSessionServices\|createAgentSessionRuntime" packages/coding-agent/src/main.ts
grep -n "export async function createAgentSessionServices\|export async function createAgentSessionFromServices" packages/coding-agent/src/core/agent-session-services.ts
grep -n "	async prompt(\|_runAgentPrompt\|this.agent.prompt" packages/coding-agent/src/core/agent-session.ts
grep -n "	async prompt(" packages/agent/src/agent.ts
grep -n "runtimeHost.prompt\|\.prompt(" packages/coding-agent/src/modes/interactive/interactive-mode.ts
grep -n "	async run(\|class InteractiveMode" packages/coding-agent/src/modes/interactive/interactive-mode.ts
grep -n "private async runWithLifecycle" packages/agent/src/agent.ts
```

---

## 最适合上 PPT 的 5 条硬事实

1. **pi 0.83.0 里有两个顶层编排类，共享同一个 792 行的循环函数。**
   `AgentSession`（`packages/coding-agent/src/core/agent-session.ts:303–3332`，类体 3030 行）经 `Agent`（`packages/agent/src/agent.ts:171–577`）在 `agent.ts:403` 调 `runAgentLoop`；`AgentHarness`（`packages/agent/src/harness/agent-harness.ts:173–1185`，类体 1013 行）在 `agent-harness.ts:658` **直接**调同一个 `runAgentLoop`（`packages/agent/src/agent-loop.ts:95`）。这一行就是两条路径的汇合点。

2. **SDK 路径 `AgentHarness` 在整个 monorepo 里的生产消费者是 0。**
   `grep -rn "\bAgentHarness\b" packages/*/src packages/*/*/src | grep -v "^packages/agent/src/harness/"` **无输出**；`new AgentHarness(` 在 src 里一次都没出现。它只被 `packages/agent/src/index.ts:6` 导出给外部。对比：`AgentSession` 有 22 个源文件、跨 4 个包引用，唯一实例化点 `packages/coding-agent/src/core/sdk.ts:376`。
   （这更正了 R10 的旧结论 —— evals 里的 "AgentHarness" 是 `createPiCodingAgentHarness` 的子串误判，evals 实际走的是 `AgentSession`。）

3. **「为什么两套」有白纸黑字的答案：harness 是排到 pi 2.0 的继任者。**
   `packages/agent/docs/models.md:793` —— "coding-agent does not use `AgentHarness` yet; `AgentSession` still drives the low-level `Agent` with a `streamFn`."
   `models.md:860` —— "AgentSession itself stays (**AgentHarness adoption is pi 2.0**)"
   `models.md:938` —— **未勾选**的 `- [ ] AgentSession -> AgentHarness;`
   佐证体量：harness 的两份 plan/design 文档 `harness.md`(2390行)+`harness-v2.md`(1827行) 加起来 **比 harness 实现本身还多 3.5 倍**。

4. **五项能力逐条分叉，同名不同义：**
   持久化 —— 产品同步 `appendFileSync`（`session-manager.ts:1040`）/ SDK 异步 + 可注入 `FileSystem`（`jsonl-store.ts:277`），后端 1 种 vs 3 种（JSONL/内存/SQLite），entry 类型 9 种 vs 11 种（多 `ActiveToolsChangeEntry`、`LeafEntry`）；
   工具 —— 7 个（`core/tools/index.ts:83`）vs 4 个（`harness/tools/index.ts`），且 SDK 版把 `cwd: string` 换成 `ExecutionEnv`（`harness/tools/read.ts:45,53`）；
   扩展 —— `ExtensionAPI` 33 个 `on()` 重载（`extensions/types.ts:1193`，扩展层共 3893 行、含 jiti 加载器）vs harness 22 个事件类型（`harness/types.ts:816`，8 项可改流程、14 项纯通知，无加载器）；
   错误 —— 产品抛裸 `Error`、有 turn 级指数退避重试 + overflow 一次自救（`agent-session.ts:2691, 2003`）vs SDK 的 `AgentHarnessError` 9 值 code（`harness/types.ts:246`）+ 重试只覆盖 `"compaction"|"branch_summary"`（`agent-harness.ts:276`）；
   事件 —— 产品 `Exclude<AgentEvent,{type:"agent_end"}>` **改写**内核事件（`agent-session.ts:140`）vs SDK `AgentEvent | AgentHarnessOwnEvent` **纯加法**（`harness/types.ts:764`）。

5. **自动压缩只存在于产品路径，SDK 路径一次都没调用判定式。**
   `grep -n "shouldCompact" packages/agent/src/harness/agent-harness.ts packages/coding-agent/src/core/agent-session.ts` → 只在 `agent-session.ts:2038` 命中，harness 零命中。SDK 侧只有显式 `compact()`（`agent-harness.ts:783`），且第一行是 `if (this.phase !== "idle") throw new AgentHarnessError("busy", "compact() requires idle harness")`（`:785`）。
   同理，「重试/压缩后自动续跑」的 `while` 在循环之外（`agent-session.ts:1065-1067`），所以两条路径的 `prompt()` 语义根本不同：产品路径一次 `prompt()` 可能触发 N 次 LLM 往返，SDK 路径的 `prompt()` 就是一次 `runAgentLoop`（`agent-harness.ts:679` 接住返回值并取最后一条 assistant 消息）。
