# R02 — 实现原理：架构与 agent 内核（0xAF-Re / re-agent）

> 取证对象：`/Users/overkazaf/playground/research/re-agent`（Go 1.22，`module github.com/overkazaf/re-agent`）
> 证据等级：**[A]** 本地读源码验证 / **[B]** README 等文档声明 / **[C]** 推断
> 所有 `file:line` 均相对仓库根目录。

---

## 0. 规模盘点 [A]

| 指标 | 值 | 依据 |
|---|---|---|
| 非测试 + 测试 Go 总行数 | **24,229** | `find . -name '*.go' \| xargs wc -l` |
| Go 文件数 | 83 | 同上 |
| `internal/` 包数 | **16** | `internal/{app,assets,auth,buildinfo,config,core,knowledge,mcp,plan,providers,security,skills,tools,types,ui,util,workflow}`（17 目录，含 buildinfo） |
| 外部依赖 | **1 个直接依赖**（`golang.org/x/term`，间接 `x/sys`） | `go.mod:4-6` |
| 内建 tool 数 | **24** | `internal/tools/registry.go:23-50` |
| slash 命令分支数 | **49** | `grep -c 'case "/' internal/app/commands.go` |
| 内置 skill 目录数 | **33**（编译进二进制） | `internal/assets/embedded/skills/`，`internal/assets/assets.go:17-18` |
| provider 后端种类 | **5** | `internal/types/types.go:13-19` |
| agent 主循环文件 | `internal/core/agentloop.go` = **640 行** | `wc -l` |
| 主循环函数 `Run` | **241 行**（`agentloop.go:265-505`），其中 `for` 循环体 **167 行**（332-498） | [A] |

**结论素材**：整个 agent 只靠标准库 + 一个 term 包，没有 LangChain / SDK。24k 行里真正的"内核"是 640 行的 `agentloop.go`。

---

## 1. 包职责总览 [A]

每一行都对应该包主文件的 package doc 注释（作者自己写的，不是推断）。

| 包 | 一句话职责 | 出处 |
|---|---|---|
| `internal/app` | CLI/REPL 宿主：参数、命令、编辑器、队列、workflow 编排；`State` 就是一次会话的全部可变状态 | `internal/app/app.go:28-47` |
| `internal/core` | **agent runtime**：append-only 会话日志、上下文预算、tool loop、operator shell 逃逸 | `internal/core/session.go:1-3` |
| `internal/plan` | 追踪 provider 正在推进的任务清单，两个来源（CLI 事件流 + 宿主 `update_plan` 工具）汇入同一个 Tracker | `internal/plan/plan.go:1-8` |
| `internal/providers` | 把 Anthropic Messages / OpenAI Responses / OpenAI-compatible Chat / tmux 里的本地 CLI / 离线 mock 统统适配成一个 `Complete()` | `internal/providers/providers.go:1-4` |
| `internal/workflow` | 高层 RE 执行模式：specialist 是 prompt 契约，caveman 是宿主级 planner → 隔离 executor 委派 | `internal/workflow/workflow.go:1-4` |
| `internal/tools` | 本地工具注册表：文件访问、命令执行、CTF/逆向助手、宿主任务清单工具；统一走审批闸和输出预算 | `internal/tools/registry.go:1-4` |
| `internal/security` | 决定一次调用是否放行：命令安全模式（`policy.go`）+ tier/mode 审批闸（`approval.go`） | `internal/security/policy.go:1-3` |
| `internal/skills` | 从 `skills/<name>/SKILL.md` 加载项目本地逆向工作流，缺失则回落到二进制内嵌副本 | `internal/skills/skills.go:1-3` |
| `internal/knowledge` | 检索已导入的逆向语料库，并把命中打包成面向模型的 context block | `internal/knowledge/knowledge.go:1-3` |
| `internal/mcp` | 极简 MCP 客户端（stdio + JSON-RPC 2.0 换行分隔），外加把 server 工具变成原生 agent 工具的适配器 | `internal/mcp/client.go:1-5`, `internal/mcp/tools.go:3-5` |
| `internal/ui` | banner、run 渲染、审批提示、表格、帮助、补全 —— live pane 之外的一切打印 | `internal/ui/ui.go:3-5` |
| `internal/types` | 全层共享数据模型（消息/工具/provider/plan/policy），**刻意不依赖树内任何其他包** | `internal/types/types.go:1-4` |
| `internal/auth` | 为 HTTP provider 找凭据（env 文件、本地 secret store），并报告每个 provider（含 CLI 型）此刻是否真的可用 | `internal/auth/auth.go:1-4` |
| `internal/config` | 加载 `agent.config.json`（覆盖内建默认），以及跨重启保存 `/theme`、`/flow` 的 UI 偏好 | `internal/config/config.go:1-3` |
| `internal/util` | 小型共享助手：参数强转、路径包含检查、截断、中断哨兵 | `internal/util/util.go:1-3` |
| `internal/assets` | 用 `//go:embed` 把 prompts 和 skills 编进二进制，同时解析磁盘上的项目根（同名文件覆盖内嵌副本，改 prompt 不用重编译） | `internal/assets/assets.go:1-5,17-18` |

