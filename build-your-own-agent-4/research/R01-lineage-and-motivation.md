# R01 — 灵感来源、项目动机、血统与体量

> 调查对象：`/Users/overkazaf/playground/research/re-agent`（0xAF-Re）
> 调查方式：只读。git / wc / find / grep / 读文件。**未运行二进制，未联网，未修改仓库。**
> 证据等级标注：**[A]** = 本地亲自执行命令验证；**[B]** = 项目文档中的声明，未独立验证；**[C]** = 推断。

---

## 1. 仓库身份（Repo Identity）

| 项 | 值 | 等级 |
| --- | --- | --- |
| 项目名 | 0xAF-Re（二进制名 `0xaf`） | [A] |
| Go module path | `github.com/overkazaf/re-agent` | [A] |
| go.mod 声明 Go 版本 | `go 1.22` | [A] |
| 文档声明最低 Go 版本 | **Go 1.21 或更新**（1.21 起工具链自动拉取所需版本） | [B] |
| License | MIT，`Copyright (c) 2026 overkazaf` | [A] |
| HEAD commit | `926e6159b3139a0591e8985657660a863ae767c7` | [A] |
| HEAD 日期 | `2026-07-31 06:06:31 +0800` | [A] |
| HEAD message | `docs: state the Go version requirement and add a worked case` | [A] |
| 总 commit 数 | **24** | [A] |
| 首个 commit | `cf07969` · `2026-07-27 03:00:00 +0800` · `0xAF-Re: a reverse engineering and CTF agent for the terminal` | [A] |
| 作者 | **唯一作者** `overkazaf <overkazaf@gmail.com>`，24/24 commit | [A] |
| 分支 | `main`（+ 一条远程 `docs/install-requirements-and-worked-case`） | [A] |
| Tags | `v0.1.1` `v0.1.2` `v0.1.3` `v0.1.4` `v0.1.5` | [A] |
| 当前发布版本 | **v0.1.5**（README 建议 `go install ...@v0.1.5` 固定版本） | [A] |

**命令与输出（节选）**

```
$ git log -1 --format='%H|%ad|%an|%ae|%s' --date=iso
926e6159b3139a0591e8985657660a863ae767c7|2026-07-31 06:06:31 +0800|overkazaf|overkazaf@gmail.com|docs: state the Go version requirement and add a worked case

$ git rev-list --count HEAD
24

$ git shortlog -sne --all
    24	overkazaf <overkazaf@gmail.com>

$ cat go.mod
module github.com/overkazaf/re-agent
go 1.22
require golang.org/x/term v0.18.0
require golang.org/x/sys v0.18.0 // indirect
```

### 1.1 依赖极简（这是 slide 级事实）

**整个项目只有 1 个直接外部依赖：`golang.org/x/term v0.18.0`**（`golang.org/x/sys` 是它的 indirect 传递依赖）。
`go.sum` 只有 4 行。README 自己也把这点当卖点：

> **Single-file install feel:** one static binary, one Go dependency, no Node or browser runtime in the critical path.
> — `README.md:109-110` [A/B]

> **安装像单文件工具:** 一个静态二进制，一个 Go 依赖，关键路径不需要 Node 或浏览器 runtime。
> — `README.zh-CN.md:95` [A/B]

### 1.2 开发节奏（时间线）

24 个 commit 全部落在 **2026-07-27 → 2026-07-31**，即 **5 天**。tag 节奏：

| tag | 日期 | commit |
| --- | --- | --- |
| v0.1.1 | 2026-07-28 | `07cc49b` |
| v0.1.2 | 2026-07-28 | `1198918` |
| v0.1.3 | 2026-07-29 | `9cefd22` |
| v0.1.4 | 2026-07-29 | `d1623de` |
| v0.1.5 | 2026-07-30 | `78fb781` |

**取证观察 [A]：** 24 个 commit 中有 **14 个** 的 author date 与 committer date 完全等于 `03:00:00 +0800`（`cf07969`、`cdcd1e2`、`18e58bf`、`27647e0`、`af32e97`、`f74e45e`、`d75ebad`、`637ea22`、`07cc49b`、`29e7b21`、`1198918`、`c1077f2`、`1dfde31`、`494cacd`）。整点秒级 000 的时间戳在 14 个 commit 上重复出现，说明这批历史是**事后整理/重写过的**（rebase 或人工设定日期），而非自然提交流。剩下 10 个（`6cf789a` 23:51:44、`fd9b632` 23:51:31、`e4e74ac` 07:15:53 等）带真实时分秒。**[C]** 结论：仓库公开时做过一次历史重排，把开发早期的实际提交压缩成了一条干净的叙事线。

**完整 commit 列表 [A]**（可直接做时间线 slide）：

```
926e615 2026-07-31 docs: state the Go version requirement and add a worked case
78fb781 2026-07-30 fix: stabilize live repl state                    ← v0.1.5
d1623de 2026-07-29 feat: add proxy capture toolkit                   ← v0.1.4
9cefd22 2026-07-29 chore: bump version to v0.1.3                     ← v0.1.3
703383e 2026-07-29 feat: add angr and frida templates
e66a014 2026-07-29 docs: add developer highlights
aded077 2026-07-29 docs: clarify workflow policy boundaries
e4e74ac 2026-07-29 docs: explain workflow evidence mode
494cacd 2026-07-28 docs: describe project motivation
1dfde31 2026-07-28 docs: add bilingual documentation pages
c1077f2 2026-07-28 docs: simplify bilingual readme
1198918 2026-07-28 feat: add delegated caveman workflow              ← v0.1.2
29e7b21 2026-07-28 docs: add bilingual onboarding use cases
07cc49b 2026-07-28 chore: release v0.1.1                             ← v0.1.1
637ea22 2026-07-28 feat: add researcher role prompts
6cf789a 2026-07-28 fix: make !cd move the workspace
fd9b632 2026-07-28 fix: keep the live HUD aligned in raw mode
d75ebad 2026-07-28 fix: tighten reverse skill workflows
f74e45e 2026-07-28 feat: show runtime commit hash
af32e97 2026-07-28 fix: merge embedded and local skills
27647e0 2026-07-28 docs: embed group qr in banner
18e58bf 2026-07-28 docs: add marketing asset gallery
cdcd1e2 2026-07-28 feat: add workflow modes and live task queue
cf07969 2026-07-27 0xAF-Re: a reverse engineering and CTF agent for the terminal
```

**注意 24 个 commit 里有 9 个是 `docs:`**（37.5%）。这个项目的文档投入密度异常高 —— 也解释了为什么会有 07-vs-oh-my-pi 这种对比图（见 §4）。

---

## 2. 体量（Scale）—— 全部实测

