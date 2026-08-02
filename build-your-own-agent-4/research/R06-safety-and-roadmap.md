# R06 — 0xAF-Re / re-agent：安全边界、工程现状与未来规划

调查对象：`/Users/overkazaf/playground/research/re-agent`（Go，module `github.com/overkazaf/re-agent`，`go.mod:3` 声明 `go 1.22`）。
标注约定：**[A]** = 本地读代码/跑统计验证；**[B]** = 文档自称，未在代码里独立验证；**[C]** = 我的推断。
全程只读，未运行二进制，未联网。

---

## 0. 一句话结论

安全模型是**「tier × mode + 命令模式正则 + 路径包含」三件套**，设计干净、文档诚实（架构文档甚至自己写明了 `safe` 模式对所有 tier 都放行），但**默认档位（`safe`）等于"除非命中正则，否则任何 exec 都不问"**；而 `run_command` 直接 `bash -c`，因此 `--write` / `--allow-network` / 工作区包含这三道闸门在 shell 层面都是可绕过的。工程现状：0 CI、0 lint 配置、0 TODO 标记、测试 3557 行 / 源码 20672 行（17.2%），但覆盖高度不均（`internal/tools` 4041 行源码只有 354 行测试，`mcp`/`types`/`util` 零测试）。路线图**只有一句话**（本地模型 + 可复现评测样例），其余全部是我从代码接缝推断的。

---

## 1. 安全模型

### 1.1 包结构

`internal/security` 只有两个文件，共 266 行源码 + 193 行测试 [A]：

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `internal/security/policy.go` | 122 | 命令安全模式（destructive / network / sensitive）+ 路径读校验 + 写开关 |
| `internal/security/approval.go` | 144 | tier × mode 审批闸门、per-tool override、`DeniedError` |
| `internal/security/policy_test.go` | 78 | — |
| `internal/security/approval_test.go` | 115 | — |

包注释把职责说得很清楚（`internal/security/policy.go:1-3`）[A]：

```go
// Package security decides whether a call runs: the command safety patterns
// (policy.go) and the tier/mode approval gate (approval.go).
```

### 1.2 三层：Tier（工具风险）

`internal/security/approval.go:60-70` [A]：

```go
func TierForRisk(risk types.Risk) types.ApprovalTier {
	switch risk {
	case types.RiskRead:
		return types.TierRead
	case types.RiskWrite:
		return types.TierWrite
	default:
		// execute and network are both "can do anything" tiers
		return types.TierExec
	}
}
```

注册表 24 个工具（`internal/tools/registry.go:24-49`）[A]，其中只有 3 个非 read：
- `write_file` → `RiskWrite`（`internal/tools/files.go:92`）
- `run_command` → `RiskExecute`（`internal/tools/files.go:169`）
- `reverse_toolkit` → `RiskExecute`（`internal/tools/retool.go:48`）

其余 21 个（含 `update_plan`、`knowledge_read`、`carve_artifacts`）都声明为 `RiskRead`。注意 `carve_artifacts` 声明 read 却能写盘（见 §1.7 洞 #4）。

### 1.3 三层：Mode（会话档位）

`internal/security/approval.go:19-23, 72-83` [A]：

```go
var ApprovalModes = []types.ApprovalMode{
	types.ApprovalYolo, types.ApprovalSafe, types.ApprovalWrite, types.ApprovalAlwaysAsk,
}
const DefaultApprovalMode = types.ApprovalSafe

func AutoApproves(mode types.ApprovalMode, tier types.ApprovalTier) bool {
	if mode == types.ApprovalYolo || mode == types.ApprovalSafe {
		return true // `safe` only reacts to concerns
	}
	if tier == types.TierRead {
		return true
	}
	if mode == types.ApprovalWrite {
		return tier == types.TierWrite
	}
	return false // always-ask
}
```

矩阵（`docs/ARCHITECTURE.md:420-425` 与代码一致 [A]）：

| Mode | read | write | exec | 命中安全模式时 |
| --- | --- | --- | --- | --- |
| `yolo` | 跑 | 跑 | 跑 | 跑 |
| `safe`（默认） | 跑 | 跑 | 跑 | **问**（无人值守则拒） |
| `write` | 跑 | 跑 | 问 | 问 |
| `always-ask` | 跑 | 问 | 问 | 问 |

**这是本项目安全模型最需要讲清楚的一格**：默认 `safe` 下 exec tier 也自动放行，闸门唯一的触发条件是「命令文本命中正则」。架构文档自己主动点破了这一点（`docs/ARCHITECTURE.md:483-485`）[A]：

> Note `AutoApproves` returns true for `yolo` **and** `safe` regardless of tier (`approval.go:72`) — `safe` reacts only to concerns.

诚实度加分，但对做 slide 而言，"默认安全"这个说法要打引号。

### 1.4 三层：Concerns（命令文本模式）

`internal/security/policy.go:14-60` 三组正则 [A]：

- **networkTokens**（`policy.go:14-17`）：`curl wget nc ncat netcat nmap ssh scp sftp rsync socat "openssl s_client" dig whois`。全词匹配（`policy.go:27`：`(?i)(^|[\s;&|])` + QuoteMeta(token) + `($|[\s;&|])`），注释明说是为了让 `concat_files.sh` 不被读成 `cat`（`policy.go:19-21`）。只在 `!policy.AllowNetwork` 时检查（`policy.go:76`）。
- **destructivePatterns**（`policy.go:38-48`）：`rm -rf`、`dd if=`、`mkfs`、`diskutil erase`、`shutdown`、`reboot`、`launchctl`、`sudo`、`> /dev/sd|disk|rdisk`。**无条件检查，没有开关能关掉**。
- **sensitivePatterns**（`policy.go:50-60`）：`.ssh` `.aws` `.gnupg` `keychain` `id_rsa` `id_ed25519` `password` `secret` `token`。只在 `!policy.AllowSensitive` 时检查。

