# P06：工具层——少而正交的四个工具

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `https://github.com/earendil-works/pi.git` | `git remote -v` |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | 版本 | `0.83.0` | `packages/coding-agent/package.json`、`packages/agent/package.json` |
> | 本地路径 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开验证。
> 行号会随上游提交漂移 —— PPT 引用时**必须带 commit 短 hash `583f153`**。

---

## 0. 先看代码体量：整个工具层多大

```bash
$ wc -l packages/coding-agent/src/core/tools/*.ts packages/agent/src/harness/tools/*.ts
```

**产品路径**（`packages/coding-agent/src/core/tools/`，15 个文件）：

| 文件 | 行数 | 作用 |
|---|---:|---|
| `bash.ts` | 505 | bash 工具（含 TUI 渲染） |
| `edit-diff.ts` | 560 | ★ 匹配/替换/diff **纯算法**，无 IO |
| `edit.ts` | 437 | edit 工具（含 TUI 渲染） |
| `write.ts` | 267 | write 工具 |
| `read.ts` | 351 | read 工具 |
| `grep.ts` | 385 | grep（ripgrep 后端） |
| `find.ts` | 374 | find（fd 后端） |
| `ls.ts` | 225 | ls |
| `truncate.ts` | 276 | ★ 全局截断策略（唯一常量出处） |
| `output-accumulator.ts` | 222 | bash 流式输出的有界内存累加器 |
| `index.ts` | 196 | 注册表 + 工厂 switch |
| `path-utils.ts` | 118 | 路径解析（含 macOS 截图文件名兜底） |
| `render-utils.ts` | 85 | — |
| `file-mutation-queue.ts` | 61 | ★ 同文件写操作串行化 |
| `tool-definition-wrapper.ts` | 47 | `ToolDefinition` → `AgentTool` 适配 |

**SDK 路径**（`packages/agent/src/harness/tools/`，10 个文件，共 1190 行）：`bash.ts 161` / `edit.ts 127` / `edit-diff.ts 500` / `read.ts 144` / `write.ts 39` / `image.ts 104` / `file-mutation-queue.ts 56` / `path-utils.ts 30` / `index.ts 23` / `tool-context.ts 6`。

> 上 PPT 的点：**一个能自己改代码的 agent，全部工具实现只有 4.1k 行**（产品路径 `4109` 行，含 TUI 渲染代码；纯逻辑不到一半）。

---

## 1. 工具总数、默认暴露几个、差额为什么不给

### 1.1 总数 = 7，唯一权威定义

`packages/coding-agent/src/core/tools/index.ts:83-84`：

```ts
export type ToolName = "read" | "bash" | "edit" | "write" | "grep" | "find" | "ls";
export const allToolNames: Set<ToolName> = new Set(["read", "bash", "edit", "write", "grep", "find", "ls"]);
```

`createToolDefinition()`（`index.ts:96-115`）是一个 7 分支 switch，`default` 直接 `throw new Error(\`Unknown tool name: ${toolName}\`)`（`:113`）——**没有动态注册的后门**，内置工具集是闭集。

同文件还提供三组预设（`index.ts:138-166`）：

```ts
createCodingToolDefinitions   // :138  read, bash, edit, write   ← 默认这一组
createReadOnlyToolDefinitions // :147  read, grep, find, ls      ← 只读场景
createAllToolDefinitions      // :156  全 7 个
```

### 1.2 默认激活 = 4

**两处硬编码，字面量完全一致**：

- `packages/coding-agent/src/core/agent-session.ts:2592-2594`
  ```ts
  const defaultActiveToolNames = this._baseToolsOverride
      ? Object.keys(this._baseToolsOverride)
      : ["read", "bash", "edit", "write"];
  ```
- `packages/coding-agent/src/core/sdk.ts:245`
  ```ts
  const defaultActiveToolNames: ToolName[] = ["read", "bash", "edit", "write"];
  ```

第三处是 system prompt 的兜底（`packages/coding-agent/src/core/system-prompt.ts:81`）：
```ts
const tools = selectedTools || ["read", "bash", "edit", "write"];
```

### 1.3 `grep` / `find` / `ls` 为什么不默认给——代码里的直接证据

**证据 A：system prompt 里有一条"没有它们就让模型用 bash"的条件 guideline**
`packages/coding-agent/src/core/system-prompt.ts:97-105`：

```ts
const hasBash  = tools.includes("bash");
const hasGrep  = tools.includes("grep");
const hasFind  = tools.includes("find");
const hasLs    = tools.includes("ls");
const hasRead  = tools.includes("read");

// File exploration guidelines
if (hasBash && !hasGrep && !hasFind && !hasLs) {
    addGuideline("Use bash for file operations like ls, rg, find");
}
```

即：**默认配置（4 工具）下这条 guideline 一定生效**，system prompt 明确告诉模型"用 bash 干 ls/rg/find"。三个工具不是"没做"，是"做了但让位给 bash"。

**证据 B：这三个工具本来就是 shell 子进程的包装，没有信息增量**

- `grep.ts:172` `const rgPath = await ensureTool("rg", true);`；`grep.ts:221` `spawn(rgPath, args, ...)`
- `find.ts:9` `import { ensureTool } from "../../utils/tools-manager.ts";`，同样 spawn `fd`
- 两者的 `description` 都写着 "Respects .gitignore"（`grep.ts:131`、`find.ts:117`）

也就是说 `grep`/`find` 相对 `bash "rg ..."` 唯一的额外价值是结构化截断参数，而 bash 已经有统一截断（见第 4 节）。**用 bash 覆盖它们，省下 3 个工具槽位和约 591 字符的描述预算**（实测：grep 221 + find 186 + ls 184 = 591 字符，见第 2 节表）。

**证据 C：官方文档明说这是"可选装"而非"缺失"**
`packages/coding-agent/README.md:584`：

