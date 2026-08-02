# R03 — 0xAF-Re / re-agent 功能点全清单

> 取证对象：`/Users/overkazaf/playground/research/re-agent`（Go，24229 行 .go，不含测试约 20k）
> 方法：全部从源码枚举，非 README 转述。标注 **[A]** = 读源码验证 / **[B]** = 文档声称 / **[C]** = 推断。
> 引用格式 `文件:行`。

---

## 0. 总览数字（全部 [A]）

| 项 | 数量 | 证据 |
|---|---|---|
| 斜杠命令（唯一名） | **52** | `internal/ui/help.go:23-88` 共 54 行，其中 `/know raw`、`/know read` 是 `/know` 的子形式 |
| 命令帮助表行数 | 54 | 同上 |
| `commands.go` 分派分支 | 50 个命令名 + `/exit` `/quit` 在 REPL 层 | `internal/app/commands.go:29-352`；`internal/app/repl.go:80` |
| 回合中（mid-turn）可用命令 | **5** | `internal/app/repl.go:717-733` |
| 内置模型工具 | **24** | `internal/tools/registry.go:24-51` |
| 只读工具 / 写 / 执行 | **21 / 1 / 2** | 见 §2 |
| 内置 skills 目录 | **33** | `skills/*/SKILL.md` |
| skill 前置元数据字段 | `name`(33) `description`(33) `tags`(9) | 全量 frontmatter 扫描 |
| reverse_toolkit 外部工具族 | **21** | `internal/tools/retool.go:83-123` |
| reverse_toolkit 探针族 | **17** | `internal/tools/retool.go:25-43` |
| carve 文件签名 | **13** | `internal/tools/binary.go:793-811` |
| 解码器模式 | **8** | `internal/tools/decode.go:19` |
| 内置 provider 预设 | **9** | `internal/config/config.go:26-111` |
| 审批模式 | **4** | `internal/security/approval.go:19-21` |
| 工作流模式 | **4** | `internal/workflow/workflow.go:16-22` |
| UI 主题 | 4（deck/amber/matrix/mono） | `internal/ui/help.go:30` |
| Frida 命名模板 | 6 | `internal/tools/meta.go:99-109` |

**一句话**：一个 CLI 里塞了 52 个斜杠命令 + 24 个模型工具 + 33 个 skill + 21 个外部逆向工具适配器 + MCP 客户端 + 本地知识库检索。

---

## 1. 斜杠命令全清单（52 个）

分派表：`internal/app/commands.go:27` `func handleCommand(line string, state *State) error`，一个巨型 `switch`。
帮助/补全/调色板三处共用同一张表：`internal/ui/help.go:23` `var SlashCommandSections`（注释原话："One table drives all three so they can never disagree." `help.go:4`）。

### 1.1 session（21 条）— `help.go:24-46`

| 命令 | 参数 | 作用 | 是否调模型 | 实现 |
|---|---|---|---|---|
| `/` | — | 列出可执行斜杠命令面板 | 否 | `commands.go:35-37` |
| `/welcome` | — | 首次运行引导 demo | 否 | `commands.go:30-34` |
| `/help` | — | 命令甲板 | 否 | `commands.go:38-40` |
| `/version` | — | 版本 / commit / 构建元数据 | 否 | `commands.go:41-43` |
| `/clear` | — | 清屏并重绘 banner | 否 | `commands.go:58-61` |
| `/theme` | `[deck\|amber\|matrix\|mono]` | 切换配色，**落盘** `config.SaveUIPrefs` | 否 | `commands.go:44-57` |
| `/flow` | `[full\|flow\|trace\|off]` | 实时数据流图 / trace 行开关，落盘 | 否 | `commands.go:175-187` |
| `/workflow` | `[off\|auto\|specialist\|caveman]` | RE 工作流模式 | 否 | `commands.go:188-198` |
| `/tasks` | `[auto\|collapse\|expand\|toggle]` | 折叠/展开实时任务列表 | 否 | `commands.go:525-552` |
| `/think` | `[auto\|collapse\|expand\|toggle\|on\|off]` | 折叠/展开流式推理 | 否 | `commands.go:564-591` |
| `/queue` | `[list\|add\|edit <id> <t>\|cancel <id\|all>\|clear\|run]` | 排队待执行提示 | 否 | `commands.go:463-516` |
| `/prompt` | `[list\|show\|path\|edit\|set\|reset\|reload]` | 编辑全局/分角色系统提示词 | 否 | `internal/app/prompts.go:43-124` |
| `/context` | — | 上下文 token 估算 vs 预算（默认 48000） | 否 | `commands.go:205-222`；`internal/core/agentloop.go:18` |
| `/compact` | `[provider]` | **调模型**把会话折成摘要 | **是** | `commands.go:223-238` |
| `/session` | — | 打印 JSONL transcript 路径 | 否 | `commands.go:272-274` |
| `/sessions` | — | 列最近 20 个会话 | 否 | `commands.go:239-241` |
| `/resume` | `[id]` | 载入历史会话消息 + plan | 否 | `commands.go:242-271` |
| `/policy` | — | 打印当前安全策略 JSON | 否 | `commands.go:277-283` |
| `/approval` | `[mode \| tool <name> allow\|deny \| reset]` | 审批模式 / 单工具覆盖 | 否 | `commands.go:275-276, 356-394` |
| `/exit` | — | 退出 | 否 | `repl.go:80` |
| `/quit` | — | 退出 | 否 | `repl.go:80` |

### 1.2 routing（8 条）— `help.go:47-56`

| 命令 | 参数 | 作用 | 实现 |
|---|---|---|---|
| `/role` | `planner\|executor\|researcher\|auto` | 选择哪一侧回答，清空 pin | `commands.go:307-314` |
| `/agent` | `<name>\|auto` | 钉住一个 provider | `commands.go:315-326` |
| `/model` | `<provider\|planner\|executor\|researcher\|active> <model>` | 本会话覆盖模型；无参列出全部 | `commands.go:396-433` |
| `/planner` | `<name>` | 设 planner provider | `commands.go:327-333` |
| `/executor` | `<name>` | 设 executor provider | `commands.go:334-340` |
| `/researcher` | `<name>` | 设 researcher provider | `commands.go:341-347` |
| `/effort` | `<provider> [level]` | reasoning effort（minimal…max）；CLI 类 provider 下回合生效 | `commands.go:62-88` |
| `/providers` | — | 列出配置的 provider | `commands.go:93-95` |

