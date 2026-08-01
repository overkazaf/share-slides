# R05 · Rust 热路径：一个 TS agent 为什么自研 9 个 Rust crate

> 取证对象：`/Users/overkazaf/playground/research/ohmypi/oh-my-pi`，HEAD `09a7c8656`（`v17.2.3`）
> 对比基线：`/Users/overkazaf/playground/research/pi/pi-mono`（上游 pi，纯 TS，无 Rust）
> 证据等级：`[A]` = 本地代码亲自读到（附 `文件:行号`）；`[B]` = 仓库内文档/元数据已核实；`[C]` = 推测，仅进「存疑区」

---

## 0. 结论先行

1. **不是 7 个，是 9 个自研 crate。** `crates/` 下 `pi-*` 共 9 个（`pi-natives / pi-shell / pi-walker / pi-ast / pi-iso / pi-voice / pi-uu-grep / pi-uu-diff / pi-uutils-ctx`），另有 `crates/vendor/` 下 48 个 vendored 第三方 crate。`[A]`
2. **自研 Rust 实测 84,448 行**（9 个 pi-* crate 全部 `.rs`，含内联测试）；vendored 另有 100,565 行。README 首页写「~55,000 lines of Rust / Four crates」，**已经过时/低估**。`[A]`
3. **动机不是「TS 慢」，是「不想 fork/exec」。** README 那一节的标题就是自我陈述：「doing the work other harnesses shell out for … No fork/exec on the hot path」。`[B]` `README.md:419-421`
4. **最大的反直觉发现**：`pi-shell` 4.1 万行里，**28,266 行（69%）是「命令输出压缩器」（minimizer）**，真正的 shell 宿主逻辑只有约 1.28 万行。它省的不是 CPU，是 **token**。`[A]`
5. **`pi-iso` 不是安全沙箱**，是文件系统 CoW 隔离 PAL（APFS clonefile / overlayfs / btrfs / zfs / FICLONE / Windows ProjFS / rcopy）。**全 crate 无 seccomp、无 landlock、无 namespace、无 seatbelt。** 拿它讲「agent 执行安全」会讲错。`[A]`
6. **性能数字：全仓库只有一份提交在册的 benchmark 结果**（`packages/mnemopi/bench/native-vectors.bench.json`），而且它测的是 mnemopi 向量核，不是这 9 个 crate。grep 的 native-vs-subprocess-rg benchmark **有脚本没结果**。本文所有性能相关处标注「无实测数据」。`[A]`

---

## 1. Crate 总表

行数 = `find crates/<c> -name '*.rs' | xargs wc -l`（含内联测试）。`[A]`

| Crate | 一句话定位 | 行数 | 测试数 | 它替代了什么 |
|---|---|---:|---:|---|
| `pi-natives` | 顶层 N-API `cdylib`，聚合其余 crate，是唯一对 JS 暴露的产物 | 23,180 | 216 | —（胶水层本身） |
| `pi-shell` | 内嵌 shell 宿主 + 进程树管理 + **命令输出 minimizer** | 41,523 | 846 | 上游 `spawn(bash, ["-c", cmd])` 子进程 |
| `pi-walker` | 并行文件系统遍历（`ignore` + `globset`），被 grep/glob/fs-cache 共用 | 6,182 | 38 | npm `glob` + `ignore` + `minimatch` |
| `pi-ast` | tree-sitter 结构化摘要 + AST 工具，56 个语法 | 3,402 | 59 | 上游无对应能力（新增） |
| `pi-iso` | 任务隔离 PAL：CoW 克隆工作区 + 变更捕获 | 4,047 | 3 | 上游无对应能力（新增） |
| `pi-uu-grep` | `grep`/`rg` 重写在 ripgrep 库上，作为**进程内 builtin** | 3,863 | 26 | 运行时从 GitHub 下载 `ripgrep` 二进制并 fork |
| `pi-uu-diff` | `diff` 重写在 `similar` 上，进程内 builtin | 608 | 13 | fork `diff(1)` / npm `diff` |
| `pi-uutils-ctx` | thread-local stdio + cwd + env + cancel 上下文垫片 | 446 | 3 | —（使 in-process builtin 成为可能的关键 446 行） |
| `pi-voice` | miniaudio 采集 + opus + webrtc，语音实时链路 | 1,197 | 4 | 上游无对应能力（新增） |
| **合计（自研）** | | **84,448** | **1,208** | |
| `crates/vendor/*`（48 个） | brush-core/builtins + 44 个 uu-* + jaq，**非自研** | 100,565 | — | — |

### 1.1 「替代了什么」的硬证据

上游 pi-mono 的做法（`[A]`，全部亲自读到）：

- **grep**：`pi-mono/packages/coding-agent/src/utils/tools-manager.ts:29-70` 定义了一张 `TOOLS` 表，运行时从 GitHub Releases **下载 `ripgrep` 和 `fd` 的预编译二进制**到 `getBinDir()`，再 fork 调用。`packages/coding-agent/src/core/tools/grep.ts:174` 的报错原文：`"ripgrep (rg) is not available and could not be downloaded"`。
- **bash**：`pi-mono/packages/coding-agent/src/core/tools/bash.ts:97` — `spawn(shellConfig.shell, [...args, command], { cwd })`，每次工具调用一个子进程。
- **JS 依赖**：`pi-mono/packages/coding-agent/package.json` 运行时依赖里有 `glob`、`highlight.js`、`diff`、`ignore`、`minimatch`、`cross-spawn`。

omp 侧的对照（`[A]`）：