### 2.1 Go 代码总量

```
$ find . -name '*.go' -not -path './.git/*' | wc -l
83

$ find . -name '*.go' -not -path './.git/*' -print0 | xargs -0 wc -l | tail -1
   24229 total

$ find . -name '*.go' -not -name '*_test.go' -not -path './.git/*' -print0 | xargs -0 wc -l | tail -1
   20672 total

$ find . -name '*_test.go' -print0 | xargs -0 wc -l | tail -1
    3557 total

$ find . -name '*_test.go' | wc -l
25
```

| 指标 | 实测值 | 等级 |
| --- | --- | --- |
| Go 文件总数 | **83** | [A] |
| Go 总行数 | **24,229** | [A] |
| 非测试代码行数 | **20,672** | [A] |
| 测试文件数 | **25** | [A] |
| 测试代码行数 | **3,557**（占 14.7%） | [A] |

### 2.2 逐包 LOC（`internal/*`，实测）

| 包 | .go 文件数 | 行数 | 占比 | 职责（据 `docs/ARCHITECTURE.md:34-51`） |
| --- | ---: | ---: | ---: | --- |
| `internal/ui` | 13 | **5,608** | 23.1% | 主题/宽度计算、live pane、HUD、dataflow 图、trace、plan box、markdown、palette、splash |
| `internal/tools` | 10 | **4,395** | 18.1% | 24 个内置工具注册表、子进程 runner、输出溢出预算 |
| `internal/app` | 16 | **4,084** | 16.9% | 参数解析、REPL、slash 命令、队列控制器、raw-mode 行编辑器、`--print` |
| `internal/providers` | 7 | **2,474** | 10.2% | 5 个 provider adapter、CLI JSONL 规范化、usage 提取 |
| `internal/core` | 8 | **2,086** | 8.6% | AgentLoop、LoopEvent、context budget、append-only session、`!` shell escape |
| `internal/knowledge` | 3 | 879 | 3.6% | RE 语料检索、context 打包、引用校验 |
| `internal/config` | 2 | 597 | 2.5% | `agent.config.json` 合并、UI 偏好、reasoning effort |
| `internal/workflow` | 3 | 584 | 2.4% | `off`/`auto`/`specialist`/`caveman` 模式解析 |
| `internal/auth` | 2 | 566 | 2.3% | 凭据发现、CLI auth 探测、FilteredEnv |
| `internal/types` | 2 | 545 | 2.2% | 全部数据模型；**故意零内部依赖** |
| `internal/mcp` | 2 | 507 | 2.1% | stdio JSON-RPC 2.0 客户端 + tool 包装 |
| `internal/security` | 4 | 459 | 1.9% | 命令安全模式 + tier × mode 审批门 |
| `internal/assets` | 2 | 297 | 1.2% | `go:embed` prompts + skills、项目根解析 |
| `internal/skills` | 2 | 280 | 1.2% | skill 加载与 system prompt 目录构建 |
| `internal/plan` | 2 | 283 | 1.2% | 任务列表 tracker |
| `internal/util` | 1 | 195 | 0.8% | 参数强转、路径包含、Clip/Truncate |
| `internal/buildinfo` | 2 | 126 | 0.5% | 版本 / commit hash |
| **internal 小计** | **81** | **23,965** | | |
| `cmd/0xaf/main.go` | 1 | **17** | | 入口只有 17 行 |
| `cmd/import-knowledge/main.go` | 1 | 247 | | 知识库导入工具 |

**测量命令 [A]：**
```
$ for d in internal/*/; do n=$(find "$d" -name '*.go' | wc -l); l=$(find "$d" -name '*.go' -print0 | xargs -0 cat | wc -l); echo "$d|$n|$l"; done
```

**Slide 级观察 [A/C]：**
- **UI 是最大的包（5,608 行，23%），比 agent loop 本身（`core` 2,086 行）大 2.7 倍。** 这直接印证 §4 的自述："effort went into visibility"。
- `cmd/0xaf/main.go` 只有 **17 行** —— 所有逻辑都在 `internal/app`。
- `internal/types` 545 行且**故意不 import 任何内部包**：
  > **`types` imports nothing.** It is the only package every layer may import, so it must be a leaf.
  > — `docs/ARCHITECTURE.md:54-56` [A]

### 2.3 Skills / Prompts / Docs / Demos

| 资产 | 数量 | 命令/依据 | 等级 |
| --- | ---: | --- | --- |
| Skills 目录数 | **33** | `ls skills \| wc -l` | [A] |
| SKILL.md 文件数 | 34（33 个 skill + `jsvmp-analysis` 等含额外 md） | `find skills -name '*.md' \| wc -l` | [A] |
| skills 目录总文件数 | 42 | `find skills -type f \| wc -l` | [A] |
| Skills markdown 总行数 | **14,353 行 / 397,723 字节（≈388 KB）** | `wc -l` / `wc -c` | [A] |
| 内嵌 skills 数 | **33，与 `skills/` 目录逐字一致** | `diff <(ls skills) <(ls internal/assets/embedded/skills)` → 无差异 | [A] |
| Prompts 文件 | **4**：`prompts/system.md` + `roles/{planner,executor,researcher}.md` | `find prompts -type f` | [A] |
| system prompt 行数 | **65 行 / 3,505 字节** | `wc -l -c prompts/system.md` | [A] |
| role prompt 行数 | planner 9 / executor 11 / researcher 9 | `wc -l prompts/roles/*.md` | [A] |
| 文档 Markdown | 4 篇：`README.md`(543) `README.zh-CN.md`(493) `docs/ARCHITECTURE.md`(1,270) `docs/ARCHITECTURE.zh-CN.md`(305) | `wc -l` | [A] |
| docs/ 总文件数 | 59（含 11 SVG cards + 11 PNG、3 casts、7 diagrams、14 shots、2 index.html） | `find docs -type f \| sort` | [A] |
| 架构图 diagrams | **7 张 SVG**：01-module-graph、02-one-turn、03-context-budget、04-approval-gate、05-live-pane、**06-oh-my-pi**、**07-vs-oh-my-pi** | [A] |
| Demos | **2 个**：`demos/welcome/`、`demos/reverse-lab/` | `find demos -type f` | [A] |
| 内置工具数 | **24** | `grep -rhoE 'Name:\s+"[a-z_]+"' internal/tools/*.go \| sort -u \| wc -l` = 24；`docs/ARCHITECTURE.md:46` 也写 "The 24-tool built-in registry" | [A] |
| Providers | **5 类适配器**（anthropic / openai-responses / openai-chat / cli-tmux / mock），`config.example.json` 里列了 **9 个具体 route** | [A] |

