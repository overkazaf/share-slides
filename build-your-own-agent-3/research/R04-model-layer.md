# R04 — omp 模型层取证：catalog 模型知识库 / dialect 方言层 / provider & auth broker

> 取证对象：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi`（HEAD `09a7c8656`，2026-08-01）
> 对比基准：`/Users/overkazaf/playground/research/pi/pi-mono`（HEAD `583f153d5`，2026-08-01）
> 证据等级：`[A]` = 本地代码/数据亲自点算并给出 `文件:行号`；`[B]` = 仓库内 README/docs 已核实；`[C]` = 推测（只出现在文末「存疑区」）
> 数字全部为本次在 HEAD 上重新点算，复现命令见文末附录 A。

---

## 0. 结论先行

1. **omp 把「模型元数据」当成一个独立的、可编译的软件制品来做**，而不是一张写死的表。`packages/catalog` 是一个独立 npm 包，内含一份 2.1 MB、**63 家 provider / 4,106 条模型记录**的 `models.json`，由 `bun run gen:models` 从 stencil.so（models.dev 的压缩镜像）+ 40 家 provider 的实时 `/v1/models` 抓取 + 手写兜底表三路合流生成。`[A]`
2. **自建模型库解决的是一个可量化的真痛点**：同一个模型在不同网关下 id 不同、价格不同、上下文窗口不同。本次点算：**543 个模型名被 2 家以上 provider 提供，其中 376 个各家标的输入价不一致，254 个各家标的上下文窗口不一致**。`[A]` 靠猜必然错。
3. **`dialect` 是绕开 native tool calling 的完整替代通道**：11 种方言、每种自带 prompt 模板 + 流式扫描器 + 历史回写渲染器。它不是"更好的 tool calling"，而是"当网关/推理服务把 native tool calling 做坏时的兜底"，并且要处理一个 native 通道不存在的失败模式——**模型自己伪造工具执行结果**（fabrication），omp 检测到即中断上游请求止损。`[A]`
4. **`packages/wire` 不是 LLM 协议层**——这是本次取证纠正的一个常见误解。它是 collab 实时会话（浏览器旁观/协作）的共享 JSON 协议契约包，零运行时依赖，不做编解码、不做加密、不做路由。`[A][B]` LLM 侧的"wire"分散在 `packages/ai/src/providers/*-wire.ts` 与 `packages/catalog/src/wire/`。
5. **auth broker 的核心是「唯一写者 + 哨兵占位」**：客户端快照里每个 `refresh` 字段都被替换成字面量 `"__remote__"`（`REMOTE_REFRESH_SENTINEL`），过期时回调 broker 服务端刷新；协议 schema 双向强制（上传拒绝哨兵、快照必须是哨兵）。"唯一写者"不是靠约定，而是靠**客户端硬拒绝 + SQLite 行级持久租约 + 进程内单飞**三层落实 —— 因为 broker 主机上仍然是多进程共用同一个 `agent.db`。但要说清两件事：**普通客户端拿到的 access token 是真的**（只有 gateway 的下游客户端才完全看不到 token），且**账号池是路由策略而非授权边界**（文档原话）。`[A][B]`
6. **相对上游 pi，omp 在模型层是"重写+加厚"而非"微调"**：pi 的 `packages/ai` 共 169 个 `.ts` / 21,429 行，**完全没有 dialect 概念**（`grep -rn "dialect\|inband" src` 零命中），模型数据甚至**不入库**（`.gitignore` 忽略 `packages/ai/src/providers/data/`，构建时现拉）。omp 的 `packages/ai` 是 278 个 `.ts` / 99,265 行，另加一个 catalog 包。`[A]`

---

## 1. `packages/catalog`：模型知识库

### 1.1 数字（本次点算，旧笔记 R08 对照）

| 指标 | 旧笔记（R08） | 本次 HEAD `09a7c8656` | 备注 |
| --- | --- | --- | --- |
| provider 家数（models.json 顶层键） | 58 | **63** | `[A]` 附录 A-1 |
| 模型记录条数 | 3,695 | **4,106** | `[A]` 附录 A-2 |
| `CATALOG_PROVIDERS` 表条目 | — | **67** | `[A]` `packages/catalog/src/provider-models/descriptors.ts:67`（表起始）；67 条中 40 条带 `catalogDiscovery`（参与生成），3 条 `specialModelManager: true` |
| dialect 方言数 | 11 | **11**（成员变了） | `[A]` `packages/catalog/src/identity/dialect.ts:3-14`；旧的 `pi` 方言已删除，新增 `minimax`（见 §3.2） |
| `models.json` 体积 | — | **2,171,711 B** | `[A]` |
| 内置 API 协议种类 | — | **14** | `[A]` `packages/catalog/src/types.ts:8-22` = `KnownApi` union；`packages/ai/src/api-registry.ts:19-32` 用类型断言保证两处不脱节 |

**为什么 63 ≠ 67**：`CATALOG_PROVIDERS` 里有 4 类 provider 不会写进 `models.json` —— 本机自托管的 `ollama` / `vllm` / `lm-studio` / `litellm` 被 `DISCOVERY_ONLY_PROVIDERS` 排除，理由写在注释里：

> "bundling them would leak machine-specific endpoints (e.g. `http://localhost:4000/v1`) into the committed snapshot"
> —— `packages/catalog/scripts/generate-models.ts:69` `[A]`

另有 `RETIRED_PROVIDERS = new Set(["wafer-pass", "wandb"])`（`generate-models.ts:70`）`[A]`。

模型数分布极不均匀（`[A]` 附录 A-2 输出）：nanogpt 810、kilo 498、openrouter 411、aimlapi 349、vercel-ai-gateway 234 —— 前 5 家聚合网关就占了 **2,302 / 4,106 ≈ 56%**；而 anthropic 只有 26、openai 51、google 42。**这本身就是"自建库"必要性的第一手证据：绝大多数条目来自网关，而网关正是 id/价格最混乱的地方。**

### 1.2 数据从哪来：三路合流 + 一路策略回炉

README 明写 `src/models.json` 禁止手改：

> "Never edit `src/models.json` by hand — it is produced from upstream sources (stencil.so, provider catalog discovery, OpenCode docs) by `scripts/generate-models.ts`"
> —— `packages/catalog/README.md` `[B]`

具体三路：

1. **上游目录**：`https://catalog.stencil.so/models.json.zstd` —— models.dev 的裁字段 + zstd 预压缩镜像。`packages/catalog/src/provider-models/openai-compat.ts:35` 定义 URL，`:116-124` 的注释给了它的工程理由：**~93 KB vs ~3.3 MB raw**，并且靠嗅探 zstd frame magic 而不是信 `content-type`；进程内单飞 + `If-None-Match` 条件请求，服务端刻意不记录 304 日志。`[A]`
2. **各家 provider 的实时 `/v1/models` 抓取**：67 条 descriptor 中 40 条带 `catalogDiscovery`，生成时用 env / `agent.db` 里的凭据去拉真实目录（`generate-models.ts:73-110` 的 `resolveProviderApiKey`，会经由 auth broker 的单飞刷新机制取 key）。`[A]` 另有针对特定厂商的专用发现器：`src/discovery/{codex,cursor,gemini,antigravity,devin,gitlab-duo-workflow,openai-compatible}.ts`，其中 cursor/devin 是走 protobuf 逆向的（`src/discovery/cursor-gen/agent_pb.ts`、`devin-gen/exa/**`）。`[A]`
3. **手写兜底/curated 种子**：如 `ANTHROPIC_CURATED_FALLBACK_MODELS`（`openai-compat.ts:245-` 起），注释写明动机：

   > "Curated Anthropic models that are live or limited-availability on the first-party `/v1/models` endpoint but that models.dev has not catalogued yet. Seeded into model generation so the bundled catalog is never gated on models.dev's update cadence"
   > —— `packages/catalog/src/provider-models/openai-compat.ts:249-253` `[A]`

   `openai-compat.ts` 单文件 **5,740 行**，就是这层"每家网关的脾气"的沉淀地。`[A]`

4. **策略回炉（generated policies）**：`scripts/generated-policies.ts`（395 行）在合流后统一重烤 thinking 能力、canonical limit 回填、Bedrock 不支持地域 id 剔除、OpenAI 上下文晋升目标链接等。`[A]`

生成后还有 **effort 变体折叠**（`src/variant-collapse.ts`，1,124 行）：把 `X` / `X-thinking`、Antigravity 的 `gemini-3.5-flash-extra-low/-low` 这类"同一个模型的不同档位 id"折成一条逻辑记录，把每档的上游 wire id 存进 `thinking.effortRouting`，请求时再解析回去。关键的自我约束写在头注释：

> "Gated on identical pricing and same api: price-divergent twins are distinct SKUs and stay separate **so billing attribution never lies**."
> —— `packages/catalog/src/variant-collapse.ts:18-21` `[A]`

### 1.3 字段有哪些（按覆盖率点算）

`[A]` 附录 A-3。4,106 条记录的字段分布：

| 字段 | 覆盖 | 说明 |
| --- | --- | --- |
| `id` / `name` / `api` / `provider` / `baseUrl` | 100% | 身份 + 路由 |
| `reasoning`（bool） | 100% | 是否推理模型 |
| `input`（`["text","image",…]`） | 100% | 模态能力位 |
| `cost{input,output,cacheRead,cacheWrite}` | 100% | **四档定价**，含 prompt cache 读写单价 |
| `contextWindow` / `maxTokens` | 100% | 上下文窗口 / 单次最大输出 |
| `thinking{mode,efforts,defaultLevel,effortMap,effortRouting,effortBudgets,…}` | 51.6%（2,117） | 思考能力的完整描述，见下 |
| `supportsComputerUse` | 50.2%（2,063） | |
| `supportsComputerUseConfig` | 40.2%（1,649） | |
| `compat` | 4.2%（174） | 每家网关的 OpenAI 兼容性偏差开关 |
| `cursorMaxMode` / `supportsTools` / `omitMaxOutputTokens` / `headers` / `applyPatchToolType` / `contextPromotionTarget` / `requestModelId` / `remoteCompaction` / `preferWebsockets` / `priority` / `premiumMultiplier` / `reasoningMode` / `useResponsesLite` | 3% ↓ | 长尾 quirk 位 |

`thinking.mode` 是一个 5 值枚举，说明"思考控制"在不同厂商根本不是一回事：`"effort" | "budget" | "google-level" | "anthropic-adaptive" | "anthropic-budget-effort"`（`packages/catalog/src/types.ts:26-31`）`[A]`。`ThinkingConfig` 里还有 `requiresEffort`（OpenRouter 的 Gemini 3.x 会报 "Reasoning is mandatory for this endpoint and cannot be disabled"，必须钳到最低档而不能关）和 `suppressWhenOff`（Cloud Code Assist 省略 config 就会套用服务端烤死的默认值，必须显式发 `thinkingBudget: 0`）—— 这两条注释（`types.ts:66-84`）本身就是最好的"为什么要建库"的素材。`[A]`

`compat`（`OpenAICompat`，`types.ts:159-` 起）是一组"这家网关到底支不支持"的开关：`supportsStore` / `supportsDeveloperRole` / `supportsMultipleSystemMessages` / `supportsReasoningEffort` / `supportsUsageInStreaming` / `enableGeminiThinkingLoopGuard` …… 默认全部"从 baseUrl 自动嗅探"，字段只是用来覆盖嗅探。`[A]`

### 1.4 别名归一化怎么做

分两条互不混用的路径，这个分工写得很清楚：

**(a) proxy/reseller 引用解析** —— `packages/catalog/src/identity/reference.ts`。目的是：给定一个二道贩子网关暴露的怪 id，找到内置库里的上游模型，**继承它的定价/限额，但保留自己的传输通道**。头注释直接给了三个真实样例：

> `[Kiro] claude-opus-4-8`、`gpt-5.4:cloud`、`vendor/claude-sonnet-4-6-thinking`
> —— `packages/catalog/src/identity/reference.ts:2-4` `[A]`

候选 id 生成是一个 BFS 队列（`reference.ts:96-138`），逐层尝试：剥方括号前后缀 → 抽"像模型 id 的段" → 去 `:cloud`/`-cloud` → 取最后一个 `/` 之后 → `:` 换 `-` → 全小写 → 剥尾部 marker。`[A]`

- **方括号剥离**（`identity/id.ts:52-77`）支持 ASCII `[]` 和中文全角 `【】`，注释里的例子是 `"[gcli转] gemini-3.1-pro-preview [假流]" -> "gemini-3.1-pro-preview"` —— 这几乎是直接对着中文二道贩子网关写的。`[A]`
- **尾部 marker 词表**（`identity/markers.ts:7-27`）18 个：`thinking, customtools, high, low, medium, minimal, xhigh, free, cloud, exacto, nitro, original, optimized, nvfp4, fp8, fp4, bf16, int8, int4`。`[A]`
- **一个精细的边界**：`search` 只在"引用查找"时算 identity-preserving，在"canonical 归并"时不算 —— 因为 Perplexity 的 `sonar-pro-search` 是和 `sonar-pro` 不同的模型，但 `claude-opus-4-6-search` 这种代理 id 应该继承上游定价。（`markers.ts:29-36`）`[A]` 这种"同一个字符串在两个语境下语义不同"的处理，是自建库比抄一张表值钱的地方。
- **兜底安全阀**：以 `@` 开头的 Portkey/gateway wire id 直接放弃模糊匹配，注释给了反例 `@modal/GLM-5-2-FP8 → devin/glm-5-2` 会匹配到不相关的条目（`reference.ts:158-160`）。`[A]`
- **谁赢**：`shouldReplaceReference`（`reference.ts:34-48`）—— 先比 contextWindow，再比 maxTokens，再优先"有完整 cache 定价"的，最后优先 first-party `openai`。另有一条特判：`xai-oauth` 的订阅制条目零定价 + 虚高 maxTokens，直接不进索引，免得压过公开定价（`reference.ts:20-30`）。`[A]`

**(b) canonical 归并** —— `packages/catalog/scripts/equivalence.ts`（build-only）。把跨 provider 的同一模型收敛成一条 `CanonicalModelRecord`，来源标 `"override" | "bundled" | "heuristic" | "fallback"`。词表和 (a) 刻意分开维护，理由见 `equivalence.ts:49-53`。`[A]`

**(c) provider 优先级** —— `identity/priority.ts:1-42` 是一张三段式硬编码顺序表：first-party 原生账号（`openai-codex, anthropic, openai, google-gemini-cli, …`）> 高质量聚合/托管推理（`fireworks, cerebras, baseten, openrouter, aimlapi, together`）> 通用网关/编辑器代理（`kilo, vercel-ai-gateway, nanogpt, github-copilot, …`）。注释写明第三段"显式选用时有用，但不应该赢得歧义时的自动角色选择"。`[A]`

**(d) 家族/host 词汇表** —— `identity/family.ts`（356 行，带进程级 memo 缓存）负责"这个 id 是不是 Kimi/Claude/GLM 家族"，因为**同一个模型不管挂在哪个 OpenAI 兼容代理下，它的怪癖都跟着走**（`family.ts:1-7`）；`hosts.ts`（155 行）负责"这个 baseUrl 属于哪家 host 类"，用子串匹配而不是解析 hostname，理由是"代理经常把上游 host 嵌在 path 段里"，但对 auth 敏感的 Anthropic 官方端点 OAuth gate 例外，那里自己解析 hostname 比较（`hosts.ts:1-24`）。`[A]`

### 1.5 运行时：发现 + SQLite 缓存

`src/model-manager.ts`（672 行）+ `src/model-cache.ts`（285 行）。三档刷新策略 `"online" | "offline" | "online-if-uncached"`，默认缓存 TTL 2 小时，非权威结果 5 分钟重试（`model-manager.ts:8-9,16`）。`[A]`

缓存是 **bun:sqlite**，"replaces per-provider JSON files with a single cache.db"，为的是跨进程原子访问（`model-cache.ts:1-4`）。两个值得上 slide 的细节：

- **请求头故意不入缓存**：`"Request headers are intentionally omitted: arbitrary provider-defined header names can carry credentials."`（`model-cache.ts:8-10`）`[A]` —— 缓存层主动拒绝存可能含凭据的数据。
- **`CACHE_SCHEMA_VERSION = 12`**，且注释保留了 v4→v12 每一次 bump 的原因（Kimi Code 输出上限按家族细分、Codex V2 压缩元数据、Antigravity budget 模式迁移、退役的 `222222/8888` 未知限额哨兵值……）（`model-cache.ts:11-25`）`[A]`。**一个模型元数据缓存迭代了 12 个 schema 版本**，这个数字本身就说明这层有多不稳定。

---

## 2. 为什么要自建模型库：证据

### 2.1 痛点一：同一模型在不同网关 id 不同

本次点算（附录 A-4）`[A]`：

- 4,106 条记录里有 **2,275 个不同的展示名**；
- 其中 **527 个名字被 2 家以上 provider 提供**；
- 最夸张的：`Kimi K2.5` 被 **19 家** provider 提供、`DeepSeek V4 Pro` 18 家、`Kimi K2.7 Code` 18 家、`Claude Sonnet 4.5` 15 家。

同一个 `Kimi K2.7 Code`，落到线上的 wire id 有 4 种写法：

```
kimi-k2-7-code
kimi-k2.7-code
moonshotai/Kimi-K2.7-Code
moonshotai/kimi-k2.7-code
```

`Claude Sonnet 5` 有 4 种：`claude-sonnet-5` / `anthropic/claude-sonnet-5` / `anthropic.claude-sonnet-5`（Bedrock）/ `claude-sonnet-5@default`（Vertex）。`Claude Sonnet 4.5` 跨 15 家共 **8 种** wire id。`[A]`

→ 这就是 `identity/id.ts` + `identity/reference.ts` 那套 BFS 候选生成存在的直接理由。

### 2.2 痛点二：定价 / 上下文窗口靠猜必错

本次点算（附录 A-5）`[A]`，在"被多条记录覆盖的模型名"（543 个）中：

- **376 个（69%）各 provider 标的 `cost.input` 不一致**；
- **254 个（47%）各 provider 标的 `contextWindow` 不一致**。

两个具体例子：

| 模型 | 记录数 | 输入价（$/M）取值集合 | contextWindow 取值集合 | maxTokens 取值集合 |
| --- | --- | --- | --- | --- |
| `Kimi K2.7 Code` | 18 | `0, 0.71, 0.73, 0.75, 0.95` | `200000, 256000, 262000, 262144` | `32000, 32768, 64000, 131072, 262000, 262144` |
| `Claude Sonnet 4.5` | 18 | `0, 2.992, 3, 3.75` | `198000, 200000, 1000000` | `8192, 32000, 64000` |

注意 `Claude Sonnet 4.5` 的 maxTokens 从 8192 到 64000 差 8 倍 —— 如果 agent 按"猜的"值去设 `max_tokens`，要么白白截断输出，要么被上游 400。上下文窗口 198000 / 200000 / 1000000 三个值并存，压缩触发点就会算错。

> 补充证据：`reference.ts:20-30` 明确处理"xai-oauth 订阅条目零定价 + 虚高 maxTokens"，`model-cache.ts:20-21` 提到已退役的 `222222/8888` "未知限额哨兵值" —— 都说明上游数据脏到需要专门的哨兵和排除规则。`[A]`

### 2.3 痛点三：能力位不能从"模型名"推断

`thinking.mode` 5 种、`OpenAIReasoningFormat` 6 种（`"openai" | "openrouter" | "zai" | "kimi" | "qwen" | "qwen-chat-template"`）、`OpenAIReasoningDisableMode` 6 种（关思考的方式各家都不一样：删字段 / 钳到最低档 / `enabled:false` / `thinking:{type:disabled}` / `enable_thinking:false` / 模板 kwarg）—— `packages/catalog/src/types.ts:146-153`。`[A]`

CHANGELOG 里有一条极好的实例（`packages/ai/CHANGELOG.md:1145`）：关思考时如果只删 `reasoning_effort`，Qwen 的 `enable_thinking`、Qwen chat-template 的 `chat_template_kwargs.enable_thinking`、OpenRouter 的嵌套 `reasoning` 都还开着；而 OpenRouter "treats deleted as default-on"，必须显式发 `{ reasoning: { enabled: false } }`。`[A]`

---

## 3. `dialect`：绕开 native tool calling

### 3.1 为什么要绕开

仓库自己的一句话动机（TUI tips 里）：

> "No native tool_calling? Inference provider botches parsing them? `PI_DIALECT=glm|kimi|anthropic…` rolls it locally for them!"
> —— `packages/coding-agent/src/modes/components/tips.txt:23` `[A]`

拆开就是三类真实场景 `[A]`：

1. **上游根本不支持 function calling**（自托管 llama.cpp / vLLM / 某些便宜网关），`supportsTools` 字段在 118 条记录上出现，就是为这种情况留的开关；
2. **上游支持但解析做坏了** —— 网关自己拿正则去切模型输出的 chat-template token，切错就丢参数。CHANGELOG:428 记录了 GLM 的典型症状："missing or malformed argument closers (such as `<arg_value>` mistyped as `</arg_key>`) caused subsequent arguments to be swallowed or merged into a single field, **affecting both in-band and native tool calling**" —— 注意"native 也中招"；
3. **想拿回控制权** —— tool 描述裁剪、示例渲染、思考通道、token 预算，全部由 omp 自己决定。

**它是显式 opt-in，不是默认路径**：`config.dialect ?? resolveOwnedDialectFromEnv(Bun.env.PI_DIALECT)`（`packages/agent/src/agent-loop.ts:1500`）。不设就走 native。`[A]`

### 3.2 支持几种 / 适用模型

**11 种**（`packages/catalog/src/identity/dialect.ts:3-14`）`[A]`：

| dialect | 语法骨架 | 由 `preferredDialect` 自动匹配的家族 |
| --- | --- | --- |
| `anthropic` | `<function_calls><invoke name=…><parameter name=…>` | Claude 全系 |
| `glm` | `<tool_call>NAME` + `<arg_key>/<arg_value>` 对 | GLM / 智谱 |
| `gemini` | ` ```tool_code ` 里写 Python：`default_api.fn(arg="v")` | Gemini |
| `gemma` | `<\|tool_call>call:NAME{k:<\|"\|>v<\|"\|>}<tool_call\|>` | Gemma |
| `kimi` | `<\|tool_calls_section_begin\|>` + `functions.NAME:INDEX` + JSON | Kimi / Moonshot |
| `qwen3` | `<tool_call>` + `{"name","arguments"}` 单行 JSON | Qwen |
| `deepseek` | DSML 全角 token `<｜tool▁calls▁begin｜>` … | DeepSeek |
| `minimax` | `<minimax:tool_call><invoke>…` | MiniMax |
| `harmony` | `<\|start\|>assistant<\|channel\|>commentary to=functions.NAME<\|message\|>{…}<\|call\|>` | OpenAI / gpt-oss |
| `hermes` | `<tool_call>` + `{"name","arguments"}` | （无家族自动映射，需显式指定） |
| `xml` | `<invoke name><parameter name>` | **FALLBACK**（未知模型） |

映射逻辑：`preferredDialect(modelId)` → `modelFamilyToken(modelId)` → switch（`identity/dialect.ts:18-41`）`[A]`。`hermes` 不在 switch 里，只能显式选；`xml` 是兜底。

**与旧笔记的差异**：数量同为 11，但成员换了 —— 旧的 `pi` 原生方言（`§`/`«»`/`¤`/`‡‡` sigil 格式）已被移除（`packages/ai/CHANGELOG.md:792` "Removed Pi dialect support and related serialization/parsing logic"），新增 `minimax`（CHANGELOG:1177，为 MiniMax M3 的 `<minimax:tool_call>` 包装器，此前会错误 fallback 到通用 XML）。`[A]` 值得一提的是被删掉的 `pi` 方言曾宣称"比 legacy 格式省 ~46% token"（CHANGELOG:1073）—— **自研省 token 的方言最终没留下来，因为模型没见过它**（这条因果是 `[C]`，见存疑区）。

### 3.3 请求侧：怎么把 tool 塞进 prompt

`prepareProviderCall`（`agent-loop.ts:1523-1531`）三件事一起做 `[A]`：

```ts
systemPrompt: [...(llmContext.systemPrompt ?? []), renderInbandToolPrompt(promptToolWireTools, ownedDialect)],
messages:     encodeInbandToolHistory(llmContext.messages, ownedDialect, promptToolWireTools),
tools:        undefined,          // ← native tools 字段清空
```

同时 `toolChoice` 强制置空（`agent-loop.ts:1596`），`pruneToolDescriptions` 关闭（`:1502`）。

prompt 模板（`packages/ai/src/dialect/prompt-template.md`）只有 12 行，结构是「工具清单（每行一个 OpenAI function JSON）+ 方言语法说明」，关键一句：

> "Tool calls are emitted as text using the exact syntax below, **not as native provider tool messages**."

每种方言的语法说明是一份独立 `.md`（`anthropic.md` / `glm.md` / …），格式统一为「Format guide + Rules」。这些 Rules 是**踩坑史的浓缩**，几条通用的：

- **"bodies are read by regex (delimiter matching), NOT a real XML parser, so never HTML-escape them (emit `a & b`, not `a &amp; b`)"** —— 出现在 anthropic/glm/minimax/xml 四种方言里。`[A]`
- **"Emit the stop sequence ONLY after the call is fully written — NEVER announce a tool then stop (e.g. halting at 'Let's run `cargo clippy`' with no `<tool_call>` emitted)"** —— 出现在 deepseek/hermes/kimi/qwen3/xml 里。这是一个非常具体的失败模式：模型说完"我来跑一下"就停了，没吐调用，agent loop 空转。`[A]`
- **"NEVER emit `<tool_response>` yourself"** —— 几乎每种方言都有，对应下面的 fabrication。`[A]`

### 3.4 响应侧：流式扫描 + 失败模式（本节是重点）

`wrapInbandToolStream`（`packages/ai/src/dialect/owned-stream.ts:87-165`）把 provider 的原始 event stream 包一层，用 `InbandStreamProjector` 把文本重新投影成 `toolCall` content block，**下游 agent loop 完全无感**。`[A]`

#### 失败模式 A：模型伪造工具执行结果（fabrication）

模型不仅吐出调用，还顺手把"工具返回了什么"也编了出来，然后基于幻觉继续推理。native 通道里这种事不会发生（结果由 runtime 注入），in-band 通道里天天发生。

实现：每种方言登记一组"结果块开启 token"（`owned-stream.ts:19-31`）`[A]`：

```ts
const RESPONSE_OPEN_TOKENS: Record<Dialect, readonly string[]> = {
  glm: ["<tool_response>"],           hermes: ["<tool_response>"],
  kimi: ["<|im_system|>"],            xml: ["<tool_response>"],
  anthropic: ["<function_results>", "<tool_response>"],
  minimax:   ["<function_results>", "<tool_response>"],
  deepseek: ["<｜tool▁outputs▁begin｜>", "<｜tool▁output▁begin｜>"],
  harmony: ["<|start|>functions."],   gemini: ["```tool_outputs"],
  gemma: ["<|tool_response>"],
};
```

扫描器一旦在文本流里撞见这些 token，`text()` 立刻 `#stopped = true` 并返回 `true`（`owned-stream.ts:284-305`）；调用方据此**直接 abort 上游请求**：

> "`text()` returns true once the model starts fabricating its own tool result. In abort mode we cut the turn immediately **so the provider stops spending tokens on the hallucinated continuation**"
> —— `packages/ai/src/dialect/owned-stream.ts:116-119` `[A]`

两种模式（`abortOnFabrication`，默认 `true`）：abort = 立刻掐断省钱；discard = 继续排干流但丢弃边界之后的一切（`agent-loop.ts:1663-1671`）。对应测试：`packages/ai/test/owned-stream-fabrication.test.ts` 里 `"aborts the provider on fabrication when abortOnFabrication is true (default)"` / `"stops before hallucinated Anthropic function results"`。`[A]`

跨 chunk 切分也考虑到了：`#responsePending` 保留 `maxTokenLen - 1` 字节的重叠窗口，避免 token 被 SSE chunk 边界切开导致漏检（`owned-stream.ts:290-303`）。`[A]`

#### 失败模式 B：模型写错闭合标签

GLM 方言里最典型：模型该写 `</arg_value>` 却写成 `</arg_key>`，或者干脆忘了写就开始下一个参数。后果很严重：

> "Without repair, either mistake **swallows every following pair into the current value** until the next `</arg_value>` anywhere in the stream."
> —— `packages/ai/src/dialect/glm.ts:439-441` `[A]`

即：一个字符打错，后面所有参数全被吞进同一个字符串字段。omp 的对策是流式"愈合扫描"（`scanValueHeal` / `matchHealSignature`，`glm.ts:403-480`）：识别两种修复签名 —— (1) 错误闭合：`</arg_key>` 后面跟 `<arg_key>` / `</tool_call>` / `</arg_value>`；(2) 缺失闭合：出现完整的 `<arg_key>…</arg_key><arg_value>` 序列。`[A]`

难点在于**流式**：签名可能只到一半就 chunk 断了，所以返回三态 `none | partial | heal`，`partial` 时调用方必须 hold 住这段不往下游 emit（`glm.ts:415-423`）。还有防误伤的边界：`HEAL_WS_MAX = 32`（标签间最多容忍 32 个空白）、`HEAL_KEY_MAX = 128`（key 最长 128 字符），超了就放弃愈合（`glm.ts:403-406`）。对应测试组 `[A]`：

```
recovers when a value is closed with </arg_key> instead of </arg_value>
recovers a wrong closer directly before </tool_call>
drops a stray </arg_key> preceding the real </arg_value>
recovers when </arg_value> is missing before the next pair
leaves values containing tag-like prose intact      ← 反向保护
```

#### 失败模式 C：native 和 in-band 双通道同时开火

即使 `tools: undefined`，某些网关的模型照样会吐 native tool call：

> "Provider emitted a native structured tool call (e.g. **Gemini via OpenRouter still returns `functionCall` parts even when owned mode sends no `tools`**). Forward the native lifecycle live so the UI streams it; otherwise the turn loses its only actionable content and **the loop retries forever on a reasoning-only message**."
> —— `packages/ai/src/dialect/owned-stream.ts:127-134` `[A]`

对策：`#toolChannel: "native" | "inband" | undefined` —— **哪个通道先产出"真"调用就锁死哪个，另一个整轮丢弃**（`owned-stream.ts:180-186`）。还要处理"ghost part"：没有 name 的空 native 块不锁通道（`hasNamedNativeToolCall`，`owned-stream.ts:69-71`）。测试覆盖 `"drops a nameless native ghost but keeps the real native call"` / `"emits exactly one call when the model uses both the in-band and native channels"`。`[A]`

#### 失败模式 D：字符串参数被当 JSON 解析（或反之）

`buildStringArgsResolver`（`dialect/coercion.ts:28-32`）从 tool 的 JSON Schema 里算出"哪些参数是纯 string 类型"，扫描器对这些参数**逐字读取、不做 JSON 解析**。`isStringOnlySchema` 会展开 `anyOf/oneOf/allOf`、剔除 `null`、处理 `enum`/`const`（`coercion.ts:43-70`），深度上限 8 防炸。`[A]` 没有这一层，一段包含 `{` 的代码 patch 就会被当成 JSON 解析失败。XML 方言还留了逃生舱：`string="false"` 属性可以强制对一个 schema 标为 string 的值做 JSON 解析（`xml.md` Rules）。`[A]`

#### 失败模式 E：跨模型回放思考链会被判违规

`renderDemotedThinking`（`dialect/demotion.ts:33-40`）—— 换模型继续对话时，上一轮的 reasoning 要以目标模型能读懂的形式塞进历史。三条特判 `[A]`：

- **Anthropic 系裸奔**：注释称 Anthropic 的 `reasoning_extraction` 分类器会把 `<thinking>` / `antml:thinking` 包着的回放读成"试图复制模型输出"，从而**拒答（Fable）或把它当可见 reasoning 泄漏出来（Opus/Sonnet/Haiku/Mythos）**。所以 Claude 一律收到裸文本，无标签无包装。（`demotion.ts:10-19`）
- **Harmony / Gemma 降级成 `<think>`**：它们的 `renderThinking` 会吐 chat-template 控制 token（`<|channel|>analysis`），塞进结构化 native message 里是非法的。（`demotion.ts:21-25`）
- **Gemini 实测结论**：`"verified end-to-end against Gemini 3: a replayed unsigned `thought` part is schema-accepted but silently discarded — neither recalled nor influencing generation"`（`demotion.ts:6-9`）—— schema 收了但静默丢弃，这种坑不实测发现不了。

#### 其他工程细节

- **inventory 渲染**：`renderToolInventory`（`dialect/inventory.ts:17-30`）把 JSON Schema 转成 TypeScript 风格签名，并按目标模型的方言渲染示例；还有一个 `demoteDescriptionHeaders`，把工具描述里的 `# ` 一级标题整体降一级，免得和外层 `# Tool: <name>` 撞层级、让描述里的小节读起来像平级工具（`inventory.ts:32-45`）。`[A]` 这是 prompt 工程被当成编译问题处理的典型。
- 每种方言都做了 `renderToolCall` / `renderAssistantToolCalls` 分离 —— 单个调用 vs 带并行包裹层的整块（`dialect/types.ts:39-42`）。`[A]`
- 测试里有一条 round-trip 不变量：`"each dialect renders calls that its scanner parses back"`（`packages/ai/test/inband-tools.test.ts`）。`[A]`

---

## 4. `packages/wire` 管什么，和 `ai` 怎么分工

### 4.1 纠正：`pi-wire` 不是 LLM 协议层

`packages/wire` = `@oh-my-pi/pi-wire`，**单文件 444 行，零运行时依赖**（`package.json` 无 `dependencies`）。`[A]` README 第一句：

> "Shared TypeScript wire contracts for **omp collab live sessions**. The package contains only JSON-safe protocol shapes and constants. It ... is consumed by both the host CLI (`@oh-my-pi/pi-coding-agent`) and browser guest (`@oh-my-pi/collab-web`)."
> `[B]`

导出内容（`packages/wire/src/index.ts`）`[A]`：消息/转录条目形状（`WireMessage`、`SessionEntry`、`CompactionEntry`、`BranchSummaryEntry`…）、live agent 事件与子代理总线载荷、`GuestFrame` / `HostFrame` / `WireFrame` 三个联合类型（AES-GCM 密封载荷）、relay 控制 TEXT 消息、以及 link/envelope 常量（`COLLAB_PROTO = 3`、`ENVELOPE_HEADER_LENGTH = 4`、`ROOM_ID_BYTES = 16`、`ROOM_KEY_BYTES = 32`、`WRITE_TOKEN_BYTES = 16`、`DEFAULT_RELAY_URL = "wss://my.omp.sh"`）。

它明确声明**不做任何实际工作**：

> "`pi-wire` does not encode, decode, validate, encrypt, or route frames. It defines the shared contract used at those boundaries"
> —— `packages/wire/README.md` `[B]`

四步边界：调用方构造 frame → 传输层序列化成 JSON 放进加密载荷 → relay 用明文 peer-id 前缀路由不透明信封 → 接收方 switch `frame.t` 并容忍未知字段。版本策略："bump `COLLAB_PROTO` only when old hosts and guests must reject each other"。`[B]`

**上 slide 的说法**：`pi-wire` 是"共享类型即协议"的极简样本 —— 一个包只放形状，不放行为，两端（Bun CLI 与浏览器）靠它对齐，加密和路由各自实现。它和模型层没有关系。

### 4.2 真正的 LLM 协议层在哪

`[A]`：

- **`packages/catalog/src/wire/`**（5 文件 354 行）：`codex.ts`、`gemini-headers.ts`、`github-copilot.ts`、`coreweave.ts`、`alibaba-token-plan.ts` —— 都是**元数据级**的 wire helper（base URL、必需 header），放 catalog 是因为生成器和运行时都要用。
- **`packages/ai/src/providers/*-wire.ts`**：`anthropic-wire.ts`、`openai-chat-wire.ts`、`openai-responses-wire.ts` —— 真正的请求/响应编解码。
- **`packages/ai/src/api-registry.ts`**：14 个内置 API id，并用 `_CheckBuiltinApis` 类型断言保证与 catalog 的 `KnownApi` union 同步（`api-registry.ts:19-39`）。
- **`packages/ai/src/stream.ts`**：统一入口 `streamSimple`，从 catalog 拿 `hosts` / `model-thinking` / `provider-models` / `wire/codex`（见其 import 头 `stream.ts:6-17`），做 effort→wire 值映射、endpoint 路由、auth retry。重型 provider（AWS SDK、google-auth-library、`@google/genai`、`@bufbuild/protobuf`）走 `register-builtins` 的 lazy dynamic import，把它们挡在 CLI 启动解析图之外（`stream.ts:42-48`）。

**分工一句话**：`catalog` = 静态知识（谁存在、多少钱、能干什么、id 怎么归一）；`ai` = 动态行为（怎么发、怎么收、怎么重试、怎么认证、怎么解析方言）；`wire` = 和这两者无关的 collab 会话契约。catalog 单向被 ai 依赖，不反向。

---

## 5. auth broker：多机多账号 token 管理

> 主要来源：`docs/auth-broker-gateway.md`（233 行，仓库自带设计文档）`[B]` + 代码 `[A]`。
> 代码量：`auth-broker/*`（10 文件 4,055）+ `auth-gateway/*`（4 文件 1,219）+ `auth-storage.ts`（**8,399**）+ `auth-retry.ts`（398）= **14,071 行**；broker 目录内最大的是 `remote-store.ts` 1,332、`server.ts` 897、`wire-schema-resource.ts` 487、`client.ts` 470。`[A]`
> 对照：上游 pi 整个 `packages/ai/src/auth/` 只有 3,366 行，且没有 broker 概念。`[A]`

### 5.1 两个服务

- **`omp auth-broker serve`**：持有权威 SQLite 凭据库（`getAgentDbPath()`），执行 OAuth 刷新，暴露 REST（`/v1/snapshot`、`/v1/snapshot/stream` SSE、`/v1/credential`、`/v1/credential/:id/refresh`、`/v1/credential/:id/disable`、`/v1/usage`、`/v1/healthz`）。默认 `127.0.0.1:8765`。`[B]`
- **`omp auth-gateway serve`**：正向代理，收 OpenAI Chat Completions / Anthropic Messages / OpenAI Responses / pi-native 四种 wire 格式，解析成 omp `Context`，用 broker 解出的凭据经 `streamSimple()` 发出去，再按入站格式重编码。默认 `127.0.0.1:4000`。**客户端永远看不到 access token。** `[B]`

gateway 本身也是 broker 的客户端（`serve` 强制要求 `OMP_AUTH_BROKER_URL`）。`[B]`

### 5.2 唯一写者模型：三层落实，不只是约定

设计声明 `[A]`：

> "The OAuth `refresh` must be the **real** refresh token (not the sentinel) — **the broker is the canonical writer**."
> —— `packages/ai/src/auth-broker/types.ts:114-117`（另见 `:4-7` 的模块头注释、`docs/auth-broker-gateway.md:42`）

它靠三层机制落实，不是一句君子协定 `[A]`：

**第 1 层 · 客户端类型/运行时硬拒绝。** `RemoteAuthCredentialStore` 的三个写方法直接抛异常（`packages/ai/src/auth-broker/remote-store.ts:647-663`）：

```
"RemoteAuthCredentialStore is read-only on the client.
 Use `omp auth-broker login <provider>` to mutate credentials."
```

接口侧同样写明（`packages/ai/src/auth-storage.ts:364-368`）。

**第 2 层 · SQLite 行级持久租约（跨进程）。** 这是最值得上 slide 的一点 —— **"唯一写者"在 broker 主机内部仍然是多进程竞争**（omp CLI、gateway、生成脚本都可能开同一个 `agent.db`），所以刷新动作用一张租约表做互斥（`auth-storage.ts:6941-6950`，`credential_id INTEGER PRIMARY KEY` ⇒ 每凭据至多一个 owner）：

```sql
INSERT INTO auth_credential_refresh_leases (credential_id, owner, expires_at_ms, updated_at)
VALUES (?, ?, ?, ...)
ON CONFLICT(credential_id) DO UPDATE SET owner=excluded.owner, ...
  WHERE auth_credential_refresh_leases.expires_at_ms <= ?     -- ← 只有过期租约才能被抢
```

—— `auth-storage.ts:6858-6866`。获取/轮询在 `:2313-2363`，心跳续租在 `:2411-2422`（丢失所有权时报 `"OAuth refresh ownership was lost before persistence"`），释放在 `:2528`。函数注释：`"Refresh one stored OAuth credential under durable row ownership."`（`:2369`）

**第 3 层 · 进程内单飞**（见 §5.4）。

**没有 leader election、没有 unix socket。** 传输就是 `Bun.serve` 的普通 TCP HTTP（`auth-broker/server.ts:658-662`），返回的 URL 硬编码 `http://`（`:886`），默认 `127.0.0.1:8765` 且注释写明 `"Loopback-only, no external exposure."`（`auth-broker/types.ts:174-175`）。对"别的进程直接改了 agent.db"的情况，broker 用一个 `GenerationGate` 每 **250 ms** 轮询 `storage.pollExternalChanges()` 并唤醒长轮询等待者（`server.ts:44, 189-206, 243-254`）。

### 5.3 占位符：只有 refresh token 是假的

哨兵定义 `[A]`（`packages/ai/src/auth-storage.ts:325-331`）：

```ts
/** Sentinel value placed in OAuth `refresh` fields when a credential is shared
 *  via AuthStorage.exportSnapshot. Refresh tokens never leave the broker;
 *  clients must call back to refresh. */