- `grep -rl '"glob"|"highlight.js"|"ignore"|"minimatch"|cross-spawn' omp/packages/*/package.json` → **全部为空**。`"diff"` 只剩在 `typescript-edit-benchmark`、`metaharness`、`hashline` 三个非运行时包里。
- `omp/packages/coding-agent/src/exec/bash-executor.ts:7` — `import { Shell } from "@oh-my-pi/pi-natives"`，文件头注释：「Uses brush-core via native bindings for shell execution.」
- 唯一残留的 `tools-manager` 用法在 `packages/coding-agent/src/web/scrapers/youtube.ts` 和 `fetch.ts`（`yt-dlp` 一类），搜索/shell 路径已全部内化。
- `crates/pi-natives/src/diff.rs:1-12` 的模块文档：「jsdiff-compatible diff primitives … producing **byte-identical output to the `diff` npm package (jsdiff v9)** … The Myers O(ND) core is a faithful port of jsdiff's `base.ts`」——**逐位兼容地重写了一个 npm 包**，1,025 行。

### 1.2 README 自述的模块表（可直接上 slide）

`README.md:429-452` 有一张官方分模块表（作者自称「intentionally omits glue and tests」），22 行合计 ≈ **15,120 行**。`[B]` 摘要：

| 模块 | 做什么 | 底座 | ~LoC |
|---|---|---|---:|
| shell | 内嵌 bash·持久会话·超时/中断·自定义 builtin | brush-shell (vendored) | 3,700 |
| grep | 正则搜索·并行/串行·glob 与类型过滤·fuzzy find | grep-regex · grep-searcher | 1,900 |
| keys | Kitty 键盘协议 + xterm 回退·PHF 完美哈希 | phf | 1,490 |
| text | ANSI 感知宽度·截断·列切片·保留 SGR 的换行 | unicode-width | 1,450 |
| summary | tree-sitter 结构化源码摘要 | tree-sitter · ast-grep-core | 1,040 |
| ast | ast-grep 模式匹配与结构化改写 | ast-grep-core | 1,000 |
| fs_cache | mtime 键控文件缓存，read/grep/lsp 共用 | in-tree | 840 |
| highlight | 语法高亮·11 语义类·30+ 别名 | syntect | 470 |
| pty | sudo/ssh 交互提示用的原生 PTY | portable-pty | 455 |
| glob / workspace / iso / fd / task / prof / ps / clipboard / tokens / sixel / html | … | … | 各 ≤ 410 |

注意其中几条本身就是「替代 fork」的自述：`clipboard` — 「no xclip/pbcopy」；`tokens` — 「O200k/Cl100k BPE，两张表都内嵌」（替代 tiktoken 的 WASM/网络下载）。

---

## 2. `pi-shell`：4 万行，最大的那个

### 2.1 它**没有**自己写 shell 解析器

这是本节最重要的纠偏。`[A]`

- `Cargo.toml:323` — `brush-parser = "0.3"`，**直接来自 crates.io，连 vendor 都没有**。
- `crates/vendor/brush-core`（26,352 行）与 `crates/vendor/brush-builtins`（9,310 行）是 vendored fork，workspace 根 `Cargo.toml:13-15` 用 `[patch.crates-io]` 指过去。
- 执行入口：`crates/pi-shell/src/shell.rs:1287-1290` — `session.shell.run_string(command, &source_info, &params)`。pi-shell 把**原始命令文本**交给 brush，解析和词展开 100% 是 brush 的。
- 会话构造：`shell.rs:590-597` — `BrushShell::builder()` + `ProfileLoadBehavior::Skip` + `RcLoadBehavior::Skip` + `BuiltinSet::BashMode`（不读用户 rc，保证 agent 环境可复现）。
- **唯一直接摸 parser 的地方**是 minimizer 的命令链切分：`crates/pi-shell/src/minimizer/plan.rs:85` 构造 `brush_parser::Parser`，把顶层 `&&`/`;` 切成 `ChainSegment`；切完还要用 brush 的 `Display` 反向重建再 re-parse 校验形状一致（`plan.rs:298-307`），不一致就整段回退；here-doc 直接排除（`plan.rs:209-215`）。

**所以「为什么要自己实现 shell」的正确答案是：它没有实现 shell，它实现了一个 shell 的宿主（host/embedding）。** 自研的是三样：builtin 集合、进程树/取消语义、以及输出压缩。

### 2.2 60 个进程内 builtin

注册是命令式的，不是表：`shell.rs:605-678` + `shell.rs:749-752`，`grep -c 'register_builtin('` = **60**。`[A]`
定义靠 `coreutils.rs:215-234` 的 `uutil_builtin!` 宏包成 `brush_core::builtins::Registration`。

| 类别 | 数量 | 说明 |
|---|---:|---|
| vendored uutils (`uu_*`) | 44 | `coreutils.rs:236-283`：mkdir/head/sort/wc/tail/ls/find/rm/mv/cat/uniq/base64/各 sum/basename/dirname/readlink/realpath/touch/stat/date/mktemp/seq/yes/printenv/ln/truncate/tac/nproc/uname/whoami/hostname/cut/tee/tr/paste/comm/sed/xargs |
| **自研 Rust 重写** | 4 | `grep`→`pi_uu_grep::run`（`coreutils.rs:243`）、`rg`→`pi_uu_grep::run_rg`（`:244`）、`diff`→`pi_uu_diff::run`（`:276`）、`jq`→`jaq::run`（`:284`） |
| moreutils（本 crate 内写） | 6 | `ts`/`sponge`/`ifne`/`isutf8`/`combine`（`coreutils.rs:285-289`）、`errno`（unix，`:290-291`） |
| pi 独有 | 6 | `fd`（`shell.rs:622`→`fd.rs` 1,837 行）、`which`、`cmp`（`cmp.rs` 635 行）、`sleep`（impl `shell.rs:1957`）、`timeout`（`:2001`）、`nohup`（`:2079`） |

