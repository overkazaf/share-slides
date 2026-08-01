# P05：上下文工程 —— system prompt 组装 · token 预算 · compaction · SKILL 渐进式披露

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `https://github.com/earendil-works/pi.git` | `git remote -v` |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/coding-agent/package.json:3`、`packages/agent/package.json:3` |
> | 本地路径 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开验证。
> 行号会随上游提交漂移 —— PPT 上引用时**必须带 commit 短 hash `583f153`**。
>
> 沿用 R10 的结构事实：pi 有**两套** agent 编排层 —— 产品路径 `packages/coding-agent/`（`pi` CLI 实际跑的）与 SDK 路径 `packages/agent/src/harness/`。本篇**以产品路径为主线**，harness 差异单列。

---

## 0. 一页看懂：一次 LLM 请求里到底装了什么

```
┌─ system（1~2 个 text block）────────────────────────────────┐
│ [OAuth 时才有] "You are Claude Code, Anthropic's official   │  ← 不是 pi 写的，provider 层强塞
│                 CLI for Claude."                            │
│ ─────────────────────────────────────────────────────────── │
│ ① 固定开场白（1 句）                                        │
│ ② Available tools: 列表     ← 只列有 promptSnippet 的工具   │
│ ③ 「还可能有自定义工具」一句                                │
│ ④ Guidelines: 列表          ← 条件生成 + Set 去重           │
│ ⑤ Pi 文档绝对路径清单（7 行）                               │
│ ⑥ appendSystemPrompt        ← .pi/APPEND_SYSTEM.md          │
│ ⑦ <project_context> AGENTS.md / CLAUDE.md 全文 </>          │
│ ⑧ <available_skills> name/description/location 三元组 </>   │
│ ⑨ Current working directory: <cwd>                          │
└─────────────────────────────────────────────────────────────┘
┌─ tools（JSON Schema 数组）─────────────────────────────────┐
│ read / bash / edit / write 的 name+description+input_schema │
└─────────────────────────────────────────────────────────────┘
┌─ messages（会话历史，compaction 的作用对象）───────────────┐
└─────────────────────────────────────────────────────────────┘
```

**实测量级**（下文各节给命令与出处）：

| 块 | 字符 | ≈token（chars/4） |
|---|---:|---:|
| system prompt 骨架（默认 4 工具，无 AGENTS.md / 无 skills） | 2 520 | 630 |
| ├ 其中 `Available tools` 列表 | 221 | 55 |
| ├ 其中 `Guidelines` 列表（10 条） | 814 | 204 |
| └ 其中固定文案 + Pi 文档路径段 | 1 444 + cwd 行 | ≈365 |
| tools JSON（4 个默认工具，Anthropic 口径） | 2 724 | 681 |
| pi 自己仓库的 `AGENTS.md` | 10 731 | 2 683 |
| skills 段头 + 段尾（固定开销） | 348 + 20 | 92 |
| 每个 skill 条目（以 `add-llm-provider` 为例） | 380 | 95 |

> 一句话上 PPT：**pi 的「自带上下文」不到 1.4K token（system 骨架 630 + tools 681）；真正吃预算的是项目自己的 `AGENTS.md`（这里 2.7K token，是 pi 骨架的 4 倍多）。**

---

## 1. system prompt 由哪几块拼起来

### 1.1 入口：一个 162 行的纯函数

```bash
$ wc -l packages/coding-agent/src/core/system-prompt.ts
     162 packages/coding-agent/src/core/system-prompt.ts
```

- 纯函数入口：`buildSystemPrompt(options: BuildSystemPromptOptions)` —— `packages/coding-agent/src/core/system-prompt.ts:28`
- 选项结构体 `BuildSystemPromptOptions` —— `system-prompt.ts:8-25`，**共 8 个字段**：`customPrompt` / `selectedTools` / `toolSnippets` / `promptGuidelines` / `appendSystemPrompt` / `cwd` / `contextFiles` / `skills`
- 唯一调用方：`AgentSession._rebuildSystemPrompt(toolNames)` —— `packages/coding-agent/src/core/agent-session.ts:1021-1054`
- 两处触发：`agent-session.ts:939`（构造 / reload）与 `agent-session.ts:2275`（活动工具集变化时重建）

`_rebuildSystemPrompt` 做的事（`agent-session.ts:1022-1054`，10 行摘要）：

```ts
const validToolNames = toolNames.filter((name) => this._toolRegistry.has(name));   // :1022
for (const name of validToolNames) {
	const snippet = this._toolPromptSnippets.get(name); if (snippet) toolSnippets[name] = snippet;      // :1026-1029
	const toolGuidelines = this._toolPromptGuidelines.get(name); if (toolGuidelines) promptGuidelines.push(...toolGuidelines);  // :1031-1034
}
const loaderSystemPrompt = this._resourceLoader.getSystemPrompt();                 // :1036
const loadedSkills = this._resourceLoader.getSkills().skills;                      // :1040
const loadedContextFiles = this._resourceLoader.getAgentsFiles().agentsFiles;      // :1041
this._baseSystemPromptOptions = { cwd, skills, contextFiles, customPrompt, appendSystemPrompt, selectedTools, toolSnippets, promptGuidelines };  // :1043-1052
return buildSystemPrompt(this._baseSystemPromptOptions);                           // :1053
```

### 1.2 默认模板分支：9 段，逐段给行号

| # | 段 | 行号 | 实测字符 | 说明 |
|---|---|---|---:|---|
| 1 | `You are an expert coding assistant operating inside pi, a coding agent harness. …` | `:121` | 146 | 固定开场白，**"harness" 这个词写在 pi 自己的 system prompt 里** |
| 2 | `Available tools:` + 列表 | `:123-124` | 221 | ★ 只列**提供了 `promptSnippet`** 的工具，全空则整段是 `(none)` |
| 3 | `In addition to the tools above, you may have access to other custom tools…` | `:126` | 106 | 给扩展工具留口 |
| 4 | `Guidelines:` + 列表 | `:128-129` | 814 | 条件生成，见 1.4 |
| 5 | `Pi documentation (read only when the user asks about pi itself…)` + 7 行 | `:131-138` | 1 070（含示例绝对路径） | README / docs / examples 的**绝对路径**，由 `config.ts:427/432/437` 三个函数算出 |
| 6 | `appendSystemPrompt` | `:140-142` | 变长 | 来自 `.pi/APPEND_SYSTEM.md` / `~/.pi/agent/APPEND_SYSTEM.md` / `--append-system-prompt` |
| 7 | `<project_context>` … `<project_instructions path="…">` … `</project_context>` | `:144-152` | 变长 | AGENTS.md / CLAUDE.md 全文，见第 6 节 |
| 8 | `formatSkillsForPrompt(skills)` | `:154-157` | 368 + 380/条 | ★ 条件：`hasRead && skills.length > 0` |
| 9 | `\nCurrent working directory: <cwd>` | `:159` | 变长 | 收尾 |

`customPrompt` 分支（`.pi/SYSTEM.md` 或 `--system-prompt`）在 `:46-72`：**整段跳过 1~5**，只保留 `custom(:47) + append(:49-51) + project_context(:54-61) + skills(:64-67) + cwd(:69)`。注意 `:64` 这里对 read 工具的判定写法与默认分支不同：

```ts
const customPromptHasRead = !selectedTools || selectedTools.includes("read");   // :64
```

即**没传 `selectedTools` 时默认当作有 read**，而默认分支 `:101` 是 `tools.includes("read")`（`tools` 已在 `:81` 兜底为 `["read","bash","edit","write"]`）。两者结果一致，但代码路径是两份。

### 1.3 实测：裸 system prompt 有多大

复刻 `system-prompt.ts:121-159` 的模板 + 4 个默认工具的 snippet/guideline（全部逐字从源码抄出），脚本在
`scratchpad/p05-toolpayload.mjs` 同目录，命令：

```bash
$ node -e '<复刻 buildSystemPrompt 默认分支>'
骨架(不含 tools/guidelines) = 1444
toolsList chars= 221
guidelines chars= 814
裸 system prompt(默认4工具, 无 AGENTS.md/skills) chars= 2520  ~tok= 630
```

**630 token。** 这是 pi 在「什么项目文件都没有」时的上下文底噪。

### 1.4 两个锐利细节

**(a) 工具出不出现在 prompt 里，由 `promptSnippet` 决定，不是由注册决定**（`system-prompt.ts:79-84`）：

```ts
// A tool appears in Available tools only when the caller provides a one-line snippet.
const tools = selectedTools || ["read", "bash", "edit", "write"];
const visibleTools = tools.filter((name) => !!toolSnippets?.[name]);
const toolsList =
	visibleTools.length > 0 ? visibleTools.map((name) => `- ${name}: ${toolSnippets![name]}`).join("\n") : "(none)";