关键设计：`CommandConcerns` 返回的是**人类可读的清单而不是布尔**（`policy.go:62-64`）[A]：

```go
// CommandConcerns lists everything about a command that deserves a second look,
// in operator-readable form. Empty means unremarkable. Callers decide what to
// do with the list: ask the operator when there is one to ask, refuse otherwise.
```

三个硬校验函数（永不弹窗，直接返回 error）：
- `ValidateCommand`（`policy.go:94-103`）——"hard refusal, for callers with no approval path"。**注意：全仓库没有一个非测试调用点**（grep 结果只有定义处）[A]，属于事实上的死代码 / 预留 API。
- `ValidatePathRead`（`policy.go:105-115`）——敏感路径拒读。
- `ValidateWriteAllowed`（`policy.go:117-122`）——`"writes are disabled; start with --write to permit write_file"`。

### 1.5 审批执行点

`internal/security/approval.go:87-118` 是唯一的决策函数 [A]。核心两行：

```go
// Safety concerns outrank an "allow" override in every mode but yolo: the
// operator allowing `run_command` is not the same as allowing `rm -rf /`.
mustAsk := len(request.Concerns) > 0 && mode != types.ApprovalYolo
if !mustAsk && (override == "allow" || AutoApproves(mode, request.Tier)) {
	return nil
}
if tc.Confirm == nil {
	return &DeniedError{Message: refusalMessage(request, mode)}
}
```

`tc.Confirm == nil` → 拒绝而非默认放行（`approval.go:108`），这是无人值守（`--print` / CI）下的正确 fail-closed 姿势 [A]。

闸门被**故意分成两趟**跑（`docs/ARCHITECTURE.md:437-444` 说明，代码验证 [A]）：
1. **tier 闸**在 loop 里：`internal/core/agentloop.go:457-459`，此时 `Concerns` 为空，因为 loop 只知道工具名不知道命令文本。
2. **命令闸**在工具内部：`internal/tools/files.go:179-187`（`run_command`）、`internal/core/shell.go:64-71`（`!` shell 逃逸）、`internal/tools/retool.go:838-842`（`reverse_toolkit`，**但不带 Concerns**，见 §1.7 洞 #3）。

`internal/tools/files.go:176-187` 的注释把这个分工写得很直白：

```go
// The tier gate already ran in the loop; this is the command-specific
// pass, where a safety pattern turns into a prompt instead of a flat
// refusal.
```

### 1.6 审批 UI 在哪

- 渲染：`internal/ui/ui.go:204` `RenderApprovalRequest`。
- 装配：`internal/app/repl.go:394` `state.ToolContext.Confirm = createApprover(state, pane, liveInput.Pause)`，turn 结束后置 nil（`repl.go:395`）。
- 实现：`internal/app/repl.go:742-770`。注释（`repl.go:742-744`）[A]：

  ```go
  // createApprover builds the interactive approval prompt. The live pane is paused
  // so the prompt owns the screen, and a bare Enter means "no" — the safe answer
  // is the one you get by reflex.
  ```
- 非交互 editor 直接返回 nil approver（`repl.go:746-748`）→ 落回 fail-closed 分支。
- 按键：`y/yes` allow、`a/always` allow-always、其余/回车/EOF = deny（`repl.go:765-768`）。
- `allow always` / `deny always` 写回 `policy.Approvals`（`internal/security/approval.go:120-132`），**只活在内存中的这一次会话**，未落盘 [A]。

### 1.7 工作区隔离怎么实现的 —— 以及它的边界

唯一的路径包含函数是 `internal/util/util.go:110-124` [A]：

```go
// ResolveInside resolves a workspace-relative path and refuses to leave the
// workspace.
func ResolveInside(root, inputPath string) (string, error) {
	normalizedRoot, err := filepath.Abs(root)
	if err != nil { return "", err }
	resolved := inputPath
	if !filepath.IsAbs(resolved) {
		resolved = filepath.Join(normalizedRoot, inputPath)
	}
	resolved = filepath.Clean(resolved)
	if resolved != normalizedRoot && !strings.HasPrefix(resolved, normalizedRoot+string(filepath.Separator)) {
		return "", fmt.Errorf("path escapes workspace: %s", inputPath)
	}
	return resolved, nil
}
```

**做了**：`filepath.Abs` + `filepath.Join`（Join 自带 Clean，吃掉 `../`）+ 前缀比对，且用了 `normalizedRoot + Separator` 而不是裸前缀（所以 `/ws-evil` 不会被判为 `/ws` 的子路径）。
**没做**：`filepath.EvalSymlinks`。全仓库 grep 无任何 `EvalSymlinks` 调用 [A]。

集中调用点（10 处）[A]：`files.go:30,60,101,128,410`、`binary.go:359`、`retool.go:374,868`、`meta.go:47`、`app/inspect.go:108`。其中 `files.go:409-418` 的 `resolveReadable` 把 `ResolveInside` + `ValidatePathRead` 打包，被 `binary.go` 的一票 read 工具复用（`binary.go:31,286,337,346` 等），这是好的设计——单点收口。

---

#### 对抗性检查：沙箱到底守不守得住

