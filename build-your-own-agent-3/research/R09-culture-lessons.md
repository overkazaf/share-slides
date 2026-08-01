# R09 · oh-my-pi 工程文化与可复制方法论

> 取证对象：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi`，HEAD `09a7c8656`（`chore: bump version to 17.2.3` 的下一提交）
> 证据等级：`[A]` 本地仓库亲自读到（附 `文件:行号`）｜`[B]` 权威二手已核实｜`[C]` 推测（只进存疑区）

---

## 0. 结论先行

omp 的工程文化可以压缩成一句话：**把"给人看的规范"和"给机器执行的约束"合并成同一份可执行资产。**

三个最硬的证据：

1. `docs/` 的 122 篇 Markdown（27,931 行）不只是给人读的 —— 它们在编译期被 gzip 打包进二进制（`PI_DOCS_EMBED`），运行时通过 `omp://` 协议供 agent 自己查阅。文档即产品的一部分。`[A]` `packages/coding-agent/src/internal-urls/docs-index.ts:1-13`、`packages/coding-agent/scripts/compile-binary.ts:42`
2. `AGENTS.md`（282 行 / 2,570 词）不是"风格建议"，而是一份带**故障史注释**的执行契约 —— 每条禁令后面挂着导致它诞生的 issue 编号。`[A]` `AGENTS.md:51`（`issues #1011, #1027, #1150`）
3. 团队不靠"感觉"判断哪种 edit 工具格式好，而是自建 `typescript-edit-benchmark` 量化，并把 6 个模型的成绩以 JSON 存在仓库里。`[A]` `packages/typescript-edit-benchmark/all_models_results.json`

同时必须诚实说明：这个仓库的 CI/基础设施部分（自建 Kata microVM k3s 集群 + Bazel 远程缓存）**是明确的过度工程**，绝大多数团队不该抄（第 6 节详述）。

---

## 1. `docs/` 全目录盘点

### 1.1 规模

| 指标 | 数值 | 证据 |
|---|---|---|
| `docs/` 下 `.md` 文件总数 | 122 | `[A]` `find docs -name '*.md' \| wc -l` |
| 总行数 | 27,931 | `[A]` 同上 `xargs wc -l` |
| 顶层条目数（含 3 个子目录） | 79 | `[A]` `ls docs/ \| wc -l` |
| 子目录 | `docs/tools/`（26 篇）、`docs/toolconv/`（9 篇）、`docs/skills/`（3 篇 + 3 个示例 README） | `[A]` |
| 最长单篇 | `rpc.md` 812 行 | `[A]` |

对照：`AGENTS.md` 282 行，`README.md` 619+ 行（38 KB），`CONTRIBUTING.md` 90 行。

### 1.2 按类别归组（全量，行数为实测）`[A]`

#### A. 架构 / 运行时内核（12 篇）
| 文档 | 行 | 一句话主题 |
|---|---:|---|
| `session.md` | 483 | 会话存储与 JSONL entry 模型 |
| `session-tree-plan.md` | 223 | 会话树（分支/fork）架构现状 |
| `session-switching-and-recent-listing.md` | 249 | 会话切换与最近列表的解析规则 |
| `session-operations-export-share-fork-resume.md` | 358 | export/dump/share/fresh/fork/resume 六种会话操作语义 |
| `compaction.md` | 423 | 上下文压缩与分支摘要 |
| `ttsr-injection-lifecycle.md` | 238 | TTSR（turn-time system reminder）注入生命周期 |
| `non-compaction-retry-policy.md` | 237 | 非压缩类自动重试策略 |
| `handoff-generation-pipeline.md` | 252 | `/handoff` 交接文档生成管线 |
| `tui-core-renderer.md` | 382 | TUI 核心渲染器的 append-only 契约 |
| `tui-runtime-internals.md` | 224 | TUI 运行时内部机制 |
| `fs-scan-cache-architecture.md` | 188 | 文件系统扫描缓存的架构契约 |
| `blob-artifact-architecture.md` | 245 | blob/artifact 存储架构 |

#### B. Native / Rust 子系统（10 篇）
`natives-architecture.md`(173)、`natives-binding-contract.md`(137)、`natives-addon-loader-runtime.md`(203)、`natives-build-release-debugging.md`(430，运维 runbook)、`natives-rust-task-cancellation.md`(217)、`natives-shell-pty-process.md`(281)、`natives-text-search-pipeline.md`(267)、`natives-media-system-utils.md`(159)、`native-crates.md`(48)、`porting-to-natives.md`(173，N-API 移植现场笔记)。

#### C. 模型 / Provider / 协议适配（11 篇）
`models.md`(749)、`providers.md`(354)、`adding-a-provider.md`(108)、`provider-endpoint-constraints.md`(395)、`provider-streaming-internals.md`(216)、`ai-schema-normalize.md`(173)、`local-models.md`(148)、`auth-broker-gateway.md`(233)、`rpc.md`(812)、`sdk.md`(368)、`ERRATA-GPT5-HARMONY.md`(209)。

#### D. 工具格式转换 `docs/toolconv/`（9 篇）
每个模型家族的 tool-calling 线格式各一篇：`anthropic.md`(630)、`deepseek.md`(383)、`gemini.md`(147)、`gemma.md`(103)、`glm-4.5.md`(296)、`harmony.md`(224)、`kimi-k2.md`(182)、`qwen3.md`(206)、`pi-native.md`(276)。

#### E. 工具参考 `docs/tools/`（26 篇）
`ask/ast-edit/ast-grep/bash/browser/checkpoint/computer/debug/edit/eval/generate_image/github/glob/grep/hub/inspect_image/learn/lsp/manage_skill/memory_edit/read/recall/reflect/retain/rewind/security_scan/task/todo/tts/web_search/write`。最长 `debug.md`(337)、`lsp.md`(316)、`read.md`(303)。

#### F. 扩展性 / 生态（12 篇）
`extensions.md`(484)、`extension-loading.md`(271)、`hooks.md`(348)、`custom-tools.md`(207)、`skills.md`(227)、`marketplace.md`(235)、`plugin-manager-installer-plumbing.md`(289)、`slash-command-internals.md`(244)、`gemini-manifest-extensions.md`(179)、`task-agent-discovery.md`(197)、`tui.md`(269)、`docs/skills/authoring-{extensions,hooks,marketplaces}.md`（258/266/268 + 3 个可运行示例）。

#### G. 配置 / 设置（8 篇）
`settings.md`(811，全仓最长之一)、`config-usage.md`(317)、`environment-variables.md`(444)、`context-files.md`(236)、`keybindings.md`(51)、`theme.md`(357)、`system-prompt-customization.md`(182)、`install-id.md`(41)。

