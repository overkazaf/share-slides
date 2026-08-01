# P02：agent 主循环逐行拆解

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `https://github.com/earendil-works/pi.git` | `git remote -v` |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95`（短 hash `583f153`） | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/agent/package.json:3` |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开确认。
> 行号会随上游提交漂移 —— PPT 上引用时**必须带短 hash `583f153`**。

---

## 0. 一句话结论

pi 的"agent 主循环"是 **792 行文件里的 121 行**（`runLoop`，`packages/agent/src/agent-loop.ts:155-275`），
是**双层 while**，有 **4 个判停点**、**0 个迭代次数上限**、**0 行重试代码**。
重试、压缩、持久化、UI 全部在循环**外面**。这是本篇最重要的结构判断。

---

## 1. 文件实测与入口定位

### 1.1 行数

```bash
$ wc -l packages/agent/src/agent-loop.ts packages/agent/src/agent.ts packages/agent/src/types.ts packages/agent/src/stream-fn.ts
     792 packages/agent/src/agent-loop.ts
     577 packages/agent/src/agent.ts
     437 packages/agent/src/types.ts
      20 packages/agent/src/stream-fn.ts
```

配套测试 `packages/agent/test/agent-loop.test.ts` **1489 行**、`packages/agent/test/agent.test.ts` **732 行** —— 测试代码是被测代码的 **1.6 倍**。

### 1.2 `agent-loop.ts` 的 4 个公开入口 + 1 个私有循环体

| 符号 | 行号 | 导出 | 干什么 |
|---|---|---|---|
| `agentLoop(prompts, context, config, signal, streamFn)` | `:31` | ✅ | 新 prompt 起一轮，返回 `EventStream` |
| `agentLoopContinue(context, config, signal, streamFn)` | `:64` | ✅ | 从现有 context 续跑（重试用），返回 `EventStream` |
| `runAgentLoop(...)` | `:95` | ✅ | 同 `agentLoop` 但用回调 `emit` 而非 stream，返回 `Promise<AgentMessage[]>` |
| `runAgentLoopContinue(...)` | `:120` | ✅ | 同上，续跑版 |
| **`runLoop(...)`** | **`:155`** | ❌ **私有** | **真正的循环体**，`:162` 到 `:275` |

两组入口的关系是 **stream 版包 promise 版**（`:40-51`、`:80-90`）：

```ts
// agent-loop.ts:38-53
const stream = createAgentStream();
void runAgentLoop(prompts, context, config, async (event) => { stream.push(event); }, signal, streamFn)
	.then((messages) => { stream.end(messages); });
return stream;
```

`createAgentStream()`（`:145-150`）把 `agent_end` 定义为流的终止事件：

```ts
// agent-loop.ts:145-150
return new EventStream<AgentEvent, AgentMessage[]>(
	(event: AgentEvent) => event.type === "agent_end",
	(event: AgentEvent) => (event.type === "agent_end" ? event.messages : []),
);
```

### 1.3 `agent-loop.ts` 的 792 行怎么分配（函数级地图）

| 行段 | 函数 | 职责 |
|---|---|---|
| `:31-150` | 4 个入口 + `createAgentStream` | 门面 |
| **`:155-275`** | **`runLoop`** | **双层 while，本篇主角** |
| `:281-372` | `streamAssistantResponse` | 一次 LLM 调用 + 流式事件转发 |
| `:381-406` | `failToolCallsFromTruncatedMessage` | 截断保护 |
| `:411-426` | `executeToolCalls` | 串/并行分派 |
| `:433-487` | `executeToolCallsSequential` | 串行执行 |
| `:489-554` | `executeToolCallsParallel` | 并行执行 |
| `:556-584` | 5 个内部类型 + `shouldTerminateToolBatch` | — |
| `:586-664` | `prepareToolCallArguments` / `prepareToolCall` | 参数校验 + 权限钩子 |
| `:666-707` | `executePreparedToolCall` | 真正调 `tool.execute` |
| `:709-754` | `finalizeExecutedToolCall` | `afterToolCall` 钩子 |
| `:756-792` | 4 个小工具函数 | 造错误结果 / 发事件 / 造 toolResult 消息 |

**循环体只占 121/792 ≈ 15%，其余 85% 全是工具执行与事件的细节。**

### 1.4 `agent.ts` 的角色：有状态包装层

`class Agent`（`packages/agent/src/agent.ts:171`）自己**不含任何 while**，它只做三件事：

- 持有 transcript（`_state.messages`，`:83-88` 用 getter/setter 强制拷贝）
- 提供 `steer()` / `followUp()` 两个队列（`:276-283`，队列类 `PendingMessageQueue` `:123`）
- 把队列 + 钩子打包成 `AgentLoopConfig` 喂给 `runAgentLoop`（`createLoopConfig`，`:434-469`）

调用点只有两处：`:403` `runAgentLoop(...)`、`:416` `runAgentLoopContinue(...)`。

---

## 2. 控制流：两层 while，各自的退出条件

### 2.1 骨架（`agent-loop.ts:170-274`，裁到 12 行）