**洞 #1 — `run_command` 就是 `bash -c`，工作区包含在它面前不存在。[A]**
`internal/tools/files.go:192-194`：

```go
result, err := Run([]string{"bash", "-c", command}, RunOptions{
	Cwd: tc.Workspace, TimeoutMs: timeoutMs, Ctx: tc.Context(),
})
```

`Cwd` 只是**起始目录**，不是牢笼。没有 chroot、没有 namespace、没有 seccomp、没有 `landlock`；`internal/tools/process.go:73-85` 的 `exec.CommandContext` 只做了 `Setpgid: true` 用于 ^C 传递，没有任何隔离。所以：
- `cat /etc/passwd` → 出工作区（不含敏感正则词，`safe` 模式下**连问都不问**）。
- `python3 -c "open('/tmp/x','w').write('y')"` → **绕过 `--write`**，因为 `ValidateWriteAllowed` 只在 `write_file`（`files.go:98`）、`carve_artifacts`（`binary.go:356`）、`frida_hook_template`（`meta.go:44`）三处调用，跟 shell 无关。
- `python3 -c "import urllib.request; ..."` → **绕过 `--allow-network`**，因为网络闸门是 14 个命令名的正则，不是真的网络策略。

这不是"bug"——对一个逆向工具这是必要能力——但**"reads stay inside the workspace / writes are off / network commands are off"（`README.md:479-483`）这三条只对 21 个结构化工具成立，对 `run_command` 不成立**。README 没有明写这个例外。[A/C]

**洞 #2 — 符号链接可以把工作区读扩张到全盘。[C，代码层面 A]**
`ResolveInside` 只做词法 Clean，不解析 symlink。在工作区里放一个 `link -> /etc`，`read_file path=link/passwd` 的解析结果 `<ws>/link/passwd` 前缀检查通过，随后 `os.Open`（`internal/tools/files.go:436`）按内核语义解析 symlink 读到 `/etc/passwd`。`ValidatePathRead` 只对**字符串**匹配敏感词（`policy.go:109-113`），`link/passwd` 里恰好含 `password`? 不含——`passwd` ≠ `password`，所以正则不触发。对 CTF 场景（工作区里就是别人给的样本/压缩包解出来的东西）这个面不算理论。同一问题也影响 `write_file`（`files.go:101-109`），一个指向仓库外的 symlink 可以让 `--write` 写到工作区外。

**洞 #3 — `reverse_toolkit` 的审批不带 Concerns，`--allow-network` 对它无效。[A]**
`internal/tools/retool.go:830-846`：

```go
func runRECommand(toolName string, command []string, label string, args map[string]any, tc types.ToolContext, outputDir string) (types.ToolResult, error) {
	...
	if err := security.RequestApproval(types.ApprovalRequest{
		Tool: toolName, Tier: types.TierExec, Summary: label,
	}, tc); err != nil {
```

`Concerns` 字段缺省为 nil → `mustAsk` 恒 false → `safe` 模式下 `AutoApproves` 直接放行。而 `reverse_toolkit` 的工具族清单（`retool.go:30-42`）里包含 `mitmproxy`、`mitmdump`、`mitmweb`、`frida`、`frida-ls-devices`、`objection`、`burpsuite`——**全是网络/远程设备工具**。换句话说：不给 `--allow-network`，`curl` 会被拦；但 `reverse_toolkit tool=mitmproxy` 一路绿灯。架构文档在 §13 "Add a tool" 第 5 条明确要求新工具自己做 `CommandConcerns + RequestApproval`（`docs/ARCHITECTURE.md:982-986`），`reverse_toolkit` 自己没照做。

**洞 #4 — 写盘发生在没有写闸门的地方（session dir）。[A]**
- `internal/tools/output.go:79-90` `writeArtifact`：任何工具输出超预算就 `os.MkdirAll(<sessionDir>/artifacts)` + `os.WriteFile(...)`，**没有 `ValidateWriteAllowed`**。默认 `--write` 关闭时依然写盘。
- `internal/tools/retool.go:892-900` `retoolOutputDir`：同样 `os.MkdirAll`，无写闸门。
- 语义上这是"运行时状态而非用户数据"（`.gitignore:5-9` 把 `sessions/ artifacts/ *.jsonl *.log` 全部忽略，注释写 "runtime state — transcripts and spilled tool output can contain anything"），可辩护；但和 README 的 "writes are off" 字面冲突。

**洞 #5 — `!cd` 用 bash 解析，可以把整个工作区搬到任意位置。[A]**
`internal/core/shell.go:92-115` `ResolveChdir` 跑 `bash -c "cd X && pwd"` 取结果，然后把 `ToolContext.Workspace` 换掉（commit `6cf789a` "fix: make !cd move the workspace" 的 body 明确说明）。注释自己写了 [A]：

> Resolution is delegated to bash so `~`, `$VARS`, relative paths, and symlinks behave exactly as they would for any other command run in the workspace.

即 `!cd /` 之后，所有 `ResolveInside` 的 root 就是 `/`，工作区包含名存实亡。这是 operator 主动动作、不是模型能触发的（模型没有 `!` 通道），所以属于**设计选择**而非漏洞——但讲 slide 时值得标出："工作区是一个可变字段，不是启动时冻结的边界"。