**24 个工具全名 [A]**（`internal/tools/*.go`）：
```
apk_inspect  binary_mitigations  carve_artifacts  ctf_decode  ctf_triage
entropy_scan  extract_symbols  file_info  find_bytes  frida_hook_template
grep  hash_file  hexdump  knowledge_read  knowledge_search  list_files
list_skills  read_file  read_skill  reverse_toolkit  run_command  strings
update_plan  write_file
```

**33 个 skills 全名 [A]**：
```
analyze-apk  analyze-sign  analyze-so  android-apk-frida  api-signature-crack
apk-so-analyzer  binary-patching  browser-hook  capstone-disassembler
crypto-identification  ctf-first-pass  deobfuscate  frida-hook-workflow  gdb
ghidra  jadx  jsvmp-analysis  keystone-assembler  native-pwn-re
ollvm-deobfuscation  proxy-capture  qemu-emulator  qiling-emulator
radare2-reverse  re-planner  re-writeup  so-string-deobfuscation
unicorn-emulator  unidbg  vmp-restore  wasm-reverser  web-crypto-analyzer
web-wasm-crypto
```

最大的 5 个 skill [A]：`re-writeup` 947 行、`analyze-sign` 750、`radare2-reverse` 733、`gdb` 706、`ghidra` 670。

**config.example.json 里的 9 个 route [A]**（`config.example.json:10-99`）：
Codex CLI tmux / Claude Code tmux / Codex API (`gpt-5.3-codex`) / Claude API Opus 4.8 / Grok Build 4.5 (`grok-4.5`) / Grok Build CLI tmux / DeepSeek / GLM · Z.AI / Mock Provider。

---

## 3. 动机（Motivation）—— 原文引用

### 3.1 "Why 0xAF-Re" / "为什么用 0xAF-Re"

**英文原文（`README.md:53-84`）：**

> Reverse engineering is already a pipeline: `file`, `strings`, `entropy`, r2, JADX, Frida, a scratch script, a note somewhere. The slow part is rarely any single tool — it is holding the thread across all of them, and re-deriving what you already knew two hours ago.
>
> 0xAF-Re keeps that pipeline and adds a planner on top of it. Five things it does that a chat window bolted onto a terminal does not:
>
> 1. **The cheap path stays free.** `/scan`, `/hex`, `/entropy`, `/carve`, `/decode`, `/mitigations`, `/apk` are direct local tools. No model, no token, no latency. You only spend a model when you actually want one to think.
> 2. **Two seats, not one.** A planner model writes the route; a separate executor model drives the tools. Give the planning to a strong reasoner and the tool calls to something cheap and fast — or point them at different vendors entirely, at runtime, with `/planner` and `/executor`.
> 3. **Cautious models can still work the case.** `caveman` mode splits one request into a planner phase and an isolated executor phase that sees only a bounded local-evidence packet. Ordinary providers that would otherwise stall on RE phrasing keep collecting file facts.
> 4. **You watch it work, and you can steer mid-turn.** Plan rows, tool calls, reasoning, tokens, and timings render live. `/think expand`, `/tasks collapse`, `/queue edit` and `/model` all take effect **while the turn is still running** — you do not have to kill a turn to redirect it.
> 5. **Nothing leaves the workspace by accident.** Reads are workspace-scoped; writes, network, and sensitive paths are off until you say otherwise; exec tier prompts before it runs. Every turn lands in a JSONL transcript you can diff, replay, and hand to someone else.
>
> And when the agent is the wrong tool for the next five minutes, `/r2 <file>` hands the terminal straight to radare2 and takes it back when you quit.

**中文原文（`README.zh-CN.md:52-76`）：**

> 逆向本来就是一条流水线：`file`、`strings`、熵扫描、r2、JADX、Frida、一个临时脚本、一份不知道存哪了的笔记。慢的地方很少是某一个工具本身，而是在这些工具之间**接住那根线**，以及两小时后重新推导一遍你早就知道的东西。
>
> 0xAF-Re 保留这条流水线，在它上面加一个规划者。相比"往终端里塞一个聊天框"，它多做五件事：
>
> 1. **省钱的那条路依然免费。** `/scan`、`/hex`、`/entropy`、`/carve`、`/decode`、`/mitigations`、`/apk` 都是直连本地工具。不过模型、不花 token、没有延迟。只有你真的想要一个脑子的时候才付费。
> 2. **两个座位，不是一个。** planner 模型写路线，executor 模型跑工具。把规划交给强推理模型、把工具调用交给便宜快速的——或者干脆指向两个不同厂商，运行中用 `/planner`、`/executor` 随时换。
> 3. **谨慎的模型也能干活。** `caveman` 模式把一次请求拆成 planner 阶段和隔离的 executor 阶段，后者只看到一个有边界的本地证据包。那些一见逆向措辞就卡住的普通 provider，照样能继续收集文件事实。
> 4. **过程可见，而且能中途改道。** plan 行、工具调用、推理、token、耗时全部实时渲染。`/think expand`、`/tasks collapse`、`/queue edit`、`/model` 都能**在这一轮还在跑的时候**生效——不需要杀掉当前 turn 才能调整方向。
> 5. **没有东西会意外离开工作区。** 读操作限定在工作区内；写盘、联网、敏感路径默认关闭；exec 级动作执行前先问。每一轮都落进 JSONL 记录，可 diff、可回放、可交给别人复核。
>
> 而当接下来五分钟里 agent 反而是碍事的那个，`/r2 <file>` 直接把终端交给 radare2，你退出时再还回来。

### 3.2 "Project Motivation" / "项目动机" —— 最关键的一段

这是全项目动机最赤裸的表述，**中英文措辞有显著差异，中文更直白**。

**英文（`README.md:121-136`）：**

> 0xAF-Re grew out of daily authorized RE/CTF work where **coding-agent risk controls tightened and general models became more cautious around reverse-engineering language**. The goal is not to hide intent. The agent keeps work local, authorized, and auditable, then improves the experience by splitting roles and composing models.
>
> - **Model composition:** use one model for planning, another for tool execution, and a researcher role for background context.
> - **Specialist routes:** GPT Cyber, Claude Code CVP, Grok, or similar security-research-friendly routes make `workflow auto` smoother.
> - **Ordinary-provider path:** caveman mode narrows the task into local evidence packets so cautious executors can still collect file facts safely.
> - **Roadmap:** local models and reproducible benchmark cases will be added so provider/workflow quality can be measured and improved over time.

**中文（`README.zh-CN.md:102-109`）：**