安全相关的两个细节值得上 slide：
- **`exec` 和 `suspend` 被显式禁用**（`shell.rs:599-604`）——它们能让命令逃出内嵌会话。`[A]`
- 一整排 kill switch：`PI_DISABLE_UUTILS_BUILTINS`（`shell.rs:612`）、`PI_DISABLE_UUTILS_DESTRUCTIVE` / `PI_DISABLE_RM_BUILTIN` / `PI_DISABLE_MV_BUILTIN`（`shell.rs:669-678`）、`PI_DISABLE_NOHUP_BUILTIN`（`:739-747`）。在自研 builtin 出问题时能一键退回系统二进制。`[A]`

### 2.3 作业控制 / 进程管理

- **PTY 不在 pi-shell**。`grep -rn 'pty' crates/pi-shell/src` 无实质命中；PTY 在 `crates/pi-natives/src/pty.rs`（633 行，`portable_pty::native_pty_system().openpty`）。`[A]`
- 每次运行都开新进程组：`shell.rs:1256` — `params.process_group_policy = ProcessGroupPolicy::NewProcessGroup`。`[A]`
- 信号：`process.rs:1508-1520` `kill_process_group` 带「不杀自己组」的守卫（`:1517`）；Linux 用 `pidfd_send_signal`（`process.rs:157-167`）；**macOS 在 `libc::kill` 前重新校验 pid 身份以防 pid 回绕**（`process.rs:394-405`）；Windows 走 `TerminateProcess`（`:958-973`）。`[A]`
- 后台作业：`terminate_background_jobs`（`shell.rs:1472-1495`）遍历 `shell.jobs_mut().jobs`，收集 pgid/代表 pid，先 TERM 后 150ms KILL。作业跟踪本身仍是 brush-core 的。`[A]`
- **`SpawnRegistry`（`process.rs:1656-1732`）**：挂在 brush 的 `SpawnObserver` 上（`shell.rs:1258`），只记录「这一次运行自己 spawn 的进程」。其文档注释（`process.rs:1633-1640`）明确说它取代了旧的「进程全局 descendants-since-baseline 差分」方案——**旧方案会跨杀并发运行**。带 `PRUNE_THRESHOLD = 64` 的摊还 O(1) 清理避免 pidfd/HANDLE 耗尽。`[A]`

### 2.4 「顺手修好重定向、cwd、取消三处语义」—— 核实结论：**成立，三处都有实打实的代码**

问题根源一句话：**把 `grep`/`ls`/`cat` 变成同一进程里的函数调用之后，POSIX 给进程的三样东西（fd 表、cwd、信号）全部失效了。**
446 行的 `pi-uutils-ctx` 就是为补这三个洞而存在的。它的模块文档（`crates/pi-uutils-ctx/src/lib.rs:1-15`）把问题说得很直白：

> uutils utilities write to the process-global `std::io::stdout()`…, and resolve relative paths against the process-global current directory. **None of that is correct when the utility runs as a builtin inside a long-lived shell process.**

`Ctx` 结构体（`lib.rs:28-44`）恰好就是这三样 + env：`stdout/stderr/stdin` / `cwd` / `cancel`。

#### (a) 重定向 — in-process builtin 不能 `dup2(1)`

1. `coreutils.rs:76-78`：在任何 await 之前，从 brush 执行上下文里取出这条命令**真正的** fd —— `context.try_fd(OpenFiles::STDIN_FD / STDOUT_FD / STDERR_FD)`。`[A]`
2. `coreutils.rs:121-149`：装成 `Box<dyn Read/Write + Send>`，在专属 `spawn_blocking` 线程上通过 `pi_uutils_ctx::scope(ScopeIo{...}, || run_caught(run, argv))` 安装为 thread-local。**一次调用一个线程**是刻意的——并发管道各段互不串流（`coreutils.rs:4-8`、`pi-uutils-ctx/src/lib.rs:12-15`）。`[A]`
3. vendored uutils 被**打补丁**改写到 `CtxStdout/CtxStderr/CtxStdin`：`pi-uutils-ctx/src/lib.rs:236-273`（`ctx_writer!` 宏）、`:287-326`。
4. **最见功力的 fail-safe**（`lib.rs:256-258`）：没有安装上下文时，写入被**丢弃**而不是落到宿主进程真实的 fd 1/2 —— 因为宿主的 fd 1/2 是 TUI 的画布，泄漏一个字节就花屏。`[A]`
5. 进程替换 `/dev/fd/N`：`coreutils.rs:39-64` `materialize_process_substitution_fds` 把 shell 级 fd clone 成真实 `OwnedFd` 并改写 argv。`[A]`
6. builtin 自己再 spawn 子进程时也继承不到 stdio：`pi_uutils_ctx::run_captured`（`lib.rs:359-383`）用管道 + 一个 stderr 辅助线程把输出接回上下文流。`[A]`
7. 回归测试：`shell.rs:3944-3968` `segmented_chain_with_redirect_executes_correctly` —— `echo hidden >/dev/null && printf 'hello\n'` 必须精确得到 `"hello\n"`。`[A]`

#### (b) cwd — 每实例，而非进程全局 `chdir`