#### H. MCP（4 篇）
`mcp-config.md`(498)、`mcp-protocol-transports.md`(283)、`mcp-runtime-lifecycle.md`(238)、`mcp-server-tool-authoring.md`(230)。

#### I. 运维 / 发布 / 安全（5 篇）
`macos-signing-notarization.md`(125)、`secrets.md`(136)、`approval-mode.md`(139)、`bash-tool-runtime.md`(300)、`computer-use.md`(306)。
另有独立目录 `infra/docs/`（README + 01~04 四篇，见第 5 节）。

#### J. 决策记录 / 迁移指南 / 勘误（4 篇 —— **这是最有文化含量的一类**）
| 文档 | 行 | 主题 |
|---|---:|---|
| `porting-from-pi-mono.md` | 387 | 从上游 pi-mono 同步改动的可重复 checklist，含"上次同步点 commit + 日期"字段 `[A]` `docs/porting-from-pi-mono.md:8-12` |
| `ERRATA-GPT5-HARMONY.md` | 209 | GPT-5 Harmony 路由头泄漏的研究勘误，开头即声明"这是历史研究笔记，不是当前运行时契约" `[A]` `docs/ERRATA-GPT5-HARMONY.md:3-5` |
| `arktype-guide.md` | 131 | Zod → ArkType 迁移指南 |
| `porting-to-natives.md` | 173 | TS → Rust N-API 移植的现场经验 |

#### K. 记忆 / 观测 / 其他（8 篇）
`memory.md`(98)、`mnemosyne-memory-backend.md`(160)、`advisor-watchdog.md`(305)、`collab.md`(132)、`tree.md`(247)、`magic-keywords.md`(46)、`vibe-mode.md`(74)、`rulebook-matching-pipeline.md`(292)、`user-facing-packages.md`(62)、`python-repl.md`(244)、`notebook-tool-runtime.md`(187)、`resolve-tool-runtime.md`(53)、`lsp-config.md`(241)。

### 1.3 最值得单独讲一页 slide 的 3 篇

**① `docs/toolconv/` 整个目录（9 篇，2,447 行）**
理由：这是"harness 必须替模型擦屁股"最直观的证据。同一个 tool call，Anthropic 走 content block、OpenAI 走 Harmony 通道 token、Gemini 走 Pythonic `default_api`、Gemma 走 `call:NAME{…}` token 分隔、Qwen3 走 Hermes 约定 —— 九种线格式各写一篇独立规范。分享时一页展示"九种格式"表格，比任何抽象讲解都有冲击力。`[A]` `docs/toolconv/*.md` 标题行

**② `docs/ERRATA-GPT5-HARMONY.md`**
理由：这是极罕见的"公开的 LLM 缺陷取证报告"。它精确描述了 gpt-5 会把路由控制 token 的**去括号明文影子**（`analysis to=functions.X code …`）当作普通内容吐进 tool 参数里，并解释了根因假说：OpenAI 对 args 区域施加 logit mask 屏蔽了控制 token ID，被压制的概率质量重新分配到模型同样学过的明文拼写上，于是泄漏对路由解析器结构性不可见。`[A]` `docs/ERRATA-GPT5-HARMONY.md:26-40`
一页 slide 讲清"为什么 agent harness 需要防御性解析"，没有比这更好的素材。同时它的开头免责声明（"统计来自本地 stats 数据库快照，不来自签入的测试或运行时代码"）本身就是可抄的写作规范。

**③ `docs/advisor-watchdog.md`**
理由：这是"第二个模型盯着第一个模型"的完整产品化设计 —— advisor 只读工具集（`read/grep/glob` + `advise`）、不能批准动作、只能注入建议；并且文档里写清了一个真实 bug 的修复过程：advisor 原本只看到 plan-mode 规则的 120 字符截断，正好切在 `NEVER create, edit, or delete files — excep…` 处，把"除了那唯一一个 plan 文件"的例外条款藏掉了，于是对 agent 写自己的 plan 文件报了假阻断。`[A]` `docs/advisor-watchdog.md:5, 70-72`
这一页可以同时讲"多 agent 监督架构"和"截断是安全 bug 的温床"两个点。

---

## 2. `AGENTS.md`：写给 AI 看的仓库说明书

### 2.1 基本事实 `[A]`
- 全仓仅 2 个 `AGENTS.md`：根目录一份（282 行 / 2,570 词 / 20 KB），`python/robomp/AGENTS.md` 一份（127 行）。
- 根目录版本的章节：Default Context → Package Structure → GitHub → Code Quality → Central Utilities → Bun Over Node → Generated Files → Logging and CLI Output → TUI Sanitization → Commands → Testing Guidance → Changelog → Releasing。

### 2.2 它规定了什么，细到什么程度

**(a) 先消歧义，再讲规则。** 开头第一件事不是规则，是术语澄清：「用户说 "agent" 时指的是 `packages/coding-agent/` 这个 CLI 实现，不是你（助手）自己」。`[A]` `AGENTS.md:7`
这解决的是 agent 在自指仓库里最容易犯的错 —— 把用户的 bug 报告当成对自己行为的抱怨。

**(b) 规则是二元的，不是建议。** 大量 `NEVER` / `MUST`，且给出替代物：
- `NEVER use ReturnType<>` —— 用真实类型名 `[A]` `AGENTS.md:35`
- `NEVER use inline imports` —— 不许 `await import()`、不许 `import("pkg").Type` `[A]` `AGENTS.md:36`
- `Never build prompts in code` —— prompt 必须住在静态 `.md` 里，用 `import content from "./prompt.md" with { type: "text" }` 引入，不许 `readFile` `[A]` `AGENTS.md:41`
- `NEVER edit packages/catalog/src/models.json directly` + 逐条列出"改哪个源文件才对" `[A]` `AGENTS.md:175-184`
- `Never use mock.module()` —— 附 bun issue 链接 `oven-sh/bun#12823` 作为理由 `[A]` `AGENTS.md:244`

**(c) 表格化的 API 替换表。** "Bun Over Node" 一节是一张 13 行的对照表：`操作 | 用什么 | 不要用什么`（文件读写用 `Bun.file()` 不用 `readFileSync`，SQLite 用 `bun:sqlite` 不用 `better-sqlite3`，字符宽度用 `Bun.stringWidth()` 不用 `get-east-asian-width`……）。`[A]` `AGENTS.md:68-81`
这种"表格 + 反例列"的形式对 LLM 极其友好 —— 它把"我该用哪个 API"从检索问题降级成查表问题。