**洞 #6 — knowledge / skills 通道天然在工作区外读文件。[A]**
- `internal/knowledge/knowledge.go:139` `os.ReadFile(entry.Path)`，路径来自本地索引 `knowledge/reverse-index.json`，指向 operator 私人语料（`.gitignore:12-13` 注释确认）。`knowledge_read` 工具（`internal/tools/meta.go:572-598`）不过 `ResolveInside` 也不过 `ValidatePathRead`。
- `internal/skills/skills.go:45` 同理读 `assets.SkillsDir()`。
两者都是 read-only 且路径来自本地配置而非模型自由输入（模型只能给 id / name），**风险有限但确实是工作区包含的合法例外**。

**洞 #7 — `sensitivePatterns` 的误报面极大。[A/C]**
`password|secret|token` 三个裸词（`policy.go:57-59`），会让 `grep -r token ./src`、`strings ./libfoo.so | grep secret`、甚至任何路径含 `token` 的正常逆向操作触发审批。这在交互式下是"多按一次 y"，在 `--print` 无人值守下是**直接失败**（`approval.go:108-110`）。可用性代价没在 README 里说明。

**没有发现的**：没有 `panic()`（非测试代码 0 处 [A]）；没有任何工具绕开 `Execute` 直接被 loop 调用；`agentloop.go:457-462` 的 tier 闸对每个工具调用都执行、无例外分支 [A]。审批被拒是 `DeniedError`（`approval.go:36-38`），loop 把它当 tool result 回灌模型而不是杀掉 turn（`agentloop.go:464-477`）——这是个漂亮的设计点。

#### 直接 os./exec. 调用清单（跳过安全层的）[A]

模型可达路径中真正值得点名的（其余为 CLI/配置/会话基础设施，模型无法影响参数）：

| file:line | 调用 | 是否过安全层 |
| --- | --- | --- |
| `internal/tools/output.go:81,86` | `os.MkdirAll` / `os.WriteFile` | ✗ 无写闸门（sessionDir） |
| `internal/tools/retool.go:896` | `os.MkdirAll` | ✗ 无写闸门（sessionDir） |
| `internal/tools/process.go:73` | `exec.CommandContext` | 由调用方负责；`run_command` 过、`reverse_toolkit` 只过 tier |
| `internal/knowledge/knowledge.go:139` | `os.ReadFile` | ✗ 索引驱动，无 ResolveInside |
| `internal/skills/skills.go:45` | `os.ReadFile` | ✗ 目录驱动，无 ResolveInside |
| `internal/tools/files.go:436`、`binary.go:464` | `os.Open` | ✓ 上游 `resolveReadable` 已 Resolve+Validate |
| `internal/tools/files.go:105,109`、`meta.go:51,54`、`binary.go:363,372` | 写 | ✓ 均先 `ValidateWriteAllowed` + `ResolveInside` |

纯基础设施（模型不可达，列出仅为完整性）：`internal/core/session.go:59,89,289`、`internal/config/config.go:133,285,307,314`、`internal/auth/auth.go:253,265,272,352`、`internal/app/prompts.go:93,96,112,184`、`internal/app/editor.go:68,93,96`、`internal/app/inspect.go:157`、`internal/mcp/client.go:68`、`internal/providers/clitmux.go:86,99,170,264,282,429,453,518,706`、`internal/ui/splash.go:73,155`、`internal/assets/assets.go:106,156,163`、`cmd/import-knowledge/main.go:79,86,114`。

其中 `internal/mcp/client.go:68` `exec.Command(config.Command, config.Args...)` 值得一提：**MCP server 从配置文件直接起进程，不经过任何 policy 检查**，且它带来的工具会被 append 进同一 registry（`internal/app/app.go:154-161`），只享受 tier 闸（MCP 工具的 Risk 由 `internal/mcp/tools.go` 赋值，架构文档 `:676` 说"wrapped tool is `RiskWrite`"[B]）。信任模型是"配置文件可信"，合理但要说出来。

---

## 2. 授权使用（liability）的处理方式

项目**没有**独立的 SECURITY.md / 免责声明文件、没有 `.github/`（无 issue template、无 CODE_OF_CONDUCT）[A]。责任框架完全靠三处文本：

### 2.1 LICENSE — 纯 MIT，无附加限制 [A]

`LICENSE:1-21`，标准 MIT，`Copyright (c) 2026 overkazaf`。无 "authorized use only" 条款，责任限制就是 MIT 标准的 `THE SOFTWARE IS PROVIDED "AS IS" ... IN NO EVENT SHALL THE AUTHORS ... BE LIABLE`。也就是说：**法律层面没有做任何超出普通 OSS 的防御**。

### 2.2 System prompt —— 唯一的模型侧硬约束 [A]

`prompts/system.md:21-25`，逐字：

```markdown
## Safety Scope

- Treat work as authorized CTF/lab/local reverse engineering.
- Do not assist unauthorized live intrusion, credential theft, persistence, evasion against real systems, or exfiltration.
- Keep tool use local to the configured workspace unless the operator explicitly broadens policy.
```

Mission 段把范围限定在本地物件（`prompts/system.md:7`）：

```markdown
- Analyze local binaries, firmware extracts, malware-lab samples, crackmes, pwn challenges, protocol dumps, and CTF artifacts.
```

三个 role prompt（`prompts/roles/planner.md` 9 行、`executor.md` 11 行、`researcher.md` 9 行）**都不含独立的安全条款**，只有作用域收窄语（`executor.md:11`："that packet and do not infer or expand the broader objective."；`researcher.md:8`："Do not run heavy local changes; collect context and propose follow-up experiments."）[A]。注意：system prompt 是 operator 可编辑的（`prompts/system.md:17`："Role-specific system prompts are editable by the operator"，`/prompt edit <role>` 见 `README.md:534`）——**这层护栏可以被用户一条命令改掉**。[A]