- **`grep -rn set_current_dir crates/pi-shell/src` = 0。** 整个 crate 从不改进程 cwd。`[A]`
- 每实例 cwd 挂在 brush shell 上：`shell.rs:62-78`（`shell_working_dir_matches` / `set_shell_working_dir_if_changed`），每次运行前应用于 `shell.rs:835-836`、`shell.rs:1240-1242`，运行后把新 cwd 回传给 JS（`shell.rs:1362`）。`[A]`
- 传进 builtin：`coreutils.rs:79` — `let cwd = context.shell.working_dir().to_path_buf();` → `ScopeIo.cwd`（`coreutils.rs:143`）。`[A]`
- builtin 遵守它，是因为被 patch 的 uutils **每个路径参数都过一遍** `pi_uutils_ctx::resolve`（`lib.rs:172-179`，文档原文：「uutils utilities are patched to resolve every path argument through this before touching the filesystem」）。`[A]`
- env 同理：shell 的 exported 变量在宿主进程 env 里根本不存在，所以要快照进 scope（`coreutils.rs:82-87`），由 `pi_uutils_ctx::var`（`lib.rs:185-191`）读回。`[A]`
- **回归测试原文**（`shell.rs:2598`）：`assert!(!std::path::Path::new("a/b/c").exists(), "mkdir leaked into process cwd")`。这行 assert 本身就是一张 slide。`[A]`

#### (c) 取消 — 四层协作，不是一个开关

1. **对宿主的 token**：`crates/pi-shell/src/cancel.rs` —— `CancelToken`（`cancel.rs:66-151`）= deadline + 共享 `Flag`；`AbortReason::{Unknown,Timeout,Signal,User}`（`:14-19`）；协作式 `heartbeat() -> Result<()>`（`:89-101`）；`AbortToken` 持 `Weak<Flag>`，中断一个已结束的运行是 no-op（`:153-163`）。`[A]`
2. **桥到 brush**：每次运行创建 `tokio_util::sync::CancellationToken`（`shell.rs:290`），`params.set_cancel_token`（`:1257`）；`shell.rs:326-346` `select!` 竞速运行任务 vs `ct.wait()`，触发后 → `tokio_cancel.cancel()` → **2 秒优雅窗口** → `run_task.abort()`。`[A]`
3. **后代清理三波**：`terminate_run`（`shell.rs:1444-1471`）——第 0 波 TERM + 75ms，第 1/2 波 KILL + 150ms，**每波都从 `SpawnRegistry` 重新取目标**，所以优雅窗口期间新生的子进程也会被回收（`process.rs:1711-1717`）。`[A]`
4. **进程内 builtin 的协作取消**（最有意思的一层——你没法给一个函数发信号）：共享 `Arc<AtomicBool>` 放进 scope（`coreutils.rs:106-107, :145`）。token 触发时 `coreutils.rs:156-172` 置位并**等 blocking 任务真正跑完**才返回 130，注释原文（`:151-155`）：这样「no detached thread keeps writing to the command's (possibly redirected) fds」。flag 有两条观测路径：`CtxStdin::read` 返回 `Ok(0)` 合成 EOF 让工具自然退栈（`pi-uutils-ctx/src/lib.rs:294-296`）；unix 上用 `libc::poll` **200ms 一片**的循环重查 flag，卡死的管道也能中断（`lib.rs:301-322`）。目录遍历这类长循环直接轮询 `is_cancelled()`（`lib.rs:220-234`）。`[A]`

**附赠第四处语义修复（旧笔记没提，但同源）：panic 隔离。** `run_caught`（`coreutils.rs:187-197`）把 vendored 工具的 panic 变成 exit 1 + `"<name>: internal error"`；注释里点名了真实事故：`uu-tail` 对 `BrokenPipe` 做了 unwrap（`coreutils.rs:180-186`）。配套的 `is_active()`（`lib.rs:126-128`）用一个**免借用的 `SCOPE_DEPTH: Cell`**（`lib.rs:48-52`）让 crash hook 能在 panic 现场安全查询——因为此时 `CTX` 的 `RefCell` 可能已被借出，再借一次会二次 panic 直接 abort。根 `Cargo.toml:22-37` 有一整段注释解释为什么 release profile 必须 `panic = "unwind"`。`[A]`

### 2.5 那 4 万行到底在干嘛：minimizer 占 69%

`[A]` 实测：

- `crates/pi-shell/src` 总计 41,207 行
- 其中 `minimizer.rs` + `minimizer/` = **28,266 行（68.6%）**
- 非 minimizer 部分 = 12,789 行 ← 这才是「shell 宿主」的真身

单文件排行前几名全是 minimizer 的按工具过滤器：`filters/jvm.rs` 3,117（Maven/Gradle）、`filters/git.rs` 2,842、`filters/listing.rs` 2,032（ls/tree/find 折叠）、`filters/docker.rs` 1,702、`filters/cloud.rs` 1,676（aws/curl/psql）、`filters/pkg.rs` 1,215（npm/pnpm/yarn）、`cargo.rs` 1,001。派发在 `filters/mod.rs:41-72` 的 `match program`；引擎 `minimizer/engine.rs:1244` 行，**过滤器在 `catch_unwind` 下运行**（写坏一个过滤器不该炸掉命令）。另有 67 个 TOML 声明式管道定义（`src/minimizer/defs/`），`build.rs:12-40` 在构建期拼接。`[A]`

> **这是全篇最值得讲的一点**：这 2.8 万行 Rust 的目的不是让命令跑得快，是让 `mvn test` 的 3000 行输出变成 30 行再进 context window。**省的是 token 和注意力，不是 CPU。** 把它归到「Rust 性能优化」是误读。

### 2.6 pi-shell 的 benchmark

**无。** 无 `benches/`、无 `[[bench]]`、无 `criterion`、无 `#[bench]`。crate 内所有数字都是**设计常量**（`POST_EXIT_IDLE 250ms` / `POST_EXIT_MAX 2s` / `READER_SHUTDOWN_TIMEOUT 250ms`，`shell.rs:1306-1308`；杀进程波次 75/150ms，`shell.rs:1463-1467`；poll 片 200ms，`pi-uutils-ctx/src/lib.rs:310`）或复杂度断言（`PRUNE_THRESHOLD = 64`，摊还 O(1)，`process.rs:1644-1676`），**不是测量值**。`[A]`

