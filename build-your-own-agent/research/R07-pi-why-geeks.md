# R07：pi agent（badlogic/pi-mono → earendil-works/pi）为什么受极客圈喜欢

> 研究日期：2026-08-01
> 本地代码基线：`/Users/nongjiawu/playground/research/pi/pi-mono`，workspace 版本 **0.83.0**，HEAD `4488ad55c18f07ae89a489096c90de8667b3adfb`（2026-08-01 03:00:02 +0300，浅克隆）
> 所有联网数据的抓取时间均为 2026-08-01。星标/下载等动态数字请在上台前复查。

---

## 0. 一句话结论

pi 的极客吸引力不来自"功能多"，而来自一条彻底贯穿的产品哲学：**core 保持最小 → 一切能力靠 TypeScript extension / skill 外挂 → 而写这些外挂的活儿本身可以交给 agent 自己干**。加上会话是可读 JSONL 树、MIT、依赖极少、供应链加固、作者公开真实 session 数据集，它命中了"可读、可改、可拥有"这一组老派黑客价值观。

pi.dev 首页的 slogan 就是这个意思：**"There are many agent harnesses—but this one is yours"**（来源：https://pi.dev ，抓取于 2026-08-01）。

---

## 1. 事实基线（可核查）

| 项 | 值 | 出处 |
|---|---|---|
| GitHub 仓库 | `earendil-works/pi`（旧路径 `badlogic/pi-mono` 现 301 跳转） | `gh api repos/earendil-works/pi` |
| 创建时间 | 2025-08-09T14:03:50Z | 同上（`created_at`） |
| Star / Fork | **81,525 / 10,065** | 同上，抓取于 2026-08-01 |
| Watchers / open issues | 273 / 91 | 同上 |
| License | **MIT**（Copyright (c) 2025 Mario Zechner） | `pi-mono/LICENSE:1-3` |
| 主语言 | TypeScript | 同上 |
| GitHub Release 总数 | **252** | `gh api repos/.../releases?per_page=1` 的 `Link: rel="last"` = page 252 |
| 最新 release | **v0.83.0，2026-07-29T22:30:33Z** | `gh api repos/earendil-works/pi/releases` |
| contributor 数 | 250（GitHub contributors 接口，上限 500，故 250 应为实数） | `gh api repos/.../contributors --paginate` |
| issue 总量（含已关） | 4,597 | `gh api search/issues?q=repo:earendil-works/pi+type:issue` |
| npm 包（新） | `@earendil-works/pi-coding-agent`，首发 **0.74.0 / 2026-05-07**，latest **0.83.0 / 2026-07-29**，共 38 版 | registry.npmjs.org |
| npm 包（旧） | `@mariozechner/pi-coding-agent`，首发 **0.6.2 / 2025-11-12**，末版 **0.73.1 / 2026-05-07**，共 271 版 | registry.npmjs.org |
| → 合计发版 | **~309 个 npm 版本 / 约 9 个月** | 上两行相加 |
| 源码体量（`packages/*/src`，含注释空行） | 合计 **110,436 行**；coding-agent 56,431（183 文件）、ai 21,429（169）、tui 14,184（37）、agent 10,368（37）、server 4,281、protocol 1,233、client 1,233 | 本地 `find + wc -l`，v0.83.0 |
| 内置工具数 | **7 个定义，默认只给模型 4 个**（read / bash / edit / write） | `analysis/raw/02-pi-coding-agent-tui.md:36`（引 `core/tools/index.ts:83`、`core/agent-session.ts:2590`） |
| 示例扩展 | `packages/coding-agent/examples/extensions/` 下 **79 个条目** | 本地 `ls \| wc -l` |
| 文档体量 | `packages/coding-agent/docs/*.md` 合计 **12,113 行**，其中 `extensions.md` 2,984 行 | 本地 `wc -l` |
| 生态包目录 | pi.dev/packages 列出 **5,345 个** package（extensions / skills / themes / prompt templates） | https://pi.dev/packages ，抓取于 2026-08-01 |

**归属变更（重要背景）**：2026-04-08，Mario Zechner 宣布加入 Armin Ronacher（Flask 作者）联合创立的 Earendil Inc.，pi 随之移交。
- Armin Ronacher《Mario and Earendil》，2026-04-08：https://lucumr.pocoo.org/2026/4/8/mario-and-earendil/ ——"we want Pi to continue to exist as a high-quality, open, extensible piece of software."
- Earendil《Announcing Pi & Lefos》，2026-04-08：https://earendil.com/posts/announcing-pi-and-lefos/ ——称 pi 是 "the minimal agent within OpenClaw"、"a widely-adopted Open Source coding agent and harness"。

---

## 2. Q1：定位与差异化——"harness" 和 "self extensible" 到底指什么

### 2.1 "agent harness"

- 官方定义（仓库根 README 标题即为 **"Pi Agent Harness"**）：`pi-mono/README.md:13-15`
  > "This is the home of the Pi agent harness project including our **self extensible coding agent**."
- 文档层定义：`packages/coding-agent/docs/index.md:3`
  > "Pi is a minimal terminal coding harness. It is designed to **stay small at the core** while being extended through TypeScript extensions, skills, prompt templates, themes, and pi packages."
- 社区给出的最清楚的解释（HN，非官方但准确）：
  - rytill，2026-02-26T03:10:42Z（HN id 47161331）："If an agent is an LLM in a loop with tool calls, there are two components: 1) the LLM. 2) The loop with tool calls. That second part could be called the harness."
  - jasonjmcghee，2026-02-25T23:48:02Z（HN id 47159755）："Harness is an appropriate name. It comes from reinforcement learning world where you need to build the proper scaffolding for it to optimize for the goal you want it to."

即：**harness = 去掉 LLM 之后剩下的那一整套「循环 + 工具 + 上下文管理 + UI + 持久化」**。pi 卖的是这一层，不是模型。

### 2.2 差异化 = "刻意不做的清单"

`packages/coding-agent/README.md:491-507`（Philosophy 节）逐条列明：

| 行号 | 原文（节选） |
|---|---|
| :493 | "Pi is **aggressively extensible** so it doesn't have to dictate your workflow." |
| :495 | "**No MCP.** Build CLI tools with READMEs, or build an extension that adds MCP support." |
| :497 | "**No sub-agents.** Spawn pi instances via tmux, or build your own with extensions." |
| :499 | "**No permission popups.** Run in a container, or build your own confirmation flow with extensions." |
| :501 | "**No plan mode.** Write plans to files, or build it with extensions." |
| :503 | "**No built-in to-dos.** They confuse models. Use a TODO.md file." |
| :505 | "**No background bash.** Use tmux. Full observability, direct interaction." |