> Available built-in tools: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`

`packages/coding-agent/src/cli/args.ts:352`（帮助文本里的示例，直接演示怎么切到只读四件套）：

```
pi --tools read,grep,find,ls -p "Review the code in src/"
```

### 1.4 怎么把它们打开（四条通路，全部实测行号）

| 通路 | 位置 | 说明 |
|---|---|---|
| CLI `--tools` / `-t` | `packages/coding-agent/src/cli/args.ts:122-126` | 逗号分隔白名单 |
| CLI `--exclude-tools` / `-xt` | `cli/args.ts:127-131` | 黑名单，在白名单之后生效 |
| CLI `--no-tools` / `--no-builtin-tools` | `cli/args.ts:118-121` → `main.ts:489-493` | `noTools = "all" \| "builtin"` |
| SDK `options.tools` | `core/sdk.ts:246-251` | 同上语义 |
| 扩展运行时改 | `core/extensions/types.ts:1337` `setActiveTools(toolNames)` → `agent-session.ts:2395` | 会话中途换工具集 |

`main.ts:488-499` 是 CLI → SDK 的映射：

```ts
// Tools
if (parsed.noTools) { options.noTools = "all"; }
else if (parsed.noBuiltinTools) { options.noTools = "builtin"; }
if (parsed.tools) { options.tools = [...parsed.tools]; }
if (parsed.excludeTools) { options.excludeTools = [...parsed.excludeTools]; }
```

### 1.5 SDK（harness）路径只有 4 个，且是硬边界

`packages/agent/src/harness/tools/index.ts`（整文件 23 行）只导出 `createBashTool` / `createEditTool` / `createReadTool` / `createWriteTool`。目录下**根本不存在** `grep.ts` / `find.ts` / `ls.ts`：

```bash
$ ls packages/agent/src/harness/tools/
bash.ts  edit-diff.ts  edit.ts  file-mutation-queue.ts  image.ts
index.ts  path-utils.ts  read.ts  tool-context.ts  write.ts
```

> **上 PPT 的一句话**：pi 把「7 个实现」和「4 个默认暴露」拆成两件事——**默认给模型的是一个正交基（读 / 写 / 改 / 执行），其余全部由 bash 张成**。

---

## 2. 每个工具的 schema 全文要点 + 实测字符数

### 2.1 实测方法

```bash
$ /usr/bin/python3 - <<'PY'
# 把 4 个 description 模板里的 ${DEFAULT_MAX_LINES}=2000、${DEFAULT_MAX_BYTES/1024}=50 代入后计 len()
PY
```

（脚本把 `truncate.ts:11-12` 的两个常量代入模板字符串，逐条 `len()`。）

### 2.2 结果表（字符数为实测）

| 工具 | `description` | `promptSnippet` | `promptGuidelines` | 参数描述合计 | 必填参数 | 可选参数 |
|---|---:|---:|---:|---:|---|---|
| `read` | **303** | 18 | 48（1 条） | 123（3 字段） | `path` | `offset`, `limit` |
| `bash` | **248** | 44 | 73（1 条） | 72（2 字段） | `command` | `timeout` |
| `edit` | **326** | 98 | **496（4 条）** | **468（4 字段）** | `path`, `edits[]` | — |
| `write` | **127** | 25 | 50（1 条） | 76（2 字段） | `path`, `content` | — |
| `grep` | 221 | 55 | 0 | — | `pattern` | `path`,`glob`,`ignoreCase`,`literal`,`context`,`limit` |
| `find` | 186 | 48 | 0 | — | `pattern` | `path`, `limit` |
| `ls` | 184 | 23 | 0 | — | — | `path`, `limit` |

- **7 个 description 合计 1595 字符**
- **默认 4 件套的全部提示预算（description + snippet + guidelines + 参数描述）= 2595 字符**，约 650 token 级别

> 对照参考：单个 `edit` 就吃掉 `326 + 98 + 496 + 468 = 1388` 字符，占默认四件套提示预算的 **53%**。**pi 把绝大部分描述预算压在最容易出错的那一个工具上。**

### 2.3 schema 全文（TypeBox，全仓无 Zod）

**read**（`core/tools/read.ts:20-24`，与 harness 版 `agent/src/harness/tools/read.ts:16-20` 一字不差）：

```ts
const readSchema = Type.Object({
    path:   Type.String({ description: "Path to the file to read (relative or absolute)" }),
    offset: Type.Optional(Type.Number({ description: "Line number to start reading from (1-indexed)" })),
    limit:  Type.Optional(Type.Number({ description: "Maximum number of lines to read" })),
});
```
description（`read.ts:212`，303 字符）：
> Read the contents of a file. Supports text files and images (jpg, png, gif, webp, bmp). Images are sent as attachments. For text files, output is truncated to 2000 lines or 50KB (whichever is hit first). Use offset/limit for large files. **When you need the full file, continue with offset until complete.**

**bash**（`core/tools/bash.ts:40-43`）：

```ts
const bashSchema = Type.Object({
    command: Type.String({ description: "Bash command to execute" }),
    timeout: Type.Optional(Type.Number({ description: "Timeout in seconds (optional, no default timeout)" })),
});
```

**edit**（`core/tools/edit.ts:33-53`）——**唯一嵌套 schema**：

```ts
const replaceEditSchema = Type.Object({
    oldText: Type.String({ description:
        "Exact text for one targeted replacement. It must be unique in the original file and must not overlap with any other edits[].oldText in the same call." }),
    newText: Type.String({ description: "Replacement text for this targeted edit." }),
}, {});

const editSchema = Type.Object({
    path:  Type.String({ description: "Path to the file to edit (relative or absolute)" }),
    edits: Type.Array(replaceEditSchema, { description:
        "One or more targeted replacements. Each edit is matched against the original file, not incrementally. Do not include overlapping or nested edits. If two changes touch the same block or nearby lines, merge them into one edit instead." }),
}, {});
```

**write**（`core/tools/write.ts:14-17`）：

```ts
const writeSchema = Type.Object({
    path:    Type.String({ description: "Path to the file to write (relative or absolute)" }),
    content: Type.String({ description: "Content to write to the file" }),
});
```

### 2.4 关键结构事实：**描述分三层**

`ToolDefinition` 里同时存在三个"给模型看的文本"字段：

| 字段 | 去处 | 位置 |
|---|---|---|
| `description` | 工具 JSON schema 里，随每次请求发给 provider | `tool-definition-wrapper.ts:12` |
| `promptSnippet` | system prompt 的 `Available tools:` 一行式清单 | `system-prompt.ts:80-84` |
| `promptGuidelines` | system prompt 的 `Guidelines:` 段，**Set 去重** | `system-prompt.ts:107-112` |

而且 **`promptSnippet` 决定工具是否出现在 system prompt 里，不是"是否注册"决定的**（`system-prompt.ts:80-84`）：

```ts
// A tool appears in Available tools only when the caller provides a one-line snippet.
const tools = selectedTools || ["read", "bash", "edit", "write"];
const visibleTools = tools.filter((name) => !!toolSnippets?.[name]);
const toolsList = visibleTools.length > 0 ? visibleTools.map((n) => `- ${n}: ${toolSnippets![n]}`).join("\n") : "(none)";
```

**harness 侧的四个工具全部没有 `promptSnippet` / `promptGuidelines`**（对比 `agent/src/harness/tools/bash.ts:55-58` 与 `coding-agent/src/core/tools/bash.ts:325-331`）——SDK 把 system prompt 完全交给宿主。

`bash` 的 `promptGuidelines` 还是**条件生成**的（`core/tools/bash.ts:329-331`）：

```ts
promptGuidelines: exposeSessionEnvironment
    ? ["Inspect PI_* environment variables for current model and session details."]
    : undefined,