**(d) 反模式清单写得比正面规则还长。** File I/O 一节列了 5 条 anti-pattern，每条都给出"为什么错"：`if (await file.exists()) { await file.json() }` 是"两次系统调用外加竞态"，正确写法是 try-catch + `isEnoent`。`[A]` `AGENTS.md:134-150`

**(e) 最独特的一条：规则附带故障史。** Worker scripts 那一节先给正确写法，然后专门写一段 `History:`：
> `with { type: "file" }` 只把入口当原始资产拷贝（编译二进制里 worker 静默崩溃 —— issues #1011、#1027），后来的"字面路径 + 额外入口"方案又要求 spawn 字面量和两个构建脚本保持同步（issue #1150）。
`[A]` `AGENTS.md:51`
并且紧接着给出**活体验证手段**：`omp --smoke-test` 会真的 spawn stats sync worker 和 tiny-model 子进程、ping 它们、退出；这个探针接进了 `ci:test:smoke` 和三种安装方式的冒烟脚本。`[A]` `AGENTS.md:52`

**(f) 测试章节是一份独立的测试哲学（17 条）。** 最狠的一条是 **"Never source-grep"**：禁止写读取实现文件源码并断言其文本的测试（`expect(src).toContain("someCall()")`、`.not.toContain("oldName")`、"注释必须写 X"）。理由写得很清楚 —— 它测的是代码**长什么样**而不是**做什么**：无害的重构（注释换行、重命名、import 重排）会让它挂，而行为真坏了它却能过。`[A]` `AGENTS.md:250`
其他要点：每个新测试必须能说出它守护的那一个"外部可观察契约"，说不出就别加；禁止 `expect(true).toBe(true)` 类占位；测试必须"全量套件安全"而不只是"单文件安全"（禁止对 `Bun.*`、`process.platform`、`process.env` 做文件级长期改写）。`[A]` `AGENTS.md:239-243`

### 2.3 可复制的做法（"给 agent 用的代码库该怎么写"）

1. **第一段永远是消歧义**，不是规则。明确"当用户说 X 时指的是仓库里的哪个东西"。
2. **给出包结构表**（包名 → 一句话职责），并声明默认工作区（"除非另有说明，都指 `packages/coding-agent/`"）。`[A]` `AGENTS.md:5, 11-22`
3. **用 NEVER/MUST，不用 "prefer/try to"**，且每条禁令必须配一个替代物。禁令没有替代物 = agent 会自己发明一个。
4. **反模式清单和正面规则一样重要**，因为模型的先验里装满了通用写法（`readFileSync`、`console.log`），你要做的是主动覆盖先验。
5. **给规则挂上故障史（issue 号）**。这是 omp 最值得抄的一招 —— 它同时服务两个目的：让人类 reviewer 知道这条不能删；让 agent 在遇到 edge case 时知道边界在哪。仓库里还专门有一条 skill 规定"删 prompt 行之前必须 `git blame`，历史会告诉你这行是复述 schema 还是事故留下的疤痕（keep scar tissue）"。`[A]` `.omp/skills/tool-prompt-optimization/SKILL.md:79`
6. **规则要有活体验证钩子**。`omp --smoke-test` 是"worker 必须复用 CLI 入口"这条规则的运行时执法者。规范 + 执法者成对出现，规范才不会腐烂。
7. **子目录可以有自己的 AGENTS.md**（`python/robomp/AGENTS.md`），内容是该子系统的数据流编号步骤（webhook → 队列 → dispatcher → worktree → RPC 子进程），而不是重复根规则。`[A]` `python/robomp/AGENTS.md:12-20`

---

## 3. 测试体系

### 3.1 规模 `[A]`

| 维度 | 数值 |
|---|---|
| TypeScript 测试文件（`*.test.ts(x)`，排除 `node_modules`） | **1,930** |
| TS 测试总行数 | **531,633** |
| Python 测试文件（`test_*.py`） | 31 |
| Python 测试总行数 | 20,485 |
| Rust 测试 | 通过 Bazel `//crates/...` 运行（`bazelisk test //crates/...`），不用 cargo nextest |

按包分布（TS 测试文件数）`[A]`：
`coding-agent` **1,207** · `ai` 335 · `tui` 87 · `catalog` 76 · `mnemopi` 72 · `utils` 48 · `agent` 30 · `stats` 19 · `hashline` 12 · `natives` 10 · `collab-web` 9 · `metaharness` 5 · `typescript-edit-benchmark` 2 · `snapcompact`/`swarm-extension`/`wire` 各 1。

### 3.2 跑测试的命令 `[A]` `package.json`

```
bun test                    # = bun scripts/ci-test-ts.ts local（本地全量）
bun run test:ts             # 仅 TS
bun run test:rs             # Rust（走 scripts/run-rs-task.ts）
bun run test:py             # pytest -x python/omp-rpc/tests && pytest -x python/robomp/tests
bun run test:scripts        # 8 个仓库脚本自身的测试
bun check                   # 类型检查 + lint 的唯一入口（AGENTS.md 明令禁止直接 tsc）
bun run ci:test:smoke       # --version / --help / stats --help / --smoke-test
```

### 3.3 CI 怎么跑 `[A]` `.github/workflows/ci.yml`（887 行，单文件）

**分片策略**：测试被切成 7 个独立 job，切分逻辑不写在 YAML 里，而写在 `scripts/ci-test-ts.ts` 这个可测试的 TS 程序里（它自己还有 `ci-concurrency.test.ts` 守着）。
- `test_workspace`（快包：hashline/wire/utils/catalog/ai/snapcompact/agent）
- `test_coding_agent_singleton`（全局状态桶，**故意不切分**，必须共进程）
- `test_ts_native`（natives/tui/collab-web/typescript-edit-benchmark）
- `test_coding_agent_ui`（chunkSize=5）
- `test_coding_agent_runtime`（chunkSize=10）
- `test_coding_agent_native`（chunkSize=10）
- `test_smoke` + `install_methods`

**分片理由被写成了代码注释，而且是实测出来的**：
> 一个 fresh 进程/chunk 会重置 Bun 堆并回收挂起的子进程，把峰值 RSS 压在 CI runner 的 OOM 天花板下（单次 170–370 文件的调用会被 SIGKILL，exit 137）。UI/TUI 桶用更小的 chunk(5)：它的套件会堆积 native ghostty-vt cell，bun 1.3.14 的 GC 在 ~10 个这类文件共享堆时会 abort（SIGTRAP/SIGABRT，exit 133/134，崩在 `DOMGCOutputConstraint` 标记阶段）。二分定位显示**没有单个文件有问题 —— 崩溃是累积堆体积导致的**。在强制 256MB 堆下，10 文件 chunk 约 50% 运行会 abort，而两个 5 文件的半区各 0/20。
`[A]` `scripts/ci-test-ts.ts:61-74`