```ts
// agent-loop.ts:170-207（节选）
while (true) {                                                  // :170 外层 = follow-up 层
	let hasMoreToolCalls = true;                                // :171
	while (hasMoreToolCalls || pendingMessages.length > 0) {    // :174 内层 = turn 层
		if (!firstTurn) await emit({ type: "turn_start" });     // :175-179
		/* :182-190 注入 pendingMessages（steering） */
		const message = await streamAssistantResponse(...);     // :193
		newMessages.push(message);                              // :194
		if (message.stopReason === "error" || message.stopReason === "aborted") {  // :196
			await emit({ type: "turn_end", message, toolResults: [] });            // :197
			await emit({ type: "agent_end", messages: newMessages });              // :198
			return;                                                                // :199 ← 判停 ①
		}
		const toolCalls = message.content.filter((c) => c.type === "toolCall");    // :203
```

外层收尾（`:262-274`）：

```ts
// agent-loop.ts:262-274
		// Agent would stop here. Check for follow-up messages.
		const followUpMessages = (await config.getFollowUpMessages?.()) || [];   // :263
		if (followUpMessages.length > 0) {
			pendingMessages = followUpMessages;                                 // :266
			continue;                                                           // :267 回到 :170
		}
		break;                                                                  // :271 ← 判停 ④
	}
	await emit({ type: "agent_end", messages: newMessages });                   // :274
```

### 2.2 层数与退出条件一览

| 层 | 位置 | 循环条件 | 退出条件 |
|---|---|---|---|
| **外层** | `:170` `while (true)` | 恒真 | `:271` `break` —— `getFollowUpMessages()` 返回空数组 |
| **内层** | `:174` `while (hasMoreToolCalls \|\| pendingMessages.length > 0)` | 还有工具调用 **或** 还有 steering 待注入 | 条件为假；或 `:199` / `:256` 提前 `return` |
| （非循环）第三层 | `:317` `for await (const event of response)` | 流式事件迭代 | `done` / `error` 事件里 `return`（`:346-359`） |
| （非循环）第四层 | `:444` / `:499` `for (const toolCall of toolCalls)` | 遍历本批工具调用 | 遍历完；或 `signal.aborted` 时 `break`（`:478`/`:516`/`:535`） |

> **注意**：真正的 `while` 只有两层。`for await` 和 `for` 都是有限遍历，不是"循环"语义上的第三第四层。PPT 上说"两层 while + 两层 for"最准确。

### 2.3 一次内层迭代干了什么（逐条对行号）

| # | 步骤 | 行号 |
|---|---|---|
| ① | 发 `turn_start`（首轮跳过，因为 `runAgentLoop:110` 已发过） | `:175-179` |
| ② | 注入 steering 消息：每条发 `message_start`+`message_end`，同时 push 进 `currentContext.messages` 与 `newMessages` | `:182-190` |
| ③ | 流式取 assistant 回复 | `:193`（实现 `:281`） |
| ④ | **判停 ①**：`stopReason ∈ {error, aborted}` → `turn_end` + `agent_end` + `return` | `:196-200` |
| ⑤ | 抽 toolCall | `:203` |
| ⑥ | **截断保护**：`stopReason === "length"` → 全批工具**不执行**、一律返回错误 | `:211-213` |
| ⑦ | 否则执行工具 | `:214` |
| ⑧ | `hasMoreToolCalls = !executedToolBatch.terminate` | `:216` |
| ⑨ | 结果同时 push 进 context 与 newMessages | `:218-221` |
| ⑩ | 发 `turn_end`（带 `{message, toolResults}`） | `:224` |
| ⑪ | `prepareNextTurn` 钩子：可换 context / model / reasoning，**下一轮生效** | `:226-245` |
| ⑫ | **判停 ②**：`shouldStopAfterTurn()` 返回 true → `agent_end` + `return` | `:247-257` |
| ⑬ | 重新拉 steering 队列 | `:259` |
| — | **判停 ③**：回到 `:174`，无工具调用且无 steering → 退内层 | `:174` |
| — | **判停 ④**：`getFollowUpMessages()` 为空 → `break` 外层 → `:274` 发 `agent_end` | `:263-271` |

### 2.4 关键细节：`hasMoreToolCalls` 的语义

`:206` 先置 `false`，只有 `toolCalls.length > 0` 时才在 `:216` 被重新赋值：

```ts
// agent-loop.ts:206, 216
hasMoreToolCalls = false;
…
hasMoreToolCalls = !executedToolBatch.terminate;
```

`terminate` 的判定极严（`:582-584`）——**批次里每一个** 工具结果都 `terminate === true` 才提前收：

```ts
// agent-loop.ts:582-584
function shouldTerminateToolBatch(finalizedCalls: FinalizedToolCallOutcome[]): boolean {
	return finalizedCalls.length > 0 && finalizedCalls.every((finalized) => finalized.result.terminate === true);
}
```

类型定义处的注释也写死了这条语义（`packages/agent/src/types.ts:365-368`）：

```ts
/**
 * Hint that the agent should stop after the current tool batch.
 * Early termination only happens when every finalized tool result in the batch sets this to true.
 */
terminate?: boolean;
```

### 2.5 **循环里没有迭代上限**

`runLoop`（`:155-275`）全文没有任何 `maxIterations` / `maxSteps` / 计数器。整个 `packages/agent/src` 也没有这类常量。
**停不下来的唯一保险是模型自己不再发 toolCall，加上宿主的 `shouldStopAfterTurn` 与用户 abort。**

---

## 3. 判停：模型说完了怎么判、工具结果怎么回灌、follow-up 从哪来