### 1.3 auth（4 条）— `help.go:57-62`

| 命令 | 参数 | 作用 | 实现 |
|---|---|---|---|
| `/auth` | — | 凭据状态（与 `/status` 同一分支） | `commands.go:284-286` |
| `/status` | — | 同上 | `commands.go:284-286` |
| `/login` | `[provider]` | 本地存 API key；缺省按 role 推断 | `commands.go:287-292, 883-891` |
| `/logout` | `<provider>` | 删除已存凭据 | `commands.go:293-306` |

### 1.4 direct tools（16 条，"零 token 廉价路"主力）— `help.go:63-80`

| 命令 | 参数 | 底层工具 | 调模型 | 实现 |
|---|---|---|---|---|
| `/tools` | — | 表格渲染 `state.Tools` | 否 | `commands.go:99-101` |
| `/mcp` | — | MCP 服务器 + 贡献的工具 | 否 | `commands.go:96-98, 628-642` |
| `/scan` | `<path>` | `ctf_triage` | 否 | `commands.go:109-113` |
| `/mitigations` | `<binary>` | `binary_mitigations` | 否 | `commands.go:125-129` |
| `/entropy` | `<file>` | `entropy_scan` | 否 | `commands.go:120-124` |
| `/findbytes` | `<file> <text\|hex>` | `find_bytes`（**自动判 hex/text**） | 否 | `commands.go:130-140` |
| `/carve` | `<file>` | `carve_artifacts` | 否 | `commands.go:141-145` |
| `/hex` | `<file> [offset] [len]` | `hexdump`（**接受 0x 前缀**） | 否 | `commands.go:146-147`；`internal/app/inspect.go:33-80` |
| `/r2` | `<file> [-w]` | **把终端交给交互式 radare2** | 否 | `commands.go:148-149`；`inspect.go` |
| `/apk` | `<apk>` | `apk_inspect` | 否 | `commands.go:150-154` |
| `/retool` | `[tool action path k=v...]` | `reverse_toolkit` | 否 | `commands.go:155-160, 777-810` |
| `/decode` | `[mode] <input>` | `ctf_decode`（别名 b64/b64url/urldecode/xorbf） | 否 | `commands.go:114-119, 812-849` |
| `/hook` | `[java\|native\|objc] <target> [method] [sig]` | `frida_hook_template` | 否 | `commands.go:161-166, 851-881` |
| `/plan` | — | 重印当前任务列表 | 否 | `commands.go:167-174` |
| `/read` | `<path>` | `read_file` | 否 | `commands.go:348-349` |
| `/run` | `<command>` | `run_command`（走同一审批门） | 否 | `commands.go:350-351` |

统一执行器：`commands.go:764-775` `runDirectTool(name, args, state)` — 直接 `tool.Execute(args, *state.ToolContext)`，**完全不进 agent loop、不产生 token**。[A]

另有 shell 逃逸 `!<command>`：`repl.go:86-88, 776-791`，输出流式打印并**追加进 transcript** 供下一轮引用；与 `run_command` 同策略，^C 可杀。[A]

### 1.5 skills & knowledge（5 行 / 3 命令）— `help.go:81-87`

| 命令 | 参数 | 作用 | 调模型 |
|---|---|---|---|
| `/skills` | — | 列内置 skill | 否（`commands.go:102-104`） |
| `/skill` | `<name> [task]` | 无 task 直接打印 skill 正文；有 task 则**发起一个回合**并强制该 workflow | 有 task 时**是**（`commands.go:646-661`） |
| `/know` | `<query>` | 检索 + **新建独立 provider 实例**合成带引用的答案 | **是**（`commands.go:702-754`） |
| `/know raw` | `<query>` | 原始索引命中，零 token | 否（`commands.go:680-685`） |
| `/know read` | `<entry-id>` | 全文读一条，上限 24000 字节 | 否（`commands.go:670-679`） |

### 1.6 回合中可用的 5 个命令 [A]

`internal/app/repl.go:716-733`：

```go
func (c *liveInputController) handleLiveCommand(line string) error {
	command, arg := splitCommand(line)
	switch command {
	case "/queue":   return handleQueueCommand(arg, c.state, c.pane)
	case "/tasks":   return handleTasksCommand(arg, c.state, c.pane)
	case "/think":   return handleThinkCommand(arg, c.state, c.pane)
	case "/model":   return handleModelCommand(arg, c.state, c.pane)
	case "/version": emitNotice(c.pane, buildinfo.VersionReport()); return nil
	default:
		return fmt.Errorf("during a turn use /queue, /tasks, /think, /model, or /version; other commands run at the normal prompt")
	}
}
```

**非斜杠输入在回合中不会被丢弃，而是自动入队**（`repl.go:708-714`：`item := c.state.Queue.Add(line)` → `queued #N for the next turn`）。这就是"中途操舵"的落点。[A]

### 1.7 命令分类计数

| 类别 | 条数 | 是否零 token |
|---|---|---|
| session / UI 控制 | 21 | 20 零 token（`/compact` 例外） |
| routing 配置 | 8 | 全部零 token |
| auth | 4 | 全部零 token |
| 本地直连工具 | 16 | **全部零 token** |
| skills & knowledge | 3（5 行） | 2.5 零 token（`/know` 裸查询与 `/skill X task` 调模型） |
| **合计** | **52** | **零 token 的 ≈ 49** |

---

## 2. 暴露给模型的工具（24 个）

注册表：`internal/tools/registry.go:24-51`，注释写明"in the order the operator sees it in `/tools`"。
Schema 统一由 `objectSchema()` 生成（`registry.go:10-20`，固定 `additionalProperties:false`）。