```

---

## 3. `edit` 的匹配算法：到底是精确还是模糊

**结论：先精确、后模糊（两级），唯一性检查始终按模糊口径，多处命中直接报错不猜。**

算法全部在 `packages/coding-agent/src/core/tools/edit-diff.ts`（560 行，**纯函数、零 IO**）。

### 3.1 两级匹配（`edit-diff.ts:206-244`）

```ts
export function fuzzyFindText(content: string, oldText: string): FuzzyMatchResult {
    // Try exact match first
    const exactIndex = content.indexOf(oldText);                        // :208
    if (exactIndex !== -1) {
        return { found: true, index: exactIndex, matchLength: oldText.length,
                 usedFuzzyMatch: false, contentForReplacement: content };
    }

    // Try fuzzy match - work entirely in normalized space
    const fuzzyContent = normalizeForFuzzyMatch(content);               // :220
    const fuzzyOldText = normalizeForFuzzyMatch(oldText);               // :221
    const fuzzyIndex = fuzzyContent.indexOf(fuzzyOldText);              // :222
    if (fuzzyIndex === -1) { return { found: false, index: -1, ... }; } // :224-232
    return { found: true, index: fuzzyIndex, matchLength: fuzzyOldText.length,
             usedFuzzyMatch: true, contentForReplacement: fuzzyContent };
}
```

**注意：第一级和第二级都是 `String.prototype.indexOf`**——没有编辑距离、没有 diff 打分、没有行级对齐、没有 LLM 兜底。所谓"fuzzy"只是**一次确定性的字符归一化**。

### 3.2 "fuzzy"到底归一化了什么（`edit-diff.ts:33-54`）

```ts
export function normalizeForFuzzyMatch(text: string): string {
    return text
        .normalize("NFKC")
        .split("\n").map((line) => line.trimEnd()).join("\n")   // 每行去尾空白
        .replace(/[\u2018\u2019\u201A\u201B]/g, "'")            // 弯单引号 → '
        .replace(/[\u201C\u201D\u201E\u201F]/g, '"')            // 弯双引号 → "
        .replace(/[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]/g, "-")  // 各种破折号 → -
        .replace(/[\u00A0\u2002-\u200A\u202F\u205F\u3000]/g, " ");      // 各种特殊空格 → 空格
}
```

**五类，且仅此五类**：NFKC、行尾空白、智能引号、Unicode 连字符/破折号、特殊空格。缩进、大小写、行内空白数量**一律不放过**。

外层还先做了两道无损归一（`edit.ts:340-342`）：
```ts
const { bom, text: content } = stripBom(rawContent);   // 剥 UTF-8 BOM，写回时再加上（:346）
const originalEnding = detectLineEnding(content);      // 记住 CRLF/LF
const normalizedContent = normalizeToLF(content);      // 全部按 LF 匹配
```
注释写得很直白（`edit.ts:339`）：`// Strip BOM before matching. The model will not include an invisible BOM in oldText.`

### 3.3 多处命中怎么办：**报错，绝不选第一个**

`edit-diff.ts:325-343`（主循环）：

```ts
for (let i = 0; i < normalizedEdits.length; i++) {
    const edit = normalizedEdits[i];
    const matchResult = fuzzyFindText(replacementBaseContent, edit.oldText);
    if (!matchResult.found) {
        throw getNotFoundError(path, i, normalizedEdits.length);          // :329
    }
    const occurrences = countOccurrences(replacementBaseContent, edit.oldText);   // :332
    if (occurrences > 1) {
        throw getDuplicateError(path, i, normalizedEdits.length, occurrences);    // :334
    }
    matchedEdits.push({ editIndex: i, matchIndex: matchResult.index, ... });
}
```

**一条容易被忽略的硬事实**：`countOccurrences`（`edit-diff.ts:251-255`）**无条件走模糊归一化**——

```ts
function countOccurrences(content: string, oldText: string): number {
    const fuzzyContent = normalizeForFuzzyMatch(content);
    const fuzzyOldText = normalizeForFuzzyMatch(oldText);
    return fuzzyContent.split(fuzzyOldText).length - 1;
}
```

即使这次是**精确命中**，唯一性也按模糊口径判定。所以：**两段只差一个行尾空格的代码，会被判为"重复"而拒绝编辑**。这是刻意的保守——宁可让模型多给上下文，也不冒替错位置的风险。

### 3.4 多编辑的原子性与重叠检测

`applyEditsToNormalizedContent`（`edit-diff.ts:304-366`）的四道闸门，按顺序：

| 闸门 | 行号 | 行为 |
|---|---|---|
| ① `oldText` 为空 | `:314-318` | `throw getEmptyOldTextError` |
| ② 未命中 | `:328-330` | `throw getNotFoundError` |
| ③ 命中 >1 处 | `:332-335` | `throw getDuplicateError` |
| ④ **两个 edit 区间重叠** | `:345-354` | 排序后相邻比较，`throw` |
| ⑤ 替换后内容未变 | `:361-363` | `throw getNoChangeError` |

重叠检测代码（`:345-354`）：

```ts
matchedEdits.sort((a, b) => a.matchIndex - b.matchIndex);
for (let i = 1; i < matchedEdits.length; i++) {
    const previous = matchedEdits[i - 1];
    const current  = matchedEdits[i];
    if (previous.matchIndex + previous.matchLength > current.matchIndex) {
        throw new Error(
            `edits[${previous.editIndex}] and edits[${current.editIndex}] overlap in ${path}. Merge them into one edit or target disjoint regions.`);
    }
}
```

**全部 edit 都是对着「同一份原始内容」匹配的，不是逐条应用后再匹配下一条**（注释 `:295-302`）。替换按 `matchIndex` **逆序**施加，保证偏移稳定（`edit-diff.ts:110-119`）：

```ts
function applyReplacements(content: string, replacements: TextReplacement[], offset = 0): string {
    let result = content;
    for (let i = replacements.length - 1; i >= 0; i--) { ... }   // ★ 从后往前
}
```

**任一 edit 失败 → 整个 tool call 抛错 → 文件一个字节都不写**（`edit.ts:343` 抛出后 `:347` 的 `writeFile` 根本到不了）。这是**全或无**语义。

### 3.5 模糊命中时怎么保住"没改的行"

如果任意一条 edit 走了模糊路径，整批替换会在**模糊归一空间**里做，然后只把"真正被碰到的那些行"写回，其余行按原字节保留——`applyReplacementsPreservingUnchangedLines`（`edit-diff.ts:131-172`），入口在 `:356-359`：

```ts
const newContent = usedFuzzyMatch
    ? applyReplacementsPreservingUnchangedLines(normalizedContent, replacementBaseContent, matchedEdits)
    : applyReplacements(replacementBaseContent, matchedEdits);
```

注释（`:121-130`）说明了为什么要按"实际替换区间"扩展到整行再分组：

> The actual replacement ranges drive preservation so duplicate normalized lines cannot be aligned to the wrong occurrence.

**净效果：模糊匹配只会污染被编辑的那几行的空白/引号，文件其余部分逐字节不变。**

### 3.6 失败返回什么：**六种错误文案，全部带自愈提示**

`edit-diff.ts:257-293`，且**单编辑 / 多编辑两套措辞**（多编辑时点名 `edits[i]`）：

