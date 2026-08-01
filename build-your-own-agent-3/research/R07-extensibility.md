# R07 — oh-my-pi 可扩展性三层 + 协作 + TUI

> 取证基线：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi` @ `09a7c8656`（v17.2.3，**shallow clone**）
> 上游对照：`/Users/overkazaf/playground/research/pi/pi-mono` @ `583f153`
> 证据等级：`[A]` 本地代码亲自读到（给 `文件:行号`） / `[B]` 文档已核实 / `[C]` 推测（只进存疑区）

---

## 0. 结论先行

1. **omp 的可扩展性不是「三层」，是「五类扩展点 × 十一个生态 provider」的二维矩阵。** 真正的架构创新是 `src/capability/` + `src/discovery/` 这套**能力-提供方注册表**：调用方只说 `loadCapability("skill")`，由 provider 层去决定从 `.omp/` / `.claude/` / `.codex/` / `.cursor/` / `.gemini/` / `AGENTS.md` 里哪个位置读。`[A]`
2. **上游 pi 没有 MCP、没有 hook、没有 plugin/marketplace、没有 custom-tool、没有 capability/discovery。** pi 只有一套 extension module 机制。omp 在扩展面上是**净增五个子系统**，同时保留了对 pi 扩展的源码级兼容（specifier 重写）。`[A]`
3. **Tier 模型是可验证的：swarm 本体确实是纯 Tier-0 扩展。** `packages/coding-agent/src/` 里对 "swarm" 的引用只有一条**注释**，零代码耦合。`[A]`
4. **collab 是事件级复制 + 对端本地重渲染，不是屏幕镜像；E2EE 是 AES-256-GCM + 带外预共享密钥。** 服务端只见密文、roomId、peerId、帧大小与时序。但有若干真实的**安全弱点**（无过期、无撤销、无帧序号、web 客户端 JS 由 relay 投递）。`[A]`
5. **`packages/stats` 零出网，纯本地 SQLite。** 全仓唯一指向作者服务器的用户数据通道是 Auto-QA grievance，**被 consent 硬门拦住，用户不手动点 Yes 就永不上传**。默认发生的唯一出网是 npm 版本检查（无 payload、无 install-id）。`[A]`
6. **TUI 是架构分叉不是优化**：上游 pi 押注「alt-screen + 约束式布局树」，omp 押注「单一主屏 append-only 提交账本 + 三层前缀增量」，并把文本度量整体下沉到 Rust（`crates/pi-natives/src/text.rs` 2065 行）。代码量 25.7k vs 14.2k，测试文件 97 vs 36。`[A]`

---

## 1. 扩展点全景表

### 1.1 五类扩展点

| # | 扩展点 | 管哪一段 | 载体形态 | 加载入口 `文件:行号` | 加载时机 | 隔离级别 | 级 |
|---|---|---|---|---|---|---|---|
| 1 | **MCP server** | 外部工具 / 资源 / prompt，跨语言跨进程 | 独立进程（stdio）或远端 HTTP/SSE | `packages/coding-agent/src/mcp/manager.ts:393` `discoverAndConnect()`；`:416` `connectServers()`；配置 `mcp/loader.ts` | 有 UI 时**延迟到 TUI 起来之后**异步连（`sdk.ts:1829` `deferMCPDiscoveryForUI`、`:1846-1862`）；无 UI 时启动同步连 | **最强：独立 OS 进程**。stdio transport = JSON-RPC over 子进程 stdin/stdout（`mcp/transports/stdio.ts:1-6`），崩溃不影响宿主 | Tier 0 |
| 2 | **Extension module**（`.ts`/`.js`） | 表达力上限：事件流改写、注册工具/命令/快捷键/CLI flag/渲染器 | 单个 TS 模块，默认导出 factory `(pi: ExtensionAPI) => void` | `extensibility/extensions/loader.ts:616` `discoverAndLoadExtensions()` → `:363` `loadExtensions()`；调用点 `sdk.ts:683`、`sdk.ts:722` | 会话构造期，早于 agent 启动 | **无沙箱，同进程同 runtime**（`docs/extension-loading.md:216-220`）；但**每个 session 各自 `loadExtensions()`，绑定本 session 的 `ExtensionAPI`**（`sdk.ts:436-443`） | Tier 0 |
| 3 | **Hook**（`.ts`/`.js`） | 扩展的「轻量版」：只订阅事件 + 注册命令/渲染器，无 tool 注册 | TS 模块，factory `(pi: HookAPI) => void` | `extensibility/hooks/loader.ts:221` `discoverAndLoadHooks()` → `:192` `loadHooks()` | 与 extension 同期；**JS/TS hook 会被塞进 extension 模块管线一起加载**（`docs/extension-loading.md:44-48`） | 同 extension：无沙箱、同进程 | Tier 0 |
| 4 | **Skill**（`SKILL.md`） | 纯提示词/流程知识，**不执行代码** | Markdown + frontmatter | `extensibility/skills.ts:123` `loadSkills()` → `:86` `loadSkillsFromDir()` | 会话构造期扫描 | **最强的另一端：纯数据**，没有可执行面。frontmatter 只能声明 `hide` / `disableModelInvocation`（`skills.ts:106`） | Tier 0 |
| 5 | **Custom tool**（`.ts`/`.js`） | 只加一个 LLM 可调用工具，不碰事件流 | TS 模块，factory 返回 `{name, description, parameters, execute}` | `extensibility/custom-tools/loader.ts:288` `discoverAndLoadCustomTools()` → `:203` `loadCustomTools()` | 会话构造期 | 同进程无沙箱；但**每个 session 绑定自己的 `CustomToolAPI`**，subagent 只继承**扫描到的路径**而非已加载实例（`sdk.ts:444-455`，注释明写「转发已加载实例会把工具执行路由回父会话——对隔离任务是错的」） | Tier 0 |

补充两类（同属 Tier 0，不在主表但同源）：

| 扩展点 | 入口 | 说明 |
|---|---|---|
| **Custom command**（`.md`） | `extensibility/custom-commands/loader.ts` | 文件即 slash command；仓库自带 `.omp/commands/` |
| **Plugin / Marketplace** | `extensibility/plugins/manager.ts`、`plugins/marketplace/{fetcher,registry,manager}.ts` | 把上面所有类型**打包分发**：一个 plugin 的 `package.json#omp` 可同时声明 extensions / tools / commands / skills |

### 1.2 真正的架构层：capability × provider 矩阵 `[A]`

`packages/coding-agent/src/capability/types.ts:1-7` 的文件头注释是全仓最重要的一段设计说明：

> This architecture **inverts control**: instead of callers knowing about paths like `.claude`, `.codex`, `.gemini`, they simply ask for `load("mcps")` and get back a unified array of MCP servers.

- **Capability（扩展点种类，14 个）**：`packages/coding-agent/src/capability/` — `context-file / extension / extension-module / fs / hook / instruction / mcp / prompt / rule / rule-buckets / settings / skill / slash-command / ssh / system-prompt / tool`
- **Provider（生态来源，17 个）**：`packages/coding-agent/src/discovery/index.ts:22-38` — `agents-md / agents / builtin / builtin-defaults / claude / claude-plugins / cline / codex / cursor / gemini / github / mcp-json / omp-plugins / opencode / ssh / vscode / windsurf`
- **Provider 接口**：`capability/types.ts:33-56` — `{ id, displayName, description, priority, load(ctx) }`，priority 决定冲突时谁赢（`:44-48` 注释给了分段：100+ 主 provider / 50-99 工具专属 / 1-49 共享标准）
- **加载选项**：`capability/types.ts:60-80` — 支持 `providers` 白名单、`excludeProviders` 黑名单、`disabledExtensions`、`dropBeforeDedupe`