| # | 工具名 | 风险层 | 必填参数 | 可选参数（默认值） | 干什么 |
|---|---|---|---|---|---|
| 1 | `list_files` | read | — | `path`(`.`) `recursive`(false) `maxEntries`(200) | 列工作区文件 |
| 2 | `read_file` | read | `path` | `maxBytes`(65536) | 按 UTF-8 读，截断 |
| 3 | `write_file` | **write** | `path` `content` | — | 写文件，**非 `--write` 启动则禁用** |
| 4 | `grep` | read | `pattern` | `path`(`.`) `maxMatches`(200) | 优先 ripgrep，退化为递归扫描 |
| 5 | `run_command` | **execute** | `command` | `timeoutMs`(30000) | 本地命令，网络/破坏性默认拦 |
| 6 | `file_info` | read | `path` | — | `file(1)` |
| 7 | `strings` | read | `path` | `minLength`(4) `maxBytes`(65536) | 可打印串 |
| 8 | `hexdump` | read | `path` | `offset`(0) `length`(512) | 十六进制窗口 |
| 9 | `hash_file` | read | `path` | — | SHA-256 + 大小 |
| 10 | `extract_symbols` | read | `path` | `maxBytes`(65536) | nm / readelf / objdump / otool 轮试 |
| 11 | `ctf_triage` | read | `path` | `maxBytes`(1048576) `maxStrings`(40) | 见 §3.1 |
| 12 | `ctf_decode` | read | `input` | `mode`(auto, 8 枚举) `key` `maxOutputBytes`(4096) | 见 §3.4 |
| 13 | `entropy_scan` | read | `path` | `window`(1024) `step`(512) `top`(12) `maxBytes`(4194304) | 见 §3.2 |
| 14 | `binary_mitigations` | read | `path` | — | 见 §3.5 |
| 15 | `find_bytes` | read | `path` `needle` | `mode`(text/hex/regex) `maxMatches`(30) `context`(16) | 偏移 + hex/ascii 上下文 |
| 16 | `carve_artifacts` | read | `path` | `extract`(false) `outDir`(carved) `maxArtifacts`(50) | 见 §3.3。`extract=true` 需 `--write` |
| 17 | `reverse_toolkit` | **execute** | — | `tool`(inventory) `action`(auto) `template` `path` `rules` `address` `symbol` `host` `port`(8080) `arch`(x64) `lines`(80) `maxBytes`(65536) `timeoutMs`(120000) | 21 个外部工具族的固定安全动作 |
| 18 | `apk_inspect` | read | `path` | `maxEntries`(200) | 见 §3.6 |
| 19 | `frida_hook_template` | read | — | `platform`(android_java/android_native/ios_objc) `template` `target` `method` `signature` `includeStack`(true) `outputPath` | 生成 Frida 脚手架；写盘需 `--write` |
| 20 | `list_skills` | read | — | — | 列本地 skill 目录 |
| 21 | `read_skill` | read | `name` | — | 按名或 tag 读一个 skill 全文 |
| 22 | `knowledge_search` | read | `query` | `limit`(8) `raw`(false) | 返回 agent-ready digest |
| 23 | `knowledge_read` | read | `id` | `maxBytes`(24000) | 读一条知识条目 |
| 24 | `update_plan` | read | `plan[]` | `explanation` | **发布/更新操作员可见的任务列表** |

行号：`files.go:21/52/90/119/167/210/235/287/334/359`；`binary.go:22/134/210/278/329/398`；`decode.go:21`；`retool.go:46`；`meta.go:22/513/526/548/575/609`。

### 2.1 安全分层 [A]

- **21 read / 1 write / 2 execute**。
- `update_plan` 被标 `RiskRead`（`meta.go:612`）——它只改宿主 UI 状态，不碰文件系统，所以不需要审批。[A]
- MCP 导入的工具**一律标 `RiskWrite`**：`internal/mcp/tools.go:103-105` 注释 "MCP servers do not declare a tier; treat them as state-changing"。[A]
- 层级映射：`internal/security/approval.go:60-70` `TierForRisk`（execute 与 network 合并为 `TierExec`）。
- 审批模式 4 种：`yolo` / `safe`(默认) / `write` / `always-ask`（`approval.go:19-23`）。
  - `safe` = 只对"疑虑"反应（`approval.go:72-83` `AutoApproves` 里 yolo 与 safe 同样直通）。
- **关键设计**：安全疑虑压过 `allow` 覆盖，只有 yolo 例外（`approval.go:101-106`）：
  ```go
  mustAsk := len(request.Concerns) > 0 && mode != types.ApprovalYolo
  ```
  注释："the operator allowing `run_command` is not the same as allowing `rm -rf /`"。
- 疑虑来源 `internal/security/policy.go:65-90`：9 条破坏性模式（`rm -rf`/`dd if=`/`mkfs`/`diskutil erase`/`shutdown`/`reboot`/`launchctl`/`sudo`/`> /dev/sd*`）、14 个网络 token（curl/wget/nc/ncat/netcat/nmap/ssh/scp/sftp/rsync/socat/`openssl s_client`/dig/whois）、9 条敏感模式（.ssh/.aws/.gnupg/keychain/id_rsa/id_ed25519/password/secret/token）。
- 网络/敏感模式在 `--allow-network` / `--allow-sensitive` 下不再提示。
- 交互审批四选一：`y/yes`=允许、`a/always`=永久允许、`d/never`=永久拒绝、**回车=拒绝**（`repl.go:753-763`，注释："a bare Enter means 'no' — the safe answer is the one you get by reflex"）。[A]
- 默认策略：`internal/app/app.go:132-134` — `CommandTimeoutMs: 30_000`、`MaxReadBytes: 128*1024`、`MaxToolOutputChars: 24_000`。[A]

---

## 3. "廉价路"：零 token 本地分析到底算了什么

以下全部 [A]，读实现得出。

### 3.1 `/scan` → `ctf_triage`（`binary.go:22-132`）

目录时：`walkTree` 列条目上限 `clamp(maxStrings, 1, 200)`。
文件时，一次性算出：

| 字段 | 计算 |
|---|---|
| `type` | 外调 `file -b` |
| `size` / `sha256` | `os.Stat` + 流式 SHA-256（`binary.go:463-474`） |
| `magic.hex` / `magic.ascii` | 前 **16 字节** |
| `sample` | 前 `clamp(maxBytes, 1KiB, 8MiB)` 字节，默认 1 MiB |
| `entropy` | 全样本 Shannon，bits/byte |
| `printable` | 可打印比（含 `\n\r\t`） |
| `signals` | 见下 |
| `next` | 最多 6 条启发式建议 |

**字符串分类器** `classifyStrings`（`binary.go:560-620`），先 `extractPrintableStrings(sample, 4)` 抽最短 4 的 ASCII 串，再打 10 类标签（`binary.go:546-558`）：