```

**(b) Guidelines 是条件生成 + Set 去重的**（`system-prompt.ts:87-119`）：

```ts
const addGuideline = (g: string) => { if (guidelinesSet.has(g)) return; guidelinesSet.add(g); guidelinesList.push(g); };  // :89-95
if (hasBash && !hasGrep && !hasFind && !hasLs) addGuideline("Use bash for file operations like ls, rg, find");  // :104-106
for (const guideline of promptGuidelines ?? []) { ... }        // :108-113  各工具贡献
addGuideline("Be concise in your responses");                   // :116 恒有
addGuideline("Show file paths clearly when working with files");// :117 恒有
```

默认 4 工具实际产出 **10 条 guideline / 814 字符**，其中 `edit` 一个工具就贡献 4 条 / 496 字符（`core/tools/edit.ts:299-304`）——**edit 是整个 system prompt 里最贵的单个工具**。

### 1.5 有没有「prompt 写在 .md 而不是代码里」？

**内置 prompt：全部是 TypeScript 字符串字面量，仓库源码目录里一个 .md 都没有。**

```bash
$ find packages/coding-agent/src packages/agent/src -name "*.md"
# （无输出）
```

内置 prompt 的三处硬编码位置：
- 主 system prompt：`core/system-prompt.ts:121-138`（模板字面量）
- 摘要 prompt：`core/compaction/compaction.ts:467`、`:500`、`:795`
- 摘要 system prompt：`core/compaction/utils.ts:156-158`

**用户侧 prompt 才走 .md**，共 5 类，全部是「发现文件 → `readFileSync` → 拼字符串」：

| 类型 | 路径 | 发现代码 |
|---|---|---|
| 替换整个 system prompt | `<cwd>/.pi/SYSTEM.md`（需 trust）→ `~/.pi/agent/SYSTEM.md` | `core/resource-loader.ts:1022-1034` |
| 追加到 system prompt | `<cwd>/.pi/APPEND_SYSTEM.md`（需 trust）→ `~/.pi/agent/APPEND_SYSTEM.md` | `core/resource-loader.ts:1036-1048` |
| 项目上下文 | `AGENTS.md` / `AGENTS.MD` / `CLAUDE.md` / `CLAUDE.MD` | `core/resource-loader.ts:70-89`、`:118-156` |
| Skill | `<dir>/SKILL.md` 或 `<dir>/*.md` | `core/skills.ts:160-260` |
| Prompt 模板（斜杠命令） | `~/.pi/agent/prompts/`、`<cwd>/.pi/prompts/` | `core/prompt-templates.ts:202-203` |

pi 自己仓库就有 5 个模板：`.pi/prompts/{cl,is,pr,sa,wr}.md`。

> 上 PPT 的点：**pi 的立场是「内核 prompt 归代码、项目 prompt 归 .md」。想改 pi 的默认人格不用改代码 —— 丢一个 `.pi/SYSTEM.md` 就整段替换掉了。**

### 1.6 SDK 路径（harness）对照

`AgentHarness` **没有默认模板**，systemPrompt 是调用方传入的字符串或工厂函数（`packages/agent/src/harness/agent-harness.ts:405-416`）：

```ts
let systemPrompt = "You are a helpful assistant.";      // :405 兜底
if (typeof this.systemPrompt === "string") systemPrompt = this.systemPrompt;          // :406-407
else if (this.systemPrompt) systemPrompt = await this.systemPrompt({ session, model, thinkingLevel, activeTools, resources });  // :408-416
```

harness 只提供 skills 片段格式化：`formatSkillsForSystemPrompt`（`packages/agent/src/harness/system-prompt.ts:3-25`，整文件 34 行）。

---

## 2. 上下文预算怎么算

### 2.1 token 计数：**两套口径混用**

**口径 A —— provider 真实 usage**（`core/compaction/compaction.ts:146-148`）：

```ts
export function calculateContextTokens(usage: Usage): number {
	return usage.totalTokens || usage.input + usage.output + usage.cacheRead + usage.cacheWrite;
}
```

**口径 B —— chars/4 启发式**（`core/compaction/compaction.ts:266-305`），注释明写「保守（高估）」：

```ts
/** Estimate token count for a message using chars/4 heuristic. This is conservative (overestimates tokens). */
export function estimateTokens(message: AgentMessage): number { ... Math.ceil(chars / 4) ... }
```

逐 role 的字符统计规则（`:268-303`）：
- `user` / `custom` / `toolResult`：文本块取 `text.length`，**图片块按固定 `ESTIMATED_IMAGE_CHARS = 4800` 计**（`:244`、`:256`）→ 每张图 ≈1 200 token
- `assistant`：`text.length` + `thinking.length` + `name.length + JSON.stringify(arguments).length`
- `bashExecution`：`command.length + output.length`
- `branchSummary` / `compactionSummary`：`summary.length`

**两套口径的缝合点** `estimateContextTokens`（`:202-227`）—— 这是最值得上 PPT 的一段设计：

```ts
const usageInfo = getLastAssistantUsageInfo(messages);            // :203  找最后一条有效 usage
if (!usageInfo) { /* 全部 chars/4 */ }                            // :205-217
const usageTokens = calculateContextTokens(usageInfo.usage);      // :219  这一段用真实值
let trailingTokens = 0;
for (let i = usageInfo.index + 1; i < messages.length; i++) trailingTokens += estimateTokens(messages[i]);  // :221-223  之后的用估算
return { tokens: usageTokens + trailingTokens, usageTokens, trailingTokens, lastUsageIndex: usageInfo.index };  // :225
```

> **「真实 usage 打底 + chars/4 补尾巴」**：已经问过模型的部分用 provider 回报的真值，最后一次回复之后新增的消息（用户输入、工具结果）用 chars/4 估。这样既不用本地跑 tokenizer，又不会在一轮里累积漂移。
>
> 「有效 usage」的定义在 `:153-166`：`stopReason` 不是 `aborted`/`error`，且 `calculateContextTokens(usage) > 0` —— **全零 usage 视为无效**，这是为了兜住某些 provider 返回 0 的畸形响应。

### 2.2 超限阈值：绝对值，不是百分比

`core/compaction/compaction.ts:132-136`：

```ts
export const DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
	enabled: true,
	reserveTokens: 16384,      // ★ 16K
	keepRecentTokens: 20000,   // ★ 20K
};
```

**判定就一行** —— `core/compaction/compaction.ts:235-238`：

```ts
export function shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings): boolean {
	if (!settings.enabled) return false;
	return contextTokens > contextWindow - settings.reserveTokens;     // :237  ★ 唯一的超限阈值行
}
```

即：**触发线 = contextWindow − 16384**。对 200K 窗口 = 183 616 token（91.8%）；对 1M 窗口 = 983 616（98.4%）。**窗口越大，触发得越晚（百分比意义上）** —— 这是绝对值阈值的直接后果。

三个常量都可被 `settings.json` 覆盖（`core/settings-manager.ts:765-792`）：

```ts
getCompactionEnabled():          this.settings.compaction?.enabled ?? true            // :765-767
getCompactionReserveTokens():    this.settings.compaction?.reserveTokens ?? 16384     // :778-780
getCompactionKeepRecentTokens(): this.settings.compaction?.keepRecentTokens ?? 20000  // :782-784
```

`contextWindow` 来自模型元数据：`this.model?.contextWindow ?? 0`（`core/agent-session.ts:1959`），为 0 时 `getContextUsage()` 直接返回 `undefined`（`:3168-3169`）。

### 2.3 给用户看的余量：`getContextUsage()`

`core/agent-session.ts:3164-3208`，返回 `ContextUsage { tokens: number|null, contextWindow: number, percent: number|null }`（类型定义 `core/extensions/types.ts:288-294`）。

关键设计（`:3171-3198`）：**刚压缩完、还没有新的 assistant 回复时，`tokens` 返回 `null` 而不是猜一个数**：

```ts
// After compaction, the last assistant usage reflects pre-compaction context size.
// We can only trust usage from an assistant that responded after the latest compaction.
if (!hasPostCompactionUsage) return { tokens: null, contextWindow, percent: null };   // :3195-3197
```

### 2.4 SDK 路径

`packages/agent/src/harness/compaction/compaction.ts:174-178` 常量**完全相同**（16384 / 20000），`shouldCompact` 在 `:263-265`，`estimateTokens` 在 `:287`，`ESTIMATED_IMAGE_CHARS = 4800` 在 `:268`。**两套实现是逐字复制的双胞胎。**

---

## 3. Compaction 完整实现

### 3.1 触发：3 种 reason，2 个调用点

触发函数 `AgentSession._checkCompaction(assistantMessage, skipAbortedCheck = true)` —— `core/agent-session.ts:1953`。文档注释在 `:1942-1951`：

```
Check if compaction is needed and run it.
Called after agent_end and before prompt submission.
1. Overflow: LLM returned context overflow error, remove error message from agent state, compact, auto-retry
2. Threshold: Context over threshold, compact, NO auto-retry (user continues manually)
```

两个调用点：`agent-session.ts:1096`（agent_end 后，`skipAbortedCheck` 默认 true）与 `:1201`（提交新 prompt 前，传 `false` —— **连被用户 Ctrl-C 中断的消息也纳入判定**）。

| reason | 条件 | 行号 |
|---|---|---|
| `manual` | 用户敲 `/compact` → `AgentSession.compact()` | 类型定义见 `core/extensions/types.ts` `CompactOptions:296-300` |
| `overflow` | `sameModel && isContextOverflow(assistantMessage, contextWindow)` | `:1983` |
| `threshold` | `shouldCompact(contextTokens, contextWindow, settings)` | `:2038-2040` |

**三道防重复触发的护栏**（都值得单独讲）：

1. **换模型豁免**（`:1968-1969`）：`sameModel = provider 相等 && model.id 相等`。从小窗模型切到大窗模型时，旧模型的 overflow 错误不再触发压缩。
2. **压缩边界时间戳比较**（`:1971-1977`）：
   ```ts
   const compactionEntry = getLatestCompactionEntry(this.sessionManager.getBranch());   // :1971
   const assistantIsFromBeforeCompaction =
       compactionEntry !== null && assistantMessage.timestamp <= new Date(compactionEntry.timestamp).getTime();
   if (assistantIsFromBeforeCompaction) return false;   // :1975-1977
   ```
3. **overflow 只救一次**（`:1992-2001`）：`this._overflowRecoveryAttempted` 标志位；第二次直接给用户
   `"Context overflow recovery failed after one compact-and-retry attempt. Try reducing context or switching to a larger-context model."`

阈值分支里还有第 4 道护栏（`:2018-2036`）：当最后一条 assistant 是 `error` 或 usage 全零时，回退到 `estimateContextTokens`，但**必须验证 usage 的来源在压缩边界之后**，否则「保留下来的旧消息带着压缩前的大 usage」会让刚压完就再压一次（`:2025-2033`）。

### 3.2 切点算法：先估 token，再吸附到合法切点

`findCutPoint(entries, startIndex, endIndex, keepRecentTokens)` —— `core/compaction/compaction.ts:403-465`，算法注释在 `:388-401`。

流程：
1. `findValidCutPoints`（`:351-363`）先扫出所有**合法**切点索引；
2. 从最新往回累加 `estimateTokens`（`:419-427`），`accumulatedTokens >= keepRecentTokens`（`:431`）即停；
3. 从停下的位置往后找**最近的合法切点**（`:433-438`）；
4. 再往前吸附相邻的「不进 context 的元数据条目」（`:445-452`，如 `label` / `custom`），避免把它们留在被丢弃的一侧；
5. 判断是否劈开了一个 turn（`:455-457`）。

**合法切点的白名单/黑名单**（`:308-321`）—— 这段代码本身就是一张 PPT：

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

另有一张更严的 `isTurnStartMessage`（`:323-335`）—— **`assistant` 和 `toolResult` 都不算轮首**，只有 `user` / `bashExecution` / `custom` / `branchSummary` / `compactionSummary` 才是。

`findValidCutPoints` 的注释直白（`:346-350`）：

> "Never cut at tool results (they must follow their tool call). When we cut at an assistant message with tool calls, its tool results follow it and will be kept."

若切点不在轮首 → `findTurnStartIndex`（`:369-376`）回溯到轮首，标记 `isSplitTurn`（`CutPointResult`，`:378-386`），被劈开的那半个 turn 额外生成一段 **turn prefix summary** —— **即一次压缩可能发两次 LLM 请求**。

### 3.3 保留什么 / 丢弃什么

`prepareCompaction(pathEntries, settings)` —— `compaction.ts:710-786`，是个**纯函数**（不发请求、不写盘）：

- **前置短路**（`:714-716`）：路径最后一条已经是 `compaction` → 返回 `undefined`，不重复压。
- **上一次压缩边界**（`:718-731`）：从后往前找上一个 `compaction` 条目，取其 `firstKeptEntryId` 作为 `boundaryStart`，其 `summary` 作为 `previousSummary`。**压缩只在「上次边界 → 现在」这个窗口内工作，不会重新读整个历史。**
- **丢弃**：`messagesToSummarize` = `[boundaryStart, historyEnd)`（`:748-752`）
- **额外摘要**：`turnPrefixMessages` = `[turnStartIndex, firstKeptEntryIndex)`，仅 split turn 时（`:755-760`）
- **保留**：`firstKeptEntryId` 起的全部尾部条目
- **旧数据一条都不删** —— session 文件 append-only，只是读路径不再走到它们（见 3.6）

**文件操作清单**跨压缩累积（`:766-772` + `extractFileOperations`，`:39-67`）：从被丢弃消息的 tool call 里抽 read/edited 文件路径，**并合并上一次 `CompactionEntry.details` 里的清单**（`:47-60`，仅当 `!prevCompaction.fromHook`）。最终以 `<read-files>` / `<modified-files>` 两个 XML 块拼到摘要末尾（`core/compaction/utils.ts:72-82`）。

> 上 PPT 的点：**「摘要会忘，文件路径不忘」—— 文件清单是结构化字段，逐次压缩累积，不经过 LLM 转写。**

### 3.4 用不用 LLM：用，而且用得很克制

用。`compact()` —— `compaction.ts:817-916`。

**4 个固定 prompt，全部是源码里的字符串字面量**：

| 常量 | 行号 | 用途 |
|---|---|---|
| `SUMMARIZATION_SYSTEM_PROMPT` | `core/compaction/utils.ts:156-158` | 摘要调用的 system prompt |
| `SUMMARIZATION_PROMPT` | `compaction.ts:467-498` | 首次压缩，6 段固定格式 |
| `UPDATE_SUMMARIZATION_PROMPT` | `compaction.ts:500-537` | 有 `previousSummary` 时的迭代合并 |
| `TURN_PREFIX_SUMMARIZATION_PROMPT` | `compaction.ts:795-809` | split turn 的前半段 |

`SUMMARIZATION_SYSTEM_PROMPT` 全文只有 3 句，最后两句是防越狱式的硬约束：

```
You are a context summarization assistant. Your task is to read a conversation between a user and an AI assistant, then produce a structured summary following the exact format specified.

Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary.
```

`SUMMARIZATION_PROMPT` 的固定 6 段（`:471-495`）：

```
## Goal
## Constraints & Preferences
## Progress   →  ### Done / ### In Progress / ### Blocked
## Key Decisions
## Next Steps
## Critical Context
```
结尾硬约束（`:497`）：`Keep each section concise. Preserve exact file paths, function names, and error messages.`

**迭代合并的选择只有一行**（`compaction.ts:643`）：

```ts
let basePrompt = previousSummary ? UPDATE_SUMMARIZATION_PROMPT : SUMMARIZATION_PROMPT;
```

`UPDATE_SUMMARIZATION_PROMPT` 的 6 条规则（`:503-509`）：`PRESERVE all existing information` / `ADD new progress…` / `UPDATE the Progress section: move items from "In Progress" to "Done" when completed` / `UPDATE "Next Steps"` / `PRESERVE exact file paths, function names, and error messages` / `If something is no longer relevant, you may remove it`。

**三个把摘要本身的成本按住的机制**：

1. **对话被序列化成文本再塞进一条 user 消息**（`:648-666`），不是把原始 messages 数组直接发过去 —— 注释写得很直白（`:646`）：`Serialize conversation to text so model doesn't try to continue it`。
2. **序列化时工具结果被截到 2000 字符**（`core/compaction/utils.ts:89`、`:144`）：
   ```ts
   const TOOL_RESULT_MAX_CHARS = 2000;                                       // :89
   parts.push(`[Tool result]: ${truncateForSummary(content, TOOL_RESULT_MAX_CHARS)}`);   // :144
   ```