这段注释本身就值一页 slide：**它记录了一次真实的二分实验和 0/20 的对照数据**。

**PR 与 main 的双轨制** `[A]`：
- PR 跑在 GitHub 托管的 `ubuntu-22.04`；main/release 跑在自建 `omp-kata`。`[A]` `ci.yml:132, 188, 296…`
- Rust 校验（test/clippy/rustfmt）**只在非 PR 事件跑**，理由写在注释里："改动 native 的 PR 罕见到不值得 PR 侧的 Rust 校验；Rust 在合并后的 main 上（kata 远程缓存，热）和 release 时各验一次。被跳过的 required check 仍然满足分支保护。" `[A]` `ci.yml:141-145`
- PR 不构建 native addon，而是从 npm 拉最新 release 的 `@oh-my-pi/pi-natives-linux-x64` tarball。`[A]` `ci.yml:193-203`
- 拉下来之后必须冒烟，且冒烟脚本要写成文件而不是 `bun -e`：注释直言 "`bun -e 'require("./x.node")'` 会吞掉 dlopen 失败（对损坏 addon 也 exit 0）；写成脚本文件在 bun 和 node 里都能强制失败。**已用一个损坏的 .node fixture 验证过**。" `[A]` `ci.yml:211-213`

**注意：Python 测试没有进 CI。** `ci.yml` 全文不含 `pytest` / `ruff` / `test:py`。`[A]`（grep 无匹配）

### 3.4 `packages/typescript-edit-benchmark` —— 是的，它就是量化"模型改代码改得准不准"

**它做什么** `[A]` `src/generate.ts:1-24`（原文注释）：
> 目标是测**编辑精度**，不是找 bug 能力。变异可以很平凡 —— 重点是模型能否在困难上下文里外科手术式地打上这个补丁：
> - **重复行**：目标行在文件里出现多次
> - **长文件**：300+ 行，编辑点在中间
> - **相似块**：多个结构相似的函数
> - **稠密代码**：极少空白，上下文更难读
> - **深嵌套**：高缩进层级下的空白敏感编辑
>
> 难度档同时控制**文件选择**和**提示详细度**。每个 prompt 都完全确定了字节级精确的修复（before/after 块，通过对期望输出重新求解来验证）；各档只改变模型需要自己定位多少：
> - `easy`：短文件、唯一行、给出精确行号
> - `medium`：中等文件、给出所在函数
> - `hard`：长文件 + 相似块、**不给位置提示**
> - `nightmare`：长文件、近乎相同的区域反复出现、不给位置提示

**怎么造题**：从一个 pi-mono 风格的 TypeScript 仓库（默认 shallow-clone `https://github.com/badlogic/pi-mono.git`）扫描 `.js/.jsx/.ts/.tsx` 源文件，做 AST 级变异（`src/mutations.ts`，1,599 行，基于 `@babel/parser` + `@babel/traverse`），产出 `fixtures.tar.gz`。`[A]` `src/generate.ts:25-52`

**怎么判分**：`src/verify.ts` 做**逐字节**比对期望产物；同时记录 `indentScore`、`formattedEquivalent`（经 prettier 归一后是否等价）、`diffStats`。`[A]` `src/verify.ts:1-23`

**代码量** `[A]`：`mutations.ts` 1,599 · `generate.ts` 1,273 · `edit-shape-stats.ts` 352 · `verify.ts` 311 · `hunks.ts` 264 · `tasks.ts` 263 · `in-process-client.ts` 229 · `formatter.ts` 69，合计 4,645 行（含 2 个测试文件）。

**结果被签入仓库** `[A]` `packages/typescript-edit-benchmark/all_models_results.json`（6 个模型，可直接上 slide）：

| model | success% | edit_success% | avg_tok_in | avg_tok_out | avg_time_ms | ghost_runs | timeout_runs |
|---|---:|---:|---:|---:|---:|---:|---:|
| claude-haiku-4.5 | **90.0** | 88.5 | 16,516 | 671 | 52,374 | 0 | 2 |
| kimi-k2.5 | 85.0 | 74.1 | 8,686 | 1,132 | 94,871 | 1 | 2 |
| gemini-3-flash | 80.0 | 74.1 | 18,985 | 268 | 64,709 | 1 | 3 |
| minimax-m2.5 | 75.0 | 88.2 | 11,645 | 2,285 | 111,853 | 0 | 5 |
| glm-4.7 | 65.0 | 79.2 | 8,444 | 1,530 | 183,592 | 3 | 4 |
| deepseek-v3.2 | 55.0 | **100.0** | 15,123 | 1,762 | 208,632 | 9 | 0 |

（`success%` = 任务整体成功率；`edit_success%` = 单次 edit 调用的成功率；`ghost_runs` = 空跑。注意 deepseek 的组合：每次 edit 都成功但任务成功率最低 + 9 次 ghost run —— 它编辑得准，但**决定编辑什么**这一步失败。这一列对比本身就是一页 slide。）

**配套还有第二套基准**：`scripts/edit-benchmark.py`（82 行）+ `scripts/edit_benchmark_common.py`，用 `PI_EDIT_VARIANT` 环境变量在 `vim` / `hashline` / `replace` / `patch` / `apply_patch` 五种 edit 工具**格式**之间切换，跨模型对比同一个编辑任务。`[A]` `scripts/edit-benchmark.py:1-12, 50-72`
还有 `scripts/rate-edit-tool.py`（1,572 行）和 `scripts/analyze_small_edits.py`（473 行）。

**README 里公布的收益** `[B]`（README 自述，未在本地复算）`[A]` `README.md:84-101`：
| 模型 | 变化 | 说明 |
|---|---|---|
| Grok Code Fast 1 | 6.7% → 68.3% | 换掉"吃掉模型"的编辑格式后十倍提升 |
| Gemini 3 Flash | +5 pp | 相对 `str_replace` |
| Grok 4 Fast | −61% tokens | 坏 diff 的重试循环消失后输出量塌缩 |
| MiniMax | 2.1× | 通过率翻倍多，同权重同 prompt |

**这就是 omp 的核心论点**：模型能力常常不是瓶颈，harness 才是。这句话在这个仓库里是**有实验数据支撑的**，不是口号。