| 标签 | 正则要点 |
|---|---|
| `flag-like` | `(flag\|ctf\|picoCTF\|HTB\|DUCTF\|N1CTF\|hxp\|uiuctf\|0xaf){...}` |
| `url` / `email` / `ipv4` | 常规 |
| `secret-keyword` | password/passwd/secret/token/api_key/private_key |
| `crypto-codec` | xor/base64/rot13/aes/des/rsa/ecb/cbc/md5/sha1/sha256/crc32/zlib/gzip |
| `pwn-re` | system/execve/popen/gets/strcpy/sprintf/mprotect/ptrace/seccomp/canary/`/bin/sh` |
| `packer` | `UPX!`/pyinstaller/nuitka/packed/obfuscat/vmprotect/themida |
| `base64-like` | `^[A-Za-z0-9+/]{24,}={0,2}$` 且 `len%4 != 1` |
| `hex-like` | `^(0x)?[0-9a-fA-F]{24,}$` 且去前缀后偶数长 |

**启发式下一步** `triageHints`（`binary.go:622-664`）：按 file 类型（ELF/Mach-O/PE/archive/image）+ **entropy ≥ 7.4** 触发"疑似压缩/加密/加壳" + **printable ≥ 0.75** 触发"grep flag/endpoint"，各给一条。

### 3.2 `/entropy` → `entropy_scan`（`binary.go:134-208`）

- 采样：前 `clamp(maxBytes, 1KiB, 32MiB)`，默认 **4 MiB**。
- 窗口：`clamp(window, 32, max(32,len))`，**默认 1024 字节**。
- 步长：`clamp(step, 1, window)`，schema 默认 512，代码 fallback 是 `window/2`（`binary.go:164`）——两者在默认窗口下一致。
- 计算：`entropyWindows`（`binary.go:671-687`）滑窗，每窗做 256 桶直方图的 Shannon（`binary.go:476-493`），单位 bits/byte（上限 8.0）。
- **补尾窗**：若最后一窗未对齐到 `len-window`，额外补一个（`binary.go:682-685`），避免尾部高熵区被步长跳过。
- 输出：全局 min/avg/max + **熵最高的 top N（默认 12，上限 50）** 窗口，每条给 `0x%08x  熵值  前16字节hex  ascii`。

### 3.3 `/carve` → `carve_artifacts`（`binary.go:329-396`）

**13 个魔数签名**（`binary.go:793-811`），全文件 `bytes.Index` 逐个扫，按 offset 排序：

| 类型 | 签名 | 落盘扩展名 |
|---|---|---|
| ELF | `7f 45 4c 46` | `.elf` |
| PE/MZ | `MZ` | `.exe` |
| DEX | `dex\n` | `.dex` |
| ZIP/APK/JAR | `50 4b 03 04` | `.zip` |
| PNG | `89 50 4e 47 0d 0a 1a 0a` | `.png` |
| JPEG | `ff d8 ff` | `.jpg` |
| GIF | `GIF8` | `.gif` |
| PDF | `%PDF-` | `.pdf` |
| gzip | `1f 8b 08` | `.gz` |
| SQLite | `SQLite format 3` | `.sqlite` |
| Mach-O 64 LE | `cf fa ed fe` | `.macho` |
| Mach-O 64 BE | `fe ed fa cf` | `.macho` |
| WASM | `00 61 73 6d` | `.wasm` |

`extract=true` 时切片规则：**第 i 个命中切到第 i+1 个命中的 offset**（末尾切到文件尾），写成 `NN_0xADDR.ext`（`binary.go:366-376`）。写盘前先 `security.ValidateWriteAllowed`，且路径经 `util.ResolveInside` 限制在工作区内。上限 `clamp(maxArtifacts, 1, 200)`，默认 50。

### 3.4 `/decode` → `ctf_decode`（`decode.go:21-157`, `160-336`）

8 个模式：`auto base64 base64url hex url rot13 xor xor_bruteforce`（`decode.go:19`）。

| 模式 | 实现要点 |
|---|---|
| `base64` | 去空白，`^[A-Za-z0-9+/]*={0,2}$` 校验，`len%4==1` 直接拒，自动补 `=` |
| `base64url` | `^[A-Za-z0-9_-]*={0,2}$`，`-`→`+`、`_`→`/` 后同上 |
| `hex` | 剥 `\x` 转义、剥 `0x`、剥 `[\s:_-]`，要求偶数长纯 hex |
| `url` | `url.QueryUnescape`，且结果需 ≠ 输入才算候选 |
| `rot13` | 只映射 A-Za-z |
| `xor` | key 支持 4 种写法：`0xNN` / 十进制 0-255 / `hex:...` / 原文（`decode.go:222-244`） |
| `xor_bruteforce` | **穷举 256 个单字节 key**，按分数排序取 top 8（`decode.go:264-279`） |

`auto` 的顺序（`decode.go:112-122`）：base64 → base64url → hex → url → rot13 → **单字节 XOR top 3 且分数 ≥ 1.4**。

**打分函数** `scoreBytes`（`decode.go:281-308`）——这是"廉价路"的核心巧思：
```
score = printableRatio
      + 1.0  若匹配 \b(flag|ctf|password|secret|token)\b
      + 1.2  若匹配 [a-z]{3,}\{[^}]{2,}\}      ← flag 花括号形状
      + 0.5  若匹配 https?://
      + 0.3  若全部可打印
```
候选去重（字节相等即跳），按分数降序输出。输出渲染：可打印比 ≥ 0.75 直接出文本，否则出 32 字符一行的 hex + ascii（`decode.go:310-336`）。

### 3.5 `/mitigations` → `binary_mitigations`（`binary.go:210-276`）

不依赖 checksec，而是**并联 4 个外部命令再正则打分**：`file -b`、`collectSymbols`（nm -an / readelf -Ws / objdump -T / otool -Iv 全试，`binary.go:689-706`）、`readelf -h -l -d -s`、`otool -hv -l -Iv`。

| 结论字段 | 判据 |
|---|---|
| `stripped` | `file` 输出含 `stripped` / `not stripped` |
| `PIE` | readelf 有 `\bDYN\b` 或 file 含 PIE 或 otool 含 `MH_PIE` |
| `NX` | `GNU_STACK.*RWE` → 否；仅 `GNU_STACK` → likely yes |
| `canary` | 合并文本含 `__stack_chk_fail\|__stack_chk_guard` |
| `RELRO` | `BIND_NOW` → full/strong；仅 `GNU_RELRO` → partial |
| dangerous imports | 18 个符号词表全词匹配：gets/strcpy/strcat/sprintf/vsprintf/scanf/sscanf/printf/system/popen/execve/mprotect/mmap/read/recv/memcpy/strncpy（`binary.go:708-726`） |