3. **maxTokens 与 reserveTokens 挂钩**：主摘要 `Math.floor(0.8 * reserveTokens)`（`:636-639` → 13 107），turn prefix 摘要 `Math.floor(0.5 * reserveTokens)`（`:936-939` → 8 192），两者都再对 `model.maxTokens` 取 min。

split turn 时两段摘要的拼法（`:880`）：

```ts
summary = `${historyText}\n\n---\n\n**Turn Context (split turn):**\n\n${turnPrefixResult.text}`;
```

**扩展可以完全接管**：`session_before_compact` 钩子（`agent-session.ts:2079-2105`）既能 `cancel`（`:2090-2099`），也能直接提供整份 `CompactionResult`（`:2101-2104`）跳过 LLM。

### 3.5 压缩产物怎么回灌 —— 关键 4 行

`core/agent-session.ts:2153-2157`：

```ts
this.sessionManager.appendCompaction(summary, firstKeptEntryId, tokensBefore, details, fromExtension, usage);  // :2153
const newEntries = this.sessionManager.getEntries();                       // :2154
const sessionContext = this.sessionManager.buildSessionContext();          // :2155  ★ 从 session 树重建
this.agent.state.messages = sessionContext.messages;                       // :2156  ★ 整体替换内存态
const estimatedTokensAfter = estimateMessagesTokens(sessionContext.messages);  // :2157
```