**分层箭头**（[C] 由 import 关系推断，但 `types` 的"零内部依赖"是 [A]）：
`types` ← 所有包；`core` ← `plan/security/types/util`；`app` 是唯一的编排层。

---

## 2. Agent 主循环 [A]

### 2.1 循环骨架（`internal/core/agentloop.go:331-498`）

```go
turns := 0
for ; turns < maxTurns; turns++ {
    if ctx.Err() != nil {                        // 停止条件 1：被打断
        l.noteInterrupted()
        return finish(turns, true), nil
    }
    emit(LoopEvent{Type: "turn", Turn: turns + 1, Provider: providerName})

    view := CompactHistory(viewMessages, CompactionOptions{BudgetTokens: budgetFor(provider.Config())})
    response, err := provider.Complete(types.ProviderInput{ /* System/Messages/Tools/Ctx/OnProgress */ })
    if err != nil { /* aborted ? finish(interrupted) : return err */ }

    l.messages = append(l.messages, assistant)   // 落盘 + 内存同步
    if len(response.ToolCalls) == 0 {            // 停止条件 2：没有 tool call → 收工
        return finish(turns+1, false), nil
    }
    for _, call := range response.ToolCalls { /* 审批 → 执行 → pushToolResult */ }
    if interrupted { l.noteInterrupted(); return finish(turns+1, true), nil }  // 停止条件 3
}
_ = l.options.Session.AppendEvent(map[string]any{"type": "max_turns_reached", "maxTurns": maxTurns})
```

### 2.2 与"经典 6 行 while 循环"的结构对比

经典写法：
```python
while True:
    resp = llm(messages, tools)
    messages.append(resp)
    if not resp.tool_calls: break
    for c in resp.tool_calls:
        messages.append(run_tool(c))
```

re-agent 是**同一个骨架**，只是每一步都被"生产化"包了一层：

| 经典行 | re-agent 对应 | 增加的东西 | 行号 |
|---|---|---|---|
| `while True` | `for ; turns < maxTurns; turns++` | 有界回合 + 每回合先查 `ctx.Err()` | 332-336 |
| `llm(messages, tools)` | `provider.Complete(...)` | 先跑 `CompactHistory` 做预算裁剪；发/收各 emit 一条 `wire` 事件（模型名、endpoint、耗时、token） | 341-403 |
| `messages.append(resp)` | append + `Session.AppendMessage` | 内存与 JSONL **同步双写** | 405-419 |
| `if not tool_calls: break` | `return finish(turns+1, false)` | 返回结构化 `RunResult`（provider/role/turns/usage/interrupted） | 421-423 |
| `run_tool(c)` | `security.RequestApproval` → `tool.Execute` | 审批闸插在执行**之前**；中断时仍为每个 call 补一条 error 结果 | 428-493 |
| （无） | `max_turns_reached` 事件 | 触顶也写进 transcript | 500 |

### 2.3 关键数字与不变量

- **最大回合数默认 8**：`internal/config/config.go:23` `MaxTurns: 8`；可被 `RunOptions.MaxTurns` 覆盖（`agentloop.go:316-319`）。
- **三个停止条件**：ctx 取消（332-336 / 379-394）、无 tool call（421-423）、tool 阶段被打断（494-497）；第四个出口是回合触顶（500-504）。
- **"每个 tool call 必须有结果"不变量**（`agentloop.go:425-427` 注释）：
  ```go
  // Every tool call must end up with a result, including on interrupt:
  // providers reject a history where an assistant tool call dangles.
  ```
  中断时也要 push 一条 `"Interrupted by operator before this tool ran."`（431-433），工具找不到时 push `"Tool not found: "`（441-443）。
- **工具分发**是线性查表 `findTool(turnTools, call.Name)`（`agentloop.go:439`, 定义 556-563），**逐个串行执行**，不并行。
- **中断后的对齐补丁** `noteInterrupted`（206-221）：插一条 `[interrupted by operator]` assistant 消息，保住严格 chat API 的 user/assistant 交替。

### 2.4 流式在哪里发生

主循环本身不流式；流式通过**回调下沉到 provider**：
- `types.ProviderInput.OnProgress func(ProviderProgress)`（`internal/types/types.go:420`），6 种 kind：`status | thinking | text | tool | usage | plan`（`types.go:402`）。
- 主循环把 progress 转成 `LoopEvent{Type:"progress"}` 上抛，同时截获 `kind=="plan"` 直接喂给 plan tracker（`agentloop.go:372-377`）。
- REPL 的 `onEvent` 把这些映射成 live pane 的相位：thinking / writing / tool / turn N（`internal/app/repl.go:268-344`）。

### 2.5 扩展点清单（**8 个回调 hook**）[A]

