# R10：pi-mono 代码级硬事实取证

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `https://github.com/badlogic/pi-mono.git` | `git remote -v` |
> | commit | `4488ad55c18f07ae89a489096c90de8667b3adfb` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 03:00:02 +0300 | `git log -1 --date=iso` |
> | commit 标题 | `Merge pull request #7410 from earendil-works/fix/sqlite-session-linear-time` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/agent/package.json:3`、`packages/coding-agent/package.json:3` |
> | 本地路径 | `/Users/nongjiawu/playground/research/pi/pi-mono` | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开验证。
> 行号会随上游提交漂移 —— PPT 上引用时**必须带 commit 短 hash `4488ad5`**。

---

## 0. 一个必须先讲清楚的结构事实：pi 里有**两套**agent 编排层

这是本次取证最重要的发现，也是最容易讲错的地方。

| | **产品路径（`pi` CLI 实际跑的）** | **SDK 路径（AgentHarness）** |
|---|---|---|
| 顶层类 | `AgentSession`（`packages/coding-agent/src/core/agent-session.ts:303`） | `AgentHarness`（`packages/agent/src/harness/agent-harness.ts:173`） |
| 依赖的循环包装 | `Agent`（`packages/agent/src/agent.ts:171`） | 无，**直接调** `runAgentLoop` |
| Session 持久化 | `packages/coding-agent/src/core/session-manager.ts`（同步 `appendFileSync`） | `packages/agent/src/harness/session/jsonl-store.ts`（异步 + `ExecutionEnv` 抽象） |
| 内置工具 | `packages/coding-agent/src/core/tools/`（7 个） | `packages/agent/src/harness/tools/`（4 个） |
| 扩展机制 | `ExtensionAPI`（33 个 `on()` 钩子） | `AgentHarness` hook（22 项结果映射） |
| 谁在用 | `pi` 二进制 | `packages/evals`（`src/pi-harness.ts`）；`packages/protocol/src/schemas.ts:37` 只是对齐 phase 词汇 |

**验证方式**：

```bash
$ grep -rn "AgentHarness" packages/coding-agent/src/ packages/server/src/ packages/client/src/
# （无输出）
$ grep -rln "AgentHarness" packages/*/src packages/*/*/src
packages/agent/src/harness/{types,agent-harness,tools/*}.ts
packages/evals/src/{extensions.eval,pi-harness,smoke.eval}.ts
packages/protocol/src/schemas.ts
```

**两条路径共享同一个底层内核** `packages/agent/src/agent-loop.ts`。所以下面第 1 节（主循环）对两者都成立，第 2/3/4/5/6/7 节我**同时给出两套的证据**，PPT 上建议只讲产品路径，把 harness 作为"同一内核的第二种封装"来讲第 9 节。

---

## 1. Agent 主循环

### 1.1 位置

- 文件：`packages/agent/src/agent-loop.ts`（**792 行**，`wc -l` 实测）
- 公开入口：`agentLoop()` `:31`、`agentLoopContinue()` `:64`、`runAgentLoop()` `:95`、`runAgentLoopContinue()` `:120`
- **真正的循环体**：`runLoop()` `:155`（私有）

### 1.2 控制流：双层 while

`agent-loop.ts:170-275`（关键片段，已裁到 10 行内）：

```ts
while (true) {                                            // :170 外层：follow-up
  let hasMoreToolCalls = true;
  while (hasMoreToolCalls || pendingMessages.length > 0) {   // :174 内层：tool-call + steering
    if (!firstTurn) await emit({ type: "turn_start" });      // :176
    /* 注入 pendingMessages → context.messages + newMessages */  // :182-190
    const message = await streamAssistantResponse(...);      // :193
    if (message.stopReason === "error" || message.stopReason === "aborted") {  // :196
      await emit({ type: "turn_end", message, toolResults: [] });
      await emit({ type: "agent_end", messages: newMessages });
      return;                                                // :199 —— 唯一的 abort 出口
    }
```

一次内层迭代做的事，逐条对应行号：

| 步骤 | 行号 | 说明 |
|---|---|---|
| ① `turn_start` | `:176` | 首轮不发（`firstTurn` 已在 `runAgentLoop:110` 发过） |
| ② 注入 steering 消息 | `:182-190` | 每条发 `message_start`+`message_end`，同时 push 进 `currentContext.messages` 与 `newMessages` |
| ③ 流式取 assistant 回复 | `:193` → 实现 `:281` | 见 1.3 |
| ④ **判停 A：错误/中断** | `:196-200` | `stopReason ∈ {error, aborted}` → 直接 `agent_end` 返回 |
| ⑤ 取 toolCall | `:203` | `message.content.filter(c => c.type === "toolCall")` |
| ⑥ **截断保护** | `:211-213` | `stopReason === "length"` → 走 `failToolCallsFromTruncatedMessage()`（`:381`），**全部工具调用返回错误而不执行** |
| ⑦ 执行工具 | `:214` | `executeToolCalls()`（`:411`） |
| ⑧ 结果回填 | `:215-221` | toolResults 同时 push 进 context 与 newMessages |
| ⑨ `turn_end` | `:224` | 带 `{message, toolResults}` |
| ⑩ `prepareNextTurn` 钩子 | `:232-245` | 可换 `context` / `model` / `reasoning`（下一轮生效） |
| ⑪ **判停 B：宿主决策** | `:247-257` | `config.shouldStopAfterTurn()` 返回 true → `agent_end` 返回 |
| ⑫ 拉新 steering | `:259` | `config.getSteeringMessages()` |
| **判停 C：无工具无消息** | `:174` | `hasMoreToolCalls === false && pendingMessages.length === 0` → 退出内层 |
| **判停 D：无 follow-up** | `:263-271` | `getFollowUpMessages()` 为空 → `break` 外层 → `:274` 发 `agent_end` |

即 **4 个判停点**：错误/中断、宿主 `shouldStopAfterTurn`、内层条件（无更多工具调用）、外层 follow-up 为空。

`hasMoreToolCalls` 的赋值（`:216`）：

```ts
hasMoreToolCalls = !executedToolBatch.terminate;
```

`terminate` 的语义极严（`agent-loop.ts:582-584`）——**批次中每一个** tool result 都 `terminate === true` 才提前结束：

```ts
function shouldTerminateToolBatch(finalizedCalls: FinalizedToolCallOutcome[]): boolean {
	return finalizedCalls.length > 0 && finalizedCalls.every((finalized) => finalized.result.terminate === true);
}
```

### 1.3 一次 LLM 调用内部（`streamAssistantResponse`, `:281`）

```ts
let messages = context.messages;
if (config.transformContext) messages = await config.transformContext(messages, signal);  // :290-292 压缩挂载点
const llmMessages = await config.convertToLlm(messages);                                   // :295 AgentMessage→Message
const llmContext: Context = { systemPrompt: context.systemPrompt, messages: llmMessages, tools: context.tools };  // :298
const resolvedApiKey = (config.getApiKey ? await config.getApiKey(config.model.provider) : undefined) || config.apiKey;  // :305 每轮重解析（OAuth 过期）
const response = await streamFunction(config.model, llmContext, { ...config, apiKey: resolvedApiKey, signal });  // :308
```

事件消费（`:317-361`）：`start` → push partial 到 context（`:321`）；9 种 `*_start/_delta/_end`（`:326-334`）→ **整条替换** `context.messages[last] = event.partial`（`:337`）；`done`/`error`（`:346`）→ `await response.result()` 取终值覆盖并 `return`。

> 上 PPT 的点：**增量事件同时携带全量快照 `event.partial`，上层不需要自己做累加**。

### 1.4 abort 的三层落点（全部实测）

1. **信号透传**：`signal` 从 `agentLoop(prompts, context, config, signal, streamFn)` 一路传到 `streamFunction(..., { signal })`（`:311`）
2. **循环层**：provider 返回 `stopReason: "aborted"` 的完整消息（含已生成的部分内容）→ `:196-200` 走 `turn_end` + `agent_end` 正常退出，**不抛异常**
3. **工具层**（3 处显式检查）：
   - 串行执行每完成一个工具后 `if (signal?.aborted) break;`（`:478-480`）
   - 并行执行入队时 `if (signal?.aborted) break;`（`:516-518`、`:535-537`）
   - **准备阶段** `prepareToolCall` 在 `beforeToolCall` 钩子前后各查一次（`:629-635`、`:644-650`），命中就返回 `createErrorToolResult("Operation aborted")`

产品层触发（`packages/coding-agent/src/core/agent-session.ts:1542-1546`）：

```ts
async abort(): Promise<void> {
	this.abortRetry();
	this.agent.abort();
	await this.waitForIdle();
}
```

`Agent.abort()` = `this.activeRun?.abortController.abort()`（`packages/agent/src/agent.ts:312-314`）。

### 1.5 工具执行：串/并行判定与保序

`executeToolCalls`（`agent-loop.ts:411-426`）：

```ts
const hasSequentialToolCall = toolCalls.some(
	(tc) => currentContext.tools?.find((t) => t.name === tc.name)?.executionMode === "sequential",
);
if (config.toolExecution === "sequential" || hasSequentialToolCall) {
	return executeToolCallsSequential(...);   // :433
}
return executeToolCallsParallel(...);        // :489
```

**并行路径的关键设计**（`:489-554`）：`prepareToolCall`（含参数校验 + `beforeToolCall` 权限钩子）在 for 循环里**串行**跑完（`:507`），只有 `execute` 被包成闭包丢进 `Promise.all`（`:522-534`、`:540-542`）。因此：

- `tool_execution_end` 事件按**完成顺序**发（在闭包内 `:532`）→ UI 实时
- tool-result **消息**按 assistant 原始顺序发（`:544-548` 遍历 `orderedFinalizedCalls`）→ 历史可重放

> 上 PPT 的点：**"UI 按完成顺序、历史按声明顺序"是同一个 for 循环里刻意拆开的两条时间线。**

---

## 2. 工具定义与注册

### 2.1 完整定义结构（产品路径）

`packages/coding-agent/src/core/extensions/types.ts:449-498`，`ToolDefinition` 共 **12 个字段**：

```ts
export interface ToolDefinition<TParams extends TSchema = TSchema, TDetails = unknown, TState = any> {
	name: string;                    // :451  LLM 看到的名字
	label: string;                   // :453  UI 显示名
	description: string;             // :455  给 LLM 的描述
	promptSnippet?: string;          // :457  ★ 决定是否出现在 system prompt "Available tools"
	promptGuidelines?: string[];     // :459  ★ 追加到 "Guidelines" 段
	parameters: TParams;             // :461  TypeBox schema
	constrainedSampling?: false | ConstrainedSamplingConfig;  // :463
	renderShell?: "default" | "self";                          // :465
	prepareArguments?: (args: unknown) => Static<TParams>;     // :468  校验前的兼容 shim
	executionMode?: ToolExecutionMode;                         // :477  "sequential" | "parallel"
	execute(toolCallId, params, signal, onUpdate, ctx): Promise<AgentToolResult<TDetails>>;  // :480
	renderCall?(...): Component;  renderResult?(...): Component;                             // :489/:492
}
```

**一个真实的完整实例** —— `read` 工具（`packages/coding-agent/src/core/tools/read.ts:203-215`）：

```ts
export function createReadToolDefinition(cwd, options?): ToolDefinition<typeof readSchema, ReadToolDetails | undefined> {
	return {
		name: "read",
		label: "read",
		description: `Read the contents of a file. Supports text files and images (jpg, png, gif, webp, bmp). …
		              For text files, output is truncated to ${DEFAULT_MAX_LINES} lines or ${DEFAULT_MAX_BYTES/1024}KB …`,
		promptSnippet: "Read file contents",
		promptGuidelines: ["Use read to examine files instead of cat or sed."],
		parameters: readSchema,   // Type.Object({ path, offset?, limit? })
		async execute(_toolCallId, { path, offset, limit }, signal, _onUpdate, ctx) { /* … */ },
```

schema 本体（`read.ts` 顶部，与 harness 版 `packages/agent/src/harness/tools/read.ts:16-20` 完全一致）：

```ts
const readSchema = Type.Object({
	path:   Type.String({ description: "Path to the file to read (relative or absolute)" }),
	offset: Type.Optional(Type.Number({ description: "Line number to start reading from (1-indexed)" })),
	limit:  Type.Optional(Type.Number({ description: "Maximum number of lines to read" })),
});
```

**全仓用 TypeBox，无 Zod**（`import { type Static, Type } from "typebox"`）。

### 2.2 内置工具清单：**7 个**（唯一权威定义）

`packages/coding-agent/src/core/tools/index.ts:83-84`：

```ts
export type ToolName = "read" | "bash" | "edit" | "write" | "grep" | "find" | "ls";
export const allToolNames: Set<ToolName> = new Set(["read", "bash", "edit", "write", "grep", "find", "ls"]);
```

**但默认只激活 4 个**（`packages/coding-agent/src/core/agent-session.ts:2592-2594`）：

```ts
const defaultActiveToolNames = this._baseToolsOverride
	? Object.keys(this._baseToolsOverride)
	: ["read", "bash", "edit", "write"];
```

即 `grep/find/ls` 已实现但默认不注入模型，模型走 `bash` 调 `rg`/`fd`。

| 工具 | 定义工厂位置 | 关键参数 |
|---|---|---|
| `read` | `core/tools/read.ts:203` | `path` / `offset?` / `limit?` |
| `bash` | `core/tools/bash.ts`（`createBashToolDefinition`） | `command` / `timeout?`，schema 描述明写 `"Timeout in seconds (optional, no default timeout)"`（`bash.ts:42`） |
| `edit` | `core/tools/edit.ts` | `path` / `edits[]` |
| `write` | `core/tools/write.ts` | `path` / `content` |
| `grep` | `core/tools/grep.ts` | ripgrep 后端 |
| `find` | `core/tools/find.ts` | fd 后端 |
| `ls` | `core/tools/ls.ts` | — |

**SDK 路径（harness）只有 4 个**（`packages/agent/src/harness/tools/index.ts:1-23` 导出：`createBashTool` / `createEditTool` / `createReadTool` / `createWriteTool`）。

**没有**：`task` / `subagent` / `todo` / `web_fetch` / `web_search` / MCP 工具（见第 8 节）。

### 2.3 注册链路

`createToolDefinition(name, cwd, opts)`（`core/tools/index.ts:96-115`）是一个 7 分支 switch；`createAllToolDefinitions`（`:156`）产出 `Record<ToolName, ToolDef>`；`AgentSession._buildRuntime` 在 `agent-session.ts:2563` 调用它，随后 `_refreshToolRegistry`（`:2596`）合并扩展工具。扩展侧注册入口是 `pi.registerTool(tool: ToolDefinition)`（`core/extensions/types.ts` ExtensionAPI 内，见第 7 节）。

---

## 3. System prompt 组装顺序

### 3.1 入口函数

**纯函数**：`buildSystemPrompt(options: BuildSystemPromptOptions)` —— `packages/coding-agent/src/core/system-prompt.ts:28`（整个文件只有 **163 行**）。

**调用方**：`AgentSession._rebuildSystemPrompt(toolNames)` —— `packages/coding-agent/src/core/agent-session.ts:1021`，在两处被触发：`:939`（构造/reload）与 `:2275`（工具集变化时）。

`_rebuildSystemPrompt` 干的事（`agent-session.ts:1022-1054`）：

```ts
const validToolNames = toolNames.filter((name) => this._toolRegistry.has(name));   // :1022
for (const name of validToolNames) {
	const snippet = this._toolPromptSnippets.get(name); if (snippet) toolSnippets[name] = snippet;   // :1026-1029
	const toolGuidelines = this._toolPromptGuidelines.get(name); if (toolGuidelines) promptGuidelines.push(...toolGuidelines);
}
this._baseSystemPromptOptions = { cwd, skills: loadedSkills, contextFiles: loadedContextFiles,
	customPrompt: loaderSystemPrompt, appendSystemPrompt, selectedTools: validToolNames, toolSnippets, promptGuidelines };  // :1044-1053
return buildSystemPrompt(this._baseSystemPromptOptions);   // :1054
```

### 3.2 拼装顺序（默认模板分支，`system-prompt.ts:121-159`）

| # | 段 | 行号 | 说明 |
|---|---|---|---|
| 1 | `"You are an expert coding assistant operating inside pi, a coding agent harness. …"` | `:121` | 固定开头，**"harness" 一词出现在 pi 自己的 system prompt 里** |
| 2 | `Available tools:` + 列表 | `:123-124` | ★ 只列 **提供了 `promptSnippet` 的工具**，否则整段是 `"(none)"` |
| 3 | `"In addition to the tools above, you may have access to other custom tools…"` | `:126` | 为扩展工具留口 |
| 4 | `Guidelines:` + 列表 | `:128-129` | 见 3.3 |
| 5 | `"Pi documentation (read only when the user asks about pi itself…)"` | `:131-138` | README / docs / examples 的**绝对路径** |
| 6 | `appendSystemPrompt` | `:140-142` | 来自 `.pi/APPEND_SYSTEM.md` 或 `--append-system-prompt` |
| 7 | `<project_context>` … `<project_instructions path="…">` … | `:144-152` | context files（AGENTS.md / CLAUDE.md） |
| 8 | `formatSkillsForPrompt(skills)` | `:154-157` | ★ **条件：`hasRead && skills.length > 0`** |
| 9 | `"Current working directory: <cwd>"` | `:159` | 收尾 |

`customPrompt`（`.pi/SYSTEM.md` 或 `--system-prompt`）分支（`:46-72`）**跳过 1~5**，只保留 `custom + append + project_context + skills + cwd`。

### 3.3 两个可上 PPT 的锐利细节

**(a) 工具是否出现在提示里，由 `promptSnippet` 决定，不是由是否注册决定**（`system-prompt.ts:80-84`）：

```ts
// A tool appears in Available tools only when the caller provides a one-line snippet.
const tools = selectedTools || ["read", "bash", "edit", "write"];
const visibleTools = tools.filter((name) => !!toolSnippets?.[name]);
const toolsList = visibleTools.length > 0 ? visibleTools.map((n) => `- ${n}: ${toolSnippets![n]}`).join("\n") : "(none)";
```

**(b) Guidelines 是条件生成的**（`:97-118`）：

```ts
if (hasBash && !hasGrep && !hasFind && !hasLs) addGuideline("Use bash for file operations like ls, rg, find");
for (const guideline of promptGuidelines ?? []) { ... }        // 各工具贡献，Set 去重
addGuideline("Be concise in your responses");                   // :116 恒有
addGuideline("Show file paths clearly when working with files");// :117 恒有
```

### 3.4 Context files 的发现顺序（`packages/coding-agent/src/core/resource-loader.ts:118-156`）

```ts
const globalContext = loadContextFileFromDir(resolvedAgentDir);   // :128 ~/.pi/agent/ 先 push
if (globalContext) { contextFiles.push(globalContext); ... }
let currentDir = resolvedCwd;
while (true) {
	const contextFile = loadContextFileFromDir(currentDir);
	if (contextFile && !isShadowed && !seenPaths.has(contextFile.path)) ancestorContextFiles.unshift(contextFile);  // :144 unshift
	const parentDir = dirname(currentDir); if (parentDir === currentDir) break; currentDir = parentDir;
}
contextFiles.push(...ancestorContextFiles);   // :153 → 最终顺序：global, 最外层祖先 … cwd
```

每目录候选顺序（`resource-loader.ts:71`）：`["AGENTS.md", "AGENTS.MD", "CLAUDE.md", "CLAUDE.MD"]`，**命中即止**。

`findShadowedContextFile`（`:100-116`）处理 git worktree 嵌套时主仓库那份 AGENTS.md 被重复加载的问题——注释里连 macOS `/tmp -> /private/tmp` symlink 和 bare 布局 `proj/.bare + proj/main` 都点名了。

`SYSTEM.md` / `APPEND_SYSTEM.md` 发现顺序（`resource-loader.ts:1022-1045`）：`<cwd>/.pi/SYSTEM.md`（需 trust）→ `~/.pi/agent/SYSTEM.md`。

### 3.5 SDK 路径对照

`AgentHarness` 侧没有默认模板，`systemPrompt` 是**调用方传入的字符串或工厂函数**（`agent-harness.ts:405-416`）：

```ts
let systemPrompt = "You are a helpful assistant.";      // :405 兜底
if (typeof this.systemPrompt === "string") systemPrompt = this.systemPrompt;
else if (this.systemPrompt) systemPrompt = await this.systemPrompt({ session, model, thinkingLevel, activeTools, resources });
```

harness 只提供 skills 片段格式化：`formatSkillsForSystemPrompt`（`packages/agent/src/harness/system-prompt.ts:3`，整文件 **34 行**）。

---

## 4. Skill 加载机制（progressive disclosure 的代码级证据）

### 4.1 目录发现

| 来源 | 代码位置 |
|---|---|
| `~/.pi/agent/skills`（user） | `core/skills.ts:430` `addSkills(loadSkillsFromDirInternal(join(resolvedAgentDir, "skills"), "user", true))` |
| `<cwd>/.pi/skills`（project） | `core/skills.ts:431` `resolve(resolvedCwd, CONFIG_DIR_NAME, "skills")` |
| `~/.agents/skills` | `core/package-manager.ts:2323` `join(getHomeDir(), ".agents", "skills")` |
| **cwd 祖先链上的 `.agents/skills`** | `core/package-manager.ts:435-453` `collectAncestorAgentsSkillDirs()` —— **到 git repo root 截断** |
| 包内 `skills/` | `core/package-manager.ts:2320`（`skills: join(globalBaseDir, "skills")` 等） |
| CLI `--skill <path>` / settings | `core/skills.ts:456-479`（`for (const rawPath of skillPaths)`） |

祖先链截断逻辑（`package-manager.ts:435-453`）：

```ts
function collectAncestorAgentsSkillDirs(startDir: string): string[] {
	const gitRepoRoot = findGitRepoRoot(resolvedStartDir);
	let dir = resolvedStartDir;
	while (true) {
		skillDirs.push(join(dir, ".agents", "skills"));
		if (gitRepoRoot && dir === gitRepoRoot) break;      // ★ git root 截断
		const parent = dirname(dir); if (parent === dir) break; dir = parent;
	}
```

且**祖先链的 `.agents/skills` 受 trust 门禁**（`package-manager.ts:2325-2328`）：

```ts
const projectTrusted = this.settingsManager.isProjectTrusted();
const projectAgentsSkillDirs = projectTrusted ? collectAncestorAgentsSkillDirs(this.cwd).filter(...) : [];
```

目录内的遍历规则（`core/skills.ts:160-167` 注释，**代码即文档**）：

```
- if a directory contains SKILL.md, treat it as a skill root and do not recurse further
- otherwise, load direct .md children in the root
- recurse into subdirectories to find SKILL.md
```

冲突策略：**first-wins + collision 诊断**（`core/skills.ts:410-427`，同 realpath 静默跳过，同 name 记 `collision` 诊断）。

### 4.2 frontmatter 解析

解析器：`packages/coding-agent/src/utils/frontmatter.ts`（整文件 **38 行**，基于 `yaml` 包）：

```ts
if (!normalized.startsWith("---")) return { yamlString: null, body: normalized };
const endIndex = normalized.indexOf("\n---", 3);
if (endIndex === -1) return { yamlString: null, body: normalized };
return { yamlString: normalized.slice(4, endIndex), body: normalized.slice(endIndex + 4).trim() };
```

字段（`core/skills.ts:67-72`）：`name?` / `description?` / `disable-model-invocation?`。

**`description` 是硬性必填**（`core/skills.ts:304-307`）：

```ts
// Still load the skill even with warnings (unless description is completely missing)
if (!frontmatter.description || frontmatter.description.trim() === "") {
	return { skill: null, diagnostics };
}
```

`name` 缺省取父目录名（`:295-296`）：`const name = frontmatter.name || parentDirName;`

真实样本 —— pi 自己仓库的 `.pi/skills/add-llm-provider.md` 前 4 行：

```yaml
---
name: add-llm-provider
description: Checklist for adding a new LLM provider to packages/ai. Covers core types, provider implementation, lazy registration, model generation, the full test matrix, coding-agent wiring, and docs.
---
```

### 4.3 progressive disclosure 的**决定性证据**

**证据 A：`Skill` 数据结构里根本没有 `content` 字段**（`packages/coding-agent/src/core/skills.ts:74-81`）：

```ts
export interface Skill {
	name: string;
	description: string;
	filePath: string;
	baseDir: string;
	sourceInfo: SourceInfo;
	disableModelInvocation: boolean;
}
```

→ 正文**从未被读进内存**，更不可能进 system prompt。

**证据 B：注入 system prompt 的只有 3 个 XML 字段**（`core/skills.ts:335-357`）：

```ts
export function formatSkillsForPrompt(skills: Skill[]): string {
	const visibleSkills = skills.filter((s) => !s.disableModelInvocation);
	const lines = [
		"\n\nThe following skills provide specialized instructions for specific tasks.",
		"Use the read tool to load a skill's file when the task matches its description.",   // ★ 明确指示用 read 工具
		"When a skill file references a relative path, resolve it against the skill directory …",
		"", "<available_skills>",
	];
	for (const skill of visibleSkills) {
		lines.push("  <skill>");
		lines.push(`    <name>${escapeXml(skill.name)}</name>`);
		lines.push(`    <description>${escapeXml(skill.description)}</description>`);
		lines.push(`    <location>${escapeXml(skill.filePath)}</location>`);
```

注释还标了标准出处：`See: https://agentskills.io/integrate-skills`（`core/skills.ts:329`）。

**证据 C：整个 skills 段的注入条件是"read 工具在场"**（`core/system-prompt.ts:154-157`）：

```ts
// Append skills section (only if read tool is available)
if (hasRead && skills.length > 0) prompt += formatSkillsForPrompt(skills);
```

→ 没有 `read` 工具就不列 skills，因为模型没法把正文拉进来。

### 4.4 正文什么时候才进上下文

**唯一入口**是显式斜杠命令 `/skill:<name> [args]` —— `AgentSession._expandSkillCommand`（`packages/coding-agent/src/core/agent-session.ts:1301-1315`）：

```ts
private _expandSkillCommand(text: string): string {
	if (!text.startsWith("/skill:")) return text;
	const skill = this.resourceLoader.getSkills().skills.find((s) => s.name === skillName);
	if (!skill) return text;
	const content = readFileSync(skill.filePath, "utf-8");          // ★ 此刻才读盘
	const body = stripFrontmatter(content).trim();
	const skillBlock = `<skill name="${skill.name}" location="${skill.filePath}">\nReferences are relative to ${skill.baseDir}.\n\n${body}\n</skill>`;
	return args ? `${skillBlock}\n\n${args}` : skillBlock;
}
```

反向解析器在 `agent-session.ts:128`（用于 TUI 重放已展开的 skill 消息）：

```ts
const match = text.match(/^<skill name="([^"]+)" location="([^"]+)">\n([\s\S]*?)\n<\/skill>(?:\n\n([\s\S]+))?$/);
```

> **两条路径合起来的完整故事**：常驻 context 只有 `name/description/location` 三元组（≈100 字符/skill）；模型自己判断相关 → 调 `read` 拉正文；或用户显式 `/skill:x` → pi 读盘注入。**零额外工具槽位**。

### 4.5 SDK 路径的小差异

`packages/agent/src/harness/skills.ts` 的 `Skill`（`harness/types.ts:64-75`）**有** `content: string`（发现时即读入内存，`skills.ts:232-265`），但注入 prompt 时仍只用 name/description/location（`harness/system-prompt.ts:15-21`），正文只在 `formatSkillInvocation()`（`harness/skills.ts:38-41`）被显式调用时才拼进去。结论一致。

---

## 5. Session 持久化

### 5.1 文件位置与命名

```
~/.pi/agent/sessions/--<cwd 编码>--/<ISO时间戳>_<sessionId>.jsonl
```

编码规则（`packages/coding-agent/src/core/session-manager.ts:474-481`）：

```ts
function getDefaultSessionDirPath(cwd: string, agentDir = getDefaultAgentDir()): string {
	const safePath = `--${resolvedCwd.replace(/^[/\\]/, "").replace(/[/\\:]/g, "-")}--`;
	return join(resolvedAgentDir, "sessions", safePath);
}
```

文件名（`session-manager.ts:952-953`）：

```ts
const fileTimestamp = timestamp.replace(/[:.]/g, "-");
this.sessionFile = join(this.getSessionDir(), `${fileTimestamp}_${this.sessionId}.jsonl`);
```

### 5.2 JSONL 结构

**第 1 行 header**（`session-manager.ts:30-39`）：

```ts
export const CURRENT_SESSION_VERSION = 3;
export interface SessionHeader {
	type: "session";
	version?: number;       // v1 sessions don't have this
	id: string;
	timestamp: string;
	cwd: string;
	parentSession?: string;  // ★ fork 来源
}
```

**其后每行一个 entry，全部继承同一基类**（`session-manager.ts:46-51`）——**这就是树的父指针**：

```ts
export interface SessionEntryBase {
	type: string;
	id: string;
	parentId: string | null;   // ★★ 树/父指针字段名
	timestamp: string;
}
```

**9 种 entry 类型**（`session-manager.ts:144-153`）：

```ts
export type SessionEntry =
	| SessionMessageEntry        // :53   type:"message",   message: AgentMessage
	| ThinkingLevelChangeEntry   // :58   type:"thinking_level_change"
	| ModelChangeEntry           // :63   type:"model_change", provider, modelId
	| CompactionEntry            // :69   type:"compaction",  summary, firstKeptEntryId, tokensBefore, details?, usage?, fromHook?
	| BranchSummaryEntry         // :82   type:"branch_summary", fromId, summary, …
	| CustomEntry                // :104  type:"custom",      customType, data?   —— 不进 context
	| CustomMessageEntry         // :135  type:"custom_message", customType, content, display  —— 进 context
	| LabelEntry                 // :111  type:"label",       targetId, label
	| SessionInfoEntry;          // :118  type:"session_info", name?
```

> SDK 路径（`packages/agent/src/harness/types.ts:453-464`）多两种：`ActiveToolsChangeEntry` 与 `LeafEntry`（把"当前叶子"也持久化），共 **11 种**；header 是硬性 `version: 3`（`harness/session/jsonl-store.ts:41-49`）。

### 5.3 写入：append-only + 延迟落盘

`_appendEntry`（`session-manager.ts:1044-1049`）：

```ts
private _appendEntry(entry: SessionEntry): void {
	this.fileEntries.push(entry);
	this.byId.set(entry.id, entry);
	this.leafId = entry.id;        // ★ 叶子指针前移
	this._persist(entry);
}
```

`_persist`（`:1015-1042`）——**文件在第一条 assistant 消息出现后才真正创建**，避免空会话堆积：

```ts
const hasAssistant = this.fileEntries.some((e) => e.type === "message" && e.message.role === "assistant");
if (!hasAssistant) { if (this.flushed) appendFileSync(...); else this.flushed = false; return; }   // :1018-1027
if (!this.flushed) {
	const fd = openSync(this.sessionFile, "wx");     // :1030 "wx" = 不覆盖已存在文件
	for (const e of this.fileEntries) writeFileSync(fd, `${JSON.stringify(e)}\n`);
	this.flushed = true;
} else appendFileSync(this.sessionFile, `${JSON.stringify(entry)}\n`);   // :1040
```

`appendMessage`（`:1057-1065`）的父指针赋值：

```ts
const entry: SessionMessageEntry = { type: "message", id: generateId(this.byId), parentId: this.leafId, timestamp: new Date().toISOString(), message };
```

### 5.4 读：路径回溯 + 压缩感知

`buildContextEntries`（`session-manager.ts:418-454`）：

```ts
const path = buildSessionPath(entries, leafId, byId);        // 沿 parentId 回溯到根再 reverse
let compaction: CompactionEntry | null = null;
for (const entry of path) if (entry.type === "compaction") compaction = entry;   // 取路径上最后一个
if (!compaction) return path;
const contextEntries: SessionEntry[] = [compaction];                              // :441 压缩条目放最前
for (let i = 0; i < compactionIdx; i++) { if (entry.id === compaction.firstKeptEntryId) foundFirstKept = true;
                                          if (foundFirstKept) contextEntries.push(entry); }   // :443-451
contextEntries.push(...path.slice(compactionIdx + 1));                            // :452
```

投影成消息 `sessionEntryToContextMessages`（`:383-408`）：`compaction` → `compactionSummary` 伪角色消息；`branch_summary` → `branchSummary`；`custom_message` → 自定义消息；**`custom` / `label` / `session_info` → 返回 `[]`（不进 context）**。同时对手改/旧版文件中 `content == null` 的消息做防御性修补（`:388-393`）。

### 5.5 fork / clone / resume / tree

> **⚠️ 需修正的旧结论**：之前的分析（`analysis/raw/02`）说 `/fork` "不新建文件，只把 leafId 移到旧节点"。**这已经不成立**。当前 commit 上 `/fork` 会**新建一个 session 文件**。

| 操作 | 实现位置 | 语义（实测） |
|---|---|---|
| `/fork` | UI: `modes/interactive/interactive-mode.ts:4663` `showUserMessageSelector()` → `:4682` `this.runtimeHost.fork(entryId)` | `position: "before"`（默认），目标必须是 **user 消息**，`targetLeafId = selectedEntry.parentId` |
| `/clone` | `interactive-mode.ts:4700` `handleCloneCommand()` → `runtimeHost.fork(leafId, { position: "at" })` | 从当前叶子整条路径 |
| **fork 实现** | `core/agent-session-runtime.ts:262-330` | 见下 |
| 抽路径成新文件 | `core/session-manager.ts:1412` `createBranchedSession(leafId)` | 见下 |
| 跨目录 fork | `core/session-manager.ts:1579` `static forkFrom(...)` | 写新 header + 逐行 append（`:1620-1625`） |
| `/tree` 导航 | `interactive-mode.ts:4721` `showTreeSelector()` | 走 `branch()` / `branchWithSummary()`，**只移动 leafId，不新建文件** |
| resume | `core/session-manager.ts` `SessionManager.open(...)`；CLI `--continue/-c`、`--resume/-r` | 读全文件 → `_buildIndex()`（`:957-976`）重建 `byId` 与 `leafId` |

`fork` 的分叉逻辑（`agent-session-runtime.ts:279-330`）：

```ts
if (position === "at") targetLeafId = selectedEntry.id;
else { if (selectedEntry.type !== "message" || selectedEntry.message.role !== "user") throw new Error("Invalid entry ID for forking");
       targetLeafId = selectedEntry.parentId; selectedText = extractUserMessageText(selectedEntry.message.content); }   // :279-287
…
if (!targetLeafId) { /* fork 第一条消息之前 → 直接开全新 session */ sessionManager.newSession({ parentSession: currentSessionFile }); }  // :296-309
…
const sessionManager = SessionManager.open(currentSessionFile, sessionDir);
const forkedSessionPath = sessionManager.createBranchedSession(targetLeafId);   // :317-318 ★ 新文件
```

`createBranchedSession`（`session-manager.ts:1412-1474`）的精髓 —— **摘掉 label 条目并重新链 parentId**：

```ts
// Because labels are real tree entries, later entries can be children of labels;
// removing labels requires re-chaining the retained path to avoid orphaned subtrees.
for (const entry of path) {
	if (entry.type === "label") continue;
	pathWithoutLabels.push({ ...entry, parentId: pathParentId });   // :1426 重链
	pathParentId = entry.id;
}
…
const header: SessionHeader = { type: "session", version: 3, id: newSessionId, timestamp, cwd, parentSession: previousSessionFile };  // :1435-1442
```

树内分支（**不新建文件**）—— `session-manager.ts:1360-1365`：

```ts
/** Moves the leaf pointer to the specified entry. The next appendXXX() call
 *  will create a child of that entry, forming a new branch. Existing entries
 *  are not modified or deleted. */
branch(branchFromId: string): void {
	if (!this.byId.has(branchFromId)) throw new Error(`Entry ${branchFromId} not found`);
	this.leafId = branchFromId;
}
```

`branchWithSummary`（`:1381-1404`）= `branch()` + 追加一条 `branch_summary` 条目。

> SDK 路径的 fork 是**声明式选择器**（`packages/agent/src/harness/session/fork.ts:4-24`）：`{kind:"all"} | {kind:"through_entry"} | {kind:"before_user_message"}`，后两者走 `reader.readPathToRootOrCompaction(...)`（沿 parentId 回溯，**遇 compaction 就停**）。

---

## 6. Compaction（上下文压缩）

### 6.1 阈值常量：**绝对值，不是百分比**

`packages/coding-agent/src/core/compaction/compaction.ts:132-136`：

```ts
export const DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
	enabled: true,
	reserveTokens: 16384,      // ★ 16K
	keepRecentTokens: 20000,   // ★ 20K
};
```

判定（`compaction.ts:235-238`），**一行**：

```ts
export function shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings): boolean {
	if (!settings.enabled) return false;
	return contextTokens > contextWindow - settings.reserveTokens;
}
```

> SDK 路径 `packages/agent/src/harness/compaction/compaction.ts:174-178` **常量完全相同**（16384 / 20000）。

### 6.2 三种触发 reason

`agent-session.ts:152` 定义：`reason: "manual" | "threshold" | "overflow"`。触发函数 `_checkCompaction`（`agent-session.ts:1953-2042`），**在 `agent_end` 之后与 prompt 提交之前调用**（`:1943-1944` 注释）：

| reason | 条件 | 行号 |
|---|---|---|
| `manual` | 用户敲 `/compact` | — |
| `overflow` | `sameModel && isContextOverflow(assistantMessage, contextWindow)` | `:1983` |
| `threshold` | `shouldCompact(contextTokens, contextWindow, settings)` | `:2038-2040` |

**三道防重复触发的护栏**（都很值得讲）：

1. **换模型豁免**（`:1966-1967`）：`sameModel = provider 与 model.id 都相等`，从小窗模型切到大窗模型时旧的 overflow 错误不再触发压缩
2. **压缩边界时间戳比较**（`:1972-1977`）：
   ```ts
   const compactionEntry = getLatestCompactionEntry(this.sessionManager.getBranch());
   const assistantIsFromBeforeCompaction = compactionEntry !== null && assistantMessage.timestamp <= new Date(compactionEntry.timestamp).getTime();
   if (assistantIsFromBeforeCompaction) return false;
   ```
3. **overflow 只救一次**（`:1990-2003`）：`this._overflowRecoveryAttempted` 标志位，第二次失败直接给用户 `"Context overflow recovery failed after one compact-and-retry attempt. Try reducing context or switching to a larger-context model."`

overflow 分支还会**先把错误消息从 agent 内存态里摘掉再重试**（`:2006-2009`）：

```ts
const messages = this.agent.state.messages;
if (messages.length > 0 && messages[messages.length - 1].role === "assistant") this.agent.state.messages = messages.slice(0, -1);
```

### 6.3 切点算法

`findCutPoint`（`compaction.ts:403`），算法注释在 `:387-399`：从最新往回累加估算 token，`accumulatedTokens >= keepRecentTokens`（`:429`）即切。

**合法切点的白名单/黑名单**（`compaction.ts:308-321`）——这段代码本身就是一张 PPT：

```ts
function isCutPointMessage(message: AgentMessage): boolean {
	switch (message.role) {
		case "user": case "assistant": case "bashExecution":
		case "custom": case "branchSummary": case "compactionSummary":
			return true;
		case "toolResult":
			return false;        // ★★ 绝不在 toolResult 上切，否则 toolCall 与其结果被切散
	}
	return false;
}
```

`findValidCutPoints`（`:351-363`）注释直白：

> "Never cut at tool results (they must follow their tool call). When we cut at an assistant message with tool calls, its tool results follow it and will be kept."

若切点不在轮首 → `findTurnStartIndex`（`:369-376`）回溯到轮首，标记 `isSplitTurn`（`CutPointResult`，`:378-385`），被劈开的那半个 turn 额外生成一段 **turn prefix summary**（用 `TURN_PREFIX_SUMMARIZATION_PROMPT`，`:795`），即 **一次压缩可能发两次 LLM 请求**。

### 6.4 压缩后保留什么

1. **一条 `CompactionEntry`**（`session-manager.ts:69-80`）：`summary` / `firstKeptEntryId` / `tokensBefore` / `details?` / `usage?` / `fromHook?`
2. **从 `firstKeptEntryId` 起的尾部条目**（`buildContextEntries`，`session-manager.ts:443-451`）
3. **文件操作清单**：从 tool call 里抽 read/edited 文件列表，跨压缩累积存进 `CompactionEntry.details`
4. **旧数据一条都不删** —— 只是读路径不再走到它们

### 6.5 摘要 prompt 的固定 6 段（`compaction.ts:467-498`）

```
## Goal
## Constraints & Preferences
## Progress   →  ### Done / ### In Progress / ### Blocked
## Key Decisions
## Next Steps
## Critical Context
```
结尾硬约束：`"Keep each section concise. Preserve exact file paths, function names, and error messages."`

**有前次摘要时换 prompt 做迭代合并**（`compaction.ts:643`）：

```ts
let basePrompt = previousSummary ? UPDATE_SUMMARIZATION_PROMPT : SUMMARIZATION_PROMPT;
```

`UPDATE_SUMMARIZATION_PROMPT`（`:500`）的规则：`PRESERVE all existing information` / `ADD new progress` / `UPDATE the Progress section: move items from "In Progress" to "Done"` / `PRESERVE exact file paths…`。

摘要请求的 `maxTokens`（`compaction.ts:638`）：`Math.floor(0.8 * reserveTokens)`；turn-prefix 摘要用 `0.5 * reserveTokens`（`:938`）。

### 6.6 SDK 路径

`AgentHarness.compact()`（`agent-harness.ts:783-840`）只提供**显式**压缩，无自动触发：

```ts
if (this.phase !== "idle") throw new AgentHarnessError("busy", "compact() requires idle harness");   // :785
this.phase = "compaction";
const preparationResult = prepareCompaction(branchEntries, DEFAULT_COMPACTION_SETTINGS);              // :792
const hookResult = await this.emitHook({ type: "session_before_compact", preparation, branchEntries, customInstructions, signal });  // :796
if (hookResult?.cancel) throw new AgentHarnessError("compaction", "Compaction cancelled");            // :803
const compactResult = provided ? { ok: true, value: provided } : await compact(preparation, this.models, model, ...);  // :805-816
const entryId = await this.session.appendCompaction(result.summary, result.firstKeptEntryId, result.tokensBefore, ...);  // :820
```

> 上 PPT 的点：**算法是纯函数、触发决策留给宿主**。harness 不猜宿主的重试/降级策略。

---

## 7. Extension / Hook

### 7.1 事件钩子清单：**33 个**（精确计数）

定义在 `packages/coding-agent/src/core/extensions/types.ts`，`ExtensionAPI` 接口从 `:1193` 开始，`on()` 重载共 **33 个**（`grep -c "^	on(" = 33`）：

```
project_trust  resources_discover
session_start  session_info_changed  session_before_switch  session_before_fork
session_before_compact  session_compact  session_shutdown  session_before_tree  session_tree
context  before_provider_request  before_provider_headers  after_provider_response
before_agent_start  agent_start  agent_end  agent_settled
turn_start  turn_end
message_start  message_update  message_end
tool_execution_start  tool_execution_update  tool_execution_end
model_select  thinking_level_select
tool_call  tool_result  user_bash  input
```

事件类型联合 `ExtensionEvent` 在 `:1034-1059`。

### 7.2 能**改变流程**的 8 个钩子（有 Result 类型）

`extensions/types.ts:1065-1094`：

| 钩子 | Result | 能力 | 行号 |
|---|---|---|---|
| `context` | `ContextEventResult { messages? }` | 改写送 LLM 的整个消息数组 | `:1065` |
| `before_provider_request` | `unknown` | 改 stream options | `:1069` |
| `tool_call` | `{ block?, reason? }` | **阻断工具执行**（注释：`To modify arguments, mutate event.input in place instead.`） | `:1071-1075` |
| `user_bash` | `{ operations?, result? }` | 整体接管 `!cmd` 执行 | `:1078-1083` |
| `tool_result` | `{ content?, details?, isError?, usage? }` | 改写工具结果 | `:1085` |
| `message_end` | `{ message? }`（注释：`The replacement must keep the original message role.`） | 替换定稿消息 | `:1092-1094` |
| `session_before_compact` | 可 cancel / 提供整份 compaction | 完全取代 LLM 摘要 | — |
| `session_before_tree` | 同上 | — | — |

### 7.3 注册 API（`ExtensionAPI`，`:1193` 起）

- **工具**：`registerTool<TParams, TDetails, TState>(tool: ToolDefinition)` 
- **命令/快捷键/CLI flag**：`registerCommand(name, opts)` / `registerShortcut(shortcut: KeyId, opts)` / `registerFlag(name, {type:"boolean"|"string", default?})` + `getFlag(name)`
- **渲染**：`registerMessageRenderer(customType, renderer)` / `registerMarkdownTransformer(t)` / `registerEntryRenderer(customType, renderer)`
- **动作**：`sendMessage(msg, {triggerTurn?, deliverAs?: "steer"|"followUp"|"nextTurn"})` / `sendUserMessage(content, {deliverAs?})` / `appendEntry(customType, data?)` / `exec(cmd, args, opts)`
- **会话元数据**：`setSessionName` / `getSessionName` / `setLabel(entryId, label)`
- **工具集与模型**：`getActiveTools()` / `getAllTools()` / `setActiveTools(names)` / `getCommands()` / `setModel(model)` / `getThinkingLevel()` / `setThinkingLevel(level)`
- **Provider**：`registerProvider(id, { baseUrl?, apiKey?, api?, models?, oauth?, streamSimple? })` —— 注释明确说明"初次加载时排队、之后即时生效，无需 `/reload`"

### 7.4 加载机制：jiti，**无沙箱**

`packages/coding-agent/src/core/extensions/loader.ts`：

```ts
import { createJiti } from "jiti/static";                       // :17
const jiti = createJiti(import.meta.url, {                      // :420
	…isBunBinary ? { virtualModules: VIRTUAL_MODULES, tryNative: false }
	 : isBuiltNode ? { virtualModules: VIRTUAL_MODULES, tsconfigPaths: true } : …   // :425-427
});
const module = await jiti.import(extensionPath, { default: true });   // :431 默认导出即工厂
const factory = module as ExtensionFactory;                            // :432
```

扩展签名 = `async (pi: ExtensionAPI) => {}`。`VIRTUAL_MODULES`（`:49`）白名单让扩展可以 `import` `pi-tui` / `pi-ai` / `typebox`（编译成 Bun 单文件二进制时无 node_modules）。有 `extensionCache: Map<string, ExtensionFactory>`（`:148`）。

### 7.5 生态规模（可作为"扩展点够用"的量化证据）

```bash
$ ls packages/coding-agent/examples/extensions/ | wc -l
79
```

其中直接对应"pi 刻意不做的功能"的示例：`permission-gate.ts`、`plan-mode/`、`sandbox/`（基于 `@anthropic-ai/sandbox-runtime`）、`gondolin/`（micro-VM）、`subagent/`、`todo.ts`、`custom-compaction.ts`、`git-checkpoint.ts`、`ssh.ts`。

pi 仓库自己也在吃狗粮：`pi-mono/.pi/` 下有 `extensions/`（4 个 .ts）、`prompts/`（5 个 .md）、`skills/`（1 个）、`git/`、`npm/`。

### 7.6 SDK 路径对照

`AgentHarness` 的钩子结果映射 `AgentHarnessEventResultMap`（`packages/agent/src/harness/types.ts:816-838`）共 **22 项**，其中 **8 项有非 undefined 的返回类型**（可改流程）：`before_agent_start`（`{messages?, systemPrompt?}`）、`context`、`before_provider_request`、`before_provider_payload`、`tool_call`、`tool_result`（多一个 `terminate?`）、`session_before_compact`、`session_before_tree`。其余 14 项（`after_provider_response` / `session_compact` / `session_tree` / `retry_*` ×3 / `model_update` / `thinking_level_update` / `resources_update` / `tools_update` / `queue_update` / `save_point` / `abort` / `settled`）是纯通知。

---

## 8. 子代理（Task）分发

### 8.1 结论：**内核里不存在**，是产品决策

`packages/coding-agent/README.md:497`：

> **No sub-agents.** There's many ways to do this. Spawn pi instances via tmux, or build your own with [extensions](#extensions), or install a package that does it your way.

同页 `:495`：

> **No MCP.** Build CLI tools with READMEs (see [Skills](#skills)), or build an extension that adds MCP support. [Why?](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/)

`packages/coding-agent/docs/usage.md:301`（一句话列全"刻意不做"清单）：

> It intentionally does not include built-in MCP, sub-agents, permission popups, plan mode, to-dos, or background bash. You can build or install those workflows as extensions or packages, or use external tools such as containers and tmux.

代码印证：`ToolName` 只有 7 个（`core/tools/index.ts:83`），无 `task`/`subagent`。

### 8.2 参考实现：**独立子进程，不是嵌套 harness**

`packages/coding-agent/examples/extensions/subagent/index.ts`（**1015 行**）。

**怎么起一个子 agent**（`:294-296`、`:325`、`:329`、`:335-338`）：

```ts
const args: string[] = ["--mode", "json", "-p", "--no-session"];        // :294 ★
if (agent.model) args.push("--model", agent.model);                     // :295
if (agent.tools && agent.tools.length > 0) args.push("--tools", agent.tools.join(","));  // :296
…
if (agent.systemPrompt.trim()) { const tmp = await writePromptToTempFile(agent.name, agent.systemPrompt);
                                 args.push("--append-system-prompt", tmpPromptPath); }   // :321-326
args.push(`Task: ${task}`);                                             // :329
const proc = spawn(invocation.command, invocation.args, { cwd: cwd ?? defaultCwd, shell: false, stdio: ["ignore", "pipe", "pipe"] });  // :335-339
```

自举方式（`:253-259`）：`{ command: process.execPath, args: [currentScript, ...args] }`（Node）或直接 `process.execPath`（Bun 单文件二进制）。

**上下文如何隔离** —— 四重，全部靠 CLI flag：

| 隔离维度 | 手段 | 行号 |
|---|---|---|
| **进程** | `spawn()` 独立 OS 进程，stdin `ignore`，stdout/stderr 管道 | `:335-339` |
| **会话** | `--no-session` —— 子进程完全不写 session 文件 | `:294` |
| **消息历史** | `-p`（print 模式）一次性 prompt，子进程从零上下文起 | `:294` |
| **工具集** | `--tools <list>` 按 agent 定义裁剪 | `:296` |
| **系统提示** | `--append-system-prompt <tmpfile>` 注入角色提示，用完删临时目录 | `:321-326` |
| **模型** | `--model <id>` 可与父 agent 不同 | `:295` |

**结果如何回传**：父进程逐行解析子进程 stdout 的 JSONL（`--mode json` 保证一行一个 `AgentSessionEvent`），只挑 `event.type === "message_end"`（`:345-360`）累积消息与 usage（`input/output/cacheRead/cacheWrite/cost/turns`）。

**注册为工具**（`:461-472`）：

```ts
export default function (pi: ExtensionAPI) {
	pi.registerTool({
		name: "subagent",
		label: "Subagent",
		description: [
			"Delegate tasks to specialized subagents with isolated context.",
			"Modes: single (agent + task), parallel (tasks array), chain (sequential with {previous} placeholder).",
			`Default agent scope is "user" (from ${path.join(getAgentDir(), "agents")}).`, …
		].join(" "),
		parameters: SubagentParams,
```

三种模式：`single` / `parallel` / `chain`（`{previous}` 占位符做串联）。agent 定义从 `~/.pi/agent/agents/` 与 `<cwd>/.pi/agents/` 发现，**项目级 agent 默认需要交互确认**（`confirmProjectAgents` 默认 `true`，`:475`、`:508`）。

> 上 PPT 的点：**pi 的子代理是"再开一个 pi 进程"，不是"在进程内再 new 一个 AgentHarness"**。上下文隔离由操作系统保证，不需要任何框架抽象。

---

## 9. AgentHarness 这一层到底封装了什么

> **"harness" 这个词的绝佳实例。** pi 自己的默认 system prompt 第一句就是：
> `"You are an expert coding assistant operating inside pi, a coding agent harness."`（`core/system-prompt.ts:121`）

`packages/agent/src/harness/agent-harness.ts`，**1185 行**，类声明在 `:173`。

### 9.1 一句话定义

**`AgentHarness` = 无状态的 `agent-loop` + 有状态的一切。** 它把"跑一次 LLM 循环"变成"经营一个可持久化、可分支、可插拔、可中断、可压缩的长生命周期会话"。

### 9.2 封装的 8 件事（每件都有代码坐标）

#### (1) 生命周期状态机

`packages/agent/src/harness/types.ts:575`，**5 个 phase**：

```ts
export type AgentHarnessPhase = "idle" | "turn" | "compaction" | "branch_summary" | "retry";
```

所有对外动作都要求 `phase === "idle"`，否则抛 `busy`：

```ts
async prompt(text, options) {           // :692
	this.assertNotShutDown();
	if (this.phase !== "idle") throw new AgentHarnessError("busy", "AgentHarness is busy");   // :694
	this.phase = "turn";
```

`compact()` `:785`、`navigateTree()` `:842` 同款守卫。

#### (2) Turn Snapshot（"save point" 语义）

`createTurnState()`（`:395-429`）在**每轮开始**冻结 10 个字段：

```ts
return { messages, resources, toolContext, streamOptions, sessionId,
         systemPrompt, model, thinkingLevel, tools, activeTools };   // :417-428
```

`prepareNextTurn` 钩子（`:527-536`）在轮边界重建快照：

```ts
prepareNextTurn: async () => {
	await this.flushPendingSessionWrites();
	const nextTurnState = await this.createTurnState();
	setTurnState(nextTurnState);
	return { context: this.createContext(nextTurnState), model: nextTurnState.model, thinkingLevel: nextTurnState.thinkingLevel };
},
```

→ 运行中调 `setModel()` / `setTools()` **不撕裂进行中的 provider 请求**，下一轮才生效。

#### (3) 工具上下文柯里化

`bindToolContext`（`:388-393`）—— 把工具的第 5 个参数吃掉，交给 agent-loop 时是标准 4 参 `AgentTool`：

```ts
private bindToolContext(tool: TTool, context: TContext): AgentTool {
	return { ...tool, execute: (toolCallId, params, signal, onUpdate) => tool.execute(toolCallId, params, signal, onUpdate, context) };
}
```

#### (4) Provider 请求的中间件层

`createStreamFn`（`:442-470`）—— 把 `models.streamSimple` 包成 `StreamFn`，中途插三个钩子：

```ts
const requestOptions = await this.emitBeforeProviderRequest(model, turnState.sessionId, snapshotOptions);   // :448
return this.models.streamSimple(model, context, {
	cacheRetention, headers, maxRetries, maxRetryDelayMs, metadata,
	onPayload: async (payload) => await this.emitBeforeProviderPayload(model, payload),                        // :455
	onResponse: async (response) => { await this.emitOwn({ type: "after_provider_response", status, headers }); },  // :456-462
	reasoning, signal, sessionId: turnState.sessionId, timeoutMs, transport });
```

#### (5) 把 hook 编译进 `AgentLoopConfig`

`createLoopConfig`（`:484-540`）—— **这是 harness 的核心翻译层**，把声明式 hook 变成 agent-loop 认识的回调：

```ts
transformContext: async (messages) => { const r = await this.emitHook({ type: "context", messages: [...messages] }); return r?.messages ?? messages; },  // :493
beforeToolCall:   async ({ toolCall, args }) => { const r = await this.emitHook({ type: "tool_call", ... }); return r ? { block: r.block, reason: r.reason } : undefined; },  // :497
afterToolCall:    async ({ toolCall, args, result, isError }) => { const patch = await this.emitHook({ type: "tool_result", ... }); return patch ? {...} : undefined; },      // :506
prepareNextTurn:  /* 见 (2) */                                                                                                      // :527
getSteeringMessages: async () => this.drainQueuedMessages(this.steerQueue, this.steeringQueueMode),                                  // :537
getFollowUpMessages: async () => this.drainQueuedMessages(this.followUpQueue, this.followUpQueueMode),                               // :538
```

#### (6) 三条消息队列 + 两种队列模式

字段（`:196-200`）：`steerQueue` / `followUpQueue` / `nextTurnQueue`，模式 `QueueMode = "all" | "one-at-a-time"`（默认后者，`:222-223`）。

`drainQueuedMessages`（`:472-482`）—— **失败会把消息塞回队列**：

```ts
const messages = mode === "all" ? queue.splice(0) : queue.splice(0, 1);
try { await this.emitQueueUpdate(); return messages; }
catch (error) { queue.unshift(...messages); throw normalizeHookError(error); }   // :479-480
```

#### (7) 持久化时序：`pendingSessionWrites` 队列 + save point

`handleAgentEvent`（`:580-607`）—— **消息即时落盘，扩展的写入延到轮边界**：

```ts
if (event.type === "message_end") { await this.session.appendMessage(event.message); await this.emitAny(event, signal); return; }   // :581-585
if (event.type === "turn_end") {
	try { await this.emitAny(event, signal); } catch (error) { eventError = error; }
	const hadPendingMutations = this.pendingSessionWrites.length > 0;
	await this.flushPendingSessionWrites();                       // :594  ★ 只在轮边界落盘
	if (eventError) throw eventError;
	await this.emitOwn({ type: "save_point", hadPendingMutations });   // :596
	return; }
if (event.type === "agent_end") { await this.flushPendingSessionWrites(); this.phase = "idle";
	await this.emitAny(event, signal); await this.emitOwn({ type: "settled", nextTurnCount: this.nextTurnQueue.length }, signal); return; }  // :599-605
```

`flushPendingSessionWrites`（`:554-578`）是一个 9 分支 dispatcher（`message` / `model_change` / `thinking_level_change` / `active_tools_change` / `custom` / `custom_message` / `label` / `session_info` / `leaf`），保证 transcript 顺序纯净。

#### (8) 失败兜底：把异常变回一条 assistant 消息

`emitRunFailure`（`:609-621`）—— 即使 `runAgentLoop` 抛了，也补齐一整套事件序列，让上层永远看到"完整的一轮"：

```ts
const failureMessage = createFailureMessage(model, error, aborted);
await this.handleAgentEvent({ type: "message_start", message: failureMessage }, signal);
await this.handleAgentEvent({ type: "message_end", message: failureMessage }, signal);
await this.handleAgentEvent({ type: "turn_end", message: failureMessage, toolResults: [] }, signal);
await this.handleAgentEvent({ type: "agent_end", messages: [failureMessage] }, signal);
```

调用点在 `executeTurn`（`:666-676`），外层还套一层 `AggregateError`（"失败上报也失败了"）。

### 9.3 `executeTurn` —— 一行看懂 harness 与 loop 的边界

`agent-harness.ts:658-665`：

```ts
return await runAgentLoop(
	messages,                                       // ← harness 组装（user 消息 + nextTurnQueue + before_agent_start 注入）
	this.createContext(turnState, beforeResult?.systemPrompt),   // ← harness 冻结的快照
	this.createLoopConfig(getTurnState, setTurnState),           // ← harness 把 hook 编译成回调
	(event) => this.handleAgentEvent(event, signal),             // ← harness 接管持久化与广播
	signal,
	this.createStreamFn(getTurnState),                           // ← harness 包装的 provider 中间件
);
```

**6 个参数里，5 个是 harness 提供的。agent-loop 本身一个状态都不存。**

### 9.4 对外 API 面（40+ 方法，`:692-1160`）

- **驱动**：`prompt` `:692` / `skill` `:708` / `promptFromTemplate` `:730` / `steer` `:748` / `followUp` `:755` / `nextTurn` `:762` / `appendMessage` `:768`
- **上下文管理**：`compact` `:783` / `navigateTree` `:842`
- **运行时可变状态**：`getModel/setModel` `:942/:946`、`getThinkingLevel/setThinkingLevel` `:964/:968`、`getTools/setTools` `:986/:990`、`getActiveTools/setActiveTools` `:1026/:1030`、`getSteeringMode/setSteeringMode` `:1059/:1063`、`getFollowUpMode/setFollowUpMode` `:1068/:1072`、`getResources/setResources` `:1077/:1084`、`getStreamOptions/setStreamOptions` `:1094/:1098`
- **生命周期**：`requestShutdown` `:1104` / `waitForShutdown` `:1116` / `abort` `:1123` / `waitForIdle` `:1153`

`abort()` 返回 `AbortResult { clearedSteer, clearedFollowUp }`（`harness/types.ts:844-847`）—— **被清掉的排队消息会还给调用方**，这样 TUI 可以把它们塞回编辑器。

---

## 10. 规模数据（PPT 可直接引用）

`find packages/<p> -name "*.ts" -not -path "*/node_modules/*" -not -path "*/dist/*" | xargs wc -l | tail -1`：

| 包 | TypeScript 行数 |
|---|---|
| `packages/coding-agent` | **117,268** |
| `packages/ai` | **55,347** |
| `packages/tui` | **29,030** |
| `packages/agent` | **18,954** |
| `packages/server` | 5,682 |
| `packages/client` | 2,463 |
| `packages/protocol` | 1,902 |
| `packages/evals` | 1,774 |
| `packages/storage` | 1,586 |

单文件：`agent-loop.ts` **792** 行 / `agent.ts` **577** 行 / `agent-harness.ts` **1185** 行 / `agent/src/types.ts` **437** 行 / `coding-agent/src/core/system-prompt.ts` **163** 行 / `coding-agent/src/core/compaction/compaction.ts` **969** 行 / `coding-agent/src/core/skills.ts` **487** 行。

Provider 层：`KnownApi` **10 种** wire protocol（`packages/ai/src/types.ts:16-26`：`openai-completions` / `mistral-conversations` / `openai-responses` / `azure-openai-responses` / `openai-codex-responses` / `anthropic-messages` / `bedrock-converse-stream` / `google-generative-ai` / `google-vertex` / `pi-messages`）；`KnownProvider` **38 个**（`types.ts:34-72`）；`src/api/` 非 lazy 文件 **19 个**；`src/providers/` 非 models 文件 **45 个**。

模式：`resolveAppMode`（`packages/coding-agent/src/main.ts:109-120`）

```ts
if (parsed.mode === "rpc") return "rpc";
if (parsed.mode === "json") return "json";
if (parsed.print || !stdinIsTTY || !stdoutIsTTY) return "print";
return "interactive";
```

---

## 11. 未找到 / 待核实

| 项 | 状态 |
|---|---|
| 内置 `task` / `subagent` 工具 | **未找到**（确认不存在，见第 8 节。只有 examples 扩展） |
| 内置 MCP 客户端 | **未找到**（README:495 明确"No MCP"）。注：`analysis/raw/06b-omp-mcp-subsystem.md` 谈的是另一个项目（omp），**不要与 pi 混讲** |
| 内置 todo / plan mode / 权限弹窗 / 后台 bash | **未找到**（docs/usage.md:301 明确列为"intentionally does not include"） |
| pi 的首次公开发布日期 / 版本时间线 | **本次未做**（这是仓库代码取证任务，未查 npm registry / GitHub Releases）。PPT 若要写日期，需另做一次 registry 取证 |
| `packages/server` 是否用 AgentHarness | **未使用**——`grep` 无命中，server 依赖 `@earendil-works/pi-coding-agent`（`packages/server/package.json:58`） |
| `Agent`（`packages/agent/src/agent.ts`）是否会被弃用 | **待核实**——代码中无 `@deprecated` 标记，但 `AgentHarness` 明显是更完整的替代品。不要在 PPT 上断言"legacy" |

## 12. 与既有分析的差异（需要修正的旧结论）

| 旧结论（`analysis/raw/02`） | 实测结果 |
|---|---|
| `/fork` "不新建文件，只把 leafId 移到旧节点" | **错**。`/fork` → `runtimeHost.fork()`（`agent-session-runtime.ts:262`）→ `createBranchedSession()`（`session-manager.ts:1412`）**新建 session 文件**。只移动 leafId 的是 `/tree`（`session-manager.ts:1360` `branch()`） |
| 扩展"33 个事件钩子" | **对**，实测 `ExtensionAPI` 有 33 个 `on()` 重载 |
| Session entry "9 种类型" | **对**（coding-agent 路径）。但 harness 路径是 **11 种**（多 `active_tools_change` 与 `leaf`） |
| `analysis/raw/01` 说 "AgentHarness 是编排层，直接调 runAgentLoop" | **对**，但需补充：**coding-agent 完全没用它**，产品路径走 `AgentSession` + `Agent` |