```ts
// :257-266 未找到
`Could not find the exact text in ${path}. The old text must match exactly including all whitespace and newlines.`
`Could not find edits[${editIndex}] in ${path}. The oldText must match exactly including all whitespace and newlines.`

// :268-277 多处命中
`Found ${occurrences} occurrences of the text in ${path}. The text must be unique. Please provide more context to make it unique.`
`Found ${occurrences} occurrences of edits[${editIndex}] in ${path}. Each oldText must be unique. Please provide more context to make it unique.`

// :279-284 空 oldText
`oldText must not be empty in ${path}.`   /   `edits[${editIndex}].oldText must not be empty in ${path}.`

// :286-293 无变化
`No changes made to ${path}. The replacement produced identical content. This might indicate an issue with special characters or the text not existing as expected.`
```

另外两条在别处：
- 文件不可读写：`edit.ts:330` `Could not edit file: ${path}. ${errorMessage}.`（`errorMessage` 形如 `Error code: ENOENT`）
- 参数结构不对：`edit.ts:122` `Edit tool input is invalid. edits must contain at least one replacement.`

成功文案（`edit.ts:356`）：`Successfully replaced ${edits.length} block(s) in ${path}.` —— **不回显 diff 全文给模型**，diff 只进 `details`（`:359`）给 TUI 渲染。

### 3.7 一个真实的"给模型擦屁股"的兼容层

`prepareEditArguments`（`edit.ts:94-118`）——注释直接点名了两个模型：

```ts
// Some models (Opus 4.6, GLM-5.1) send edits as a JSON string instead of an array
if (typeof args.edits === "string") {
    try { const parsed = JSON.parse(args.edits); if (Array.isArray(parsed)) args.edits = parsed; } catch {}
}
// 老式单编辑格式 { oldText, newText } → 归一成 edits[]
const legacy = args as LegacyEditToolInput;
if (typeof legacy.oldText !== "string" || typeof legacy.newText !== "string") return args as EditToolInput;
const edits = Array.isArray(legacy.edits) ? [...legacy.edits] : [];
edits.push({ oldText: legacy.oldText, newText: legacy.newText });
```

这个 hook 在 schema 校验**之前**跑（`packages/agent/src/agent-loop.ts:617-618`）：

```ts
const preparedToolCall = prepareToolCallArguments(tool, toolCall);
const validatedArgs = validateToolArguments(tool, preparedToolCall);
```

> 上 PPT 的点：**`prepareArguments` 是"在校验前修脏参数"的官方口子**，pi 用它兜住了具体模型的具体毛病，而不是放松 schema。

### 3.8 harness 版一模一样

`packages/agent/src/harness/tools/edit.ts`（127 行）的 schema（`:17-37`）、description（`:86`）、`prepareEditArguments`（`:48-64`）与产品版**逐字相同**，算法直接 `import` 自 harness 自己的 `edit-diff.ts`（500 行，去掉了 `computeEditsDiff` 预览函数）。差别只在 IO 抽象：产品版用 `fs/promises`，harness 版用 `env.readTextFile` / `env.writeFile`（`:100-112`）。

---

## 4. `bash`：超时 / 截断 / 进程模型 / cwd

### 4.1 超时：**默认没有超时**

schema 描述就明写（`core/tools/bash.ts:42`）：

```ts
timeout: Type.Optional(Type.Number({ description: "Timeout in seconds (optional, no default timeout)" })),
```

`resolveTimeoutMs`（`bash.ts:27-38`）：

```ts
function resolveTimeoutMs(timeout: number | undefined): number | undefined {
    if (timeout === undefined) return undefined;                                   // ★ 不设定时器
    if (!Number.isFinite(timeout) || timeout <= 0) throw new Error("Invalid timeout: must be a finite number of seconds");
    const timeoutMs = timeout * 1000;
    if (timeoutMs > MAX_TIMEOUT_MS) throw new Error(`Invalid timeout: maximum is ${MAX_TIMEOUT_SECONDS} seconds`);
    return timeoutMs;
}
```

上界（`bash.ts:24-25`）：`MAX_TIMEOUT_MS = 2_147_483_647`（32 位有符号上限，≈ **2147483.647 秒 ≈ 24.86 天**）。

超时动作是 **杀整棵进程树**，不是 `child.kill()`（`bash.ts:117-122`）：

```ts
if (timeoutMs !== undefined) {
    timeoutHandle = setTimeout(() => { timedOut = true; if (child.pid) killProcessTree(child.pid); }, timeoutMs);
}
```

超时后抛的是 `timeout:${timeout}`（`bash.ts:138`），在外层被翻译成给模型看的文案（`bash.ts:442-445`）：
```ts
if (err instanceof Error && err.message.startsWith("timeout:")) {
    const timeoutSecs = err.message.split(":")[1];
    throw new Error(appendStatus(text, `Command timed out after ${timeoutSecs} seconds`));
}
```
**注意 `appendStatus(text, ...)`：超时前已经产生的输出会一起回给模型**（`bash.ts:424`）。

### 4.2 输出截断阈值：2000 行 / 50KB，取先到者，**保尾**

唯一常量出处 `core/tools/truncate.ts:11-13`：

```ts
export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024;   // 50KB
export const GREP_MAX_LINE_LENGTH = 500;      // grep 单行上限
```

文件头注释就是规格说明（`truncate.ts:1-9`）：

> Truncation is based on two independent limits - whichever is hit first wins: Line limit (default: 2000 lines) / Byte limit (default: 50KB). Never returns partial lines (except bash tail truncation edge case).

**bash 用 `truncateTail`（保尾），read/grep/find/ls 用 `truncateHead`（保头）**：
- `truncateTail`（`truncate.ts:168-241`）从末尾往回收行——因为报错和最终结果在尾部
- `truncateHead`（`truncate.ts:78-160`）从头收——因为文件从头读

`truncateTail` 有一个刻意保留的破例（`truncate.ts:205-212`）：如果**最后一行本身就超过 50KB**，会切出这行的末尾 50KB 并标 `lastLinePartial = true`，UTF-8 边界用 `truncateStringToBytesFromEnd`（`:247-262`）对齐。

**截断了怎么办：全量写临时文件。** `OutputAccumulator`（`core/tools/output-accumulator.ts`，222 行）在 bash 里以 `tempFilePrefix: "pi-bash"` 构造（`bash.ts:342`），临时文件名 `os.tmpdir()/pi-bash-<16位hex>.log`（`output-accumulator.ts:19-22`）。类注释说明了内存策略（`:28-33`）：

> Incrementally tracks streaming output with bounded memory. Appends decode chunks with a streaming UTF-8 decoder, keeps only a decoded tail for display snapshots, and opens a temp file when the full output needs to be preserved.

滚动窗口是 `maxBytes * 2`（`output-accumulator.ts:59`）。

回给模型的三种截断脚注（`bash.ts:412-419`）：

```
[Showing last 50.0KB of line 1234 (line is 3.2MB). Full output: /tmp/pi-bash-xxxx.log]
[Showing lines 8001-10000 of 10000. Full output: /tmp/pi-bash-xxxx.log]
[Showing lines 9120-10000 of 10000 (50.0KB limit). Full output: /tmp/pi-bash-xxxx.log]
```