> **这就是回灌的全部**：写一条 `compaction` 条目进 session 文件 → 从 session 树重新算一遍 context → **整个替换** `agent.state.messages`。没有增量 patch，没有 diff。**session 文件是唯一真相源，内存态只是它的投影。**

`willRetry` 时还会摘掉尾部那条 error assistant（`:2184-2191`）：

```ts
if (willRetry) {
	const messages = this.agent.state.messages;
	const lastMsg = messages[messages.length - 1];
	if (lastMsg?.role === "assistant" && (lastMsg as AssistantMessage).stopReason === "error") this.agent.state.messages = messages.slice(0, -1);
	return true;
}
```

### 3.6 投影链路：compaction 条目 → LLM 里的一条 user 消息

三跳，每跳都能查到行号：

**第 1 跳** `buildContextEntries`（`core/session-manager.ts:418-454`）—— 沿 `parentId` 回溯出路径，取路径上**最后一个** compaction，重排成「compaction 条目在最前 + 从 `firstKeptEntryId` 起的保留段 + compaction 之后的全部」：

```ts
const contextEntries: SessionEntry[] = [compaction];                        // :441
for (let i = 0; i < compactionIdx; i++) {
	if (path[i].id === compaction.firstKeptEntryId) foundFirstKept = true;   // :445-447
	if (foundFirstKept) contextEntries.push(path[i]);                        // :448-450
}
contextEntries.push(...path.slice(compactionIdx + 1));                       // :452
```