同一份清单在 `packages/coding-agent/docs/usage.md:297-301`（"Design Principles"）复述。

对应的原始论证见 Mario Zechner 的博客（**2025-11-30 发布**，早于 pi 被 Earendil 收编）：
https://mariozechner.at/posts/2025-11-30-pi-coding-agent/ 《What I learned building an opinionated and minimal coding agent》
- 对 sub-agent："You have zero visibility into what that sub-agent does. It's a black box within a black box."
- 对 MCP："MCP servers are overkill for most use cases, and they come with significant context overhead."（另有专文 https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/ ，README:495 直接链接过去）
- 对 to-do："to-do lists generally confuse models more than they help. They add state that the model has to track and update."

> ⚠️ 该博客的引文经 WebFetch 摘要提取，措辞已尽量保留原文；上台前建议对逐字引用做一次人工核对。

### 2.3 差异化的"社会证明"

- **OpenClaw 底层就是 pi**。Earendil 官方口径："Pi is the minimal agent within OpenClaw"（https://earendil.com/posts/announcing-pi-and-lefos/ ，2026-04-08）。HN 上多人确认，如 stavros，2026-04-08T11:55:57Z（id 47688960）："OpenClaw uses Pi the framework, so now Mario Zechner is joining Armin Ronacher's company."
- **OpenAI 官方点名**：https://developers.openai.com/community/codex-for-oss ——"Developers should code in the tools they prefer, whether that's Codex, OpenCode, Cline, **pi**, OpenClaw, or something else"。

---

## 3. Q2：**"自扩展"具体怎么实现**（完整证据链）

pi 的"self extensible"不是营销词，是一条**可以在源码里逐环节验证的机制链**：

### 环节 1 — 文档和示例随 npm 包一起发布

`packages/coding-agent/package.json:27-34`：
```json
"files": ["dist", "docs", "examples", "containerization.md", "CHANGELOG.md", "npm-shrinkwrap.json"]
```
即 12,113 行文档 + 79 个示例扩展会安装到用户机器上，而不是只留在 GitHub。

### 环节 2 — 系统提示里直接写死"你自己的文档在哪"

`packages/coding-agent/src/core/system-prompt.ts:131-138`（默认提示模板的一段）：
```
Pi documentation (read only when the user asks about pi itself, its SDK, extensions, themes, skills, or TUI):
- Main documentation: ${readmePath}
- Additional docs: ${docsPath}
- Examples: ${examplesPath} (extensions, custom tools, SDK)
...
- When asked about: extensions (docs/extensions.md, examples/extensions/), themes (docs/themes.md), skills (docs/skills.md), ...
- When working on pi topics, read the docs and examples, and follow .md cross-references before implementing
```
路径由 `packages/coding-agent/src/config.ts:427-439` 的 `getReadmePath()/getDocsPath()/getExamplesPath()` 解析为绝对路径。

**这就是"self extensible"的物理实现**：agent 拿到的是"读自己的源码级文档 + 抄自己的 79 个示例"的能力，然后用 `write` 工具写出新的 `.ts` 扩展。

维护者本人在 HN 上的确认（the_mitsuhiko = Armin Ronacher，2026-02-25T07:34:19Z，HN id 47148529）：
> "Pi ships with docs that include extensions and **the agent looks there for inspiration if you ask it to build a custom extension.**"

### 环节 3 — 每份可扩展文档的第一行就是"叫 pi 自己写"

| 文件 | 第 1 行 |
|---|---|
| `docs/extensions.md:1` | `> pi can create extensions. Ask it to build one for your use case.` |
| `docs/skills.md:1` | `> pi can create skills. Ask it to build one for your use case.` |
| `docs/tui.md:1` | `> pi can create TUI components. Ask it to build one for your use case.` |
| `docs/themes.md:1` | `> pi can create themes. Ask it to build one for your setup.` |
| `docs/prompt-templates.md:1` | `> pi can create prompt templates. Ask it to build one for your workflow.` |
| `docs/sdk.md:1` | `> pi can help you use the SDK. Ask it to build an integration for your use case.` |

根 README 更直白（`pi-mono/README.md:24`）："Read the documentation, but **you can also ask the agent to explain itself**."

### 环节 4 — 写完能热加载，不用重启（闭环的关键）

- `/reload` 命令：`packages/coding-agent/src/core/slash-commands.ts:40`
  > `{ name: "reload", description: "Reload keybindings, extensions, skills, prompts, themes, and context files" }`
- `docs/extensions.md:7`："Extensions in auto-discovered locations can be **hot-reloaded with `/reload`**."
- 扩展 API 里有 `ctx.reload()`：`docs/extensions.md:1275-1297`。

### 环节 5 — **agent 可以自己触发 reload**（官方文档给了完整代码）

`docs/extensions.md:1299-1332`：
> "Tools run with `ExtensionContext`, so they cannot call `ctx.reload()` directly. Use a command as the reload entrypoint, then expose a tool that queues that command as a follow-up user message.
> **Example tool the LLM can call to trigger reload:**"
```typescript
pi.registerTool({
  name: "reload_runtime",          // docs/extensions.md:1317
  label: "Reload Runtime",
  description: "Reload extensions, skills, prompts, themes, and context files",
  parameters: Type.Object({}),
  async execute() {
    pi.sendUserMessage("/reload-runtime", { deliverAs: "followUp" });
    return { content: [{ type: "text", text: "Queued /reload-runtime as a follow-up command." }] };
  },
});
```

**闭环成立**：agent 读自己的文档 → 写新扩展文件 → 调 `reload_runtime` → 下一轮就多了新工具。**一次会话内 agent 可以改变自己的工具集，不需要人重启进程。**

### 环节 6 — 运行中动态增删工具（不废掉 prompt cache）

`docs/extensions.md:2327-2341`（Dynamic Tool Loading）：
> "Extensions can register many tools while keeping only a small initial set active. A tool can then add more tools with `pi.setActiveTools()` during execution. Pi detects purely additive changes, records the newly available tool names on that tool result, and applies the updated active set before the next model request."