### 3.5 附带的"数据驱动 prompt 优化"设施 `[A]`
- `scripts/session-stats/`（9,315 行）：`sync.py`(1,235) 同步会话到本地库，`analyze.py` 分析 tools/edits/followups，`read_optimizer.py`(778)、`optimize_read_config.py`(907) 用真实会话数据反推 `read` 工具的最佳默认参数，`harmony_backtest.py`(1,168) 回测 Harmony 泄漏检测规则，`audit.ts`(1,463) 做审计。
- `.omp/skills/tool-prompt-optimization/`：一套**测量 prompt 冗余度**的方法论 —— 只给模型 `(工具名, JSON schema, 空白大纲)`，让它预测 prompt 正文；能稳定预测出来的行 = 剪枝候选（schema 已经教过了），永远预测不出来的 = 承重行。并明确警告两点：① 删之前**必须** `git blame`，很多行是真实事故后加的疤痕组织；② 公开仓库可能在训练数据里，模型可能是**背诵**而非推断，判别方法是看预测里有没有 schema 中不存在的仓库特有细节。`[A]` `.omp/skills/tool-prompt-optimization/SKILL.md:8-10, 72-80`
- `.omp/skills/system-prompts/SKILL.md`：项目 prompt 写作规范 —— 标签词表（`<critical>` 放在开头和结尾）、RFC 2119 全大写关键词（项目别名：优先 `NEVER` 而非 `MUST NOT`，因为在 cl100k/o200k 里都是单 token 且权威等同）、密度规则（"用 `X? Y.` 替代 `If X, then Y`"、"符号胜过词：`→`、`=`、`B+1`、`A..B`"）。`[A]` `.omp/skills/system-prompts/SKILL.md:12-56`

---

## 4. `python/` —— Python 在体系里的位置

Python 不是"机器人"，也不是通用远程执行层。它是**两个东西**：

### 4.1 `python/omp-rpc`（4,350 行 src + 4 个测试文件）—— 官方 Python 绑定 `[A]`
`omp --mode rpc` 暴露的是换行分隔的 JSON RPC（stdio）。`omp-rpc` 是它的类型化 Python 客户端：
- `protocol.py` 1,793 行（协议模型）、`client.py` 2,154 行（进程管理 + 请求关联）、`host_uris.py` 126、`host_tools.py` 80。
- 能力：协议 v2 自动协商、无损分块重组、稳定的消息分页、类型化的逐事件监听器 + 全局通知钩子、**host tools**（Python 侧用 JSON Schema 注册自定义工具给 agent 用）。`[A]` `python/omp-rpc/README.md:5-15`

用法长这样 `[A]` `python/omp-rpc/README.md:20-30`：
```python
from omp_rpc import RpcClient
with RpcClient(provider="anthropic", model="claude-sonnet-4-5") as client:
    turn = client.prompt_and_wait("Reply with just the word hello")
    print(turn.require_assistant_text())
```

**与 TS 主体的通信方式**：子进程 + stdio 上的 NDJSON RPC。没有共享内存、没有 HTTP、没有 FFI。`[A]`

### 4.2 `python/robomp`（src 13,363 行，31 个测试文件 20,485 行）—— 自托管的 GitHub 机器人 `[A]`

它是 **omp 自己用来维护 omp 的机器人**：监听 GitHub webhook，对新 issue 分类打标签，然后分支处理 —— `bug`/`documentation` 走"复现 → 在新分支修 → 开 PR（PR body 必须有 `## Repro` / `## Cause` / `## Fix` / `## Verification` 和 `Fixes #N`）"；`question` 走"一条评论 + 👎 保持开启的提示，作者若 N 小时内不 👎 就自动关闭"；`enhancement`/`proposal` 只评论不开 PR。`[A]` `python/robomp/README.md:1-18`

**架构：两个容器，一条信任边界** `[A]` `python/robomp/README.md:24-45`
- **robomp**：FastAPI + sqlite 事件队列 + `WorkerPool`，在 `/data/workspaces/` 下的**每 issue 独立 git worktree** 里跑 `omp --mode rpc`。持有 HMAC key，**永不持有 PAT**。
- **gh-proxy**：同一台机器上的 sidecar，挂在 `internal: true` 网络上。持有 `GITHUB_TOKEN`，校验 robomp 发来的 HMAC 签名请求，执行 REST + `git push`。**只允许出网到 `api.github.com`**。

数据流：webhook → HMAC 校验 → `github_events.route` → sqlite `events` 表（按 `X-GitHub-Delivery` 去重）→ `WorkerPool` 在 `BEGIN IMMEDIATE` 下认领，配合进程内按 `(owner, repo, n)` 的 `_inflight` 集合 → `sandbox.ensure_workspace` 产出 `farm/<8hex>/<slug>` 分支的 worktree → `worker.run_task` spawn `omp --mode rpc`，`cwd=worktree`，持久化 `session_dir`，**模型从 `ROBOMP_MODEL`（CSV）里随机抽**。

**几个特别值得讲的设计** `[A]` `python/robomp/README.md:129-149`、`python/robomp/AGENTS.md:12-20`：
- 编排器**看到自己环境里有 `GITHUB_TOKEN` 就拒绝启动**。
- HMAC-SHA256 + ±30s 时钟偏移窗口 + 常数时间比较。
- `git push` 用 `git -c http.extraheader=…`，token 走临时进程环境变量，`.git/config` 里的 remote URL 保持无 token。
- gh-proxy 没有宿主端口；`robomp_internal` 网络 `internal: true`（无入向无出向），gh-proxy 只为了访问 `api.github.com` 才加入 `default` 网络。
- agent 子进程环境被 `worker._SCRUBBED_ENV_KEYS` 洗掉敏感变量。
- webhook 签名错误返回 **401 而不是 5xx**（让 GitHub 停止重试）。
- git 错误经 `git_ops.GitCommandError`，把 `https://user:pw@host` 在 argv/stdout/stderr 里全部改写成 `https://***@host` 之后才抛出。
- 每一次 host tool 调用都被审计进 `tool_calls` 表，参数和结果都经过凭据脱敏。
- **崩溃恢复即续接会话**：`session_dir` 下已有 `*.jsonl` 时 worker 传 `--continue`，所以后续事件和"编排器重启后重新入队的在途事件"都恢复同一个 session，带着之前的推理继续，而不是从头开始。

**host tools 是 GitHub 写操作的唯一出口**（`host_tools.py` 2,052 行）：`gh_post_comment`、`gh_push_branch`、`gh_open_pr`、`gh_request_review`、`gh_search_issues`。其中 `gh_push_branch` 和 `gh_open_pr` 在执行前会先跑 `_run_pre_publish_bun_fix` + `_run_pre_publish_bun_check` —— **机器人在推代码之前必须自己过一遍 `bun check`**。`[A]` `python/robomp/src/host_tools.py:883-884, 941-942`