### 3.1 "模型说完了" = 这一条 assistant 消息里没有 `toolCall`

判定就是 `:203` 的一行 filter + `:207` 的 `if (toolCalls.length > 0)`。
没有 toolCall → `hasMoreToolCalls` 保持 `:206` 的 `false` → `:174` 条件为假 → 退内层。

**pi 不看 `stopReason === "stop"`，只看 content 里有没有 toolCall。** `stopReason` 只在三处被检查：
- `:196` `"error"` / `"aborted"` → 立即退出
- `:212` `"length"` → 截断保护
- 其余（包括 `"stop"` / `"toolUse"`）一视同仁

### 3.2 工具结果怎么回灌

三步，全在 `:211-221`：

```ts
// agent-loop.ts:211-221
const executedToolBatch =
	message.stopReason === "length"
		? await failToolCallsFromTruncatedMessage(toolCalls, emit)
		: await executeToolCalls(currentContext, message, config, signal, emit);
toolResults.push(...executedToolBatch.messages);
hasMoreToolCalls = !executedToolBatch.terminate;

for (const result of toolResults) {
	currentContext.messages.push(result);   // ← 回灌进"送给 LLM 的上下文"
	newMessages.push(result);               // ← 同时进"本轮新增消息"（给宿主持久化）
}
```

**双写是刻意的**：`currentContext.messages` 决定下一次 LLM 请求看到什么；`newMessages` 是 `agent_end` 事件的 payload（`:274`），宿主拿去落 session。

回灌的 `ToolResultMessage` 由 `createToolResultMessage`（`:773-787`）构造，有一处防御性归一化值得看：

```ts
// agent-loop.ts:778-780
// Untyped tools (JS extensions) can return results without content; normalize
// so the null never enters session history or provider payloads.
content: finalized.result.content ?? [],
```

### 3.3 follow-up 从哪来

`config.getFollowUpMessages?.()`（`:263`）。契约写在 `packages/agent/src/types.ts:241-252`：

> Called when the agent has no more tool calls and no steering messages. …
> **Contract: must not throw or reject. Return [] when no follow-up messages are available.**

实现方两处：
- 产品/SDK 通用：`packages/agent/src/agent.ts:467` `getFollowUpMessages: async () => this.followUpQueue.drain()`
- harness：`packages/agent/src/harness/agent-harness.ts:538`

队列的 drain 策略有两种模式（`agent.ts:139-152`）：

```ts
// agent.ts:139-152
drain(): AgentMessage[] {
	if (this.mode === "all") { const drained = this.messages.slice(); this.messages = []; return drained; }
	const first = this.messages[0];
	if (!first) return [];
	this.messages = this.messages.slice(1);
	return [first];      // "one-at-a-time"：一次只放一条
}
```

**默认是 `"one-at-a-time"`**（`agent.ts:224-225`）：

```ts
this.steeringQueue = new PendingMessageQueue(runtimeOptions.steeringMode ?? "one-at-a-time");
this.followUpQueue = new PendingMessageQueue(runtimeOptions.followUpMode ?? "one-at-a-time");
```

### 3.4 steering vs follow-up 的差别（一句话）

| | steering | follow-up |
|---|---|---|
| 拉取时机 | 循环启动时 `:167` + 每个 turn 结束后 `:259` | 内层循环退出后 `:263` |
| 语义 | **打断**：工作到一半插话 | **排队**：等它干完再说 |
| 效果 | 进 `pendingMessages`，下一次 LLM 请求前注入 | 进 `pendingMessages` 并 `continue` 外层，等于重开内层循环 |
| 关键点 | **不取消已发出的工具调用**（types.ts:233 明写 `Tool calls from the current assistant message are not skipped.`） | — |

---

## 4. abort / 取消

### 4.1 signal 的来源：`AbortController` 在 `Agent` 里，一次 run 一个

```ts
// agent.ts:476-481
const abortController = new AbortController();
let resolvePromise = () => {};
const promise = new Promise<void>((resolve) => { resolvePromise = resolve; });
this.activeRun = { promise, resolve: resolvePromise, abortController };
```

`abort()` 就一行（`agent.ts:312-314`）：

```ts
abort(): void { this.activeRun?.abortController.abort(); }
```

产品层入口（`packages/coding-agent/src/core/agent-session.ts:1542-1546`）：

```ts
async abort(): Promise<void> {
	this.abortRetry();      // ← 先掐掉正在 sleep 的重试退避
	this.agent.abort();
	await this.waitForIdle();
}
```

### 4.2 穿透到 provider

`runLoop(…, signal, …)` → `streamAssistantResponse(context, config, signal, …)`（`:193`）→

```ts
// agent-loop.ts:308-312
const response = await streamFunction(config.model, llmContext, {
	...config,
	apiKey: resolvedApiKey,
	signal,
});
```

provider 侧（以 Anthropic 为例，`packages/ai/src/api/anthropic-messages.ts`）：
- `:555` fetch 带 `...(options?.signal ? { signal: options.signal } : {})`
- `:573` SSE 迭代器也吃 signal：`iterateAnthropicEvents(response, options?.signal)`
- `:747-749` 循环结束前再查一次 `if (options?.signal?.aborted) throw new Error("Request was aborted")`
- `:766` **catch 里把 abort 转成消息状态而不是异常**：