> 上 PPT 的点：**截断不丢数据——把全量落到 `/tmp` 并把路径写进 tool result，模型可以自己再 `read` 那个文件**。这是"截断"与"自愈"的接缝。

### 4.3 进程模型：**每次新起，不是持久 shell**

`createLocalBashOperations.exec`（`bash.ts:84-147`）每次调用都 `spawn` 一次（`bash.ts:97-103`）：

```ts
const child = spawn(shellConfig.shell, commandFromStdin ? shellConfig.args : [...shellConfig.args, command], {
    cwd,
    detached: process.platform !== "win32",     // ★ 非 Windows 建独立进程组
    env: env ?? getShellEnv(),
    stdio: [commandFromStdin ? "pipe" : "ignore", "pipe", "pipe"],
    windowsHide: true,
});
```

**结论直接的推论**：`cd /x && ...` 只在这一次调用内有效；`export FOO=1` 不跨调用；后台进程需要自己 `nohup`。文档也把 background bash 列进"刻意不做"清单（`docs/usage.md:301`）。

`detached: true` 的目的是让 `killProcessTree(child.pid)` 能一次干掉整组（`bash.ts:112`、`:120`）；同时用 `trackDetachedChildPid` / `untrackDetachedChildPid`（`bash.ts:108`、`:142`）登记，进程退出时兜底清理。

shell 解析顺序（`utils/shell.ts:60-118`，注释 `:60-66`）：

1. 用户显式 `shellPath`（settings.json）
2. Windows：Git Bash 已知路径 → PATH 上的 `bash.exe`
3. Unix：`/bin/bash` → PATH 上的 `bash` → 退回 `sh`

命令传递方式（`shell.ts:20-22`）：

```ts
function getBashShellConfig(shell: string): ShellConfig {
    return isLegacyWslBashPath(shell) ? { shell, args: ["-s"], commandTransport: "stdin" } : { shell, args: ["-c"] };
}
```
即默认 `bash -c "<command>"`；只有旧版 WSL 的 `C:\Windows\System32\bash.exe` 走 `bash -s` + stdin 喂命令（`shell.ts:15-18` 的正则判定）。

### 4.4 cwd 怎么管：**闭包捕获，全程不变**

- `createBashToolDefinition(cwd, options)`（`bash.ts:316`）把 `cwd` 捕进闭包
- `execute` 里 `resolveSpawnContext(resolvedCommand, cwd, spawnHook, ...)`（`bash.ts:341`）
- 传给 `spawn` 的就是它（`bash.ts:98`）
- 全仓 **没有任何 `process.chdir` 调用**：
  ```bash
  $ grep -rn "process.chdir\|setCwd" packages/coding-agent/src/
  packages/coding-agent/src/core/footer-data-provider.ts:169:  setCwd(cwd: string): void {     # 只是 footer 显示
  packages/coding-agent/src/modes/interactive/interactive-mode.ts:1782:  this.footerDataProvider.setCwd(...)
  ```

执行前会显式检查目录还在（`bash.ts:90-94`）：

```ts
try { await fsAccess(cwd, constants.F_OK); }
catch { throw new Error(`Working directory does not exist: ${cwd}\nCannot execute bash commands.`); }
```

唯一能改 cwd 的口子是 `spawnHook`（`bash.ts:150-156`、`:183`）：

```ts
export interface BashSpawnContext { command: string; cwd: string; env: NodeJS.ProcessEnv; }
export type BashSpawnHook = (context: BashSpawnContext) => BashSpawnContext;
...
return spawnHook ? spawnHook(baseContext) : baseContext;
```
这是 sandbox / SSH / 容器类扩展的挂载点。

### 4.5 环境变量：注入 `PI_*`，但先删再加

`resolveSpawnContext`（`bash.ts:158-184`）：

```ts
const env = { ...getShellEnv() };
delete env.PI_SESSION_ID; delete env.PI_SESSION_FILE;
delete env.PI_PROVIDER;   delete env.PI_MODEL;  delete env.PI_REASONING_LEVEL;   // :166-170 ★ 先清
if (exposeSessionEnvironment && ctx) {
    env.PI_SESSION_ID = ctx.sessionManager.getSessionId();
    const sessionFile = ctx.sessionManager.getSessionFile(); if (sessionFile) env.PI_SESSION_FILE = sessionFile;
    if (model) { env.PI_PROVIDER = model.provider; env.PI_MODEL = model.id; }
    if (ctx.thinkingLevel) env.PI_REASONING_LEVEL = ctx.thinkingLevel;
}
```

先无条件 `delete` 五个 `PI_*` 是为了**防止父进程（比如嵌套的 pi）的会话信息泄漏进子命令**。

`getShellEnv()`（`utils/shell.ts:122-134`）会把 pi 自己的 bin 目录前插进 `PATH`（大小写不敏感地找 `PATH` key，兼容 Windows），这样 `rg` / `fd` 这类自动下载的工具在 bash 里也能直接用。

### 4.6 流式输出节流 100ms

`BASH_UPDATE_THROTTLE_MS = 100`（`bash.ts:200`），`scheduleOutputUpdate`（`bash.ts:369-382`）做的是「距上次更新不足 100ms 就攒一个定时器」。harness 版常量相同（`agent/src/harness/tools/bash.ts:9`）。

### 4.7 退出码非 0 = 报错

`bash.ts:451-453`：

```ts
if (exitCode !== 0 && exitCode !== null) {
    throw new Error(appendStatus(outputText, `Command exited with code ${exitCode}`));
}
```

**输出在前、状态在后**（`appendStatus`，`bash.ts:424`）：`${text}\n\n${status}`。所以模型拿到的是「完整输出 + 一行退出码说明」，而不是只有一句 "command failed"。

---

## 5. 工具错误怎么回给模型

### 5.1 三个捕获点，全部在 `packages/agent/src/agent-loop.ts`

| 阶段 | 位置 | 捕获什么 |
|---|---|---|
| 准备（找工具 / prepareArguments / schema 校验 / `beforeToolCall`） | `:600-664` | `Tool X not found`（`:611`）、`Operation aborted`（`:632`、`:647`）、`block`（`:639`）、任意异常（`:660`） |
| 执行 | `:666-707` | `tool.execute()` 抛的任何东西（`:697-703`） |
| 收尾（`afterToolCall` 钩子） | `:709-754` | 钩子自己抛的异常（`:743-746`） |

### 5.2 错误文案模板：**就一个函数，六行**

`agent-loop.ts:756-761`：

```ts
function createErrorToolResult(message: string): AgentToolResult<any> {
    return {
        content: [{ type: "text", text: message }],
        details: {},
    };
}
```

**没有包装、没有前缀、没有 `<error>` 标签、没有堆栈**。错误消息就是 `error.message` 原文：

```ts
result: createErrorToolResult(error instanceof Error ? error.message : String(error)),   // :660, :701, :744
isError: true,
```