| Hook | 签名位置 | 用途 |
|---|---|---|
| `RunOptions.OnEvent` | `agentloop.go:248` | 8 种 `LoopEvent`：`turn/wire/compaction/progress/plan/reply/tool_start/tool_end`（`agentloop.go:24`） |
| `ProviderInput.OnProgress` | `types.go:420` | provider 内部流式进度 |
| `ToolContext.OnPlan` | `types.go:310` | `update_plan` 工具回写任务清单 |
| `ToolContext.Confirm` | `types.go:308` | 交互式审批 |
| `workflowRunOptions.OnPhase` | `internal/app/workflow_run.go:14` | planner/executor 阶段切换通知 UI |
| `ShellRunOptions.OnChunk` | `internal/core/shell.go:54` | shell 输出实时回显 |
| `LivePaneOptions.OnFrame` | `internal/app/repl.go:233` | 每帧重绘钩子 |
| `Provider.Complete` | `types.go:434-438` | 后端接入点本身 |

---

## 3. Planner / Executor 双模型拆分 [A]

### 3.1 两个模型怎么接线

配置层就是两个字段（`internal/types/types.go:98-109`）：

```go
type AgentConfig struct {
    PlannerProvider    string `json:"plannerProvider"`
    ExecutorProvider   string `json:"executorProvider"`
    ResearcherProvider string `json:"researcherProvider,omitempty"`
    KnowledgeProvider  string `json:"knowledgeProvider,omitempty"`
    DefaultRole        AgentRole
    MaxTurns           int
    ...
}
```

默认值：**planner = `codex`（Codex CLI，tmux），executor = `claude`（Claude Code CLI，tmux）**，researcher = codex（`internal/config/config.go:20-23`）。

### 3.2 路由在哪（`agentloop.go:530-543`）

```go
func (l *AgentLoop) route(role types.AgentRole, prompt string) routedRole {
    switch role {
    case types.RolePlanner:   return routedRole{l.options.Config.PlannerProvider, types.RolePlanner}
    case types.RoleExecutor:  return routedRole{l.options.Config.ExecutorProvider, types.RoleExecutor}
    case types.RoleResearcher:return routedRole{l.researcherProvider(), types.RoleResearcher}
    }
    if isExecutionPrompt(strings.ToLower(prompt)) {          // 关键词路由
        return routedRole{l.options.Config.ExecutorProvider, types.RoleExecutor}
    }
    return routedRole{l.options.Config.PlannerProvider, types.RolePlanner}
}
```

`role == auto` 时靠**关键词表**决定去 planner 还是 executor —— 表里同时有中英文（`agentloop.go:618-632`）：
`"run ", "execute", "shell", "grep", "strings", "objdump", ... , "执行", "运行", "跑一下", "读取", "列出", "查看文件", "分析 ./"`。
[C] 这是最朴素的意图分类：**没有用模型做 router，就是 substring 匹配**，成本 0、可解释、可预测。

角色 prompt 拼接在 `systemPrompt()`（`agentloop.go:512-523`）：全局 system prompt + 角色 prompt 两段拼接，角色为 `auto` 时不追加。

### 3.3 planner 产出什么

**注意：`internal/plan` 不是"planner 的输出结构"，而是 UI 任务清单追踪器。** 真正的 planner 产出是**自由文本**，按约定格式（`internal/workflow/delegate.go:44-55`）：

```
Output format:
PLAN:
- 3 to 7 short steps for the planner-facing strategy.

EXECUTOR_PACKET:
```text
Objective: collect local evidence about <paths>.
Scope: workspace-local, read-only inspection and summarization.
Steps:
1. ...
Return: ...
```
```

而 `internal/plan/plan.go` 追踪的是 `types.PlanStep`（`types.go:218-226`）：`Text / Status(pending|in_progress|completed) / ID / StartedAt / CompletedAt`。它的三个设计点全部 [A]：
- **来源不可信**：`sanitize()` 剥 ANSI、剥控制字符、单步截断 200 字、最多 64 步，超出补一行 `"… N more steps not shown"`，避免"截断后看起来像做完了"（`plan.go:86-109`）。
- **时间戳只有 tracker 知道**：源每次重发全量清单且不带计时，`carryTimings()` 按 ID（无则按文本）匹配旧步骤续接 `StartedAt/CompletedAt`（`plan.go:127-175`）。
- **去重**：`sameSteps` 只比 text/status/ID，计时不参与比较，没变就返回 nil，跳过重绘与落盘（`plan.go:38-63,177-189`）。

### 3.4 交接点（`internal/app/workflow_run.go:27-62`）

```go
plannerResult, err := state.Loop.Run(workflow.DelegatedPlannerPrompt(prompt), core.RunOptions{
    Role: types.RolePlanner, ProviderName: planner,
    Tools: workflow.DelegatedPlannerTools(state.Tools),          // 只给 1 个工具
})
...
executorResult, err := state.Loop.Run(
    workflow.DelegatedExecutorPrompt(prompt, lastAssistantText(plannerResult.Messages)),
    core.RunOptions{
        Role: types.RoleExecutor, ProviderName: executor,
        Isolated:     true,                                       // 只发本 run 的消息
        SystemPrompt: workflow.DelegatedExecutorSystemPrompt(),   // 换一套 system prompt
        Tools:        workflow.DelegatedExecutorTools(state.Tools),// 只给 14 个只读工具
        FreshSession: true,                                       // 让 CLI provider 不 resume
    })
```