export const REMOTE_REFRESH_SENTINEL = "__remote__" as const;
```

替换发生在四个点 `[A]`：

| 位置 | 文件:行 | 说明 |
| --- | --- | --- |
| 快照导出（服务端） | `auth-storage.ts:6142-6156` | `credential.type === "api_key" ? credential : { ...credential, refresh: REMOTE_REFRESH_SENTINEL }` |
| refresh 响应 | `auth-storage.ts:6284` | 刷新后回给客户端的也是哨兵 |
| upload 响应 | `auth-storage.ts:6327-6330` | |
| 客户端返回路径 | `remote-store.ts:920-931` | 保证哨兵不会在本地被真值替换；注释 `:898-901` |

**双向 schema 级强制**（ArkType wire schema）`[A]`：上传时 `refresh` 若等于哨兵直接拒绝（`auth-broker/wire-schema-resource.ts:93-97`，`ctx.mustBe("not equal to the remote sentinel (__remote__)")`）；快照里则**必须**是哨兵（`:109-113`，`type.enumerated(REMOTE_REFRESH_SENTINEL)`）。协议层把方向锁死了。

**一个精妙的坑**（`auth-storage.ts:2987-2991`）`[A]`：

> "Broker-backed rows all carry REMOTE_REFRESH_SENTINEL as their refresh token — **it identifies nothing**, and comparing it would match the FIRST OAuth row regardless of which account/org is being refreshed."

即：哨兵是常量，绝不能当行标识用。回归测试专门守这条：`packages/ai/test/auth-storage-org-scoped-identity.test.ts:507-524`。诊断侧另有 `remoteRefresh?: true` 标志（`auth-storage.ts:225-226`，设值处 `:4042`）。MCP 管理器也认这个哨兵（`packages/coding-agent/src/mcp/manager.ts:1398`）；Web 搜索 provider 甚至会把哨兵原样发给上游 token endpoint，靠上游归类成失败来走正确的错误路径（`packages/coding-agent/src/web/search/providers/base.ts:13`）。`[A]`

> ⚠️ **重要澄清（不要在 slide 上说错）**：普通 broker 客户端**照样拿到真实可用的 provider access token**，被藏起来的只有 refresh token。真正"连 access token 都看不到"的只有 **gateway 的下游客户端** —— 因为上游请求是 gateway 自己发的，且"there is no raw provider passthrough path"（`docs/auth-broker-gateway.md:6, 129`）。`[A][B]`

### 5.4 刷新：三层单飞 + 主动预热 + 401 三段式

**单飞三层** `[A]`：

1. **进程内按 credential id**：`#oauthRefreshInFlight` / `#oauthCredentialRefreshInFlight`（`auth-storage.ts:1295-1296`），合流点 `:6184-6205`，注释给了硬理由 —— `"which is required for providers that rotate refresh tokens on every successful refresh"`（refresh token 一次性轮换的厂商，并发刷新会互相作废）。另一处 `:4772-4791`。
2. **跨进程**：§5.2 的 SQLite 租约。
3. **跨机器**：客户端靠 SSE / 30 s 长轮询观察到同伴刷新的结果，而不是各自发起（`remote-store.ts:345-394`，`BACKGROUND_WAIT_MS = 30_000` at `:64-66`）。