```ts
// packages/ai/src/api/anthropic-messages.ts:765-768
output.stopReason = options?.signal?.aborted ? "aborted" : "error";
output.errorMessage = error instanceof Error ? error.message : JSON.stringify(error);
stream.push({ type: "error", reason: output.stopReason, error: output });
stream.end();
```

### 4.3 穿透到工具

`tool.execute` 的第三个形参就是 signal（`types.ts:389-394`），实际传参在 `agent-loop.ts:675-678`：

```ts
const result = await prepared.tool.execute(
	prepared.toolCall.id,
	prepared.args as never,
	signal,
	(partialResult) => { /* onUpdate */ },
);
```

循环内**另有 5 处显式 `signal?.aborted` 检查**：

| 位置 | 行号 | 动作 |
|---|---|---|
| 串行执行：每完成一个工具后 | `:478-480` | `break` 跳出批次 |
| 并行执行：immediate 分支入队后 | `:516-518` | `break` |
| 并行执行：闭包入队后 | `:535-537` | `break` |
| `prepareToolCall`：`beforeToolCall` 钩子**之后** | `:629-635` | 返回 `createErrorToolResult("Operation aborted")` |
| `prepareToolCall`：进入 prepared 之前 | `:644-650` | 同上 |

工具自身也可以再落一层，比如 bash 工具在 spawn 前查 `if (signal?.aborted)`（`packages/coding-agent/src/core/tools/bash.ts:86`）、abort 时杀整个进程树（`bash.ts:126` 注释 `Handle abort signal by killing the entire process tree.`）。

### 4.4 中断后状态怎么收尾

**核心设计：abort 不抛异常，走正常事件序列退出。**

1. provider 把 abort 变成 `stopReason: "aborted"` 的**完整 AssistantMessage**（含已生成的部分文本）
2. `EventStream.result()` **永不 reject**（`packages/ai/src/utils/event-stream.ts:64-66` 只 resolve；`AssistantMessageEventStream` `:69-83` 把 `error` 事件的 payload 当正常返回值）
3. `agent-loop.ts:196-200` 命中 → 发 `turn_end` + `agent_end` → `return`
4. `Agent.finishRun()`（`agent.ts:514-520`）清运行时状态：

```ts
private finishRun(): void {
	this._state.isStreaming = false;
	this._state.streamingMessage = undefined;
	this._state.pendingToolCalls = new Set<string>();
	this.activeRun?.resolve();
	this.activeRun = undefined;
}
```

5. `waitForIdle()`（`agent.ts:321-323`）返回的就是这个 run 的 promise，**在所有 `agent_end` 监听器 settle 之后才 resolve**（`processEvents` 的 `await listener(...)`，`agent.ts:573-575`）

> **上 PPT 的点**：pi 里"取消"不是抛 `AbortError` 让上层 catch，而是**把中断建模成一个正常的消息终态**。整条链上 `try/catch` 少了一大半，UI 也能直接把半截回复渲染出来。

---

## 5. 错误恢复

### 5.1 三类错误的处理路径完全不同

| 错误类型 | 表现形式 | 处理位置 | 循环内有重试吗 |
|---|---|---|---|
| provider 报错（限流/5xx/断流） | 返回 `stopReason: "error"` 的 AssistantMessage，**不抛** | `agent-loop.ts:196-200` 直接退出 | ❌ 无 |
| 工具抛异常 | `try/catch` 转成错误 toolResult | `agent-loop.ts:697-703` | ❌ 无 |
| 工具参数校验失败 / 工具不存在 | 转成 `immediate` 错误结果 | `agent-loop.ts:608-613`、`:657-663` | ❌ 无 |
| 输出被 token 上限截断 | 整批工具**不执行**，全部报错 | `agent-loop.ts:381-406` | ❌ 无（让模型自己重发） |
| `afterToolCall` 钩子抛异常 | 覆盖成错误结果 | `agent-loop.ts:743-746` | ❌ 无 |

**`agent-loop.ts` 全文 792 行里 "retry" 出现 0 次。**（`grep -n retry packages/agent/src/agent-loop.ts` 无输出）

### 5.2 工具异常：绝不让它冒泡

```ts
// agent-loop.ts:697-706
} catch (error) {
	acceptingUpdates = false;
	await Promise.all(updateEvents);
	return {
		result: createErrorToolResult(error instanceof Error ? error.message : String(error)),
		isError: true,
	};
} finally {
	acceptingUpdates = false;
}
```

`AgentTool.execute` 的文档反过来**要求**工具抛异常而不是自己编错误内容（`types.ts:388`）：

> `/** Execute the tool call. Throw on failure instead of encoding errors in content. */`

`acceptingUpdates` 这个 flag（`:672`、`:680`、`:694`、`:698`、`:705`）解决的是**工具 settle 之后还调 onUpdate** 的竞态——注释在 `types.ts:374-376`：

> The callback is scoped to the current `execute()` invocation. Calls made after the tool promise settles are ignored.

### 5.3 截断保护（`length` stop）—— 一个很少见但很对的细节

```ts
// agent-loop.ts:374-380（函数头注释）
 * Fail all tool calls from an assistant message that was truncated by the
 * output token limit. Streamed tool-call arguments are finalized with a
 * best-effort JSON salvage parser, so a truncated message can yield tool calls
 * whose arguments parse and validate but are silently incomplete. None of them
 * are safe to execute; report each as an error so the model can re-issue them.
```