交接的载荷 = **planner 最后一条 assistant 文本里被正则/标记提取出的 EXECUTOR_PACKET**，`ExtractExecutorPacket`（`delegate.go:102-137`）容忍四种写法（`executor_packet:` / `executor packet:` / 无冒号），优先取 ``` 围栏内内容，否则截到下一个全大写标题为止。

合并结果（`workflow_run.go:64-73`）：provider 字段变成 `"codex->claude"`，turns 相加，usage 相加，任一阶段被打断则整体 interrupted。

### 3.5 能不能跨厂商 —— 能，且是运行时热切

| 入口 | 位置 | 效果 |
|---|---|---|
| `/planner <provider>` | `internal/app/commands.go:327-333` | 校验 provider 存在后直接改 `state.Config.PlannerProvider` |
| `/executor <provider>` | `commands.go:334-340` | 同上改 `ExecutorProvider` |
| `/researcher <provider>` | `commands.go:341-347` | 同上 |
| `/role planner\|executor\|researcher\|auto` | `commands.go:307-314` | 改角色，并清空 pin 的 provider |
| `/agent <provider>` | `commands.go:315-326` | pin 死一个 provider（绕过路由，也绕过 caveman 委派） |
| `--planner/--executor/--researcher` | `internal/app/app.go:60-68` | 启动期覆盖 |

默认配置里 planner=Codex CLI、executor=Claude Code CLI，就已经是**跨厂商**了。`/planner deepseek` + `/executor claude-api` 这类组合完全合法，因为循环只认 `types.Provider` 接口的三个方法（`types.go:434-438`）。

---

## 4. caveman 模式 [A]

### 4.1 它是什么

四种 workflow 之一（`internal/workflow/workflow.go:15-22`）。文档级定位（[A]，代码注释）：

```go
// Package workflow defines high-level RE execution modes. Specialist mode is a
// prompt contract for purpose-built routes; caveman mode is a host-level
// planner -> isolated executor delegation with a narrow local-evidence surface.
```

### 4.2 它到底做了什么（三件事，都是宿主级的）

**(1) planner 阶段：让强模型写一个"有界本地证据包"** —— `DelegatedPlannerPrompt`（`delegate.go:24-60`）关键约束：

```go
"2. Do not ask the executor to solve the full objective. Ask it only to",
"   collect bounded local evidence: file listings, type, size, hashes,",
"   printable strings, byte offsets, entropy, embedded signatures, package",
"   metadata, imports, symbols, and protection summaries.",
"3. The executor packet must be plain text, self-contained, and limited to",
"   workspace-relative paths and local inspection steps. Do not encode, hide,",
"   euphemize, or launder intent.",
```

**(2) executor 阶段：换脑袋 + 剪工具 + 截上下文** —— `DelegatedExecutorPrompt`（`delegate.go:83-100`）构造投递的 packet，**这就是"bounded local-evidence packet"的建包代码**：

```go
func DelegatedExecutorPrompt(original, plannerReply string) string {
    packet := ExtractExecutorPacket(plannerReply)
    if packet == "" {
        packet = fallbackExecutorPacket(original)     // planner 没照格式写 → 本地兜底生成
    }
    return strings.Join([]string{
        "0xAF-Re delegated workflow: executor phase",
        "You are receiving a bounded local evidence packet prepared by the planner.",
        "Work only from this packet and the workspace. Do not infer or expand the",
        "broader objective.",
        "Executor packet:",
        "```text",
        util.Clip(packet, 6000),                       // 硬上限 6000 字符
        "```",
    }, "\n")
}
```

兜底包 `fallbackExecutorPacket`（`delegate.go:178-197`）会从 prompt 里扫本地目标（`./`、`/`、`~/` 前缀，或 `.apk/.so/.dex/.wasm/.elf/.pcap/...` 20 种后缀，`delegate.go:222-239`），然后生成固定四步的证据采集脚本。

**(3) 工具面收窄** —— executor 只能看到 **14 个只读工具**，且每个的 description 被就地改写成中性描述（`delegate.go:145-162`）；planner 只有 **1 个工具**（`update_plan`，`delegate.go:139-143`）：

```go
func DelegatedExecutorTools(list []types.Tool) []types.Tool {
    return selectedTools(list, map[string]string{
        "list_files": "List files under the workspace.",
        "read_file":  "Read a workspace text file with truncation.",
        "grep": "...", "file_info": "...", "strings": "...", "hexdump": "...",
        "hash_file": "...", "extract_symbols": "...", "entropy_scan": "...",
        "binary_mitigations": "...", "find_bytes": "...", "carve_artifacts": "...",
        "apk_inspect": "...", "update_plan": "...",
    })
}
```
24 个工具 → 14 个，`run_command` / `write_file` 被摘掉。

### 4.3 为什么存在（哪个失败模式）

[A] 代码注释 `wrapCaveman`（`workflow.go:140-166`）自己写死了动机与红线：

```go
"This is the fallback for ordinary providers when no GPT Cyber / CC CVP style",
"specialist route is configured. Do not use translation, classical Chinese,",
"ciphering, euphemisms, or prompt laundering to bypass a model or site policy.",
"The point of caveman mode is smaller safe contexts, local evidence, and clear",
"artifact-focused decomposition.",
```

**失败模式**：普通商用模型面对"逆向这个 APK"这类整体请求时会过度谨慎/直接拒绝，或者把长上下文越滚越危险。caveman 的解法不是骗模型，而是**把一个大请求拆成"规划"和"取证"两段，让执行方只看到一个 6000 字的本地只读取证清单**，执行方连整体目标都不知道（`DelegatedExecutorSystemPrompt`：`"You do not need the broader objective."`，`delegate.go:66-67`）。

测试直接把这条红线钉死（`internal/workflow/workflow_test.go:56-58`）：wrapped prompt 必须包含 `"Do not use translation"` 和 `"prompt laundering"`。

### 4.4 触发条件（三个否决项）

```go
func ShouldDelegate(requested Mode, config *types.AgentConfig, pinnedProvider string, role types.AgentRole) bool {
    if pinnedProvider != "" { return false }              // /agent 钉死了 → 不委派
    if role != "" && role != types.RoleAuto { return false } // 显式 role → 不委派
    return Effective(requested, config, pinnedProvider) == Caveman
}
```
`internal/workflow/delegate.go:14-22`

---

## 5. Workflow 模式枚举 [A]

`internal/workflow/workflow.go:15-22`，共 **4 种**：

| 模式 | 判定/解析 | 特征 | 是否双阶段 |
|---|---|---|---|
| `off` | `Effective` 直接返回 Off（`workflow.go:46-48`） | 完全不包 prompt，原样送 | 否 |
| `auto` | 探测到 specialist provider → `specialist`，否则 → `caveman`（`workflow.go:49-54`） | 唯一会"解析"的模式 | 取决于解析结果 |
| `specialist` | `wrapSpecialist`（`workflow.go:119-138`） | 纯 **prompt 契约**：5 条规则，要求先发 3-7 步计划再动手，优先内建 skill | 否（单 provider） |
| `caveman` | `wrapCaveman` + `ShouldDelegate` 委派 | **宿主级双阶段**：planner(1 工具) → 隔离 executor(14 只读工具) | 是 |

**specialist 探测规则**（`workflow.go:79-92`）：把 provider 名 + Label + Model + CLICommand + CLIArgs 拼成一串小写，命中 `gpt-cyber / gpt cyber / cyber / cvp / claude-cvp / cc-cvp` 任一 marker 即算 specialist。

**有没有状态机？** 没有显式 FSM 类型。[A] 状态转移体现在两处：
1. `Effective(requested) → effective` 是一次**纯函数解析**（auto 是唯一有分支的输入）。
2. 运行时的阶段推进写死在 `runDelegatedWorkflow` 里，是**两次顺序的 `Loop.Run` 调用**（`workflow_run.go:34-57`），planner 被打断就直接 return，不进 executor（`workflow_run.go:41-43`）。

状态串可以用 `Status()` 一行打出来（`workflow.go:94-105`）：
```
workflow=auto effective=caveman specialist=not configured runner=delegated-planner-executor
```

---

## 6. 上下文管理 [A]

### 6.1 两级 compaction

**机械压缩（自动，每回合跑）** —— `internal/core/compaction.go`，文件头注释写明"两遍，先便宜的"：

```go
//  1. elide the bodies of old tool results (the bulk of an RE session)
//  2. drop whole oldest exchanges, replacing them with one compaction marker
//
// Both preserve the invariant strict chat APIs care about: an assistant message
// with tool calls is never separated from its tool results.
```
`compaction.go:5-13`

| 参数 | 默认 | 位置 |
|---|---|---|
| `DefaultContextBudgetTokens` | **48,000**（"塞得进 deepseek-chat 的 64k"） | `agentloop.go:16-18` |
| `defaultKeepRecent` | 8 条最近消息不动 | `compaction.go:43` |
| `defaultElideOver` | tool result 超 400 字符才是省略候选 | `compaction.go:44` |
| per-provider 覆盖 | `ProviderConfig.ContextBudgetTokens` | `types.go:87-89`，`agentloop.go:236-241` |

关键实现细节：
- **keep-recent 是偏好不是下限**：预算连最近 8 条都装不下时，会继续吃进去，但 `lastExchangeStart` 是硬底（`compaction.go:134-157,183-192`）。
- **marker 自身的 token 是实测不是估算**（`compaction.go:140-149`），注释：`otherwise the budget is quietly overshot`。
- **token 估算无 tokenizer**：latin 4 字符/token、CJK 1.5 字符/token，每条消息 +4 信封开销（`compaction.go:47-83`）。

**模型压缩（手动 `/compact`）** —— `AgentLoop.Compact`（`agentloop.go:138-184`）：把整段 session 丢给模型总结，**摧毁式**替换为一条 `[session summary — earlier turns compacted]` 消息，注释直言 `Destructive by design: the detail lives on in the JSONL`。总结 prompt 见 `compaction.go:238-249`（要求覆盖：目标与已确认事实、已跑过的命令与结论、当前假设与死路、已恢复的 flag/key/路径）。

### 6.2 会话持久化 = JSONL

`internal/core/session.go:47-96`。每行一个 `SessionEntry{Type, Timestamp, Data}`，三种 type：`session`（元信息）/ `message` / `event`。写入用 `O_APPEND|O_CREATE|O_WRONLY` + mutex（`session.go:87-95`），文件名 `<UTC时间戳>-<name>.jsonl`。

**恢复路径的两个硬核处理**：
- `readEntries` 对解析失败的行**静默跳过**：`// A truncated last line is expected when a session was killed mid-write.`（`session.go:299-303`）。
- `repair()`（`session.go:196-238`）双向修剪悬空引用：**有 call 无 result → 摘掉 call；有 result 无 call → 丢掉 result**。注释：`Providers reject a dangling call *and* an orphan result`。