### 2.3 README —— 定位声明 + 对"绕模型风控"的主动否认 [A]

首句定位（`README.md:3`）："A terminal agent for **authorized** reverse-engineering and CTF work."
结尾再说一遍（`README.md:541-543`）："Scoped for authorized CTF, lab, and local reverse-engineering work: binary triage, static inspection, local dynamic experiments, solve planning, and reproducible notes."

最有意思的是 §Project Motivation（`README.md:123-136`），它直面了"你这是不是在绕风控"：

> 0xAF-Re grew out of daily authorized RE/CTF work where coding-agent risk controls tightened and general models became more cautious around reverse-engineering language. **The goal is not to hide intent.** The agent keeps work local, authorized, and auditable, then improves the experience by splitting roles and composing models.

以及 §Workflow Modes 里的 caveman 模式声明（`README.md:377-390`）：

> Caveman mode is not translation, ciphering, or prompt laundering. It keeps the ordinary executor focused on workspace-local file facts and refuses unsafe live target, credential, persistence, deployment, or network work.
>
> About provider safety systems: 0xAF-Re **does not bypass model policy checks** or guarantee that a provider will not classify a turn. It reduces false positives for authorized local RE by changing what each role legitimately needs to see:
>
> - the planner sees the full authorized objective and produces a bounded packet
> - the executor sees only workspace paths and evidence-collection steps
> - the executor tool list is read-only and local
> - the session transcript keeps both phases auditable
> - unsafe requests are refused instead of being hidden in alternate wording

中文版对应 `README.zh-CN.md:104`：

> 这个项目**不做隐写、暗语或绕策略**，而是把工作限定在授权、本地、可审计范围内，再通过角色拆分和多模型组合改善体验。

**这条声明里有一句是可验证的**：「the executor tool list is read-only and local」。验证结果 ✅ [A]——`internal/workflow/delegate.go:145-161` `DelegatedExecutorTools` 白名单 14 个工具，全是 read tier：`list_files read_file grep file_info strings hexdump hash_file extract_symbols entropy_scan binary_mitigations find_bytes carve_artifacts apk_inspect update_plan`。`run_command`、`write_file`、`reverse_toolkit` 都不在里面。planner 更狠，只有 `update_plan`（`delegate.go:139-143`）。

⚠️ 但 `carve_artifacts` 在这个"read-only"白名单里，而它在 `--write` 打开时会写盘（`internal/tools/binary.go:356-375`）——白名单的 read-only 承诺依赖 `--write` 默认关闭，不是结构性保证。[A]

---

## 3. 工程现状诚实体检

### 3.1 代码规模与测试 [A]

```
Go 文件总数            83
非测试 Go 源码        20 672 行
测试代码               3 557 行  (25 个 _test.go)
测试 / 源码             17.2 %
```

**逐包分布（源码行 / 测试行）**：

| 包 | 源码 | 测试 | 比例 | 备注 |
| --- | --- | --- | --- | --- |
| `internal/security` | 266 | 193 | **72.6%** | 全仓最高，安全逻辑测得最认真 |
| `internal/core` | 1378 | 708 | 51.4% | loop / compaction / session / shell 各有测试 |
| `internal/plan` | 189 | 94 | 49.7% | |
| `internal/skills` | 188 | 92 | 48.9% | |
| `internal/workflow` | 433 | 151 | 34.9% | |
| `internal/config` | 452 | 145 | 32.1% | |
| `internal/auth` | 448 | 118 | 26.3% | |
| `internal/buildinfo` | 103 | 23 | 22.3% | |
| `internal/knowledge` | 728 | 151 | 20.7% | |
| `internal/providers` | 2108 | 366 | 17.4% | 5 个 provider 只有 2 个测试文件 |
| `internal/app` | 3482 | 602 | 17.3% | `repl.go` 本体基本没测 |
| `internal/ui` | 5064 | 544 | **10.7%** | 12 个源文件 / 1 个测试文件 |
| `internal/tools` | 4041 | 354 | **8.8%** | 9 个源文件 / 1 个测试文件；24 个工具的实现基本靠一个 `tools_test.go` |
| `internal/mcp` | 507 | 0 | **0%** | |
| `internal/types` | 545 | 0 | **0%** | 含手写 JSON 编解码 `message_json.go` |
| `internal/util` | 195 | 0 | **0%** | **含 `ResolveInside` 这个安全关键函数** |
| `cmd/0xaf` | 17 | 0 | 0% | 薄壳，可接受 |
| `cmd/import-knowledge` | 247 | 0 | 0% | |

**最不好看的一格**：`util.ResolveInside`（唯一的工作区包含实现）所在的 `internal/util` 包**零测试文件**。架构文档 `docs/ARCHITECTURE.md:937` 声称它被 `TestReadFileRefusesToEscapeTheWorkspace` 钉住 [B]——那个测试在 `internal/tools/tools_test.go` 里、走 `read_file` 间接覆盖，不是对 `ResolveInside` 本身的直接单测。所以「路径包含」这条不变量的直接单测覆盖为 0，只有一条端到端断言。[A]

第二不好看：`internal/tools` 4041 行只有 354 行测试，而这里正是全部 24 个工具、`SpillIfLarge` 预算、子进程 runner 的所在地。

### 3.2 CI / Lint [A]