**主动（proactive）** `[A][B]`：`AuthBrokerRefresher`（117 行）每 60 s 扫一遍，刷新所有 5 min 内到期的（`refresher.ts:78-100`；常量 `auth-broker/types.ts:177-181`）。启动时立刻踢一次，注释：`"so freshly-booted brokers don't hand out near-expired tokens for the first interval."`（`refresher.ts:52-55`）

还有一个很少见的设计：broker 会在快照里给出每个凭据的**预测轮换时间** `rotatesInMs`（`server.ts:291-309`），客户端发请求前若发现轮换迫在眉睫（`WAIT_THRESHOLD_MS = 1_000`）就最多等 5 s（`MAX_WAIT_MS = 5_000`）拿新快照再发（`remote-store.ts:615-631`，hook 契约在 `auth-storage.ts:482-488`）。**用"等一下"换掉一次注定 401 的往返。** `[A]`

**反应式（401）三段式** —— 策略集中写在 `packages/ai/src/auth-retry.ts:10-26` `[A]`：

```
(a) 初次解析凭据  →  (b) 强制刷新同一账号  →  (c) 轮换到兄弟账号
```

- gateway 侧钩子 `refreshGatewayApiKeyAfterAuthError`（`auth-gateway/server.ts:231-272`）：401 ⇒ `invalidateCredentialMatching` + 重解析；命中用量上限 ⇒ `markUsageLimitReached`（**封锁而不是继续烧**，理由注释在 `:211-224`）。
- 客户端 401 时让 broker 重发行：`auth-storage.ts:523-529`（`"Remote stores force the broker to re-issue the row"`），调用点 `:5978-5982`、`:6077-6081`；`RemoteAuthCredentialStore.markCredentialSuspect` 本质就是 `POST /v1/credential/:id/refresh`（`remote-store.ts:633-641`）。
- 确定性失效的 token 直接删除而非刷新（`auth-storage.ts:6062-6074`）。
- 刷新有超时上限，防止吊死的 token endpoint 卡住选路（`auth-storage.ts:4858-4870`）。