---

## 3. `pi-natives`：绑定方式、开销、分发

### 3.1 绑定方式：**napi-rs（N-API `cdylib`）**，不是 wasm，也不是 bun FFI

`[A]` `crates/pi-natives/Cargo.toml` — `[lib] crate-type = ["cdylib"]`；`crates/pi-natives/src/task.rs:34` — `use napi::{Env, Error, Result, Status, Task, bindgen_prelude::*}`。
`[B]` `docs/natives-architecture.md:1-8`：两层结构 = ESM loader（JS）+ Rust N-API 模块层；`index.d.ts` 由 napi-rs 在 `scripts/build-native.ts` 中生成；snake_case → camelCase 自动映射。

**调度模型**（`docs/porting-to-natives.md:15` `[B]` + `crates/pi-natives/src/task.rs:1-28` `[A]`）：

- CPU 密集/阻塞 I/O → `task::blocking(tag, cancel_token, work)`，跑在 **libuv 线程池**上（napi `Task` trait）
- 异步 I/O（shell 执行）→ `task::future(env, tag, work)`，跑在 **tokio** 上
- 暴露 `timeoutMs` / `AbortSignal` 的 API 必须传 `CancelToken` 并在长循环里 `heartbeat()`
- `task.rs` 用 `catch_unwind`（`task.rs:30-31`）在跨 `extern "C"` 边界前接住 panic，转成 rejected Promise 而不是进程 abort——根 `Cargo.toml:22-37` 有长注释解释这个 RFC 2945 的坑

`packages/natives` **没有 TS wrapper 层**（`docs/natives-binding-contract.md:5` `[B]`）：公开 API 就是 napi-rs 生成的 `native/index.d.ts`（68 KB）+ `gen-enums.ts` 补出来的显式 ESM 具名导出（枚举在 napi-rs 里只有 TS 类型、没有运行时对象，必须补）。

### 3.2 调用开销：唯一的实测数据

**`packages/mnemopi/bench/native-vectors.bench.json`（提交在册，`sha 8047beda`，2026-07-22，Apple M1 / darwin-arm64 / bun 1.3.14，「crossing-inclusive」即含 N-API 跨越成本）** `[A]`：

| kernel | count | ts_us | native_us | speedup |
|---|---:|---:|---:|---:|
| searchExactVectorIndex | 10 | 17.34 | 9.49 | 1.83× |
| searchExactVectorIndex | 10000 | 5562.41 | 3437.82 | 1.62× |
| **cosineSimilarityPairs** | **10** | **26.42** | **30.67** | **0.86×（更慢）** |
| cosineSimilarityPairs | 100 | 4418.75 | 1866.25 | 2.37× |
| cosineSimilarityPairs | 1000 | 445625.44 | 179685.28 | 2.48× |
| mmrRerankIndices | 10 | 395.50 | 17.62 | **22.44×** |
| mmrRerankIndices | 1000 | 103521.56 | 3430.07 | 30.18× |

**读法（这张表比任何口号都诚实）**：小批量时 N-API 跨越成本能把 Rust 的优势吃光（0.86×，净亏）；算法复杂度高的核（MMR 重排，O(n²)）才有 20–36× 的量级差。

代码里对应的自觉：`crates/pi-natives/src/vectors.rs:1-8` 的模块文档 —— 「Every export processes **an entire candidate batch per N-API crossing** so the crossing cost is amortized over the whole recall operation.」`[A]`
以及 `docs/porting-to-natives.md:170-173` 的「Rule of thumb」：「**If native is slower, do not switch callsites.**」`[B]`

> ⚠️ **必须标清楚**：以上数字来自 mnemopi 向量核，**不是** grep/shell/walker 的数字。后者的 benchmark 脚本存在但**结果未入库**。

### 3.3 构建产物怎么分发

三层，全部核实过：

**(1) 构建：Bazel（不是 cargo）** `[A]`
- `MODULE.bazel:1-16`：「replacing cargo-zigbuild/cargo-xwin/sccache plus the hand-rolled CI caches with Bazel's content-addressed action cache」；cargo workspace 仍是**本地迭代**的权威（rust-analyzer / `cargo nextest` / napi typedef 生成），Bazel 只负责产物与 CI。
- `rules_rust 0.71.3` + `hermetic_cc_toolchain 4.2.0`（zig cc），`crate_universe` 直接从 `Cargo.lock` 推导依赖图。
- Rust 工具链**双份**：Bazel 侧钉 `nightly/2026-04-29`（`MODULE.bazel:39`，且逐档案钉 sha256，注释解释这是为了让 rules_rust 判定 repo 可缓存，否则每个 CI pod 冷启要重下 ~5 套工具链 × ~20s）；本地 `rust-toolchain.toml` 是 `nightly-2026-07-28`。
- 还要给 hermetic_cc_toolchain 打**自研补丁**（`bazel/patches/hermetic_cc_toolchain-isolated-compile-cache.patch`），绕 ziglang/zig#18763 的并发缓存损坏。`MODULE.bazel:26-33`
- **8 个构建目标**（`BUILD.bazel:16-25`）：linux-x64-baseline / linux-x64-modern / linux-arm64 / linux-musl-x64-baseline / linux-musl-arm64 / darwin-x64-baseline / darwin-arm64 / win32-x64-baseline。
- Windows 交叉编译要下 **~2 GiB LLVM + ~1 GiB xwin CRT/SDK**，且后者不进 repo cache（`docs/natives-build-release-debugging.md:229`）；darwin 冷图约 **~40 分钟**（`:165`）。`[B]`