> 0xAF-Re 源于作者日常授权 RE/CTF 工作里的痛点：**CC 类 CLI 风控升级后，普通模型面对逆向语义也更容易过度谨慎，本地样本分析经常被打断**。这个项目**不做隐写、暗语或绕策略**，而是把工作限定在授权、本地、可审计范围内，再通过角色拆分和多模型组合改善体验。
>
> - **模型组合:** planner 负责路线，executor 负责工具，researcher 负责背景资料；三个角色可以接不同模型。
> - **专用订阅加成:** 如果有 GPT Cyber、Claude Code CVP、Grok 或类似更适配安全研究/逆向的 route，`workflow auto` 会更顺。
> - **普通 provider 也能跑:** caveman 模式把任务收窄成本地证据包，让谨慎的 executor 只收集文件事实。
> - **后续计划:** 加入本地模型和可复现评测样例，用样例结果衡量不同 provider/workflow 的效果并迭代。

**差异点 [A]：** 中文版点名了 **"CC 类 CLI 风控升级"**（CC = Claude Code），英文版模糊化成 "coding-agent risk controls tightened"。中文还加了英文没有的一句 **"不做隐写、暗语或绕策略"** —— 这是主动的合规声明。这段文字由 commit `494cacd docs: describe project motivation`（2026-07-28）一次性加入，同时改了 README.md(+19)、README.zh-CN.md(+11)、docs/index.html(+55/-18)、docs/index.zh-CN.html(+43/-2)。

### 3.3 "Developer Highlights" / "开发者亮点"

**英文（`README.md:102-119`）：**

> If you build agents, 0xAF-Re is a compact RE-focused reference implementation: one Go binary with provider routing, tool governance, live telemetry, prompt/skill overrides, queueing, and audit logs. **It is small enough to read, but opinionated enough to show the parts most agent demos skip.**
>
> - **Single-file install feel:** one static binary, one Go dependency, no Node or browser runtime in the critical path.
> - **Composable model seats:** planner, executor, and researcher can use different providers, models, and editable prompts.
> - **Evidence-first workflows:** specialist routes use GPT Cyber / CC CVP / Grok style subscriptions directly; caveman mode isolates ordinary executors to read-only local evidence packets.
> - **Visible agent loop:** HUD, trace lines, token/timing telemetry, task state, and JSONL sessions make each turn debuggable.
> - **Hackable surface area:** built-in RE tools, MCP tools, skills, knowledge import, project-local overrides, and runtime queue editing.

**中文（`README.zh-CN.md:89-100`）：**

> 如果你在做 agent，0xAF-Re 是一个足够小、但关键部件齐全的 RE 场景参考实现：单个 Go 二进制里包含 provider 路由、工具治理、实时遥测、prompt/skill 覆盖、任务队列和审计日志。**它不像 demo 那样只展示聊天，而是把 agent 真正落地时麻烦的部分也摊开。**

（此段由 commit `e66a014 docs: add developer highlights`，2026-07-29 加入，+21/+15 行。）

### 3.4 ARCHITECTURE.md 的定位陈述

> `0xaf` is a single static Go binary (`cmd/0xaf`, module `github.com/overkazaf/re-agent`) that drives reverse-engineering and CTF work from a terminal. It talks to five interchangeable model backends — Anthropic Messages, OpenAI Responses, OpenAI-compatible Chat, a local coding CLI driven inside a detached tmux session, and an offline mock — exposes a registry of local file/binary/CTF tools plus any MCP server's tools, records every message to an append-only JSONL transcript, and narrates the whole thing in an in-place terminal HUD. **Everything hangs off one function: `AgentLoop.Run` (`internal/core/agentloop.go:245`)**, a bounded `for turns < maxTurns` loop that on each pass compacts the transcript to the provider's context budget, sends one request, records the assistant reply, and — if the reply carried tool calls — runs each one through the approval gate and appends its result before looping again.
> — `docs/ARCHITECTURE.md:13-26` [A]

文档自设的证据标准（对做取证 slide 很有用）：

> Audience: someone about to extend or audit this binary. **Every claim here should be checkable against a file.** Anchors are `path:line` against the tree as committed.
> — `docs/ARCHITECTURE.md:5-7` [A]

### 3.5 它**故意不做**的事（deliberately NOT doing）

| 不做 | 原文依据 | 等级 |
| --- | --- | --- |
| 不做 hash-anchored 编辑 / 编辑 benchmark | "Writes are off until you ask — no anchoring, no edit benchmark — **deliberately**" `docs/diagrams/07-vs-oh-my-pi.svg` | [A] |
| 不做跨 session 长期记忆 | "Left behind: … cross-session memory"（同上） | [A] |
| 不做 LSP/DAP 语言服务层 | "There is no language server for a stripped binary"（同上） | [A] |
| 不自带 shell / coreutils | "Uses the host shell, and budgets what comes back"（同上） | [A] |
| 不做 per-toolchain 输出过滤器 | "`objdump -d` output is noise the same way every time; no per-toolchain filter earns its keep."（同上） | [A] |
| 不做 SDK / 插件体系 | "**No SDK to learn.** The extension surface is a file you can write in a text editor."（同上） | [A] |
| 不做隐写/暗语/绕策略 | "这个项目不做隐写、暗语或绕策略" `README.zh-CN.md:104`；"The goal is not to hide intent." `README.md:125` | [A] |
| 不提交 knowledge index | "The index is deliberately **not** committed: it points at files on the operator's own disk" `knowledge/README.md:7-8` | [A] |

---

## 4. 血统（Inspiration Lineage）—— 核心发现

### 4.1 最硬的证据：两张专门的对比图

仓库里有 **7 张架构 SVG**，其中 **2 张（29%）不是画自己，而是画别人和对比别人**：

- `docs/diagrams/06-oh-my-pi.svg` — 标题 **"oh-my-pi — the harness, as built"**
- `docs/diagrams/07-vs-oh-my-pi.svg` — 标题 **"Where the two diverge, and why"**

两张图都在**首个 commit `cf07969`（2026-07-27）**就已存在（`git log -- docs/diagrams/0{6,7}-*.svg` 只返回 `cf07969`）。**[A]** 也就是说：**对 oh-my-pi 的研究先于（或同步于）本项目的公开发布，是设计输入而不是事后比较。**

README 在 "More Docs" 和顶部 Links 里都显式挂了这两张图：
- `README.md:9` — `· [Comparison diagram](docs/diagrams/07-vs-oh-my-pi.svg)`
- `README.md:537-538` — `[oh-my-pi architecture note]` / `[0xAF-Re vs oh-my-pi]`
- `README.zh-CN.md:8, 488-489` — 同上，中文
**[A]**

### 4.2 参照对象身份

> **can1357/oh-my-pi** · a Bazel-built polyglot monorepo: **16 TypeScript packages, 9 Rust crates, a resident Python**. GitHub labels it "TypeScript" — the substrate is not.
> — `docs/diagrams/06-oh-my-pi.svg` 标题栏 [A/B]