底层由 `packages/ai/src/utils/deferred-tools.ts` 支持（Anthropic 的 `tool_reference` / `defer_loading`、OpenAI 的 `tool_search_call`），目的正是**新增工具不作废前缀缓存**（见 `analysis/raw/01-pi-agent-ai-core.md:156`）。

### 环节 7 — 真实用户已经这么干了（第三方证据）

HN 用户 self_awareness，2026-02-26T17:48:03Z（HN id 47169421，thread 47143754）：
> "I just told PI to **generate itself** a `permissioned_*` equivalents of read,write,bash,edit. Now, `permissioned_read`, `permissioned_write`, `permissioned_edit` have full access to anything from current dir and deeper, and `permissioned_bash` is always permission-gated. Default read,edit,write,bash are disabled. It seems to work really good. Generally, I'm in awe. **I think I've already changed the way I work.**"

HN 用户 stpedgwdgfhgdd，2026-07-09T16:16:19Z（HN id 48848338，thread 48847407）：
> "Pi is meant for people who know what they are doing... The whole idea is that **you customize Pi to your own needs by asking it to modify itself through extensions.**"

### 环节 8 — 生态规模验证机制有效

pi.dev/packages 列出 **5,345 个**第三方 package（抓取于 2026-08-01），其中包括 `pi-mcp-adapter`（nicopreme）——**核心不做 MCP，社区用扩展补上了 MCP**，恰好证明"外挂路线可行"这一主张。

---

## 4. Q3：刻意不做权限系统——理由、加分还是减分

### 4.1 官方理由（三处、口径一致）

1. `pi-mono/README.md:37-45`：
   > "Pi **does not include a built-in permission system** for restricting filesystem, process, network, or credential access. By default, it runs with the permissions of the user and process that launched it. **If you need stronger boundaries, containerize or sandbox Pi.**"
   随后给出三种模式：Gondolin micro-VM 扩展 / 纯 Docker / NVIDIA OpenShell（详见 `packages/coding-agent/docs/containerization.md`）。

2. `packages/coding-agent/docs/security.md:31-35`（"No Built-in Sandbox"）：
   > "**This is intentional.** Pi is designed to operate on local source trees, invoke project toolchains, and integrate with the user's existing development environment. **A partial in-process sandbox would be easy to misunderstand as a security boundary** while still depending on the host shell, filesystem, package managers, credentials, and extension code. **Real isolation needs to come from the operating system or a virtualization/container boundary.**"

3. `pi-mono/SECURITY.md:50`（Out Of Scope 第一条）：
   > "Local code execution or sandboxing behavior (**the Pi coding agent intentionally does not have a sandbox**)"
   同文件 :20-23 还写明 prompt injection 不视为漏洞："files like `AGENTS.md` or instructions in comments can be used to prompt inject the coding agent trivially and this cannot be protected against."

4. 作者原始论证（博客 2025-11-30）：
   > "As soon as your agent can write code and run code, it's pretty much game over. The only way you could prevent exfiltration of data would be to cut off all network access...which makes the agent mostly useless." ——并称其它 agent 的安全措施 "mostly security theater"。

5. 补充：pi **有** "project trust" 机制（决定是否加载项目本地 `.pi/` 扩展与设置，`docs/security.md:5-29`），但文档明说 "It is **not a sandbox**"。

### 4.2 极客圈：加分 or 减分？——**两边都有，且分歧本身就是话题度**

**加分派（诚实 > 剧场；且可自建）**

- the_mitsuhiko（Armin Ronacher），2026-02-25T07:30:01Z，HN id 47148492：
  > "I too would like to know what a good UX looks like here but I have doubts that the permission prompts of Claude are the way to go right now. **Within days people become used to just hitting accept and allowlisting pretty much everything.** The agents write length scripts into shell scripts or test runners that themselves can be destructive but they immediately allowlisted."
- chriswarbo，2026-02-25T00:57:48Z，HN id 47145881：
  > "**Pi supports permission popups, but doesn't use them by default.** Their example extensions show how to do it (add an event listener for `tool_call` events; to block the call put `block: true` in its result)."
  （代码侧证据：`docs/extensions.md` Quick Start 里第一个 `pi.on("tool_call", ...)` 示例就是拦 `rm -rf`。）
- kristianpaul（该 HN 帖的提交者本人），2026-02-25T16:46:45Z，HN id 47154031：
  > "this got me interested at first read: No plan mode... No built-in to-dos... No background bash. Use tmux. Full observability, direct interaction. **This is very important to have control and ownership.** Pi is not for everyone, but the ones eventually want to have tools like (read, bash, edit, write, grep, find, ls) as building blocks."
- 用户自建沙箱的实例：carderne，2026-02-25T11:45:19Z（id 47150266）——"I got pi to write me a very basic sandbox based on an example from the pi github... https://github.com/carderne/pi-sandbox"

**减分派**

- cyanydeez，2026-02-24T22:27:07Z，HN id 47144198：
  > "The backing to OpenClaw/MoltBot whatever they're calling themselves. Why is it insecure, well, Pi tells you >No permission popups."
- esafak，2026-02-25T05:30:58Z，HN id 47147706：
  > "But the agent has to interact with the world; fetch docs, push code, fetch comments, etc. You can't sandbox everything. So you push that configuration to your sandbox, **which is a worse UX than the harness just asking you at the right time** what you'd like to do."
- solarkraft，2026-02-25T12:24:12Z，HN id 47150619：
  > "while it does seem to do a lot of things very well around extensibility, **I do miss support for permissions, MCP and perhaps Todos and a server mode.** OpenCode seems a lot more complete in that regard."
- colinsane，2026-07-09T16:57:14Z，HN id 48848965：
  > "ironically (?) i prefer to improve Pi by connecting MCP servers instead of native extensions in part due to this (**process-level sandboxing is trivial**; anything more granular -- as would be required for in-process plugins -- is far more intimidating)."

**演讲建议的判断**：对极客圈整体是**净加分**，因为 pi 把"要不要权限系统"从产品决策降级为**用户的一次扩展编写**（10 行 `pi.on("tool_call")`），并且拒绝提供"看起来安全但不是安全边界"的东西——这对懂行的人是诚实信号。但对企业/团队采购、以及"我只想装了就用"的人群是明确减分项，也是 pi 与 OpenCode/Claude Code 的主要分野。

---

## 5. Q4：session 树 / JSONL / fork / resume 对 power user 的价值

### 5.1 机制（本地文档 + 源码）