**第 2 跳** `sessionEntryToContextMessages`（`session-manager.ts:383-411`）：`compaction` 条目 → 一条伪 role 消息 `compactionSummary`（`createCompactionSummaryMessage`，`core/messages.ts:110-122`）。

**第 3 跳** `convertToLlm`（`core/messages.ts:148-194`）：`compactionSummary` 伪 role → **一条普通 `user` 消息**（`:176-183`）：

```ts
case "compactionSummary":
	return { role: "user", content: [{ type: "text", text: COMPACTION_SUMMARY_PREFIX + m.summary + COMPACTION_SUMMARY_SUFFIX }], timestamp: m.timestamp };
```

包裹文案（`core/messages.ts:11-17`）：

```ts
export const COMPACTION_SUMMARY_PREFIX = `The conversation history before this point was compacted into the following summary:

<summary>
`;
export const COMPACTION_SUMMARY_SUFFIX = `
</summary>`;
```

> 上 PPT 的点：**LLM 眼里根本没有「compaction」这个概念 —— 它只看到一条 user 消息说「之前的历史被压成了这个 `<summary>`」。所有树结构、边界指针、伪 role 都止步于 `convertToLlm`。**

### 3.7 SDK 路径

`packages/agent/src/harness/compaction/compaction.ts` 是产品路径的逐字复制版（常量 `:174-178`、`shouldCompact:263`、`estimateTokens:287`、`findCutPoint` 附近 `:413`）。差别在**触发权**：`AgentHarness` 只提供显式 `compact()`，**没有自动触发** —— 决策留给宿主。

---

## 4. SKILL 机制：渐进式披露

### 4.1 结构体定义与字段

`packages/coding-agent/src/core/skills.ts:74-81`：

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

**6 个字段。**

frontmatter 结构体 `SkillFrontmatter`（`skills.ts:67-72`）只认 3 个字段（外加 `[key: string]: unknown` 兜底）：

```ts
export interface SkillFrontmatter {
	name?: string;
	description?: string;
	"disable-model-invocation"?: boolean;
	[key: string]: unknown;
}
```

字段来源（`skills.ts:309-318`）：

```ts
return { skill: {
	name,                                                                    // :311 缺省取父目录名，见 :296
	description: frontmatter.description,                                    // :312
	filePath,                                                                // :313
	baseDir: skillDir,                                                       // :314
	sourceInfo: createSkillSourceInfo(filePath, skillDir, source),           // :315
	disableModelInvocation: frontmatter["disable-model-invocation"] === true, // :316
}, diagnostics };
```

`description` 是**硬性必填**（`skills.ts:304-307`）：

```ts
// Still load the skill even with warnings (unless description is completely missing)
if (!frontmatter.description || frontmatter.description.trim() === "") {
	return { skill: null, diagnostics };
}
```

`name` 缺省取父目录名（`skills.ts:296`）：`const name = frontmatter.name || parentDirName;`

### 4.2 「Skill 没有 content 字段」—— 在新 commit 上复核：**成立**

> **复核结论：第一篇的结论在 `583f153` 上依然成立，且行号未变。**

产品路径 `Skill` 接口 `packages/coding-agent/src/core/skills.ts:74-81`（上引）**没有 `content` 字段**。

```bash
$ sed -n '74,81p' packages/coding-agent/src/core/skills.ts   # 6 个字段，无 content
```

三条支撑证据：

**证据 A —— 注入 system prompt 的只有 3 个 XML 字段**（`skills.ts:335-361`）：

```ts
export function formatSkillsForPrompt(skills: Skill[]): string {
	const visibleSkills = skills.filter((s) => !s.disableModelInvocation);        // :336
	const lines = [
		"\n\nThe following skills provide specialized instructions for specific tasks.",
		"Use the read tool to load a skill's file when the task matches its description.",   // ★ 明确指示用 read 工具
		"When a skill file references a relative path, resolve it against the skill directory …",
		"", "<available_skills>",
	];                                                                            // :342-348
	for (const skill of visibleSkills) {
		lines.push("  <skill>");
		lines.push(`    <name>${escapeXml(skill.name)}</name>`);                   // :352
		lines.push(`    <description>${escapeXml(skill.description)}</description>`);  // :353
		lines.push(`    <location>${escapeXml(skill.filePath)}</location>`);       // :354
```