> oh-my-pi · a coding agent　　vs　　0xAF-Re · this project · a reverse engineering agent
> — `docs/diagrams/07-vs-oh-my-pi.svg` [A]

> **oh-my-pi optimizes for changing code. 0xAF-Re optimizes for reading binaries. Almost every difference below follows from that one sentence.**
> — `docs/diagrams/07-vs-oh-my-pi.svg`（副标题）[A] ← **这是全项目最好的一句 slide 文案**

### 4.3 "What actually crossed over" —— 作者自述的借鉴清单（逐字）

> **Taken:** the single event-driven loop · output budgets as a first-class concern · structured results instead of parsed prose · one tool registry · MCP · tiered approval
>
> **Left behind:** hash-anchored edits · the LSP/DAP layer · cross-language workers · a custom shell and coreutils · cross-session memory · the Bazel monorepo
>
> Every item on the second line is excellent engineering that solves a problem this project does not have.
>
> **The honest summary: oh-my-pi is a platform and 0xAF-Re is a tool.** Its Rust substrate exists because a coding agent runs cargo and npm a thousand times a day and their output is the bottleneck. A reverse agent runs `strings` once and then stares at the result — **so the effort went into visibility, approval, and not lying about sources.**
> — `docs/diagrams/07-vs-oh-my-pi.svg` [A]

**"borrowed 6 / dropped 6" 这个对称结构是天然的 slide。** 而且 §2.2 的实测数据**独立验证了 "effort went into visibility"**：`internal/ui` 5,608 行 > `internal/core` 2,086 行 × 2.7。**[A+C]**

### 4.4 逐维度分歧表（图内原文摘要）

| 维度 | oh-my-pi | 0xAF-Re | 图内理由 |
| --- | --- | --- | --- |
| engineering shape | Bazel monorepo，三种语言；16 TS packages · 9 Rust crates · resident Python；仅 `coding-agent/src` 就 123 modules | One Go module, one binary；**64 files · 18,610 lines · 1 external dependency**；6.7 MB · ~6.7 ms cold start；prompts 与 skills 内嵌 | "Breadth is the point: it is a platform" vs **"Narrowness is the point: lab boxes rarely have a runtime, and you scp one file."** |
| shell & tool output | 自带 shell（`pi-shell` 封装 vendored brush = Rust 版 bash）+ 自己的 coreutils（`pi-uu-grep` / `pi-uu-diff` 基于 uutils）+ 按 toolchain 的 minimizer（cargo/git/go/jvm/npm，带 fixtures） | 用宿主 shell；进：shell-escape 分析；出：output budget；超限溢出到 artifact（head + tail + path） | "`objdump -d` output is noise the same way every time; no per-toolchain filter earns its keep." |
| writing to disk | `packages/hashline` hash 锚定编辑，写入前验证锚点；`typescript-edit-benchmark` 量化编辑准确率 | **写默认关闭**；无锚定、无编辑 benchmark（deliberately）；核心是 approval gate：tier × mode + 按工具覆盖 | "The subject is read-only. Building an edit-safety net for solve notes does not pay for itself." |
| context & memory | compaction 是独立 package（`snapcompact`）；memory 是子系统（`mnemopi`/`memories`/`memory-backend`/`autolearn`/`autoresearch`/`hindsight`） | **一个函数、两趟、一个下限**：`CompactHistory` 先削 tool body，再整段丢 exchange；**last-exchange floor —— 宁可超预算也不删当前 turn** | "Memory is the knowledge base instead, and it must cite entry ids or the UI calls it out." |
| model orchestration | 一个模型 fan-out 到 subagents；task tool 拆活，结果 schema 校验；`swarm-extension` 放大同一思路 | **两个厂商、两个座位、可运行中互换**：planner (codex, `--sandbox read-only`) · executor (claude)；`/planner /agent /executor /effort` 免重启 | "Parallelism is the lever: many workers, one mind." vs **"Vendor diversity is the lever: on a refusal, ask a different company."** |
| understanding the target | `src/lsp`（rename 走 `workspace/willRenameFiles`）、`src/dap` 真调试器、`pi-ast` 逐语言解析 | **"There is no language server for a stripped binary"**；24 个工具：triage · entropy · carve · symbols · mitigations · APK · Frida；`reverse_toolkit` 前置 radare2 · JADX · Ghidra · gdb · YARA · unidbg | "Ground truth is **recovered, not queried** — which is why every tool is also a slash command." |
| extending it | hooks / custom tools / SDK / swarm（`src/extensibility` 三种都有示例）；`.omp/skills` 自举自己的 skill 格式；`metaharness`/`stats`/`eval` 自测 | **一个 markdown 文件 + MCP**：`skills/<name>/SKILL.md`（磁盘版覆盖内嵌版）；任何 stdio MCP server 进同一 registry、同一审批门 | "**No SDK to learn.** The extension surface is a file you can write in a text editor." |

**[A]**（表格内容逐字来自 `docs/diagrams/07-vs-oh-my-pi.svg` 的 `<text>`/`<tspan>` 节点；提取命令见文末）

### 4.5 ⚠️ 数字打架：图里的自述体量对不上仓库实测

**图内声明 [B]：** `One Go module, one binary · 64 files · 18,610 lines · 1 external dependency · 6.7 MB · ~6.7 ms cold start`

**实测 [A]：**

| 口径 | 文件数 | 行数 |
| --- | ---: | ---: |
| 图内声明 | 64 | 18,610 |
| HEAD `926e615` 全部 .go | **83** | **24,229** |
| HEAD 非测试 .go | 58 | 20,672 |
| 首 commit `cf07969` 全部 .go | 66 | 19,936 |
| 首 commit `cf07969` 非测试 .go | 51 | 17,487 |

```
$ git ls-tree -r --name-only cf07969 | grep '\.go$' | wc -l
66
$ git ls-tree -r --name-only cf07969 | grep '\.go$' | while read f; do git show cf07969:"$f"; done | wc -l
19936
```

**结论 [A/C]：`64 files / 18,610 lines` 与仓库任何一个 commit 的任何一种口径都不完全吻合**，最接近的是首 commit（66 / 19,936）。合理推断：这个数字取自**打 commit 之前的工作区快照**，之后又改了几笔才提交。做 slide 时**应引用实测值 83 文件 / 24,229 行**，并可把这个"文档数字比代码慢半拍"当成一个诚实的细节讲。

**"6.7 MB / ~6.7 ms cold start" 无法验证 [B]** —— 任务约束禁止构建和运行二进制。只能标注为项目自述。

### 4.6 第二条血统线：Claude Code / Agent Skills 格式

