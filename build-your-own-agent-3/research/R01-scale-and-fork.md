# R01 — omp 的规模、血统、版本节奏与「fork 成本模型」的下落

> 研究日期：2026-08-02
> 本地素材：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi`
> HEAD：`09a7c865636457c50ed75fc3b1a7cc21ef72c105`（2026-08-01 17:39:21 +0200，author `can1357`）
> 版本：`17.2.3`（`Cargo.toml:6`；`packages/*/package.json`）
> 对照素材：`/Users/overkazaf/playground/research/pi/pi-mono`（HEAD `583f153`，2026-08-01）
> 前作旧笔记：`build-your-own-agent/research/R08-ohmypi.md`（写于 v16.3.12）——本篇所有数字**全部在当前 HEAD 重新点算**，旧数字过时处以「旧 X → 新 Y」标出。
>
> **证据等级**：`[A]` = 本地仓库亲自点算/引用（给文件:行号或命令）；`[B]` = 权威二手且已核实；`[C]` = 存疑，只出现在 §8。

---

## 0. 结论先行（五条）

1. **`FORK.md` 在本地这份仓库里不存在，tier 成本模型也不存在。** `[A]` 旧笔记 §2 整节讲的 tier 模型，是**私有下游 fork 自己写的文件**，不是 `can1357/oh-my-pi` 上游的产物。本地这份是从 `can1357/oh-my-pi` 直接 clone 的，所以 §2 的所有引用在本篇**不成立**，必须换个讲法（见 §4）。
2. **规模比旧笔记涨了约 15%，且 Rust 侧涨得更凶。** `[A]` TS 源码 630,753 → **723,921** 行；自研 Rust 68/69k → **83,443** 行；vendor Rust 67,421 → **100,565** 行。
3. **这个仓库 23% 的 commit 是它自己写的。** `[A]` depth-200 窗口内 10,892 个 commit 里，作者 `roboomp <omp@can.ac>` 占 **2,497** 个——`python/robomp/README.md:1-5` 明写它是「Self-hosted GitHub triage bot，把 `omp --mode rpc` 当子进程驱动」。**omp 在用 omp 开发 omp。**
4. **节奏：约 155 commit/天，约 2.4 天一个版本号。** `[A]` 2026-06-01→07-30 共 9,300 commit；窗口内 195 个不同的 `bump version to` 版本号，跨 15.0.0 → 17.2.3。
5. **三套构建体系是分工不是重复**：bun workspace 管 TS 与产品、Cargo 管本地 Rust 迭代、Bazel 管 8 目标产物与 CI —— `MODULE.bazel:1-18` 把这个分工白纸黑字写清楚了。

---

## 1. 血统：三层，但本地这一层要重讲

### 1.1 当前状态表

| 层 | 仓库 | 关系 | 证据 |
|---|---|---|---|
| L1 上游本体 | `earendil-works/pi`（原 `badlogic/pi-mono`，Mario Zechner） | agent 工具包本体 | `[A]` `LICENSE:3` 保留其版权；`[A]` `docs/porting-from-pi-mono.md`（387 行）整篇讲怎么从 pi-mono 迁移 |
| L2 深度 fork | `can1357/oh-my-pi`（`omp`，Can Bölük） | pi 的**代码级深度 fork，仓库层面独立** | `[A]` `LICENSE:3-4` 双版权并列；`[A]` `Cargo.toml:11` `repository = "https://github.com/can1357/oh-my-pi"` |
| L3 私有下游 fork | **本地这份不是** | — | `[A]` `git remote -v` → `origin https://github.com/can1357/oh-my-pi.git`；`[A]` `git branch -a` 只有 `main` / `origin/main` |

**必须纠正旧笔记的地方** `[A]`：旧笔记 L3 行写的是「本地这份 = `xia0maiiii/oh-my-pi`，`FORK.md:3`」。本次素材**不是**那个私有 fork：

- `ls FORK.md` → 不存在；
- `git log --all --diff-filter=A --name-only` 在 depth-200 窗口内**从未出现过** `FORK.md`（只有同名无关文件：`docs/session-operations-export-share-fork-resume.md`、`packages/stats/test/fork-dedup.test.ts` 等）；
- `git log --all -- .github/workflows/fork-sync.yml` → 空；`.github/workflows/` 下只有 `ci.yml` 与 `bazel-cache-warm.yml`；
- `grep -rn "omp-fork(" packages/ crates/` → **0 条**（这与旧笔记 §2.5 的观察一致，但原因不同：不是「下游把足迹清零了」，而是**这里根本就是上游本身**）。

所以：**本篇讲的是 L2 上游本体的规模与节奏；tier 模型属于 L3 的工程实践，讲的时候必须换个出处（见 §4）。**

### 1.2 LICENSE 原文 `[A]`（`LICENSE:1-4`）

```
MIT License

Copyright (c) 2025 Mario Zechner
Copyright (c) 2025-2026 Can Bölük
```

双版权并列，是代码血缘最硬的本地证据。

### 1.3 与上游 pi 的体量对照 `[A]`

同一天（2026-08-01）两个仓库的 HEAD，用同口径点算：

| 维度 | `pi-mono`（HEAD `583f153`） | `oh-my-pi`（HEAD `09a7c865`） | 倍数 |
|---|---:|---:|---:|
| TS/TSX 源码（`*/src/*`，排除 test） | **112,232** 行 / 495 文件 | **723,921** 行 / 1,875 文件 | **6.45×** |
| Rust 文件数 | **0** | 418（自研 114 + vendor 304） | ∞ |
| Markdown 文件（全仓，排除 node_modules） | 97 | 122（仅 `docs/`） | — |
| workspace 包 | 9 | 16 | 1.8× |
| package.json version | `0.0.3`（monorepo 根，非发布号） | `17.2.3` | — |

> 口径说明：pi 侧命令为
> `find . -type f \( -name '*.ts' -o -name '*.tsx' \) -path '*/src/*' ! -path '*/node_modules/*' ! -name '*.test.ts' ! -path '*/test/*' | xargs wc -l`
> omp 侧同命令（把 `.` 换成 `packages`，并多排除 `*.spec.ts` / `tests` / `__tests__`）。

**一句话**：`[A]` **omp 的 TS 源码是 pi 的 6.45 倍，外加 pi 完全没有的 18.5 万行 Rust。**

---

## 2. 精确规模点算（源码 / 测试 / vendor 分开算）

> 全部命令在 `/Users/overkazaf/playground/research/ohmypi/oh-my-pi` 下、HEAD `09a7c865` 执行。

### 2.1 TypeScript / TSX `[A]`

命令：

```bash
# 源码：packages/*/src 下，排除 test 文件与 test 目录
find packages -type f \( -name '*.ts' -o -name '*.tsx' \) -path '*/src/*' \
  ! -path '*/node_modules/*' ! -name '*.test.ts' ! -name '*.test.tsx' ! -name '*.spec.ts' \
  ! -path '*/test/*' ! -path '*/tests/*' ! -path '*/__tests__/*' -print0 | xargs -0 wc -l | tail -1