注释里还标了标准出处（`skills.ts:329`）：`See: https://agentskills.io/integrate-skills`。

**证据 B —— 整个 skills 段的注入条件是「read 工具在场」**（`core/system-prompt.ts:154-156`）：

```ts
// Append skills section (only if read tool is available)
if (hasRead && skills.length > 0) prompt += formatSkillsForPrompt(skills);
```

没有 `read` 工具就不列 skills —— 因为模型没法把正文拉进来，列了也是浪费 token。

**证据 C —— 正文的唯一「pi 主动读盘」入口是显式斜杠命令**（`core/agent-session.ts:1301-1325`）：

```ts
private _expandSkillCommand(text: string): string {
	if (!text.startsWith("/skill:")) return text;                                 // :1302
	const skill = this.resourceLoader.getSkills().skills.find((s) => s.name === skillName);  // :1308
	if (!skill) return text;
	const content = readFileSync(skill.filePath, "utf-8");                        // :1312  ★ 此刻才读盘
	const body = stripFrontmatter(content).trim();                                // :1313
	const skillBlock = `<skill name="${skill.name}" location="${skill.filePath}">\nReferences are relative to ${skill.baseDir}.\n\n${body}\n</skill>`;  // :1314
	return args ? `${skillBlock}\n\n${args}` : skillBlock;                        // :1315
}
```

调用点：`agent-session.ts:1154`（提交 prompt 前展开）。

### 4.3 实测：渐进式披露省了多少

以 pi 自己仓库唯一的 skill `.pi/skills/add-llm-provider.md` 为例：

```bash
$ node -e '<按 formatSkillsForPrompt 的逐字模板复刻>'
skills 段头 chars= 348
单个 skill 条目 chars= 380
段尾 </available_skills> chars= 20
该 skill 正文全文 chars= 3097  ~tok= 775
常驻/全文 比 = 12.3%
```

> **常驻上下文只有 380 字符（≈95 token），正文 3 097 字符（≈775 token）。压缩比 8:1。** 而且**零额外工具槽位** —— 加载靠的是已有的 `read` 工具，不新增任何 tool schema。

### 4.4 目录发现规则

`core/skills.ts:160-167` 的注释就是规范（**代码即文档**）：

```
Discovery rules:
- if a directory contains SKILL.md, treat it as a skill root and do not recurse further
- otherwise, load direct .md children in the root
- recurse into subdirectories to find SKILL.md
```

默认目录（`skills.ts:431-432`）：

```ts
addSkills(loadSkillsFromDirInternal(join(resolvedAgentDir, "skills"), "user", true));                        // ~/.pi/agent/skills
addSkills(loadSkillsFromDirInternal(resolve(resolvedCwd, CONFIG_DIR_NAME, "skills"), "project", true));      // <cwd>/.pi/skills
```

CLI `--skill <path>` / settings 指定的路径在 `skills.ts:466`。

### 4.5 SDK 路径：**有** content，但注入行为一致

`packages/agent/src/harness/types.ts:64-75` 的 `Skill` **有** `content: string`（`:70`，注释 `Full skill instructions.`），共 5 个字段：`name` / `description` / `content` / `filePath` / `disableModelInvocation?`。

但 `formatSkillsForSystemPrompt`（`packages/agent/src/harness/system-prompt.ts:3-25`）注入的**仍然只有 name/description/location 三元组**（`:17-19`），正文不进 system prompt。措辞略有差别：harness 版第 2 句是 `"Read the full skill file when the task matches its description."`（`:10`），产品版是 `"Use the read tool to load a skill's file when the task matches its description."`（`skills.ts:344`）—— **产品版点名了工具，harness 版不假设有哪个工具。**

> 结论：**两条路径的 progressive disclosure 语义一致**；harness 把正文缓存在内存里只是为了让宿主能自己拼（`formatSkillInvocation`），并没有塞进 prompt。

---

## 5. 上下文里的「隐性占用」

### 5.1 工具 schema：实测 2 724 字符 / ≈681 token

序列化口径见 `packages/ai/src/api/anthropic-messages.ts:1297-1322`。注意 **非 strict 模式下只发 `{type, properties, required}` 三件套**，TypeBox schema 上的其它字段被丢掉：

```ts
const legacyInputSchema = { type: "object" as const, properties: schema.properties ?? {}, required: schema.required ?? [] };  // :1300-1304
const inputSchema = strict === true ? { ...(tool.parameters as Record<string, unknown>), ...legacyInputSchema } : legacyInputSchema;  // :1305-1311
return { name: ..., description: tool.description, ..., input_schema: inputSchema, ... };   // :1313-1321
```

按这个口径复刻 4 个默认工具（描述与参数描述全部逐字抄自 `core/tools/{read,bash,edit,write}.ts`），脚本 `scratchpad/p05-toolpayload.mjs`：

```bash
$ node p05-toolpayload.mjs
read	655 chars	~164 tok(chars/4)
bash	513 chars	~129 tok(chars/4)
edit	1150 chars	~288 tok(chars/4)
write	401 chars	~101 tok(chars/4)
TOTAL(4 tools)	2724 chars	~681 tok
```

**`edit` 一个工具就占了 42%** —— 它的 description 326 字符 + `edits[]` 数组描述 236 字符 + `oldText` 描述 154 字符，全是在教模型「别写重叠的 edit」。加上它在 system prompt 里贡献的 4 条 guideline（496 字符），**edit 相关文案总计 ≈1 650 字符 / 410 token，是 pi 上下文里最贵的单一概念。**

### 5.2 环境信息：**只有一行 cwd**

```bash
$ grep -rn "Current working directory" packages/coding-agent/src/core/system-prompt.ts
69:		prompt += `\nCurrent working directory: ${promptCwd}`;
159:	prompt += `\nCurrent working directory: ${promptCwd}`;
```

`system-prompt.ts` 里**没有** `process.platform`、`new Date()`、git 状态、目录树、shell 版本 —— 一个都没有。

```bash
$ grep -n "platform\|new Date()\|<env>" packages/coding-agent/src/core/system-prompt.ts packages/agent/src/harness/system-prompt.ts
# （无输出）
```