**这条最适合上 slide**：omp 能直接吃掉你已有的 Claude Code / Cursor / Codex / Gemini 配置，不需要迁移。这不是「兼容性糖」，是把「配置发现」抽象成了一个可注册的插件点——**扩展点系统本身也是可扩展的**。

### 1.3 隔离级别谱系（从强到弱）

```
MCP server        ── 独立 OS 进程，JSON-RPC 边界，崩溃隔离、崩溃熔断器
   ↓
Skill (SKILL.md)  ── 纯数据，零可执行面
   ↓
Custom tool       ── 同进程，但 per-session API 绑定，执行路由不串会话
   ↓
Extension / Hook  ── 同进程、同 runtime、共享 EventBus，无沙箱
                     只有「错误隔离」：单个 path 加载失败不阻断其他
                     （docs/extension-loading.md:204-224）
```

**诚实评价**：extension/hook 明确「not sandboxed」。omp 提供的是**故障隔离**（loader 逐路径 try/catch、runner 捕获 handler 异常）而**不是安全隔离**。一个恶意 extension 与宿主同权。这一点文档写得很坦白，值得肯定，但在 slide 上不该说成「安全模型」。

### 1.4 加载时序与去重 `[B]` `docs/extension-loading.md:165-187`

`discoverAndLoadExtensions()` 按序拼一张列表再统一加载：

1. 原生自动发现（`<cwd>/.omp/extensions`、`~/.omp/agent/extensions`）
2. JS/TS hook factory
3. 已安装 plugin 的 extension 入口
4. 显式配置路径（CLI `-e/--hook` → settings `extensions`）

去重按**绝对路径、首次出现者胜**。含义：同一模块既被自动发现又被显式配置时，只在第一阶段加载一次。

模块加载走 `loadLegacyPiModule()`（`extensibility/plugins/legacy-pi-compat.ts`），带 `?mtime` cache-buster，**改源码即热重载** `[B] docs/extension-loading.md:193-198`。

---

## 2. 扩展体系 ↔ Tier 成本模型

### ⚠️ 重要前置更正

**`FORK.md` 在本次 checkout（`09a7c8656`）中不存在。** `[A]`
- `git ls-tree HEAD` 无 `FORK.md`
- `git log --all -- FORK.md` 无记录（但仓库是 **shallow clone**，`.git/shallow` 存在、`rev-list --count HEAD` = 10892，所以历史不完整）
- 全仓 grep `"out-of-core"` / `"lowest tier that works"` / `"ZERO sync conflict"` 零命中

因此本节引用的 tier 原文全部来自旧笔记 `R08-ohmypi.md:48-104`，标 `[B]`（文档已核实但**无法在本次 checkout 复验**）。若要在 slide 上引原文，建议先确认 FORK.md 是被删除、被重命名，还是只存在于 shallow 之外的历史。

### 2.1 tier 定义（`[B]`，转引自 R08）

> Every change has a **tier** = how much it costs to carry across an upstream sync. The cost of this fork is dominated by how much lands in Tier 2. **Push everything you can down to Tier 0.**

- **Tier 0 — out-of-core，零同步冲突**：hooks / extensions / capability providers / SYSTEM.md / 磁盘上的 tools·commands·skills·rules·context files
- **Tier 1 — 薄的加性缝（seam）**：只往核心的 list/union 里加一行
- **Tier 2 — 深核心 / Rust patch**：turn loop、prompt 模板结构、TUI 内部、provider 内部、`crates/*`

### 2.2 为什么「做成扩展 = Tier 0 = 可持续」

成本函数不是「代码量」，是「**是否触碰上游文件**」。Tier 0 的东西住在 fork 自有目录（或干脆是独立 npm 包），上游怎么改都**物理上不可能冲突**。所以：

> **一个 1500 行的 Tier-0 扩展，同步成本是 0；一个 3 行的 Tier-2 patch，每次 sync 都可能要人工重解。**

这就是为什么「扩展点的价值 = 它把多少 Tier-2 需求降级为 Tier-0」是设计扩展点时唯一有意义的评价标准。

### 2.3 代码证据：swarm 本体确实是纯 Tier-0 扩展 `[A]`

这是本节最硬的证据链。

**(a) 它是独立 npm 包，不是核心的一部分**
`packages/swarm-extension/package.json`：
```json
"name": "@oh-my-pi/swarm-extension",
"peerDependencies": { "@oh-my-pi/pi-coding-agent": "^16" },
"omp": { "extensions": ["./src/extension.ts"] },
"bin": { "omp-swarm": "src/cli.ts" }
```
- 用 `peerDependencies` 而非 workspace 内部依赖 → 它把宿主当**外部**依赖，是「被加载方」不是「组成部分」
- `omp.extensions` 清单字段正是 `docs/extension-loading.md:142` 描述的 plugin 入口声明格式
- 同时还有独立 CLI `omp-swarm` → 可完全脱离宿主运行

**(b) 入口是标准 extension factory**
`packages/swarm-extension/src/extension.ts:22-25`：
```ts
export default function swarmExtension(pi: ExtensionAPI): void {
	pi.setLabel("Swarm Orchestrator");
	pi.registerCommand("swarm", { ... });
```
只用了公开的 `ExtensionAPI`。

**(c) 核心对它零耦合 —— 决定性证据**
`grep -rli "swarm" packages/coding-agent/src/` 只命中 **1 个文件**，且是**一条注释**：
```
packages/coding-agent/src/modes/controllers/event-controller.ts:55
 * window top, where they are neither on screen nor in history. A swarm burst
```
**核心代码里没有任何一行 import、注册、或 if 分支提到 swarm。**

**(d) 它靠公开 SDK 导出实现多 agent 编排**
`packages/swarm-extension/src/swarm/executor.ts:16`：
```ts
import { runSubprocess } from "@oh-my-pi/pi-coding-agent";
```
子 agent 派生能力是**公开 API**，不是内部特权。1541 行的 YAML DAG 编排器（`dag.ts` 拓扑排序 + `pipeline.ts` 波次执行 + `state.ts` 状态跟踪）**全部住在 Tier 0**。

### 2.4 这条论断能立住的原因

「多 agent 编排」在大多数 agent 框架里都是 Tier-2 级需求——要改 turn loop、要改调度器。omp 把它做成了一个可以 `npm install` 的外部包。**这是「扩展面表达力上限」的活体证明**：如果 swarm 都能用扩展写完，那用户的需求几乎不可能撞到天花板。

反向的诚实提醒：`ExtensionAPI` 有 **43 个事件 + 20+ 个 action**（`extensions/types.ts:961-994`、`:1103-1301`），`types.ts` 单文件 1571 行。**「Tier-0 表达力强」的代价是扩展接口本身成为一个巨大的、必须长期兼容的公共 API 面。** 这个成本被转移了，没有消失。

---

## 3. 与上游 pi 的扩展机制对比

### 3.1 子系统存在性对照 `[A]`

| 子系统 | 上游 pi (`583f153`) | omp (`09a7c865`) |
|---|---|---|
| Extension module | ✅ `packages/coding-agent/src/core/extensions/`（types 1713 行 / loader 713 / runner 1236） | ✅ `src/extensibility/extensions/`（types 1571 / loader 624 / runner 1396） |
| **MCP** | ❌ **完全没有**。`grep -rli "modelcontextprotocol\|mcpServers" packages/coding-agent/src` 零命中；无 `mcp` 目录 | ✅ `src/mcp/` 23 文件，manager 1521 行 + OAuth 全流程 + stdio/http/sse 三 transport + tool cache |
| **Hook** | ❌ 无 `hooks` 目录 | ✅ `src/extensibility/hooks/`（types 612 / runner 425 / loader 244） |
| **Custom tool** | ❌ 无 | ✅ `src/extensibility/custom-tools/` |
| **Plugin / Marketplace** | ❌ 无 | ✅ `src/extensibility/plugins/` + `plugins/marketplace/` |
| **Capability / Discovery** | ❌ 无 `capability`、无 `discovery` 目录 | ✅ 14 capability × 17 provider |
| Skill | ✅ 有（`core/resource-loader.ts`、`core/pi-manifest.ts`、测试 fixture `test/fixtures/skills/`） | ✅ `src/extensibility/skills.ts` 511 行，跨 5 个 provider 发现 |