**definitive vs transient 二分** `[A][B]`（`refresher.ts:8-11, 105-114`）：`invalid_grant` / `invalid_token` / `revoked` / 非网络抖动的 401/403 → 停用；timeout / ECONNREFUSED / fetch failed → 原地保留等下一轮。

这里踩过一个非常值得讲的并发坑（`packages/ai/CHANGELOG.md:889`）`[A]`：refresher 曾经无条件 `disableCredentialById`，导致"另一个进程或一次新登录刚轮换过的凭据"被误拆。修法是把拆除动作挪进 `AuthStorage.refreshCredentialById` 用 **compare-and-set**（`auth-storage.ts:6234-6252`，`#disableCredentialByIdIfMatches`，CAS 失败就 `await this.reload()`），refresher 只记日志。**"唯一写者"不等于"唯一进程"—— 这条补丁是整个模型最有教学价值的地方。**

另有跨进程的 429 记忆（CHANGELOG:576）`[A]`：`auth_credential_blocks` 表（auth schema v5）持久化每凭据的限流封锁，broker 快照/SSE 携带，配 `POST /v1/credential/:id/block`，"so gateway and sibling omp processes stop re-discovering exhausted accounts by burning a 429 each"。

### 5.5 多机多账号

- **账号枚举**：账号就是 broker `agent.db` 里的行，以 `SnapshotEntry[]` 发布（`packages/ai/src/auth-broker/types.ts:33-43`），每条带一个**无 token 的** `identityKey`（`resolveCredentialIdentityKey`，`auth-storage.ts:6580-6583`，注入点 `:6152, :6285, :6334`）。形如 `email:alice@example.com|org:org-team`；API key 的 `identityKey` 为 `null`。`[A][B]`
- **客户端账号池**：`OMP_AUTH_BROKER_ACCOUNT_POOL_FILE` 指向一个 `{provider: [identityKey…]}` JSON，限制本进程可见的 OAuth 账号（实现 `remote-store.ts:43-51`，构造时防御性拷贝 `:279-282`）。缺省不限制；空数组 = 该 provider 的 OAuth 全部隐藏；非空 = 精确匹配。API key 不受影响。文件解析失败/JSON 非法/provider 项非法 → **中止初始化而不是静默放宽**。`[A][B]`
- **`remote-store.ts`（1,332 行）到底是什么**：broker 快照在客户端的**物化视图**（`class RemoteAuthCredentialStore implements AuthCredentialStore`，`:241`）。后台同步优先走 SSE（`#consumeSnapshotStream`，`:383-394`），遇 404 就闩住 `#streamingUnsupported` 降级到 30 s 长轮询 + `ifGenerationGt` + 指数退避（`:345-381`）。此外还负责 usage 代理与 15 s 单飞、限流封锁的乐观本地应用 + fire-and-forget POST（`:522-568`）、以及全部写操作转发给 broker（`:591-673`）。`[A]`
- **远程登录**：`omp auth-broker login <provider> --via=user@host` 会 shell 出 `ssh -L <callback-port>:127.0.0.1:<callback-port> …`，让 OAuth 回调打到本地浏览器、凭据却写在 broker 主机上。内置回调端口：`anthropic:54545`、`openai-codex:1455`、`google-gemini-cli:8085`、`google-antigravity:51121`、`gitlab-duo:8080`。`[B]`
- **迁移/导入**：`migrate --from-local` 把本地 SQLite 上传（默认只传 API key，OAuth 要 `--include-oauth`，env 派生的要 `--include-env`）；`import` 支持 CLIProxyAPI 风格 JSON。`[B]`