**证据链 [A]：**

1. **skill 格式逐字照搬 Anthropic Agent Skills**：`skills/<name>/SKILL.md`，YAML frontmatter 只含 `name` + `description`。
   ```
   $ head -4 skills/ghidra/SKILL.md
   ---
   name: ghidra
   description: Use when analyzing binaries with Ghidra, decompiling functions, scripting headless analysis, ...
   ---
   ```
   `description` 以 **"Use when …"** 开头 —— 这是 Claude Code skill 的标准写法。
   解析器：`internal/skills/skills.go:148` `frontmatterRE = regexp.MustCompile('^([A-Za-z0-9_-]+):\s*(.*)$')`，`skills.go:153 parseFrontmatter`。

2. **progressive disclosure 机制被完整复刻，但项目里从未用这个词**（全仓 grep `progressive disclosure` 零命中，唯一 `progressively` 出现在 `skills/jsvmp-analysis/SKILL.md:604` 是无关正文）**[A]**。机制本身在 `internal/skills/skills.go:108-131`：
   ```go
   // SystemPrompt is the catalog appended to the agent's system prompt.
   func SystemPrompt(list []Skill) string {
       ...
       catalog = append(catalog, fmt.Sprintf("- %s: %s%s", skill.Name, skill.Description, tags))
       ...
       "Ask for `read_skill` when you need full instructions; use `list_skills` to inspect the catalog.",
   ```
   即：**system prompt 里只放 name + description（一行一个），完整正文由 `read_skill` 工具按需拉取。**

   **实测的披露比 [A]：**
   | 层 | 体量 |
   | --- | ---: |
   | 33 条 description（常驻 system prompt） | **7,258 字节** |
   | 33 个 SKILL.md 全文 | **397,723 字节** |
   | **压缩比** | **≈ 1 : 54.8（常驻只占 1.8%）** |
   | system.md 本体 | 3,505 字节 / 65 行 |

   这是整份研究里**最适合做一页 slide 的数字**：常驻 7 KB，按需 388 KB。

3. **skill 名单与 Claude Code 技能生态高度重合 [A/C]**：`ghidra`、`jadx`、`radare2-reverse`、`unidbg`、`frida-hook-workflow`、`capstone-disassembler`、`qiling-emulator`、`unicorn-emulator`、`jsvmp-analysis`、`re-writeup`、`re-planner`、`web-crypto-analyzer`、`ollvm-deobfuscation`、`so-string-deobfuscation`、`analyze-apk`、`analyze-so`、`analyze-sign`、`deobfuscate`、`binary-patching`、`browser-hook`、`keystone-assembler`、`vmp-restore`、`wasm-reverser`、`api-signature-crack`、`apk-so-analyzer`、`gdb`、`qemu-emulator`、`crypto-identification` —— 这批名字与 Claude Code 侧同名 skill 一一对应。**[C]** 结论：这 33 个 skill 是从作者已有的 Claude Code skills 库**平移过来**的，不是为本项目新写的。

4. **代码里残留 Claude Code 生态痕迹 [A]**：`cmd/import-knowledge/main.go:35` 的忽略列表
   ```go
   ".git": true, ".claude": true, ".agents": true, "node_modules": true,
   ```
   `.claude` 目录被显式列入忽略 —— 说明知识库语料来自带 `.claude/` 的工作区。

5. **两个 provider 直接就是 Claude Code 和 Codex 的 CLI [A]**：`config.example.json:29-35`
   ```json
   "type": "cli-tmux", "label": "Claude Code tmux", "model": "claude-code-cli",
   "cliUnsetEnv": ["ANTHROPIC_API_KEY", "ANTHROPIC_OAUTH_TOKEN"]
   ```
   即 0xAF-Re 把 Claude Code CLI 当成一个 backend，在 detached tmux 里驱动它。（`internal/providers/clitmux.go`，731 行，是 providers 里最大的文件。）

### 4.7 第三条线索：一个 TypeScript/Bun 前身的化石

**这是本次调查最意外的发现 [A]。**

`demos/` 下的说明文档里，运行命令**不是 Go 二进制，而是 Bun 跑 TypeScript**：

```
$ grep -rn 'bun src/cli.ts' demos/
demos/README.md:20:bun src/cli.ts --welcome
demos/README.md:21:bun src/cli.ts --workspace ./demos/welcome
demos/welcome/README.md:18:bun src/cli.ts --workspace ./demos/welcome \
demos/welcome/README.md:26:bun src/cli.ts --workspace ./demos/welcome \
demos/welcome/README.md:41:bun src/cli.ts --workspace ./demos/welcome --write \
```

但 **git 全历史中从未出现过任何 `.ts`/`.tsx` 文件**：
```
$ git log --all --diff-filter=A --name-only --format='' | sort -u | grep -E '\.(ts|tsx|js|json)$'
config.example.json
demos/welcome/chall.js
```
（`chall.js` 是 demo 靶子本身，不是源码。）

**[C] 推断：0xAF-Re 存在一个未进入这个 git 仓库的 TypeScript/Bun 版本前身（入口 `src/cli.ts`），当前 Go 仓库是 rewrite 后的产物，公开时重开了历史；`demos/*/README.md` 是唯一没被清理干净的化石。** 这与 §1.2 的时间戳异常（14 个 commit 同为 03:00:00）互相印证：仓库历史是重写过的。

**次要不一致 [A]：** `demos/welcome/README.md:11-12` 声明存在 `artifacts/session.log` 和 `artifacts/operator-notes.txt`，但 `ls -R demos/welcome` 只有 `README.md` 和 `chall.js` —— 因为 `.gitignore:8` 忽略了 `artifacts/`。demo 文档承诺的文件在 clone 后并不存在。

### 4.8 MCP：明确借用，且明确"不用 SDK"

> `internal/mcp/client.go` is a **from-scratch JSON-RPC 2.0 client over stdio**, newline-delimited — enough to **borrow another process's tools** (`ida-pro-mcp` being the one that matters here) **without an SDK**. Protocol version `2024-11-05`.
> — `docs/ARCHITECTURE.md:663-666` [A]

> MCP servers do not declare a tier, so every wrapped tool is `RiskWrite`, which is what the approval modes assume for anything that is not a read.
> — `docs/ARCHITECTURE.md:677-679` [A]

工具命名 `mcp__<server>__<tool>`，截断到 64 字符（OpenAI 兼容限制），**优先砍 server 那一半**，理由是"the tool name is what the model reasons about"（`docs/ARCHITECTURE.md:672-676`）。`internal/mcp` 只有 **507 行 / 2 个文件**就完成了整个 MCP 客户端。**[A]**

### 4.9 各"血统词"grep 命中统计 [A]