返回给模型的文案（`:396`）：

> `Tool call "<name>" was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments.`

注意 `:405` 返回 `terminate: false` —— **循环继续**，模型有机会重发。

### 5.4 真正的重试在循环外面（产品路径）

**位置**：`packages/coding-agent/src/core/agent-session.ts`，机制是 **"跑完 → 看结果 → 重新 `continue()`"**：

```ts
// agent-session.ts:1061-1067
private async _runAgentPrompt(messages: AgentMessage | AgentMessage[]): Promise<void> {
	this._isAgentRunActive = true;
	try {
		await this.agent.prompt(messages);
		while (await this._handlePostAgentRun()) {
			await this.agent.continue();
		}
	} finally { … }
```

`_handlePostAgentRun()`（`:1074-1101`）的三级决策：

```ts
// agent-session.ts:1082-1100（节选）
if (this._isRetryableError(msg) && (await this._prepareRetry(msg))) return true;   // ① 重试
if (msg.stopReason === "error" && this._retryAttempt > 0) { /* 发 auto_retry_end 失败事件 */ }
if (await this._checkCompaction(msg)) return true;                                 // ② 压缩后重跑
// The agent loop drains both queues before emitting agent_end. Any messages
// here were queued by agent_end extension handlers and need a continuation.
return this.agent.hasQueuedMessages();                                             // ③ 扩展补了消息
```

重试参数（`packages/coding-agent/src/core/settings-manager.ts:818-824`）：

```ts
getRetrySettings(): { enabled: boolean; maxRetries: number; baseDelayMs: number } {
	return {
		enabled: this.getRetryEnabled(),
		maxRetries: this.settings.retry?.maxRetries ?? 3,      // 默认 3 次
		baseDelayMs: this.settings.retry?.baseDelayMs ?? 2000,  // 默认 2s
	};
}
```

退避是纯指数（`agent-session.ts:2691`）：`const delayMs = settings.baseDelayMs * 2 ** (this._retryAttempt - 1);` → **2s / 4s / 8s，无 jitter**（settings-manager.ts:32 的注释也这么写：`exponential backoff: 2s, 4s, 8s`）。

**重试前会把错误消息从 agent 内存态摘掉**（`agent-session.ts:2701-2704`）：

```ts
// Remove error message from agent state (keep in session for history)
const messages = this.agent.state.messages;
if (messages.length > 0 && messages[messages.length - 1].role === "assistant") {
	this.agent.state.messages = messages.slice(0, -1);
}
```

—— **session 文件里留着，送给 LLM 的上下文里删掉。** 这是"重试不污染上下文"的关键一招。

退避 sleep 是可中断的（`:2706-2711`），`abortRetry()`（`:2731-2733`）就是 abort 这个 controller。

**哪些错可重试**（`agent-session.ts:2631-2639`）：

```ts
/**
 * Check if an error is retryable (overloaded, rate limit, server errors).
 * Context overflow errors are NOT retryable (handled by compaction instead).
 */
private _isRetryableError(message: AssistantMessage): boolean {
	if (isContextOverflow(message, this.model?.contextWindow ?? 0)) return false;
	return isRetryableAssistantError(message);
}
```

计数器在**每条成功的 assistant 消息**上归零（`agent-session.ts:654-661`），不是每次 run 归零 —— 注释：`This prevents accumulation across multiple LLM calls within a turn`。

### 5.5 超时

| 层 | 值 | 位置 |
|---|---|---|
| HTTP idle 超时 | **300_000 ms（5 分钟）** | `packages/coding-agent/src/core/http-dispatcher.ts:4` `export const DEFAULT_HTTP_IDLE_TIMEOUT_MS = 300_000;` |
| provider 重试延迟上限 | `maxRetryDelayMs`，透传给 stream fn | `agent.ts:119/206/229/444` → `types.ts:179-181` |
| 工具超时 | **没有默认值**，由工具自己实现 | `bash.ts:42` schema 描述原文：`"Timeout in seconds (optional, no default timeout)"` |
| 循环层超时 | **不存在** | `agent-loop.ts` 无任何 timer |

bash 工具的超时是自己 `setTimeout` 打的（`bash.ts:110-121`），上限 `MAX_TIMEOUT_MS`（`bash.ts:34`）。

> **上 PPT 的点**：**主循环里一个 timer 都没有。** 超时全部下沉到 HTTP 层和工具层。

### 5.6 `Agent` 层的兜底 catch

如果配置回调（`convertToLlm` / `transformContext` / `shouldStopAfterTurn` …）真的抛了，`runLoop` 会直接把异常冒到 `Agent.runWithLifecycle`（`agent.ts:487-493`），由 `handleRunFailure`（`:496-512`）**伪造一条 assistant 消息**补齐事件序列：

```ts
// agent.ts:497-511（节选）
const failureMessage = {
	role: "assistant", content: [{ type: "text", text: "" }],
	…
	stopReason: aborted ? "aborted" : "error",
	errorMessage: error instanceof Error ? error.message : String(error),
	timestamp: Date.now(),
} satisfies AgentMessage;
await this.processEvents({ type: "message_start", message: failureMessage });
await this.processEvents({ type: "message_end", message: failureMessage });
await this.processEvents({ type: "turn_end", message: failureMessage, toolResults: [] });
await this.processEvents({ type: "agent_end", messages: [failureMessage] });
```