输出结尾固定提示 "Treat unknown as a prompt for deeper analysis, not as absence."（`binary.go:270`）——**明确把"没证据"和"没有"分开**。

### 3.6 `/apk` → `apk_inspect`（`binary.go:398-459`）

条目枚举三级降级（`binary.go:839-861`）：`unzip -Z -1` → `zipinfo -1` → **进程内读 ZIP 中央目录** `zipEntriesNative`。

- DEX：`(^|/)classes.*\.dex$`；native libs：`^lib/.*\.so$`；assets：`^assets/`（截 50 条）。
- **7 类加壳检测**（`binary.go:863-884`）：360 jiagu(`libjiagu|qihoo|360`)、腾讯乐固(`libshell|libtup|libexecmain|tencent`)、Bangcle(`libsecexe|libsecmain|libdexhelper`)、爱加密(`ijiami|libexec\.so`)、SecNeo、网易易盾(`libnesec|netease|yidun`)、DexGuard/ProGuard。
- **8 类框架识别**（`binary.go:886-908`）：React Native、Flutter、Unity、Cordova、Xamarin、Cocos2d、UniApp、微信小程序(`.wxapkg`)。

### 3.7 `/retool` → `reverse_toolkit`（`retool.go:25-171`）

**21 个工具族**（`retool.go:83-123`）：`inventory, radare2, rizin, jadx, apktool, binwalk, yara, ghidra, gdb, lldb, objdump, readelf, nm, apkid, aapt, frida, burp, mitmproxy, angr, unicorn, unidbg`。
**17 个探针族**（`retool.go:25-43`）用于 `inventory`，检 CLI 二进制 + Python 模块（angr 检 `angr/claripy/cle/pyvex`；python-re-libs 检 `unicorn/capstone/keystone/lief/angr/androguard`）。
r2/rizin 动作固定为 `info/sections/symbols/imports/strings/functions/disasm`（`retool.go:252-297`）——不是任意命令注入，是**白名单动作**。
`angr` / `unicorn` / `unidbg` 不执行，只**产出 harness 模板**（`retool.go:120-123`）。
超时被会话策略双重收紧（`retool.go:879-885`）。

---

## 4. Skills（33 个）

加载器：`internal/skills/skills.go`。目录约定 `skills/<name>/SKILL.md`，并有 `//go:embed embedded/skills` 的内置副本（`internal/assets/assets.go:17`）。

### 4.1 加载与"渐进披露" [A]

```go
// skills.go:31-53
func loadFrom(dir string, embedded map[string]string) []Skill {
	byName := map[string]Skill{}
	for name, body := range embedded { ... }        // 先铺内置
	if dir != "" {
		for _, entry := range entries {              // 磁盘同名覆盖内置
			data, err := os.ReadFile(filepath.Join(dir, entry.Name(), "SKILL.md"))
			skill := parse(entry.Name(), skillPath, string(data))
			byName[strings.ToLower(skill.Name)] = skill
		}
	}
	...
}
```

**渐进披露发生在"上下文"层而非"IO"层**：`Load()` 把每个 SKILL.md 整份读进内存（`Skill.Body`），但注入系统提示的只有 **name + description + tags** 的一行目录：

```go
// skills.go:109-131
func SystemPrompt(list []Skill) string {
	for _, skill := range list {
		catalog = append(catalog, fmt.Sprintf("- %s: %s%s", skill.Name, skill.Description, tags))
	}
	return strings.Join([]string{
		"## Built-in 0xAF-Re Skills", ...
		"Ask for `read_skill` when you need full instructions; use `list_skills` to inspect the catalog.",
		...
	}, "\n")
}
```

正文只有在模型主动调 `read_skill`（`meta.go:526-538`，`util.Clip(skill.Body, tc.Policy.MaxReadBytes)`）或操作员 `/skill <name>` 时才进上下文。`/skill <name> <task>` 走 `TurnPrompt`，正文**硬截断 32000 字符**（`skills.go:134-145`）。→ **是渐进披露 [A]**。

容错：`os.ReadFile` 失败 `continue`，注释 "Missing or unreadable skills are skipped rather than fatal"（`skills.go:25-26`）。
查找 `Find` 同时按 **name 和 tag** 匹配（`skills.go:82-95`）。

### 4.2 Frontmatter 字段 [A]

解析器 `parseFrontmatter`（`skills.go:153-170`）：只认文件以 `---\n` 开头、找下一个 `\n---`，行内正则 `^([A-Za-z0-9_-]+):\s*(.*)$`，值去引号。**没有 YAML 解析器，是极简手写的**。

| 字段 | 出现次数/33 | 缺省行为 |
|---|---|---|
| `name` | 33 | 缺省用目录名（`skills.go:64-67`） |
| `description` | 33 | 缺省用首个 `# ` 标题，再缺省用固定串（`skills.go:68-74`） |
| `tags` | 9 | 缺省用目录名（`skills.go:75-78`），按 `[,\s]+` 切分 |

### 4.3 33 个 skill 分类

| 类别 | skill（行数） |
|---|---|
| **Android / APK**（6） | analyze-apk(265)、analyze-so(293)、apk-so-analyzer(294)、android-apk-frida(41)、jadx(197)、unidbg(308) |
| **Frida / 动态插桩**（2） | frida-hook-workflow(573)、android-apk-frida |
| **静态逆向 / 反汇编**（5） | radare2-reverse(733)、ghidra(670)、gdb(706)、capstone-disassembler(433)、keystone-assembler(402) |
| **模拟执行**（3） | qemu-emulator(441)、qiling-emulator(607)、unicorn-emulator(318 + `scripts/`) |
| **反混淆 / 脱壳**（5） | deobfuscate(286)、ollvm-deobfuscation(583)、so-string-deobfuscation(428)、vmp-restore(604)、jsvmp-analysis(620) |
| **Web / JS / WASM**（4） | browser-hook(575)、web-crypto-analyzer(435)、wasm-reverser(424)、web-wasm-crypto(48) |
| **密码学 / 签名**（3） | crypto-identification(647)、analyze-sign(750)、api-signature-crack(475) |
| **CTF / PWN**（2） | ctf-first-pass(43)、native-pwn-re(46) |
| **补丁 / 抓包**（2） | binary-patching(510)、proxy-capture(37) |
| **元流程**（2） | re-planner(331)、re-writeup(947) |