### 5.6 离线可用性：加密快照缓存

`discoverAuthStorage()` 把快照落到 `~/.omp/cache/auth-broker-snapshot.enc` `[A][B]`：

- **AES-256-GCM**，密钥 = `SHA-256(OMP_AUTH_BROKER_TOKEN)`，**broker URL 作为 AAD**（`packages/ai/src/auth-broker/snapshot-cache.ts:111-133, 171-183`）—— 换 token 或换 URL 都会让缓存不可读；
- 原子写，`0600`（`snapshot-cache.ts:93-104`）；
- 新鲜度锚定 broker 盖的 `snapshot.generatedAt` 而非本地写入时间，默认 TTL 1 h（`DEFAULT_SNAPSHOT_CACHE_TTL_MS = 60*60_000`，`auth-broker/types.ts:183-184`）；
- 即使缓存新鲜，也会在 **500 ms 启动预算**（`discover.ts:44`）内向可达的 broker revalidate 一次，这样刚导入/吊销/轮换的凭据对 one-shot 命令立即可见；
- **401/403 不被缓存掩盖**（`discover.ts:284-287` 直接重抛）；只有传输层/5xx 才回落缓存。

模块头注释自己划了信任边界（`snapshot-cache.ts:4-7`）`[A]`：

> "The cache is defense-in-depth for at-rest snapshots: a copied cache file is useless without the matching broker bearer token and URL. **The token itself is still the trust boundary; a process that can read both the token and this file can decrypt the snapshot.**"