`--resume` / `/sessions` 的选择器靠 `Summary`（`session.go:26-37`），并会把 `[operator shell]` / `[context compacted]` 开头的伪 prompt 排除出"第一条提示"（`session.go:263-266`）。

### 6.3 Token 计量与遥测

- `types.TokenUsage`：input / output / **thinking** / cacheRead / cacheWrite / costUsd（`types.go:346-353`），带 `Merge`（流式覆盖语义）与 `Add`（跨回合累加）两种合并（`types.go:358-389`）。
- 各厂商字段名归一在 `internal/providers/usage.go`：Anthropic 用 `input_tokens/cache_read_input_tokens/cache_creation_input_tokens`，Responses 用 `output_tokens_details.reasoning_tokens` 取 thinking。
- 每回合发/收各一条 `wire` 事件，含 model、endpoint、消息数、token、工具数、毫秒、是否 OK、tool call 数、文本字符数（`agentloop.go:26-41`, 358-401）。
- `DescribeEndpoint`（`agentloop.go:567-581`）把"这一回合到底发去哪"渲染成最短诚实形式：HTTP 给 URL，tmux CLI 给 `tmux:codex`。

### 6.4 工具输出预算（第三道闸）

`internal/tools/output.go:3-7`：
```
// Reverse engineering commands are exactly the kind that emit megabytes
// (`objdump -d`, `strings` on a fat binary), and a raw dump into the transcript
// costs the whole context window. Anything over budget is spilled to a file
// next to the session log; the model gets head+tail plus the path.
```
默认 `MaxToolOutputChars = 24_000`（`internal/app/app.go:134`），超限按 **head 60% / tail 40%** 切（`output.go:27-45`），全文落到 `<sessionDir>/artifacts/`。