模型想知道日期/系统/git 状态？**自己调 `bash`。** 相关的唯一提示是 bash 工具的 guideline（`core/tools/bash.ts:329-331`）：`"Inspect PI_* environment variables for current model and session details."` —— 即模型/会话信息通过**子进程环境变量**暴露，不占上下文。

> 上 PPT 的点：**pi 的环境信息注入量 = 1 行。**这是与主流 coding agent 差异最大的一处设计选择。

### 5.3 provider 层偷偷加的东西

**OAuth token 时，system 数组的第 0 块不是 pi 写的**（`packages/ai/src/api/anthropic-messages.ts:975-991`）：

```ts
if (isOAuthToken) {
	params.system = [{ type: "text", text: "You are Claude Code, Anthropic's official CLI for Claude.", ...(cacheControl ? { cache_control: cacheControl } : {}) }];   // :976-983
	if (context.systemPrompt) params.system.push({ type: "text", text: sanitizeSurrogates(context.systemPrompt), ... });   // :984-990
}
```

同文件 `:996` 还有 `const claudeCodeVersion = "2.1.75";` 与工具名改写 `toClaudeCodeName(tool.name)`（`:1314`）—— 注释直接写 `Stealth mode: Mimic Claude Code's tool naming exactly`（`:995`）。

**Prompt cache 断点位置**（同文件）：
- system block 上（`:981`、`:988`、`:997`）
- **最后一个 tool 上**（`:1320`）：`...(cacheControl && index === tools.length - 1 ? { cache_control: cacheControl } : {})`
- 最后一条 user 消息上（`:1256-1275`，注释 `Add cache_control to the last user message to cache conversation history`）

默认 retention 为 `"short"`（`:49-57`），`PI_CACHE_RETENTION=long` 且模型支持时用 `ttl: "1h"`（`:68-72`）。

> 上 PPT 的点：**「tools 数组的最后一项挂 cache breakpoint」= 前缀 system + 全部 tool schema 一次性缓存。这也解释了为什么 pi 敢把 tool description 写这么长 —— 它只在 cache miss 时全价计费。**

### 5.4 文件快照：**没有**

pi 不做「文件快照 / 自动附带项目结构 / 自动 git diff」。上下文里跟文件有关的只有三样：

1. `read` / `bash` 工具的返回值，**截断到 2000 行或 50KB**（`core/tools/truncate.ts:11-12`）：
   ```ts
   export const DEFAULT_MAX_LINES = 2000;
   export const DEFAULT_MAX_BYTES = 50 * 1024; // 50KB
   ```
   超出部分写临时文件，只在结果里附一行路径（`core/messages.ts:94-96`：`[Output truncated. Full output: ${msg.fullOutputPath}]`）。
2. `!cmd` 的 bash 执行结果（`bashExecution` 伪 role），**`!!` 前缀的显式排除**（`core/messages.ts:152-155`：`if (m.excludeFromContext) return undefined;`）。
3. compaction 累积的 `<read-files>` / `<modified-files>` 清单（见 3.3）。

图片按 4 800 字符 / ≈1 200 token 记账（`core/compaction/compaction.ts:244`）。

---

## 6. AGENTS.md / 项目上下文文件的发现与注入

### 6.1 候选文件名：4 个，命中即止

`core/resource-loader.ts:70-89`：

```ts
function loadContextFileFromDir(dir: string): { path: string; content: string } | null {
	const candidates = ["AGENTS.md", "AGENTS.MD", "CLAUDE.md", "CLAUDE.MD"];      // :71
	for (const filename of candidates) {
		const filePath = join(dir, filename);
		if (existsSync(filePath)) {
			if (!statSync(filePath).isFile()) continue;                            // :76-78  防目录同名
			return { path: filePath, content: readFileSync(filePath, "utf-8") };   // :79-82
		}
	}
	return null;
}
```

**每个目录最多贡献一份**，`AGENTS.md` 优先于 `CLAUDE.md`。

### 6.2 发现顺序：global 先，祖先链后（外 → 内）

`core/resource-loader.ts:118-156`：

```ts
const globalContext = loadContextFileFromDir(resolvedAgentDir);      // :128  ~/.pi/agent/ 先 push
if (globalContext) { contextFiles.push(globalContext); seenPaths.add(globalContext.path); }   // :129-132
const shadowedContextFile = findShadowedContextFile(resolvedCwd);    // :136
let currentDir = resolvedCwd;
while (true) {
	const contextFile = loadContextFileFromDir(currentDir);
	const isShadowed = shadowedContextFile !== undefined && canonicalizePath(contextFile?.path ?? "") === shadowedContextFile;  // :141-142
	if (contextFile && !isShadowed && !seenPaths.has(contextFile.path)) ancestorContextFiles.unshift(contextFile);  // :143-146  ★ unshift
	const parentDir = dirname(currentDir); if (parentDir === currentDir) break; currentDir = parentDir;   // :148-150
}
contextFiles.push(...ancestorContextFiles);   // :153
```

`unshift` + `push` 的组合决定了最终顺序：**global → 最外层祖先 → … → cwd**。即**离 cwd 越近的 AGENTS.md 在 prompt 里越靠后**（LLM 通常更重视后出现的指令）。**注意：没有去重合并、没有覆盖语义 —— 全部原文并列注入。**

### 6.3 git worktree 去重：`findShadowedContextFile`

`core/resource-loader.ts:100-116`，解决「嵌套 worktree 时主仓库那份 AGENTS.md 被加载两次」的问题。注释里连 macOS symlink 和 bare 布局都点名了（`:96-113`）：

```ts
const commonGitDir = canonicalizePath(gitPaths.commonGitDir);                                   // :103
const worktreeRoot = canonicalizePath(gitPaths.repoDir);                                        // :104
const mainRepoRoot = dirname(commonGitDir);                                                     // :105
if (!worktreeRoot.startsWith(`${mainRepoRoot}${sep}`)) return undefined;                        // :108  兄弟 worktree 不算
if (canonicalizePath(join(mainRepoRoot, ".git")) !== commonGitDir) return undefined;            // :113  bare 布局 / submodule 不算
const worktreeContextFile = loadContextFileFromDir(worktreeRoot);
return worktreeContextFile ? join(mainRepoRoot, basename(worktreeContextFile.path)) : undefined; // :114-115
```

注释原文（`:96-98`）：`Returned canonicalized (realpath), because git worktree add writes the .git file's gitdir: target in realpath form while cwd may still be symlinked (macOS /tmp -> /private/tmp).`

### 6.4 注入格式与开关

注入（`core/system-prompt.ts:144-152`）：