| 关键词 | 仓库命中情况 |
| --- | --- |
| `oh-my-pi` | 2 个 SVG 文件 + README.md:9,537,538 + README.zh-CN.md:8,488,489 |
| `can1357` | 1 次，`docs/diagrams/06-oh-my-pi.svg` 标题栏（作者归属） |
| `claude code` / `claude-code` | `config.example.json:30-31`、README.md:131、README.zh-CN.md:97,107 |
| `codex` | `config.example.json` 6 处、README 多处（planner 默认 route）、`internal/ui/ui_test.go` 大量测试 fixture |
| `grok` | `config.example.json:53-66`（两个 route：API 与 CLI tmux）、README.md:113,131,398 |
| `anthropic` | `internal/types/types.go:15 KindAnthropic`、`config.example.json:46-50` |
| `MCP` | `internal/mcp/`（507 行）、`docs/ARCHITECTURE.md` §10、README skills 章节 |
| `SKILL.md` | 16 处，含 `internal/skills/skills.go` 与 ARCHITECTURE §13 |
| `progressive disclosure` | **0 次**（机制存在，术语未用） |
| `pi` / `oh-my-pi` 之外的 pi 引用 | 无（`pi-shell`/`pi-uu-grep` 等仅出现在描述 oh-my-pi 的两张 SVG 内） |

---

## 5. 为什么是 Go

### 5.1 明确陈述的理由

**唯一一处直白的"为什么"，在对比图里 [A]：**

> One Go module, one binary
> 64 files · 18,610 lines · 1 external dependency
> 6.7 MB · ~6.7 ms cold start · prompts and skills embedded
> **Narrowness is the point: lab boxes rarely have a runtime, and you scp one file.**
> — `docs/diagrams/07-vs-oh-my-pi.svg` [A]

> Its Rust substrate exists because a coding agent runs cargo and npm a thousand times a day and their output is the bottleneck. **A reverse agent runs `strings` once and then stares at the result** — so the effort went into visibility, approval, and not lying about sources.
> — 同上 [A]

README 侧的表述（更保守）：
> **Single-file install feel:** one static binary, one Go dependency, **no Node or browser runtime in the critical path.** — `README.md:109-110` [A]
> **安装像单文件工具:** 一个静态二进制，一个 Go 依赖，**关键路径不需要 Node 或浏览器 runtime。** — `README.zh-CN.md:95` [A]

**[C] 归纳三条理由：**
1. **实验机没有 runtime。** 逆向工作常在隔离/一次性的 lab box 上，装不了 Node/Python 环境，`scp` 一个文件最省事。
2. **性能不是瓶颈，可见性才是。** 编码 agent 的瓶颈是工具输出噪声（所以 oh-my-pi 下沉到 Rust）；逆向 agent 跑一次 `strings` 然后盯着看 —— 所以投入去了 UI/审批/溯源（实测 `internal/ui` 5,608 行验证了这点）。
3. **`go:embed` 让 prompts + 33 个 skills（388 KB markdown）打进同一个二进制**，安装物只有一个文件。（`internal/assets/assets.go:17` `//go:embed embedded/prompts embedded/skills`）

### 5.2 Makefile：确实是静态 + 交叉编译

`Makefile` 全文关键部分 [A]：

```make
LDFLAGS := -s -w

build:
	go build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o $(BIN)/0xaf ./cmd/0xaf
	go build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o $(BIN)/import-knowledge ./cmd/import-knowledge

# Puts `0xaf` on PATH. Assets are embedded, so the binary works from anywhere;
# set OXAF_RE_HOME to point it at a project checkout for live skills/knowledge.
install:
	go install -ldflags "$(LDFLAGS)" ./cmd/0xaf ./cmd/import-knowledge

# Static single binaries for the usual lab targets.
cross:
	GOOS=linux  GOARCH=amd64 CGO_ENABLED=0 go build -ldflags "$(LDFLAGS)" -o $(BIN)/0xaf-linux-amd64  ./cmd/0xaf
	GOOS=linux  GOARCH=arm64 CGO_ENABLED=0 go build -ldflags "$(LDFLAGS)" -o $(BIN)/0xaf-linux-arm64  ./cmd/0xaf
	GOOS=darwin GOARCH=amd64 CGO_ENABLED=0 go build -ldflags "$(LDFLAGS)" -o $(BIN)/0xaf-darwin-amd64 ./cmd/0xaf
	GOOS=darwin GOARCH=arm64 CGO_ENABLED=0 go build -ldflags "$(LDFLAGS)" -o $(BIN)/0xaf-darwin-arm64 ./cmd/0xaf
```

| 事实 | 值 | 等级 |
| --- | --- | --- |
| `CGO_ENABLED=0` | ✅ 仅在 `cross` target 上显式设置（`build`/`install` 未设，走默认） | [A] |
| `-ldflags "-s -w"` | ✅ 剥符号表和 DWARF，缩小体积 | [A] |
| 交叉编译目标 | **4 个**：linux/amd64、linux/arm64、darwin/amd64、darwin/arm64 | [A] |
| **没有 Windows 目标** | 注释写 "the usual **lab** targets" | [A] |
| 资产内嵌 | Makefile 注释："Assets are embedded, so the binary works from anywhere; set `OXAF_RE_HOME` to point it at a project checkout for live skills/knowledge." | [A] |
| 二进制体积 | **未验证**（禁止构建）；项目自述 6.7 MB | [B] |
| 冷启动 | **未验证**；项目自述 ~6.7 ms | [B] |

覆盖机制 [A]：`internal/assets/assets.go` 的项目根解析顺序是 `$OXAF_RE_HOME` → 可执行文件目录 → cwd（向上走 6 层）（`docs/ARCHITECTURE.md:38`）。`internal/skills/skills.go:34-48` 先装载内嵌 33 个 skill，再用磁盘上的 `skills/<name>/SKILL.md` **同名覆盖**。commit `af32e97 fix: merge embedded and local skills` 就是修这个合并逻辑的。

---

## 6. 一页速查（Slide 备用数字表）

