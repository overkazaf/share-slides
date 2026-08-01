# P09：模型接入层 `packages/ai` 代码级取证

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `pi-mono`（`@earendil-works/pi-ai`） | `packages/ai/package.json:2` |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --format='%ci'` |
> | 包版本 | `0.83.0` | `packages/ai/package.json:3` |
> | 代码量 | **21429 行** TS（`src/` 下 169 个 `.ts`） | `find src -name '*.ts' \| xargs wc -l \| tail -1`、`find src -name '*.ts' \| wc -l` |
> | 测试量 | **30632 行**、**122 个 `.test.ts`** | `wc -l test/*.ts \| tail -1`、`ls test/*.test.ts \| wc -l` |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对 `pi-mono/packages/ai/`（跨包引用会写全路径），均已在上述 commit 上实际打开验证。
> 行号会随上游漂移 —— PPT 上引用时**必须带 commit 短 hash `583f153`**。
>
> ⚠️ **一个必须先说的前置事实**：本仓库 checkout 后**没有 `node_modules`，也没有 `src/providers/data/`**（见 §4.2），所以本次取证**全部靠读源码 + grep 实测枚举**，无法运行 `vitest`。凡是"跑出来的数"我都写了命令与输出；凡是仓库自己的测试断言（如"模型总数 > 500"）我都标注为"仓库自称"，不当作实测。

---

## 0. 一句话结论

`packages/ai` 是一个**独立可发布的 npm 包**（`@earendil-works/pi-ai`），职责是把 **38 个 provider / 10 种 wire API** 收敛成**一套 canonical 消息类型 + 一条 12 种事件的流协议**。它**混用官方 SDK 与手写 HTTP**：Anthropic / OpenAI / Azure / Mistral / Bedrock / Google 用官方 SDK，OpenAI Codex 与 pi 自家 `pi-messages` 是**手写 SSE**。模型元数据（窗口 / 价格 / 能力位）**既不是硬编码也不是运行时拉取**，而是**构建期**从 `models.dev` 抓下来落成 gitignored 的 JSON。

---

## 1. Provider 枚举（实测）

### 1.1 内置 provider：**38 个**

唯一权威清单是 `builtinProviders()` —— `src/providers/all.ts:87-128`。

**实测命令与输出**：

```bash
$ sed -n '88,127p' src/providers/all.ts | grep -oE '[a-zA-Z]+Provider\(\)' | wc -l
38

$ sed -n '88,127p' src/providers/all.ts | grep -oE '[a-zA-Z]+Provider\(\)' | tr '\n' ' '
amazonBedrockProvider() antLingProvider() anthropicProvider() azureOpenAIResponsesProvider()
cerebrasProvider() cloudflareAIGatewayProvider() cloudflareWorkersAIProvider() deepseekProvider()
fireworksProvider() githubCopilotProvider() googleProvider() googleVertexProvider() groqProvider()
huggingfaceProvider() kimiCodingProvider() minimaxProvider() minimaxCnProvider() mistralProvider()
moonshotaiProvider() moonshotaiCnProvider() nvidiaProvider() openaiProvider() openaiCodexProvider()
opencodeProvider() opencodeGoProvider() openrouterProvider() qwenTokenPlanProvider()
qwenTokenPlanCnProvider() radiusProvider() togetherProvider() vercelAIGatewayProvider() xaiProvider()
xiaomiProvider() xiaomiTokenPlanAmsProvider() xiaomiTokenPlanCnProvider() xiaomiTokenPlanSgpProvider()
zaiProvider() zaiCodingCnProvider()
```

交叉验证：类型联合 `KnownProvider`（`src/types.ts:34-72`）也是 **38 个字符串字面量**：

```bash
$ sed -n '34,72p' src/types.ts | grep -oE '"[a-z0-9-]+"' | wc -l
38
```

> **两个数一致**，说明「类型层的 provider 清单」与「运行期注册清单」是同步维护的（`all.ts:51` 的 `BuiltinProvider = keyof typeof MODELS` 还从生成的目录反推了第三份，三者互相钉死）。

另外还有 **1 个图像生成 provider**（`builtinImagesProviders()`，`all.ts:139-142`）：`openrouterImagesProvider()`，以及 **1 个测试假 provider** `fauxProvider`（`src/providers/faux.ts`，不在 `builtinProviders()` 里）。

### 1.2 值得单独点名的几类 provider

| 类别 | provider | 说明 |
|---|---|---|
| 一方 API | `anthropic` / `openai` / `google` / `mistral` / `xai` / `deepseek` | — |
| 云托管 | `amazon-bedrock` / `google-vertex` / `azure-openai-responses` / `cloudflare-workers-ai` | — |
| 网关/聚合 | `openrouter` / `vercel-ai-gateway` / `cloudflare-ai-gateway` / `huggingface` | — |
| 订阅制（OAuth） | `openai-codex`（ChatGPT Plus/Pro）、`github-copilot`、`kimi-coding`、`opencode` / `opencode-go` | 需 OAuth。`src/auth/oauth/` 共 11 个文件，其中 **8 个是具体 flow**（`anthropic` / `github-copilot` / `kimi-coding` / `openai-codex` / `openrouter` / `radius` / `xai` / `device-code`），另 3 个是公共件（`load.ts` / `pkce.ts` / `oauth-page.ts`） |
| **中国区双份** | `zai`/`zai-coding-cn`、`minimax`/`minimax-cn`、`moonshotai`/`moonshotai-cn`、`qwen-token-plan`/`-cn`、`xiaomi-token-plan-cn`/`-ams`/`-sgp` | 同一家厂商按 region 拆成独立 provider id |
| **pi 自家** | `radius` | 唯一使用 `pi-messages` API 的 provider，也是唯一实现了 `refreshModels` 的内置 provider（`grep -ln refreshModels src/providers/*.ts` → 只有 `radius.ts`） |

### 1.3 官方 SDK vs 手写 HTTP —— **两条路都走**

`package.json:62-74` 的 `dependencies` 里同时躺着 **5 个官方 SDK**：

```json
"@anthropic-ai/sdk": "0.91.1",
"@aws-sdk/client-bedrock-runtime": "3.1048.0",
"@google/genai": "1.52.0",
"@mistralai/mistralai": "2.2.6",
"openai": "6.26.0",
"partial-json": "0.1.7",
"typebox": "1.3.7"
```

逐个 API 适配器实测（`grep '^import' src/api/*.ts`）：

| API 适配器 | 传输实现 | 证据 |
|---|---|---|
| `anthropic-messages.ts`（1351 行） | **官方 SDK** `import Anthropic from "@anthropic-ai/sdk"` | `:1`，client 构造在 `:869`/`:892`/`:927` |
| `openai-completions.ts`（1523 行） | **官方 SDK** `import OpenAI from "openai"` | `:1`，client 在 `:667` |
| `openai-responses.ts`（360 行） | **官方 SDK** | `:1-2`，client 在 `:248` |
| `azure-openai-responses.ts`（325 行） | **官方 SDK** `AzureOpenAI` | `:1` |
| `mistral-conversations.ts`（677 行） | **官方 SDK** `import { HTTPClient, Mistral }` | `:1` |
| `bedrock-converse-stream.ts`（1173 行） | **官方 SDK** `BedrockRuntimeClient` | `:3-24`，`new BedrockRuntimeClient(config)` 在 `:228` |
| `google-generative-ai.ts`（516 行） | **官方 SDK** `@google/genai` | `:6` |
| `google-vertex.ts`（591 行） | **官方 SDK** `@google/genai` | `:9` |
| **`openai-codex-responses.ts`（1650 行）** | **手写 `fetch` + 手写 SSE 解析器** | `:406` `await (options?.fetch ?? globalThis.fetch)(...)`；`parseSSE()` 在 `:764` |
| **`pi-messages.ts`（433 行）** | **手写 `fetch` + 手写 SSE 解析器** | `:382` `await (options?.fetch ?? globalThis.fetch)(url, ...)`；解析在 `:267-306` |

两个手写的都有明确理由：

- **Codex**：走的是 ChatGPT 后端的私有协议，请求体要 zstd 压缩（`openai-codex-responses.ts:65`、`:382` 注释），并且支持 WebSocket transport（`:836`、`:1252`），官方 SDK 覆盖不了。
- **pi-messages**：这是 **pi 自己定义的 wire 协议**，文件头注释（`pi-messages.ts:1-10`）写得很清楚：

```
 * Streams pi's own message protocol directly to a backend: the request is a
 * single POST of `{ model, context, options }` to `<baseUrl>/messages`, the
 * response is an SSE stream of serialized assistant-message events plus a
 * terminal `done`/`error` event.
```

> **上 PPT 的点**：**pi 把自己的 canonical 事件流本身也做成了一种 wire 协议**（`pi-messages`），任何后端实现它就能被 pi 当 provider 用。这是"统一抽象"做到极致的自然结果 —— 抽象层反过来定义了一个新协议。

### 1.4 Provider → API 的多对多映射（实测）

`KnownApi` 共 **10 种**（`src/types.ts:16-26`）：

```ts
export type KnownApi =
	| "openai-completions" | "mistral-conversations" | "openai-responses"
	| "azure-openai-responses" | "openai-codex-responses" | "anthropic-messages"
	| "bedrock-converse-stream" | "google-generative-ai" | "google-vertex" | "pi-messages";
```

实测每个 provider 用哪些 API（脚本扫 `src/providers/*.ts` 里出现的 api 字面量）：

- **`openai-completions` 是绝对主力**：`ant-ling` / `cerebras` / `cloudflare-workers-ai` / `deepseek` / `groq` / `huggingface` / `moonshotai(-cn)` / `nvidia` / `openrouter` / `qwen-token-plan(-cn)` / `together` / `xiaomi(+3 region)` / `zai(-coding-cn)` —— 约 20 个 provider 只走这一条。
- **一个 provider 可以挂多个 API**：`opencode` 同时声明 `anthropic-messages` / `google-generative-ai` / `openai-completions` / `openai-responses` 四种；`github-copilot`、`cloudflare-ai-gateway`、`opencode-go` 各挂三种；`fireworks`、`xai` 各两种。

这靠 `createProvider` 的 `api` 字段支持"单实现或按 `model.api` 分派的 map"（`src/models.ts:546-547`、分派逻辑 `:570-587`）：

```ts
const single = typeof (input.api as ProviderStreams).stream === "function" ? (input.api as ProviderStreams) : undefined;
const byApi = single ? undefined : (input.api as Partial<Record<string, ProviderStreams>>);
const apiFor = (model: Model<Api>): ProviderStreams | undefined => single ?? byApi?.[model.api];
```

**没有匹配的 API 实现不抛异常，而是返回一个"内含错误事件的流"**（`models.ts:581-585`）—— 这是全包贯穿的错误约定，见 §6.1。

---

## 2. 统一抽象：canonical 形状

### 2.1 输入侧：`Context` = systemPrompt + Message[] + Tool[]

`src/types.ts:487-491`：

```ts
export interface Context {
	systemPrompt?: string;
	messages: Message[];
	tools?: Tool[];
}
```

`Message` 是 **3 元联合**（`types.ts:433`）：`UserMessage | AssistantMessage | ToolResultMessage`。

- `UserMessage`（`:393-397`）：`content: string | (TextContent | ImageContent)[]`
- `AssistantMessage`（`:399-413`）：`content: (TextContent | ThinkingContent | ToolCall)[]`
- `ToolResultMessage`（`:415-431`）：`content: (TextContent | ImageContent)[]` + `details?` + `isError`

`Tool`（`:480-485`）用 **TypeBox**（`import type { TSchema } from "typebox"`，`:456`），全包**无 Zod**：

```ts
export interface Tool<TParameters extends TSchema = TSchema> {
	name: string;
	description: string;
	parameters: TParameters;
	constrainedSampling?: false | ConstrainedSamplingConfig;
}
```

### 2.2 内容块：4 种，每种都带"回灌用的不透明签名"

| 块类型 | 行号 | 签名字段 | 用途 |
|---|---|---|---|
| `TextContent` | `:338-342` | `textSignature?` | OpenAI Responses 的 message item id（`TextSignatureV1` JSON，`:332-336`） |
| `ThinkingContent` | `:344-352` | `thinkingSignature?` + `redacted?` | Anthropic signature / OpenAI reasoning item / Google thoughtSignature |
| `ImageContent` | `:354-358` | — | base64 + mimeType |
| `ToolCall` | `:360-366` | `thoughtSignature?` | Google 专用 |

> **上 PPT 的点**：**canonical 类型里为每种内容块都预留了一个"provider 私有的不透明签名"槽位**。这是跨 provider 抽象最难的一块 —— 思维链、reasoning item、tool 的思考签名都是**不可解释、只能原样带回去**的 blob，pi 的做法不是丢弃，而是**显式建模成 `*Signature` 字段**。

### 2.3 输出侧：`AssistantMessage`（`types.ts:399-413`）

```ts
export interface AssistantMessage {
	role: "assistant";
	content: (TextContent | ThinkingContent | ToolCall)[];
	api: Api;                     // :402  哪套 wire 协议产的
	provider: ProviderId;         // :403
	model: string;                // :404  请求的 model id
	responseModel?: string;       // :405  ★ OpenRouter "auto" 实际路由到的 model
	responseId?: string;          // :406
	diagnostics?: AssistantMessageDiagnostic[];  // :407  脱敏后的失败/恢复诊断
	usage: Usage;                 // :408
	stopReason: StopReason;       // :409
	errorMessage?: string;        // :410
	rawStopReason?: string;       // :411  ★ 原始 provider 字符串，不丢
	timestamp: number;            // :412
}
```

`StopReason` 收敛成 **6 种**（`:391`）：`"pending" | "stop" | "length" | "toolUse" | "error" | "aborted"`。

> 注意 `rawStopReason` 与 `stopReason` **并存**：映射后的枚举给上层判停用，原始字符串留给排查。测试里专门有 `bedrock-raw-stop-reason.test.ts` / `google-raw-stop-reason.test.ts` / `mistral-raw-stop-reason.test.ts` / `openai-completions-raw-stop-reason.test.ts` 四份。

### 2.4 各家 wire 格式怎么映射进来 —— `compat` 位是主要手段

`Model<TApi>`（`types.ts:761-788`）用**条件类型**给每种 api 挂不同的 compat 结构：

```ts
compat?: TApi extends "openai-completions" ? OpenAICompletionsCompat
	: TApi extends "openai-responses" | "azure-openai-responses" | "openai-codex-responses" ? OpenAIResponsesCompat
	: TApi extends "anthropic-messages" ? AnthropicMessagesCompat
	: TApi extends "bedrock-converse-stream" ? BedrockCompat
	: never;
```

**`OpenAICompletionsCompat` 有 22 个开关**（`types.ts:519-574`），这是全包信息密度最高的一段。挑几条最能说明"OpenAI 兼容 API 其实一点都不兼容"的：

| 字段 | 行号 | 说的是什么坑 |
|---|---|---|
| `supportsDeveloperRole` | `:523` | 有的接受 `developer` 角色，有的只认 `system` |
| `maxTokensField` | `:531` | `max_completion_tokens` 还是 `max_tokens` |
| `requiresToolResultName` | `:533` | tool result 要不要带 `name` |
| `requiresAssistantAfterToolResult` | `:535` | tool result 后面直接跟 user 消息会报错，得插一条 assistant |
| `requiresThinkingAsText` | `:537` | thinking 块必须降级成 text |
| `requiresReasoningContentOnAssistantMessages` | `:539` | 回放的 assistant 消息必须带空 `reasoning_content` |
| **`thinkingFormat`** | `:541-551` | **10 种**思考参数格式：`openai`/`openrouter`/`deepseek`/`together`/`zai`/`qwen`/`chat-template`/`qwen-chat-template`/`string-thinking`/`ant-ling` |
| `supportsFinishReason` | `:529` | 有的流根本不发 `finish_reason`，pi 自己推断 `stop` 还是 `toolUse` |
| `cacheControlFormat` | `:565` | 值只有 `"anthropic"` —— 即"在 OpenAI 兼容端点上套 Anthropic 风格的 `cache_control`" |
| `sessionAffinityFormat` | `:571` | 三种 session 亲和头格式 |

`AnthropicMessagesCompat`（`:595-648`）也有 9 个，同样揭示了"Anthropic 兼容"厂商的坑，例如 `supportsCacheControlOnTools`（`:621`，注释点名 Fireworks 不支持在 tools 上加 `cache_control`）、`supportsTemperature`（`:627`，注释：Claude Opus 4.7+ 拒绝非默认 temperature）。

compat 的默认值**从 baseUrl 自动探测**，再被模型元数据覆盖 —— `openai-completions.ts:1455` 是探测默认表，`:1506` 是合并：

```ts
requiresThinkingAsText: model.compat.requiresThinkingAsText ?? detected.requiresThinkingAsText,
```

---

## 3. 流式解析

### 3.1 流的载体：一个 88 行的 `EventStream`

`src/utils/event-stream.ts`（**整文件 88 行**）。核心是"队列 + 等待者"的手写 async iterator（`:4-67`），外加一个 `result(): Promise<R>` 终值 Promise。

`AssistantMessageEventStream`（`:69-83`）只是把「完成判据」和「终值抽取」钉死：

```ts
super(
	(event) => event.type === "done" || event.type === "error",
	(event) => {
		if (event.type === "done") return event.message;
		else if (event.type === "error") return event.error;
		throw new Error("Unexpected event type for final result");
	},
);
```

> 即：**一条流既可以 `for await` 逐事件消费，也可以 `await stream.result()` 只要终值**。`Models.complete()` 就是 `this.stream(...).result()`（`models.ts:509`）。

### 3.2 事件协议：**12 种**（`types.ts:501-513`）

```ts
export type AssistantMessageEvent =
	| { type: "start";          partial: AssistantMessage }
	| { type: "text_start";     contentIndex; partial }
	| { type: "text_delta";     contentIndex; delta: string; partial }
	| { type: "text_end";       contentIndex; content: string; partial }
	| { type: "thinking_start"; contentIndex; partial }
	| { type: "thinking_delta"; contentIndex; delta: string; partial }
	| { type: "thinking_end";   contentIndex; content: string; partial }
	| { type: "toolcall_start"; contentIndex; partial }
	| { type: "toolcall_delta"; contentIndex; delta: string; partial }
	| { type: "toolcall_end";   contentIndex; toolCall: ToolCall; partial }
	| { type: "done";  reason: "stop"|"length"|"toolUse"; message: AssistantMessage }
	| { type: "error"; reason: "aborted"|"error";         error: AssistantMessage };
```

**每个增量事件都带 `partial: AssistantMessage` 全量快照** —— 上层不需要自己做累加。（这一点在 R10 §1.3 已经从 agent-loop 那侧印证过：`context.messages[last] = event.partial` 整条替换。）

### 3.3 增量 block 组装（Anthropic 为例）

组装状态就是**输出消息的 `content` 数组本身**，加一个临时 `index` 字段做 wire 索引 → 数组下标的映射（`anthropic-messages.ts:570-571`）：

```ts
type Block = (ThinkingContent | TextContent | (ToolCall & { partialJson: string })) & { index: number };
const blocks = output.content as Block[];
```

`content_block_start`（`:587-628`）按 4 种 wire 类型建块，其中 `redacted_thinking` 被映射成一个**文本占位 + 原始 payload 塞进签名**（`:605-614`）：

```ts
} else if (event.content_block.type === "redacted_thinking") {
	const block: Block = {
		type: "thinking",
		thinking: "[Reasoning redacted]",
		thinkingSignature: event.content_block.data,
		redacted: true,
		index: event.index,
	};
```

### 3.4 工具调用增量怎么拼（**核心 12 行**，`anthropic-messages.ts:654-666`）

```ts
} else if (event.delta.type === "input_json_delta") {
	const index = blocks.findIndex((b) => b.index === event.index);
	const block = blocks[index];
	if (block && block.type === "toolCall") {
		block.partialJson += event.delta.partial_json;
		block.arguments = parseStreamingJson(block.partialJson);   // ★ 每个 delta 都重解一次
		stream.push({
			type: "toolcall_delta",
			contentIndex: index,
			delta: event.delta.partial_json,
			partial: output,
		});
	}
}
```

关键设计：

1. **`partialJson` 是 scratch buffer，`arguments` 是随时可读的已解析对象** —— 每个 delta 都重新 `parseStreamingJson` 整串，所以 UI 在流中途就能拿到半成品参数树渲染。
2. **收尾时 scratch 必须删掉**（`:694-705`）：

```ts
} else if (block.type === "toolCall") {
	block.arguments = parseStreamingJson(block.partialJson);
	// Finalize in-place and strip the scratch buffer so replay only
	// carries parsed arguments.
	delete (block as { partialJson?: string }).partialJson;
	stream.push({ type: "toolcall_end", contentIndex: index, toolCall: block, partial: output });
}
```

出错路径也要删（`:760-765`），否则 scratch 会被持久化进 session：

```ts
} catch (error) {
	for (const block of output.content) {
		delete (block as { index?: number }).index;
		// partialJson is only a streaming scratch buffer; never persist it.
		delete (block as { partialJson?: string }).partialJson;
	}
```

### 3.5 `parseStreamingJson`：**四层 fallback**（`src/utils/json-parse.ts:104-124`）

```ts
try { return parseJsonWithRepair<T>(partialJson); }        // ① 严格 JSON，失败则修控制字符/非法转义再试
catch {
  try { return (partialParse(partialJson) ?? {}) as T; }   // ② partial-json 包，容忍截断
  catch {
    try { return (partialParse(repairJson(partialJson)) ?? {}) as T; }  // ③ 先修再 partial
    catch { return {} as T; }                              // ④ 兜底空对象，绝不抛
  }
}
```

`repairJson`（`:32-83`）是手写的字符级修复：字符串内的裸控制字符转义、非法反斜杠转义翻倍。

### 3.6 手写 SSE 解析（`openai-codex-responses.ts:764-812`）

```ts
async function* parseSSE(response: Response, signal?: AbortSignal): AsyncGenerator<Record<string, unknown>> {
	const reader = response.body.getReader();     // :767
	const decoder = new TextDecoder();            // :768
	…
	let idx = buffer.indexOf("\n\n");             // :787  以空行切事件
	…
		.split("\n").filter((l) => l.startsWith("data:"))   // :793-794
```

`pi-messages.ts:267-306` 是同一套写法（`indexOf("\n\n")` + `startsWith("data:")`）。**两处都没用第三方 SSE 库。**

### 3.7 OpenAI Completions 侧：`reasoning` 字段名有 3 个候选（`openai-completions.ts:484-515`）

```ts
// Some endpoints return reasoning in reasoning_content (llama.cpp),
// or reasoning (other openai compatible endpoints)
// Use the first non-empty reasoning field to avoid duplication
// (e.g., chutes.ai returns both reasoning_content and reasoning with same content)
const reasoningFields = ["reasoning_content", "reasoning", "reasoning_text"];
```

**命中的字段名被存进 `thinkingSignature`**（`:502-506`），回放时原样用作 key 写回去（见 §7.2）。这是"签名槽位"最朴素的一种用法 —— 记住上游用的是哪个字段名。

---

## 4. 模型元数据：窗口 / 定价 / 能力位

### 4.1 存在哪：`Model<TApi>`（`types.ts:761-788`）

```ts
export interface Model<TApi extends Api> {
	id: string; name: string; api: TApi; provider: ProviderId; baseUrl: string;
	reasoning: boolean;                       // :767  能力位：是否支持思考
	thinkingLevelMap?: ThinkingLevelMap;      // :772  pi 的 6 档 → provider 私有值；null = 该档不支持
	input: ("text" | "image")[];              // :773  能力位：模态
	cost: ModelCost;                          // :774
	contextWindow: number;                    // :775
	maxTokens: number;                        // :776
	headers?: Record<string, string>;
	compat?: /* 条件类型，见 §2.4 */;
}
```

定价结构支持**请求级阶梯价**（`types.ts:743-758`）：

```ts
export interface ModelCostRates { input; output; cacheRead; cacheWrite; }   // 单位：$/百万 token
export interface ModelCostTier extends ModelCostRates { inputTokensAbove: number; }
export interface ModelCost extends ModelCostRates {
	/** Request-wide pricing tiers. The highest matching input threshold applies to the full request. */
	tiers?: ModelCostTier[];
}
```

思考档位共 **6 档**（`types.ts:79-80`）：`minimal | low | medium | high | xhigh | max`，加上 `off` 共 7 个值（`models.ts:661`）。

### 4.2 **不是硬编码，也不是运行时拉取 —— 是构建期生成**

这是本节最重要的事实，链路有 4 层：

**① 生成脚本**：`scripts/generate-models.ts`（**2762 行**）。数据源在 `:1093-1095`：

```ts
console.log("Fetching models from models.dev API...");
const response = await fetch("https://models.dev/api.json");
if (!response.ok) throw new Error(`models.dev API returned ${response.status}`);
```

另有 3 个 provider 直接打各家 `/models` 端点：NVIDIA（`:950`）、OpenRouter（`:972`）、Vercel AI Gateway（`:1034`）。

**② 落成 JSON**：写进 `src/providers/data/<provider>.json`。这个目录**被 gitignore**：

```bash
$ grep -n "data" /Users/overkazaf/playground/research/pi/pi-mono/.gitignore
11:packages/ai/src/providers/data/