**(2) 加载：loader 五级探测** `[B]` `docs/natives-architecture.md:43-91`
- platform tag = `${process.platform}-${process.arch}`，5 个受支持 tag
- x64 再分 `modern`（AVX2）/ `baseline` 两个变体，检测方式各平台不同：Linux 读 `/proc/cpuinfo`，macOS `sysctl machdep.cpu.leaf7_features`，**Windows 起一个 PowerShell 查 `System.Runtime.Intrinsics.X86.Avx2`**
- 版本哨兵：`.node` 必须导出以包版本命名的符号（如 `__piNativesV16_0_3`），否则拒绝加载
- Windows 的 `node_modules` 安装还要先把 addon **stage 到版本化缓存目录**，避免全局升级时文件被占用

**(3) 发布：核心包 + 5 个平台 leaf 包（optionalDependencies）** `[B]` + `[A]`（npm registry 实查，v17.2.3）

| 包 | 解压体积 | 文件数 |
|---|---:|---:|
| `@oh-my-pi/pi-natives`（核心，只有 loader，**不含 .node**） | 111.2 KiB | 9 |
| `@oh-my-pi/pi-natives-linux-x64` | **285.2 MiB** | 4（baseline + modern 双变体） |
| `@oh-my-pi/pi-natives-win32-x64` | 143.8 MiB | 3 |
| `@oh-my-pi/pi-natives-linux-arm64` | 139.4 MiB | 3 |
| `@oh-my-pi/pi-natives-darwin-x64` | 138.7 MiB | 3 |
| `@oh-my-pi/pi-natives-darwin-arm64` | 137.6 MiB | 3 |

> 来源：`curl https://registry.npmjs.org/@oh-my-pi/pi-natives-<tag>` 的 `dist.unpackedSize`，2026-08 实查。`[A]`
> **这是这笔投入最直观的代价**：一个 Rust addon ≈ **138–285 MiB**（含 56 个 tree-sitter 语法、syntect 语法/主题、两张 BPE 表、多份 bitmap/TTF 字体、webrtc + opus）。上游 pi 的对应成本是「首次用到时下载 rg/fd」，几 MB。

---

## 4. `pi-iso`：是隔离，但**不是安全沙箱**

**这一节最容易讲错，请务必按此口径。**

### 4.1 它是什么

`crates/pi-iso/src/lib.rs:1-19` 自述：「Cross-platform **isolation PAL**」——「A backend gives the caller a writable 'merged' view of a read-only 'lower' tree **without paying for a deep copy**」。`[A]`

即：**给 subagent 一份写时复制的工作区副本，跑完再把改动 diff 出来。** 契约两半（`lib.rs:238-260`）：生命周期 `start`/`stop` + 变更捕获 `diff`。这解释了为什么依赖里有 `similar` 这个**文本 diff 库**。

**全 crate 无 seccomp / landlock / namespace / cgroup / ptrace / job object / AppContainer / `sandbox_init`。** 它防的是「subagent 改坏你的工作树」，不防「subagent 读你的 `~/.ssh`」或「发起网络请求」。`[A]`

### 4.2 后端矩阵（10 个模块，4,047 行）

| 平台 | 后端 | 具体机制（file:line） |
|---|---|---|
| macOS | APFS | `apfs.rs:98` — `libc::clonefile(src, dst, 0)` 递归 reflink |
| Linux | overlayfs（`native()` 默认） | `overlayfs.rs:191-197` — `libc::mount("overlay", merged, "overlay", 0, "lowerdir=…,upperdir=…,workdir=…")`；EPERM/EACCES/ENODEV/EINVAL 时退到 `fuse-overlayfs`（`:206, :235-266`）；卸载 `umount2(MNT_DETACH)`（`:218`） |
| Linux | reflink | `linux_reflink.rs:216` — `libc::ioctl(dst_fd, FICLONE, src_fd)`；FICLONE 常量手写（`:85`），因为 `libc::Ioctl` 在 musl 是 `c_int`、glibc 是 `c_ulong` |
| Linux | btrfs | `btrfs.rs:98-99` — shell out `btrfs subvolume snapshot` |
| Linux/BSD/macOS | zfs | `zfs.rs:111-114` — `zfs snapshot` + `zfs clone -o mountpoint=`；`is_own_clone` 守卫拒绝销毁无关数据集（`:131-135`） |
| Windows | block clone | `windows_block_clone.rs:281-291` — `DeviceIoControl(FSCTL_DUPLICATE_EXTENTS_TO_FILE)`（NTFS/ReFS） |
| Windows | ProjFS（默认） | `projfs.rs:239-283` — **运行时 `LoadLibraryW` + `GetProcAddress`** 动态加载 `ProjectedFSLib.dll` 的 10 个符号，实现 5 个 `unsafe extern "system"` 回调（`:469/:495/:513/:594/:642`）；拒绝在 Windows ARM64 的 x64 模拟下运行（`:32`） |
| 全平台兜底 | rcopy | `rcopy.rs:120-124` — `git worktree add --detach`；非 git 仓库则保模式/mtime 递归复制（`:330`） |

选择顺序 `lib.rs:126-140`：macOS `Apfs→Zfs→Rcopy`；Linux `Btrfs→Zfs→LinuxReflink→Overlayfs→Rcopy`；Windows `WindowsBlockClone→Projfs→Rcopy`。`resolve()`（`:352-387`）返回整个候选列表，让调用方在 `Unavailable` 时按序重试。`[A]`

### 4.3 谁在用