```ts
prompt += "\n\n<project_context>\n\n";
prompt += "Project-specific instructions and guidelines:\n\n";
for (const { path: filePath, content } of contextFiles) {
	prompt += `<project_instructions path="${filePath}">\n${content}\n</project_instructions>\n\n`;
}
prompt += "</project_context>\n";
```

**总开关**：`--no-context-files` / `-nc`（`packages/coding-agent/src/cli/args.ts:171-172`，帮助文本 `:289` "Disable AGENTS.md and CLAUDE.md discovery and loading"），落到 `core/resource-loader.ts:514-521`：

```ts
const agentsFiles = { agentsFiles: this.noContextFiles ? [] : loadProjectContextFiles({ cwd: this.cwd, agentDir: this.agentDir }) };
```

SDK 侧还有 `agentsFilesOverride` 钩子（`:522`）可以整体改写。

### 6.5 ★ AGENTS.md **不受 trust 门禁**

这是取证过程中最反直觉的一条。

`.pi/SYSTEM.md` 与 `.pi/APPEND_SYSTEM.md` **要求项目已被信任**（`core/resource-loader.ts:1022-1048`）：

```ts
private discoverSystemPromptFile(): string | undefined {
	const projectPath = join(this.cwd, CONFIG_DIR_NAME, "SYSTEM.md");
	if (this.settingsManager.isProjectTrusted() && existsSync(projectPath)) return projectPath;   // :1024
	const globalPath = join(this.agentDir, "SYSTEM.md");
	if (existsSync(globalPath)) return globalPath;                                                 // :1029
	return undefined;
}
```

而 `loadProjectContextFiles`（`:118-156`）**签名里根本没有 trust 参数**，调用点（`:514-521`）也只看 `noContextFiles`。

更进一步：需要触发信任提示的资源清单里**没有 AGENTS.md**（`core/trust-manager.ts:29-37`）：

```ts
const TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES = [
	"settings.json", "extensions", "skills", "prompts", "themes", "SYSTEM.md", "APPEND_SYSTEM.md",
] as const;
```

`hasTrustRequiringProjectResources(cwd)`（`trust-manager.ts:184-206`）只检查 `<cwd>/.pi/` 下的这 7 项 + 祖先链上的 `.agents/skills`。

> **后果**：clone 一个只有 `AGENTS.md` 的陌生仓库并在里面跑 `pi`，**不会弹信任提示**，但那份 `AGENTS.md` 的全文会原封不动进 system prompt。这是 prompt injection 的一条现成入口，**必须上 PPT 的安全提醒**。

---

## 7. 两条路径速查表

| 维度 | 产品路径 `coding-agent` | SDK 路径 `agent/harness` |
|---|---|---|
| system prompt 模板 | 内置 9 段（`core/system-prompt.ts:121-159`） | 无，调用方传入（`harness/agent-harness.ts:405-416`），兜底 `"You are a helpful assistant."` |
| skills 格式化 | `core/skills.ts:335-361` | `harness/system-prompt.ts:3-25` |
| `Skill.content` | **无**（`core/skills.ts:74-81`，6 字段） | **有**（`harness/types.ts:64-75`，`:70`） |
| 压缩常量 | 16384 / 20000（`core/compaction/compaction.ts:132-136`） | 16384 / 20000（`harness/compaction/compaction.ts:174-178`） |
| `shouldCompact` | `core/compaction/compaction.ts:235-238` | `harness/compaction/compaction.ts:263-265` |
| `estimateTokens` | `core/compaction/compaction.ts:266` | `harness/compaction/compaction.ts:287` |
| 自动触发压缩 | 有（`core/agent-session.ts:1953`） | **无**，只有显式 `compact()` |
| AGENTS.md 发现 | `core/resource-loader.ts:118-156` | 无内置，靠宿主 |

---

## 8. 最适合上 PPT 的 5 条硬事实

1. **pi 的「自带上下文」只有 ≈1 311 token：system prompt 骨架 630 + 4 个工具 schema 681。**
   （复刻 `core/system-prompt.ts:121-159` 实测 2 520 字符；按 `packages/ai/src/api/anthropic-messages.ts:1297-1322` 口径复刻 tools 实测 2 724 字符。对比：pi 自己仓库的 `AGENTS.md` 就有 10 731 字符 / ≈2 683 token —— **项目自己的文件是 pi 内核的 2 倍**。）

2. **上下文超限阈值是一行绝对值减法，不是百分比：`contextTokens > contextWindow - 16384`。**
   （`core/compaction/compaction.ts:237`，常量在 `:132-136`。对 200K 窗口触发于 91.8%，对 1M 窗口触发于 98.4% —— **窗口越大越晚触发**。）

3. **Token 计数是「provider 真实 usage 打底 + chars/4 补尾巴」的混合口径，pi 从不本地跑 tokenizer。**
   （`estimateContextTokens`，`core/compaction/compaction.ts:202-227`；`estimateTokens` 的 chars/4 在 `:266-305`，注释自称 "conservative (overestimates)"；图片按固定 4 800 字符记账，`:244`。）

4. **`Skill` 结构体只有 6 个字段、确认没有 `content`（`core/skills.ts:74-81`，在 `583f153` 上复核成立）；常驻上下文每个 skill 只花 380 字符，正文 3 097 字符只在模型调 `read` 或用户敲 `/skill:` 时才进来 —— 8:1 压缩比，零额外工具槽位。**
   （注入格式 `skills.ts:335-361` 只有 name/description/location 三元组；注入条件 `core/system-prompt.ts:154-156` 是「read 工具在场」；显式读盘唯一入口 `core/agent-session.ts:1312`。）

5. **压缩产物的回灌只有 4 行，且不做增量 patch —— 写一条 compaction 条目进 session 文件，再从 session 树整体重建内存态；LLM 眼里它只是一条普通 user 消息。**
   （`core/agent-session.ts:2153-2156`；三跳投影 `session-manager.ts:418-454` → `:383-411` → `core/messages.ts:176-183`；包裹文案 `core/messages.ts:11-17`。切点绝不落在 `toolResult` 上：`core/compaction/compaction.ts:308-321`。）

**（附赠 · 安全向）** `.pi/SYSTEM.md` 要 trust 才加载，**但 `AGENTS.md` 不要**：信任清单 `core/trust-manager.ts:29-37` 里没有它，`loadProjectContextFiles`（`core/resource-loader.ts:118-156`）签名里也没有 trust 参数。**只带 `AGENTS.md` 的陌生仓库不弹信任提示，全文直接进 system prompt。**