**一句话**：pi 的扩展面 = 「一个 extension module 机制」；omp 的扩展面 = 「一个扩展点注册表 + 五种扩展点 + 一个分发市场」。

### 3.2 事件面对比 `[A]`

两边**规模相当，但取向不同**（注意：pi-mono 也在持续演进，这是两条并行的演化线，不是「omp 单方面加了多少」）。

**pi 有而 omp 没有**（`pi-mono/.../core/extensions/types.ts:1198-1239`）：
`project_trust`、`session_info_changed`、`session_before_fork`、`agent_settled`、`model_select`、`thinking_level_select`、`before_provider_headers`、`message_end` 带返回值

**omp 有而 pi 没有**（`oh-my-pi/.../extensions/types.ts:961-994`、`:1142-1180`）：
`session.compacting`（可完全接管压缩）、`session_stop`（可否决停止）、`before_provider_request`（可替换整个请求负载）、`goal_updated`、`credential_disabled`、`mcp_notification`、`user_python`、`tool_approval_requested` / `tool_approval_resolved`、`ttsr_triggered`、`todo_reminder`、`auto_retry_start` / `auto_retry_end`

omp 新增事件的共同特征：**围绕它自己新增的子系统**（MCP 通知、审批模式、自动重试、TTSR、Python 执行、凭证轮换）。扩展点跟着功能一起长——这本身就是 tier 模型的行为印记。

### 3.3 接口兼容吗？—— **源码级兼容，靠加载期 specifier 重写** `[A]`

omp 换了包 scope（`@mariozechner/*` → `@oh-my-pi/*`），本会让所有既有 pi extension 失效。omp 的解法在 `packages/coding-agent/src/extensibility/plugins/legacy-pi-compat.ts`（2000+ 行）：

- `:619` `const PI_SCOPE_ALIASES = ["oh-my-pi", "mariozechner", "earendil-works"]` —— 三个历史 scope 全部接受
- `:654` `LEGACY_PI_SPECIFIER_FILTER` 正则匹配所有需重写的 specifier
- `:851-853` 把 `@*/pi-ai`、`@*/pi-coding-agent`、`@*/pi-tui` 映射到三个 shim 模块（`extensibility/legacy-pi-{ai,coding-agent,tui}-shim.ts`）
- `:955` `rewriteLegacyExtensionSource()` 在 Bun `onLoad` 钩子里**改写源码文本**再交给 Bun 求值
- `:627-631` 还处理了「上游在包根暴露、omp 挪到子目录」的路径迁移
- 清单字段双认：`omp.extensions` **和** legacy `pi.extensions` 都接受（`docs/extension-loading.md:142`、`:263-271`）

**评价**：这是一个很实在的兼容方案——不改用户代码、不要求重新发包，代价是宿主里常驻一个 2000 行的加载期改写器。它保证的是**源码兼容**，不是 ABI 或语义兼容：pi 独有事件（如 `model_select`）在 omp 上不会触发，import 能过、行为静默失效。

**发现路径也有兼容层但已收窄** `[B] docs/extension-loading.md:41-42`：原生自动发现现在是 `.omp` 目录制，`.pi/extensions` **不再是原生根**，仅在包清单 `pi.extensions` 和项目 override 查找中保留。

---

## 4. `collab-web` — 会话共享与端到端加密

### 4.1 传输模型：**事件级复制 + 对端本地重渲染**（确认，非屏幕镜像）`[A]`

证据链：

- `packages/collab-web/src/lib/client.ts:285-404` `#applyFrame()` 是结构化帧的 switch：`welcome` / `snapshot-chunk` / `entry` / `event` / `state` / `agents` / `bus` / `ui-request` / `transcript` / `bye` / `error`。更新的是 `#entries: readonly SessionEntry[]` / `#state` / `#agents`（`:108-120`）——**没有字符缓冲区、没有 ANSI 解析、没有屏幕单元格结构**
- `client.ts:406-486` `#applyEvent()` 处理的是 agent 语义事件（`message_start/update/end`、`tool_execution_*`、`agent_start/end`、`auto_retry_*`、`auto_compaction_*`），不是终端事件
- 渲染是浏览器自己的 React DOM：`src/tool-render/registry.ts` 有 30+ 个 per-tool 渲染器（`tools/*.tsx`）。若是屏幕镜像，这些渲染器不必存在
- `src/lib/jsonl.ts:8-22` `parseJsonl(text, carry)` + `src/lib/transcript-poll.ts:26-36`：子 agent transcript 按**字节偏移增量拉原始 JSONL**，本地解析、本地渲染
- Host 侧同构：`packages/coding-agent/src/collab/host.ts:388-411` 把 `snapshotForReplication()` 的 entries 过滤后用 `welcome` + `snapshot-chunk` 发送
- `[B]` `docs/collab.md:3`：「Guests render the same session natively in their own TUI … no terminal mirroring」

**架构含义（适合上 slide）**：因为传的是语义事件而非像素/字符，guest 可以用**完全不同的渲染器**——TUI guest 用终端渲染，web guest 用 React DOM，同一份事件流。这是「事件溯源」在协作场景的直接收益，也意味着 session 本身就是可重放的。

### 4.2 端到端加密

**算法：AES-256-GCM（WebCrypto）** `[A]` `packages/collab-web/src/lib/codec.ts:10-11`
```ts
const AES_ALGORITHM = "AES-GCM";
const IV_LENGTH = 12;
const KEY_LENGTH = 32;
```
封装（`codec.ts:29-38`），线格式 `[12B IV][ciphertext+tag]`（`codec.ts:6` 注释）：
```ts
const iv = new Uint8Array(IV_LENGTH);
crypto.getRandomValues(iv);
const plaintext = TEXT_ENCODER.encode(JSON.stringify(frame));
const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: AES_ALGORITHM, iv }, key, plaintext));
```
Host 侧字节级同构实现：`packages/coding-agent/src/collab/crypto.ts:10-54`。互操作有硬编码测试向量：`packages/collab-web/test/codec.test.ts:6-18`（用真实 host `seal()` 产出的密文，web 端能解出），篡改拒绝测试 `:27-32`。

**认证标签** `[A]/[C]`：GCM 自带 tag 附在密文尾。代码**未显式传 `tagLength`**，走 WebCrypto 默认 128 bit——「默认值是 128」是规范事实，不是代码里写死的，此处标 `[C]` 边界。

**Nonce/IV** `[A]`：每帧 `crypto.getRandomValues` 生成全新 12B 随机 IV，明文前缀传输。通读 `codec.ts` / `socket.ts` / `client.ts` **未发现任何 nonce 记录表、序号校验、重放检测或 rekey 逻辑**。

**密钥来源与交换 —— 没有密钥协商，是带外预共享密钥（PSK）** `[A]`
- 生成：`packages/coding-agent/src/collab/host.ts:212-213` `generateRoomKey()` / `generateWriteToken()`；`packages/wire/src/index.ts:412`、`:419` 用 `crypto.getRandomValues`，roomKey 32B、writeToken 16B
- 分发：整条链接。`src/lib/link.ts:6` 格式 `wss://<host>/r/<roomId>.<base64url-key>`；full link 是 `base64url(key ∥ writeToken)` = 48B（`link.ts:128-143`）
- **注意**：分隔符是**点号**不是 `#`，因为 RFC 3986 禁止 fragment 里出现裸 `#`（`link.ts:114-127` 注释）。但 **web 客户端仍把整条链接放在页面 URL 的 fragment 里**：`src/app.tsx:31-37` `hashLink()`、`:59` `window.location.hash = link` —— 浏览器不会把 fragment 发给服务端