| 主题 | 数字 | 等级 |
| --- | --- | --- |
| 开发周期 | 2026-07-27 → 07-31，**5 天，24 commit，1 位作者** | [A] |
| 版本 | v0.1.5（5 个 tag，全在 3 天内） | [A] |
| Go 代码 | **83 文件 / 24,229 行**（非测试 20,672；测试 3,557 / 25 文件） | [A] |
| 外部依赖 | **1 个**（`golang.org/x/term`） | [A] |
| 最大包 | `internal/ui` **5,608 行（23%）**，是 `internal/core`（2,086）的 **2.7 倍** | [A] |
| 入口 | `cmd/0xaf/main.go` = **17 行** | [A] |
| 内置工具 | **24** | [A] |
| Skills | **33 个，14,353 行 / 388 KB markdown**，与二进制内嵌副本逐字一致 | [A] |
| Progressive disclosure 比 | 常驻 **7,258 B** : 按需 **397,723 B** ≈ **1 : 55** | [A] |
| Prompts | 4 个文件；system.md **65 行 / 3.5 KB** | [A] |
| Providers | 5 类适配器 / 9 个示例 route | [A] |
| MCP 客户端 | **507 行 / 2 文件**，from-scratch JSON-RPC 2.0，协议版本 `2024-11-05` | [A] |
| 交叉编译 | 4 个目标，`CGO_ENABLED=0`，`-s -w`，无 Windows | [A] |
| 架构图 | 7 张，其中 **2 张（29%）是画竞品/对比竞品** | [A] |
| 文档占比 | 24 个 commit 中 **9 个是 `docs:`（37.5%）** | [A] |
| 借鉴清单 | Taken 6 项 / Left behind 6 项（原文对称） | [A] |
| 数字打架 | 图里写 64 文件 18,610 行，实测 83 / 24,229 | [A] |
| TS 前身化石 | `demos/README.md:20` 仍写 `bun src/cli.ts --welcome`，而 git 史无任何 .ts | [A] |

---

## 7. 无法验证 / 需要标注为 [B] 的项

1. **二进制体积 6.7 MB、冷启动 ~6.7 ms** — 任务禁止构建/运行，只能引用项目自述（`docs/diagrams/07-vs-oh-my-pi.svg`）。
2. **oh-my-pi 侧的一切数字**（16 TS packages / 9 Rust crates / 123 modules / `pi-shell` 等包名）— 全部来自本仓库的 SVG 描述，**未访问 can1357/oh-my-pi 本体**（禁止联网）。做 slide 时应说明"这是 0xAF-Re 作者对 oh-my-pi 的描述"。
3. **"CC 类 CLI 风控升级"** — 项目的动机陈述，属主观体验，无法从代码验证。
4. **33 个 skill 来自作者的 Claude Code skills 库** — [C] 推断，依据是名称一一对应，未做逐字 diff（Claude Code skill 库不在本仓库内）。
5. **TypeScript/Bun 前身** — [C] 推断，依据是 `demos/*/README.md` 的 `bun src/cli.ts` 与 git 史无 .ts 的矛盾。

---

## 8. 附：本报告用到的关键命令

```bash
R=/Users/overkazaf/playground/research/re-agent

# 身份
git -C $R log -1 --format='%H|%ad|%an|%ae|%s' --date=iso
git -C $R rev-list --count HEAD
git -C $R shortlog -sne --all
git -C $R for-each-ref --sort=creatordate --format '%(refname:short)|%(creatordate:short)|%(objectname:short)' refs/tags
git -C $R log --format='%h|A:%ad|C:%cd|%s' --date=iso        # 时间戳取证

# 体量
find $R -name '*.go' -not -path '*/.git/*' | wc -l
find $R -name '*.go' -not -path '*/.git/*' -print0 | xargs -0 wc -l | tail -1
for d in $R/internal/*/; do n=$(find "$d" -name '*.go'|wc -l); l=$(find "$d" -name '*.go' -print0|xargs -0 cat|wc -l); echo "$d|$n|$l"; done
find $R/skills -name '*.md' -print0 | xargs -0 wc -l | tail -1
cat $R/skills/*/SKILL.md | wc -c
grep -h '^description:' $R/skills/*/SKILL.md | wc -c
grep -rhoE 'Name:\s+"[a-z_]+"' $R/internal/tools/*.go | sed 's/.*"\(.*\)"/\1/' | sort -u | wc -l
diff <(ls $R/skills) <(ls $R/internal/assets/embedded/skills)

# 血统
grep -oE '>[^<]{2,}</text>|>[^<]{2,}</tspan>' $R/docs/diagrams/07-vs-oh-my-pi.svg | sed 's/^>//;s/<\/te.*//;s/<\/ts.*//'
grep -oE '>[^<]{2,}</text>|>[^<]{2,}</tspan>' $R/docs/diagrams/06-oh-my-pi.svg     | sed 's/^>//;s/<\/te.*//;s/<\/ts.*//'
git -C $R log --format='%h|%ad|%s' --date=short -- docs/diagrams/07-vs-oh-my-pi.svg docs/diagrams/06-oh-my-pi.svg
git -C $R log --all --diff-filter=A --name-only --format='' | sort -u | grep -E '\.(ts|tsx|js|json)$'
grep -rn 'bun src/cli.ts' $R/demos/

# 数字核对
git -C $R ls-tree -r --name-only cf07969 | grep '\.go$' | wc -l
git -C $R ls-tree -r --name-only cf07969 | grep '\.go$' | while read f; do git -C $R show cf07969:"$f"; done | wc -l
```

---

**主要引用文件（绝对路径）**
- `/Users/overkazaf/playground/research/re-agent/README.md`（543 行；Why §53-84、Highlights §102-119、Motivation §121-136、More Docs §527-543）
- `/Users/overkazaf/playground/research/re-agent/README.zh-CN.md`（493 行；为什么 §52-76、亮点 §89-100、动机 §102-109）
- `/Users/overkazaf/playground/research/re-agent/docs/ARCHITECTURE.md`（1,270 行；Orientation §11-28、Package map §32-51、MCP §661-686、Extension points §941-1140）
- `/Users/overkazaf/playground/research/re-agent/docs/diagrams/06-oh-my-pi.svg`
- `/Users/overkazaf/playground/research/re-agent/docs/diagrams/07-vs-oh-my-pi.svg` ← **本任务信息密度最高的单个文件**
- `/Users/overkazaf/playground/research/re-agent/Makefile`
- `/Users/overkazaf/playground/research/re-agent/go.mod`
- `/Users/overkazaf/playground/research/re-agent/config.example.json`
- `/Users/overkazaf/playground/research/re-agent/internal/skills/skills.go`（:97-131 progressive disclosure；:148-163 frontmatter）
- `/Users/overkazaf/playground/research/re-agent/internal/assets/assets.go`（:17 go:embed；:181-192 EmbeddedSkills）
- `/Users/overkazaf/playground/research/re-agent/internal/tools/meta.go`（:513-532 list_skills / read_skill）
- `/Users/overkazaf/playground/research/re-agent/demos/README.md`（:20-21 bun 化石）
- `/Users/overkazaf/playground/research/re-agent/knowledge/README.md`
- `/Users/overkazaf/playground/research/re-agent/cmd/import-knowledge/main.go`（:35 `.claude` 忽略列表）