- 格式：`packages/coding-agent/docs/session-format.md:3`
  > "Sessions are stored as **JSONL** (JSON Lines) files. Each line is a JSON object with a `type` field. Session entries form a **tree structure via `id`/`parentId` fields**, enabling **in-place branching without creating new files**."
- 存储位置：`~/.pi/agent/sessions/--<cwd 编码>--/<ISO时间戳>_<uuid>.jsonl`（`docs/session-format.md:7-11`）
- 版本演进：v1 线性 → v2 树 → v3 重命名 `hookMessage`→`custom`，加载时自动迁移（`docs/session-format.md:22-28`）
- entry 类型：`message` / `model_change` / `thinking_level_change` / `compaction` / `branch_summary` / `custom` / `custom_message` / `label` / `session_info`（`docs/session-format.md:208-301`）——**换模型、改思考档、打书签都是树上的一条边**
- 命令面：`/tree`（原地导航整棵树）、`/fork`（从旧的 user message 长出新会话文件）、`/clone`（复制当前分支为新文件）、`/resume`、`/compact`、`/export`（自包含单文件 HTML）、`/share`（私有 gist）——对照表见 `docs/sessions.md:29-36` 与 `:118-127`
- **分支摘要**：`/tree` 切走一条分支时，可让模型总结被放弃的分支并挂到新位置（`docs/sessions.md:129-139`），避免"换条路就丢上下文"
- 延迟落盘：文件在第一条 assistant 消息出现时才创建，避免空会话堆积（`analysis/raw/02-pi-coding-agent-tui.md:128`）
- 跨 provider 续接：`packages/ai/src/api/transform-messages.ts` 在切模型时丢弃加密 thinking、降级普通 thinking 为 text、归一化 tool call id、给孤儿 tool call 补合成结果（`analysis/raw/01-pi-agent-ai-core.md:110-115`）——**这是"同一条 session 里换模型"能跑通的工程前提**

### 5.2 power user 为什么在乎（真实引用）

- jauntywundrkind，2026-02-25T03:40:16Z，HN id 47147023：
  > "As for subagents, **Pi has sessions. And it has a full session tree & forking. This is one of my favorite things, in all harnesses:** build the thing with half the context, then keep using that as a checkpoint, doing new work, from that same branch point. It means still having a very usable lengthy context window but having good fundamental project knowledge loaded."
- theturtletalks，2026-07-31T11:38:46Z，HN id 49121876（thread 49118781）：
  > "**This is exactly why Pi will win. It lets you hot swap models when one is struggling or straight up refusing the task.** And since it works with any sub outside Claude Code, you can use it to try different models on OpenCode Go sub or even OpenRouter."
- theturtletalks，2026-07-31T17:03:57Z，HN id 49125819：
  > "1. Sessions are locked into Codex and Claude Code so you can't take a session with you. **Pi solves that since they all stay Pi sessions and you can change models in the same session.** 2. Subagent prompts are not shown. Pi solves this by not supporting subagents out of the box..."
- jsumrall，2026-02-25T18:13:27Z，HN id 47155345：
  > "In the middle of a session I might switch from gpt-5.2 to opus and get it to do something or review something and then switch back to gpt. Since models are being released every few weeks this is interesting to compare models without having to switch to a different harness."
- theturtletalks，2026-07-31T19:28:41Z，HN id 49127547（把 JSONL 当 API 用）：
  > "the Pi extension I made lets **Pi read and parse the JSONL files for the session.** It also has workspaces with their own memory."
- NamlchakKhandro，2026-07-31T13:42:51Z，HN id 49123050（老鸟的实操细节）：
  > "switching models mid session kills your KV cache. you should fork or handoff or start a new one and tell the new one to **read the old session.jsonl**"

### 5.3 时代红利：这个点在 2026 年 7 月被放大

Earendil 于 **2026-07-30** 发表《The Session You Cannot Take With You》（https://earendil.com/posts/session-portability/ ），论证 provider 正通过加密 reasoning token、服务端 web search、不透明 compaction 把 session 锁死在自家：
> "The transcript on your machine is no longer your session but a partial view of a session whose operational state belongs to an inference provider and not you."
> "The user should be able to close an account, keep a session, and hand it to another model."

该文 **2026-07-31 登上 HN，733 分 / 212 条评论**（HN id 49118781）。**这是目前最新、最热的"pi 相关"公共讨论，演讲若在 2026 年 8 月讲，这是最新鲜的锚点。**

---

## 6. Q5：工程洁癖细节（"这仓库是能读的"）

### 6.1 体量与可读性

- `packages/*/src` 合计 110,436 行 TypeScript；四件套 read/bash/edit/write 是默认全部工具。
- 最有力的第三方评价（HN 用户 fny，2026-02-15T23:51:12Z，HN id 47029074，在 "I'm joining OpenAI" 帖下）：
  > "**The pi agent repos are a joy to read, are 1/100th the size of OpenClaw, and have 95% of the functionality.**"
  （注：`1/100th` 是该用户的主观量级说法，未经独立测量，上 PPT 请按"用户评价"引用，不要当成实测数据。）
- rkunnamp，2026-02-16T00:19:51Z，HN id 47029294：
  > "**Your Pi is a piece of art.** Thank you for building it. I spend almost 16 hrs a day with it. And there is not a single day I am not awestruck. Big fan!"

### 6.2 依赖极少 / 不用重型框架

v0.83.0 各包 **runtime dependencies**（`packages/*/package.json`）：

| 包 | 外部依赖 | 说明 |
|---|---|---|
| `pi-tui` | **2 个**：`get-east-asian-width`, `marked` | 一个 14k 行的终端 UI 框架，差分渲染自研 |
| `pi-protocol` | **1 个**：`typebox` | CBOR 编解码器是手写 RFC 8949 严格子集，不用第三方 CBOR 库（`analysis/raw/03-...md:11`） |
| `pi-agent-core` | 4 个外部：`diff`, `ignore`, `typebox`, `yaml` | |
| `pi-coding-agent` | 15 个外部（chalk / glob / undici / jiti / semver / minimatch / highlight.js / …） | 其余 5 个是 workspace 内部包 |
| `pi-ai` | 11 个（主要是各家官方 SDK + `partial-json`） | 用 lazy import，"40 个 provider 但只打包 1 个 SDK"（`analysis/raw/01-...md:86-97`） |
| 根 devDependencies | **仅 10 个** | biome / tsgo / esbuild / husky / shx / tsx / typescript / … |