**密钥从不发给服务端** `[A]`
- 建连 URL：`src/lib/socket.ts:110` `new WebSocket(\`${this.#opts.wsUrl}?role=${this.#opts.role}\`)`
- `wsUrl` 由 `parseCollabLink` 产出，`link.ts:189` 返回 `\`${normalized.origin}/r/${roomId}\`` —— **不含 key**（`packages/wire/src/index.ts:428` 注释：「no query, no fragment」）
- key 只进 WebCrypto，且 `importKey(..., extractable=false, ...)`（`codec.ts:26`）
- **writeToken 也走加密信道**：`client.ts:215` `send({ t:"hello", proto, name, writeToken })`，而 `socket.ts:75` 先 `seal()` 再上线 → relay 看不到 write token

### 4.3 服务端能看到什么

**⚠️ 关键限定** `[A]`：**生产 relay 的实现不在本仓库。** 全仓无 `.go` 文件；`grep -rln "peer-joined"` 只命中本地桩与测试（`packages/collab-web/scripts/local-relay.ts`、`packages/coding-agent/test/collab/helpers/in-memory-relay.ts`）。`[B]` `docs/collab.md:114` 称「The relay is a small content-blind Go service」——**该承诺无法在本仓库做代码级验证**。下表基于本地桩 + 协议契约。

| relay 可见的**明文** | 证据 |
|---|---|
| roomId（URL path） | `local-relay.ts:20,53` `ROOM_PATH_RE = /^\/r\/([A-Za-z0-9_-]{10,64})$/` |
| role=host\|guest（query） | `local-relay.ts:54-55` |
| 4 字节 BE peerId 路由前缀 | `local-relay.ts:88` `unpackEnvelope()`；`link.ts:58-63` `packEnvelope` |
| 每帧密文**大小** | `local-relay.ts:97` 直接读 `message.byteLength` |
| 消息条数 / 时序 / 时间戳 | 隐含于每帧一次回调 |
| 连接数、guest 加入/离开 | `local-relay.ts:78-81,117-119` 明文 TEXT `{"t":"peer-joined","peer":N}` |
| 房间生命周期 | `local-relay.ts:109` `{"t":"room-closed"}` |

**relay 看不到**：所有 payload。`local-relay.ts:17` 注释「The relay never sees plaintext: payloads stay sealed end to end.」；转发路径 `:90-99` 只读/改写 peerId，密文原样 `guest.send(message)`，从不解析 payload。

### 4.4 guest 权限模型 —— **两层，真正强制点在 host** `[A]`

Guest→host 可发帧：`sendPrompt`（`client.ts:172`）、`sendUiResponse`（`:176`）、`sendAbort`（`:184`）、`sendAgentCmd`（`:188`，chat/kill/revive）、`fetchTranscript`（`:197`）。

**(a) 客户端 UI 层（软，可绕过）**：`src/components/shell/Composer.tsx:117-133` 的 `readOnly` 只是禁用输入框，改 JS 即可绕过。

**(b) Host 层（硬强制）**：`packages/coding-agent/src/collab/host.ts:358-364`，**timing-safe** 校验 16B write token：
```ts
/** Timing-safe write-token check; peers without a valid token are read-only. */
#verifyWriteToken(token: string | undefined): boolean {
	const expected = this.#writeToken;
	if (!expected || !token) return false;
	const bytes = Buffer.from(token, "base64url");
	return bytes.byteLength === expected.byteLength && timingSafeEqual(bytes, expected);
}
```
结果存 peer 表（`host.ts:380-381`），**每个变更帧独立复查**并定向回错（`#rejectReadOnly` `:366-369`）：prompt `:469-473`、abort `:502-506`、agent-cmd `:586-590`、ui-response `:461-465`。额外硬化：`host.ts:591-595` 即使有 write token 也拒绝对 `kind === "advisor"` 的 agent 做 chat/kill/revive。

**读权限没有分级** `[A]/[B]`：view 链接（32B 裸 key）能读全部内容，含子 agent transcript（`fetch-transcript` 路径无 canWrite 检查；`docs/collab.md:90` 确认）。

**身份归属无密码学保证** `[A]`：`host.ts:487` 的 `from` 来自 guest 自报的 `hello.name`，仅 `trim().slice(0,64)`（`:379`）。任何持链接者可自称任意名字（`docs/collab.md:86` 也说 names are display-only）。

### 4.5 链接生命周期 `[A]`

- **无 TTL / 无 exp / 无过期时间戳**。grep `revoke|rotate|expire|ttl` 覆盖 `src/collab/` 与 `collab-web/src/` 后只命中 toast 时长和 CSS `rotate(90deg)`
- 生命周期 = 房间生命周期，房间随 host WebSocket 存在（`local-relay.ts:66-70` 建房 / `:105-115` host 断开则删房 + 广播 `room-closed` + close 4001）
- **撤销的唯一手段是整体 `/collab stop`**（`host.ts:291-295`）：**没有单 guest 踢出、没有 token 撤销、没有密钥轮换**。重开会生成全新 roomId/key/token（`host.ts:212-214`）
- Host 自动停止：会话切换时 `host.ts:322-330` 自动 `stop("session switched")`
- 重连：指数退避 1s→30s 带抖动（`socket.ts:202-211`）；致命码不重连（`socket.ts:15-20`：4001/4004/4009/4029）；**解密失败永不重连**（`socket.ts:158-161` → `#failFatal("bad key or corrupted frame")`）
- 协议闸门：`packages/wire/src/index.ts:397` `COLLAB_PROTO = 3`，host 严格比对拒绝旧版（`host.ts:371-377`）
- 浏览器残留：链接（含 key）进 `window.location.hash`（`app.tsx:59`），留在历史里；`leave()` 时 `history.replaceState` 清掉（`app.tsx:72`）。`localStorage` 只存显示名，**不存 key**（`app.tsx:25,54`）

### 4.6 安全弱点小结（均 `[A]`，除标注外）

1. **无过期、无单点撤销**：full link 一旦泄漏，在整个 host session 期间等于完全控制权（prompt / abort / kill subagent）。唯一止血是 `/collab stop`
2. **12B 随机 IV + 无帧序号**：恶意 relay 可**丢帧 / 重放 / 重排**而不被检测（GCM 只保护单帧完整性）。同 key 下随机 IV 的碰撞是标准 birthday bound，代码无缓解也无 rekey
3. **peerId 由 relay 写入且是明文，`from` 名字由 guest 自报**：转录里的「谁说了什么」不具备密码学保证
4. **`[A]`代码 + `[C]`结论：web 路径上 E2EE 有信任降级**。`[B] docs/collab.md:117-118` 说同一 relay 还托管静态 web 客户端 —— 即**你的浏览器客户端 JS 由 relay 投递**，而 key 在 fragment 里。恶意/被攻陷的 relay 理论上可投毒 JS 拿到明文。代码中未见 SRI / pinning 之类缓解。**注意**：这条的前半（relay 托管 web 客户端）是文档说法，我未在本仓库读到 relay 的静态资源服务实现
5. **生产 relay 代码不在本仓库**，「content-blind」承诺无法代码级验证

---

## 5. `packages/stats` — 遥测与隐私（重点结论）

### 5.1 结论：**omp 没有默认开启的远程遥测；`packages/stats` 100% 本地、零出网。** `[A]`

### 5.2 stats 统计什么、存哪 `[A]`