注意密钥派生是**裸 SHA-256(token)，无 salt、无 KDF 拉伸**（`snapshot-cache.ts:180-183`）—— 在 token 是高熵随机串的前提下够用，但这是个明确的设计取舍。`[A]`

### 5.7 usage 缓存：两层刻意叠加

`[A][B]`

| 层 | 位置 | TTL | 目的 |
| --- | --- | --- | --- |
| 服务端 | broker `AuthStorage`，SQLite | **5 min ± 25% jitter**（`USAGE_REPORT_TTL_MS = 5 * 60_000`，`auth-storage.ts:682`；jitter 计算在 `:3153`） | Anthropic/OpenAI 按源 IP 限流 `/usage`，5 个凭据同步扇出每轮必 429；抖动几轮内解相关 |
| 服务端 last-good | 同上 | **24 h**（`USAGE_LAST_GOOD_RETENTION_MS`，`auth-storage.ts:684`，使用点 `:1195`） | 上游抖动不把 widget 打空白 |
| 客户端 | `RemoteAuthCredentialStore` 内存 | **15 s**（`USAGE_CACHE_TTL_MS = 15_000`，`remote-store.ts:60`，使用点 `:1017,1026,1071`） | 把 `#rankOAuthSelections` 的并行扇出合并成一次 broker 往返 |