$ ls packages/ai/src/providers/data
ls: src/providers/data: No such file or directory      # ← 本次 checkout 实测：不存在
```

**③ 薄壳 shard**：仓库里 commit 的是 **37 个 8 行的 `*.models.ts`**（`ls src/providers/*.models.ts | wc -l` → 37）。整份 `anthropic.models.ts` 就这么长：

```ts
// This file is auto-generated by scripts/generate-models.ts
// Do not edit manually - run 'npm run generate-models' to update
import values from "./data/anthropic.json" with { type: "json" };
import { flattenModelCatalog, type ModelCatalog } from "../model-catalog.ts";
export const ANTHROPIC_MODELS: ModelCatalog<typeof values, "anthropic"> = flattenModelCatalog("anthropic", values);
```

`flattenModelCatalog`（`src/model-catalog.ts:22-27`，**整文件 27 行**）只做一件事：把 `{ api: { modelId: model } }` 摊平成 `{ modelId: model }`，同时靠 `typeof values` 把 **JSON 的字面量类型**升成 TS 类型 —— 于是 `getBuiltinModel("anthropic", "claude-opus-4-7")` 有精确类型。

**④ 构建期强校验**：`package.json:41` `"build:offline": "npm run check:model-data && tsgo ..."`，`scripts/check-model-data.ts:10-15`：

```ts
validateGeneratedModelData(packageRoot);
…
console.error("\nModel data is missing or stale. Run `npm run hydrate:model-data` from the repository root.");
```

校验靠 manifest（`scripts/model-data.ts:5-15`）：`schemaVersion: 3` + `generatedAt` + `structureHash`（对"provider → modelId → api"三元组做 sha256，`:111-118`）+ 每文件 hash。

> **上 PPT 的点**：pi 的模型目录是**"构建期快照 + 结构哈希校验"**，不是硬编码也不是运行时拉取。好处：运行时零网络、零延迟、可 tree-shake；代价：**目录会过期，必须重新构建才能更新价格**。`getBuiltinModelDataGeneratedAt()`（`all.ts:72-75`）就是把 manifest 里的 `generatedAt` 暴露给上层，让 UI 能显示"目录是什么时候的"。

### 4.3 运行时还有一条动态覆盖通道

`createProvider` 的 `fetchModels`（`models.ts:544`）+ `refreshModels`（`:596-617`）：

```ts
const stored = await context.store.read();                    // :600  先恢复本地缓存
if (stored) dynamicModels = stored.models.filter(m => m.provider === input.id)…
if (!context.allowNetwork || context.signal?.aborted) return; // :606  离线就到此为止
const refreshed = await fetchModels(context);                 // :607
dynamicModels = refreshed;
await context.store.write({ models: refreshed, checkedAt: Date.now() });  // :610
```

合并策略是**动态覆盖同 id、追加新 id**（`:561-569`），并且用 `inflightRefresh` 做了单飞去重（`:598`、`:611-613`）。

**实测：内置 provider 里只有 `radius` 实现了它**：

```bash
$ grep -ln "refreshModels" src/providers/*.ts
src/providers/radius.ts
```

（其他动态 provider 如 openrouter/nvidia/vercel 的动态目录是在**生成脚本里**抓的，不是运行时。）

### 4.4 模型总数

⚠️ **无法实测**（`data/` 不存在 + 无 node_modules）。仓库自己的断言在 `test/providers.test.ts:35`：

```ts
const all = models.getModels();
expect(all.length).toBeGreaterThan(500);
```

PPT 上只能说「仓库测试断言 > 500 个模型」，**不要说成实测数字**。

另一条可引用的自述在 `README.md:5`：

> This library only includes models that support tool calling (function calling), as this is essential for agentic workflows.

---

## 5. 计费与用量统计

### 5.1 `Usage` 的形状（`types.ts:368-389`）

```ts
export interface Usage {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
	/** Subset of `cacheWrite` written with 1h retention. Only Anthropic reports this split. */
	cacheWrite1h?: number;                                        // :374
	/** … This is a subset of `output`: `output` already includes these tokens. */
	reasoning?: number;                                           // :380
	totalTokens: number;
	cost: { input; output; cacheRead; cacheWrite; total };
}
```

两条容易讲错、注释里写死的语义：

- **`reasoning` 是 `output` 的子集，不是额外的**（`:376-379`）。
- **`cacheWrite1h` 是 `cacheWrite` 的子集**（`:373`），只有 Anthropic 报。

### 5.2 计费：**唯一函数** `calculateCost`（`src/models.ts:639-659`）

```ts
export function calculateCost<TApi extends Api>(model: Model<TApi>, usage: Usage): Usage["cost"] {
	const inputTokens = usage.input + usage.cacheRead + usage.cacheWrite;      // :640 ★ 阶梯价按"总输入"判
	let rates: ModelCostRates = model.cost;
	let matchedThreshold = -1;
	for (const tier of model.cost.tiers ?? []) {                              // :643-648 取最高命中档
		if (inputTokens > tier.inputTokensAbove && tier.inputTokensAbove > matchedThreshold) {
			rates = tier; matchedThreshold = tier.inputTokensAbove;
		}
	}
	// Anthropic charges 2x base input for 1h cache writes.
	const longWrite = usage.cacheWrite1h ?? 0;                                // :651
	const shortWrite = usage.cacheWrite - longWrite;                          // :652
	usage.cost.input     = (rates.input     / 1000000) * usage.input;
	usage.cost.output    = (rates.output    / 1000000) * usage.output;
	usage.cost.cacheRead = (rates.cacheRead / 1000000) * usage.cacheRead;
	usage.cost.cacheWrite = (rates.cacheWrite * shortWrite + rates.input * 2 * longWrite) / 1000000;  // :656 ★
	usage.cost.total = usage.cost.input + usage.cost.output + usage.cost.cacheRead + usage.cost.cacheWrite;
	return usage.cost;
}
```

三个可上 PPT 的锐利点：

1. **阶梯价是"请求级"而非"分段累进"**：`types.ts:756` 注释明写 *"The highest matching input threshold applies to the full request."* —— 超过 200k 就**整个请求**都按高价算，不是超出部分才涨价。
2. **1h cache write 单独按 `input * 2` 计价**（`:656`），因为 Anthropic 的 1h 写入是基础输入价的 2 倍。有专门测试 `test/anthropic-cache-write-1h-cost.test.ts`。
3. **`cost` 是被就地 mutate 的**（函数既返回也改传入对象），调用方是各 provider 的流循环。

### 5.3 token 从哪来：**优先信 provider，缺了才估**

**A. provider 上报**（Anthropic 为例，`anthropic-messages.ts:574-586`，在 `message_start` 就先记一次）：

```ts
output.usage.input      = event.message.usage.input_tokens || 0;
output.usage.output     = event.message.usage.output_tokens || 0;
output.usage.cacheRead  = event.message.usage.cache_read_input_tokens || 0;
output.usage.cacheWrite = event.message.usage.cache_creation_input_tokens || 0;
output.usage.cacheWrite1h = event.message.usage.cache_creation?.ephemeral_1h_input_tokens || 0;
// Anthropic doesn't provide total_tokens, compute from components
output.usage.totalTokens = input + output + cacheRead + cacheWrite;
calculateCost(model, output.usage);
```

注释 `:576-577` 说明了为什么要在 `message_start` 就记：**"This ensures we have input token counts even if the stream is aborted early."**

`message_delta` 更新时**逐字段判 `!= null`**（`:718-730`），注释 `:716-717`：*"Preserves input_tokens from message_start when proxies omit it in message_delta."* —— 这是被代理坑过的痕迹。

reasoning token 走一个 SDK 类型没覆盖的字段（`:731-737`）：

```ts
// Anthropic reports reasoning tokens in `output_tokens_details.thinking_tokens` on the
// final message_delta usage (a subset of output_tokens). SDK 0.91.1 omits the field from
// its Usage type, so read it through a narrow cast. Verified against the live API.
const thinkingTokens = (event.usage as { output_tokens_details?: { thinking_tokens?: number } })
	.output_tokens_details?.thinking_tokens;