然后原样变成一条 `toolResult` 消息（`agent-loop.ts:773-787`）：

```ts
function createToolResultMessage(finalized: FinalizedToolCallOutcome): ToolResultMessage {
    return { role: "toolResult", toolCallId, toolName,
             content: finalized.result.content ?? [],   // 注释：Untyped tools (JS extensions) can return results without content
             details, usage, isError: finalized.isError, timestamp: Date.now() };
}
```

> **所以"错误文案模板"其实分布在各个工具自己的 `throw new Error(...)` 里**——`agent-loop` 只负责把 `message` 原样搬运。这是刻意的：谁最懂这个错，谁写文案。

### 5.3 是否鼓励自愈：**是，而且是设计出来的**

四条硬证据：

1. **错误文案本身带修复指令**（`edit-diff.ts:271`、`:275`）：
   > `... The text must be unique. **Please provide more context to make it unique.**`

2. **schema 校验失败会把收到的参数原样回给模型**（`packages/ai/src/utils/validation.ts:301-307`）：
   ```ts
   const errors = validator.Errors(args).map((e) => `  - ${formatValidationPath(e)}: ${e.message}`).join("\n") || "Unknown validation error";
   const errorMessage = `Validation failed for tool "${toolCall.name}":\n${errors}\n\nReceived arguments:\n${JSON.stringify(toolCall.arguments, null, 2)}`;
   ```
   **模型能看见自己发了什么、错在哪个字段** —— 这是自愈信息量的上限。

3. **bash 失败时把已产生的输出一起回**（`bash.ts:437-446`），模型不需要重跑一次才知道发生了什么。

4. **错误不中断循环**。`isError: true` 只是消息上的一个布尔位；主循环的判停条件是「没有更多 tool call」而不是「有没有报错」——模型收到错误后可以直接在同一轮发新的 tool call 修。唯一会因为工具结果提前结束的情况是 `terminate`，而且要求**整批全部** `terminate === true`（`agent-loop.ts:582-584`）：
   ```ts
   function shouldTerminateToolBatch(finalizedCalls: FinalizedToolCallOutcome[]): boolean {
       return finalizedCalls.length > 0 && finalizedCalls.every((f) => f.result.terminate === true);
   }
   ```

5. **`read` 的 description 里直接写了续读协议**（`read.ts:212`）：*"When you need the full file, continue with offset until complete."*；`bash` 的截断脚注给出临时文件绝对路径——**两处都是"我截断了，但你有办法自己拿全"**。

### 5.4 没有的东西（也是硬事实）

- 没有工具级重试
- 没有错误分类/错误码枚举
- 没有"连续 N 次失败就停"的熔断
- `createErrorToolResult` 的 `details` 恒为 `{}`，错误不携带结构化信息

---

## 6. 权限模型：pi 号称"不做权限弹窗"——代码里到底有没有拦截

### 6.1 官方主张

`packages/coding-agent/README.md:499`：
> **No permission popups.** Run in a container, or build your own confirmation flow with extensions inline with your environment and security requirements.

`packages/coding-agent/docs/usage.md:301`：
> It intentionally does not include built-in MCP, sub-agents, **permission popups**, plan mode, to-dos, or background bash.

### 6.2 实测：全仓 grep

```bash
$ grep -rniI "permission" packages/coding-agent/src/ | wc -l
3
$ grep -rniI "permission" packages/coding-agent/src/
packages/coding-agent/src/modes/interactive/interactive-mode.ts:2721:  // Silently ignore clipboard errors (may not have permission, etc.)
packages/coding-agent/src/utils/ansi.ts:10:  * Permission is hereby granted, free of charge, ...   ← MIT 许可证文本
packages/coding-agent/src/utils/ansi.ts:17:  * The above copyright notice and this permission notice ...
```

**三处，零个是权限逻辑**：一条剪贴板注释 + 两行 MIT 许可证。

```bash
$ grep -rniI "permission" packages/agent/src/
packages/agent/src/harness/types.ts:153:      | "permission_denied"        ← 文件系统错误码枚举
packages/agent/src/harness/types.ts:318:  /** ... Other errors, such as permission failures, return a FileError. */
packages/agent/src/harness/env/nodejs.ts:108: return new FileError("permission_denied", message, path, cause);
```
同样只是 **POSIX 文件权限错误的映射**，不是 agent 权限系统。

`grep -rni "permission" packages/coding-agent/src/core/tools/ packages/agent/src/harness/tools/` → **零命中**。

### 6.3 逐项核对可能的拦截面

| 可能的拦截面 | 实测结论 | 证据 |
|---|---|---|
| 执行前弹窗确认 | **不存在** | `agent-loop.ts:600-664` 的 `prepareToolCall` 全流程只有：找工具 / `prepareArguments` / schema 校验 / `beforeToolCall` 钩子 / abort 检查 |
| 命令白/黑名单 | **不存在** | `bash.ts` 里 `command` 从 schema 直达 `spawn`（`:341` → `:97`），中间只有 `commandPrefix` 拼接（`:340`） |
| 路径沙箱（限制在 cwd 内） | **不存在** | `resolveToCwd`（`core/tools/path-utils.ts:44-48`）→ `utils/paths.ts:81-85`：`isAbsolute(normalized) ? nodeResolvePath(normalized) : nodeResolvePath(baseDir, normalized)`。**绝对路径原样通过，`../../../etc/passwd` 也照常解析**。仓库里确实有 `getCwdRelativePath`（`paths.ts:87-96`）能判断是否在 cwd 内，但它只被 `formatPathRelativeToCwdOrAbsolute`（`:98-101`）用于**显示** |
| 危险文件保护（`.env` / `.ssh` 之类） | **不存在** | `read.ts` / `write.ts` / `edit.ts` 全文无任何路径模式匹配 |
| 只读模式 | **不存在**（只有工具集裁剪） | `createReadOnlyToolDefinitions`（`tools/index.ts:147-154`）是靠**不给 write/edit/bash** 实现的，不是运行时拦截 |

### 6.4 **唯一**的拦截点：`beforeToolCall` → 扩展 `tool_call` 钩子

`packages/agent/src/agent-loop.ts:619-642`：

```ts
if (config.beforeToolCall) {
    const beforeResult = await config.beforeToolCall({ assistantMessage, toolCall, args: validatedArgs, context: currentContext }, signal);
    if (signal?.aborted) { return { kind: "immediate", result: createErrorToolResult("Operation aborted"), isError: true }; }
    if (beforeResult?.block) {                                                        // :636
        return { kind: "immediate",
                 result: createErrorToolResult(beforeResult.reason || "Tool execution was blocked"),   // :639
                 isError: true };
    }
}
```

产品层怎么接（`packages/coding-agent/src/core/agent-session.ts:469-488`）：