- **没有 `.github/` 目录**。无 GitHub Actions、无 workflow、无 issue/PR 模板、无 dependabot。
- **没有 `.golangci.yml`** 或任何 linter 配置。
- 唯一的自动化是 `Makefile`（`Makefile:18-25`）：

  ```make
  test:
  	go test ./...
  vet:
  	go vet ./...
  fmt:
  	gofmt -w .
  ```

  即：质量保障 = 作者自己记得手动敲 `make test vet`。首个 commit（`cf07969`）的 body 声称 "go vet clean, go test ./... green" [B]（我按只读约束未执行验证）。

### 3.3 错误处理质量 [A]

- `TODO` / `FIXME` / `XXX` / `HACK` 在 `*.go` 中共 **0 处**。这既可以读作"没欠债"，也可以读作"欠债没被标记"——考虑到 §3.2 的缺口，后者更接近实情 [C]。
- `panic(` 非测试代码 **0 处**。
- `if err != nil {` 共 **203 处**；显式丢弃 `_ = ` **33 处**。丢弃基本集中在"装饰性"路径，且被架构文档列为**成文的不变量**（`docs/ARCHITECTURE.md:934`）[A]：

  > Plans are decorative and must never fail a run: unrecognized shapes yield `nil`, session writes are `_ =`, `sanitize` clamps rather than rejects... | break it and | an upstream CLI changing its plan event shape starts killing turns

- 错误分类做得比多数同规模项目细：`errorResult`（模型该看到并自愈的预期失败）vs 返回 Go `error`（模型无法处理的）——`internal/tools/registry.go:63-66` + `docs/ARCHITECTURE.md:987-990` 明文规定这条约定 [A]。
- `DeniedError` + `util.ErrInterrupted`（`internal/util/util.go:17`，wraps `context.Canceled` 所以 `errors.Is` 两边都成立）是两个专门的哨兵类型 [A]。
- 小瑕疵：`asDenied`（`approval.go:45-58`）和 `asExitError`（`process.go:171-184`）是**手写的 unwrap 循环**，标准库 `errors.As` 就能做，且 `IsAbort`（`util.go:22-29`）在类型判断失败后**回退到子串匹配** `strings.Contains(lower, "context canceled")` —— 脆弱，会误判任何输出里含这串字符的工具结果 [A/C]。

### 3.4 依赖与产物 [A]

- `go.mod`：**一个**直接依赖 `golang.org/x/term v0.18.0`（+间接 `golang.org/x/sys`）。首 commit 自称 "one external dependency"，属实。
- `go.mod` 声明 `go 1.22`，但最后一个 commit（`926e615`）的文档说的是 "Go 1.21+ requirement"——**文档与 go.mod 不一致**（1.21 vs 1.22）[A]。
- 交叉编译 4 目标（`Makefile:29-33`）：linux/darwin × amd64/arm64，`CGO_ENABLED=0`。
- 首 commit 自称：`~6.7 ms cold start, 6.7 MB binary` [B]。

---

## 4. 路线图 / 未来方向

### 4.1 明文写下来的规划 —— 只有一条 [A]

**在整个仓库中，"roadmap" 一词只出现 2 次**，指向同一件事：

`README.md:135-136`：
> **Roadmap:** local models and reproducible benchmark cases will be added so provider/workflow quality can be measured and improved over time.

`README.zh-CN.md:109`：
> **后续计划:** 加入本地模型和可复现评测样例，用样例结果衡量不同 provider/workflow 的效果并迭代。

`docs/index.html:138-143`（项目主页上做成了一张卡片，标题 "Roadmap with measurements"）：
> Local model routes and concrete evaluation samples are planned so the agent can be measured: same artifact, same workflow, different provider. That gives the project a practical way to improve instead of relying on anecdotes.

**没有** `ROADMAP.md`、没有 `docs/` 下的规划文档、没有 issue 模板、没有 TODO 文件、没有 milestone 引用 [A]。所以：**"stated roadmap" = 两个具体项（本地模型 route + 可复现评测集），仅此而已。** 任何比这更宏大的路线图都是编的。

### 4.2 24 个 commit 的开发轨迹 [A]

时间跨度：2026-07-27 → 2026-07-31，**5 天 24 个 commit**。这是一次密集冲刺，不是长期演进。

| # | 日期 | commit | 内容 |
| --- | --- | --- | --- |
| 1 | 07-27 | `cf07969` | **初始投放**：整个 agent 一次性落地——core loop、5 个 provider adapter、24 个工具、security 包、live UI、mcp/skills/knowledge、7 张架构图、双语 README。commit body 就是一篇完整的架构说明 |
| 2 | 07-28 | `cdcd1e2` | feat: workflow 模式 + live task queue |
| 3-5 | 07-28 | `18e58bf` `27647e0` | docs: 营销素材库、banner 嵌入群二维码 |
| 6 | 07-28 | `af32e97` | fix: 合并 embedded 与本地 skills |
| 7 | 07-28 | `f74e45e` | feat: 显示运行时 commit hash |
| 8 | 07-28 | `d75ebad` | fix: 收紧逆向 skill workflow |
| 9 | 07-28 | `fd9b632` | fix: raw mode 下 live HUD 对齐（CRLF，body 有完整根因） |
| 10 | 07-28 | `6cf789a` | fix: `!cd` 改变工作区（body 有完整根因） |
| 11 | 07-28 | `637ea22` | feat: researcher role prompt（第三个角色） |
| 12 | 07-28 | `07cc49b` | **chore: release v0.1.1** |
| 13 | 07-28 | `29e7b21` | docs: 双语 onboarding 用例 |
| 14 | 07-28 | `1198918` | **feat: delegated caveman workflow**（tag v0.1.2） |
| 15-19 | 07-28~29 | `c1077f2` `1dfde31` `494cacd` `e4e74ac` `aded077` | docs 五连：双语页面、项目动机、workflow evidence 模式、workflow policy 边界 |
| 20 | 07-29 | `e66a014` | docs: developer highlights |
| 21 | 07-29 | `703383e` | feat: angr + frida 模板 |
| 22 | 07-29 | `9cefd22` | **chore: bump v0.1.3** |
| 23 | 07-29 | `d1623de` | **feat: proxy capture toolkit**（Burp/mitmproxy，tag v0.1.4） |
| 24 | 07-30 | `78fb781` | fix: 稳定 live repl 状态（tag v0.1.5） |
| 25 | 07-31 | `926e615` | docs: Go 版本要求 + Worked Case（HEAD，**未打 tag**） |