技术选型也很"极客口味"：schema 全用 **TypeBox 而非 Zod**；类型检查用 **`tsgo`（`@typescript/native-preview`）而非 tsc**；lint/format 用 **biome**；源码只用 **erasable TypeScript 语法**（Node strip-only 模式可直接跑，禁 `enum`/`namespace`/参数属性，见 `pi-mono/AGENTS.md:20`）。

### 6.3 供应链加固（`pi-mono/README.md:75-87`，逐条可查）

| 措施 | 证据 |
|---|---|
| 直接外部依赖**全部锁定精确版本**，内部 workspace 包保留 range | `README.md:79` |
| `.npmrc` 设 `save-exact=true` + **`min-release-age=2`**（避免解析到当天刚发布的依赖，防投毒窗口） | `pi-mono/.npmrc:1-2` |
| `package-lock.json` 为唯一事实来源；**pre-commit 阻止误提交 lockfile**，除非显式 `PI_ALLOW_LOCKFILE_CHANGE=1` | `README.md:81`；`pi-mono/.husky/pre-commit` |
| 发布的 CLI 包内含 `npm-shrinkwrap.json`，为 npm 用户锁死传递依赖 | `README.md:83`；`packages/coding-agent/package.json:27-34` |
| 官方安装命令带 `--ignore-scripts`；CI 用 `npm ci --ignore-scripts`；`pi update --self` 同样 | `README.md:85-86`、`docs/index.md:10-13` |
| **依赖 lifecycle script 需显式 allowlist**，新增带脚本的依赖会让 check 失败直到人工评审 | `README.md:87`；`AGENTS.md:42` |
| 定时 GitHub workflow 跑 `npm audit --omit=dev` + `npm audit signatures --omit=dev` | `README.md:86` |
| npm 发布走 **GitHub Actions OIDC trusted publishing**，本地不需要 token/OTP | `AGENTS.md:156` |
| Release 源码 tarball 带 `SHA256SUMS`，可**从发布源码复现官方 standalone 二进制** | `README.md:62-73` |

### 6.4 其它"洁癖"细节（都很上镜）

- **AGENTS.md 是给人和 agent 共用的一份规则**（`pi-mono/README.md:49`）。里面有一条极有画面感的规则（`AGENTS.md:47-59`）：
  > "**Multiple pi sessions may be running in this cwd at the same time**, each modifying different files. ... Stage explicit paths (`git add <path1> <path2>`); **never `git add -A` / `git add .`**."
  以及"Never run: `git reset --hard`, `git checkout .`, `git clean -fd`, `git stash`, `git commit --no-verify`"——**这是一份为"多 agent 并发在同一个 worktree 里干活"写的 git 规范**。
- **贡献门槛写在明面上**（争议但极客爱看）：`pi-mono/README.md:11` + `CONTRIBUTING.md:23-34`
  > "All issues and PRs from new contributors are **auto-closed by default**." 维护者回复 `lgtmi` 解锁提 issue，`lgtm` 才解锁提 PR。
  `CONTRIBUTING.md:15`（The One Rule）：
  > "**You must understand your code.** ... Using AI to write code is fine. **Submitting AI-generated slop without understanding it is not.**"
  `CONTRIBUTING.md:9`：
  > "If your feature does not belong in the core, it should be an extension. **PRs that bloat the core will likely be rejected.**"
- **公开 RFC 流程**：https://rfc.earendil.com/keyword/pi/ 列出 9 篇 pi 相关公开 RFC（RFC-0015 Pi Licensing 2026-03-30 讨论中；RFC-0019 Pi Telemetry 2026-04-14 已实现；RFC-0031 Terminal Multiplexers 2026-05-07 已发布；RFC-0043 Experimental Pi Flag 2026-06-09 已发布；RFC-0047 New Locked Pi Install 2026-06-24；RFC-0054 Responses Lite Investigation 2026-07-11 等）。抓取于 2026-08-01。
- **四种运行模式**：interactive / print(JSON) / RPC(stdin-stdout JSONL) / SDK（`packages/coding-agent/README.md:19`）。RPC 模式让编辑器集成变得平凡——HN 用户 chriswarbo，2026-02-25T16:48:01Z（id 47154047）：
  > "Doesn't need a terminal: run it in RPC mode to send/receive JSON over stdio. That's how the **pi-coding-agent Emacs package** works, which is the only way I've ever used Pi. ... when I added permission requests to the `bash` tool, the 'Are you sure y/N' requests started appearing just like they were native to Emacs."

---

## 7. Q6：作者把真实 session 公开到 HuggingFace 的意义

### 7.1 事实

- 数据集：https://huggingface.co/datasets/badlogicgames/pi-mono
  - 创建于 **2026-04-06T13:07:23Z**，`lastModified` **2026-04-06T13:10:36Z**（HF API）
  - **627 个 `.jsonl` session 文件**（+ manifest），合计 **224.8 MB**（629 个 file 对象）
  - **188 likes**，`downloads`（近 30 天）**1,337**（抓取于 2026-08-01）
  - 最早 session 文件名时间戳：`2026-01-16T02-31-35-233Z`
  - license: `other`；tags: `agent-traces`, `coding-agent`, `pi-share-hf`
- 工具：https://github.com/badlogic/pi-share-hf ——三层防护：**确定性 redaction（精确 secret 值，非泛正则）→ TruffleHog 扫描兜底（任何命中直接拒绝该 session）→ LLM review（判断是否与该 OSS 项目相关、是否适合公开、是否有漏网）**，全部通过才上传。
  - README 原话："This is deliberate. **Exact values are high precision. Generic token regexes are noisy.**"
- 号召写在两个 README 的显眼位置：`pi-mono/README.md:89-104` 与 `packages/coding-agent/README.md:21-37`：
  > "**Public OSS session data helps improve coding agents with real-world tasks, tool use, failures, and fixes instead of toy benchmarks.**"
