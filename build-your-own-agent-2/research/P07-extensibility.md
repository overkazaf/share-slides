# P07：扩展面取证 —— extension / skill / prompt template / theme / pi package

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处（实测命令） |
> |---|---|---|
> | 仓库 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/coding-agent/package.json:3` |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开验证。
> PPT 引用请带短 hash **`583f153`**。
>
> ⚠️ **与 R10 的差异**：R10 取证于 `4488ad5`，`ExtensionAPI` 起始行是 `:1193`、`on()` 起始行是 `:1193`。
> 本次实测 `ExtensionAPI` 仍在 `types.ts:1193`，但 `on()` 重载从 **`:1198`** 开始（中间插了三行注释分隔）。
> **钩子数量仍是 33，本次独立重数过**（命令见 §1.1），不是抄的。

---

## 0. 一句话总纲

pi 的扩展面不是"一个插件系统"，而是**四类可外挂资源 + 一套 33 钩子的宿主 API**，
四类资源共用同一条发现/信任/合并流水线（`pi-manifest.ts:10` 的 `RESOURCE_FIELDS`），
而 33 钩子里有 **11 个能真正改变流程**（其余是纯通知）。

```ts
// packages/coding-agent/src/core/pi-manifest.ts:10
const RESOURCE_FIELDS = ["extensions", "skills", "prompts", "themes"] as const;
```

**这一行就是整篇的骨架**：pi 眼里"可外挂的东西"精确地只有四种，且它们在 npm 包的 `package.json` 里
用同一个 `pi` 字段声明（`pi-manifest.ts:3-8`）。

---

## 1. ExtensionAPI 全钩子清单

### 1.1 数量实测（自己数的，命令写在这里）

```bash
$ grep -n "^\ton(" packages/coding-agent/src/core/extensions/types.ts | wc -l
33
```

（注意 `on()` 有 3 个是多行签名 —— `:1202`、`:1207`、`:1216` —— 上面那条 grep 匹配的是**行首 `on(`**，
每个多行签名只贡献 1 行，所以 33 是**签名数**而不是"行数"，已逐行核对，见下表。）

接口位置：`packages/coding-agent/src/core/extensions/types.ts:1193`（`export interface ExtensionAPI`），
`on()` 重载区间 **`:1198` – `:1239`**。整个文件 **1713 行**（`wc -l` 实测）。

### 1.2 33 个钩子逐条（钩子名 / 定义行号 / 一句话作用）

| # | 钩子 | 行号 | 作用 | 能改流程？ |
|---|---|---|---|---|
| 1 | `project_trust` | `:1198` | 项目信任决策发生时通知（有专用 `ProjectTrustHandler` 类型，不走通用 `ExtensionHandler`） | ✅ `ProjectTrustEventResult` |
| 2 | `resources_discover` | `:1199` | 扩展自己往资源池里补 skills/prompts/themes | ✅ `ResourcesDiscoverResult` |
| 3 | `session_start` | `:1200` | 会话建立/恢复完成（扩展在此恢复自己的持久化状态） | — |
| 4 | `session_info_changed` | `:1201` | 会话名等元数据变化 | — |
| 5 | `session_before_switch` | `:1202` | 切会话前，可 `cancel` | ✅ `{cancel?}` |
| 6 | `session_before_fork` | `:1206` | fork 前，可 `cancel` / `skipConversationRestore` | ✅ |
| 7 | `session_before_compact` | `:1207` | 压缩前，可 `cancel`，也可**直接交出整份 `compaction` 结果顶替 LLM 摘要** | ✅ |
| 8 | `session_compact` | `:1211` | 压缩已完成的通知 | — |
| 9 | `session_shutdown` | `:1212` | 退出前清理（sandbox 例子用它 `SandboxManager.reset()`） | — |
| 10 | `session_before_tree` | `:1213` | 树导航生成分支摘要前，可 cancel / 自带 summary / 改 customInstructions / 改 label | ✅ |
| 11 | `session_tree` | `:1214` | 树导航完成通知 | — |
| 12 | `context` | `:1215` | **改写送 LLM 的整个消息数组** | ✅ `{messages?}` |
| 13 | `before_provider_request` | `:1216` | 改 stream options（返回类型是 `unknown`） | ✅ |
| 14 | `before_provider_headers` | `:1220` | 改请求头 | — |
| 15 | `after_provider_response` | `:1221` | 拿到 provider 响应后的通知 | — |
| 16 | `before_agent_start` | `:1222` | **注入一条自定义消息 / 替换本轮 system prompt**（多扩展返回时 systemPrompt 链式叠加，见 `:1099` 注释：`If multiple extensions return this, they are chained.`） | ✅ |
| 17 | `agent_start` | `:1223` | agent 开跑 | — |
| 18 | `agent_end` | `:1224` | agent 停下（plan-mode 在此弹选择框） | — |
| 19 | `agent_settled` | `:1225` | 队列排空、真正 idle | — |
| 20 | `turn_start` | `:1226` | 单轮开始 | — |
| 21 | `turn_end` | `:1227` | 单轮结束（带 message + toolResults） | — |
| 22 | `message_start` | `:1228` | 消息开始流式 | — |
| 23 | `message_update` | `:1229` | 流式增量 | — |
| 24 | `message_end` | `:1230` | **替换定稿消息**（约束：role 必须一致，`:1093` 注释 + `runner.ts:850-857` 运行时强制） | ✅ `{message?}` |
| 25 | `tool_execution_start` | `:1231` | 工具开始执行 | — |
| 26 | `tool_execution_update` | `:1232` | 工具执行中的流式输出 | — |
| 27 | `tool_execution_end` | `:1233` | 工具执行结束 | — |
| 28 | `model_select` | `:1234` | 用户切模型 | — |
| 29 | `thinking_level_select` | `:1235` | 用户切思考档位 | — |
| 30 | `tool_call` | `:1236` | **阻断工具调用**（`{block?, reason?}`；注释明写"改参数请直接原地 mutate `event.input`"，`:1071`） | ✅ |
| 31 | `tool_result` | `:1237` | **改写工具结果**（`{content?, details?, isError?, usage?}`） | ✅ |
| 32 | `user_bash` | `:1238` | **整体接管用户 `!cmd` 的执行**（`{operations?, result?}`） | ✅ |
| 33 | `input` | `:1239` | 拦截/改写用户输入（`InputEventResult`，agent-session.ts:1145 处理 `action === "transform"`） | ✅ |

**能改流程的 = 14 个**（表中 ✅）：`project_trust`、`resources_discover`、`session_before_switch`、
`session_before_fork`、`session_before_compact`、`session_before_tree`、`context`、
`before_provider_request`、`before_agent_start`、`message_end`、`tool_call`、`tool_result`、
`user_bash`、`input`。

实测命令（把 42 行的重载区压成一行再逐签名匹配）：

```bash
$ sed -n '1198,1239p' packages/coding-agent/src/core/extensions/types.ts | tr '\n' ' ' \
    | grep -oE 'on\([^;]*\)' | grep -oE '"[a-z_]+"' | wc -l
33                       # 总签名数

$ sed -n '1198,1239p' … | tr '\n' ' ' | grep -oE 'on\([^;]*\)' | grep -c "Result"
13                       # 第二个泛型参数是 XxxResult 的
```

13 + `project_trust`（它不走通用 `ExtensionHandler`，用专属的 `ProjectTrustHandler`，
返回 `ProjectTrustEventResult`，`types.ts:538-541`）= **14**。

> **修正 R10**：R10 §7.2 说"能改变流程的 8 个钩子"，那是只数了 `types.ts:1065-1094` 那一段
> Event Results 区块里列出来的条目。完整的 Result 类型定义分布在三处（`grep -n "^export interface.*Result"` 实测）：
> `ProjectTrustEventResult` `:526`、`ResourcesDiscoverResult` `:551`、`InputEventResult` `:844`，
> 以及集中区块 `:1065`–`:1117` 的 11 个（`ContextEventResult` `:1065`、
> `BeforeProviderRequestEventResult` `:1069`、`ToolCallEventResult` `:1071`、`UserBashEventResult` `:1078`、
> `ToolResultEventResult` `:1085`、`MessageEndEventResult` `:1092`、`BeforeAgentStartEventResult` `:1097`、
> `SessionBeforeSwitchResult` `:1103`、`SessionBeforeForkResult` `:1107`、
> `SessionBeforeCompactResult` `:1112`、`SessionBeforeTreeResult` `:1117`）。3 + 11 = **14**。
> 上 PPT 建议用 **"33 个钩子，14 个能改流程"**。

### 1.3 除了 `on()`，ExtensionAPI 还给了什么

`types.ts:1245-1431`，按注释分区块（区块标题就是代码里的 `// ===` 注释）：

| 区块 | 方法 | 行号 |
|---|---|---|
| Tool Registration | `registerTool(tool)` | `:1246` |
| Command / Shortcut / Flag | `registerCommand` `:1255`、`registerShortcut` `:1258`、`registerFlag` `:1267`、`getFlag` `:1277` | — |
| Message Rendering | `registerMessageRenderer` `:1284`、`registerMarkdownTransformer` `:1287`、`registerEntryRenderer` `:1290` | — |
| Actions | `sendMessage` `:1297`、`sendUserMessage` `:1306`、`appendEntry` `:1312` | — |
| Session Metadata | `setSessionName` `:1319`、`getSessionName` `:1322`、`setLabel` `:1325`、`exec` `:1328` | — |
| Tools & Commands 查询 | `getActiveTools` `:1331`、`getAllTools` `:1334`、`setActiveTools` `:1337`、`getCommands` `:1340` | — |
| Model | `setModel` `:1347`、`getThinkingLevel` `:1350`、`setThinkingLevel` `:1353` | — |
| Provider | `registerProvider` `:1411/:1412`（两个重载）、`unregisterProvider` `:1427` | — |
| 通信 | `events: EventBus` `:1430` | — |

`registerProvider` 的注释里有一句极值钱的产品语义（`:1367-1370`）：

> During initial extension load this call is **queued** and applied once the runner has bound its context.
> After that it takes effect **immediately**, so it is safe to call from command handlers or event callbacks
> **without requiring a `/reload`**。

代码印证：加载期是入队（`loader.ts:212-217` 的 `pendingProviderRegistrations.push`），
bind 之后被替换成直连 ModelRegistry（`types.ts:1600-1602` 注释 + `agent-session.ts:2439-2441`）。

### 1.4 钩子拿到的 `ctx`：这才是"表达力上限"的真身

`ExtensionContext`（`types.ts:307-347`）给了 15 个字段/方法，其中 `ctx.ui` 是
`ExtensionUIContext`（`types.ts:131-282`），**共 25 个方法名**（实测）：

```bash
$ awk 'NR>=131 && NR<=275' packages/coding-agent/src/core/extensions/types.ts \
  | grep -oE "^\t[a-zA-Z]+(<[^>]*>)?\(" | sed 's/[<(].*//;s/^\t//' | sort -u | wc -l
25
```

清单：`select` `confirm` `input` `notify` `onTerminalInput` `setStatus` `setWorkingMessage`
`setWorkingVisible` `setWorkingIndicator` `setHiddenThinkingLabel` `setWidget` `setFooter`
`setHeader` `setTitle` `custom` `pasteToEditor` `setEditorText` `getEditorText` `editor`
`addAutocompleteProvider` `setEditorComponent` `getEditorComponent` `getAllThemes` `getTheme`
`setTheme`（另有 `setToolsExpanded`/`getToolsExpanded` `:278-281` 和只读的 `theme` 属性 `:265`）。

**上 PPT 的点**：`setFooter` `:183`、`setHeader` `:190`、`setEditorComponent` `:259` 三个方法允许
扩展**整体替换 pi 的页脚、页眉和输入编辑器**。`:238-256` 的 JSDoc 里直接给了一个 `VimEditor extends CustomEditor`
的完整例子 —— 也就是说"给 pi 加 vim 模式"官方认定为 Tier-0 级别的事。

---

## 2. 扩展的加载机制

### 2.1 从哪些目录发现

两条独立的发现路径，最终汇合到同一个 `loadExtensions(paths)`。

**路径 A：`extensions/loader.ts` 的 `discoverAndLoadExtensions()`（`:665-713`）** —— SDK 直连入口：

| 顺序 | 目录 | 行号 |
|---|---|---|
| 1 | `<cwd>/.pi/extensions/` | `:687-688` |
| 2 | `<agentDir>/extensions/`（默认 `~/.pi/agent/extensions/`，`config.ts:515-521`） | `:691-692` |
| 3 | 显式配置的路径（目录→再发现，文件→直接加） | `:695-710` |

**路径 B：产品路径（`pi` CLI 实际走的）** —— `ResourceLoader.reload()`
（`core/resource-loader.ts:387-546`）先问 `PackageManager.resolve()`（`package-manager.ts:885`）
拿到四类资源的候选清单，再交给 `loadExtensionsCached`（`resource-loader.ts:558`）。

`PackageManager.addAutoDiscoveredResources()`（`package-manager.ts:2278-2442`）是真正的目录表：

```ts
// package-manager.ts:2311-2322
const userDirs    = { extensions: join(globalBaseDir, "extensions"), skills: …, prompts: …, themes: … };
const projectDirs = { extensions: join(projectBaseDir, "extensions"), skills: …, prompts: …, themes: … };
```

### 2.2 目录内的发现规则（`loader.ts:618-660`，注释即文档）

```
1. Direct files: extensions/*.ts 或 *.js        → 加载
2. Subdirectory with index: */index.ts|index.js → 加载
3. Subdirectory with package.json 的 "pi" 字段  → 加载它声明的路径
No recursion beyond one level. Complex packages must use package.json manifest.
```

`resolveExtensionEntries(dir)`（`:586-616`）优先读 `package.json` 的 `pi.extensions`，
其次退回 `index.ts` / `index.js`。

产品路径上还额外做了 **`.gitignore`/`.ignore`/`.fdignore` 过滤**
（`package-manager.ts:560-612` 的 `collectAutoExtensionEntries`，用 `ignore` 包；
`IGNORE_FILE_NAMES` 定义在 `package-manager.ts:203`），并跳过 `node_modules` 和 `.` 开头的条目（`:577-578`）。

### 2.3 什么时候加载：**两趟，中间夹一道信任闸**

这是整个扩展面最关键的安全设计，在 `resource-loader.ts:387-402`：

```ts
async reload(options?: ResourceLoaderReloadOptions): Promise<void> {
    resetTimings("extensions");
    if (this.loaded) clearExtensionCache();                                   // :390-392
    let preTrustExtensions: LoadExtensionsResult | undefined;
    if (options?.resolveProjectTrust) {
        preTrustExtensions = await this.loadProjectTrustExtensions();          // :396  ← 第一趟
        const projectTrusted = await options.resolveProjectTrust({ extensionsResult: preTrustExtensions });
        this.settingsManager.setProjectTrusted(projectTrusted);               // :398
    }
    await this.settingsManager.reload();                                      // :402  ← 第二趟按新信任态重跑
```

第一趟干了什么（`:379-385`）：

```ts
async loadProjectTrustExtensions(): Promise<LoadExtensionsResult> {
    // Force untrusted project settings for the bootstrap pass. This keeps project-local
    // extensions/packages out while still loading user/global and temporary CLI extensions.
    this.settingsManager.setProjectTrusted(false);
    …
}
```

→ **"要不要信任这个项目"这个问题本身，是由一个只加载了 user/global 扩展的 pi 来问的。**
项目里的 `.pi/extensions/*.ts` 在用户点头之前一行都不会跑。

信任闸的落点在 `package-manager.ts:2343-2394`：

| 资源 | 是否受 project trust 门禁 | 行号 |
|---|---|---|
| project `extensions` | ✅ 受 | `:2343-2351` |
| project `.pi/skills` | ✅ 受 | `:2353-2360` |
| project 祖先链 `.agents/skills` | ✅ 受（`projectTrusted ? … : []`） | `:2325-2327` |
| project `prompts` | ✅ 受 | `:2379-2386` |
| project `themes` | ✅ 受 | `:2387-2393` |
| user 侧四类（`~/.pi/agent/*`） | ❌ 不受，无条件加载 | `:2396-2441` |

另有一道更硬的：访问 project 作用域的**包存储**直接抛异常（`package-manager.ts:1714-1718`）：

```ts
private assertProjectTrustedForScope(scope: SourceScope): void {
    if (scope === "project" && !this.settingsManager.isProjectTrusted()) {
        throw new Error("Project is not trusted; refusing to access project package storage");
    }
}
```

### 2.4 TypeScript 怎么在运行时执行：**jiti，无编译步骤，无沙箱**

`packages/coding-agent/src/core/extensions/loader.ts:412-440`：

```ts
const jiti = createJiti(import.meta.url, {
    moduleCache: false,
    ...(isBunBinary
        ? { virtualModules: VIRTUAL_MODULES, tryNative: false }            // :425
        : isTypeScriptSourceRuntime
            ? { virtualModules: VIRTUAL_MODULES, tsconfigPaths: true }     // :427
            : { alias: getAliases() }),                                    // :428
});
const module = await jiti.import(extensionPath, { default: true });        // :431
const factory = module as ExtensionFactory;                                // :432
if (typeof factory !== "function") return undefined;                       // :433-435
```

- 依赖：`jiti` **2.7.0**（`packages/coding-agent/package.json:59`，pinned）
- **不预编译、不产出 dist**：`.ts` 源文件被 jiti 就地转译并 import
- 三种宿主形态各有一套模块解析策略（`:424-428`）：
  1. **Bun 单文件二进制**（`isBunBinary`）→ `virtualModules` + `tryNative: false`
  2. **TS 源码直跑**（`isTypeScriptSourceRuntime`，判定见 `:78`：非 bun 二进制且 `loader.ts` 后缀是 `.ts`）→ `virtualModules` + `tsconfigPaths`
  3. **构建后的 Node**（默认分支）→ `alias` 指向各包的 `dist/*.js`（`getAliases()` `:86-142`）
- `VIRTUAL_MODULES`（`:50-74`）是一张 **22 条的白名单**（`sed -n '50,74p' … | grep -c ":"` 实测），把 `typebox` / `@earendil-works/pi-{ai,tui,agent-core,coding-agent}`
  等静态 import 进来的模块暴露给扩展。注释 `:18-20` 说明原因："These MUST be static so Bun bundles them into the compiled binary."
- 白名单里同时保留了 `@mariozechner/*` 旧 scope（`:67-73`）—— **改名后的兼容层，扩展生态不用改一行**
- **无沙箱**：`factory(api)` 直接 `await` 调用（`loader.ts:484`），扩展跑在 pi 主进程里，
  能 `import "node:child_process"`（sandbox 例子 `sandbox/index.ts:44` 就这么干的）

### 2.5 扩展的错误隔离：不 crash 宿主

`runner.ts:801-833` 的 `emit()`：每个 handler 单独 `try/catch`，异常转成 `ExtensionError`
经 `emitError()`（`:563`）广播给监听器，循环继续。

```ts
} catch (err) {                                             // :819
    this.emitError({ extensionPath: ext.path, event: event.type, error: message, stack });
}
```

`message_end` 还额外做了语义校验（`:850-857`）：返回的消息 role 变了 → 记错误、**丢弃这次替换**、继续下一个扩展。

### 2.6 扩展工具**覆盖**内置工具（sandbox 例子的底层机制）

`agent-session.ts:2471-2521`：先把内置工具灌进 `definitionRegistry`，再用扩展工具**同名覆盖**：

```ts
const definitionRegistry = new Map(… this._baseToolDefinitions …);      // :2471-2481  内置打底
for (const tool of allCustomTools) {
    definitionRegistry.set(tool.definition.name, {…});                   // :2482-2487  扩展覆盖
}
…
const toolRegistry = new Map(wrappedBuiltInTools.map(t => [t.name, t])); // :2517
for (const tool of wrappedExtensionTools) toolRegistry.set(tool.name, tool);  // :2518-2520
```

→ 扩展 `registerTool({ name: "bash", … })` 就能整体替掉内置 bash。这是 sandbox 例子的全部魔法。

---

## 3. skill / prompt template / theme 各自的机制

### 3.1 Skill：加载 = 只读元数据；触发 = 两条路

**加载目录**（`core/skills.ts:431-432` + `package-manager.ts:2353-2426`）：

| 来源 | 位置 |
|---|---|
| `~/.pi/agent/skills` | `skills.ts:431` |
| `<cwd>/.pi/skills`（需 trust） | `skills.ts:432`、`package-manager.ts:2354-2360` |
| `~/.agents/skills` | `package-manager.ts:2323` + `:2420-2426` |
| cwd 祖先链上的 `.agents/skills`（需 trust，到 git root 截断） | `package-manager.ts:2325-2327`、`:435-453` |
| npm/git 包内的 `skills/` 或 `pi.skills` | `pi-manifest.ts:10`、`package-manager.ts:2313` |
| CLI `--skill <path>` / settings 里的 `skills[]` | `skills.ts:466` |

**目录内遍历规则**（`skills.ts:164-166` 注释，代码即文档）：

```
- if a directory contains SKILL.md, treat it as a skill root and do not recurse further
- otherwise, load direct .md children in the root
- recurse into subdirectories to find SKILL.md
```

冲突策略：first-wins + `collision` 诊断（`skills.ts:397-427`）。

**`Skill` 结构里没有 `content` 字段**（`skills.ts:74-81`）：

```ts
export interface Skill {
    name: string; description: string; filePath: string;
    baseDir: string; sourceInfo: SourceInfo; disableModelInvocation: boolean;
}
```

→ 正文永不进内存，更不进 system prompt。注入的只有三个 XML 字段
（`skills.ts:350-355`：`<name>` / `<description>` / `<location>`），
且整段的注入条件是 **read 工具在场**（`system-prompt.ts:155-156`：`if (hasRead && skills.length > 0)`）。

**触发的两条路**：

1. **模型自主**：system prompt 里那句 `"Use the read tool to load a skill's file when the task matches its description."`（`skills.ts:344`）→ 模型自己发 `read` 调用。
2. **用户显式**：`/skill:<name> [args]` → `AgentSession._expandSkillCommand`（`agent-session.ts:1301`），
   此刻才 `readFileSync(skill.filePath)`。

`disable-model-invocation: true`（frontmatter，`skills.ts:70`、`:316`）会把该 skill 从
`formatSkillsForPrompt` 的可见列表里剔除（`skills.ts:336`）—— **但 `/skill:` 显式调用仍然可用**。
这就是"只给人用、不给模型用"的 skill。

**`description` 硬性必填**（`skills.ts:305-307`）：缺了直接返回 `{skill: null}`，整个 skill 被丢弃。
`name` 缺省取父目录名（`skills.ts:296`）。

### 3.2 Prompt template：最简单的一类，纯字符串替换

文件：`core/prompt-templates.ts`（**285 行**）。

- **发现**：`~/.pi/agent/prompts/` → `<cwd>/.pi/prompts/`（需 trust）→ 显式路径。
  `loadPromptTemplates` `:194-263`，两个默认目录在 `:202-203`、`:236-237`。
- **扫描规则**：`loadTemplatesFromDir` `:138-175`，**非递归**，只收直接子级的 `.md`（`:163`），
  symlink 要 `statSync` 确认指向文件（`:152-161`，坏 symlink 静默跳过）。
- **名字 = 文件名去掉 `.md`**（`:109`）。描述取 frontmatter `description`，
  缺省则取正文第一行非空内容并截断到 60 字符（`:112-120`）。
- **触发**：`expandPromptTemplate(text, templates)` `:269-284`，正则 `^\/([^\s]+)(?:\s+([\s\S]*))?$`（`:272`），
  纯本地字符串替换，**不经过 LLM**。
- **参数语法**（`substituteArgs` `:70-102`，注释 `:57-68` 列全）：
  `$1 $2 …` / `$@` / `$ARGUMENTS` / `${N:-default}` / `${@:-default}` / `${@:N}` / `${@:N:L}`（bash 风格切片）。
  参数用 `parseCommandArgs` `:24-55` 做 bash 风格引号解析。
  注释 `:66-68` 明确：**替换只做一层，参数值里的 `$1`/`$@` 不会被递归展开**（防注入）。

**与 skill 的调用顺序**（`agent-session.ts:1151-1156`）：

```ts
// Expand skill commands (/skill:name args) and prompt templates (/template args)
let expandedText = currentText;
if (expandPromptTemplates) {
    expandedText = this._expandSkillCommand(expandedText);            // :1154  skill 先
    expandedText = expandPromptTemplate(expandedText, [...this.promptTemplates]);  // :1155  template 后
}
```

→ **`/skill:x` 优先于同名 prompt template**。

### 3.3 Theme：JSON + TypeBox 校验 + 热重载

- 内置只有 **2 个**：`dark` / `light`（`theme.ts:453-464`，从 `getThemesDir()` 下的
  `dark.json` / `light.json` 读盘，**不是硬编码在 TS 里**）
- 用户自定义：`~/.pi/agent/themes/*.json`（`config.ts:524-526` 的 `getCustomThemesDir()`；
  扫描在 `theme.ts:504-527`，只收 `.json`，解析失败静默忽略并交给 resource-loader 报诊断，`:521-524` 注释）
- 项目/包/CLI 来的主题走统一资源流水线，最后由 `setRegisteredThemes(themes)`
  （`theme.ts:838-843`）灌进 `registeredThemes` Map（`theme.ts:836`）。
  调用点 3 处：`cli/startup-ui.ts:78`、`interactive-mode.ts:527`（启动）、`:1764` / `:5471`（reload / 换主题）
- **文件格式校验用 TypeBox**：`validateThemeJson.Check(json)`（`theme.ts:538`），
  失败时把 `required` 错误单独归类成 "Missing required color tokens" 列表（`:544-559`），
  并补一句 `"See the built-in themes (dark.json, light.json) for reference values."`（`:564`）
- schema 文件 `src/modes/interactive/theme/theme-schema.json` 对外发布，
  docs 里给的 `$schema` URL 直指 GitHub raw（`docs/themes.md:57`）→ 用户写主题有 IDE 补全
- **主题名不能含 `/`**（`theme.ts:529-535`），因为 `/` 被 `settings.json` 的
  "light/dark 自动切换" 语法占用了
- **热重载**：`theme.ts:910-938` watch `${watchedThemeName}.json`，改文件即时 `loadThemeFromPath` 重灌
- 文件类型过滤统一在 `package-manager.ts:196-201`：

```ts
const FILE_PATTERNS: Record<ResourceType, RegExp> = {
    extensions: /\.(ts|js)$/, skills: /\.md$/, prompts: /\.md$/, themes: /\.json$/,
};
```

### 3.4 pi package：npm / git / local 三种来源

`PackageManager`（`core/package-manager.ts`，**2625 行**）：

- 来源类型 `ParsedSource = NpmSource | GitSource | LocalSource`（`:142`）
- 声明位置：`settings.json` 的 `packages[]`，global 与 project 各一份，
  **project 先入以便 cwd 资源在冲突时胜出**（`:890-896` 注释 + 代码）
- 一个包通过 `package.json` 的 `pi` 字段声明它提供哪几类资源（`pi-manifest.ts:16-33`），
  没有 `pi` 字段则按目录约定 `extensions/` `skills/` `prompts/` `themes/` 收（`:2312-2322` 同名子目录）
- npm 安装刻意关掉 peer 解析（`:1758-1779`），注释 `:1760-1763` 解释：
  > Extension packages run inside pi and resolve pi APIs through loader aliases/virtual modules.
  > Disable peer dependency resolution … so package managers do not install or solve host-provided
  > `@earendil-works/pi-*` peers. Stale auto-installed pi peers can otherwise block updates.

  → bun 用 `--omit=peer`、pnpm 用三个 `--config.*=false`、npm 用 `--legacy-peer-deps`
- 包管理器本身可配（`getNpmCommand()` `:1720-1730`，读 `settingsManager.getNpmCommand()`）

---

## 4. `examples/extensions/` 实测与三个样本精读

### 4.1 数量实测

```bash
$ ls packages/coding-agent/examples/extensions/ | wc -l
79                    # 含 README.md

$ ls packages/coding-agent/examples/extensions/*.ts | wc -l
69                    # 顶层单文件扩展

$ ls -d packages/coding-agent/examples/extensions/*/ | wc -l
9                     # 目录型扩展

$ find packages/coding-agent/examples/extensions -name "*.ts" -not -path "*/node_modules/*" | wc -l
85                    # 全部 .ts 文件（含目录内的辅助模块）
```

**79 = 69 个单文件 + 9 个目录 + 1 个 README.md。**

9 个目录型：`custom-provider-anthropic` `custom-provider-gitlab-duo` `doom-overlay`
`dynamic-resources` `gondolin` `plan-mode` `sandbox` `subagent` `with-deps`。

其中 5 个被登记进 monorepo workspace（根 `package.json:5-11`）：
`with-deps`、`custom-provider-anthropic`、`custom-provider-gitlab-duo`、`sandbox`、`gondolin`
—— 因为它们有自己的 `dependencies`，需要真装 node_modules。

配套文档 `packages/coding-agent/docs/extensions.md` **2984 行**（`wc -l` 实测），
是整个 docs/ 目录最长的一篇（第二名 `rpc.md` 1576 行）。**文档长度本身就是产品重心的证据。**

pi 自己也吃狗粮：`pi-mono/.pi/` 下有 `extensions/`（4 个 `.ts`：`import-repro.ts` `prompt-url-widget.ts`
`redraws.ts` `tps.ts`）、`prompts/`（5 个 `.md`：`cl` `is` `pr` `sa` `wr`）、`skills/`（1 个 `add-llm-provider.md`）。

### 4.2 样本一：`plan-mode/`（390 + 168 = 558 行）—— 用 7 个钩子重建 Claude Code 的 Plan Mode

**它到底改了什么**：把"只读探索 → 出计划 → 逐步执行并打勾"这一整套模式，在**零 core 改动**下做出来。

`index.ts` 用到的 API（逐条对应行号）：

| 手段 | 行号 | 干了什么 |
|---|---|---|
| `registerFlag("plan")` | `:53` | 新增 CLI 开关 `--plan` |
| `registerCommand("plan")` / `("todos")` | `:141` / `:146` | 两个斜杠命令 |
| `registerShortcut(Key.ctrlAlt("p"))` | `:158` | Ctrl+Alt+P 切换 |
| `pi.setActiveTools(…)` | `:108` / `:112` | **进入 plan 模式时把 `edit`/`write` 从活跃工具集里摘掉**（`PLAN_MODE_DISABLED_TOOLS` `:24`），退出时用 `toolsBeforePlanMode` 精确还原（`:104-114`） |
| `on("tool_call")` | `:164-174` | bash 命令过白名单，不在名单里 `{block: true, reason}` |
| `on("before_agent_start")` | `:201-247` | 注入一条 `display: false` 的自定义消息，内容是 plan 模式的行为约束 + "把计划写成 `Plan:` 编号列表" |
| `on("context")` | `:177-198` | **退出 plan 模式时，把历史里所有 `[PLAN MODE ACTIVE]` 消息从送 LLM 的数组里过滤掉** |
| `on("turn_end")` | `:250-259` | 扫 assistant 文本里的 `[DONE:n]` 标记，勾掉对应步骤 |
| `on("agent_end")` | `:262-337` | 抽取计划步骤 → `ctx.ui.select()` 弹三选一（执行/留在 plan/精修）→ `sendMessage(..., {triggerTurn: true, deliverAs: "followUp"})` 驱动下一轮 |
| `ctx.ui.setStatus` / `setWidget` | `:63-83` | 页脚显示 `📋 3/7`，编辑器上方显示 ☑/☐ 待办列表 |
| `pi.appendEntry("plan-mode", state)` | `:117-122` | 状态持久化进 session（`custom` 条目，不进 LLM context） |
| `on("session_start")` | `:340-389` | resume 时从 session 条目恢复状态，并**只扫描最后一个 `plan-mode-execute` 标记之后的消息**重建勾选状态（`:360-383`，注释解释了为什么不能全扫） |

**这就是表达力上限的样本 A**：一个模式化功能（工具集切换 + 提示注入 + 上下文清洗 + 进度追踪 +
UI 组件 + 崩溃后恢复）完全在 userland 完成，代码 558 行。
Claude Code 里这是 core feature；在 pi 里它是 `examples/` 下的一个目录。

### 4.3 样本二：`sandbox/`（321 行）—— 替换内置 bash 工具，加 OS 级沙箱

**它到底改了什么**：让 `bash` 工具和用户的 `!cmd` 都跑在 macOS `sandbox-exec` / Linux `bubblewrap` 里。

关键三段：

```ts
// sandbox/index.ts:214-227  —— 用同名 registerTool 覆盖内置 bash
const localBash = createBashTool(localCwd);                      // :209 复用内置实现
pi.registerTool({
    ...localBash,
    label: "bash (sandboxed)",                                    // :216
    async execute(id, params, signal, onUpdate, _ctx) {
        if (!sandboxEnabled || !sandboxInitialized) return localBash.execute(id, params, signal, onUpdate);
        const sandboxedBash = createBashTool(localCwd, { operations: createSandboxedBashOps() });  // :222-224
        return sandboxedBash.execute(id, params, signal, onUpdate);
    },
});

// :229-232  —— 用户的 !cmd 走另一条路，用 user_bash 钩子接管
pi.on("user_bash", () => {
    if (!sandboxEnabled || !sandboxInitialized) return;
    return { operations: createSandboxedBashOps() };
});
```

`createSandboxedBashOps()`（`:132-199`）实现的是 pi 导出的 `BashOperations` 接口：
`SandboxManager.wrapWithSandbox(command)`（`:139`）包一层，再 `spawn("bash", ["-c", wrapped], {detached: true})`，
自己处理 timeout（`process.kill(-pid, "SIGKILL")` 杀整个进程组，`:151-162`）和 abort（`:172-182`）。

生命周期挂在 `session_start`（`:234-285`，含平台检查 `:251-256`、初始化失败降级 `:281-284`）
和 `session_shutdown`（`:287-295`，`SandboxManager.reset()`）。

配置合并策略写在文件头注释（`:12-14`）：`~/.pi/agent/extensions/sandbox.json`（global）
与 `<cwd>/.pi/sandbox.json`（project）深合并，project 胜（`loadConfig` `:79-103`）。

文件头 `:8-10` 的注释是产品态度的直接表述：

> Note: this example **intentionally overrides the built-in `bash` tool to show how built-in tools can be replaced**.
> Alternatively, you could sandbox `bash` via `tool_call` input mutation without replacing the tool.

**样本 B 说明的上限**：连内置工具本身都能被同名替换，且官方把这当作示范用法而不是 hack。

### 4.4 样本三：`custom-provider-anthropic/`（610 行）—— 一个扩展 = 一个完整 LLM Provider + OAuth 登录流

**它到底改了什么**：注册一个全新 provider `custom-anthropic`，包含自定义 API 类型、
自己的流式实现、两个模型定义、以及**完整的 OAuth 授权码流程**。

```ts
// custom-provider-anthropic/index.ts:574-609
export default function (pi: ExtensionAPI) {
    pi.registerProvider("custom-anthropic", {
        baseUrl: "https://api.anthropic.com",
        apiKey: "$CUSTOM_ANTHROPIC_API_KEY",          // :577  环境变量插值语法
        api: "custom-anthropic-api",                   // :578  自定义 API 标识
        models: [ { id: "claude-opus-4-5",  … contextWindow: 200000, maxTokens: 64000 },   // :581-589
                  { id: "claude-sonnet-4-5", … } ],                                         // :590-598
        oauth: {                                       // :601-606
            name: "Custom Anthropic (Claude Pro/Max)",
            login: loginAnthropic,                     // :78  完整 PKCE 授权码流
            refreshToken: refreshAnthropicToken,
            getApiKey: (cred) => cred.access,
        },
        streamSimple: streamCustomAnthropic,           // :608  自己接管整条流式管线
    });
}
```

OAuth 端点是硬编码在扩展里的（`:54-56`）：
`https://claude.ai/oauth/authorize` / `https://console.anthropic.com/v1/oauth/token` /
`.../oauth/code/callback`。`streamCustomAnthropic` 里还自己拼 beta header（`:377`）。

包声明（`custom-provider-anthropic/package.json`）：

```json
"pi": { "extensions": ["./index.ts"] },
"dependencies": { "@anthropic-ai/sdk": "0.52.0" }
```

**样本 C 说明的上限**：`/login <provider>` 这条产品级流程对扩展开放。
"接入公司内部 SSO 大模型网关"这种在多数 agent 里必须改 core 的需求，在 pi 里是一个 610 行的目录。

### 4.5 荣誉提名（不精读，但值得一句话）

- `doom-overlay/`（538 行，含 `doom-engine.ts` / `doom-component.ts` / `wad-finder.ts` / `doom-keys.ts`）
  —— 在 TUI overlay 里跑 DOOM。它的存在唯一目的就是证明 `ctx.ui.custom()` 是真正的图形层出口。
- `subagent/`（1141 行）—— 用 `spawn(pi --mode json -p --no-session …)` 起独立子进程做子代理（R10 §8 已详述）。
- `overlay-qa-tests.ts`（1450 行，全仓最长的单文件示例）、`tic-tac-toe.ts`（1008 行）、
  `space-invaders.ts`（560 行）、`snake.ts`（343 行）—— TUI 能力的压力测试。

---

## 5. 「core 最小、能力外挂」的可验证落点 —— 与反例

### 5.1 六个正面落点（每条都能 grep 出来）

| # | 落点 | 证据 |
|---|---|---|
| 1 | **显式的"不做清单"** | `packages/coding-agent/README.md:495`：`**No MCP.** Build CLI tools with READMEs …, or build an extension that adds MCP support.`；`:497`：`**No sub-agents.** … build your own with extensions, or install a package that does it your way.` |
| 2 | **同一句话在 usage 文档里被复述成完整清单** | `docs/usage.md:301`：`It intentionally does not include built-in MCP, sub-agents, permission popups, plan mode, to-dos, or background bash. You can build or install those workflows as extensions or packages, or use external tools such as containers and tmux.` —— **6 项刻意不做，其中 plan mode / to-dos / permission popups 三项在 examples 里各有现成实现** |
| 3 | **内置工具只有 7 个，默认只激活 4 个** | `core/tools/index.ts:83-84` 的 `ToolName` 联合与 `allToolNames`；`agent-session.ts:2592-2594` 的 `defaultActiveToolNames = ["read","bash","edit","write"]` |
| 4 | **四类资源用同一个 manifest 字段声明** | `core/pi-manifest.ts:10` 的 `RESOURCE_FIELDS`，只有 4 项。加第五类资源需要改 core —— 这个边界是被刻意画死的 |
| 5 | **扩展工具能同名覆盖内置工具** | `agent-session.ts:2482-2487`、`:2518-2520` |
| 6 | **文档权重**：`docs/extensions.md` 2984 行 > 任何其它单篇文档 | `wc -l packages/coding-agent/docs/*.md`；第二名 `rpc.md` 1576 行，`sdk.md` 1186 行 |

补一条软证据：`ExtensionAPI` 里 `registerProvider` 的注释专门保证"**不需要 `/reload`**"（`types.ts:1367-1370`），
说明作者把"扩展的开发者体验"当成一等公民在设计，而不是把扩展当二等公民。

### 5.2 反例：core 里确实塞了本该外挂的东西

**反例 A：`grep` / `find` / `ls` 三个工具实现了但默认不启用。**

```ts
// core/tools/index.ts:83-84
export type ToolName = "read" | "bash" | "edit" | "write" | "grep" | "find" | "ls";
```
```ts
// agent-session.ts:2592-2594
const defaultActiveToolNames = this._baseToolsOverride ? Object.keys(this._baseToolsOverride)
                                                       : ["read", "bash", "edit", "write"];
```

`createToolDefinition` 是一个 7 分支 switch（`tools/index.ts:96-115`）。
三个默认关闭的工具占着 core 的代码、类型联合和 switch 分支 ——
**按 pi 自己的标准，它们完全够格做成一个 examples 扩展**。这是 core 没有跟着自己的哲学收敛的地方。

**反例 B：HTML 导出住在 core 里，746 行。**

```bash
$ wc -l packages/coding-agent/src/core/export-html/*.ts
258 ansi-to-html.ts   316 index.ts   172 tool-renderer.ts   →  746
```

导出 HTML 是典型的 "读 session、渲染成另一种格式" 的旁路功能，
`ExtensionContext.sessionManager`（只读，`types.ts:317`）+ `registerCommand` 完全够用。
它在 core 里的唯一理由是历史与便利。

**反例 C：22 个内置斜杠命令，其中若干可外挂。**

```bash
$ grep -c 'name: "' packages/coding-agent/src/core/slash-commands.ts
22
```

清单在 `core/slash-commands.ts:20-41`。其中至少 `/export`（`:23`）、`/import`（`:24`）、
`/share`（`:25`，"Share session as a secret GitHub gist"）、`/copy`（`:26`）、`/changelog`（`:29`）
都是**纯旁路**功能 —— `/share` 甚至硬编码了 GitHub gist 这一个后端。

**反例 D（最戏剧化）：core 的 TUI 组件目录里躺着一个 164 行的彩蛋，含一张 32×32 的十六进制人像。**

`packages/coding-agent/src/modes/interactive/components/daxnuts.ts:1-4`：

```
/**
 * POWERED BY DAXNUTS - Easter egg for OpenCode + Kimi K2.5
 * A heartfelt tribute to dax (@thdxr) for providing free Kimi K2.5 access via OpenCode.
 */
```

`:11` 是一条长达 6KB 的 `DAX_HEX` 字符串（`// 32x32 RGB image of dax, hex encoded (3 bytes per pixel)`）。
按 pi 自己的标准，这**应该**是一个 examples 扩展 —— `ctx.ui.custom()` 渲染图片的能力
`doom-overlay/` 已经证明绰绰有余。

> **上 PPT 的诚实说法**：pi 的哲学是真的（正面证据 6 条，都可 grep），
> 但**"core 最小"是方向不是事实**。反例集中在两类：
> (a) 历史遗留的旁路功能（HTML 导出、gist 分享、彩蛋），
> (b) 已实现但默认关闭的工具（grep/find/ls）。
> 二者都不影响主循环，所以没人有动力去外挂化 —— 这本身就是"最小核心"最常见的失守方式。

---

## 6. 与 oh-my-pi `FORK.md` tier 模型的呼应（**本节是判断，不是取证**）

### 6.1 tier 模型回顾（引自 `R08-ohmypi.md:64-68`，原始出处 oh-my-pi `FORK.md`）

| Tier | 定义 | 同步成本 |
|---|---|---|
| **Tier 0** | out-of-core：hooks / extensions / 磁盘上的 tools·commands·skills·rules·context files。**不碰任何上游文件，上游同步物理上不可能冲突** | 0 |
| **Tier 1** | 往 core 的某个 list/union 里加**一行** | 极低，冲突平凡 |
| **Tier 2** | 深度 core / Rust patch：turn loop、prompt 模板结构、TUI 内部、provider 内部 | 高，需 seam marker + 账本 + 漂移测试 |

FORK.md 的核心主张：**"Push everything you can down to Tier 0."**
以及 R08 提炼的评价标准（`R08-ohmypi.md:494`）：
**"扩展点的价值 = 它把多少 Tier-2 需求降级为 Tier-0。"**

### 6.2 【判断】用这把尺子量 pi 的扩展面

下表左列是"在一个没有扩展面的 agent 里、这件事落在哪个 tier"，右列是"在 pi 里它落在哪个 tier"。
**tier 归属是我的判断**，右列的"pi 侧机制"是取证过的事实。

| 需求 | 无扩展面时 | pi 里的 tier | pi 侧机制（已取证） |
|---|---|---|---|
| Plan mode（只读探索 + 计划执行） | **Tier 2**（改 turn loop + 工具集 + prompt 结构） | **Tier 0** | `setActiveTools` + `tool_call` + `before_agent_start` + `context`（`plan-mode/index.ts`） |
| 权限门禁 / 危险操作确认 | **Tier 2**（在工具执行前插逻辑） | **Tier 0** | `tool_call` 返回 `{block, reason}`（`types.ts:1236`、`examples/permission-gate.ts`） |
| OS 级 sandbox | **Tier 2**（改 bash 执行器） | **Tier 0** | `registerTool` 同名覆盖 + `user_bash`（`sandbox/index.ts:214-232`） |
| 子代理 | **Tier 2**（加工具 + 嵌套 loop） | **Tier 0** | `registerTool` + `spawn` 子进程（`subagent/index.ts`） |
| 接入企业 SSO 模型网关 | **Tier 2**（改 provider 层 + auth 层） | **Tier 0** | `registerProvider({oauth, streamSimple})`（`custom-provider-anthropic/index.ts:574-609`） |
| 自定义压缩策略 | **Tier 2**（改 compaction） | **Tier 0** | `session_before_compact` 可直接返回整份 `compaction`（`types.ts:1207`、`examples/custom-compaction.ts`） |
| 改整个消息流（脱敏 / 注入 / 裁剪） | **Tier 2** | **Tier 0** | `context` 返回 `{messages}`（`types.ts:1215`） |
| 替换输入编辑器（vim 模式） | **Tier 2**（TUI 内部） | **Tier 0** | `ctx.ui.setEditorComponent(factory)`（`types.ts:259`，JSDoc 给了完整 `VimEditor` 例子） |
| 换页眉/页脚/主题/状态栏 | **Tier 2**（TUI 内部） | **Tier 0** | `setHeader` `:190` / `setFooter` `:183` / theme JSON |
| 新增一类**资源**（比如 "agents/" 目录） | Tier 2 | **仍是 Tier 1/2** | `pi-manifest.ts:10` 的 `RESOURCE_FIELDS` 只有 4 项 —— 这是硬边界 |
| 改 turn loop 的判停语义 | Tier 2 | **仍是 Tier 2** | `agent-loop.ts` 无对应钩子；`shouldStopAfterTurn` 是 SDK 层 config，不是 extension 钩子 |
| 改 session JSONL 的 entry 类型 | Tier 2 | **仍是 Tier 2** | `SessionEntry` 是封闭联合（`session-manager.ts:144-153`）；扩展只能用 `custom`/`custom_message` 两个逃生口 |

**【判断】结论**：pi 的扩展面把**产品级功能层**（模式、权限、沙箱、子代理、provider、压缩策略、TUI 外观）
几乎整体降级到了 Tier 0；但**内核语义层**（turn loop 判停、session 数据模型、资源种类）仍是 Tier 2。

这条分界线画得很清楚，而且和 FORK.md 的 Tier 1 定义精确吻合 ——
FORK.md 说 Tier 1 只有 4 个坐标（`BUILTIN_TOOLS`/`HIDDEN_TOOLS`、hook 事件 union、rpc-types、system-prompt 的 data 对象），
**pi 侧对应的正是 `ToolName`（`tools/index.ts:83`）、`ExtensionEvent`（`types.ts:1034` 起）、`RESOURCE_FIELDS`（`pi-manifest.ts:10`）**
—— 三个都是"往联合里加一行"的形态。

**【判断】反过来的批评**：oh-my-pi 之所以仍需要大量 Tier 2，恰恰是因为它要改的东西
（turn loop、prompt 模板结构、TUI 内部、`crates/*`）**正好落在 pi 扩展面的盲区里**。
pi 的扩展面覆盖的是"功能"，不是"语义"。这不是缺陷，是设计选择：
语义留在 core，才能保证 33 个钩子的行为契约是稳定的。

---

## 最适合上 PPT 的 5 条硬事实

1. **`ExtensionAPI` 有 33 个事件钩子（`types.ts:1193` 接口起，`:1198`–`:1239` 是 `on()` 重载区），
   其中 14 个带 Result 类型、能真正改变流程**（`context` 改整个消息数组、`tool_call` 阻断执行、
   `message_end` 替换定稿消息、`user_bash` 接管执行、`session_before_compact` 顶替 LLM 摘要……）。
   命令：`grep -c "^\ton(" packages/coding-agent/src/core/extensions/types.ts` → `33`。

2. **扩展是 jiti 2.7.0 就地转译的 TypeScript，不编译、不打包、无沙箱，跑在 pi 主进程里**
   （`extensions/loader.ts:420-432`；jiti 版本见 `package.json:59`）。
   三种宿主形态各一套模块解析：Bun 二进制用 `virtualModules`、TS 源码直跑用 `virtualModules + tsconfigPaths`、
   构建后 Node 用 dist `alias`（`loader.ts:424-428`）。22 条虚拟模块白名单里连旧 scope `@mariozechner/*` 都保留着（`:67-73`）。

3. **加载分两趟，中间夹一道信任闸：第一趟强制 `setProjectTrusted(false)` 只加载 user/global 扩展，
   由这个"干净的 pi"去问用户要不要信任本项目；点头后第二趟才加载 `.pi/` 下的东西**
   （`resource-loader.ts:379-402`）。project 侧的 extensions / skills / prompts / themes 四类全部受这道闸控制
   （`package-manager.ts:2343-2394`），访问 project 包存储直接抛异常（`:1714-1718`）。

4. **可外挂的资源精确地只有 4 类，写死在一行里**：
   `const RESOURCE_FIELDS = ["extensions", "skills", "prompts", "themes"] as const;`（`core/pi-manifest.ts:10`）。
   四类共用同一条发现→信任→合并流水线，也共用同一个 npm 包 manifest 字段（`package.json` 的 `pi`）。
   文件类型过滤同样只有一张表：`extensions: /\.(ts|js)$/, skills: /\.md$/, prompts: /\.md$/, themes: /\.json$/`
   （`package-manager.ts:196-201`）。

5. **`examples/extensions/` 下 79 个条目（69 个单文件 + 9 个目录 + 1 个 README，实测 85 个 `.ts`），
   配套 `docs/extensions.md` 2984 行 —— 全仓最长的单篇文档。**
   三个样本证明了表达力上限：`plan-mode/`（558 行，7 个钩子重建 Plan Mode）、
   `sandbox/`（321 行，用同名 `registerTool` 覆盖内置 bash + `user_bash` 接管 `!cmd`）、
   `custom-provider-anthropic/`（610 行，一个扩展 = 完整 provider + PKCE OAuth 登录流 + 自定义流式实现）。
   **反例也要一并讲**：`grep`/`find`/`ls` 三个工具实现在 core 却默认不启用（`tools/index.ts:83` vs `agent-session.ts:2592-2594`）、
   746 行的 HTML 导出住在 `core/export-html/`、22 个内置斜杠命令里 `/share` 硬编码了 GitHub gist、
   以及 `core` 的 TUI 组件目录里躺着一个 164 行、含 6KB 十六进制人像的彩蛋（`components/daxnuts.ts`）。