---

## 7. 并发、中断与"turn 中途转向" [A]

### 7.1 取消的三层传播

```
^C / SIGTERM
  └─ repl.go:370-386  signal goroutine → cancel()      （CompareAndSwap 保证只触发一次）
      └─ ctx 传进 RunOptions.Ctx → agentloop.go:332,364,429,465,490
          ├─ provider：input.Context() → http.NewRequestWithContext (providers/http.go:50)
          │            / exec.CommandContext + runCtx (clitmux.go:280)
          └─ tool：callContext.Ctx = ctx (agentloop.go:452-453)
                    → tools/process.go:70 context.WithCancel
```

最狠的一处在 `internal/tools/process.go:78-86`：
```go
// A process group lets a killed `bash -c` take its children with it.
cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
cmd.Cancel = func() error {
    if cmd.Process != nil { _ = syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL) }
    return nil
}
```
[A] 负号 PID = 杀整个进程组，避免 `bash -c "objdump ... | grep ..."` 留下孤儿。

中断被当成**结果而非错误**（`agentloop.go:389-394`）：
```go
// An interrupt is an outcome, not a failure: keep the transcript
// usable so the next prompt (or a resumed session) still lines up.
```

### 7.2 turn 运行中的键盘输入（mid-turn steering）

这是最有意思的一段。`liveInputController`（`internal/app/repl.go:484-740`）：

- turn 一开始就把 stdin 切成 **raw mode**（`term.MakeRaw`，`repl.go:573-584`），起一个 goroutine 用 `unix.Poll(fds, 100)` 轮询（`repl.go:613-620`）—— 用 poll 而不是阻塞读，才能在 100ms 粒度上响应 `done` 通道退出。
- 逐字符解析：`^C`→`cancel()`、`Enter`→提交、`^U` 清行、`^W` 删词、`127/8` 退格（`repl.go:629-671`）。
- **回车提交的内容有两条路**（`repl.go:689-714`）：
  - 以 `/` 开头 → 立刻执行「turn 内白名单命令」；
  - 否则 → 进 `taskQueue`，turn 结束后 `drainQueue` 依次跑（`repl.go:468-482`）。

**turn 内允许的命令只有 5 个**（`repl.go:716-733`）：
```go
case "/queue":   ...
case "/tasks":   ...
case "/think":   ...
case "/model":   ...
case "/version": ...
default: return fmt.Errorf("during a turn use /queue, /tasks, /think, /model, or /version; other commands run at the normal prompt")
```