- 相关 X 帖（作者 @badlogicgames）：
  - https://x.com/badlogicgames/status/2037811643774652911 —— README 指为"完整解释"的那篇
  - https://x.com/badlogicgames/status/2040979640265633882 —— pi-share-hf 发布帖，正文（经搜索引擎快照）："Putting my tokens where my mouth is. I built pi-share-hf. Share your pi coding agent sessions as @huggingface datasets. It tries to prevent you from uploading sessions containing PII/sensitive data with 3 tiers of defenses..."
  - https://x.com/badlogicgames/status/2041151967695634619 —— README 指为"演示如何发布 pi-mono session"的视频
  - https://x.com/badlogicgames/status/2041309308290244646 —— 加入 TruffleHog 的更新帖
  > ⚠️ **日期说明**：x.com 对本工具返回 HTTP 402，无法直读页面。以上日期由 **推文 snowflake ID 反解**得到（`(id >> 22) + 1288834974657` 毫秒）：分别为 **2026-03-28**、**2026-04-06**、**2026-04-06**、**2026-04-07**（UTC）。方法确定可复现，但**未经页面直接核对，标记为「待核实」**。

### 7.2 为什么这件事在极客圈有分量

1. **"把嘴上说的用 token 兑现"**：作者自己不是发一篇《我们该开放 agent 数据》的檄文，而是先把自己 627 段真实工作 session（含失败、走弯路、被中断、compaction）倒出来。
2. **打的是 benchmark 造假问题**："real-world tasks, tool use, failures, and fixes **instead of toy benchmarks**"——极客圈对 SWE-bench 式刷榜早有疲劳，这是对症的。
3. **与 Q4 的 JSONL 开放格式互为因果**：正因为 session 是纯 JSONL 树、不含 provider 私有密文，它才**能够**被导出、脱敏、公开、被别人 parse。闭源 harness 的 session 想开放也开放不了——这正是 2026-07-30 那篇《The Session You Cannot Take With You》的论点。
4. **自曝式透明**：公开自己的 agent session ≈ 公开自己的开发过程和错误，这在工程师文化里是极高的可信度信号（类比公开 `.vimrc`、公开 postmortem）。
5. **已经形成社区效应**：@christinetyip 把它做成了 skill（"so agents can automatically share + learn from the traces in a collective intelligence"，X 帖 https://x.com/christinetyip/status/2041640711645491245 ）。

---

## 8. Q7：极客圈的具体评价（真实引用，注明出处与日期）

**主要公共讨论源：Hacker News thread 47143754**
- 标题 "Pi – A minimal terminal coding harness"，提交者 `kristianpaul`，链接 https://pi.dev
- **发布时间 2026-02-24T21:53:59Z（UTC），608 分，306 条评论**（数据来自 HN Firebase API `item/47143754`，抓取于 2026-08-01）
- 讨论页：https://news.ycombinator.com/item?id=47143754

### 8.1 高强度正面

| 引用 | 作者 / 时间 / ID |
|---|---|
| "**My current fave harness.** I've been using it to great effect, **since it is self-extensible**, and added support for it to https://github.com/rcarmo/vibes because it is so much faster than ACP." | rcarmo，2026-02-24T22:40:28Z，47144370 |
| "**I haven't met a single person who has tried pi for a few days and not made it their daily driver.** Once you taste the freedom of being able to set up your tool exactly how you like, there's really no going back." | tmustier，2026-02-25T00:38:41Z，47145723 |
| "I spent 3 months adopting Codex and Claude Code SDKs only to realize **they're just vendor lock-in and brittle**... After digging into OpenClaw codebase, I can safely say that **most of its success comes from the underlying harness, pi agent.** pi plugins support adding hooks at every stage, from tool calls to compaction and let you customize the TUI UI as well." | buremba，2026-02-25T06:23:25Z，47148023 |
| "To me, the most interesting thing about Pi and the 'claw' phenomenon is what it means for open source... Instead of extensions you install, you download a skill file that tells a coding agent how to add a feature. **The software stops being an artifact and starts being a living tool that isn't the same as anyone else's copy.**" | CGamesPlay，2026-02-25T03:28:43Z，47146936 |
| "**Your Pi is a piece of art.** ... I spend almost 16 hrs a day with it. And there is not a single day I am not awestruck." | rkunnamp，2026-02-16T00:19:51Z，47029294（在 "I'm joining OpenAI" 帖下） |
| "**The pi agent repos are a joy to read, are 1/100th the size of OpenClaw, and have 95% of the functionality.**" | fny，2026-02-15T23:51:12Z，47029074 |
| "**Pi to me felt like when you install a fresh OS with nothing on it and then customize it to your liking.** Sure there are some features that you'll want immediately but when I took a look at the number of slash commands that ship with Claude code I find it ridiculous." | alasano，2026-07-31T15:28:29Z，49124337 |
| "it is not just what you can add that Claude Code doesn't offer, but also **what you don't need to add that Claude Code does offer that you don't want.** ... With Pi, I just didn't install an extension for that." | tomashubelbauer，2026-02-25T09:13:37Z，47149209 |
| "PI is what it looks like when you **treat your Plugin sdk as the golden path**" | NamlchakKhandro，2026-03-06T04:54:10Z，47271031 |
| "But I like pi precisely because it is so minimal. I want to understand and work around the simplest possible agentic coding setup, find the sharp edges, maybe even improve my prompting ability. And doing all three with a locally hosted LLM." | clusterhacks，2026-07-09T15:50:44Z，47(48)847944 |

### 8.2 负面 / 保留意见（必须给，否则不可信）

| 引用 | 作者 / 时间 / ID |
|---|---|
| "> I haven't met a single person who has tried pi for a few days and not made it their daily driver. **Pleased to meet you!** For me, it just didn't compare in quality with Claude CLI and OpenCode. **It didn't finish the job.** Interesting for extending, certainly, but not where my productivity gains lie." | sshine，2026-02-25T03:41:06Z，47147031 |
| "I do miss support for **permissions, MCP and perhaps Todos and a server mode**. OpenCode seems a lot more complete in that regard." | solarkraft，2026-02-25T12:24:12Z，47150619 |
| "Making the upgrades or maintaining or crafting from scratch a plugin isn't free, **it costs tokens and time and attention. And you're almost assuredly reinventing a wheel** that someone else already did and probably did better." | evilduck，2026-07-09T17:55:13Z，48849920 |
| "> Pi is meant for people who know what they are doing —— **How many people genuinely know what they're doing when the value prop of Pi is basically to vibe code it to your taste?**" | ljm，2026-07-09T17:12:26Z，48849185 |
| "Pi's OSS vacation BS..."（抱怨 PR 无人处理，因贡献门槛/休假制度） | neop1x，2026-02-25T23:31:39Z，47159577 |
| "even Steinberger in his interviews is not giving pi the proper attribution."（社区对 OpenClaw 未署名 pi 的不满） | twsted，2026-02-25T20:44:33Z，47157587 |