一个并发正确性细节 `[B]`：客户端共享单个 `#usageInflight` promise，每个调用方的 `AbortSignal` 是**和共享 promise 赛跑**而不是穿进去 —— 一个调用方 abort 不会级联掐掉别人的在途请求。

### 5.8 安全设计的取舍（不吹不贬）

**买到了什么** `[A][B]`：

- refresh token 只存在于 broker 主机的 SQLite 里，笔记本/CI/容器上没有，且协议层双向强制（§5.3）；
- 通过 gateway 访问时，下游客户端连 access token 都拿不到（无裸转发路径，全部走 `pi-ai` provider 逻辑）；
- token 文件 `0600` / 父目录 `0700`；
- 快照缓存 AES-256-GCM 且绑定 (token, URL)；
- 模型缓存主动拒绝存 header，因为"任意 provider 自定义 header 名可能携带凭据"（`model-cache.ts:8-10`）；
- 跨进程刷新有持久租约，跨账号停用有 CAS，不会互相拆台。

**付出/未覆盖的** `[A][B]`：

- **传输安全完全外包给运维**：`docs/auth-broker-gateway.md:8` —— "delegated to the operator (Tailscale / Wireguard / reverse proxy + TLS)"。broker server 自己只讲 `http://`（`auth-broker/server.ts:886`），不做 TLS、也不做服务端身份验证。
- **单一 bearer = 全量凭据、无 scope**：除 `/v1/healthz` 外所有端点共用一个静态 bearer。拿到它就能 `GET /v1/snapshot` 读到**全部账号身份 + 真实 access token + 明文 API key**（API key 的 wire schema 就是 `key: type("string").atLeastLength(1)`，`wire-schema-resource.ts:124-130`），还能写（`POST /v1/credential`、`/disable`、`/refresh`）。没有 per-client 身份，没有权限分级。
- **broker 的 bearer 校验不是常量时间**：`packages/ai/src/auth-broker/server.ts:90-100` 用普通 `Set.has()`；而且 `if (tokens.size === 0) return true;` —— **空 token 集合等于完全关闭鉴权**。对比之下 **gateway 做对了**：`auth-gateway/http.ts:63-95` 遍历全部 token 做常量时间比较，注释写明 `"Iterate every allowed token regardless of early hits so the result timing reflects the full set"`。同一个仓库里两套实现不一致，是个值得一提的真实观察。
- **`--no-auth`**：gateway 可以完全关掉 bearer 校验（仅供 loopback）。`[B]`
- **账号池不是授权边界** —— 代码和文档都加粗声明：

  > "This is a trusted-client routing policy, **not broker authorization**." —— `remote-store.ts:232-235`
  > "The client still holds a broker bearer token, receives **raw broker responses** before applying its local view, and can call broker endpoints directly. Use server-side authorization—not account pools—when clients must be prevented from retrieving other credentials." —— `docs/auth-broker-gateway.md:183`

  并且加密快照缓存里存的是**未过滤的原始快照**（`docs/auth-broker-gateway.md:181`）。
- **运维工具卫生只是建议**：`docs/auth-broker-gateway.md:172` —— "Operator tooling **should** project only `provider` and `identityKey`; it must not retain or print the accompanying credential payload." 没有任何机制强制。
- **broker 是单点**：它挂了，客户端靠 1 h 加密快照缓存续命；过期的 access token 无法刷新（刷新必须回 broker）。
- **假设 `agent.db` 与旧进程共享**：SQLite 里保留一份物理 `shared` 兼容镜像，供"直接读 `agent.db` 的 pre-meter 老二进制"使用（`docs/auth-broker-gateway.md:86`）—— 也就是说数据库文件本身被当成进程间接口。
- **fire-and-forget 写可能静默漂移**：`remote-store.ts:531-543, 591-597` 在传播失败时只 `logger.warn`，客户端本地视图与 broker 可能不一致。
- **混版本降级偏保守**：不带 `OMP-Auth-Broker-Capabilities: codex-meter-block-scopes` 的老客户端拿到把 `chat`/`spark` 投影成 `shared` 的保守表示；文档明说"倾向于保持被限流的凭据处于封锁状态，而不是放行导致反复 429"（`docs/auth-broker-gateway.md:88`）。`[B]`
- **本目录只有一处 TODO**，且与安全无关：`auth-gateway/server.ts:188` `// TODO(pi-ai): land first-class fields and replace these blocks.` `[A]`

### 5.9 一个容易忽略的耦合

catalog 的**生成脚本**会去调 auth broker：`packages/catalog/scripts/generate-models.ts:82-101` 通过 `discoverAuthStorage()` 拿 provider 的 API key/OAuth token 去抓真实模型目录，注释说明这是刻意的 —— "AuthStorage.getApiKey refreshes through the broker-aware single-flighted machinery, so a build-time invocation no longer silently falls back to bundled models when an expired-but-refreshable OAuth credential is on disk"。`[A]` 也就是说**"构建模型库"这件事本身需要一套账号体系**，这是 63 家 provider 的 catalog 能自动化的前提。

---

## 6. 与上游 pi `packages/ai` 的对比

`[A]`，均为本次点算（附录 A-6）。

| 维度 | 上游 pi (`583f153d5`) | omp (`09a7c8656`) | 倍数 |
| --- | --- | --- | --- |
| `packages/ai/src` `.ts` 文件数 | 169 | 278 | 1.6× |
| `packages/ai/src` 行数 | 21,429 | 99,265 | **4.6×** |
| 独立 catalog 包 | 无（catalog 在 ai 内） | 有（`packages/catalog`，49 个非生成 `.ts` / 16,343 行 + 2.1 MB 数据） | — |
| 模型数据是否入库 | **否** —— `.gitignore:11` 忽略 `packages/ai/src/providers/data/`，`npm run build` 先 `generate-models` 现拉 | **是** —— `src/models.json` 2.1 MB 提交进仓库 | — |
| provider 数据文件 | 37 个 `*.models.ts`（每个只是 `import values from "./data/X.json"` 的薄壳，见 `src/providers/anthropic.models.ts:4-8`） | 单份 `models.json`，63 顶层键 | — |
| dialect / in-band tool calling | **完全没有**（`grep -rn "dialect\|inband" src` 零命中） | 11 种方言 / `packages/ai/src/dialect/` 24 文件 5,802 行 | ∞ |
| auth 层 | `src/auth/`（含 11 个 OAuth provider）+ `oauth.ts`，共 3,366 行 | auth-broker + auth-gateway + auth-storage + auth-retry = 14,071 行；registry 104 文件 7,616 行 | **4.2×** |
| auth broker / gateway | **无**（`grep -rn "broker" src` 零命中） | 有（§5） | — |
| provider registry 条目 | 37 | 104 个 registry 文件 / 67 条 catalog descriptor | — |
| 运行时模型发现 | `models-store.ts` 45 行 | `model-manager.ts` 672 + `model-cache.ts` 285（SQLite，schema v12）+ `discovery/` 7 个专用发现器 | — |
| 上游数据源 | `https://models.dev/api.json`（raw，~3.3 MB，`scripts/generate-models.ts:1094`） | `https://catalog.stencil.so/models.json.zstd`（裁字段 + zstd，~93 KB） | — |
| effort 变体折叠 | 无 | `variant-collapse.ts` 1,124 行 | — |
| 别名/身份归一 | 无独立模块 | `identity/` 8 文件 1,009 行 + `scripts/equivalence.ts` | — |

**几个定性差异（比数字更值得上 slide）**：