- **数据源：纯本地读会话文件**。`packages/stats/src/parser.ts:448-450` `listSessionDirs()` 直接 `fs.readdir(getSessionsDir())`，`:462` 只收 `.jsonl`；`packages/utils/src/dirs.ts:769-771` `getSessionsDir()` → `~/.omp/agent/sessions`
- **存储：本地 SQLite**。`packages/stats/src/db.ts:1` `import { Database } from "bun:sqlite"`；`:78` `db = new Database(getStatsDbPath())`；`packages/utils/src/dirs.ts:700-702` → `~/.omp/stats.db`
- **统计维度**（`db.ts:8-31`）：按 model / provider / folder / agentType / tool 聚合的 requests、input/output/cacheRead/cacheWrite tokens、cost、TTFT、duration、error rate、premium requests、时间序列
- **最敏感的一块**：`packages/stats/src/user-metrics.ts:8-60` 的 `UserMessageMetrics` 对**用户输入原文**做行为学分析——`chars`/`words`/`yelling`(全大写句数)/`profanity`(脏话命中)/`anguish`(崩溃情绪信号)/`negation`(纠错次数)/repetition。**但它是纯函数、无 I/O**（`user-metrics.ts:1-6` 注释「Pure, side-effect free」），结果只落本地 behavior 表

### 5.3 `sync-worker` 的 "sync" 不是网络同步 `[A]`

`packages/stats/src/sync-worker.ts:1-12` 文件头注释：

> Stateless parse worker for `syncAllSessions`. The main thread owns the SQLite handle; workers receive `{ sessionFile, fromOffset }`, run `parseSessionFile` (**which is pure I/O + CPU, no DB**), and post the structured-clone-safe result back.

全文件 40 行，唯一外部调用 `parseSessionFile()`（`:33`），唯一输出 `self.postMessage`（`:31,:34,:37`）。**无 fetch、无 net、无 URL。** `aggregator.ts:220-260` `syncAllSessions()` 做的是 mtime 比对 + 增量 offset 解析 + 写本地 DB。

### 5.4 `server.ts` 是本地 dashboard `[A]`

`packages/stats/src/server.ts:303-306` `Bun.serve({ port, fetch })`；`packages/stats/src/index.ts:175` 打印 `http://localhost:${port}`（默认 3847，`index.ts:104`）。整个 `packages/stats/src` **只有 2 处 fetch**：
- `port-conflict.ts:23` `fetch("http://localhost:${port}/api/stats/models")` —— 端口冲突时探测是否自家 dashboard，**localhost only**
- `client/api.ts:30` 浏览器端，`API_BASE = "/api"`（`:15`），**相对路径无外域**

无 CDN 依赖（`server.ts:169-181` 内联 HTML 只引本地资源）。

### 5.5 全仓出网点清查

| 类别 | 端点 | 默认 | 数据 | 证据 |
|---|---|---|---|---|
| 🔴 Auto-QA grievance | `https://qa.omp.sh/v1/grievances` | 功能位 `dev.autoqa` 默认 `true`，**但 consent 默认 `unset` = 不发** | `{agent, installId, platform, arch, entries:[{id,model,version,tool,report}]}` | 端点 `config/settings-schema.ts:5476`；body `tools/report-tool-issue.ts:419-427`；POST `:435-440` |
| 🟡 npm 版本检查 | `https://registry.npmjs.org/@oh-my-pi/pi-coding-agent/latest` | `startup.checkUpdate` 默认 `true` | **无 payload、无 installId**，仅 GET | `main.ts:115-118`；默认值 `settings-schema.ts:1798-1800` |
| 🟢 collab relay | `wss://my.omp.sh` | 需 `/collab` 主动开 | 仅密文 | `packages/wire/src/index.ts:422` |
| 🟢 session share | `https://my.omp.sh/s` | 需 `omp share` 主动执行 | 用户显式分享 | `packages/wire/src/index.ts:425`；`export/share.ts:510` |
| 🟢 OpenRouter 归属 header | `HTTP-Referer: https://omp.sh/` | 随你自己的 LLM 请求 | 仅 header 字符串 | `packages/ai/src/utils/openrouter-headers.ts:6` |
| 🟡 OpenTelemetry | **无硬编码地址** | **纯 opt-in**，需设 `OTEL_*` env | 发往**你自己的** collector | `telemetry-export.ts:7-8`、`:216-230`；`OTEL_SDK_DISABLED` 支持见 `:139` |

**grep 阴性结果** `[A]`：`posthog` / `sentry` / `amplitude` / `mixpanel` / `segment.io` / `beacon` / `navigator.sendBeacon` 全仓（排除 node_modules）**零命中**。

### 5.6 Auto-QA 的 consent 门是**硬阻断** `[A]`

这是本节最重要的细节，决定了「默认开启」四个字的实际含义：

- `tools/report-tool-issue.ts:531` — `if (!$flag("PI_AUTO_QA_PUSH") && !(await resolveAutoQaConsent(session.settings))) return;` ← **未同意则连本地 DB 都不写**
- `:384-386` — `const consented = settings?.get("dev.autoqaConsent") === "granted"; if (!consented && !$flag("PI_AUTO_QA_PUSH")) return null;` ← 返回 null 则 `flushGrievances`（`:477-478`）直接 skipped
- `dev.autoqaConsent` 默认 `"unset"`（`settings-schema.ts:5504-5508`），首次触发弹 Yes/No（`modes/interactive-mode.ts:3962-3967`，handler 注册于 `:909`）
- **headless / 无 handler 时 `resolveAutoQaConsent` 返回 `false`**（`report-tool-issue.ts:236`）→ CI 环境默认静默不报
- 触发条件极窄：只有模型主动写 `xd://report_issue` 才走这条路（`:545-559`），**不是周期性心跳**
- 本地暂存 `~/.omp/autoqa.db`（`:253-256`）

**精确表述：「默认开启」的是功能开关，「默认关闭」的是数据流。用户必须亲手点 Yes 才会发生第一次上传。**

### 5.7 `install-id` `[A]`

- 实现在 `packages/utils/src/dirs.ts:885-937`（**没有独立的 `install-id.ts`**，只有 `docs/install-id.md` 和测试）
- 生成：`dirs.ts:900` `const next = crypto.randomUUID();` —— **纯 CSPRNG UUIDv4，不混入 hostname / username / MAC / 任何主机熵**
- 存储：`~/.omp/install-id`，`dirs.ts:910` 以 `O_WRONLY|O_CREAT|O_EXCL, 0o600` 独占创建
- **全仓唯一消费者**：`tools/report-tool-issue.ts:422` `installId: getInstallId()`（grep `getInstallId` 在 src 中仅命中定义 + 该文件 import/使用）
- `[B]` `docs/install-id.md:34` 确认唯一 consumer；`:36` 要求「MUST NOT derive PII from it」

**即：install-id 只在你同意 Auto-QA 后、随 grievance 上报时才离开本机。**

### 5.8 opt-out 开关 `[A]`

| 开关 | 位置 | 效果 |
|---|---|---|
| `dev.autoqa: false` | `settings-schema.ts:5462` | 完全关闭 Auto-QA |
| `PI_AUTO_QA=0` | `report-tool-issue.ts:114` | env 覆盖，优先级最高（`:101` 注释：env > settings > default） |
| `dev.autoqaConsent: "denied"` | `settings-schema.ts:5504`；`report-tool-issue.ts:109-112` | 弹窗选 No 即持久化，之后完全 no-op |
| `startup.checkUpdate: false` | `settings-schema.ts:1798` | 关闭 npm 版本检查 |
| `OTEL_SDK_DISABLED=true` | `telemetry-export.ts:139` | 关闭 OTLP |
| `PI_AUTO_QA_PUSH_URL` | `report-tool-issue.ts:388` | 改指自己的端点 |

**不存在的开关** `[A]`：`DO_NOT_TRACK`、`OMP_NO_TELEMETRY`、`disableTelemetry` 全仓**零命中**。**omp 不遵守 `DO_NOT_TRACK` 事实标准。**

### 5.9 `devicecheck` 是给 OpenAI 的，不是给作者的 `[A]`