`crates/pi-natives/src/iso.rs`（243 行）导出 `isoProbe/isoResolve/isoStart/isoStop/isoDiff/isoIsUnavailableError` → `packages/natives/native/index.d.ts:1148-1249` → **Task/subagent 工具的隔离工作区模式**：`packages/coding-agent/src/task/worktree.ts:432/446/463/478`。`[A]`

一个值得讲的坑：`worktree.ts:453` 在 start 之后调 `git.detachGitDir(mergedDir, sourceCommonDir)`——因为 CoW 克隆会把 `.git` 一起复制，不断开的话副本和母 checkout 共享 HEAD/index。**CoW 隔离引入的、非 CoW 方案不会有的 bug。**`[A]`

### 4.4 测试与 benchmark

- **测试仅 3 个**，且没有一个端到端跑通任一后端：`rcopy.rs:515`（git apply 的 stdin/stderr 管道死锁回归）、`projfs.rs:101/:109`（纯环境变量解析）。行为覆盖靠 TS 侧 mock：`packages/coding-agent/test/task/worktree.test.ts:127-170`。`[A]`
- **benchmark：无。** `[A]`

---

## 5. `pi-walker` / `pi-uu-grep` / `pi-uu-diff`：检索的进程内化

### 5.1 三者关系

```
pi-walker (6,182 行, ignore+globset+rayon+dashmap)
   ├── pi-uu-grep (3,863 行) ── 目录递归
   ├── pi-natives/glob.rs, fd.rs, grep.rs, ast.rs ── 经 fs_cache.rs 共享扫描缓存
   └── pi-shell/fd.rs (1,837 行) ── `fd` builtin
pi-uutils-ctx (446 行) ── 给 grep/diff 提供 fd/cwd/cancel 上下文
   ├── pi-uu-grep
   └── pi-uu-diff (608 行, similar)
```

模块自述 `[A]`：
- `pi-walker/src/lib.rs:1-7`：「owns the native directory-read fast path used for globbing, grep candidate discovery, AST scans, and shell builtins. The crate exposes **plain Rust types … so consumers do not inherit N-API dependencies**.」——刻意与 napi 解耦，才能同时被 pi-shell 和 pi-natives 用。
- `pi-uu-grep/src/lib.rs:1-11`：ripgrep 的**库**（`grep-regex` 匹配器 + `grep-searcher` 扫描）+ `pi-walker` 递归 + `globset` 过滤；「It **never calls `std::process::exit`**」——因为它现在跑在宿主进程里，exit 会杀掉整个 agent。
- `pi-uu-diff/src/lib.rs:1-16`：`similar` + `-u/-U N/-q/-N` + 二进制探测 + 递归目录比较；同样「never calls `std::process::exit`」，clap 的 help/error 渲染到上下文流。

`fs_cache`（`crates/pi-natives/src/fs_cache.rs`）把目录扫描结果按 `(root, include_hidden, use_gitignore, skip_node_modules, detail)` 五元组缓存，供 glob / fuzzyFind / grep / astGrep 共享（`docs/fs-scan-cache-architecture.md:1-45` `[B]`）。**这是「进程内化」真正的复利来源**：子进程模式下，每次 `rg` 调用的目录遍历成果随进程退出一起蒸发；进程内化之后可以跨调用复用。

### 5.2 Benchmark：脚本有，结果无

`packages/natives/bench/grep.ts` `[A]` —— 设计得相当规范：
- 4 个用例（tui/src ~50 文件、coding-agent/src ~200+ 文件；content 与 filesWithMatches 两种输出模式）
- 对照组是**真的 subprocess `rg`**，且先比对匹配数确保语义等价
- 两个维度：串行 + `CONCURRENCY = 2` 并发（并发才是 agent 的真实场景——subprocess 每次都要重新 fork/exec + 重新遍历，进程内可以共享缓存）
- 输出 `Native grep is N.Nx faster than rg (sequential / 2x concurrent)`

**但仓库内没有任何一次运行结果被提交。** 全仓库唯一入库的 benchmark 结果是 `packages/mnemopi/bench/native-vectors.bench.json`（见 §3.2），与本节无关。

> **口径**：讲 grep/walker/diff 时说「**无实测数据**；仓库提供了 native-vs-subprocess-rg 的对照脚本，含并发维度，但结果未入库」。不要给数字。

---

## 6. 总账：这笔投入换来了什么

### 6.1 规模

| 项 | 行数 |
|---|---:|
| 自研 Rust（9 个 `crates/pi-*`，含内联测试） | **84,448** |
| ├─ `pi-shell` | 41,523（其中 minimizer **28,266**） |
| ├─ `pi-natives` | 23,180 |
| ├─ `pi-walker` | 6,182 |
| ├─ `pi-iso` | 4,047 |
| ├─ `pi-uu-grep` | 3,863 |
| ├─ `pi-ast` | 3,402 |
| ├─ `pi-voice` | 1,197 |
| ├─ `pi-uu-diff` | 608 |
| └─ `pi-uutils-ctx` | 446 |
| vendored（48 个 crate，**不算自研**） | 100,565 |
| Rust 测试函数（自研部分） | 1,208 |
| 全仓 TypeScript | 1,265,449 |

自研 Rust ≈ TS 的 **6.7%**。这个比例值得强调：**它不是「用 Rust 重写 agent」，是「把 agent 最脏的 6% 换成 Rust」。**

### 6.2 换来了什么（客观）