```ts
this.agent.beforeToolCall = async ({ toolCall, args }) => {
    const runner = this._extensionRunner;
    if (!runner.hasHandlers("tool_call")) {
        return undefined;                       // ★ :471-473 没有扩展注册 → 直接放行，零开销
    }
    try {
        return await runner.emitToolCall({ type: "tool_call", toolName: toolCall.name, toolCallId: toolCall.id, input: args as Record<string, unknown> });
    } catch (err) {
        if (err instanceof Error) throw err;
        throw new Error(`Extension failed, blocking execution: ${String(err)}`);   // :486 ★ 扩展抛错 = 阻断
    }
};
```

### 6.5 结论（明确表态）

**"pi 不做权限弹窗"这个说法——成立，且比宣传更彻底。**

- 内置代码路径里**没有任何**执行前拦截、确认、白名单、沙箱、路径限制。默认配置下 `bash` 是完整的本地 shell 权限，`read`/`write`/`edit` 是完整的本地文件系统权限，**不受 cwd 约束**。
- 但代码里**留了一个精确的钩子**（`tool_call` → `{ block, reason }`），并且默认零成本（无 handler 时 `hasHandlers` 短路）。
- 官方给了参考实现：`packages/coding-agent/examples/extensions/permission-gate.ts`，**整个"权限系统"34 行**：

```ts
const dangerousPatterns = [/\brm\s+(-rf?|--recursive)/i, /\bsudo\b/i, /\b(chmod|chown)\b.*777/i];

pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;
    const command = event.input.command as string;
    if (dangerousPatterns.some((p) => p.test(command))) {
        if (!ctx.hasUI) return { block: true, reason: "Dangerous command blocked (no UI for confirmation)" };
        const choice = await ctx.ui.select(`⚠️ Dangerous command:\n\n  ${command}\n\nAllow?`, ["Yes", "No"]);
        if (choice !== "Yes") return { block: true, reason: "Blocked by user" };
    }
    return undefined;
});
```

- 唯一的**内置**能力限制手段是**静态工具集裁剪**（`--tools` / `--exclude-tools` / `--no-tools` / `--no-builtin-tools`，`cli/args.ts:118-131`）。这是"给不给这把刀"，不是"这一刀让不让砍"。
- 官方推荐的隔离手段是**进程外**的：容器 / 沙箱扩展（`examples/extensions/` 下 79 个示例中就有 `sandbox/`）。

> **上 PPT 的表述建议**：不要说"pi 没有权限系统"，要说 **"pi 把权限系统从内核搬到了扩展层，内核只留一个 `{block, reason}` 的返回值；官方参考实现 34 行。"**

---

## 7. 两个横切设施（讲工具设计绕不开）

### 7.1 同文件写操作串行化：`withFileMutationQueue`

`packages/coding-agent/src/core/tools/file-mutation-queue.ts`（61 行），注释即规格（`:28-31`）：

> Serialize file mutation operations targeting the same file. Operations for different files still run in parallel.

队列 key 是 **`realpath`**（`:16-26`），文件不存在时退回 `resolve()`（`:22-24`）：

```ts
async function getMutationQueueKey(filePath: string): Promise<string> {
    const resolvedPath = resolve(filePath);
    try { return await realpath(resolvedPath); }
    catch (error) { if (isMissingPathError(error)) return resolvedPath; throw error; }
}
```

**用 realpath 做 key 意味着：符号链接指向同一个文件时也会被正确串行化。**

只有 `edit`（`edit.ts:312`）和 `write`（`write.ts:203`）用它；`read` 和 `bash` **不用**（读不需要，bash 的副作用 pi 管不了）。

### 7.2 abort 在工具内的落法：不用事件监听器

`edit.ts:313-319` 的注释是这套代码里最值得抄的一段：

```ts
// Do not reject from an abort event listener here: that would release the
// mutation queue while an in-flight filesystem operation may still finish.
// Checking signal.aborted after each await observes the same aborts while
// keeping the queue locked until the current operation has settled.
const throwIfAborted = (): void => { if (signal?.aborted) throw new Error("Operation aborted"); };
```

于是 `edit` 里 `throwIfAborted()` 出现 **6 次**（`:321`、`:327`、`:332`、`:337`、`:344`、`:348`），`write` 里 **4 次**（`:212`、`:215`、`:219` + `:208` 定义）。harness 版同样是 `if (signal?.aborted) throw new Error("Operation aborted")` 逐段插入（`harness/tools/edit.ts:93, 102, 108, 113`）。

> 上 PPT 的点：**"中断"和"释放锁"是两件事**。事件驱动的 abort 会在文件操作还在飞的时候放锁，pi 选了轮询式检查换取锁的正确性。

---

## 8. 工具设计原则（从这套代码反推，可迁移）

以下每条都对应上文的具体行号，不是泛泛而谈。

### 原则 1：默认工具集要是一组**正交基**，不是功能清单

read / bash / edit / write = 读 / 执行 / 改 / 覆写，四个动作互不重叠，且 `bash` 张成了剩下所有文件操作。
证据：`agent-session.ts:2592-2594` + `system-prompt.ts:97-100` 的条件 guideline。
反例就在同一个仓库里——grep/find/ls 实现了 984 行，默认不给。

### 原则 2：**实现数 ≠ 暴露数**，把选择权留给宿主

`allToolNames` 7 个（`tools/index.ts:84`），默认激活 4 个，通过 `--tools` / `setActiveTools` 任意组合。
三组预设（`tools/index.ts:138/147/156`）说明 pi 认为"工具集"是一个**场景变量**，不是产品常量。

### 原则 3：把描述预算花在最容易出错的工具上

实测：`edit` 一个工具吃掉默认四件套 2595 字符预算的 **53%**（1388 字符，4 条 guidelines + 4 个字段描述）；`write` 只有 278 字符。
**难用的工具值得写长文档，简单的工具一句话。**

### 原则 4：模糊匹配只允许"确定性归一化"，绝不允许"猜"

`normalizeForFuzzyMatch`（`edit-diff.ts:33-54`）只做 5 类可枚举的字符归一，匹配仍是 `indexOf`。
多处命中 → `throw`（`edit-diff.ts:333-335`），**永远不选第一个**。
唯一性检查甚至比匹配更严（`countOccurrences` 无条件模糊，`:251-255`）。
**宁可拒绝，不可改错地方。**

### 原则 5：批量操作要么全成、要么全不做，并且都对着原始快照匹配

`applyEditsToNormalizedContent`（`edit-diff.ts:304-366`）五道闸门全过才写盘；替换逆序施加保证偏移稳定（`:110-119`）；重叠显式检测（`:345-354`）。
注释直说（`:295-297`）：*"All edits are matched against the same original content."*
**这消灭了"第 3 条 edit 因为前 2 条改了文件而匹配失败"这一整类 bug。**

### 原则 6：截断必须给"取回全量"的出口

bash 截断 → 全量写 `/tmp/pi-bash-*.log` 并把绝对路径写进 tool result（`bash.ts:414-418`）；
read 截断 → description 明写 *"continue with offset until complete"*（`read.ts:212`）。
**截断是压缩上下文，不是丢信息。**