### 7.3 `/model` 为什么能中途生效

因为 provider 持有的是 **`*types.ProviderConfig` 指针**（`baseProvider{config *types.ProviderConfig}`，`providers/http.go:24-30`），而每次 `Complete` 都在请求体里现读 `p.config.Model`（如 `http.go:112`、`http.go:371`）。`/model` 走 `config.SetProviderModel(provider, model)` 直接改这个共享结构体（`config.go:370-400`），所以**下一回合的请求就用新模型**。UI 也如实告知边界：

```go
emitNotice(pane, strings.Join(notices, " · ")+"; applies to the next provider turn")
```
`internal/app/commands.go:431`

`SetProviderModel` 对 CLI 型 provider 还要改命令行参数，四种策略（`config.go:376-399`）：`{model}` 占位符 → 已有 `--model` flag → `claude --model` 前插 → `codex exec --model` 在 `exec` 后插；都不匹配则只记录并提示。

`/think expand` 更简单：只改 `state.ThinkDisplay` 并调 `pane.SetThinkDisplay`（`commands.go:564-591`），是**纯 UI 显示切换**，不影响模型请求 —— [A] 这点值得在 slide 上澄清，避免误解成"中途调推理强度"。真正调推理强度的是 `/effort`（`commands.go:62`）。

### 7.4 其他并发点

| 位置 | 并发原语 | 用途 |
|---|---|---|
| `repl.go:33-34` | `chan []auth.Status` + goroutine | 开机动画期间并发探测凭据，"开机屏幕几乎不花额外时间" |
| `clitmux.go:395-412` | goroutine + `time.NewTicker(100ms)` | tail CLI 子进程 stdout 文件（**不是 pipe**），边跑边出 JSONL 事件 |
| `clitmux.go:387-424` | `sync.WaitGroup` + `sync.Once` | stop 时保证最后一次 drain，不丢尾部事件 |
| `process.go:118-135` | `WaitGroup` + `sync.Mutex emit` | stdout/stderr 双 goroutine 泵出，回调处**统一串行化**（注释：两个 goroutine 写 map 是 crash 不是 race） |
| `mcp/client.go:94,202` | `chan json.RawMessage` + pending map | JSON-RPC 请求/响应配对 |
| `plan/plan.go:25-28` | `sync.Mutex` | Tracker 快照 |
| `session.go:50,87` | `sync.Mutex` | JSONL 追加写 |

---

## 8. Providers 层 [A]

### 8.1 5 个后端，一个接口

```go
type Provider interface {
    Name() string
    Config() *ProviderConfig
    Complete(input ProviderInput) (ProviderResponse, error)
}
```
`internal/types/types.go:434-438` —— **整个抽象就是这 3 个方法**。

工厂（`internal/providers/providers.go:14-30`）：

| Kind | 实现 | 说明 |
|---|---|---|
| `anthropic` | `AnthropicProvider` | Messages API，`http.go:93-124` |
| `openai-responses` | `OpenAIResponsesProvider` | `/responses`，`http.go:239-268` |
| `openai-chat` | `OpenAIChatProvider` | `/chat/completions`，任何 OpenAI 兼容端点（DeepSeek/GLM），`http.go:361-387` |
| `cli-tmux` | `CLITmuxProvider` | 把本地 codex/claude/grok CLI 塞进 detached tmux，tail 它的 JSONL stdout（731 行，最大的 provider 文件） |
| `mock` | `MockProvider` | 离线；带 `mockScript` 时变成"每回合一条脚本"的可编程假 provider，用来在无网络无 key 情况下测 tool 流程（`providers.go:32-91`） |

内置 provider 预设 **9 个**（`config.go:26-110`）：codex / claude / codex-api / claude-api / grok / grok-cli / deepseek / glm / mock。

### 8.2 方言与怪癖处理（slide 金句素材）

**(1) OpenAI Chat：严格后端拒绝空数组和 null**（`http.go:406-421`）
```go
// Strict backends (DeepSeek, GLM) reject `tool_calls: []` and a null
// content with no tool calls, so both keys are only sent when meaningful.
entry := map[string]any{"role": "assistant"}
if text != "" {
    entry["content"] = text
} else if len(toolCalls) > 0 {
    entry["content"] = nil
} else {
    entry["content"] = ""
}
if len(toolCalls) > 0 { entry["tool_calls"] = toolCalls }
```

**(2) OpenAI Responses：tool call 必须回传，否则整轮被拒**（`http.go:288-297`）
```go
// The tool calls have to go back too. Without them the
// `function_call_output` below references a `call_id` that is not in
// the input, and the API rejects the whole turn.
```

**(3) Anthropic：鉴权方案要靠猜**（`http.go:126-158`）—— `sk-ant-` 前缀 → `x-api-key`；env 名含 `OAUTH`/`AUTH_TOKEN` → `Authorization: Bearer`；可被 `authScheme` 显式覆盖。