# 测试：*.test.ts / *.spec.ts 或落在 test/tests/__tests__ 目录下
find packages -type f \( -name '*.ts' -o -name '*.tsx' \) ! -path '*/node_modules/*' \
  \( -name '*.test.ts' -o -name '*.test.tsx' -o -name '*.spec.ts' \
     -o -path '*/test/*' -o -path '*/tests/*' -o -path '*/__tests__/*' \) -print0 | xargs -0 wc -l | tail -1

# 全量
find packages -type f \( -name '*.ts' -o -name '*.tsx' \) ! -path '*/node_modules/*' -print0 | xargs -0 wc -l | tail -1
```

| 类别 | 行数 | 文件数 | 旧笔记（v16.3.12） |
|---|---:|---:|---|
| **源码**（`packages/*/src`，排除测试） | **723,921** | **1,875** | 旧 630,753 → 新 723,921（**+14.8%**） |
| **测试** | **538,157** | **2,011** | 旧 388,486 / 1,568 → 新 538,157 / 2,011（**+38.5%**） |
| **全量**（packages 下全部 .ts/.tsx） | **1,279,422** | **3,975** | 旧 1,039,493 → 新 1,279,422 |

> 差额说明 `[A]`：723,921 + 538,157 = 1,262,078，与全量 1,279,422 差 **17,344 行**——落在 `src/` 之外、又不属于测试的位置（各包的 `scripts/`、`bench/`、包根 `.ts` 等）。

**测试/源码比 = 0.74×**（旧 0.62×）。测试增速快于源码增速。

### 2.2 TS 逐包明细（src 行数，排除测试）`[A]`

| 包 | src 行数 | 文件数 | 备注 |
|---|---:|---:|---|
| `coding-agent` | **398,480** | 1,147 | 产品主体 |
| `catalog` | **105,235** | 70 | 其中 **88,892 行是 21 个 `*_pb.ts` 生成的 protobuf 客户端**（`packages/catalog/src/discovery/{cursor-gen,devin-gen}/…`）——**catalog 的「手写」源码其实只有约 1.6 万行** |
| `ai` | **99,265** | 278 | |
| `tui` | **25,666** | 37 | |
| `utils` | **20,480** | 83 | |
| `mnemopi` | **19,603** | 66 | |
| `agent` | **14,873** | 27 | |
| `stats` | **11,520** | 58 | |
| `collab-web` | **8,045** | 62 | |
| `hashline` | **6,904** | 19 | |
| `metaharness` | **5,825** | 7 | **新包**（旧笔记没有），`packages/metaharness/README.md:1-6`：统一 Harbor / TypeScript-edit / SnapCompact 三套 benchmark |
| `typescript-edit-benchmark` | **4,382** | 10 | |
| `snapcompact` | **2,020** | 2 | |
| `swarm-extension` | **1,179** | 8 | |
| `wire` | **444** | 1 | |
| `natives` | 0（src 为生成物） | — | |

包总数 **16**（`ls -d packages/*/`）。相比旧笔记：`terminal-bench` 消失，`metaharness` 新增。

**一个必须点出来的口径陷阱** `[A]`：旧笔记把 catalog 的 98,590 行当作「模型目录包很大」的证据。实际上其中 **90%（88,892/105,235）是 protoc 生成的 `*_pb.ts`**，是 Cursor / Devin(Windsurf/Codeium) 转售商协议的机器产物。上 slide 时应说「catalog 手写代码约 1.6 万行 + 8.9 万行生成的 protobuf 客户端」。

### 2.3 Rust `[A]`

命令：

```bash
# 自研 crate 的 src
find crates -name '*.rs' -not -path 'crates/vendor/*' -path '*/src/*' -print0 | xargs -0 wc -l | tail -1
# 自研 crate 全部（含 tests/benches/build.rs）
find crates -name '*.rs' -not -path 'crates/vendor/*' -print0 | xargs -0 wc -l | tail -1
# vendored 第三方
find crates/vendor -name '*.rs' -print0 | xargs -0 wc -l | tail -1
```

| 类别 | 行数 | 文件数 |
|---|---:|---:|
| **自研 Rust 源码**（`crates/pi-*/src`） | **83,443** | 108 |
| 自研 Rust 全部（含 tests/benches） | 84,448 | 114 |
| 自研 Rust 的 tests + benches | 840 | 3 |
| **vendored 第三方**（`crates/vendor/*`） | **100,565** | **304** |
| **Rust 合计** | **185,013** | 418 |

逐 crate（全部 `.rs`）：

| Crate | 行数 | 文件 | 职责 |
|---|---:|---:|---|
| `pi-shell` | **41,523** | 49 | 嵌入式 bash（brush fork）+ 进程树 + 输出 minimizer + coreutils builtin 宿主 |
| `pi-natives` | **23,180** | 37 | 唯一的 napi-rs cdylib，聚合全部能力 |
| `pi-walker` | **6,182** | 4 | 并行 FS 遍历 + 进程内扫描缓存 |
| `pi-iso` | **4,047** | 10 | 跨平台写时复制工作区隔离 PAL |
| `pi-uu-grep` | **3,863** | 2 | 进程内 `grep`/`rg` builtin |
| `pi-ast` | **3,402** | 6 | tree-sitter 摘要 / 块边界 |
| `pi-voice` | **1,197** | 4 | **新 crate**（旧笔记没有） |
| `pi-uu-diff` | **608** | 1 | **新 crate**（旧笔记没有） |
| `pi-uutils-ctx` | **446** | 1 | thread-local stdio/cwd/env/cancel 垫片 |

`crates/vendor/` 共 **49 个 vendored crate** `[A]`（`ls crates/vendor | wc -l`）：`brush-core`、`brush-builtins`、`jaq`，加 **46 个 `uu-*`**（uutils coreutils 的逐命令 crate：`uu-cat`/`uu-sed`/`uu-sort`/`uu-find`/`uu-xargs`/…）。

`Cargo.toml:1-3` `[A]`：
```toml
[workspace]
members = ["crates/pi-*", "crates/vendor/*"]
resolver = "3"
```

**对比旧笔记** `[A]`：自研 Rust 69,901 → **83,443**（+19.4%，且 crate 数 7 → **9**）；vendor 67,421 → **100,565**（+49.2%，vendor 扩张比自研更快）。

**README 自称 vs 实测的口径差** `[A]`：`README.md:27` 写
> `**40+** providers · **32** built-in tools · **14** lsp ops · **28** dap ops · **~55k** lines of Rust core.`

而本地 v17.2.3 实测自研 Rust src = **83,443 行**。README 的「~55k」大概率是排除了 `pi-shell` 里的 minimizer 之类的口径，**上 slide 请用「8.3 万行自研 Rust（v17.2.3 本地实测，排除 vendor）」并注明口径**，或直接引 README 并标为官方口径。

### 2.4 Python `[A]`

命令：`find <dir> -name '*.py' ! -path '*/node_modules/*' | xargs wc -l`

| 位置 | 行数 | 文件数 | 是什么 |
|---|---:|---:|---|
| `python/robomp` | **32,453** | 59 | 自托管 GitHub triage bot（见 §5.3） |
| `packages/snapcompact/research` | **29,101** | 77 | snapcompact 的离线 eval / 研究脚本 |
| `python/omp-rpc` | **6,844** | 10 | Python 侧 RPC 客户端 |
| 其余（`scripts/`、`packages/*/scripts`、`eval/py`…） | ~15,036 | 21 | 零散工具 |
| **全仓合计** | **83,434** | **167** | |

Python 是旧笔记完全没提的一块，**8.3 万行，和自研 Rust 一个量级**。

### 2.5 总量卡片（可直接上 slide）`[A]`

| 维度 | v17.2.3 实测 | 旧笔记 v16.3.12 |
|---|---:|---:|
| TS/TSX 源码 | **723,921** 行 / 1,875 文件 | 630,753 |
| TS/TSX 测试 | **538,157** 行 / 2,011 文件 | 388,486 / 1,568 |
| 自研 Rust | **83,443** 行 / 9 crate | 69,901 / 7 crate |
| vendored Rust | **100,565** 行 / 49 crate | 67,421 |
| Python | **83,434** 行 / 167 文件 | 未统计 |
| **合计（源码+测试+vendor+Python）** | **≈ 152.9 万行** | — |
| bun workspace 包 | **16** | 16 |
| `docs/` Markdown | **122 篇 / 27,931 行** | 121 / 27,073 |
| 包内 prompt `.md`（`packages/**/src/**.md`） | **243** | 226 |
| 内置工具 | **29 + 2 隐藏**（见下） | 30 + 5 |
| 模型目录 | **63 provider / 4,106 条目 / 2.17 MB** | 58 / 3,695 / 1.84 MB |
| 版本号 | TS 与 Rust 共用 **17.2.3** | 16.3.12 |

工具清单变化 `[A]`（`packages/coding-agent/src/tools/index.ts:405-441`）：
- `BUILTIN_TOOLS` = **29 个**：read / security_scan / bash / edit / ast_grep / ast_edit / ask / debug / eval / github / glob / grep / lsp / inspect_image / browser / computer / checkpoint / rewind / task / hub / todo / web_search / write / memory_edit / retain / recall / reflect / learn / manage_skill
- `HIDDEN_TOOLS` = **2 个**（`:437-440`）：yield / goal
- 相比旧笔记**新增** `security_scan` / `computer` / `hub`；**移除** `ssh` / `irc` / `job` / `search_tool_bm25` / `report_finding` / `report_tool_issue` / `resolve`
- **`DEFAULT_ESSENTIAL_TOOL_NAMES` 与 `search_tool_bm25` 在当前 HEAD 已不存在** `[A]`（`grep -n "ESSENTIAL" packages/coding-agent/src/tools/index.ts` 无命中）。旧笔记 §3.1 第 8 条「6 个 essential + BM25 发现」**已过时**——现在的机制是 `xd://` 挂载（`tools/index.ts:667` 注释：「Ordinary sessions use xd:// for discoverable built-ins, custom tools, and…」）。讲这条时必须改口径。

模型目录点算命令 `[A]`：
```bash
python3 -c "import json;m=json.load(open('packages/catalog/src/models.json'));\
print(len(m), sum(len(v) for v in m.values() if isinstance(v,(dict,list))))"
# → 63 4106
ls -l packages/catalog/src/models.json   # → 2,171,711 bytes
```

---

## 3. `docs/` 目录：122 篇，工程文化的最硬证据

`[A]` 命令：`find docs -name '*.md' | wc -l` → **122**；`find docs -name '*.md' | xargs wc -l | tail -1` → **27,931** 行。

### 3.1 分布

| 目录 | 篇数 |
|---|---:|
| `docs/*.md`（顶层） | **76** |
| `docs/tools/*.md` | **31** |
| `docs/toolconv/*.md` | **9** |
| `docs/skills/*.md` | **3** |
| `docs/skills/examples/**`（3 个示例扩展各 1 篇） | **3** |
| **合计** | **122** |

### 3.2 顶层 76 篇的分类（我按文件名与内容归纳，`[A]` 文件名逐个来自 `ls docs/*.md`）

| 类别 | 篇数 | 代表文件 |
|---|---:|---|
| **Rust natives 子系统**（`natives-*` + `native-crates` + `porting-to-natives` + `fs-scan-cache-architecture`） | **9** | `natives-architecture.md`、`natives-binding-contract.md`、`natives-rust-task-cancellation.md`、`natives-shell-pty-process.md`、`natives-build-release-debugging.md`(430 行) |
| **Provider / 模型 / 传输层** | **10** | `providers.md`、`models.md`(749)、`adding-a-provider.md`、`provider-endpoint-constraints.md`(395)、`provider-streaming-internals.md`、`local-models.md`、`auth-broker-gateway.md`、`ai-schema-normalize.md`、`ERRATA-GPT5-HARMONY.md`、`computer-use.md` |
| **MCP** | **4** | `mcp-config.md`(498)、`mcp-protocol-transports.md`、`mcp-runtime-lifecycle.md`、`mcp-server-tool-authoring.md` |
| **Session / 压缩 / 记忆** | **8** | `session.md`(483)、`session-tree-plan.md`、`session-operations-export-share-fork-resume.md`、`session-switching-and-recent-listing.md`、`compaction.md`(423)、`non-compaction-retry-policy.md`、`memory.md`、`mnemosyne-memory-backend.md` |
| **可扩展性**（hooks / extensions / skills / 插件市场 / 自定义工具） | **9** | `extensions.md`(484)、`extension-loading.md`、`hooks.md`、`skills.md`、`custom-tools.md`、`marketplace.md`、`plugin-manager-installer-plumbing.md`、`slash-command-internals.md`、`gemini-manifest-extensions.md` |
| **配置发现 / 设置 / 环境** | **8** | `settings.md`(811)、`environment-variables.md`(444)、`config-usage.md`、`context-files.md`、`secrets.md`、`install-id.md`、`keybindings.md`、`theme.md` |
| **TUI** | **3** | `tui.md`、`tui-core-renderer.md`、`tui-runtime-internals.md` |
| **工具运行时细节** | **7** | `bash-tool-runtime.md`、`notebook-tool-runtime.md`、`resolve-tool-runtime.md`、`python-repl.md`、`lsp-config.md`、`approval-mode.md`、`magic-keywords.md` |
| **协议 / SDK / 集成** | **4** | `rpc.md`(**812 行，全 docs 最长**)、`sdk.md`、`tree.md`、`user-facing-packages.md` |
| **特色子系统** | **6** | `advisor-watchdog.md`、`ttsr-injection-lifecycle.md`、`collab.md`、`vibe-mode.md`、`rulebook-matching-pipeline.md`、`blob-artifact-architecture.md` |
| **迁移 / 发布 / 运维** | **4** | `porting-from-pi-mono.md`(387)、`macos-signing-notarization.md`、`handoff-generation-pipeline.md`、`system-prompt-customization.md` |
| 其余 | 4 | `arktype-guide.md`、`task-agent-discovery.md`、`fs-scan-cache-architecture.md`… |

### 3.3 三个可以直接讲的观察 `[A]`

1. **最长的文档是 `docs/rpc.md`（812 行）**，其次 `settings.md`(811)、`models.md`(749)。**协议文档比设置文档还长**——说明 omp 把「被别的程序驱动」当一等场景。
2. **`docs/tools/` 有 31 篇，几乎一个工具一篇。** 加上 `docs/toolconv/` 9 篇（工具调用格式转换，`toolconv/anthropic.md` 630 行）——工具面被当成公开 API 在写文档。
3. **`docs/natives-*` 独占 9 篇**，包括「怎么把东西移进 Rust」（`porting-to-natives.md`）和「怎么调试 native 构建」（`natives-build-release-debugging.md`, 430 行）。**一个子系统配 9 篇文档，是这个仓库工程文化最直白的量化指标。**

补充证据 `[A]`：`.omp/` 目录说明这个仓库还给自己配了 agent 工作流——`.omp/commands/{review-prs,fix-issues,triage,release}.md` 四个 slash command，`.omp/skills/{semantic-compression,system-prompts,tool-prompt-optimization}/` 三个 skill。**仓库在用自己的产品维护自己。**

---

## 4. 「tier 成本模型」：本地没有，必须改讲法

### 4.1 事实澄清 `[A]`

- `FORK.md` **不存在**（`ls FORK.md` 无此文件；depth-200 git 历史内也从未添加过）。
- `AGENTS.md`（282 行）、`CONTRIBUTING.md`（90 行）、`README.md`（633 行）中 **grep `-i tier` 只有一处命中，且无关**：`README.md:308` 是标题「### Frontier APIs」里的 "Frontier" 子串。
- 全仓 `grep -rn "lowest tier that works\|Tier 0 —\|Tier 2 —\|out-of-core" --include='*.md'` **唯一命中**是 `.omp/skills/semantic-compression/SKILL.md:28`「**Tier 2 — Delete unless meaning changes:**」——那是**文本压缩 skill 的删除激进度分级**，和 fork 成本模型毫无关系。**别讲混了。**
- `grep -rn "omp-fork(" packages/ crates/` → **0 条**。

**结论** `[A]`：旧笔记 §2 引用的 `FORK.md:15-19 / :21 / :46 / :60-64 / :74-91 / :95-104 / :169-174` **在本次素材中全部无法复现**。那份 FORK.md 是私有下游 fork（`xia0maiiii/oh-my-pi`）自己写的维护手册，不是上游文件。

### 4.2 演讲怎么办：两条合法路径

**路径 A（推荐）——明确标注出处切换。**
tier 模型本身仍然是好东西，但要说清楚：「这是**一个下游 fork 维护者**为了跟上 omp 而写的方法论文档，不在 omp 上游仓库里」。引用时用旧笔记 R08 §2 作为二手出处 `[B]`（旧笔记是在那份私有 fork 上亲自点算的），**不要在本篇的 `文件:行号` 体系下伪造成本地证据**。

**路径 B——用上游自己的成本约束替换。**
`can1357/oh-my-pi` 上游有它自己的一套「降低协作成本」的规矩，**这些是本地可引的**：

1. **`CONTRIBUTING.md:19-26`**——大改动必须先在 Discord 讨论：
   > "Discuss major features and broad architectural or behavioral changes in [Discord] **before writing the implementation**. This includes new subsystems, large UI changes, new dependencies, and changes that span several packages. A GitHub issue is not a substitute for this discussion, and prior discussion does not guarantee that a pull request will be merged."

2. **`CONTRIBUTING.md:28-32`**——**不要为你自己要做的活开 issue**，理由极其现代：
   > "If you intend to implement a change yourself, **do not create an issue for it first**. robomp treats actionable issues as work to pick up and may start the same fix in parallel, wasting compute and maintainer time."

   **这句话是本篇最有冲击力的一条**：贡献指南里出现了「机器人会把 issue 当工单抢着做，会浪费算力」这种约束——**协作规则第一次要为 AI 贡献者让路。**

3. **`CONTRIBUTING.md:38-51`**——AI 辅助贡献的四条硬要求：
   > "AI agents are welcome as tools, not as unattended contributors. Do not give an agent a vague goal and submit whatever it produces."
   > 必须：约束 agent 到议定范围、审阅每个改动文件、亲自跑检查并验证行为、审阅后才提交 PR。
   > "You are responsible for the code, regardless of who or what generated it."

4. **`CONTRIBUTING.md:55-57 / 64-74`**——PR 正文**必须有至少一句你自己写的话**；`bun check` 通过**不算**验证：
   > "Every pull request body **MUST include at least one sentence written by you, in your own words**…"
   > "「`bun check` passes」by itself is not sufficient verification."

5. **`AGENTS.md`（282 行）里的成本型硬规矩**，同样可引：
   - `AGENTS.md:41`：「**Prompts**: never build prompts in code (no inline strings, template literals, or concatenation). Prompts live in static `.md` files」——243 个 prompt `.md` 是这条规矩的产物。
   - `AGENTS.md:58`：「Search first: `grep` for the operation before implementing it. **Two implementations of the same thing is a bug even when both work.**」
   - `AGENTS.md:175`：「**NEVER edit `packages/catalog/src/models.json` directly.**」
   - `AGENTS.md:36`：「**NEVER use inline imports**」；`:35`：「**NEVER use `ReturnType<>`**」

**我的建议**：slide 上讲 tier 模型时打一行小字「出自某下游 fork 的 FORK.md，非 omp 上游文件」，然后立刻切到 `CONTRIBUTING.md:28-32` 的 robomp 条款——**后者是本地可验证的、且更有时代冲击力的一手材料。**

---

## 5. 版本与演进节奏

### 5.1 数据窗口的限制（必须先说）`[A]`

本地是 `git clone --depth 200`：

- `.git/shallow` 存在，含 **32 行**（32 个 shallow 边界 commit）；
- `git rev-list --count HEAD` = **10,892**（depth 200 是按每条 tip 谱系算的，合并进来的分支使可达 commit 远超 200）；
- 日期范围 **2026-05-11 → 2026-08-01**（约 82 天），**首尾两天不完整**；
- 本地 `git tag` 只有 **182** 个（`v15.1.9` … `v17.2.3`），**不是仓库全部 tag**（旧笔记记录上游累计 790 tag `[B]`）。

**所以：所有 git 统计只对「2026-05-11 起的约 82 天窗口」有效，不代表项目全史。上 slide 请标注这个口径。**

### 5.2 commit 频率 `[A]`

| 口径 | commit 数 | 天数 | 日均 |
|---|---:|---:|---:|
| 全窗口 2026-05-11 → 08-01 | 10,892 | ~82 | ~133 |
| **2026-06-01 → 07-30（完整 60 天）** | **9,300** | 60 | **≈155** |
| 2026-07-02 → 07-30（完整 29 天） | 4,392 | 29 | ≈151 |

单日峰值 `[A]`：`2026-07-23` **275 个**；`2026-07-17` 253；`2026-07-27` 235；`2026-07-14` 244。低谷 `2026-07-19` 21 个（周日）。

命令：`git log --format='%ad' --date=short | sort | uniq -c`

### 5.3 作者分布——最值得讲的一节 `[A]`

`git log --format='%an|%ae' | sort | uniq -c | sort -rn`：

| 排名 | 作者 | commit | 占比 |
|---|---|---:|---:|
| 1 | `can1357 <me@can.ac>` | **5,618** | 51.6% |
| 2 | **`roboomp <omp@can.ac>`** | **2,497** | **22.9%** |
| 3 | `Can Bölük <can1357@users.noreply.github.com>` | 315 | 2.9% |
| 4 | `Mathews-Tom` | 219 | 2.0% |
| 5 | `metaphorics` | 206 | 1.9% |
| 6 | `oldschoola` | 138 | 1.3% |
| 7 | `usr-bin-roygbiv` | 117 | 1.1% |
| 8 | `Wolfgang Schoenberger` | 111 | 1.0% |

- **窗口内不同 author 名共 232 个** `[A]`（`git log --format='%an' | sort -u | wc -l`）。
- **1 + 3 名合并（同为 Can Bölük）= 5,933 = 54.5%**。
- **roboomp = 22.9%**。它是什么？`python/robomp/README.md:1-5` 原文 `[A]`：
  > "# roboomp
  > Self-hosted GitHub triage bot. Drives [`omp --mode rpc`] as a subprocess against a per-issue git worktree, then writes back to GitHub through a sidecar that holds the PAT."

  它的行为（同文件 `:7-22`）`[A]`：issue 开启时自动分类打标签；`bug`/`documentation` → **复现、在新分支上修、开带 `## Repro`/`## Cause`/`## Fix`/`## Verification` 与 `Fixes #N` 的 PR**；`question` → 一条评论 + 4 小时无 👎 自动关闭；后续评论用 `--continue` 恢复同一个 omp session。
- roboomp 的活动区间 `[A]`：**2026-05-15 → 2026-08-01**（几乎覆盖整个窗口）。它的 commit 长这样：`fix(mnemopi): anchored think stripping to leading blocks`、`fix(coding-agent): clear bash auto-background threshold timer`——**是真 bugfix，不是格式化机器人。**
- 其他 bot 身份 `[A]`：`oh-my-pi-bot`、`github-actions[bot]`、`robomp-bot`、`Hermes DevOps Bot` 也在作者列表里（量级小）。

**这一条上 slide 的说法**：`[A]` **oh-my-pi 有 22.9% 的 commit 由它自己驱动的 bot 写；而 `CONTRIBUTING.md:28-32` 甚至要求人类贡献者别开 issue，免得抢了 bot 的活。**

### 5.4 最近在改什么 `[A]`

commit scope 分布（`git log --format='%s' | grep -oE '^[a-z]+(\([^)]+\))?' | sort | uniq -c | sort -rn`）：

| scope | 次数 |
|---|---:|
| `fix(coding-agent)` | 1,026 |
| `fix(ai)` | 557 |
| `fix(tui)` | 486 |
| `chore` | 446 |
| `feat(coding-agent)` | 350 |
| `style` | 251 |
| `fix`（无 scope） | 213 |
| `fix(agent)` | 192 |
| `test(coding-agent)` | 176 |
| `merge` | 163 |
| `fix(catalog)` | 137 |
| `feat` / `feat(ai)` | 124 / 120 |
| `fix(session)` / `fix(cli)` / `fix(advisor)` / `fix(mcp)` | 109 / 89 / 81 / 79 |

**fix 压倒性多于 feat**（粗算 fix 系 ≈2,900+ vs feat 系 ≈600+，约 **4.8:1**）——这是一个已经进入「稳定期高频修 bug」而非「狂加功能」的项目。

改动最密集的目录（窗口内 `git log --name-only` 的路径前两段计数）`[A]`：

| 目录 | 文件改动次数 |
|---|---:|
| `packages/coding-agent` | 90,531 |
| `packages/ai` | 22,094 |
| `packages/utils` | 5,780 |
| `packages/tui` | 5,774 |
| `crates/pi-shell` | 5,110 |
| `packages/catalog` | 4,574 |
| `crates/vendor` | 4,571 |
| `packages/mnemopi` | 4,161 |
| `python/robomp` | 3,514 |
| `packages/snapcompact` | 3,276 |

> 注 `[A]`：列表里出现的 `crates/brush-core-vendored`(2,066) / `crates/brush-builtins-vendored`(1,139) 是**窗口内被重命名到 `crates/vendor/` 之前的旧路径**——目录重构在窗口期内发生过。

### 5.5 版本号从哪来、发得多快 `[A]`

- **单一版本号真源**：`Cargo.toml:6` `version = "17.2.3"`，且 **16 个 TS 包里 13 个的 `package.json` version 也是 `17.2.3`**（例外：`collab-web` 停在 `16.3.6`；`metaharness` 与 `typescript-edit-benchmark` 是 `0.0.1` 的内部包）。**TS 与 Rust 共用同一个版本号**这一点旧笔记记录正确，且在 v17.2.3 仍成立。
- **CHANGELOG**：14 个包各自带 `CHANGELOG.md`（`packages/{catalog,utils,agent,swarm-extension,ai,hashline,natives,mnemopi,stats,collab-web,snapcompact,coding-agent,wire,tui}/CHANGELOG.md`）`[A]`。根目录**没有** CHANGELOG——版本记录是**逐包**的。
- **发布节奏** `[A]`：窗口内 `git log --format='%s' | grep -oE 'bump version to [0-9.]+' | sort -u | wc -l` = **195 个不同版本号**，从 `15.0.0`（2026-05-13）到 `17.2.3`（2026-08-01）。**80 天走了 195 个版本号 ≈ 2.4 天一个版本，跨两个大版本号。**
- 本地 tag `[A]`：182 个，`v15.1.9`(2026-05-21) → `v17.2.3`(2026-08-01)。
- **对比旧笔记**：旧笔记记录本地停在 `v16.3.12`（2026-07-08），最新是 `v17.2.2`（2026-07-31）`[B]`。本次 HEAD 已是 **v17.2.3**（2026-08-01），即上游又前进了一个 patch。

---

## 6. 构建体系：bun + Cargo + Bazel，三套并存的分工

### 6.1 三者的边界（`MODULE.bazel:1-18` 把它写死了）`[A]`

`MODULE.bazel` 开头的 docstring 原文：

> """oh-my-pi — Bazel build for the native (Rust) side of the workspace.
> Builds the pi_natives NAPI cdylib for every shipped target with hermetic toolchains, **replacing cargo-zigbuild/cargo-xwin/sccache plus the hand-rolled CI caches** with Bazel's content-addressed action cache (see infra/bazel-remote.yaml).
> Layout:
>   `//:natives-<target>`      release-grade renamed .node artifacts (root BUILD.bazel)
>   `//crates/...`             first-party crate targets
>   `//bazel/...`              platforms, ISA-variant constraints, toolchains, rules
>   `@crates//...`             third-party crates from Cargo.lock via crate_universe
> **The cargo workspace stays authoritative for local iteration** (rust-analyzer, `cargo nextest`, napi typedef regeneration); **Bazel is the artifact and CI pipeline**. `crate_universe` derives the Bazel dependency graph directly from Cargo.toml/Cargo.lock and the module annotations; no separate repin step is required."""

**一句话总结**：`[A]` **Cargo 是本地开发的真源，Bazel 是产物与 CI 的真源，两者共用同一份 `Cargo.toml`/`Cargo.lock`（通过 `crate_universe` 派生），不需要单独 repin。**

### 6.2 各自管什么

| 体系 | 管什么 | 证据 |
|---|---|---|
| **bun workspace** | TS 侧全部：16 个 `packages/*` + `python/robomp/web`；依赖版本用 `catalog:` 协议集中锁定；3 个 patch 包；所有 `check`/`lint`/`test`/`build`/`fmt` 的入口 | `[A]` `package.json:1-30`（`"packageManager": "bun@1.3.14"`、`workspaces.packages = ["packages/*", "python/robomp/web"]`、`workspaces.catalog` 集中版本表、`patchedDependencies` 3 项） |
| **Cargo** | 本地 Rust 迭代：rust-analyzer、`cargo nextest`、napi typedef 再生成；workspace members = `crates/pi-*` + `crates/vendor/*`；`resolver = "3"`；`[patch.crates-io]` 把 `brush-core`/`brush-builtins` 指向本地 vendor | `[A]` `Cargo.toml:1-14`；`rust-toolchain.toml`、`rustfmt.toml`、`rust-analyzer.toml` 均在根 |
| **Bazel** | 8 个发布目标的 `.node` cdylib 产物 + CI 上的 test/clippy/rustfmt | `[A]` `BUILD.bazel:16-24` 的 `_ADDONS` 字典列出 8 个目标；`.github/workflows/ci.yml:147-176` |

Bazel 的 8 个发布目标 `[A]`（`BUILD.bazel:16-24`）：
`linux-x64-baseline` / `linux-x64-modern` / `linux-arm64` / `linux-musl-x64-baseline` / `linux-musl-arm64` / `darwin-x64-baseline` / `darwin-arm64` / `win32-x64-baseline`

> 注意 `linux-x64-baseline` 与 `linux-x64-modern` 并存 `[A]`——**同一个平台按 ISA 变体（`//bazel/variants`）出两份产物**，即 x86-64 老 CPU 与带新指令集的 CPU 各一份。这是很少见的发行粒度。

全仓 **66 个 `BUILD.bazel`** `[A]`（`find . -name 'BUILD.bazel' | grep -v node_modules | wc -l`）。

### 6.3 CI 里的三套联动 `[A]`（`.github/workflows/ci.yml`）

- `:137` `run: bun run ci:check:full` —— TS 侧检查走 bun
- `:139` `run: bun run collab:web:build`
- `:147` job `Validate Rust workspace (bazel)` → `:162` `bazelisk test //crates/...`
- `:169-174` **clippy 分两档**：`pi-ast`/`pi-iso`/`pi-natives`/`pi-shell`/`pi-voice`/`pi-walker` 用 `--config=clippy-strict`；其余（排除 `vendor/brush-core`、`vendor/brush-builtins`）用普通 `--config=clippy`。注释 `:163-166` 说明：「Clippy scope mirrors `cargo clippy --workspace` (libraries only…) … brush fork is exempt (same as run-rs-task.ts's cargo excludes)」——**Bazel 侧刻意与 Cargo 侧保持同一套豁免规则**，这是两套构建共存时最容易漂移的地方，他们专门写了注释锁住。
- `:176` `bazelisk build --config=rustfmt //crates/...`
- `:187` job `Build native addons (bazel)`
- 另有独立 workflow `bazel-cache-warm.yml` 预热缓存 `[A]`

根 `package.json` 的脚本层把三套黏在一起 `[A]`：
```
check    = bun run --parallel check:ts check:rs
check:rs = bun scripts/run-rs-task.ts check:rs      # bun 脚本转调 cargo
test:rs  = bun scripts/run-rs-task.ts test:rs
build:native = bun --cwd=packages/natives run build
```
即 **bun 是唯一的人类入口**，Cargo/Bazel 藏在 `scripts/*.ts` 后面。

---

## 7. 相对旧笔记的「旧 X → 新 Y」总表

| 项 | 旧（v16.3.12） | 新（v17.2.3, HEAD `09a7c865`） | 变化 |
|---|---:|---:|---|
| 版本号 | 16.3.12 | **17.2.3** | 跨一个大版本 |
| TS 源码 | 630,753 | **723,921** | +14.8% |
| TS 测试 | 388,486 / 1,568 文件 | **538,157 / 2,011** | +38.5% |
| TS 全量 | 1,039,493 | **1,279,422** | +23.1% |
| 自研 Rust | 69,901 | **83,443** | +19.4% |
| vendor Rust | 67,421 | **100,565** | +49.2% |
| 自研 crate 数 | 7 | **9**（新增 `pi-voice`、`pi-uu-diff`） | +2 |
| vendor crate 数 | 未点算 | **49** | — |
| Python | 未统计 | **83,434 / 167 文件** | 新维度 |
| workspace 包 | 16 | **16**（`terminal-bench` 去，`metaharness` 来） | 持平 |
| `docs/` | 121 篇 / 27,073 行 | **122 篇 / 27,931 行** | +1 篇 |
| `docs/*.md` 顶层 | 73 | **76** | +3 |
| `docs/tools/` | 33 | **31** | −2 |
| prompt `.md` | 226 | **243** | +17 |
| 内置工具 | 30 + 5 隐藏 | **29 + 2 隐藏** | 见 §2.5 增删清单 |
| catalog provider / 模型 / 大小 | 58 / 3,695 / 1.84 MB | **63 / 4,106 / 2.17 MB** | +5 / +411 / +18% |
| catalog 包 src | 98,590 | **105,235**（其中 88,892 为生成 protobuf） | 口径修正 |
| `coding-agent` src | 336,468 | **398,480** | +18.4% |
| `ai` src | 85,793 | **99,265** | +15.7% |
| `FORK.md` / tier 模型 | 存在（L3 私有 fork） | **不存在** | §4 已重写 |
| `DEFAULT_ESSENTIAL_TOOL_NAMES` + BM25 | 存在 | **已移除**，改 `xd://` 挂载 | 讲法需更新 |

---

## 8. 存疑区（`[C]`，不得当结论用）

| # | 存疑项 | 说明 | 处理 |
|---|---|---|---|
| 1 | `[C]` 全仓真实 commit 总数 / tag 总数 | 本地 depth-200 只看到 10,892 commit、182 tag。旧笔记记的 16,594 commit / 790 tag 是 GitHub API 数（`[B]`，且已过时 25 天）。**本篇未联网核实。** | slide 上只写「近 60 天日均 ≈155 commit（本地 depth-200 窗口实测）」，不写全史总数 |
| 2 | `[C]` roboomp 的 2,497 commit 中有多少是「自主开的 PR 被合并」vs「维护者用 omp 辅助后署名 roboomp」 | `omp@can.ac` 与 `me@can.ac` 同域，无法从 git 元数据区分 | 说「22.9% 的 commit 署名给项目自己的 bot 账号 `roboomp`」，**不要说「22.9% 的代码是 AI 独立写的」** |
| 3 | `[C]` 232 个 author 的去重后真人数 | 同一人多身份（`can1357` / `Can Bölük`；`usr-bin-roygbiv` / `usr_bin_roygbiv`）已发现至少 2 组；bot 账号至少 5 个 | 说「窗口内 200+ 个提交身份」更稳 |
| 4 | `[C]` README「~55k lines of Rust core」的口径 | 与本地实测 83,443 差 28k。可能排除 `pi-shell` minimizer、可能只算 `pi-natives` | 用本地口径并注明；或引 README 并标官方口径 |
| 5 | `[C]` 那份 `FORK.md`（tier 模型）现在还在不在 | 旧笔记引的是 `xia0maiiii/oh-my-pi`。本次素材换成上游 clone，**无法验证该私有 fork 现状** | 引用时一律标「据 R08 旧笔记记录，出自某下游 fork」 |
| 6 | `[C]` `packages/snapcompact/research/` 的 29,101 行 Python 是否随发布分发 | 未核实 `.npmignore`/`files` 字段 | 统计时单列，不并入「产品代码」 |
| 7 | `[C]` `crates/brush-core-vendored` → `crates/vendor/brush-core` 重命名的确切 commit | 窗口内 `git log --name-only` 两个路径都出现，未逐 commit 追 | 只说「窗口期内 vendor 目录做过重构」 |
| 8 | `[C]` 上游 pi 的 `0.0.3` 是什么 | pi-mono 根 `package.json` version = `0.0.3`，与 npm 上 `@earendil-works/pi-coding-agent` 的发布号不是一回事 | 不做版本号对比 |

---

## 9. 最适合上 slide 的 5 条（本篇结论）

1. **`[A]` omp 的 TS 源码是上游 pi 的 6.45 倍（723,921 vs 112,232 行），外加 pi 完全没有的 18.5 万行 Rust（8.3 万自研 + 10.1 万 vendored）+ 8.3 万行 Python。全仓约 153 万行。**（同日 HEAD 对照，命令见 §1.3/§2）

2. **`[A]` 这个仓库 22.9% 的 commit 署名给它自己驱动的 bot：`roboomp <omp@can.ac>`，2,497 / 10,892。`python/robomp/README.md:1-5` 明写它把 `omp --mode rpc` 当子进程跑，自动分类 issue、复现、修、开 PR。omp 在用 omp 开发 omp。**

3. **`[A]` `CONTRIBUTING.md:28-32`：「不要为你自己要做的活开 issue —— robomp 会把可行动的 issue 当工单捡起来，可能并行做同一个修复，浪费算力和维护者时间。」贡献指南第一次要为 AI 贡献者让路。**

4. **`[A]` 节奏：近 60 天（2026-06-01→07-30）9,300 个 commit ≈ 155/天，单日峰值 275（07-23）；80 天内走了 195 个版本号（15.0.0 → 17.2.3），约 2.4 天一个版本。TS 与 Rust 共用同一个版本号（`Cargo.toml:6` = `packages/*/package.json`）。**

5. **`[A]` `FORK.md` 与 tier 成本模型在 `can1357/oh-my-pi` 上游里根本不存在——那是某个下游 fork 自己写的维护手册。上游自己的工程文化证据是另一套：122 篇 / 27,931 行 `docs/`（光 Rust natives 子系统就 9 篇）、243 个 prompt `.md` 文件、以及三套并存的构建体系——`MODULE.bazel:1-18` 白纸黑字分工：「Cargo 是本地迭代的真源，Bazel 是产物与 CI 的真源」，Bazel 出 8 个发布目标（含 x86-64 baseline/modern 两个 ISA 变体）。**

---

## 10. 附：本篇用到的全部点算命令

```bash
cd /Users/overkazaf/playground/research/ohmypi/oh-my-pi