**这条闭环反过来解释了 `CONTRIBUTING.md` 里一条看起来很奇怪的规定**：
> 如果你打算自己实现某个改动，**不要先建 issue**。robomp 会把可执行的 issue 当作要认领的工作，可能并行开始同一个修复，浪费算力和维护者时间。
`[A]` `CONTRIBUTING.md:28-32`
—— 贡献流程被机器人的存在改写了。这是一个非常有讲头的细节。

---

## 5. `infra/` + Bazel + Dockerfile：一个 CLI 为什么需要这套东西

### 5.1 为什么需要（真实约束，不是炫技）`[A]`
omp 不是纯 TS 的 CLI。它带着 **~55,000 行 Rust**，编译成一个按平台打标的 N-API addon。`[A]` `README.md:422-424`
要发布的 addon 组合有 **8 个**（平台 × 架构 × ISA 变体）：`linux-x64-baseline`、`linux-x64-modern`、`linux-arm64`、`linux-musl-x64-baseline`、`linux-musl-arm64`、`darwin-x64-baseline`、`darwin-arm64`、`win32-x64-baseline`。`[A]` `BUILD.bazel:16-25`
再加上 macOS 需要 Developer ID 签名 + 公证、npm 需要 trusted publishing、Homebrew 需要更新 formula。**分发复杂度才是这套基础设施的来源，不是 CLI 本身。**

### 5.2 Bazel 替代了什么 `[A]` `.bazelrc:1-40`、`BUILD.bazel:1-14`
- 交叉编译目标、ISA 变体、release codegen 全部编码在 `//:natives-*` 目标里（通过 `bazel/defs.bzl` 的 transition），所以裸的 `bazel build //:natives-<target>` **总是 release 级**。
- `--incompatible_strict_action_env`：宿主环境不泄漏进 action key。需要宿主工具的构建脚本（`audiopus_sys` 要 cmake 编 opus）通过 `MODULE.bazel` 里的 crate annotation 显式拿到 PATH。
- **Bazel 在 CI 里替代了 `cargo clippy` / `cargo nextest`**，并且复刻了 cargo 的语义：带 `[lints] workspace = true` 的 crate（pi-ast/pi-iso/pi-natives/pi-shell/pi-voice/pi-walker）走严格策略（`clippy-strict`，`bazel/clippy.bazelrc` 由 `Cargo.toml` 生成），其余走默认 clippy + `-Dwarnings`；vendored 的 brush fork 豁免。`[A]` `.bazelrc:24-34`、`ci.yml:167-176`
- CI 侧 `--reuse_sandbox_directories`，原因注释写明：zig/xwin 工具链每个 action 要 stage 约 10k 文件的输入树，成千上万个 action 反复建/异步删会把 kata pod 的文件描述符耗尽（`unix_jni` 里 EMFILE）。`[A]` `.bazelrc:48-51`
- `MODULE.bazel` 14,782 字节，`MODULE.bazel.lock` **3.6 MB**。`[A]`

### 5.3 `infra/` = 自建的 Kata microVM CI 集群 `[A]` `infra/docs/README.md:3`
> **每一个跑在自建 `omp-kata` 标签上的 CI job 都跑在自己的一次性 Kata Containers QEMU/KVM 微虚拟机里。** 单台裸金属 Linux 主机跑单节点 k3s；actions-runner-controller 监听 GitHub 的排队 job，为每个 job 创建 JIT 临时 runner pod，pod 启一个全新微虚拟机（自己的 guest kernel，与宿主隔离），跑**恰好一个 job**，然后销毁。

关键属性 `[A]` `infra/docs/README.md:47-54`：
- **一 job 一 VM**，无模板无池化，job 永不继承上一个 job 的状态。
- **缩容到零**：`minRunners: 0` / `maxRunners: 8`。runner 可突发（请求 3 vCPU/10 GiB，上限 8 vCPU/14 GiB）。
- **PR 故意跑在 GitHub 托管 runner 上**，自建机群只服务可信的 `push`/main + release，**不可信的 PR 代码永远碰不到共享缓存**。
- **无外部镜像仓库**：runner 镜像在宿主上构建后直接导入 k3s 的 containerd。
- 共享缓存：bazel-remote v2.6.2（`svc bazel-remote:9092` grpcs，集群内，100Gi PVC）存 Bazel action result 和 CAS blob；`runner-cache` PVC（100Gi）存 Bun/Cargo 下载。缓存流量不出宿主。

参考主机：裸金属 CentOS Stream 10，32 vCPU / 125 GiB RAM，AMD，k3s `v1.35.5+k3s1`，Kata `3.31.0`，ARC `0.14.2`。`[A]` `infra/docs/README.md:70-74`、`infra/docs/01-host-and-cluster.md:9`

**而且 `infra/docs/` 是按"从零复现指南"写的**（README 总览 + 01 主机与集群 / 02 Kata 运行时 / 03 runner 镜像 / 04 ARC 与缓存，要求按序阅读），配置从生产主机逐字复制后做**占位符脱敏**，并附一张占位符替换表；同时明确列出"故意保留原值"的东西（pod CIDR `10.42.0.0/16`、CoreDNS `10.43.0.10`、集群内服务名端口、所有版本号），因为它们不敏感但跟着做需要。`[A]` `infra/docs/README.md:86-102`
—— **把内部基础设施写成外部可复现的教程，这是 omp 最反常也最值得学的一条文化。**

### 5.4 `Dockerfile`（含四段注释掉的构建/运行示例）`[A]` `Dockerfile:1-23`
分阶段：`natives-builder`（Rust + Bun → `pi_natives.linux-<arch>.node`）→ `wheel-builder`（`omp_rpc` Python wheel）→ `pi-base`（python + bun + rustup + natives + omp_rpc + `/usr/local/bin/omp` shim）→ `pi-runtime`（默认，可运行）。

层次划分是为了**限定失效半径** `[A]` `Dockerfile:55-87`：
- Layer 1 只 COPY manifest + lockfile（用 `--parents`，需要 `syntax=docker/dockerfile:1.7-labs`），所以改 `packages/*/src` 和 `crates/*/src` 不会让 `bun install` 失效；
- Layer 2 `bun install --frozen-lockfile --ignore-scripts`；
- Layer 3 才 COPY 全量源码；
- Layer 4 用 `--mount=type=cache` 挂 cargo registry / git deps / target 目录做增量编译。