**轨迹形状（我的读法 [C]）**：
1. **Day 1 = 一次性把骨架全落地**（不是渐进式开发，是一个已经在私下写了很久的项目做首次公开投放）。
2. **Day 2 = 功能补全 + 第一个 release**（workflow 模式 → researcher 角色 → v0.1.1 → caveman → v0.1.2）。
3. **Day 2-3 = 文档密集期**（24 个 commit 里有 **10 个是 docs**，占 42%）。这个比例说明作者当前的瓶颈是**说清楚**而不是**写出来**。
4. **Day 3-4 = 工具面横向扩张**（angr/frida 模板 → proxy capture toolkit）。
5. **最后两个 commit 是 fix + docs**，且 HEAD 未打 tag。

**最后几个 commit 指向什么 [C]**：`d1623de`（proxy capture）把工具面从"静态分析 + 本地动态"推进到了 **HTTP 抓包 / 移动端流量**；`926e615`（Worked Case，把一道题用"纯手工"和"agent"各解一遍，声称数据来自真实 session）指向**可复现的效果证据**——这恰好就是 §4.1 那条 "reproducible benchmark cases" 路线图的第一块砖。所以下一步最可能是：**把 Worked Case 这种手工转录的案例，变成能自动跑、能横向对比 provider 的评测集**。这是 stated roadmap 与 commit 轨迹唯一的交点。

### 4.3 代码接缝指向的缺口（**推断，非项目声明**）[A 证据 / C 结论]

| # | 缺口 | 证据 file:line |
| --- | --- | --- |
| 1 | **本地模型 provider 不存在。** 5 个 adapter：`anthropic` / `openai-responses` / `openai-chat` / `cli-tmux` / `mock`（`internal/providers/providers.go:16` 的 Create switch）。没有 ollama / llama.cpp / vLLM。README 说要加本地模型，但连口子都还没开——不过 `openai-chat` 类型 + 自定义 `baseUrl` 事实上可以接 ollama，所以这条路线图**可能只是文档工作而非代码工作** | `internal/providers/providers.go:16`，`config.example.json` 无本地条目 |
| 2 | **`security.ValidateCommand` 是零调用点的死代码。** 注释说它是 "the hard refusal, for callers with no approval path"——这个"caller"从未出现。要么是给未来的非交互模式预留，要么是重构残留 | `internal/security/policy.go:93-103`（全仓 grep 仅定义处） |
| 3 | **审批记忆不持久化。** `allow always` / `deny always` 写进 `policy.Approvals` 这个内存 map，进程退出即失。`config.go` 里有 prefs 落盘机制（`internal/config/config.go:285,307,314`）却没用于审批 | `internal/security/approval.go:120-132` vs `internal/config/config.go:307-314` |
| 4 | **没有任何真实沙箱。** 只有 `Setpgid`，无 chroot / namespace / seccomp / landlock / Docker。对一个跑不可信二进制的逆向工具，这是最大的结构性缺口 | `internal/tools/process.go:73-85` |
| 5 | **符号链接未解析。** 补 `filepath.EvalSymlinks` 是一个 3 行的明显 TODO，没人写 | `internal/util/util.go:112-124` |
| 6 | **`reverse_toolkit` 未接命令级 concerns。** 架构文档自己规定的规矩，自己的最大工具没遵守 | `internal/tools/retool.go:838` vs `docs/ARCHITECTURE.md:982-986` |
| 7 | **无 CI。** `Makefile` 有 `test`/`vet` target 但没有触发器。加个 GitHub Actions 是最低垂的果实 | 无 `.github/` |
| 8 | **`internal/mcp` / `internal/types` / `internal/util` 零测试。** MCP 是外部工具的入口（`client.go:68` 起子进程），types 有手写 JSON 编解码，util 有安全关键的路径函数 | 见 §3.1 表 |
| 9 | **`internal/ui` 5064 行是全仓最大的包**，比 core+security+tools 的核心逻辑加起来还重，测试率 10.7%。终端 UI 的重量已经超过 agent 本体 | 见 §3.1 表 |
| 10 | **MCP 只有一个示例配置且被禁用。** `config.example.json` 的 `mcpServers.ida` 带 `"disabled": true`——MCP 通道是通的但生态是空的 | `config.example.json`（mcpServers 段） |
| 11 | **Windows 未支持。** `make cross` 只出 linux/darwin；`internal/tools/process.go:11,79` 用 `syscall.SysProcAttr{Setpgid}`（POSIX-only），`internal/app/repl.go`/`internal/ui/live.go` 有 `//go:build` 约束依赖 `x/sys/unix` 和 `x/term` | `Makefile:29-33`，`internal/tools/process.go:79`，commit `926e615` body |
| 12 | **文档 vs go.mod 的 Go 版本不一致**（1.21+ vs 1.22） | `go.mod:3` vs `926e615` commit body |