正因如此，`AgentLoopConfig` 里几乎每个回调的 JSDoc 都写着同一句硬约束（`types.ts:154-155`、`:182-183`、`:203`、`:215`、`:237`、`:250`）：

> **Contract: must not throw or reject.**

harness 路径同理，`agent-harness.ts:671-677` 用 `emitRunFailure` 兜，兜底失败还会包成 `AggregateError`。

---

## 6. 事件流

### 6.1 全部 9 种事件（唯一定义处：`packages/agent/src/types.ts:422-437`）

```ts
export type AgentEvent =
	| { type: "agent_start" }                                                          // :424
	| { type: "agent_end"; messages: AgentMessage[] }                                  // :425
	| { type: "turn_start" }                                                           // :427
	| { type: "turn_end"; message: AgentMessage; toolResults: ToolResultMessage[] }    // :428
	| { type: "message_start"; message: AgentMessage }                                 // :430
	| { type: "message_update"; message: AgentMessage; assistantMessageEvent: AssistantMessageEvent }  // :432
	| { type: "message_end"; message: AgentMessage }                                   // :433
	| { type: "tool_execution_start"; toolCallId: string; toolName: string; args: any }  // :435
	| { type: "tool_execution_update"; toolCallId: string; toolName: string; args: any; partialResult: any }  // :436
	| { type: "tool_execution_end"; toolCallId: string; toolName: string; result: any; isError: boolean };    // :437
```

**共 10 个成员**（`agent_start` / `agent_end` / `turn_start` / `turn_end` / `message_start` / `message_update` / `message_end` / `tool_execution_start` / `tool_execution_update` / `tool_execution_end`）。

### 6.2 每个事件的发射点（全部实测）

| 事件 | 发射位置 | 备注 |
|---|---|---|
| `agent_start` | `agent-loop.ts:109`、`:138` | **只在两个 `runAgentLoop*` 入口发，`runLoop` 内不发** |
| `turn_start` | `:110`、`:139`（首轮）、`:176`（后续轮） | `firstTurn` 标志避免重复 |
| `message_start` | `:112`（prompt）、`:184`（steering）、`:323`（流式开始）、`:355`/`:368`（无流式的兜底）、`:790`（toolResult） | **6 处** |
| `message_update` | `:338-342` | 仅 assistant 流式，携带 `assistantMessageEvent` **与全量快照 `message`** |
| `message_end` | `:113`、`:185`、`:357`、`:370`、`:791` | **5 处** |
| `tool_execution_start` | `:387`（截断分支）、`:445`（串行）、`:500`（并行） | **3 处** |
| `tool_execution_update` | `:683-689`（`executePreparedToolCall` 的 onUpdate 闭包内） | 唯一 |
| `tool_execution_end` | `emitToolExecutionEnd()` `:763`，被 `:400`/`:472`/`:514`/`:532` 调用 | **4 个调用点** |
| `turn_end` | `:197`（错误/中断）、`:224`（正常） | **2 处** |
| `agent_end` | `:198`（错误/中断）、`:255`（宿主判停）、`:274`（正常收尾） | **3 处** |

### 6.3 三个值得单独讲的事件设计

**(a) 增量事件自带全量快照**（`:335-342`）：

```ts
if (partialMessage) {
	partialMessage = event.partial;
	context.messages[context.messages.length - 1] = partialMessage;   // 整条替换，不是 append
	await emit({ type: "message_update", assistantMessageEvent: event, message: { ...partialMessage } });
}
```

→ 上层 UI **不需要自己维护累加缓冲区**，拿 `event.message` 直接渲染即可。

**(b) 并行执行时，两条时间线被刻意拆开**（`:489-548`）：
- `tool_execution_end` 在**闭包内部**发（`:532`），所以按**完成顺序**到达 → UI 实时
- tool-result **消息**在 `Promise.all` 之后按 `orderedFinalizedCalls` 遍历发（`:544-548`），按 **assistant 声明顺序** → 历史可重放

**(c) `agent_end` ≠ idle**（`types.ts:415-421` 与 `agent.ts:522-528` 两处注释都强调）：

> `agent_end` only means no further loop events will be emitted. The run is
> considered idle later, after all awaited listeners for `agent_end` finish
> and `finishRun()` clears runtime-owned state.

监听器是**串行 await** 的（`agent.ts:573-575`）：

```ts
for (const listener of this.listeners) {
	await listener(event, signal);
}
```

→ 一个慢监听器会**阻塞整个循环**。这是设计取舍（保证持久化顺序），不是 bug。

---

## 7. 与"教科书版 while 循环"的差异清单 ★本篇核心

教科书伪代码通常长这样：

```python
while True:
    resp = llm(messages)
    messages.append(resp)
    if not resp.tool_calls:
        break
    for tc in resp.tool_calls:
        messages.append(run_tool(tc))
```

**6 行。pi 的对应实现是 121 行 + 517 行支撑代码。** 多出来的东西逐条列：