- `crates/pi-natives/src/devicecheck.rs:3` 注释：「Reimplements the flow the ChatGPT desktop app's `devicecheck.node` addon」
- 唯一调用点 `packages/coding-agent/src/live/attestation.ts:86` `deviceCheckGenerateToken()`，在 `generateCodexAttestation()` 内
- **触发条件极窄**：`attestation.ts:82` `if (process.platform !== "darwin" || process.arch !== "arm64") return undefined;` —— 只有 macOS ARM64，且只在 ChatGPT-OAuth Codex provider 路径
- 采集内容 `attestation.ts:45-59`：locale、timeZone（各截 64 字符）、`APP_SESSION_ID`（进程启动时 `crypto.randomUUID()`，**每次重启就变，非持久标识**），加上硬编码 `bundle_id = "com.openai.codex"`（`:69`、`:3`）和 Apple 签发的 DeviceCheck token
- 打包进 `x-oai-attestation` header 发给 **OpenAI**（`live/transport.ts:97`）。**与 omp 作者服务器无关，不含 install-id**
- `[B]` `packages/natives/CHANGELOG.md:84`：非 macOS 构建 `supported: false` 且「without touching the network」

### 5.10 值得批评的地方

1. **文档缺位** `[B]`：`docs/environment-variables.md` 中 grep `PI_AUTO_QA` / `telemetry` / `track` / `opt-out` / `checkUpdate` **全部零命中**。`PI_AUTO_QA*` 在 `docs/*.md` 中仅 `docs/install-id.md:34` 顺带提及一次。**没有任何一份文档系统性说明「omp 会向 qa.omp.sh 发东西以及如何关闭」**
2. **不支持 `DO_NOT_TRACK`** `[A]`
3. **grievance 的 `report` 字段无脱敏** `[A]`：`report-tool-issue.ts:536-538` 原文入库、`:427` 原文出网，且 `report` 是**模型自己写的自由文本**。同意弹窗承诺 "nothing personal"、系统提示词要求写 `<tool>: <concise description>`，但代码路径上**没有任何过滤 / 脱敏 / 截断**

---

## 6. `packages/tui` — 终端渲染架构

### 6.0 一句话结论

omp 与上游 pi 的 TUI 是**架构分叉**，不是「omp 优化了 pi」：**上游 pi 押注「alt-screen + 约束式布局树」，omp 押注「单一主屏 append-only 提交账本 + 三层前缀增量」**，并把文本度量整体下沉到 Rust。`[A]`（文件事实）/ `[C]`（「投资取向」是判断）

代码规模对比 `[A]`：

| | omp `packages/tui/src` | 上游 pi `packages/tui/src` |
|---|---|---|
| 总行数 | **25,666** | **14,184** |
| `tui.ts` | 4,272 | 1,223 |
| `components/markdown.ts` | 3,106 | 861 |
| `terminal.ts` | 1,824 | 531 |
| `keys.ts` | 566 | 1,401 |
| `utils.ts` | 619（大部分下沉 Rust） | 1,303 |
| test 文件数 | **97** | 36 |

- **omp 独有**：`terminal-capabilities.ts`(1211)、`latex-to-unicode.ts`(2017)、`latex-block.ts`(1338)、`deccara.ts`(314)、`kitty-graphics.ts`、`desktop-notify.ts`、`loop-watchdog.ts`、`mouse.ts`、`bracketed-paste.ts`、`tmux.ts`、`components/tab-bar.ts`
- **上游 pi 独有**：`layout.ts`、`layout-node.ts`、`tui-alt-screen.ts`(805)、`tui-main-screen.ts`(552)、`components/{stack,h-stack,v-stack}.ts`、`terminal-colors.ts`、`terminal-image.ts`、`undo-stack.ts`、`word-navigation.ts`
- 上游设计意图见 `pi-mono/tui-plan.md`（1001 行，"Alternate-Screen Layout System Plan"）：约束布局是 alt-screen 专属；每次渲染重建布局树、**不做增量布局**（`tui-plan.md:18`）；非目标里明确列了 transcript 虚拟化和增量布局树（`:104-116`）
- omp 的 `index.ts` 不导出任何 layout/stack/alt-screen；`altScreenActive` 只在 `terminal.ts:218-231` 作为待复位状态位存在

### 6.1 核心洞察：「你无法观测终端的滚动位置」`[A]`

`docs/tui-core-renderer.md:26-35`（omp 有 3 篇 TUI 设计文档：`tui-core-renderer.md` 382 行 / `tui-runtime-internals.md` 224 行 / `tui.md` 269 行）：

> 渲染器**无法观测终端滚动位置**——ConPTY 的探测会撒谎，POSIX 根本没有 API。旧引擎去猜「什么时候能安全重写 native scrollback」，每种策略都只是在 yank / 闪屏 / 花屏 / resize 前不可见 这几类 bug 之间来回换。

**新引擎取消了这个猜测**：native scrollback **append-only**，滚上去的行永远不改。

这是本节最适合上 slide 的一条——**一个把「猜测」从系统里删除掉的架构决策**。

### 6.2 三层前缀机制 `[A]`

**(1) commit ledger（引擎层）** `docs/tui-core-renderer.md:38-63`
- `committedRows C`（已物理进入历史，不可变）、`windowTopRow W = max(C, L-height)`
- 组件通过 `NativeScrollbackLiveRegion` 接口（`tui.ts:206-233`）汇报两个边界：**byte-stable end B**（保证不再重排版）与 **durable end D**（字节还可能漂移但内容永久，例如流式 markdown 表格重新对齐列宽）
- 每帧只把 `frame[C, C')` 这一块写进历史，`C' = max(C, min(D, W))`

**(2) committed-prefix 审计（防组件违约）** `tui.ts:864-910` `findCommittedPrefixResync()`，契约在 `tui.ts:829-861` 与 `test/committed-prefix-resync.test.ts:5-16`
- 只采样前缀**尾部**（最后 24 行 / 8 个非空样本），O(1) 成本，不是全量比对
- `rowsEquivalent()` 剥掉 SGR 再比 → **主题切换导致的重新着色不触发 resync**（历史里留旧配色是可接受产物）
- 尾部窗口内**容忍 1 个 mismatch**（离屏还在跳的 spinner / 单行原地编辑）；出现 2 个才判定为行位移
- 原则一句话：**duplication, never loss**
- 修复手段：能用 ED3（`CSI 3 J`）的终端擦掉重放；multiplexer pane 里 ED3 不安全，就在旧片段下方重新锚定

**(3) RenderStablePrefix（组件层，跳过重复工作）** `tui.ts:242-268`
- 语义很讲究：「**读取即消费**」，读完把 baseline 重置到当前数组状态，所以引擎帧之间的带外 `render()`（如 exporter 遍历树）只会**降低**这个数字不会虚高

### 6.3 流式 markdown 的增量渲染（最适合上 slide 的一段）`[A]`

`packages/tui/src/components/markdown.ts`：

- **问题**：marked **没有可恢复的 lexer**，流式追加时每次都要全量重 lex
- **解法**：找一个「冻结前缀」`#streamPrefixText` / `#streamPrefixTokens`（`markdown.ts:1426-1435`），使 `lex(prefix) ++ lex(tail) === lex(prefix+tail)`，只重 lex 增量尾巴
- **难点是「哪里能切」的正确性证明**（`markdown.ts:893-902`、`stableBlockBoundary()` `:960-1000`）：切点必须是 `\n\n` 硬分段、必须在文本内部（末尾切不安全，下一个字符还没到）、下一个字符必须是真正的块内容
- **最刁钻的一条：列表可能跨空行继续**。`listMayContinueAt()` `markdown.ts:913-946` 逐字符模拟 marked v18 的 `listItemRegex`，并明确处理 append-only 语义下「什么叫已经确定关闭」：尾部是 `"1x"` 永远不可能长成有序项（可冻结），尾部是 `"1"` 还可能长成 `"1. c"`（不可冻结）。**保守答案永远是「别冻结」**
- **独立发现（很好的分享故事）**：`markdown.ts:985-996` —— **Bun 的正则引擎对 marked 的块规则不做起始锚点优化**。`hr`/`lheading`/`table`/`html` 都是 `^` 锚定的量化分支交替，每次失败的 `exec` 会重扫剩余全文 → lexing 退化成 O(n²)。实测 **800KB 消息在 Bun 下 ~41s，Node/V8 只要 ~60ms**，且跑在渲染路径上直接冻 UI。对策 `lexWindowed()`（`:1020-1046`）：2KB 窗口，边界由 marked 自己的 block-only 探测 lex 给出，inline tokenization 延到最后统一做；<16KB 走单遍。**41s → ~0.7s**
- 渲染层还有 `#streamPrefixLineCache`（`:1433-1450`）。测试手法值得学：`test/markdown-stream-prefix-cache.test.ts:16` 断言的是「流式追加时 codeBlock 主题回调调用次数 == 0」——**用回调次数当缓存命中断言，比断言耗时稳定得多**