robomp 的镜像通过 `FROM ${PI_BASE}` 扩展 `pi-base`，所以"改 robomp 的 Python 只动运行时层，改 pi 源码才重建基础镜像"。`[A]` `python/robomp/README.md:77-79`

---

## 6. 落脚点：一个普通开发者/团队能真正搬走什么

### ✅ 五条可操作的做法

---

**① 把 `AGENTS.md` 写成"带故障史的执行契约"，而不是风格指南。**

具体怎么做：
- 第一段写消歧义（"用户说 X 时指的是仓库里的 Y"）+ 一张包结构表 + 默认工作区。
- 规则一律用 `NEVER` / `MUST`，**每条禁令必须配替代物**（"不要 `ReturnType<>` → 用真实类型名"）。
- 用**对照表**表达 API 选择（`操作 | 用什么 | 不要用什么`），比散文效率高一个量级。
- 反模式清单要写，因为你在覆盖模型的先验。
- **每条非显然的规则后面挂 issue 号**，写清"这条是因为 #1011 和 #1027 才存在的"。
- 子系统可以有自己的 `AGENTS.md`，内容是该子系统的编号数据流，不重复根规则。

证据：`AGENTS.md:5,7,11-22,35-41,51,68-81,134-150,175-184,244`；`python/robomp/AGENTS.md:12-20`
成本：一天写初版，之后每次事故补一行。**这条投入产出比最高。**

---

**② 给你的 agent 建一个"编辑精度基准"，哪怕只有 20 个 case。**

omp 的做法可以直接缩小复刻：
- 从**你自己的代码库**取源文件（不是合成代码）；
- 做**平凡的** AST 变异（改个标识符、挪个语句）—— 测的是定位与落刀精度，不是推理能力；
- 用四档难度控制**上下文难度**而非任务难度：给行号 / 给函数名 / 长文件+相似块不给提示 / 近似重复区域不给提示；
- 判分**逐字节**比对，同时记 `formattedEquivalent`（格式化归一后是否等价）以区分"改错了"和"缩进不对"；
- 结果签入仓库，换模型/换 prompt 时重跑对比。

证据：`packages/typescript-edit-benchmark/src/generate.ts:1-24`、`src/verify.ts:1-23`、`all_models_results.json`
为什么值得：deepseek-v3.2 的 `edit_success 100%` 配 `success 55%` 配 9 次 ghost run —— 这种诊断信息你**只有量化才能看见**，靠人肉试用是看不出来的。
成本：一个周末。`generate.ts` + `mutations.ts` 加起来 2,872 行是因为它要支持 5 类变异 × 4 档难度 × 多语言；单语言单变异的最小版本 200 行足够。

---

**③ 用"契约测试"取代"覆盖率测试"，并明令禁止 source-grep 测试。**

抄这三条进你的测试规范：
- 每个新测试必须能一句话说出它守护的**外部可观察契约**（行为 / 输出形状 / 状态转换 / 错误映射 / 易回归的解析边界）。**说不出来就不要加这个测试。**
- **禁止源码文本断言**：`expect(src).toContain("someCall()")`、`.not.toContain("oldName")`、"注释必须写 X" 一律禁掉。它测的是代码长什么样而不是做什么，会被无害重构打挂，也会在行为真坏时通过。结构性不变量用类型测试或 lint 规则守，不要用字符串扫描。
- 测试必须**全量套件安全**而不只是单文件安全：禁止文件级长期改写 `process.env` / `process.platform` / 全局对象；用 `spyOn` + `afterEach(restoreAllMocks)`。

证据：`AGENTS.md:239-250`
适用范围：**任何项目**，与 agent 无关。这是纯粹的软件工程收益。

---

**④ 把 CI 的分片逻辑写成有测试的程序，把"为什么这么切"写成注释里的实验记录。**

omp 的 `scripts/ci-test-ts.ts` 是可运行、可 `--dry-run`、有自己单测的 TS 程序，YAML 里只调用它。分片参数（chunkSize=5 / 10 / 不切）不是拍脑袋，注释里记着实测：256MB 强制堆下 10 文件 chunk 约 50% 会 abort，5 文件的两个半区各 0/20。

可搬走的最小形态：
- CI 编排逻辑离开 YAML，进入一个能本地跑的脚本；
- 每个"魔数"（并发度、超时、chunk 大小）旁边写一句**它是怎么测出来的**；
- 给这个脚本本身加一个测试（omp 有 `ci-concurrency.test.ts` 守 GHA 配置的并发组规则）。

再抄一条具体的坑：**验证动态库加载时不要用 `-e` 一行命令**，要写脚本文件 —— `bun -e 'require("./x.node")'` 对损坏的 addon 也返回 exit 0。omp 用一个损坏的 `.node` fixture 验证过这一点。

证据：`scripts/ci-test-ts.ts:31-127`、`ci.yml:206-220`、`package.json`（`test:scripts`）

---

**⑤ 让文档同时服务人和 agent —— 一份来源，两个消费者。**

omp 的做法：`docs/` 在编译期被打成 `[文件名 JSON 数组]\n[bodies 的 base64 gzip]` 两行格式注入 `PI_DOCS_EMBED`，运行时 agent 通过 `omp://` 协议按需读取；列目录只解析第一行，body 在首次真正读取时才在 zlib 线程池上懒解压一次。dev 树/源码 checkout 则直接读磁盘上的 `docs/`。

同时 `DEVELOPMENT.md` 明确交代了为什么这么做：
> 曾经住在这里的长篇架构走查，**过时的速度比任何人重读它的速度都快**。`docs/` 树保持更新（并且为 agent 的 `docs://` / `/docs` 界面建了索引），所以这个文件改为链接过去，而不是复制一份会腐烂的散文。

可搬走的最小形态（不需要编译期注入）：
- 建一个 `docs/` 目录，规定它是**唯一权威**；
- `AGENTS.md` / `CLAUDE.md` 里不写架构描述，只写**指向 docs 的索引表**（子系统 → 文档路径），像 `DEVELOPMENT.md:61-81` 那张表一样；
- 每篇 doc 顶部列出对应的实现文件路径（`docs/advisor-watchdog.md:9-19` 就是这么干的）；
- 这样 agent 的检索路径和人的阅读路径重合，文档不更新会立刻被 agent 的错误暴露出来。

证据：`packages/coding-agent/src/internal-urls/docs-index.ts:1-13`、`packages/coding-agent/scripts/compile-binary.ts:42`、`packages/coding-agent/DEVELOPMENT.md:3-10, 61-81`

---

### ❌ omp 特有的过度工程 —— 不建议抄