# --- 血统 ---
git remote -v; git branch -a; git log -1 --format='%H %ad %an' --date=iso
ls FORK.md; git log --all --diff-filter=A --name-only --format='' | grep -i fork | sort -u
grep -rn "omp-fork(" packages/ crates/ | wc -l
grep -rn "lowest tier that works\|Tier 0 —\|Tier 2 —\|out-of-core" --include='*.md' .

# --- TS ---
find packages -type f \( -name '*.ts' -o -name '*.tsx' \) -path '*/src/*' \
  ! -path '*/node_modules/*' ! -name '*.test.ts' ! -name '*.test.tsx' ! -name '*.spec.ts' \
  ! -path '*/test/*' ! -path '*/tests/*' ! -path '*/__tests__/*' -print0 | xargs -0 wc -l | tail -1
find packages -type f \( -name '*.ts' -o -name '*.tsx' \) ! -path '*/node_modules/*' \
  \( -name '*.test.ts' -o -name '*.test.tsx' -o -name '*.spec.ts' \
     -o -path '*/test/*' -o -path '*/tests/*' -o -path '*/__tests__/*' \) -print0 | xargs -0 wc -l | tail -1
find packages -type f \( -name '*.ts' -o -name '*.tsx' \) ! -path '*/node_modules/*' -print0 | xargs -0 wc -l | tail -1
find packages/catalog/src -name '*_pb.ts' -print0 | xargs -0 wc -l | tail -1