### 8.3 其它可佐证"生态活跃"的公共信号

- **oh-my-pi**（第三方发行版 fork，作者 can1357）：https://github.com/can1357/oh-my-pi ，缘起博文 https://blog.can.ac/2026/02/12/the-harness-problem/ （2026-02-12）。HN 上 infruset（2026-02-24T22:46:35Z，47144468）："I use it as a daily driver but I also love pi."
- **lazypi**（开箱即用配置发行版）：https://lazypi.org/ ，2026-07-09 上 HN，**151 分 / 74 条评论**（HN id 48847407）。
- 其它围绕 pi 的 Show HN：`pi-openwiki`（LangChain，2026-07-06）、`pi-auto-reviewer`（2026-06-12）、`pi-statusbar` macOS 状态栏（2026-02-20）、`pi-session-manager` 图形会话管理器（2026-02-26）、`PiPulse` iOS 远程控制（2026-03-02）。
- 本地模型圈也在用：horsawlarway，2026-06-15T17:44:54Z（48544680）——"I replaced a $100/m subscription to claude in favor of running pi harness pointed at unsloth studio, using both qwen ... and gemma"。

> **公开讨论覆盖面说明**：Reddit 侧未能通过本次检索找到高质量、可引用的 pi 专题讨论帖（搜索结果多为聚合站/SEO 站）。**如需 Reddit 引用请标注"未找到"，不要编造。** 目前 pi 的公共讨论主要集中在 **Hacker News** 与 **X**，以及官方 Discord（https://discord.com/invite/3cU7Bz4UPx ，未公开索引）。

---

## 9. 可以直接上 PPT 的「极客爽点」（10 条，每条附证据）

> 建议每条一页，左边一句话，右边引原文/代码。

**① 它敢在 README 第一段就说"我不做权限系统"，并给你三条容器化替代路径。**
> "Pi does not include a built-in permission system... If you need stronger boundaries, containerize or sandbox Pi."
> 证据：`pi-mono/README.md:39-45`；理由见 `packages/coding-agent/docs/security.md:31-35`（"A partial in-process sandbox would be easy to misunderstand as a security boundary"）

**② 一张"我们刻意不做什么"的清单，比任何 feature list 都圈粉。**
> No MCP / No sub-agents / No permission popups / No plan mode / No built-in to-dos / No background bash
> 证据：`packages/coding-agent/README.md:495-505`
> 提交 HN 的人就是被这段打动的：kristianpaul，2026-02-25，HN id 47154031

**③ "self extensible" 是可验证的闭环：agent 读自己的文档 → 写扩展 → 调 `reload_runtime` → 当场多一个工具。**
> 证据链：`src/core/system-prompt.ts:131-138`（系统提示写死自身文档绝对路径）→ `package.json:27-34`（docs/examples 随 npm 发布）→ `docs/extensions.md:1301-1332`（官方给出 LLM 可调用的 `reload_runtime` 工具代码）

**④ 每份可扩展文档的第一行都是"叫 pi 自己写"。**
> `docs/extensions.md:1` / `docs/skills.md:1` / `docs/tui.md:1` / `docs/themes.md:1` / `docs/prompt-templates.md:1` / `docs/sdk.md:1`
> 根 README:24 更狠——"you can also **ask the agent to explain itself**"

**⑤ 有人真的让 pi 给自己长出了一套权限系统。**
> "I just told PI to **generate itself** a `permissioned_*` equivalents of read,write,bash,edit... Default read,edit,write,bash are disabled. It seems to work really good."
> 证据：HN 用户 self_awareness，2026-02-26T17:48:03Z，https://news.ycombinator.com/item?id=47169421
> —— **"没有权限系统"因此不是缺失，而是把权限系统降级成了一次 prompt。**

**⑥ Session 是 JSONL 树（`id`/`parentId`），可原地分叉、可换模型续接、可 `jq`、可开源。**
> "Session entries form a tree structure via `id`/`parentId` fields, enabling in-place branching without creating new files."
> 证据：`packages/coding-agent/docs/session-format.md:3`；`/tree` `/fork` `/clone` 对照表 `docs/sessions.md:118-127`
> 用户评价：jauntywundrkind，2026-02-25，HN id 47147023——"Pi has sessions. And it has a full session tree & forking. **This is one of my favorite things, in all harnesses.**"

**⑦ 同一条 session 里热切模型——2026 年 7 月最热的"session 可携带性"话题的现成答案。**
> "Sessions are locked into Codex and Claude Code so you can't take a session with you. **Pi solves that since they all stay Pi sessions and you can change models in the same session.**"
> 证据：theturtletalks，2026-07-31T17:03:57Z，https://news.ycombinator.com/item?id=49125819
> 背景文：Earendil《The Session You Cannot Take With You》，2026-07-30，https://earendil.com/posts/session-portability/ （HN 733 分 / 212 评，id 49118781）

**⑧ `.npmrc` 里那两行，就是一份供应链态度声明。**
```
save-exact=true
min-release-age=2
```
> 证据：`pi-mono/.npmrc:1-2`；配套还有：直接依赖全部 pin、发布包内置 `npm-shrinkwrap.json`、pre-commit 拦 lockfile、`--ignore-scripts` 全链路、依赖 lifecycle script 白名单强制评审、npm OIDC trusted publishing、release 源码带 SHA256SUMS 可复现二进制
> 证据：`pi-mono/README.md:75-87`、`AGENTS.md:39-43`、`AGENTS.md:156`

**⑨ 依赖表少到可以整个念出来：TUI 框架 2 个依赖，protocol 1 个，根 devDeps 只有 10 个。**
> `packages/tui/package.json`：`get-east-asian-width` + `marked`（一个 14,184 行、带差分渲染的终端 UI 框架）
> `packages/protocol/package.json`：只有 `typebox`（CBOR 编解码器手写 RFC 8949 子集）
> 选型也很挑：TypeBox 而非 Zod、`tsgo` 而非 tsc、biome、只用 erasable TypeScript 语法（`AGENTS.md:20`）