**观察**：体量两极——`re-writeup` 947 行 vs `proxy-capture` 37 行。短的（37-48 行：ctf-first-pass / native-pwn-re / android-apk-frida / proxy-capture / web-wasm-crypto，共 5 个）恰好是**带 `tags` 字段的一批**，看得出是本项目原生写的"路由卡片"；长的多为移植自通用 skill 生态的完整手册。[C]
只有 2 个 skill 带附属脚本：`analyze-so/analyze_so.sh`、`apk-so-analyzer/analyze_apk_so.sh`；`unicorn-emulator/scripts/` 是目录。[A]

---

## 5. 知识库

三块：`internal/knowledge/`（302 + 426 行）、`knowledge/`（**只有一个 README.md，索引不入库**）、`cmd/import-knowledge/`（247 行）。

### 5.1 存储 [A]

单个 JSON 文件 `knowledge/reverse-index.json`（`internal/knowledge/knowledge.go:34` → `assets.KnowledgeIndexPath()`）。每次 `Search`/`ReadEntry` **都重新 `os.ReadFile` + `json.Unmarshal` 整个索引**（`knowledge.go:36-46, 61, 124`）——无缓存、无数据库、无向量库。[A]

条目结构（`knowledge.go:17-32`）：
```go
type Entry struct { ID, Title, Path, Source, Kind string; Tags []string; Summary, Preview string }
type Index struct { GeneratedAt string; SourceRoots []string; Entries []Entry }
```

### 5.2 索引构建 `cmd/import-knowledge` [A]

- 默认根目录：`~/frida/reverse-engineering{,_}/android_reversing/docs`、`web_reversing/docs`、`README.md`、`QUICK_START.md`（`main.go:19-32`）。可传参覆盖。
- 只收 markdown，跳过 `.git/.claude/.agents/node_modules/venv/__pycache__/output/public/site`（`main.go:34-37`）。
- 每篇产出：`ID`=路径 slug、`Title`=首标题或文件名、`Tags`=`tagsFor(file, text)`、`Summary`=`summarize(text)`、`Preview`=去 markdown 后**前 2400 字符**（`main.go:113-141`）。
- 输出 `indexed N documents -> path`。

### 5.3 检索：**纯关键词加权计分，无 embedding、无 BM25** [A]

```go
// knowledge.go:97-121
func scoreEntry(entry Entry, needles []string) int {
	score := 0
	for _, term := range needles {
		if strings.Contains(title, term)    { score += 8 }
		if strings.Contains(tags, term)     { score += 6 }
		if strings.Contains(pathText, term) { score += 3 }
		if strings.Contains(summary, term)  { score += 1 }   // summary + preview
	}
	return score
}
```
- 查询切词：`[^\p{L}\p{N}_]+` 切分并小写（`knowledge.go:48-58`）。
- 排序：分数降序，同分按 Title 字典序（稳定排序）。limit 钳制在 `[1, 50]`。
- **无 IDF、无长度归一、无词干、无同义词**——这是它和 BM25 的实质差别。[A]
- 结论：**关键词加权 contains 检索**，不是向量检索也不是 BM25。[A]

### 5.4 打包进上下文 `Pack`（`knowledge.go:180-220`）[A]

| 参数 | 默认 | 含义 |
|---|---|---|
| `MaxBytes` | 40000 | 整个上下文块硬上限 |
| `FullTextCount` | 3 | **只有前 3 条内联全文**，其余只给 id/title/tags/summary |
| `MaxEntryBytes` | 12000 | 每条内联正文上限 |

**关键设计**（`knowledge.go:176-179` 注释）：某条超预算被跳过后**继续打包后面的条目**，"one oversized body must not cost the model the cheap metadata of every hit behind it"。被跳过的进 `Truncated`，UI 会提示"另有 N 条命中因上下文预算被略去"。

每条用 `<<< ENTRY [id] >>> ... <<< END [id] >>>` 定界并盖 id 戳（`knowledge.go:224-241`）。

### 5.5 合成答案的强约束 [A]

`knowledge.SystemPrompt`（`knowledge.go:243-272`）强制**四段固定结构**，且必须中文标记：
```
### 结论  / ### 步骤  / ### 坑  / ### 出处
```
硬规则：`出处` 只能写供给条目里字面出现过的 id，**不许写路径、URL、标题**；`坑` 无内容写 `- 无`；不许补充条目外的工具/参数/版本。

解析器 `ParseAnswer`（`answer.go:63-103`）+ `resolveCitations`（`answer.go:203`）会**检出模型编造的 id**，记为 `InventedCitations`，并写进会话事件（`commands.go:747-752`）：
```go
_ = state.Session.AppendEvent(map[string]any{
	"type": "knowledge", "query": query,
	"matched": ..., "used": ..., "citations": ..., "inventedCitations": answer.InventedCitations, "parsed": answer.Parsed,
})
```
→ **幻觉引用是被显式度量并留痕的**，不是靠提示词祈祷。[A]

另一处关键：`/know` 的合成**跑在全新 provider 实例上**（`commands.go:698-720`），注释原话："the configured CLI providers resume one long-lived native session, and a side lookup must not be spliced into the conversation the operator is actually having."[A]

模型侧工具 `knowledge_search` 默认返回 `FormatDigest`（`answer.go:307-392`）——"证据 + 契约"，而非原始命中；`raw:true` 才退回旧的 `FormatMatches`（`meta.go:558-568`）。

---

## 6. UI / 实时视图（`internal/ui`，11 个文件约 4300 行）

| 文件 | 行数 | 职责 |
|---|---|---|
| `hud.go` | 971 | HUD 模型、chips、plan 行、sparkline、布局与"降级丢弃" |
| `flow.go` | 645 | 实时数据流图（ASCII canvas） |
| `theme.go` | 607 | 4 套配色 |
| `ui.go` | 550 | 通用渲染（notice/error/reply/表格） |
| `live.go` | 540 | `LivePane` 实时面板与定时器 |
| `help.go` | 411 | 命令表 / 补全 / 调色板 |
| `splash.go` | 369 | 启动探针画面 |
| `markdown.go` | 327 | 终端 markdown |
| `trace.go` | 296 | 逐行 trace |
| `canvas.go` / `plan.go` / `welcome.go` | — | 画布、任务列表、欢迎页 |

### 6.1 一个回合中实时渲染什么 [A]

`HudModel`（`hud.go:118-150`）字段即答案清单：