| # | 多出来的东西 | 教科书里有吗 | pi 的实现位置 | 为什么非有不可 |
|---|---|---|---|---|
| 1 | **第二层 while（follow-up）** | ❌ | `agent-loop.ts:170`、`:263-268` | 用户在 agent 跑的时候又发了一条消息，不能丢；跑完得接着干 |
| 2 | **steering 队列（跑一半插话）** | ❌ | `:167`、`:182-190`、`:259` | 交互式 agent 的刚需；且**不取消已发出的工具调用**（types.ts:233） |
| 3 | **宿主判停钩子 `shouldStopAfterTurn`** | ❌ | `:247-257` | 让上层能在"上下文快满了"时优雅收尾。注：全仓**仅测试用到**（`test/agent-loop.test.ts:1142`），产品路径未用 |
| 4 | **`prepareNextTurn`：轮间热换 model / context / thinking level** | ❌ | `:226-245` | 用户在 agent 跑的中途 `/model` 切模型，下一轮就生效（产品实现见 `agent-session.ts:520-541`） |
| 5 | **`transformContext` 压缩挂载点** | ❌ | `:290-292` | 上下文压缩要在 `convertToLlm` 之前、在 AgentMessage 层面做 |
| 6 | **`convertToLlm`：内部消息模型 ≠ LLM 消息模型** | ❌ | `:295`，默认实现 `agent.ts:32-36` | pi 的 transcript 里有 bashExecution / compactionSummary / custom 等 LLM 看不懂的消息，必须过滤投影 |
| 7 | **每轮重新解析 API key** | ❌ | `:305-306` | 注释直说：`important for expiring tokens`。长跑工具阶段 OAuth token 会过期（types.ts:198-201 点名 GitHub Copilot） |
| 8 | **截断保护：`stopReason === "length"` 时整批工具不执行** | ❌ | `:211-213` → `:381-406` | 流式 tool-call 参数用 best-effort JSON 抢救解析，截断后**能通过 schema 校验但内容是残的**（`:376-378` 注释）——最阴的一类 bug |
| 9 | **`terminate` 的全票制** | ❌ | `:216`、`:582-584` | 一个工具想停，不能替整批做主 |
| 10 | **串/并行自动分派 + 单个工具可强制串行** | ❌ | `:419-425` | `edit`/`write` 这种有副作用的工具不能并发；靠 `executionMode: "sequential"` 一票否决整批 |
| 11 | **"UI 按完成顺序、历史按声明顺序"双时间线** | ❌ | `:532` vs `:544-548` | 并行执行时若历史也按完成顺序写，session 重放会和 assistant 的 toolCall 顺序对不上 |
| 12 | **AbortSignal 五处显式检查 + 穿透到 provider 和工具** | ❌ | `:478`/`:516`/`:535`/`:629`/`:644`；provider `anthropic-messages.ts:555,573,747` | Ctrl-C 必须在 100ms 内有反应，不能等当前工具跑完 |
| 13 | **abort/error 建模成消息终态，而非异常** | ❌ | `:196-200`；`EventStream.result()` 永不 reject（`event-stream.ts:64-66`） | 半截回复要能渲染、要能存进 session；异常会丢掉这些内容 |
| 14 | **`beforeToolCall` 权限钩子（可 block）** | ❌ | `:619-643` | 危险命令确认、沙箱、plan mode 全靠它 |
| 15 | **`afterToolCall` 结果改写钩子** | ❌ | `:720-747` | 结果脱敏、截断、注入额外上下文 |
| 16 | **`prepareArguments` 参数兼容 shim + schema 校验** | ❌ | `:586-598`、`:618` | 不同模型对同一 schema 的填法有偏差，得先归一化再校验 |
| 17 | **工具异常 100% 被 catch 成 toolResult** | ❌（教科书直接崩） | `:697-703` | 一个工具挂了不能让整个会话死 |
| 18 | **`onUpdate` 流式工具进度 + settle 后丢弃的竞态保护** | ❌ | `:671-695`（`acceptingUpdates`） | 长跑 bash 要实时出日志；同时不能让迟到的 update 破坏状态 |
| 19 | **`content ?? []` 归一化** | ❌ | `:780` | JS 扩展写的工具可能返回 `undefined` content，null 不能进 session 和 provider payload |
| 20 | **10 个生命周期事件 + 增量事件自带全量快照** | ❌ | `types.ts:422-437`；`:338-342` | 没有事件流就没有 TUI |
| 21 | **`newMessages` 与 `context.messages` 双写** | ❌ | `:218-221` 等 | 一个喂模型，一个喂持久化，两者生命周期不同 |
| 22 | **循环外的重试（3 次、2/4/8s 指数退避、可中断、重试前删错误消息）** | ❌ | `agent-session.ts:1064-1066`、`:2676-2726` | 限流/5xx 是常态；但**刻意不放进循环** |
| 23 | **循环外的压缩重跑** | ❌ | `agent-session.ts:1096-1098` | 溢出后压缩再 `continue()`，同样不进循环 |
| 24 | **`agent_end` 之后监听器 settle 才算 idle** | ❌ | `agent.ts:514-520`、`:573-575`、`types.ts:415-421` | session 落盘必须在"用户能发下一条"之前完成 |
| 25 | **没有迭代上限、没有 timer** | —— | `runLoop` 全文 | 反向差异：教科书常加 `max_steps`，pi **刻意不加**，把决定权交给宿主的 `shouldStopAfterTurn` 和用户的 Ctrl-C |

### 7.1 一句话总结这 25 条

> 教科书循环解决的是"怎么把工具结果喂回去"；
> **真实产品循环 90% 的代码在解决"跑到一半，世界变了"**——用户插话、token 过期、模型切换、上下文满了、用户按 Ctrl-C、工具炸了、输出被截断。