**确实拿到的：**
1. **消除了运行时二进制依赖。** 上游 pi 首次 grep 要去 GitHub 下 ripgrep（`tools-manager.ts`），离线/内网/企业代理环境直接失败（有 `PI_OFFLINE` 开关也只是让它更早失败）。omp 的 grep 是 `.node` 里的函数。`[A]`
2. **消除了 6 个 npm 运行时依赖**（glob / highlight.js / diff / ignore / minimatch / cross-spawn），其中 `diff` 是**逐位兼容重写**的（`pi-natives/src/diff.rs:1-12`）。供应链面积和 JS 启动成本都降了。`[A]`
3. **跨调用共享状态成为可能**：`fs_cache` 的目录扫描结果、shell 的持久会话与 cwd、`SpawnRegistry` 的进程归属。这些在 fork/exec 模型下**在架构上不可能**。`[A]`
4. **精确的取消语义**：三波信号 + 只杀自己 spawn 的后代 + builtin 协作式中断（§2.4c）。子进程模型下你只能 `SIGKILL` 一个 pid，然后祈祷。`[A]`
5. **可控的多语言 AST**：56 个 tree-sitter 语法内嵌（`pi-ast/Cargo.toml`），无 wasm 加载、无网络。`[A]`
6. **token 层面的收益**（minimizer，2.8 万行）——这是被低估的最大回报，且与「Rust 快」无关。`[A]`

**代价（同样真实）：**
1. **产物体积 138–285 MiB / 平台**（npm registry 实查，§3.3）。核心包只有 111 KiB，但每个用户必然装一个百兆级 leaf。`[A]`
2. **构建复杂度上了一个数量级**：Bazel + rules_rust + hermetic_cc(zig) + crate_universe + 8 个目标 + 双 Rust 工具链（Bazel 钉 `nightly/2026-04-29`，本地 `nightly-2026-07-28`）+ 一个自研的 zig 缓存补丁。Windows 交叉编译要拉 ~3 GiB SDK，darwin 冷构建 ~40 分钟。`[A][B]`
3. **cargo 与 Bazel 双轨并存**（`MODULE.bazel:13-16` 明说 cargo 仍是本地权威，Bazel 是产物/CI 权威）——两套依赖图要同时保持能跑。`[B]`
4. **进程边界的保护没了，得手动补回来**：panic 隔离（`catch_unwind` 三处：`task.rs:30-31`、`coreutils.rs:187-197`、`minimizer/engine.rs`）、fd 泄漏防护（`pi-uutils-ctx/src/lib.rs:256-258` 无上下文时丢弃写入）、`std::process::exit` 全面禁用、`exec`/`suspend` builtin 禁用。**这就是那 446 行 `pi-uutils-ctx` 存在的全部理由。** `[A]`
5. **测试覆盖极不均衡**：`pi-shell` 846 个测试（且 minimizer 占绝大多数），而 `pi-iso` 只有 3 个、`pi-uutils-ctx` 3 个、`pi-voice` 4 个。恰恰是最难写测试的平台相关代码（overlayfs / clonefile / ProjFS）**零覆盖**。`[A]`
6. **文档漂移**：`docs/natives-shell-pty-process.md:9/:38/:253` 和 `docs/natives-binding-contract.md:68` 都记录了 `applyBashFixups` / `crates/pi-shell/src/fixup.rs`，但**文件不存在、符号在 `index.d.ts` 里 0 命中**（实测 `grep -c applyBashFixups packages/natives/native/index.d.ts` = 0）。README 首页的「~55,000 lines / Four crates」也已过时（实为 84,448 / 9 个）。`[A]`

### 6.3 一句话评价

> 这不是「Rust 更快所以重写」，而是「**把子进程边界换成函数调用边界**」的架构选择。收益（无外部二进制、跨调用共享缓存、精确取消、token 压缩）都来自边界的消失；代价（百兆产物、Bazel 双轨、手工补回 panic/fd/exit 隔离、平台代码零测试覆盖）也全部来自同一个边界的消失。**是不是划算，取决于你的 agent 是跑一次就退，还是开一天。**（omp 的 slogan 恰好是 "made for terminals that stay open"。）

---

## 7. 存疑区 `[C]`

- **crate 引入时间线不可靠**。`git log --diff-filter=A -- crates/<c>` 显示 8 个 crate 同时出现在 `06f2ae96f`（2026-07-22），但那是个 merge commit，标题与 crate 无关（"Merge PR #6139: fix(ai): retry provider connection failures"）；仓库最早提交是 2026-05-13。历史看起来经过压平/重写，**不要在 slide 上讲「X 月拆分出 Y crate」**。
- **README「~55,000 行」的口径未知**。可能是「排除测试 + 排除 minimizer」或某次统计后未更新。已知实测值 84,448（含测试）。分模块表合计 15,120（作者自称已排除 glue 和 tests）。三个数对不上，建议 slide 上只用「84,448（含内联测试，实测）」并注明 README 自述值。
- **`pi-voice` 未深挖**。1,197 行，`live.rs` 722 + `audio.rs` 410，依赖 `maudio`(miniaudio) / `opus` / `webrtc`，被 `pi-natives/src/audio.rs`、`live.rs` 消费。看上去是实时语音对话链路，但未追到 TS 侧调用点。上游 pi 无对应能力。
- **N-API 跨越的绝对开销未单独测**。只能从 `native-vectors.bench.json` 的 `cosineSimilarityPairs @ count=10 → 0.86×` 反推「小 payload 时跨越成本可以吃掉全部收益」，无法给出「一次跨越 X 微秒」这样的数字。
- **`crates/pi-natives/src/desktop.rs`（2,676 行）+ `desktop_x11.rs`（1,253 行）+ `devicecheck.rs`（351 行）** 是 Computer Use / Apple DeviceCheck 相关，属于本维度之外但计入了 84,448。若要精确说「检索与执行热路径的自研 Rust」，应扣掉这约 4,280 行。