| 字段 | 渲染成什么 |
|---|---|
| `Label` / `Route *HudRoute` | 路由 chip：planner → executor，高亮当前作答方（`hud.go:92-97, 497`） |
| `Phase` | 阶段文字（thinking / writing / interrupting …） |
| `Frame` + `ElapsedMs` + `Now` | 转轮 + 计时；`Now` 独立传入以便**步骤计时同帧一致** |
| `Stats HudStats` (= `types.TokenUsage`) | input/output/thinking/cacheRead/cacheWrite/costUsd（`types.go:347-352`），`counterChips`(`hud.go:620`)、`costChip`(`hud.go:525`) |
| `Spark []float64` | **输出 token 增量的火花线**，固定节拍采样（`live.go:429-433`，`Sparkline` `hud.go:439`） |
| `Plan *types.PlanSnapshot` + `PlanDisplay` | 任务列表行，含**每步耗时**（`PlanRows` `hud.go:260`、`stepRow` `hud.go:334`、`elapsedLabel` `hud.go:359`、`spanOf` `hud.go:374`）；进度 chip `ProgressChip`(`hud.go:474`) |
| `QueueCount` / `QueueDraft` | 队列行 + **正在敲的草稿**（`queueRow` `hud.go:720`） |
| `Thinking` + `ThinkingWindow` + `ThinkDisplay` | 流式推理尾巴（`thinkingRows` `hud.go:768`） |
| `MaxRows` | 硬行数上限，HUD **主动丢内容**去满足它 |

`ComposePane`（`live.go:118`）把 `FlowState` 与 `HudModel` 合成一屏。

### 6.2 折叠语义的巧思 [A]

`hud.go:110-117` 注释：
> ThinkDisplayMode controls how much of the streamed reasoning tail the HUD shows. **Collapsed hides the text but not the `think` token counter**, so a folded HUD still says that reasoning is happening — only the words go away.

`hud.go:54-57`：展开 think 还会把它**挪到丢弃顺序的最后**——"content you asked for should not be the first thing dropped"。

### 6.3 数据流图 `/flow` [A]

`VizMode` 四态：`full`(图+trace) / `flow`(只图) / `trace`(只行) / `off`（`commands.go:177-178`；`flow.go:27-38`）。落盘到 UI 偏好。
`FlowModel` 消费 `core.LoopEvent`（`flow.go:180` `Apply`），有 `Begin/SeedPlan/End/Tick`，用 `Canvas` 画线（`drawWire` `flow.go:619`），带 plan 徽章（`paintPlanBadge` `flow.go:528`）。
`trace.go:43` `TraceEvent` 逐事件出行，含 `durationBar`（`trace.go:251`）耗时条与 `summarizeArgs`（`trace.go:270`）参数摘要。

### 6.4 中途操舵怎么暴露 [A]

三条通路：

1. **裸文本入队**——回合中敲的非斜杠内容自动 `queue add`，回执 `queued #N for the next turn`（`repl.go:708-714`）。HUD 上有 `QueueDraft`（正在敲的字）和 `QueueCount`。
2. **5 个 mid-turn 命令**（§1.6），其中 `/queue edit <id> <task>` 允许**改已排队但未执行的任务**（`commands.go:478-487`）。`/queue run` 在回合中只回 "queue will continue after the current turn"（`commands.go:506-511`）——**不打断当前回合**。
3. **中断**：`repl.go:368-378` `interruptedAt atomic.Int64` + `pane.SetPhase("interrupting")`；`repl.go:445` 提示 "interrupted — partial work kept in the transcript"——**部分成果保留**。

`/queue` 完整动作集：`list / add / edit <id> <task> / cancel <id|all> / rm / drop / clear / run`（`commands.go:469-514`）。→ **有 `/queue edit`，确认存在 [A]**。

### 6.5 审批提示的屏幕交接 [A]

`createApprover`（`repl.go:745-775`）：暂停输入 → `pane.Pause()` → 打印请求 → 读一行 → `pane.Resume()`。`/prompt edit` 与 `/r2` 用同一套"把终端让给全屏子进程"的手法（`inspect.go:6-10` 注释）。

---

## 7. MCP

`internal/mcp/`：`client.go`(370) + `tools.go`(139)。

| 项 | 结论 |
|---|---|
| 角色 | **只有客户端（consumer），不是 server** [A] `client.go:1-5` |
| 传输 | **stdio**，JSON-RPC 2.0 over newline-delimited JSON [A] `client.go:1-4` |
| 协议版本 | `2024-11-05`（硬编码 `client.go:21`） |
| clientInfo | `{"name":"0xaf-re-agent","version":"0.1.5"}`（`client.go:23`） |
| 握手 | `initialize`（空 capabilities）→ `notifications/initialized` → `tools/list` [A] `client.go:99-118` |
| 支持的能力 | **仅 tools**。无 resources / prompts / sampling / roots [A]（全文件无相关方法） |
| 调用 | `CallTool(name, args, ctx)`，返回内容块 |
| 并发启动 | `ConnectAll` 用 goroutine + WaitGroup 并行连接，按名字排序保证顺序稳定 `tools.go:56-77` |
| 失败处理 | **连不上不致命**，记 `Connection.Error`，注释 "an IDA plugin that is not running should not stop a session" `tools.go:53-55` |
| 命名 | `mcp__<server>__<tool>`，超 64 字符时**先砍 server 半边**（"the tool name is what the model reasons about"）`tools.go:16-51` |
| 风险层 | **一律 `RiskWrite`** `tools.go:103-105` |
| 大输出 | 走 `tools.SpillIfLarge` 溢写到工件文件 `tools.go:112-115` |
| 图片 | MCP 返回的 `image` 内容块被透传 `tools.go:116-120` |
| 环境 | `auth.FilteredEnv(nil)` + 配置 env，**不继承宿主全部环境** `client.go:70-74` |
| 配置项 | `command / args / env / cwd / timeoutMs / disabled / tools` `types.go:113-121` |
| 示例配置 | `ida-pro-mcp`（`python3 -m ida_pro_mcp.server`，`timeoutMs:120000`，**默认 `disabled:true`**）`config.example.json:103-110` |

关闭时的细节 [A]：`client.go:61-64` 注释——`pumped chan struct{}` 保证 stdout reader 见到 EOF 之前不跑 `cmd.Wait()`，否则"服务器最后一帧会被从 scanner 底下抽走"。

---

## 8. 配置全项

配置加载：`config.Load`（`config.go:117-140`），按序找第一个存在的：`--config 指定` → `$CWD/agent.config.json` → `~/.0xaf-re-agent/config.json`，**覆盖在内置默认之上**。