### 6.4 渲染调度：自适应背压 `[A]`

- 不是 rAF 也不是固定 tick，是「按需 + 自适应节流」的 timer 链：`tui.ts:2354` `#scheduleRender()`，每帧回调执行完若 `#renderRequested` 仍为真就重排下一帧（`:2378-2389`）
- 节流基线 **30fps**：`#MIN_RENDER_INTERVAL_MS = 1000/30`（`tui.ts:940`）；上游 pi 是固定 16ms（`pi-mono/packages/tui/src/tui.ts:332`）
- **自适应背压**（`tui.ts:2368-2376`）：`adaptiveFloor = min(200, lastFrameCost × 2)`，即目标「**render duty cycle ≤ 50%**」——下一帧最早在「上帧开始 + 2×上帧耗时」才开；上限 200ms（~5fps 地板，再慢用户会以为界面死了）。**上游 pi 完全没有这个机制**
- **可注入的 `RenderScheduler` 抽象**（`tui.ts:104-122`）让渲染循环在测试里变成确定性可驱动：`test/input-render-scheduling.test.ts:21` 的 `DeferredRenderScheduler` 验证输入优先级；`test/render-stress-scheduler.ts:4` 的 `StressRenderScheduler` 用虚拟时钟 + `drain()`，>100 轮不收敛就报错——**把「渲染循环收敛性」做成了断言**
- 多种 settle/debounce 窗口，注释里每条都挂着 issue 号（`tui.ts:948-995`）：`MULTIPLEXER_RESIZE_DEBOUNCE_MS = 50`（#2088 tmux SIGWINCH 早于 pane 重排完成 → 闪屏）、`RESIZE_VIEWPORT_SETTLE_MS = 120`（拖拽期间只画 throwaway 帧不动 commit ledger，避免 O(history) 的 markdown 重 lex × 每秒几十次）、`CONPTY_POST_FULL_PAINT_SETTLE_MS = 150`（#2095）、`GHOSTTY_INITIAL_IMAGE_DELAY_MS = 100`
- **事件循环看门狗**：`src/loop-watchdog.ts:44` —— 每 250ms 排一个 tick，迟到 >250ms 判定 loop 被阻塞，用 `takeRecentLoopPhase()` 给卡顿打上「是谁卡的」标签；>60s 视为系统休眠不上报；handle `unref()` 不吊住进程。**这是「TUI 里给自己装 APM」**

### 6.5 宽字符 / Unicode：下沉 Rust + 运行时协商 `[A]`

- omp 把宽度计算整体下沉：`packages/tui/src/utils.ts:1-13` 从 `@oh-my-pi/pi-natives` 导入 `visibleWidth / truncateToWidth / sliceWithWidth / wrapTextWithAnsi / extractSegments`
- Rust 实现 `crates/pi-natives/src/text.rs`（**2065 行**），用 `unicode_width` crate（`:20`），ASCII 快路径不做 grapheme 分段也不做 UTF-8 转换（`:5-6`）。导出：`visible_width`(`:1832`)、`truncate_to_width`(`:1260`)、`slice_with_width`(`:1574`)、`extract_segments`(`:1795`)、`wrap_text_with_ansi`(`:1245`)
- 上游 pi 对比：`pi-mono/packages/tui/src/utils.ts:1` 用 npm 的 `get-east-asian-width` + `Intl.Segmenter`，手写 emoji/RGI 判定和 legacy wcwidth 例外表（`:22, :45`）

**韩文兼容字母（Hangul Compatibility Jamo, U+3131..U+318E）—— 终端不一致的经典案例**：

- 关键认知（`text.rs:601-604`）：**这个宽度由客户端终端决定，不是宿主 OS**。UAX#11 说宽（2 cells），macOS 平台惯例是窄（1 cell），实际取决于你连的是哪个终端
- 做成运行时可配置：`setHangulCompatibilityJamoWidth()`（`utils.ts:79-84`），类型 `"platform" | "unicode" | 1 | 2`，wire 编码 0/1/2/3 传给 native（`:23-27`），Rust 侧 `set_hangul_compat_jamo_width_override`（`text.rs:608`）
- **按终端 profile 决定**：Ghostty → 2，Warp → 1，其余 → platform 默认（`terminal-capabilities.ts:110-114`）。Ghostty 的检测有三条路径（`GHOSTTY_RESOURCES_DIR` / `TERM_PROGRAM` / `TERM=xterm-ghostty`），因为过滤 env 的 shell 会丢掉前两个
- **width epoch 失效机制（漂亮的小设计）**：`utils.ts:36-41` `widthConfigEpoch`，任何影响宽度的运行时配置变更让 epoch++，所有派生缓存必须带 epoch 戳，不匹配即丢弃
- **line-width sidecar**（`utils.ts:44-76`）：`WeakMap<readonly string[], {epoch, lines, widths}>`，用组件返回的那个 lines 数组本身当 key 发布逐行可见宽度；条目随数组一起死。**「零成本传递已算好的度量结果」的好例子**
- 热路径保护：`tui.ts:57-60` `LINE_FIT_MIN_SOURCE_CODE_UNITS = 4096` / `MAX = 65536` —— 短行不走 native；长行按可见 cell 而非 code unit 裁，防止「零宽字符堆前缀」把真正该显示的后缀藏掉。且**遇到超宽行是 clamp 不是 throw**（`tui.ts:15-16`）

### 6.6 终端能力协商：DA1 哨兵 FIFO `[A]`

`packages/tui/src/terminal.ts:776-784` —— 整个能力协商的骨架：

> 终端**按顺序**处理转义序列。所以每发一个可能无人应答的探测（OSC 11 背景色、DECRQM、kitty keyboard `CSI ? u`、OSC 99 通知），就跟一个 DA1 `\x1b[c` 作哨兵。若 DA1 先回来 → 该终端不支持这个特性，**立刻判定不支持，不会无限挂起，也不会把探测字节泄漏给应用输入**。