### 7.2 分层落点（这张图最适合上 PPT）

```
┌─ AgentSession（coding-agent）───────────────────────────────┐
│  重试(3次/2·4·8s) · 压缩 · session 落盘 · 扩展 33 钩子       │  ← 循环外
│  while (await _handlePostAgentRun()) await agent.continue() │     agent-session.ts:1064
├─ Agent（agent.ts:171）─────────────────────────────────────┤
│  transcript · steering/followUp 队列 · AbortController      │  ← 有状态包装
│  · 事件监听器串行 await · handleRunFailure 兜底              │     agent.ts:471-520
├─ runLoop（agent-loop.ts:155-275）★ 121 行 ─────────────────┤
│  while(true) { while(hasMoreToolCalls || pending) { … } }   │  ← 纯逻辑，无 IO 无 timer
├─ 工具执行（agent-loop.ts:381-754）─────────────────────────┤
│  串/并行 · 校验 · before/after 钩子 · 异常吞掉 · 事件        │
├─ provider（packages/ai）───────────────────────────────────┤
│  fetch(signal) · SSE · error/abort → stopReason，不抛异常   │
└────────────────────────────────────────────────────────────┘
```

---

## 8. 待核实

1. **`shouldStopAfterTurn` 是否有生产使用者**：`grep -rn "shouldStopAfterTurn" --include="*.ts" packages/` 只命中 `agent-loop.ts:248`、`types.ts:120/217/231` 和测试 `agent-loop.test.ts:1104/1142`。**产品路径与 harness 均未设置该回调**。但不能排除某个 example 扩展间接设置，未逐一排查 79 个 example。
2. **`getSteeringMessages` 在 `runLoop:167` 的首次调用**对 `Agent` 而言会被 `skipInitialSteeringPoll`（`agent.ts:435`、`:461-464`）跳过一次——这个 flag 只在 `continue()` 走 steering 分支时置位（`agent.ts:363`）。具体交互场景（steer 后立即 continue）未做端到端验证。
3. **`maxRetryDelayMs` 的实际生效点**：在 `agent.ts:444` 透传进 `AgentLoopConfig`，`types.ts:179-181` 说明是"服务端要求的等待过长时抛错交由上层处理"，但未逐个 provider 确认其实现。
4. **harness 路径的 abort 收尾**：`agent-harness.ts:661-686` 有 `emitRunFailure` + `AggregateError` 包装，未展开细读，本篇 abort 一节以产品路径为准。
5. `packages/agent/src/proxy.ts`（`:70`、`:112` 出现 `maxRetryDelayMs`）未纳入本次取证范围。

---

## 9. 最适合上 PPT 的 5 条硬事实

1. **真正的主循环是 121 行，占 792 行文件的 15%。** `runLoop()` 在 `packages/agent/src/agent-loop.ts:155-275`，是私有函数；4 个公开入口（`agentLoop:31` / `agentLoopContinue:64` / `runAgentLoop:95` / `runAgentLoopContinue:120`）全是门面，前两个只是把后两个包成 `EventStream`。

2. **双层 while、4 个判停点，且没有任何迭代上限。** 外层 `:170` 管 follow-up（退出条件：`getFollowUpMessages()` 返回空，`:263-271`），内层 `:174` 管 tool-call + steering。四个判停：① `stopReason ∈ {error, aborted}`（`:196`）② 宿主 `shouldStopAfterTurn`（`:247`）③ 无工具无 steering（`:174`）④ 无 follow-up（`:271`）。`runLoop` 全文没有 `maxIterations`，也没有一个 timer。

3. **"模型说完了"的判定不看 `stopReason`，只看 `message.content` 里还有没有 `toolCall`**（`:203` + `:206-207`）。`stopReason` 只被检查三次：`error`/`aborted` 退出、`length` 触发截断保护。截断保护（`:211-213` → `:381-406`）会让整批工具**一个都不执行**，理由写在注释里：流式参数用 best-effort JSON 抢救解析，截断后能通过 schema 校验但内容是残的。

4. **abort 不抛异常，被建模成消息终态。** signal 从入口一路传到 `streamFunction(..., { signal })`（`:308-312`）和 `tool.execute(..., signal, ...)`（`:675-678`），循环内另有 **5 处**显式 `signal?.aborted` 检查（`:478`/`:516`/`:535`/`:629`/`:644`）。provider 在 catch 里把 abort 写成 `stopReason: "aborted"` 的完整消息（`packages/ai/src/api/anthropic-messages.ts:766`），`EventStream.result()` 永不 reject（`packages/ai/src/utils/event-stream.ts:64-66`）——所以半截回复能渲染、能存盘。

5. **循环里 0 行重试代码；重试在循环外，靠"跑完再 `continue()`"实现。** `grep retry packages/agent/src/agent-loop.ts` 无输出。真正的重试是 `agent-session.ts:1064-1066` 的 `while (await this._handlePostAgentRun()) await this.agent.continue();`，默认 **3 次、2s/4s/8s 纯指数退避无 jitter**（`settings-manager.ts:821-822`），退避 sleep 可被 `abortRetry()` 中断，且**重试前会把错误消息从送 LLM 的上下文里删掉、但保留在 session 文件中**（`agent-session.ts:2701-2704`）。