### 8.1 顶层选项（`types.go:99-110`，默认见 `config.go:18-25`）

| 键 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `name` | string | `0xAF-Re` | 显示名 |
| `plannerProvider` | string | `codex` | 规划侧 |
| `executorProvider` | string | `claude` | 执行侧 |
| `researcherProvider` | string | `codex` | 研究侧；空则回落 planner |
| `knowledgeProvider` | string | *(空)* | `/know` 合成用；空则用 executor（`commands.go:703-706`） |
| `defaultRole` | enum | `auto` | planner/executor/researcher/auto |
| `maxTurns` | number | `8` | 单轮最大工具循环数 |
| `providers` | map | 9 个预设 | 见下 |
| `mcpServers` | map | *(示例含 ida，disabled)* | MCP 配置 |

### 8.2 provider 选项（`types.go:66-96`）

| 键 | 说明 |
|---|---|
| `type` | `cli-tmux` / `openai-responses` / `openai-chat` / `anthropic` / `mock` |
| `label` / `model` | 显示名 / 模型 id |
| `baseUrl` | API 基址 |
| `apiKey` / `apiKeyEnv[]` | 直填 or 环境变量名列表（按序取第一个非空） |
| `authScheme` | `api-key` \| `bearer` |
| `cliCommand` / `cliArgs[]` | CLI 类；`{output}` `{prompt}` 为占位符 |
| `cliTimeoutMs` | 默认预设里 600000（10 分钟） |
| `cliPromptMaxChars` | grok-cli 预设 80000 |
| `cliFallbackDirect` | `*bool`，tmux 失败是否直连 |
| `cliUnsetEnv[]` | **启动子 CLI 前清掉的环境变量**（防止 API key 抢占 OAuth 会话） |
| `cliResumeSession` | 是否复用长驻原生会话（claude/grok-cli 预设为 true） |
| `cliSessionIdArg` / `cliResumeArg` | 会话续接参数名 |
| `cliStream` | `*bool` |
| `maxTokens` | API 类默认 8192 |
| `contextBudgetTokens` | 覆盖 `DefaultContextBudgetTokens = 48_000`（`agentloop.go:18`） |
| `reasoningEffort` | minimal…max |
| `headers` | 额外 HTTP 头 |
| `mockScript[]` | mock provider 脚本 |

### 8.3 9 个内置 provider 预设 [A]（`config.go:26-111`）

| 名字 | type | model | 要点 |
|---|---|---|---|
| `codex` | cli-tmux | codex-cli | `--sandbox read-only --ask-for-approval never`；**默认里带 `--json`，example 里不带** |
| `claude` | cli-tmux | claude-code-cli | 默认 `--output-format stream-json --include-partial-messages`（example 里是 `text`）；`cliResumeSession:true` |
| `codex-api` | openai-responses | gpt-5.3-codex | effort=high |
| `claude-api` | anthropic | claude-opus-4-8 | maxTokens 8192 |
| `grok` | openai-responses | grok-4.5 | api.x.ai |
| `grok-cli` | cli-tmux | grok-build-cli | `--disable-web-search --no-memory`，promptMax 80000 |
| `deepseek` | openai-chat | deepseek-chat | — |
| `glm` | openai-chat | glm-4.6 | `ZAI_API_KEY`/`GLM_API_KEY` |
| `mock` | mock | mock-reasoner | 测试用 |

⚠️ **`config.example.json` 与 `config.Defaults()` 不完全一致**（codex 的 `--json`、claude 的 `stream-json` vs `text`、`cliResumeSession`）——example 是保守版。[A]

### 8.4 命令行参数（`internal/app/args.go:86-222`，29 个）

`--config --workspace/--cwd --session-dir --role --agent/--provider --planner --executor --researcher --prompt --theme --workflow --model --effort --print/-p --smoke --welcome --version --write --allow-network --allow-sensitive --continue/-c --resume --sessions --flow --yolo --approval --max-output --help/-h`

安全相关三个开关直接改 `ExecutionPolicy`：`--write`(AllowWrites) / `--allow-network` / `--allow-sensitive`；`--yolo` 与 `--approval <mode>` 设审批模式；`--max-output` 覆盖 `MaxToolOutputChars`（`app.go:139`）。

### 8.5 UI 偏好持久化 [A]

`config.SaveUIPrefs(config.UIPrefs{Theme, Flow})`——只有 `/theme` 和 `/flow` 跨重启保留（`commands.go:53, 185`；`config.go:1-2` 注释）。`/tasks` `/think` `/workflow` `/role` 等**只活在本会话**。

---

## 9. 值得上幻灯片的五个细节

1. **零 token 廉价路的规模**：52 个斜杠命令里约 49 个不产生任何 token，16 个"direct tools"直接绕过 agent loop 调工具函数（`commands.go:764-775`）。逆向工作 80% 的动作根本不该问模型。
2. **XOR 爆破的打分函数**（`decode.go:281-308`）：`printableRatio + flag词1.0 + 花括号形状1.2 + http0.5 + 全可打印0.3`——用 5 行代码把 256 个候选排出正确答案。
3. **skills 的渐进披露不在 IO 层而在上下文层**：全部读进内存，但系统提示只放 `name+description+tags` 一行目录，正文靠 `read_skill` 按需拉（`skills.go:109-131`）。33 个 skill 共 ~13000 行，进上下文的目录只有 33 行。
4. **知识检索是关键词加权 contains，不是向量也不是 BM25**（`knowledge.go:97-121`，权重 8/6/3/1），但它给答案套了四段中文契约并**把模型编造的引用 id 记进会话日志**（`answer.go:203`，`commands.go:750`）。
5. **安全疑虑压过 allow 覆盖**（`approval.go:101-106`）："操作员允许 `run_command` 不等于允许 `rm -rf /`"；且审批提示的回车默认是"拒绝"。

---

## 附：待核项

- `knowledge/` 目录下只有 `README.md`，`reverse-index.json` 未入库（`.gitignore` 应有条目）——所以**开箱即用的知识条目数 = 0，需先跑 `import-knowledge`**。[A]
- `internal/tools/zip.go` / `output.go` / `process.go` 未逐行读；`process.go`(201 行) 无工具定义（grep 无 `Name:`），推断为 `Run()` 子进程执行辅助。[C]
- `internal/ui/theme.go` 的 4 个主题具体色值未展开。[未查]