- 实现：`#da1SentinelOwners: Da1SentinelOwner[]`（`terminal.ts:603`），判别联合 owner 类型（`:500-505`），DA1 回包时 `shift()` 出队首 owner 分派（`:1032-1080`）
- **坑：不能假设应答顺序**（`test/kitty-keyboard-da1-ordering.test.ts:9-15`）。启动发 `CSI ? u` + `CSI c`；kitty 的 `CSI ? <flags> u` 是权威答案，DA1 只是保底哨兵。**Superset / Electron 上的 xterm 会先回 DA1** —— 此时必须仍然认后到的 kitty 回复（`terminal.ts:1086-1095`）
- **分片 CSI 重组**（`:893-960`）：私有 CSI 部分匹配用于跨多次 stdin read 重组回复；有纯文本快路径（`:911-914`，注释说明每个 data 事件跑全套探测正则会把**粘贴**变慢）
- Sixel 独立探测（`tui.ts:1678-1735`）：同时发 DA1 与 XTSMGRAPHICS，双 pending 标志 + 500ms 超时兜底，非探测字节 passthrough 回输入流
- Kitty graphics：一次 `encodeKittyTransmit`，后续帧只发 `encodeKittyPlacement` 小序列（稳定 `i=` image id）；删除必须用 `d=I`，因为 **`CSI 2J`/`CSI 3J` 不会删掉 kitty 图形**（`terminal-capabilities.ts:738`）
- **ImageBudget**（`src/components/image.ts`）：全局共享预算限制同屏 live graphics 数量，超出降级为文本。**降级会改变已提交行 → 正是 §6.2 committed-prefix 审计要处理的违约来源之一**
- **DECCARA 优化器（omp 独有）**：`src/deccara.ts:1-19` —— kitty 把 VT510 DECCARA 扩展到包括背景色的所有 SGR，于是整块纯色背景面板可以用**一条矩形转义**代替「每行一整排带背景色的空格」。`detectRectangularSgrSupport()`（`terminal-capabilities.ts:346`）**只对 kitty 返回 true**，注释解释了为什么不能信 terminfo 的 `Cara` 能力
- **关 autowrap 的理由值得讲**（`tui.ts:61-68`）：多个终端写满整行后保留 "pending wrap" 标志，随后的光标移动会先换行，产生阶梯状拖影；引擎改为显式 CRLF 并在离开 paint 前恢复 autowrap

### 6.7 测试文化差异 `[A]`

- omp 有 **12 个 `issue-NNNN-repro.test.ts`**（#848 #879 #1962 #1974 #2034 #2045 #2088 #2095 #2115 #2130 #4863）——每个线上渲染 bug 固化成一个复现测试
- 一整套 stress/oracle 体系：`test/render-stress-harness.ts`（**4159 行**）、`render-stress-reducer.ts`（随机用例**缩小器**）、`render-stress-subprocess.ts`、`render-stress-oracles.test.ts`、`virtual-terminal.ts`（718 行）
- 即：**给 TUI 渲染器做 property-based testing + shrinking**。上游 pi 的 test 目录里没有对应物

---

## 7. 存疑区（`[C]`，不得用于结论）

1. **`[C]` FORK.md 的去向。** 该文件不在 `09a7c8656` 的 tree 中，且仓库是 shallow clone 导致无法查历史。可能是被删、被重命名、或只存在于旧提交。**建议**：`git fetch --unshallow` 后 `git log --all --diff-filter=D -- FORK.md`。在此之前，slide 上引用 tier 原文应注明「引自早期版本」。
2. **`[C]` stats dashboard 的绑定地址。** `packages/stats/src/server.ts:304-305` 的 `Bun.serve({ port, ... })` **未指定 `hostname`**（这一点是 `[A]`），且 `:313` CORS 为 `Access-Control-Allow-Origin: "*"`（`[A]`）。Bun 的默认 hostname 是否为 `0.0.0.0` 我未在本仓库找到确证。若是，则同 LAN 内任何人可读取完整 token/成本/项目路径/行为统计。**建议实测 `lsof -nP -iTCP:3847`。** 这是本地攻击面问题，不是上报问题。
3. **`[C]` AES-GCM 的 tagLength。** 代码未显式传参，依赖 WebCrypto 默认 128 bit。这是规范默认而非代码事实。
4. **`[C]` 生产 relay 的行为。** 代码不在本仓库，`docs/collab.md:114` 的 "content-blind" 承诺无法代码级验证。同理 `docs/collab.md:117-118` 称 relay 托管 web 客户端静态资源，我未读到该实现。
5. **`[C]` grievance 泄露面取决于模型自律。** 未审计系统提示词的约束强度。
6. **`[C]` 未逐行审计 `crates/` 全部 Rust 代码，以及 plugin/marketplace 的安装下载路径**（有 `raw.githubusercontent.com` 等约 105 处命中，属取件而非上报，未一一确认）。
7. **`[C]` omp `keys.ts` 只有 566 行 vs 上游 1401 行，推测键解析也下沉到了 native**（`crates/pi-natives/src/keys.rs` 存在，但未确认 TUI 是否实际调用）。

---

## 8. 最适合上 slide 的 5 个发现

> 按「一句话能讲清 + 有代码坐标 + 有可迁移的方法论」排序。

**1. 「你无法观测终端的滚动位置」→ 于是把猜测从系统里删掉** `[A]`
`docs/tui-core-renderer.md:26-63`。ConPTY 的滚动探测会撒谎，POSIX 根本没这个 API。旧引擎去猜「什么时候能安全重写 scrollback」，结果只是在 yank / 闪屏 / 花屏 几类 bug 之间来回换。新引擎改成 **native scrollback append-only + commit ledger**，配一个 O(1) 的尾部前缀审计（`tui.ts:864-910`），原则是 **duplication, never loss**。
→ **可迁移的方法论：当一个量无法可靠观测时，正确的做法是重构架构使其不再被需要，而不是把猜测做得更精巧。**

**2. swarm 是 tier 成本模型的活体证明** `[A]`
1541 行的 YAML DAG 多 agent 编排器（`packages/swarm-extension/`），用 `peerDependencies` 把宿主当外部依赖，入口是标准 `(pi: ExtensionAPI) => void` factory。而 `grep -rli swarm packages/coding-agent/src/` 只命中**一条注释**（`event-controller.ts:55`）。
→ **成本函数不是代码量，是「是否触碰上游文件」。1500 行 Tier-0 的同步成本是 0；3 行 Tier-2 每次 sync 都要人工重解。**

**3. 扩展点系统本身是可扩展的：capability × provider 矩阵** `[A]`
`capability/types.ts:1-7` 的原话是 "This architecture **inverts control**"。14 个 capability × 17 个 provider（`discovery/index.ts:22-38`），调用方只说 `loadCapability("skill")`，由 provider 决定从 `.omp/` / `.claude/` / `.codex/` / `.cursor/` / `.gemini/` / `AGENTS.md` 哪里读。**omp 能直接吃掉你已有的 Claude Code / Cursor 配置，零迁移。**
→ 对照：上游 pi 完全没有这一层，也没有 MCP / hook / plugin / custom-tool。

**4. 「默认开启」的是功能开关，「默认关闭」的是数据流** `[A]`
`packages/stats` 零出网（纯 `bun:sqlite` + localhost dashboard，`sync-worker` 的 sync 是本地并发解析不是网络同步）。全仓唯一指向作者服务器的用户数据通道是 Auto-QA，功能位默认 `true` 但 consent 默认 `unset`，**未同意时连本地 DB 都不写**（`report-tool-issue.ts:531`）。install-id 是纯 UUIDv4、0600 权限、全仓唯一消费者就是这条需同意的上报。
→ 但要同时讲**不足**：不支持 `DO_NOT_TRACK`，且 `docs/environment-variables.md` 完全没提这套开关。

**5. 一个性能 bug 其实是运行时正则引擎的差异** `[A]`
`markdown.ts:985-996`：Bun 的正则引擎对 marked 的块规则不做起始锚点优化，`^` 锚定的量化分支交替每次失败 `exec` 都重扫全文 → lexing 退化成 O(n²)。**800KB 消息在 Bun 下 41s，Node/V8 只要 60ms**，且跑在渲染路径上直接冻 UI。对策 `lexWindowed()` 2KB 窗口，41s → 0.7s。
→ 配套彩蛋：**韩文兼容字母的宽度由客户端终端而非 OS 决定**（`text.rs:601-604`，Ghostty→2 / Warp→1），并用 `widthConfigEpoch`（`utils.ts:36-41`）做缓存失效。

**备选（若时间充裕）**：collab 传语义事件不传像素（`client.ts:285-404` vs `tool-render/registry.ts:*`），所以 TUI guest 与 web guest 能用完全不同的渲染器消费同一份流——事件溯源在协作场景的直接收益。