# --- Rust ---
find crates -name '*.rs' -not -path 'crates/vendor/*' -path '*/src/*' -print0 | xargs -0 wc -l | tail -1
find crates -name '*.rs' -not -path 'crates/vendor/*' -print0 | xargs -0 wc -l | tail -1
find crates/vendor -name '*.rs' -print0 | xargs -0 wc -l | tail -1
ls crates/vendor | wc -l

# --- Python ---
find . -name '*.py' ! -path '*/node_modules/*' ! -path './.git/*' -print0 | xargs -0 wc -l | tail -1

# --- docs ---
find docs -name '*.md' | wc -l
find docs -name '*.md' -print0 | xargs -0 wc -l | tail -1
ls docs/*.md | wc -l
find packages -name '*.md' -path '*/src/*' ! -path '*/node_modules/*' | wc -l

# --- catalog ---
python3 -c "import json;m=json.load(open('packages/catalog/src/models.json'));\
print(len(m), sum(len(v) for v in m.values() if isinstance(v,(dict,list))))"
ls -l packages/catalog/src/models.json

# --- git 节奏 ---
git rev-list --count HEAD; wc -l < .git/shallow; git tag | wc -l
git log --format='%ad' --date=short | sort | uniq -c
git log --since=2026-06-01 --until=2026-07-31 --oneline | wc -l
git log --format='%an|%ae' | sort | uniq -c | sort -rn | head
git log --format='%s' | grep -oE '^[a-z]+(\([^)]+\))?' | sort | uniq -c | sort -rn
git log --name-only --format='' | grep -v '^$' | cut -d/ -f1-2 | sort | uniq -c | sort -rn
git log --format='%s' | grep -oE 'bump version to [0-9.]+' | sort -u | wc -l

# --- 构建 ---
find . -name 'BUILD.bazel' | grep -v node_modules | wc -l
sed -n '1,30p' MODULE.bazel; sed -n '16,24p' BUILD.bazel
grep -nE 'bazelisk|bun run' .github/workflows/ci.yml
```