**⑩ 作者把自己 627 段真实工作 session（224.8 MB）倒到 HuggingFace，理由是"别再拿玩具 benchmark 说事"。**
> "Public OSS session data helps improve coding agents with **real-world tasks, tool use, failures, and fixes instead of toy benchmarks.**"
> 证据：`pi-mono/README.md:89-104`；数据集 https://huggingface.co/datasets/badlogicgames/pi-mono （627 个 `.jsonl`、224.8 MB、188 likes、近 30 天 1,337 次下载，创建于 2026-04-06，抓取于 2026-08-01）
> 脱敏三层防护工具：https://github.com/badlogic/pi-share-hf

**（备选 ⑪）新贡献者的 issue 和 PR 默认自动关闭——而这条在极客圈居然是加分项。**
> "All issues and PRs from new contributors are auto-closed by default."（`pi-mono/README.md:11`、`CONTRIBUTING.md:23`）
> "**You must understand your code.** ... Using AI to write code is fine. Submitting AI-generated slop without understanding it is not."（`CONTRIBUTING.md:15-17`）
> 反面证据也要给：neop1x，2026-02-25，HN id 47159577——抱怨"can't submit because of Pi's OSS vacation BS"

**（备选 ⑫）AGENTS.md 里有一份专为"多个 agent 同时在同一个工作目录里干活"写的 git 规范。**
> "Multiple pi sessions may be running in this cwd at the same time... Stage explicit paths; **never `git add -A` / `git add .`**. Never run `git reset --hard`, `git checkout .`, `git clean -fd`, `git stash`, `git commit --no-verify`."
> 证据：`pi-mono/AGENTS.md:47-59`

---

## 10. 待核实 / 分歧 / 引用陷阱

1. **X 帖日期**：`x.com` 对本工具返回 402，无法直读。本文中 4 条推文日期由 snowflake ID 反解（方法可复现），**标记为待核实**，上台前建议人工点开确认。
2. **"1/100th the size of OpenClaw, 95% of the functionality"**：这是 HN 用户 fny 的**主观说法**（2026-02-15，id 47029074），非实测。引用时必须说明是用户评价。
3. **本地 LOC 统计口径**：110,436 行是 `packages/*/src` 下 `.ts/.tsx` 的原始行数（含注释与空行），未去除生成文件（`models.generated.ts` 仅 118 行，影响可忽略）。**不要说成"有效代码行"**。
4. **contributor = 250**：GitHub contributors 接口对超大仓库有 500 上限；250 未触顶，应为实数，但仍建议标注"GitHub 统计口径"。
5. **⚠️ 引用陷阱**：在 HN thread 47143754 中有一条 `saberience` 的评论抱怨"possibly the worst rust code I've seen in my life... files with 5000 to 10000 lines"。**这条不是在说 pi**（pi 是 TypeScript 写的），是在说该子线程里的另一个项目。**切勿引用为对 pi 的批评。**
6. **Reddit 讨论**：本次检索未找到可引用的 Reddit 原帖。若演讲需要"多平台反响"，请如实说明**公开讨论集中在 HN 与 X**，不要虚构 Reddit 引用。
7. **"self extensible" 的官方措辞边界**：这个词只出现在 **仓库根 README.md:15**。pi.dev 首页用的是 "aggressively extensible" / "Primitives, not features"，`earendil.com` 的公告里没有出现该词。演讲时若说"官方自称 self extensible"，出处应指仓库 README，而非官网。
8. **HuggingFace 数据集的"最后更新"**：HF API 给出 `lastModified = 2026-04-06T13:10:36Z`，与页面上"最近 session 时间戳"（2026-01 起）是两个不同的概念，别混用。README 说作者"regularly publish"，但**数据集元数据显示自 2026-04-06 后未再更新**——若要强调"持续公开"，需要重新核实。
9. **星标 81,525 是 2026-08-01 的快照**，且仓库已由 `badlogic/pi-mono` 迁至 `earendil-works/pi`（旧链接 301 跳转，README 与文档里两种路径混用）。

---

## 11. 关键链接清单

**一手**
- 仓库：https://github.com/earendil-works/pi （旧：https://github.com/badlogic/pi-mono ）
- 官网：https://pi.dev ｜ 文档：https://pi.dev/docs/latest ｜ 包目录：https://pi.dev/packages
- npm：https://www.npmjs.com/package/@earendil-works/pi-coding-agent
- 公开 RFC：https://rfc.earendil.com/keyword/pi/
- Discord：https://discord.com/invite/3cU7Bz4UPx

**作者/公司发文**
- Mario Zechner《What I learned building an opinionated and minimal coding agent》，2025-11-30：https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
- Mario Zechner《What if you don't need MCP?》，2025-11-02：https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/
- Armin Ronacher《Mario and Earendil》，2026-04-08：https://lucumr.pocoo.org/2026/4/8/mario-and-earendil/
- Earendil《Announcing Pi & Lefos》，2026-04-08：https://earendil.com/posts/announcing-pi-and-lefos/
- Earendil《The Session You Cannot Take With You》，2026-07-30：https://earendil.com/posts/session-portability/

**社区讨论**
- HN《Pi – A minimal terminal coding harness》，2026-02-24，608 分/306 评：https://news.ycombinator.com/item?id=47143754
- HN《The session you cannot take with you》，2026-07-31，733 分/212 评：https://news.ycombinator.com/item?id=49118781
- HN《Opinionated and easy Pi.dev configuration》(lazypi)，2026-07-09，151 分/74 评：https://news.ycombinator.com/item?id=48847407
- OpenAI Codex for Open Source（点名 pi）：https://developers.openai.com/community/codex-for-oss

**数据与工具**
- HuggingFace 数据集：https://huggingface.co/datasets/badlogicgames/pi-mono
- pi-share-hf：https://github.com/badlogic/pi-share-hf
- 第三方发行版：https://github.com/can1357/oh-my-pi ｜ https://lazypi.org/
- 容器化：Gondolin https://github.com/earendil-works/gondolin ｜ NVIDIA OpenShell https://docs.nvidia.com/openshell/about/overview

**本地素材**
- `/Users/nongjiawu/playground/research/pi/pi-mono/`（v0.83.0 源码 + 文档）
- `/Users/nongjiawu/playground/research/pi/analysis/raw/01-pi-agent-ai-core.md`（ai/agent 内核）
- `/Users/nongjiawu/playground/research/pi/analysis/raw/02-pi-coding-agent-tui.md`（工具集/系统提示/session/压缩/扩展层）
- `/Users/nongjiawu/playground/research/pi/analysis/raw/03-pi-protocol-server-storage.md`（protocol/server/client/storage）