### 原则 7：错误消息是给模型的**下一步指令**，不是给人的日志

`edit-diff.ts:257-293` 六种文案全部包含"该怎么改"；
schema 校验失败连收到的参数 JSON 一起回（`ai/src/utils/validation.ts:307`）；
bash 失败把已产生输出一起回（`bash.ts:437-446`）。
而 `createErrorToolResult`（`agent-loop.ts:756-761`）本身只有 6 行、零包装——**框架不加戏，文案归工具**。

### 原则 8：给"脏参数"留一个校验前的修正口，而不是放松 schema

`prepareArguments`（`ToolDefinition` 字段）在 `validateToolArguments` 之前跑（`agent-loop.ts:617-618`）。
pi 用它兜住了具体模型的具体毛病（`edit.ts:101` 注释点名 Opus 4.6 / GLM-5.1 把 `edits` 发成 JSON 字符串），schema 本身仍然是严格的数组类型。

### 原则 9：权限不进内核，只留一个返回值

内核只有 `beforeToolCall → { block?, reason? }`（`agent-loop.ts:636-642`），无 handler 时短路（`agent-session.ts:471-473`）。
34 行的扩展就能实现完整确认流（`examples/extensions/permission-gate.ts`）。
**代价要讲清楚：默认状态下没有任何路径沙箱**（`utils/paths.ts:81-85`，绝对路径直通）。

### 原则 10：工具的核心算法必须是无 IO 纯函数

`edit-diff.ts`（560 行）不碰文件系统，`edit.ts` 只负责 read → 调纯函数 → write。
直接收益：TUI 能在工具真正执行**之前**用同一份算法算出 diff 预览（`computeEditsDiff`，`edit-diff.ts:518-547`，被 `edit.ts:380` 的 `renderCall` 调用），**预览和实际执行不可能不一致**。

### 原则 11：所有 IO 都走可替换的 `operations` 接口

`ReadOperations`（`read.ts:43-50`）、`WriteOperations`（`write.ts:25-30`）、`EditOperations`（`edit.ts:74-81`）、`BashOperations`（`bash.ts:56-74`），注释统一写着 *"Override these to delegate ... to remote systems (for example SSH)."*
harness 路径干脆把整个 IO 抽成 `env`（`harness/tools/write.ts:26` `env.writeFile(...)`）。
**同一套工具语义可以跑在本地 / SSH / 容器 / 内存 FS 上。**

### 原则 12：并发的安全边界按"资源"划，不按"工具"划

`withFileMutationQueue` 用 `realpath` 做 key（`file-mutation-queue.ts:16-26`），同文件串行、异文件并行。
没有把 `edit`/`write` 标成 `executionMode: "sequential"`（全仓工具定义里**零处**设置 `executionMode`，只在 wrapper 里透传：`tool-definition-wrapper.ts:16, 44`）——**并发粒度做在资源层，不是工具层。**

---

## 9. 最适合上 PPT 的 5 条硬事实

1. **7 个内置工具，默认只给模型 4 个**（`tools/index.ts:84` vs `agent-session.ts:2592-2594` / `sdk.ts:245`）。`grep`/`find`/`ls` 实现了 984 行却默认不注入——system prompt 里有一条条件规则 `if (hasBash && !hasGrep && !hasFind && !hasLs) addGuideline("Use bash for file operations like ls, rg, find")`（`system-prompt.ts:103-105`），**用 bash 张成它们，省下 3 个槽位和 591 字符描述预算**。

2. **默认四件套的全部提示预算实测 2595 字符，其中 `edit` 一个占 1388 字符（53%）**：description 326 + snippet 98 + 4 条 guidelines 496 + 4 个字段描述 468。**最难用的工具值得写长文档；`write` 全部只有 278 字符。**

3. **`edit` 的"模糊匹配"其实是两次 `indexOf`**：先精确 `content.indexOf(oldText)`，失败后把双方做 5 类确定性归一（NFKC / 行尾空白 / 智能引号 / Unicode 破折号 / 特殊空格，`edit-diff.ts:33-54`）再 `indexOf`。**多处命中一律 `throw`，永不选第一个**（`:333-335`）；而且唯一性检查**无条件按模糊口径**（`countOccurrences`，`:251-255`），比匹配本身还严。一批 edit 全部对着原始快照匹配、逆序施加、任一失败则一个字节都不写。

4. **`bash` 默认没有超时**（`bash.ts:42` schema 描述原文 `"Timeout in seconds (optional, no default timeout)"`，`resolveTimeoutMs` 见 `:27-38`），上限 24.86 天；**每次调用 `spawn` 一个新 shell**（`bash.ts:97`，`detached: true`），所以 `cd`/`export` 不跨调用；cwd 是工厂闭包捕获的常量，全仓**零处 `process.chdir`**；输出保尾截断到 **2000 行 / 50KB 取先到者**（`truncate.ts:11-12`），超限时全量落 `/tmp/pi-bash-<hex>.log` 并把绝对路径写进 tool result——**截断不丢数据**。

5. **"pi 不做权限弹窗"成立，且比宣传更彻底**：`grep -rniI "permission" packages/coding-agent/src/` 只有 **3 行命中，全是剪贴板注释和 MIT 许可证**；无命令白名单、无路径沙箱（`utils/paths.ts:81-85` 绝对路径直通，`../../../` 照常解析）。内核只留一个钩子 `beforeToolCall → { block?, reason? }`（`agent-loop.ts:636-642`），无扩展注册时直接短路（`agent-session.ts:471-473`）；官方参考实现 `examples/extensions/permission-gate.ts` **整整 34 行**。

---

## 附：本次取证用到的全部命令

```bash
cd /Users/overkazaf/playground/research/pi/pi-mono
git rev-parse HEAD                    # 583f153d502aa8e958eefdb9af0fbd3344e68f95
git log -1 --date=iso --format='%ad%n%s'

wc -l packages/coding-agent/src/core/tools/*.ts packages/agent/src/harness/tools/*.ts
ls packages/agent/src/harness/tools/            # 无 grep/find/ls

grep -rn "defaultActiveToolNames" packages/coding-agent/src/
grep -rn "allToolNames" packages/coding-agent/src/
grep -rn '\-\-tools\|excludeTools\|noBuiltinTools' packages/coding-agent/src/

grep -rniI "permission" packages/coding-agent/src/ | wc -l      # 3
grep -rniI "permission" packages/coding-agent/src/core/tools/   # 0
grep -rn "process.chdir\|setCwd" packages/coding-agent/src/     # 仅 footer 显示

grep -rn "createErrorToolResult" packages/agent/src/agent-loop.ts
wc -l packages/coding-agent/examples/extensions/permission-gate.ts   # 34
ls packages/coding-agent/examples/extensions/ | wc -l               # 79

# 描述字符数实测（把 DEFAULT_MAX_LINES=2000 / DEFAULT_MAX_BYTES/1024=50 代入模板串后 len()）
/usr/bin/python3 - <<'PY'
... （见 2.1 节）
PY
```