| 项目 | 为什么不该抄 | 证据 |
|---|---|---|
| **自建 Kata microVM + k3s + ARC 的 CI 集群** | 需要一台 32 vCPU/125 GiB 的裸金属机、KVM、firewalld NAT、k3s、Kata 3.31、ARC 0.14.2、bazel-remote，四篇文档才讲得完安装。它解决的问题是"要给 8 个平台交叉编译 Rust 且不能让 PR 代码碰共享缓存"。你如果没有 native 代码，GitHub 托管 runner 完全够。 | `infra/docs/README.md:70-84` |
| **Bazel 取代 cargo 做 clippy/rustfmt/test** | 为此要维护 `MODULE.bazel`(14.8 KB) + `MODULE.bazel.lock`(**3.6 MB**) + `bazel/` 下的 platforms/toolchains/triples/variants/patches 五个子目录 + 一份从 `Cargo.toml` 生成的 `clippy.bazelrc`。收益只在"多目标交叉编译 + 远程缓存"场景兑现。单目标项目用 cargo 就好。 | `MODULE.bazel*`、`bazel/`、`.bazelrc:24-34` |
| **122 篇 / 27,931 行的 `docs/`** | 这个体量本身是 agent 时代的独特产物（文档是 agent 的检索语料，所以写得越细越有用）。普通项目照抄会造出无人维护的文档坟场。抄"docs 是唯一权威 + AGENTS.md 只做索引"的**结构**，不要抄篇数。 | 第 1.1 节 |
| **1,930 个测试文件 / 53 万行 TS 测试** | 其中 `coding-agent` 一个包就 1,207 个。这是 17 个大版本累积 + 多 provider 组合爆炸的结果。抄测试**哲学**（`AGENTS.md:239-250`），不要抄数量。 | 第 3.1 节 |
| **自建 GitHub 三方机器人 robomp（13,363 行 src + 20,485 行测试）** | 它有完整的双容器信任边界、HMAC sidecar、凭据脱敏审计表、崩溃续接会话。这是"agent 自动修自己仓库的 issue"这个具体目标才需要的规模。想要类似效果先用现成的 GitHub App / Actions 方案。**但它的安全设计值得读**（第 4.2 节那 8 条），哪怕你只做一个小脚本。 | `python/robomp/README.md:129-149` |
| **9 篇 `toolconv/` 线格式规范** | 只有做"支持 40+ provider 的通用 harness"才需要。用单一 provider 的团队完全用不上 —— 但**值得读一遍**，它会让你明白你现在依赖的 SDK 在替你挡什么。 | `docs/toolconv/` |

---

## 7. 存疑区

- `[C]` README 里那张 "benchmaxxed" 表（Grok Code Fast 1 从 6.7% 到 68.3% 等）标注为 `[B]`（README 自述 + 外链博客 `blog.can.ac/2026/02/12/the-harness-problem/`），我**没有**在本地找到复现这些具体数字的脚本或结果文件。`all_models_results.json` 里的 6 个模型与 README 表里的 4 个模型没有交集。这两组数据来自不同的实验批次。`[A]`（交集为空这一点是本地核实的）
- `[C]` `all_models_results.json` 未标注生成时间、fixture 版本、样本量（`success_pct` 都是 5 的倍数，推测每模型 20 个 task；`edit_success_pct` 出现 74.1 / 88.5 等值，推测分母是 edit 调用次数 27 / 26）。上 slide 时应注明"仓库内快照，非官方发布基准"。
- `[C]` Rust 侧测试的绝对数量我没有统计（`grep '#\[test\]'` 在本次 shell 下未成功执行）。已确认的是 CI 通过 `bazelisk test //crates/...` 跑它们。`[A]` `ci.yml:162`
- `[C]` `bench:gen-fixtures` 脚本默认指向 `/tmp/typescript-source`，而 `packages/typescript-edit-benchmark` 的 `generate` 脚本指向 `/tmp/pi-mono-source`，`generate.ts` 里的默认又是 shallow-clone `pi-mono`。三处不一致，可能是历史遗留。`[A]`（不一致是实读的）`[C]`（原因是推测）
- `[C]` Python 测试（31 文件 / 20,485 行）在 `ci.yml` 中找不到执行入口，只有本地 `bun run test:py`。是有意为之（robomp 是外围工具）还是遗漏，无法从仓库判断。`[A]`（CI 中无 pytest 是实证的）
- `[C]` `docs/` 是否有自动化的"文档与实现同步"检查（比如 doc 里引用的文件路径失效时报错），我没有找到；`.fallowrc.jsonc` 只管死代码。若无，则 `docs/` 的准确性依赖人工纪律。

---

## 附：可直接上 slide 的原始引文（中英对照备用）

1. **测试哲学的核心禁令** —— `AGENTS.md:250`
   > "Never source-grep. A test that reads an implementation file and asserts on its *text* is banned. It tests how code *looks*, not what it *does*: it breaks on harmless refactors and passes while the behavior is broken."

2. **规则的疤痕组织** —— `.omp/skills/tool-prompt-optimization/SKILL.md:79`
   > "`git blame` before cutting — MUST, not SHOULD. Many prompt lines were added on purpose after a real failure... They look redundant precisely because they now prevent the mistake. Keep scar tissue. Inferability is necessary for pruning, NEVER sufficient."

3. **文档为什么要放在 docs/** —— `packages/coding-agent/DEVELOPMENT.md:7-10`
   > "The long architecture walkthrough that used to live here drifted out of date faster than anyone re-read it."

4. **基准的目标** —— `packages/typescript-edit-benchmark/src/generate.ts:4-6`
   > "The goal is testing edit precision, not bug-finding ability. The mutation can be trivial — what matters is whether the model can surgically apply the patch in difficult contexts."

5. **CI 分片是实验出来的** —— `scripts/ci-test-ts.ts:69-74`
   > "Bisection showed no single file is at fault — the crash is cumulative heap volume. Under a 256MB-forced heap, a 10-file chunk aborts ~50% of runs while either 5-file half is 0/20."

6. **贡献流程被机器人改写** —— `CONTRIBUTING.md:30-32`
   > "If you intend to implement a change yourself, do not create an issue for it first. robomp treats actionable issues as work to pick up and may start the same fix in parallel."

7. **AI 辅助贡献的边界** —— `CONTRIBUTING.md:40-51`
   > "AI agents are welcome as tools, not as unattended contributors... You are responsible for the code, regardless of who or what generated it."
   > 且 PR body **必须包含至少一句你自己写的话**；"`bun check` passes" 本身不构成验证。