```

**B. 本地估算**（`src/utils/estimate.ts`，**143 行**），只在需要"当前上下文有多大"时用：

```ts
const CHARS_PER_TOKEN = 4;            // :14
const ESTIMATED_IMAGE_CHARS = 4800;   // :15  一张图按 4800 字符 ≈ 1200 token 估

export function calculateContextTokens(usage: Usage): number {                    // :17-19
	return usage.totalTokens || usage.input + usage.output + usage.cacheRead + usage.cacheWrite;
}
export function estimateTextTokens(text: string): number {                        // :37-39
	return Math.ceil(text.length / CHARS_PER_TOKEN);
}
```

`ContextUsageEstimate`（`:3-12`）的设计很聪明：**「最近一次 assistant 上报的 usage」+「其后消息的字符估算」**，即 `tokens = usageTokens + trailingTokens`。已确定的部分用真值，只有尾巴用估。

估算的一个直接用途是**输出预算钳位**（`src/api/simple-options.ts:12-19`）：

```ts
const CONTEXT_SAFETY_TOKENS = 4096;
export function clampMaxTokensToContext(model, context, maxTokens) {
	if (model.contextWindow <= 0) return Math.max(1, maxTokens);
	const available = model.contextWindow - estimateContextTokens(context).tokens - CONTEXT_SAFETY_TOKENS;
	return Math.min(maxTokens, Math.max(1, available));
}
```

### 5.4 cache 命中怎么计

- **计数**：`cacheRead` / `cacheWrite` 由 provider 直接上报（见上）。
- **计价**：`cacheRead` 用 `rates.cacheRead`；`cacheWrite` 拆 short/long 两段（§5.2）。
- **怎么让它命中**：`StreamOptions.cacheRetention: "none" | "short" | "long"`（`types.ts:101`、`:136`），默认 `"short"`。Anthropic 侧的映射（`anthropic-messages.ts:49-72`）：

```ts
function resolveCacheRetention(cacheRetention?, env?): CacheRetention {
	if (cacheRetention) return cacheRetention;
	if (getProviderEnvValue("PI_CACHE_RETENTION", env) === "long") return "long";   // :53 环境变量后门
	return "short";
}
const ttl = retention === "long" && getAnthropicCompat(model).supportsLongCacheRetention ? "1h" : undefined;
return { retention, cacheControl: { type: "ephemeral", ...(ttl && { ttl }) } };
```

**cache breakpoint 打在 4 个位置**（Anthropic）：system prompt（`:981`/`:988`/`:997` 区域）、**最后一个 tool 定义**（`:1320` `index === tools.length - 1`）、**最后一条 user 消息的最后一个 block**（`:1256-1273`）。

OpenAI 侧走 `prompt_cache_key`，且有个 8 行的小文件专门管长度（`src/api/openai-prompt-cache.ts:1-8`）：

```ts
export const OPENAI_PROMPT_CACHE_KEY_MAX_LENGTH = 64;
export function clampOpenAIPromptCacheKey(key: string | undefined): string | undefined {
	if (key === undefined) return undefined;
	const chars = Array.from(key);
	if (chars.length <= OPENAI_PROMPT_CACHE_KEY_MAX_LENGTH) return key;
	return chars.slice(0, OPENAI_PROMPT_CACHE_KEY_MAX_LENGTH).join("");
}
```

还有 **session affinity**：`sessionId` 通过 header 送出去，让网关把请求路由到同一副本以提高 cache 命中率（`types.ts:606-613` 注释点名 Fireworks）。

---

## 6. 重试 / 限流 / 错误分类

### 6.1 全局错误约定：**流不抛异常，错误编码进流**

`types.ts:312-324` 的 `StreamFunction` 契约注释是全包的宪法：

```
// Contract:
// - Must return an AssistantMessageEventStream.
// - Once invoked, request/model/runtime failures should be encoded in the
//   returned stream, not thrown.
// - Error termination must produce an AssistantMessage with stopReason
//   "error" or "aborted" and errorMessage, emitted via the stream protocol.
```

实现这个契约的是 `lazyStream`（`src/api/lazy.ts:46-61`）—— **同步返回流，异步做 auth 解析和模块加载**：

```ts
export function lazyStream(model, setup): AssistantMessageEventStream {
	const outer = new AssistantMessageEventStream();
	setup()
		.then((inner) => forwardStream(outer, inner))
		.catch((error) => {
			const message = createSetupErrorMessage(model, error);   // :4-23 造一条 stopReason:"error" 的空消息
			outer.push({ type: "error", reason: "error", error: message });
			outer.end(message);
		});
	return outer;
}
```

`lazyApi`（`:68-75`）在此之上做**按需 `import()`**：`src/api/*.lazy.ts` 共 **11 个**（`ls src/api/*.lazy.ts | wc -l` → 11，其中 9 个是 4 行的薄壳，`bedrock-converse-stream.lazy.ts` 30 行、`openrouter-images.lazy.ts` 10 行），作用是让"用 Anthropic 就不加载 openai SDK"。

### 6.2 **两层重试**

#### 第一层：SDK 级 —— `retryProviderRequest`（`src/utils/provider-retry.ts`，125 行）

存在理由写在 `:97-104`：

> Reproduce the retry behavior used by the OpenAI and Anthropic SDKs while making their backoff sleep **interruptible**. Their built-in retry timers ignore the request AbortSignal, so callers must invoke the SDK with `maxRetries: 0` and wrap the request with this helper.

对应地，所有 SDK 调用都传 `maxRetries: 0`（实测 3 处）：

```bash
$ grep -n "maxRetries: 0" src/api/*.ts
src/api/anthropic-messages.ts:557
src/api/openai-completions.ts:240
src/api/openai-responses.ts:147
```

**重试判据**（`provider-retry.ts:23-35`）—— 状态码维度：

```ts
function isRetryableProviderError(error: ProviderError): boolean {
	const shouldRetry = error.headers?.get("x-should-retry");
	if (shouldRetry === "true") return true;          // :25 provider 显式说重试
	if (shouldRetry === "false") return false;        // :26 provider 显式说别重试
	if (error.status === undefined) return true;      // :28 连状态码都没有（网络层）→ 重试
	return error.status === 408 || error.status === 409 || error.status === 429 || error.status >= 500;
}
```

**退避算法**（`:51-67`）—— 三级优先：

```ts
const retryAfterMs = error.headers?.get("retry-after-ms");   // ① :52
…
const retryAfter = error.headers?.get("retry-after");        // ② :58 支持秒数和 HTTP-date
…
const exponentialDelay = Math.min(0.5 * 2 ** retryIndex, 8) * 1000;   // ③ :65 指数退避，封顶 8s
return exponentialDelay * (1 - Math.random() * 0.25);                // :66 ★ ±25% 抖动
```

**服务端要求过长的等待会直接失败**（`:37-49`，默认上限 60s，`:1` `DEFAULT_MAX_RETRY_DELAY_MS = 60_000`）：

```ts
if (maxDelayMs > 0 && delayMs > maxDelayMs) {
	throw new Error(`Server requested ${Math.ceil(delayMs/1000)}s retry delay (max: ${Math.ceil(maxDelayMs/1000)}s). ${providerErrorMessage}`);
}
```

设计意图（`types.ts:178-185` 注释）：**宁可失败给外层，让用户看得见，也不要静默睡 5 分钟。** 注意这个错误消息里含 `"retry delay"`，而 `"retry delay"` 恰好在第二层的**可重试**白名单里（`retry.ts:79`）—— 两层是刻意串联的。

`:114` 还有一句细节注释：*"Each retry is a fresh SDK request, so X-Stainless-Retry-Count remains zero."*

#### 第二层：语义级 —— `retryAssistantCall`（`src/utils/retry.ts`，227 行）

这一层**不看状态码，看 `AssistantMessage.errorMessage` 的文本**，因为到这一层错误已经被编码进消息了。

**分类器 `isRetryableAssistantError`（`:222-227`）**：

```ts
export function isRetryableAssistantError(message: AssistantMessage): boolean {
	if (message.stopReason !== "error" || !message.errorMessage) return false;
	const errorMessage = message.errorMessage;
	if (NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN.test(errorMessage)) return false;   // ★ 黑名单先判
	return RETRYABLE_PROVIDER_ERROR_PATTERN.test(errorMessage);
}
```

**黑名单（不重试）8 条**（`:7-24`）—— 都是"重试也没用"的账户级问题：`GoUsageLimitError` / `FreeUsageLimitError` / `Monthly usage limit reached` / `available balance` / `insufficient_quota` / `out of budget` / `quota exceeded` / `billing`。

**白名单（重试）40 条**（`:26-89`），分 6 组，每组都有注释说明来自哪个 issue：

| 组 | 例子 | 行号 |
|---|---|---|
| 负载/HTTP 状态 | `overloaded`、`rate.?limit`、`429`、`500`、`502`、`503`、`504`、**`524`** | `:28-39` |
| 网关文本 | `provider.?returned.?error`（注释：OpenRouter #2264） | `:43` |
| 网络/代理 | `fetch failed`、`getaddrinfo`、`ENOTFOUND`、`EAI_AGAIN`、`upstream.?connect`、`reset before headers`、`socket hang up`、`timeout`、`terminated` | `:48-63` |
| WebSocket | `websocket.?closed`、`websocket.?error` | `:66-67` |
| **流提前结束** | `ended without`、`stream ended before message_stop`（#4433）、`http2 request did not get a response`（Bedrock #3594） | `:72-75` |
| **provider 自己说"再试一次"** | `you can retry your request`、`try your request again`、`please retry your request`（#6019） | `:83-85` |

**退避在这一行**（`retry.ts:195`）：

```ts
const delayMs = policy!.baseDelayMs * 2 ** (attempt - 1);
```

⚠️ **一个可以当"读代码要读到底"的例子**：`:101` 的 doc 注释写着 *"Per-attempt delay is `baseDelayMs * 2^(attempt-1)` **before jitter**"*，但 `:195` 的实现**没有任何 jitter** —— 抖动只存在于第一层（`provider-retry.ts:66`）。**注释和代码不一致**。

**四个提前返回点**（`retryAssistantCall`，`:172-191`）：

```ts
if (response.stopReason === "aborted") { … return response; }        // :176 abort 永不重试
if (response.stopReason !== "error")  { … return response; }         // :182 成功
if (attempt >= maxAttempts || !isRetryableAssistantError(response))  // :188 预算耗尽 或 不可重试
	{ … return response; }
```

**退避期间被 abort 会被归一化成 aborted 消息**（`:200-208`），注释 `:198-199`：*"so callers do not need to care when cancellation happened."*

```ts
} catch (error) {
	await callbacks?.onRetryFinished?.(false, attempt, lastRetry.errorMessage);
	if (error instanceof RetrySleepAbortError) {
		return { ...response, stopReason: "aborted", errorMessage: undefined };
	}
	throw error;
}
```

**策略从哪来**（跨包）：`RetryPolicy` 定义在 `retry.ts:97-103`，默认值在 coding-agent 侧 —— `/Users/overkazaf/playground/research/pi/pi-mono/packages/coding-agent/src/core/settings-manager.ts:818-823`：

```ts
getRetrySettings(): { enabled: boolean; maxRetries: number; baseDelayMs: number } {
	return {
		enabled: this.getRetryEnabled(),
		maxRetries: this.settings.retry?.maxRetries ?? 3,
		baseDelayMs: this.settings.retry?.baseDelayMs ?? 2000,
	};
}
```

即默认 **3 次重试，2s → 4s → 8s**（`settings-manager.ts:32` 注释原文：`// default: 2000 (exponential backoff: 2s, 4s, 8s)`）。

### 6.3 第三类错误：**上下文溢出**（`src/utils/overflow.ts`，168 行）

这是**独立于重试**的一条分支（`retry.ts:216-220` 注释：*"Callers should first handle context overflow separately, then apply their own retry budget"*）。

`OVERFLOW_PATTERNS` 共 **25 条正则**（`:37-63`），而 `:9-35` 的注释是一张**"各家 provider 溢出错误文案对照表"**，直接可以做一页 PPT：

```
 * - Anthropic: "prompt is too long: 213462 tokens > 200000 maximum"
 * - OpenAI: "Your input exceeds the context window of this model"
 * - Google: "The input token count (1196265) exceeds the maximum number of tokens allowed (1048575)"
 * - xAI: "This model's maximum prompt length is 131072 but the request contains 537812 tokens"
 * - Groq: "Please reduce the length of the messages or completion"
 * - Cerebras: "400/413 status code (no body)"
 * - z.ai: Does NOT error, accepts overflow silently - handled via usage.input > contextWindow
 * - Xiaomi MiMo: Truncates input to fill contextWindow exactly, then returns finish_reason "length"
 *   with output=0 (no room left to generate).
```

最后两条是"**没有错误消息的溢出**"—— z.ai 静默接受、Xiaomi 静默截断，只能靠 `usage.input > contextWindow` 或 `stopReason === "length" && output === 0` 反推。

还有 `NON_OVERFLOW_PATTERNS`（`:74-78`）做**排除**，注释说明了原因：Bedrock 的限流错误文案是 `"ThrottlingException: Too many tokens, please wait before trying again."`，会误命中 `/too many tokens/i`。

### 6.4 错误体归一化（`src/utils/error-body.ts`，149 行）

文件头注释（`:1-14`）解释了痛点：**SDK 错误对象把 HTTP body 藏在各自不同的字段名下**，只读 `error.message` 会得到 `"403 status code (no body)"` 这种废话。

`normalizeProviderError`（`:38-53`）按 SDK 字段顺序探测（`:56-59` 注释）：

> `statusCode`（Mistral）→ `status`（`openai`、`@google/genai`）→ `$metadata.httpStatusCode`（Bedrock）→ `$response.statusCode`（Bedrock）

body 截断上限 **4000 字符**（`:16` `MAX_PROVIDER_ERROR_BODY_CHARS`）。

另有 `src/utils/diagnostics.ts` 提供 `AssistantMessageDiagnostic`（`:8-13`），挂在 `AssistantMessage.diagnostics` 上（`types.ts:407`，注释：*"Redacted provider/runtime diagnostics for failures and recoveries"*）。

---

## 7. thinking / reasoning 内容怎么处理

**总答案：尽可能保留并原样回灌；无法回灌时降级成文本；跨模型时丢弃。** 三种策略在代码里都能定位到。

### 7.1 Anthropic：签名在则回灌，签名缺失则降级成 text

回灌逻辑 `anthropic-messages.ts:1178-1212`：

```ts
} else if (block.type === "thinking") {
	// Redacted thinking: pass the opaque payload back as redacted_thinking
	if (block.redacted) {
		blocks.push({ type: "redacted_thinking", data: block.thinkingSignature! });   // :1180-1185
		continue;
	}
	const thinkingSignature = block.thinkingSignature;
	const hasThinkingSignature = !!thinkingSignature && thinkingSignature.trim().length > 0;
	if (block.thinking.trim().length === 0 && !hasThinkingSignature) continue;        // :1189 空块丢弃
	// If thinking signature is missing/empty (e.g., from aborted stream),
	// convert to plain text for Anthropic. Some compatible providers emit
	// and accept empty signatures, so let marked models preserve the block.
	if (!hasThinkingSignature) {
		blocks.push(allowEmptySignature
			? { type: "thinking", thinking: sanitizeSurrogates(block.thinking), signature: "" }   // :1196-1200
			: { type: "text",     text:     sanitizeSurrogates(block.thinking) });                // :1201-1204
	} else {
		blocks.push({ type: "thinking", thinking: …, signature: thinkingSignature });             // :1207-1211
	}
```

关键：**中断的流会产生"有思考文本但没签名"的块**，这种块 Anthropic 不接受，只能降级成 text。`allowEmptySignature` compat 位（`types.ts:638`）给少数接受空签名的兼容 provider 开口子（测试：`test/anthropic-empty-thinking-signature-compat.test.ts`、`test/xiaomi-token-plan-ams-anthropic-empty-signature-smoke.test.ts`）。

### 7.2 OpenAI Completions：签名 = 字段名，直接当 key 写回

`openai-completions.ts:1100-1128`：

```ts
if (compat.requiresThinkingAsText) {
	// Convert thinking blocks to plain text (no tags to avoid model mimicking them)
	const thinkingText = nonEmptyThinkingBlocks.map(b => sanitizeSurrogates(b.thinking)).join("\n\n");
	assistantMsg.content = [{ type: "text", text: thinkingText }, ...assistantTextParts];   // :1109
} else {
	…
	let signature = nonEmptyThinkingBlocks[0].thinkingSignature;
	if (model.provider === "opencode-go" && signature === "reasoning") signature = "reasoning_content";  // :1122
	if (signature && signature.length > 0) {
		(assistantMsg as any)[signature] = nonEmptyThinkingBlocks.map(b => b.thinking).join("\n");       // :1126 ★
	}
}
```

`(assistantMsg as any)[signature] = …` —— **用记下来的字段名动态写回**。这就是 §3.7 里"把命中的 reasoning 字段名存进 thinkingSignature"的收尾。

注释 `:1105` 还留了个坑的说明：**降级成文本时不加 `<thinking>` 标签**，因为模型会开始模仿它。

### 7.3 OpenAI Responses：签名 = **整个 reasoning item 的 JSON**

`openai-responses-shared.ts:662-666`：

```ts
if (item.type === "reasoning" && slot?.type === "thinking") {
	…
	slot.block.thinkingSignature = JSON.stringify(item);   // :666 ★ 整个 item 序列化进签名
}
```

回灌时反序列化（`:221-222`）：

```ts
if (block.thinkingSignature) {
	const reasoningItem = JSON.parse(block.thinkingSignature) as ResponseReasoningItem;
```

还有一个 Azure 专用补丁（`:515-529`）：Azure 会在 `response.output_item.done` 里漏掉 `encrypted_content`，pi 用终态 response 里的值**补回签名**，保证 `store:false` 模式下的多轮连续性。

text 块也有签名（`:48-60` 的 `encodeTextSignatureV1` / decode，`:677`），编码成 `{v:1, id, phase}`。

### 7.4 Google：`thoughtSignature` 可以出现在**任何** part 上

`google-shared.ts:20-34` 的注释是全包最容易讲错的一处：

```
 * - `thought: true` is the definitive marker for thinking content (thought summaries).
 * - `thoughtSignature` is an encrypted representation of the model's internal thought process
 * - `thoughtSignature` can appear on ANY part type (text, functionCall, etc.) - it does NOT
 *   indicate the part itself is thinking content.
```

`:41` 还记了一个 backend 差异：*"Some backends only send `thoughtSignature` on the first delta for a given part/block; later deltas may omit it."*

这也是为什么 canonical 的 `ToolCall` 上要有 `thoughtSignature` 字段（`types.ts:365`）—— 签名可能挂在工具调用上而不是思考块上。

### 7.5 跨模型/跨 provider：**丢弃**

`google-shared.ts:129-161` 和 `src/api/transform-messages.ts:101-115` 是同一条规则的两处实现：

```ts
if (block.type === "thinking") {
	// Redacted thinking is opaque encrypted content, only valid for the same model.
	…
	// For same model: keep thinking blocks with signatures (needed for replay)
	// even if the thinking text is empty (OpenAI encrypted reasoning)
	if (isSameModel && block.thinkingSignature) return block;       // transform-messages.ts:109
	// Skip empty thinking blocks, convert others to plain text
	if (!block.thinking || block.thinking.trim() === "") return [];  // :111
	return { type: "text", text: block.thinking };                   // :113-115
}
```

即三分支：**同模型 + 有签名 → 原样保留；空 → 丢；其余 → 降级成 text**。

`transform-messages.ts:188-192` 还处理"最后一条 assistant 消息是错误/中断态"的情况：

```
 * - May have partial content (reasoning without message, incomplete tool calls)
 * - Replaying them can cause API errors (e.g., OpenAI "reasoning without following item")
```

### 7.6 思考档位的映射与钳位

pi 的 6 档 → provider 私有值靠 `Model.thinkingLevelMap`（`types.ts:768-772`）：

> *"Missing keys use provider defaults. **null marks a level as unsupported**."*

`getSupportedThinkingLevels`（`models.ts:663-672`）：

```ts
if (!model.reasoning) return ["off"];
return EXTENDED_THINKING_LEVELS.filter((level) => {
	const mapped = model.thinkingLevelMap?.[level];
	if (mapped === null) return false;                              // :668 显式不支持
	if (level === "xhigh" || level === "max") return mapped !== undefined;  // :669 ★ 高档必须显式声明
	return true;                                                    // 低档默认支持
});
```

`clampThinkingLevel`（`:674-693`）：**先往上找，再往下找**，保证任何请求档位都能落到一个可用档。

token 预算派生（`src/api/simple-options.ts:52-77`），给"按 token 预算"的老模型用：

```ts
const defaultBudgets: ThinkingBudgets = { minimal: 1024, low: 2048, medium: 8192, high: 16384 };  // :59-64
…
const maxTokens = baseMaxTokens === undefined ? modelMaxTokens : Math.min(baseMaxTokens + thinkingBudget, modelMaxTokens);
if (maxTokens <= thinkingBudget) thinkingBudget = Math.max(0, maxTokens - minOutputTokens);  // :73-75 留 1024 出文
```

`clampReasoning`（`:48-50`）把 `xhigh`/`max` 压回 `high`，给不认这两档的 API 用。

Anthropic 侧还分两种模式（`anthropic-messages.ts:1027-1049`）：**adaptive thinking**（`thinking: { type:"adaptive", display }` + effort，新模型）vs **budget-based**（`budget_tokens`，老模型，默认 1024）。`forceAdaptiveThinking` compat 位（`types.ts:637`）让自定义兼容 provider 也能强制走 adaptive。

---

## 8. 几个顺带挖到、上 PPT 很好用的细节

1. **`sanitizeSurrogates`**（`src/utils/sanitize-unicode.ts:21`）：**未配对的 Unicode 代理字符会让很多 provider 的 JSON 序列化炸掉**，所以每一处文本进 wire 前都过一遍。有专门测试 `test/unicode-surrogate.test.ts`。

2. **Deferred tools**（`src/utils/deferred-tools.ts:8-38`）：工具可以**在会话中途才对模型可见** —— `ToolResultMessage.addedToolNames`（`types.ts:428`）声明"这条结果之后哪些工具可用了"，`splitDeferredTools` 把工具集切成 `immediate` / `deferred`。Anthropic 侧靠 `tool_reference` 块（compat `supportsToolReferences`，`types.ts:647`），Kimi 有自己的模式（`deferredToolsMode: "kimi"`，`:569`）。

3. **约束采样**（`src/api/constrained-sampling.ts`，148 行 + `types.ts:459-478`）：`Tool.constrainedSampling` 支持 `json_schema`（strict）和 `grammar`（Lark / regex 两种变体），流式时还得**把 grammar 工具的裸输出反包成 JSON**（`GrammarToolInputJsonBuffer`，`:15-19`）。

4. **`faux` provider**（`src/providers/faux.ts`）：内置的可编程假 provider，测试用。做 agent 框架的人容易忘记这一层。

5. **可 tree-shake 的设计是显式的**：`package.json:9-13` 的 `sideEffects` 只列了 3 个文件；`types.ts:202-206` 注释解释为什么 `ApiOptionsMap` 用 type-only import（*"Type-only imports from API implementation modules are erased at emit, so this is tree-shake safe."*）；`*.lazy.ts` 10 个文件做动态 import。

---

## 最适合上 PPT 的 5 条硬事实

1. **38 个 provider、10 种 wire API、21429 行代码 —— 但 canonical 类型只有一个文件、795 行。**
   `src/providers/all.ts:87-128` 列出 38 个 provider 工厂（`sed -n '88,127p' src/providers/all.ts | grep -oE '[a-zA-Z]+Provider\(\)' | wc -l` → 38），`src/types.ts:16-26` 定义 10 种 `KnownApi`，全部收敛到 `src/types.ts` 里的 `Context` / `Message` / `AssistantMessage` / `AssistantMessageEvent`。约 20 个 provider 共用同一套 `openai-completions` 实现。

2. **"用不用官方 SDK"不是立场问题，是逐个 API 的工程判断 —— 8 个用 SDK，2 个手写 SSE。**
   Anthropic / OpenAI / Azure / Mistral / Bedrock / Google(×2) 走官方 SDK（`package.json:62-74` 共 5 个 SDK 依赖）；`openai-codex-responses.ts:764` 和 `pi-messages.ts:267` 各自手写 `getReader()` + `indexOf("\n\n")` 的 SSE 解析器，因为一个走 ChatGPT 私有协议（zstd 请求体 + WebSocket），一个**是 pi 自己定义的协议**。

3. **模型元数据是"构建期从 models.dev 抓的快照"，既非硬编码也非运行时拉取 —— 而且这份数据不进 git。**
   `scripts/generate-models.ts:1094` `fetch("https://models.dev/api.json")` → 落成 `src/providers/data/*.json` → 被 `.gitignore:11` 忽略（本次 checkout 实测该目录不存在）→ 仓库只 commit 37 个 8 行的薄壳 `*.models.ts` → `npm run build` 前置 `check-model-data` 用 sha256 结构哈希校验（`scripts/model-data.ts:111-118`）。**代价是：不重新构建就拿不到新价格。**

4. **计费只有一个 20 行函数，但里面藏着两条容易算错的规则。**
   `src/models.ts:639-659`：① **阶梯价是"请求级"不是"累进"** —— `types.ts:756` 注释原文 *"The highest matching input threshold applies to the full request"*，超阈值则整个请求都按高价；② **Anthropic 的 1h cache write 按 `input * 2` 单独计价**（`models.ts:656`），不是按 `cacheWrite` 费率。另外 `usage.reasoning` 是 `output` 的**子集**不能重复加（`types.ts:376-379`）。

5. **重试分两层：SDK 层看状态码，语义层看错误文案里的 35 条正则。**
   第一层 `provider-retry.ts:23-35`（408/409/429/5xx + `x-should-retry` 头）、退避 `:65-66`（`min(0.5*2^n, 8)s` + **±25% 抖动**）、服务端要求 >60s 直接失败（`:1`、`:43-47`）；第二层 `retry.ts:222-227` 用 **40 条可重试正则**（`:26-89`，含 `524`、`socket hang up`、`stream ended before message_stop`、`you can retry your request`）减去 **8 条不可重试的账单/配额黑名单**（`:7-24`），退避在 `retry.ts:195` 一行 `baseDelayMs * 2 ** (attempt-1)`，默认 3 次、2s/4s/8s（`packages/coding-agent/src/core/settings-manager.ts:818-823`）。
   👉 **额外彩蛋**：`retry.ts:101` 的注释写着 "before jitter"，但 `:195` 的实现**根本没有 jitter** —— 注释与代码不符，是个现成的"读代码要读到实现"的例子。