**(4) tool result 的角色映射三家全不同**：Anthropic 塞进 `role:user` 的 `tool_result` block（`http.go:184-191`）；Responses 用顶层 `function_call_output`（`http.go:298-301`）；Chat 用 `role:"tool"` + `tool_call_id`（`http.go:422-425`）。

**(5) 参数解析永不 panic**：`safeArguments` 解析失败时返回 `{"raw": <原文>}` 而非报错（`http.go:502-511`）；ID 缺失时补 `call_<index>`（`http.go:495-500`）。

**(6) 401/403 特判**：直接换成"你需要哪个凭据"的提示，而不是抛原始 JSON（`http.go:74-78`）。

**(7) CLI 型的 resume delta**：只把「上次本 provider 的 assistant 消息之后」的新消息发过去（`clitmux.go:249-260`），并在每次 resume 时重新携带 system prompt —— 注释解释：`The system prompt is only sent on the first turn of a resumed CLI session`（`clitmux.go:326-329`）。

**(8) tmux 失败回落直跑**：`runDirect`（`clitmux.go:278-295`），但**被中断时不回落**（文件头注释 `clitmux.go:3-6`）。

**(9) 流式事件归一**：`internal/providers/stream.go:3-5` 把 `claude -p --output-format stream-json` 和 `codex exec --json` 两种 JSONL 归一成一个 `StreamEvent{Kind: status|thinking|text|tool|usage|final|plan}`（`stream.go:15-30`）。Claude Code 会屏蔽推理原文只给 token 估算，Codex 给真文本 —— REPL 对此有专门注释（`repl.go:285-286`）。

### 8.3 HTTP 层共性

- 全局 `http.Client{Timeout: 10 * time.Minute}`（`http.go:22`）—— 单例、10 分钟超时。
- `postJSON` 统一：先设内置 header，再用 `provider.Headers` 覆盖（`http.go:54-59`，允许配置层强制改任意头）。
- **非流式**：三个 HTTP provider 都是一次性 POST + 解析，流式只发生在 CLI-tmux 路径。[A]

---

## 9. 安全闸（与内核耦合的部分）[A]

主循环里**唯一一处安全调用**在工具执行前一行（`agentloop.go:456-463`）：

```go
// Tier gate. Command-level safety concerns are raised inside the
// tool, which is the only place that knows the actual command text.
err := security.RequestApproval(types.ApprovalRequest{
    Tool: call.Name, Tier: security.TierForRisk(tool.Risk), Summary: summarizeCall(call),
}, callContext)
```

两级设计（`internal/security/approval.go:3-9`）：tier（read/write/exec，由 `Tool.Risk` 推导，`approval.go:60-70`）× mode（`yolo/safe/write/always-ask`，`types.go:253-263`）。最关键的一条规则（`approval.go:101-104`）：

```go
// Safety concerns outrank an "allow" override in every mode but yolo: the
// operator allowing `run_command` is not the same as allowing `rm -rf /`.
mustAsk := len(request.Concerns) > 0 && mode != types.ApprovalYolo
```

无人值守时（`tc.Confirm == nil`）默认**拒绝**（`approval.go:108-110`）；交互式提示里裸回车也等于 no（`repl.go:743-773`，注释：`the safe answer is the one you get by reflex`）。

---

## 10. 可直接上 slide 的数字卡

| 卡片 | 数字 | 出处 |
|---|---|---|
| agent 内核 | 640 行 `agentloop.go`，主循环函数 241 行 | `internal/core/agentloop.go` |
| 最大回合 | 8 | `config.go:23` |
| 停止条件 | 3 个 + 1 个触顶出口 | `agentloop.go:332,421,494,500` |
| 上下文预算 | 48,000 tokens（可 per-provider 覆盖） | `agentloop.go:18` |
| 工具输出预算 | 24,000 字符，超出落 artifact 文件 | `app.go:134`, `output.go` |
| 内建工具 | 24 → caveman executor 只剩 14 | `registry.go:23-50`, `delegate.go:145-162` |
| caveman 包大小上限 | 6,000 字符 | `delegate.go:97` |
| 任务清单上限 | 64 步 / 每步 200 字符 | `plan.go:20-23` |
| provider 后端 | 5 种 kind / 9 个预设 | `types.go:13-19`, `config.go:26-110` |
| 扩展 hook | 8 个回调点 | 见 §2.5 |
| slash 命令 | 49 个，turn 内只开放 5 个 | `commands.go`, `repl.go:716-733` |
| 外部依赖 | 1（`golang.org/x/term`） | `go.mod` |

---

## 附：未验证 / 需注意

- [C] `internal/buildinfo` 未单独展开（版本字符串生成，与架构无关）。
- [C] `internal/ui`（约 4,300 行，占全仓 18%）是最大的包，但对 agent 语义无影响 —— 可作为"体验成本"论据。
- [A] `types.RunOptions`（`types.go:440-446`）与 `core.RunOptions`（`agentloop.go:243-263`）**同名但不同结构**，前者似为遗留，未被主循环使用。
- 未运行任何二进制；全部结论来自静态阅读。