---

## 5. 分发 / 采纳

### 5.1 版本与发布 [A]

- 当前版本常量：`internal/buildinfo/buildinfo.go:8` → `const Version = "0.1.5"`。
- Git tags **5 个**，全部在 4 天内打完：

  | tag | 日期 | commit |
  | --- | --- | --- |
  | v0.1.1 | 2026-07-28 | `07cc49b` |
  | v0.1.2 | 2026-07-28 | `1198918` |
  | v0.1.3 | 2026-07-29 | `9cefd22` |
  | v0.1.4 | 2026-07-29 | `d1623de` |
  | v0.1.5 | 2026-07-30 | `78fb781` |

  注意**没有 v0.1.0**（首个 commit 未打 tag），且 HEAD（`926e615`）在 v0.1.5 之后、未打 tag。
- 安装方式：`go install github.com/overkazaf/re-agent/cmd/0xaf@v0.1.5`（`README.zh-CN.md:114`）——**纯 Go module 分发，没有 GitHub Releases 的预编译二进制、没有 Homebrew tap、没有 Docker 镜像**（无 `.github/workflows`，无 `Dockerfile`）[A]。
- commit hash 通过 `-ldflags -X ...buildinfo.Commit` 注入，也能从 `debug.ReadBuildInfo()` 的 `vcs.revision` 回落（`internal/buildinfo/buildinfo.go:11-45`），`/status` 能显示"是否 dirty"。这是很讲究的细节。

### 5.2 项目页与素材 [A]

- 项目主页：**https://overkazaf.github.io/re-agent/**（`README.md:9,539`），中文版 `index.zh-CN.html`（`README.zh-CN.md:8,490`）。GitHub Pages 从 `docs/` 直出。
- `docs/social-card.png` + `docs/social-card.svg` —— OG 社交卡片。
- `docs/cards/` —— **11 张竖版宣传卡 SVG** + `png/` 目录：`01-cover` `02-problem` `03-two-seats` `04-context-budget` `05-refusal` `06-live-pane` `07-fast-path` `08-model-says-no` `09-workflow-modes` `10-live-queue` `11-xhs-group`。`docs/index.zh-CN.html:228` 写明："竖版卡片是 1080×1440，适合**小红书**笔记"。
- `docs/shots/` —— 14 张终端截图 SVG（approval / auth / boot / help / live / palette / providers / reply / scan / shell / theme / tools / turn / verify）。
- `docs/casts/` —— 3 段动画 SVG（deck / quickstart / scan），由 `scripts/capture-cast.py` + `scripts/record-casts.sh` 生成（commit `926e615` body）。
- `docs/diagrams/` —— 7 张架构图 + 双语 index.html，其中 `06-oh-my-pi.svg` / `07-vs-oh-my-pi.svg` 是**与另一个 harness（oh-my-pi）的对比图**——明确的竞品定位动作。
- `scripts/` 四个脚本（`capture-cast.py` `capture-shot.py` `make-cards.py` `record-casts.sh`）—— **素材生产被脚本化了**，说明作者把"营销素材"当工程产物在维护 [C]。

### 5.3 社区渠道 [A]

- **唯一的社区入口是小红书群二维码**：`docs/xhs-group-qr.png` + `docs/xhs-group-qr-crop.png`，嵌在 banner 里（commit `27647e0` "docs: embed group qr in banner"），并在 `docs/index.zh-CN.html:249-250` 提供下载（alt="小红书群二维码"）。宣传卡 `11-xhs-group.svg` 也是为它做的。
- **没有 Discord、没有 Telegram、没有 Slack、没有 issue 模板、没有 CONTRIBUTING.md**。
- 分发策略读法 [C]：**英文做技术门面（README/架构文档/项目页），中文做社区获客（小红书群 + 竖版卡片）**，两套素材并行维护，双语 README 甚至保持逐节对齐（`README.md:33-51` 的 Bilingual Map 表）。

---

## 6. 给 slide 的取舍建议

**可以拿来讲的三个"漂亮点"**（都验证过）：
1. `DeniedError` 让"拒绝"变成模型能读到的 tool result，而不是杀掉 turn（`approval.go:36` + `agentloop.go:464-477`）——这是"安全不打断 agent"的正确姿势。
2. 闸门故意跑两趟：loop 知道工具名不知道命令文本，工具知道命令文本——职责切得干净（`agentloop.go:457` vs `files.go:183`），且架构文档把"破坏它会怎样"写成了不变量表（`docs/ARCHITECTURE.md:930-937`）。
3. `tc.Confirm == nil` = 拒绝（`approval.go:108`），无人值守 fail-closed。

**必须一起讲的三个"诚实点"**（否则 slide 就是软文）：
1. 默认 `safe` 模式对 exec tier 也放行——安全依赖正则命中，不依赖 tier（作者自己在 `docs/ARCHITECTURE.md:483` 承认了）。
2. `run_command` = `bash -c`，没有真沙箱；`--write` / `--allow-network` / 工作区包含三道闸在 shell 面前都不成立。
3. 唯一的路径包含函数所在的 `internal/util` 包**零测试**，且不解析 symlink。

**路线图必须说清是"一句话"**：本地模型 + 可复现评测集，来自 `README.md:135`，三处文案（英/中/主页卡片）说的是同一件事。其余 12 条"未来方向"是我从代码接缝推的，不是项目承诺。