1. **pi 把模型数据当构建产物，omp 把它当源代码**。pi 的 `build` 脚本是 `generate-models && build:offline` —— 每次构建现拉 models.dev；omp 把 4,106 条快照提交进仓库，离线可用，且能被 diff/review（如 `git log -- packages/catalog/src/models.json` 里的 `fix(catalog): dropped unconfirmed GMI Cloud cache-read price`）。代价是仓库里多 2.1 MB 且需要定期 `chore: bump models`。`[A]`
2. **pi 的 provider 集合明显更"官方"**，37 家里几乎全是一线厂商 + 少量网关；omp 的 63 家里有大量二三线聚合网关（nanogpt/kilo/aimlapi/zenmux/venice/novita/kilo/opencode-zen…），这是它需要 `identity/reference.ts` 那套方括号剥离和 marker 归一的直接原因 —— **pi 不需要处理 `[gcli转] gemini-3.1-pro-preview [假流]` 这种 id**。`[A]`
3. **pi 完全信任 native tool calling**，omp 为"上游做不到或做坏了"准备了完整的 fallback 通道。这是二者面向的用户群不同的最强信号。`[A]`
4. **pi 的凭据模型是"每台机器一份本地 store"**，omp 加了一整个 broker/gateway 分层来支撑多机 + 多账号轮换 + 跨进程限流记忆。`[A]`

---

## 7. 存疑区（`[C]`，未经验证的推测）

1. `[C]` **`pi` 自研方言被删的原因**是"模型没在预训练里见过这套 sigil 语法，遵循率不如各家原生 chat-template 语法"。CHANGELOG 只记录了「新增（省 46% token）」和后来的「移除」两条事实，没写移除动因。需要 issue/PR 讨论才能坐实。
2. `[C]` **`nanogpt` 810 条、`kilo` 498 条**这类超大目录，估计有相当比例是同一底模的量化/路由变体（`-fp8`/`:nitro`/`-free`），真实"不同模型"数量应远小于 4,106。`markers.ts` 的 18 个 marker 词表支持这个方向，但我没有做去重后的点算。
3. `[C]` **catalog 的更新频率**。`git log -- packages/catalog/src/models.json` 只有 19 次提交（2026-07-22 该包拆出至今 10 天），无法据此推断长期节奏；models.json 的实际新鲜度取决于维护者何时跑 `bun run gen:models`。
4. `[C]` **`preferredDialect` 的兜底代价**。未知模型一律落 `xml`，对没见过 `<invoke>/<parameter>` 语法的小模型遵循率如何，仓库里没有 eval 数据。
5. `[C]` **auth broker 的实际部署形态**。默认绑 `127.0.0.1:8765` 且注释写 "Loopback-only, no external exposure"，多机使用必须自行叠 Tailscale/反代。仓库没说清楚"团队共用一台 broker"是不是设计意图 —— 从"单 bearer 无 scope + 账号池只是路由"来看，我倾向于它面向的是**单人多机**而非**团队多人**，但这是推测。
6. `[C]` **`supportsComputerUseConfig` 只覆盖 40%** 而 `supportsComputerUse` 覆盖 50% —— 两者的差集（约 414 条）含义我没有追到定义处，可能是"支持但无额外配置"。

---

## 附录 A：复现命令

全部在 `/Users/overkazaf/playground/research/ohmypi/oh-my-pi`（HEAD `09a7c8656`）下执行。

**A-1 / A-2 provider 家数与模型条数（含分布）**

```bash
python3 -c "
import json,collections
d=json.load(open('packages/catalog/src/models.json'))
print('providers:',len(d)); print('models:',sum(len(v) for v in d.values()))
for k,v in collections.Counter({k:len(v) for k,v in d.items()}).most_common(): print(f'{v:5d} {k}')
"
# => providers: 63 / models: 4106
```

**A-3 字段覆盖率 + API 协议分布**

```bash
python3 -c "
import json,collections
d=json.load(open('packages/catalog/src/models.json'))
keys=collections.Counter(); apis=collections.Counter()
for ms in d.values():
  for v in ms.values(): keys.update(v.keys()); apis[v.get('api')]+=1
n=sum(len(v) for v in d.values())
for k,c in keys.most_common(): print(f'{c:6d} {c*100//n:3d}%  {k}')
print('---'); [print(f'{c:6d} {k}') for k,c in apis.most_common()]
"
```

**A-4 跨网关 id 分裂**

```bash
python3 -c "
import json,collections
d=json.load(open('packages/catalog/src/models.json'))
byname=collections.defaultdict(set); ids=collections.defaultdict(set)
for p,ms in d.items():
  for mid,v in ms.items(): byname[v['name'].strip().lower()].add(p); ids[v['name'].strip().lower()].add(mid)
multi={k:v for k,v in byname.items() if len(v)>1}
print('distinct names:',len(byname),'| multi-provider names:',len(multi))
for k,v in sorted(multi.items(), key=lambda x:-len(x[1]))[:8]:
  print(f'  {len(v):3d} providers  {k!r}  distinct wire ids={len(ids[k])}')
print(sorted(ids['kimi k2.7 code']))
"
# => 2275 / 527；Kimi K2.5 19 家；Kimi K2.7 Code 4 种 wire id
```

**A-5 定价 / 窗口分歧**

```bash
python3 -c "
import json,collections
d=json.load(open('packages/catalog/src/models.json'))
g=collections.defaultdict(list)
for p,ms in d.items():
  for mid,v in ms.items():
    g[v['name'].strip().lower()].append((v['cost']['input'],v['contextWindow'],v['maxTokens']))
multi=[rows for rows in g.values() if len(rows)>1]
print('multi-entry names:',len(multi))
print('divergent input price:',sum(1 for r in multi if len({x[0] for x in r})>1))
print('divergent contextWindow:',sum(1 for r in multi if len({x[1] for x in r})>1))
for probe in ['kimi k2.7 code','claude sonnet 4.5']:
  r=g[probe]; print(probe,len(r),sorted({x[0] for x in r}),sorted({x[1] for x in r}),sorted({x[2] for x in r}))
"
# => 543 / 376 / 254
```

**A-6 规模对比**

```bash
# omp
find packages/ai/src      -name '*.ts' | wc -l ; find packages/ai/src      -name '*.ts' -exec cat {} + | wc -l   # 278 / 99265
find packages/catalog/src -name '*.ts' -not -path '*-gen/*' -not -path '*proto*' | wc -l                        # 49
find packages/catalog/src -name '*.ts' -not -path '*-gen/*' -not -path '*proto*' -exec cat {} + | wc -l          # 16343
wc -l packages/ai/src/dialect/*.ts | tail -1                                                                     # 5802
wc -l packages/ai/src/auth-broker/*.ts packages/ai/src/auth-gateway/*.ts \
      packages/ai/src/auth-storage.ts packages/ai/src/auth-retry.ts | tail -1                                    # 14071
grep -c '^\t| "' packages/catalog/src/identity/dialect.ts                                                        # 11
grep -c '^\t\tid: "' packages/catalog/src/provider-models/descriptors.ts                                         # 67
grep -c 'catalogDiscovery: {' packages/catalog/src/provider-models/descriptors.ts                                # 40

# upstream pi
cd /Users/overkazaf/playground/research/pi/pi-mono/packages/ai
find src -name '*.ts' | wc -l ; find src -name '*.ts' -exec cat {} + | wc -l                                     # 169 / 21429
ls src/providers/*.models.ts | wc -l                                                                             # 37
grep -rn "dialect\|inband" src | wc -l                                                                           # 0
grep -rn "broker" src | wc -l                                                                                    # 0
wc -l src/auth/*.ts src/auth/oauth/*.ts | tail -1                                                                # 3366
grep -n "packages/ai/src/providers/data" ../../.gitignore                                                        # 11:packages/ai/src/providers/data/
```

## 附录 B：主要证据文件索引

| 主题 | 路径 |
| --- | --- |
| 模型数据快照 | `packages/catalog/src/models.json`（2,171,711 B） |
| 生成器 | `packages/catalog/scripts/generate-models.ts`（749）、`generated-policies.ts`（395） |
| 各家网关脾气 | `packages/catalog/src/provider-models/openai-compat.ts`（5,740） |
| provider 描述表 | `packages/catalog/src/provider-models/descriptors.ts`（576） |
| 类型 / 能力位定义 | `packages/catalog/src/types.ts`（924） |
| 别名归一 | `packages/catalog/src/identity/{id,markers,reference,family,classify,priority,dialect}.ts` |
| 变体折叠 | `packages/catalog/src/variant-collapse.ts`（1,124） |
| 运行时发现/缓存 | `packages/catalog/src/model-manager.ts`（672）、`model-cache.ts`（285）、`discovery/` |
| 方言定义 | `packages/ai/src/dialect/*.ts`（24 文件 5,802）+ 11 份 `*.md` prompt |
| in-band 流投影 | `packages/ai/src/dialect/owned-stream.ts`（481） |
| in-band 接入点 | `packages/agent/src/agent-loop.ts:1480-1532, 1596, 1657-1671` |
| LLM 统一入口 | `packages/ai/src/stream.ts`、`api-registry.ts` |
| collab 协议（非 LLM） | `packages/wire/src/index.ts`（444）、`packages/wire/README.md` |
| auth broker | `packages/ai/src/auth-broker/*`（10 文件 4,055）、`auth-gateway/*`（1,219）、`auth-storage.ts` |
| auth 设计文档 | `docs/auth-broker-gateway.md`（233） |
