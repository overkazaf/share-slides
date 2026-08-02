# R05 — 0xAF-Re 能干什么：具体样例与端到端案例

调查对象：`/Users/overkazaf/playground/research/re-agent`（Go 实现，二进制名 `0xaf`）
只读调查，未执行任何 0xaf 二进制、未跑 demo、未联网。

**证据标记约定**

| 标记 | 含义 |
| --- | --- |
| `[A]` | 直接从仓库文件读出的内容（代码 / 测试断言 / 已录制的 SVG 终端帧），可 file:line 复核 |
| `[B]` | 文档声称，仓库里没有可复现的 harness 支撑 |
| `[C]` | 我基于 skill 文本 + 工具清单重构的**示意性**流程，**不是**已录制的真实运行 |

---

## 0. 一页速查：这个 agent 的"能力面"长什么样

工具注册表共 **24 个工具**，由单元测试钉死（改一个就红）：

```
list_files  read_file  write_file  grep  run_command  file_info
strings  hexdump  hash_file  extract_symbols  ctf_triage  ctf_decode
entropy_scan  binary_mitigations  find_bytes  carve_artifacts  reverse_toolkit
apk_inspect  frida_hook_template  list_skills  read_skill  knowledge_search
knowledge_read  update_plan
```

`[A]` `internal/tools/tools_test.go:41-56`（`TestRegistryIsComplete`，长度和名字都断言）
`[A]` 同一份清单出现在真实录屏 `docs/casts/quickstart.svg`（`--smoke` 输出）里，只是当时是 24 个。
`[A]` `docs/shots/turn.svg` 里 HUD 显示 `tools 23`，`docs/casts/quickstart.svg` 里显示 `tools 24 · execute 2 · read 21 · write 1` —— 两次录制版本不同（v0.1.2 vs v0.1.1），做 slide 时以测试里的 24 为准。

**风险分级**（`/tools` 真实输出，`[A]` `docs/shots/tools.svg`）：`read` 21 个、`exec` 1-2 个（`run_command`）、`write` 1 个（`write_file`，非 `--write` 启动时禁用）。

Skills 共 **33 个目录**（`[A]` `find skills -type f` → 42 个文件 / 33 个 `SKILL.md`，另有 9 个附带脚本）。

---

## 1. `demos/` —— 仓库自带的两个离线工作区

### 1.1 目录清单 `[A]`

```
demos/README.md
demos/welcome/README.md
demos/welcome/chall.js            # 20 行 Node.js 玩具校验器
demos/reverse-lab/README.md
demos/reverse-lab/artifact.txt    # 295 bytes ASCII
demos/reverse-lab/carrier.bin     # 121 bytes 二进制
```

**⚠️ 两个可以直接上 slide 的"文档腐化"证据**（讲"文档会漂移"这一点时很好用）：

1. `demos/README.md:19-22` 和 `demos/welcome/README.md:17-43` 里的命令全部是 `bun src/cli.ts --welcome`
   —— 这是**上一代 TypeScript 实现**留下的，当前仓库是 Go，二进制是 `./bin/0xaf`。`[A]`
2. `demos/welcome/README.md:10-11` 声称有 `artifacts/session.log` 和 `artifacts/operator-notes.txt`，
   **这两个文件在仓库里不存在**。`[A]`（`find demos -type f` 只有 6 个文件）

### 1.2 `demos/welcome/chall.js` —— 全部内容与解 `[A]`

```javascript
// demos/welcome/chall.js:3-5
const key = 0x2a;
const encoded = [26, 82, 75, 76, 81, 93, 75, 88, 71, 95, 90, 117, 78, 79, 73, 65, 87];
const expected = encoded.map(value => String.fromCharCode(value ^ key)).join("");
// :14-20  provided === expected → "accepted" exit 0；否则 "rejected" exit 1
```

逐字节 XOR 0x2a 得到 → **`0xaf{warmup_deck}`**（我离线用 python 复核过，与 `README.md:308` 一致）`[A]`

### 1.3 `demos/reverse-lab/` —— 两个 artifact 的真实内容 `[A]`

`artifact.txt`（295 bytes，被故意撒了五类"信号词"，专门用来触发 `ctf_triage` 的分类器）：

```text
CTF demo artifact
Hints:
- base64 candidate: ZmxhZ3tkZW1vX3JldmVyc2VfbGFiX2ZsYWd9
- suspicious endpoint: https://ctf.example.invalid/api/sign
- crypto words: AES CBC HMAC SHA256 token secret
- pwn words: system /bin/sh printf strcpy
The useful answer is encoded, not hidden by network access.
```

base64 解出 → **`flag{demo_reverse_lab_flag}`**（离线复核）`[A]`

`carrier.bin`（121 bytes，`file(1)` 报 `data`），hexdump 布局 `[A]`：

| 偏移 | 内容 | 用途 |
| --- | --- | --- |
| 0x00 | `carrier-prefix\n` | 噪声前缀，让 magic 判不出类型 |
| 0x10 | `noise noise noise\n` | 噪声 |
| 0x21 | `%PDF-1.7 … %%EOF` | **内嵌 PDF 签名**，喂给 `/carve` 和 `/findbytes` |
| 0x59 | `more-noise\n` | 噪声 |
| 0x60 | `PK\x03\x04demo zip marker\n` | **内嵌 ZIP local header**，第二个 carve 目标 |
| 0x77 | `final\n` | 结尾 |

`demos/reverse-lab/README.md:5-14` 给出的官方 7 条命令 `[A]`：

```text
/skills
/skill ctf-first-pass scan the demo artifacts
/scan artifact.txt
/decode base64 ZmxhZ3tkZW1vX3JldmVyc2VfbGFiX2ZsYWd9
/findbytes carrier.bin %PDF-
/carve carrier.bin
/entropy carrier.bin
/know frida ssl pinning
```

> 这 7 条是整个 slide 里**性价比最高的一屏**：无网络、无设备、无 API key、无模型，全部本地工具直出。

---

## 2. 旗舰案例：README "Worked Case: solve a challenge end to end"

位置：`README.md:232-339` / `README.zh-CN.md:202-300`。
README 自称："全部来自一次针对 `demos/welcome` 的真实运行……plan 文本、命令、耗时和答案都是从 session 记录里抄出来的" `[B]`（transcript 本身不在仓库里，无法复核，因此标 B）。

### 案例 A —— 完全不用模型（零 token）`[A: 文本逐字来自 README.md:243-257`）

```bash
0xaf --workspace ./demos/welcome
```

```text
/read chall.js
# const key = 0x2a;
# const encoded = [26, 82, 75, 76, 81, 93, 75, 88, 71, 95, 90, 117, 78, 79, 73, 65, 87];

!node -e 'const k=0x2a,e=[26,82,75,76,81,93,75,88,71,95,90,117,78,79,73,65,87];console.log(e.map(v=>String.fromCharCode(v^k)).join(""))'
# 0xaf{warmup_deck}

!node chall.js '0xaf{warmup_deck}'
# accepted
```

要点：`!` 前缀 = 直接跑 shell（`docs/shots/shell.svg` 有真实 `!ls -la` 的录屏 `[A]`）；
`/read` = `read_file` 工具直出。整个解题过程模型未参与。

README 紧接着给出"把这套搬到真样本"的映射 `[A]` `README.md:260-263`：
`/scan` 定性 → `/hex <file> 0x20` 读头 → `/carve` 抠内嵌载荷 → `/r2 <file>` 上反汇编器。

### 案例 B —— 让 agent 自己跑完（一句话 prompt）`[B]`

输入 prompt（一句话）：

```text
Recover the expected token from chall.js, verify it by actually running the
checker, and explain how the check works.
```

**Step 1 · planner 出计划**（`codex` 承担 planner，工具调用之前先落 4 步）`README.md:282-287`：

```text
PLAN 0/4 · via codex
  1  Locate chall.js and identify its runtime/checker interface
  2  Reverse the validation logic and derive the expected token
  3  Run the checker with the recovered token and capture the result
  4  Explain the check in concise solve notes
```

**Step 2 · executor 逐条执行**（每条都是受策略约束的真实工具调用）`README.md:293-299`：

| # | 实际命令 | 这一步在干什么 |
| --- | --- | --- |
| 1 | `rg --files` | 盘点工作区有哪些文件 |
| 2 | `file chall.js` | 判定目标类型 |
| 3 | `node -v` | 确认运行时存在（不假设环境） |
| 4 | `sed -n '1,240p' chall.js` | 读校验逻辑 |
| 5 | `sha256sum chall.js && wc -c chall.js` | **钉住本次检查的确切字节** |
| 6 | `node chall.js '0xaf{warmup_deck}'` | 正例 → `accepted` · `exit=0` |
| 7 | `node chall.js 'wrong'` | **反例** → `rejected` · `exit=1` |

> 讲稿钩子：第 6、7 步是这个案例的全部说服力所在。agent 没有停在"我读源码读出来是 X"，
> 而是**正例 + 反例各跑一次**，把结论从"我读对了"降级成"我观察到了"。
> README 自己也把这句话点出来了（`README.md:302-304`）。

**Step 3 · 答案带着证据一起给出** `README.md:308-317`：

```text
Recovered token:   0xaf{warmup_deck}
Verification run:  node chall.js '0xaf{warmup_deck}'  → accepted, exit=0

How it works: chall.js:3 stores an integer array and XORs each byte with 0x2a.
Decoding that array gives 0xaf{warmup_deck}. The script then compares
process.argv[2] directly against that decoded string; exact match prints
accepted and exits 0, otherwise rejected and exit 1.

╰─ via codex · role auto · turns 1 · took 1m34s · in 162k out 2.2k think 895 cache 122k
```

**Step 4 · 跑的过程中操作员能做什么**（中途可输入）`README.md:326-331`：

| 想要 | 中途输入 |
| --- | --- |
| 展开模型推理（不只 3 行尾巴） | `/think expand` / `/think collapse` |
| 展开全部 plan 步骤（含未开始的） | `/tasks expand` |
| 不打断当前轮，排下一个问题 | `/queue add <text>` / `/queue edit <id> <text>` |
| 换掉后续会话用的模型 | `/model executor <name>` |

跑完 `/session` 打印 JSONL 路径，plan 快照 / 工具调用 / 结果 / token 计数按序落盘。

**README 自己给的复现免责声明**（诚实，值得抄进 slide）`README.md:336-339`：
> 案例 B 需要真实的 planner 和 executor。`--smoke` 和 `mock` provider 只验证线路，
> **mock 不会规划也不调工具，跑不出上面这一轮。**

---

## 3. `docs/casts/` 与 `docs/shots/` —— 已录制的真实运行（最硬的 ground truth）

### 3.1 录制方式 `[A]` `scripts/record-casts.sh:1-40`

不是手写的假终端。脚本注释原文：
> "Every cast below runs the real binary against a demo workspace with the offline `mock` provider,
> so this needs no API key, no network and no CLI login — what you see is what the tool actually prints."

三段 cast 的**确切喂入序列**（`--cols 120 --rows 40` 的 pty 录制，输出为动画 SVG）：

| 文件 | 启动命令 | `--feed` 喂入 | 参数 |
| --- | --- | --- | --- |
| `docs/casts/quickstart.svg` | `bash -i` | `./bin/0xaf --smoke\n./bin/0xaf --workspace ./demos/reverse-lab\n` | `record-casts.sh:24-27` |
| `docs/casts/scan.svg` | `./bin/0xaf --provider mock --workspace ./demos/reverse-lab` | `/scan carrier.bin\n/scan artifact.txt\n` | `:30-33` |
| `docs/casts/deck.svg` | 同上 | `/theme\n/theme matrix\n/policy\n` | `:37-40` |

### 3.2 `quickstart.svg` 真实输出 `[A]`

```
$ ./bin/0xaf --smoke
▏ 0xAF-Re mock response via mock.
▏ Received: smoke test: identify yourself and list capabilities
▏ Available tools: list_files, read_file, write_file, grep, run_command, file_info, strings, hexdump,
▏ hash_file, extract_symbols, ctf_triage, ctf_decode, entropy_scan, binary_mitigations, find_bytes,
▏ carve_artifacts, reverse_toolkit, apk_inspect, frida_hook_template, list_skills, read_skill,
▏ knowledge_search, knowledge_read, update_plan
smoke: ok
session: /mnt/data/research/0xaf-re-agent/sessions/2026-07-28T17-16-52-721Z-0xaf.jsonl
```

紧接着 `./bin/0xaf --workspace ./demos/reverse-lab` 的启动面板（ASCII banner + 四段信息）：

```
reverse ops deck · v0.1.1 · 29e7b21f7fbb-dirty
┌─SYSTEM     runtime go 1.22.5 · linux amd64 | commit 29e7b21f7fbb·dirty | tmux 3.2a
├─WORKSPACE  path …/demos/reverse-lab | contents 3 files · 0 dirs · no binaries detected
├─ROUTE      plan codex ● ready | exec claude ● ready | research codex ● ready
├─ARSENAL    tools 24 · execute 2 · read 21 · write 1
└─policy     write off · net off · sensitive off · log …-16-58-017Z-0xaf.jsonl
```

注意 ROUTE 三行的状态从 `checking…` 变成 `● ready` —— 启动时异步探测三个 provider 的凭据。`[A]`

### 3.3 `scan.svg` —— `/scan carrier.bin` 的**逐字真实输出** `[A]`

```
auto/mock ❯ /scan carrier.bin
CTF TRIAGE
path: carrier.bin
type: data
size: 121 bytes
sha256: 1a1578330c7227d0be3394982d109e4ac366034244828aeb1c762a065da8ee2d
magic.hex: 636172726965722d7072656669780a6e
magic.ascii: carrier-prefix.n
sample: 121/121 bytes
entropy: 4.868 bits/byte
printable: 98.3%
signals:
- none found in sample
next:
- Mostly printable: grep for flags, endpoints, scripts, encodings, and protocol grammar.
```

同一段 cast 里还录到了**命令面板的实时补全**：输入 `/sc` 时弹出 `/scan <path> — Fast CTF triage on an artifact or directory`；
输入 `/s` 时弹出 6 条候选（`/session /sessions /status /scan /skills /skill`）；
输入 `/scan car` 时提示 `No argument suggestions for this command`。`[A]`

### 3.4 `docs/shots/scan.svg` —— `/scan artifact.txt`（信号命中的那次）`[A]`

这是对照组，最能说明 `ctf_triage` 的分类器在干什么：

```
auto/auto ❯ /scan artifact.txt        (no model in the loop)
CTF TRIAGE
path: artifact.txt          type: ASCII text        size: 295 bytes
sha256: 3b926e1a779e76bbbe658c5e5d79f5a091b3657570d99b9f4a39db0c8ec99ba1
magic.ascii: CTF demo artifac
entropy: 5.083 bits/byte    printable: 100.0%
signals:
- crypto-codec:    - base64 candidate: ZmxhZ3tkZW1vX3JldmVyc2VfbGFiX2ZsYWd9
- url:             https://ctf.example.invalid/api/sign
- secret-keyword:  - crypto words: AES CBC HMAC SHA256 token secret
- crypto-codec:    - crypto words: AES CBC HMAC SHA256 token secret
- pwn-re:          - pwn words: system /bin/sh printf strcpy
next:
- Mostly printable: grep for flags, endpoints, scripts, encodings, and protocol grammar.
- Codec keyword found: try ctf_decode on nearby candidate strings.
- Exploit primitive hint: check mitigations and xrefs around dangerous calls.
```

**四类信号 → 三条 next**：`signals` 是分类，`next` 是**下一步实验建议**——这就是 agent 的
"我该往哪走"的输入。carrier.bin 那次 `signals: none found`，next 只有一条通用建议，对比极强。

### 3.5 `docs/shots/turn.svg` —— 一整轮的遥测流（mock provider，5 turn）`[A]`

prompt：`triage artifact.txt and decode whatever payload it carries`

```
t+ 0.001 ▏ ⇢ POST mock://mock-reasoner   model=mock-reasoner in=19 msgs=1 tools=23
t+ 0.002 ▏ ⇠ 200  out=380 think=105 cache=416k calls=1  ██████████ 1ms
t+ 0.006 ▏ ◇ plan 1/4  opened via update_plan
t+ 0.007 ▏ ↻ turn 2
t+ 0.009 ▏   ⚙ run_command  command=sleep 4; file artifact.txt; head -c 64 artifact.txt
t+ 4.025 ▏   ✓ 4.0s  $ sleep 4; file artifact.txt; head -c 64 artifact.txt
t+ 4.026 ▏ ↻ turn 3
t+ 4.030 ▏   ⚙ ctf_decode  input=ZmxhZ3tkZW1vX3JldmVyc2VfbGFiX2ZsYWd9
t+ 4.033 ▏   ✓ 3ms  CTF DECODE
t+ 4.036 ▏ ◇ plan 3/4  ✔ 定位校验函数并复现 4.0s
t+ 4.036 ▏ ◇ plan 3/4  ✔ reproduce the flag path
t+ 4.036 ▏ ◇ plan 3/4  ▸ write reproducible notes
t+ 4.072 ▏ ■ turn complete  via mock  4.1s
```

每一行都带 `t+` 相对时间戳、方向符号（`⇢` 请求 / `⇠` 响应 / `⚙` 工具开始 / `✓` 工具完成 / `◇` plan 更新 / `↻` 新一轮 / `■` 结束）。
注意 `sleep 4` 是**故意塞进去的**，为的是让 `docs/shots/live.svg` 能拍到 mid-turn 画面。

### 3.6 `docs/shots/live.svg` —— run_command 执行中的 mid-turn 帧 `[A]`

```
[you]══════▶[ctx]══════▶((mock))          3 msg  147 tok  ⋯ awaiting tools
[plan 1/4][tools]◀══•═════•═══[calls×1]    ▰▰▱▱▱▱▱ ⣾ run_command 2.1s ✓1
╭─ ⠴ 0xAF·RE ───────────────────────────────────────────╮
│ mock ▰▰▱▱▱▱▱▱ 25%                                     │
│ the checker looks like sub_401a20                     │  ← 模型推理尾行
│ ✔ triage: file/arch/packer          │ ◷ 2.3s          │
│ ⠴ 定位校验函数并复现 2.2s            │ ▸ run_command    │
│ ○ reproduce the flag path           │                 │
│ ○ write reproducible notes          │                 │
╰───────────────────────────────────────────────────────╯
```

### 3.7 `docs/shots/reply.svg` —— 同一轮结束时的归档 plan + markdown 回答 `[A]`

```
╭─ PLAN 3/4 ▰▰▰▰▰▰▱▱ 75% ────────────────────────────────╮
│ ✔ triage: file/arch/packer                             │
│ ✔ 定位校验函数并复现 4.0s                               │
│ ✔ reproduce the flag path                              │
│ ⠿ write reproducible notes                             │
╰────────────────────────────────────────────────────────╯
◆ mock · mock-reasoner
▏ Result
▏  The artifact is plain ASCII with an embedded base64 payload.
▏  ▸ decoded flag — flag{demo_reverse_lab_flag}
▏  ▸ the base64 sits at offset 0x2f, right after the candidate: label
▏  ▸ no packing: entropy is 5.08 bits/byte and the file is 100% printable
▏ ▍Next
▏  1. carve carrier.bin — it holds a %PDF- and a ZIP local header
▏  2. run entropy_scan if you want the window map
▏ ▌Nothing here needs a debugger.
╰─ via mock · role auto · turns 5 · took 4.1s · in 52k out 9.7k think 630 cache 1.7M  $3.1600
```

> 这段回答的每个数字都能和 §1.3 的文件内容对上（0x2f 偏移、5.08 熵、%PDF- 与 PK 头）。
> 唯一注意：这是 **mock provider**，回答是预置的，不代表真模型质量。

### 3.8 `docs/shots/approval.svg` —— 拒绝一次网络命令 `[A]`

```
safe mode stopping for a network command
 REVIEW run_command (exec)
│ curl -s https://ctf.example.invalid/api/sign
│ ! network command 'curl'  (--allow-network to stop asking)
│ y run once · a always this tool · n skip · d never this tool
❯ n
t+ 0.253 ▏ ✗ 0ms  Operator denied run_command: curl -s https://ctf.example.invalid/api/sign
```

`deck.svg` 里 `/policy` 的真实输出（默认策略）`[A]`：

```json
{ "allowWrites": false, "allowNetwork": false, "allowSensitive": false,
  "commandTimeoutMs": 30000, "maxReadBytes": 131072,
  "maxToolOutputChars": 24000, "approvalMode": "safe", "approvals": {} }
```

`docs/shots/shell.svg` 还录到了越界失败：`/read nope.txt` →
`stat …/demos/reverse-lab/nope.txt: no such file or directory` `[A]`

### 3.9 `docs/shots/verify.svg` —— 构建与性能 `[A/B]`

```
$ go vet ./... && go test -count=1 ./...
ok  .../internal/app 0.009s   .../internal/core 0.234s   .../internal/tools 0.029s  … (10 包全 ok)
$ ls -la bin/0xaf        # 单个静态二进制，assets 已嵌入
-rwxrwxr-x 1 dell dell 6684932  7月 28 09:42 bin/0xaf
$ time (for i in $(seq 50); do ./bin/0xaf --welcome >/dev/null; done)   # 冷启动 x50
real 0m0.375s
```

`[A]` 二进制 6.68 MB、50 次启动 0.375 s（≈7.5 ms/次）。
`[B]` ⚠️ 但 `docs/index.html:54-55` 与 `:967` 的文案写的是 "0.335 s / 6.7 ms start"，
**与它自己 SVG 里的 0.375 s 不一致**。若上 slide，用 SVG 里的 0.375 s / ~7.5 ms，或干脆说"约 7 ms 级"。

---

## 4. `docs/cards/` 与 `scripts/make-cards.py`

`[A]` `scripts/make-cards.py:1-10` 头注释：生成 `docs/cards/` 下的**竖版分享卡**，
`1080x1440`（3:4，小红书 / feed 阅读器的裁剪比例）。纯 Python 手写 SVG，
逐行输出而**不自动换行**——注释原话："a long word can never push a line past the margin —
the whole point of the deck is that it reads at thumbnail size."

11 张卡的标题（`make-cards.py` 各 `c.title([...])` 调用）`[A]`：

| # | 文件 | 标题 |
| --- | --- | --- |
| 01 | `01-cover.svg` | A reverse engineering agent that shows its… (`:179`) |
| 02 | `02-problem.svg` | An agent you cannot see is an agent you cannot trust. (`:202`) |
| 03 | `03-two-seats.svg` | Two seats, one loop. (`:222`) |
| 04 | `04-context-budget.svg` | Context is a budget, not a bin. (`:248`) |
| 05 | `05-refusal.svg` | A refusal is an answer. (`:269`) |
| 06 | `06-live-pane.svg` | Decoration must never fail a run. (`:292`) |
| 07 | `07-fast-path.svg` | **The fast path costs zero tokens.** (`:314`) |
| 08 | `08-model-says-no.svg` | When the model says no. (`:340`) |
| 09 | `09-workflow-modes.svg` | Cyber seat when you have it. (`:366`) |
| 10 | `10-live-queue.svg` | Do not wait for the turn to finish. (`:398`) |
| 11 | `11-xhs-group.svg` | Scan into the XHS discussion group. (`:426`) |

`docs/cards/png/` 下是同名 PNG 导出。这些卡是**营销物料**，不是运行证据——
但第 07 张 "The fast path costs zero tokens" 正好是 §1.3 那 7 条命令的一句话概括，做 slide 时可以直接引它的文案。

`scripts/capture-cast.py`（动画 SVG）和 `scripts/capture-shot.py`（静态 SVG）是配套录制工具，
`docs/shots/*.svg` 由后者重制。`[A]`

---

## 5. 六个代表性端到端场景（skills 落地）

Skills 的调用方式（`[A]` `README.zh-CN.md:400-405`）：

```text
/skills                                          # 列出全部
/skill android-apk-frida inspect this APK        # 强制走某个 skill
/skill proxy-capture capture api.example.test traffic
```

Agent 侧对应两个工具：`list_skills` / `read_skill`（`[A]` `internal/tools/tools_test.go:44`）。
Skill 之间有显式的 **Handoff Rules**（下一步该读哪个 skill），这是这套 skill 体系最值得讲的设计。

---

### 场景 ① CTF 未知样本首轮分诊 —— `ctf-first-pass`

**目标**：拿到一个不知道是什么的文件，判断它属于哪一类题、下一个最小实验是什么。
**证据等级**：`[A]` 流程逐字来自 `skills/ctf-first-pass/SKILL.md:13-17`，输出形态有 §3.3/§3.4 真实录屏佐证。

| 步 | 动作（skill 原文） | agent 调的工具 | 产出 |
| --- | --- | --- | --- |
| 1 | 先对 artifact 或整个目录跑 `ctf_triage` | `ctf_triage` | type / size / sha256 / magic / entropy / printable% / signals / next |
| 2 | 若像二进制：`binary_mitigations` + `extract_symbols` + `strings` + `entropy_scan` | 4 个 read 工具 | 保护位、符号表、可疑串、熵窗口图 |
| 3 | 若像数据：`find_bytes` 找 flag 标记 + `carve_artifacts` 找内嵌文件 | 2 个 read 工具 | 偏移 + 内嵌文件签名列表 |
| 4 | 若含编码串：先 `ctf_decode` 再猜算法 | `ctf_decode` | 明文候选 |
| 5 | 收敛成一句假设：类别 + 可能的 primitive + 最小下一步实验 | — | 结论 |

**决策规则**（`SKILL.md:21-25`，直接可上 slide 的判据表）`[A]`：

| 观察 | 判断 |
| --- | --- |
| 高熵 + 低可打印率 | 加壳 / 压缩 / 加密 / 内嵌密文 |
| 危险导入 或 `/bin/sh` | pwn 路线 → 查保护位和调用点 |
| base64/hex 串挨着 crypto 词 | 先解码，再看 key/IV/mode |
| 多个 magic 偏移 | 取证 / carving 路线 |
| APK/DEX/SO 指示 | 转 `android-apk-frida` |

**Handoff**（`:29-33`）：ELF/Mach-O/PE → `native-pwn-re`；Android → `android-apk-frida` → `jadx`/`radare2-reverse`/`unidbg`；
JS/WASM → `web-wasm-crypto`；需要指令级执行的混淆算法 → `unicorn-emulator`；收尾 → `re-writeup`。

**可直接演示的命令序列**（`SKILL.md:38-42`，与 `demos/reverse-lab/README.md` 一致）`[A]`：

```text
/scan ./artifact
/entropy ./artifact
/carve ./artifact
/findbytes ./artifact flag{
/decode auto <candidate>
```

---

### 场景 ② Android APK 签名算法逆向 —— `android-apk-frida`

**目标**：找出 APK 里请求签名 / 加密是哪个类哪个方法干的，并挂钩子看到真实入参出参。
**证据等级**：`[A]` 步骤与命令逐字来自 `skills/android-apk-frida/SKILL.md:13-41`。

| 步 | 动作 | 工具 / 命令 | 产出 |
| --- | --- | --- | --- |
| 1 | 对 APK 跑 `apk_inspect` | `/apk ./app.apk` | DEX 列表、native libs、**加固壳特征**、框架识别 |
| 2 | 对可疑 `.dex`/`.so`/assets/抠出来的 blob 跑 `ctf_triage` | `/scan ./lib/arm64-v8a/libfoo.so` | 类型 / 熵 / 信号 |
| 3 | 在反编译源码里搜 crypto、token、sign、encrypt、login、root、emulator、debug、frida | `jadx -d jadx_out app.apk` 后 `rg` | 候选类/方法 |
| 4 | **确定 class/method/module 之后**才生成 hook 脚手架 | `frida_hook_template` | Frida JS 骨架 |
| 5 | 涉及 native：合并 `extract_symbols` + `binary_mitigations` + JNI 名搜索 | 2 个 read 工具 | 导出表 + 保护位 |

**JADX 快路（skill 里给的原始命令）** `[A]` `SKILL.md:29-33`：

```bash
jadx -d jadx_out app.apk
rg -n "Cipher|MessageDigest|sign|token|encrypt|decrypt" jadx_out/sources
rg -n "Debug.isDebuggerConnected|TracerPid|ptrace|frida|xposed|substrate" jadx_out/sources -i
```

**三种 hook 目标写法** `[A]` `SKILL.md:37-39`：

```
Java:          com.example.Crypto.sign(java.lang.String, byte[])
Native export: libfoo.so!Java_com_example_Crypto_sign
Native 地址:    libfoo.so+0x1234
```

**`frida_hook_template` 的真实输出形态**（由单元测试断言钉死，比 skill 文档更硬）`[A]` `internal/tools/tools_test.go:271-300`：

| 调用参数 | 输出必须包含 |
| --- | --- |
| `{target:"com.a.Crypto", method:"sign", signature:"java.lang.String"}` | `Java.use("com.a.Crypto")` + `.overload("java.lang.String")` |
| `{platform:"android_native", target:"libfoo.so!sign"}` | `Module.findExportByName("libfoo.so", "sign")` |
| `{platform:"ios_objc", target:"AFCrypto", method:"- sign:"}` | `ObjC.classes` |
| `{template:"android_ssl_pinning"}` | `CertificatePinner` + `TrustManagerImpl` |
| `{template:"android_crypto"}` | `javax.crypto.Cipher` + `SecretKeySpec` |
| `{template:"android_root_debug"}` | `Debug.isDebuggerConnected` + `Runtime.exec` |

**纪律条款**（`SKILL.md:41`，很适合做"agent 的方法论"这一页）`[A]`：
> "Prefer observation hooks first: log args, returns, stack trace, and byte arrays.
> **Patch return values only when the hypothesis is already tested.**"
> （先观察后改写：先打参数/返回/调用栈/字节数组；只有假设已经被验证过，才去改返回值。）

---

### 场景 ③ SO 里的 native 函数还原成可调用服务 —— `unidbg`

**目标**：拿到 `libtarget.so` 里的 JNI 签名函数，在没有真机的情况下把它当成一个函数来调，喂输入拿输出。
**证据等级**：`[A]` 步骤与 pom/harness 逐字来自 `skills/unidbg/SKILL.md`（共 308 行）。

选型分界线（`SKILL.md:9`）`[A]`：
> 需要 Java/JNI 上下文、Android framework 取值、依赖库、文件系统 mock → 用 **unidbg**；
> 只是一小段没有 Java 依赖的独立指令区间 → 用 **unicorn-emulator**。

| 步 | 动作 | 证据来源 | 产出 |
| --- | --- | --- | --- |
| 1 | 先攒证据再写 Java：APK/包名/类/方法（来自 `jadx` 或 `apk_inspect`）；ABI 与 so 路径；JNI 方法签名；导出与偏移（`extract_symbols` / `nm -D` / `radare2-reverse`） | `SKILL.md:13-17` | 一张"参数表" |
| 2 | 写**最小** harness：加载 APK/SO → `callJNI_OnLoad` → 解析目标类 → 调一个方法 | `:18` | `src/main/java/recase/Demo.java` |
| 3 | 第一次跑开 `vm.setVerbose(true)`，**只补失败日志里真正缺的 JNI 回调** | `:19` | 逐步收敛的 AbstractJni 实现 |
| 4 | 稳定 Android 状态：包名、Build 字段、Android ID、`/proc` 下文件、app data 路径 | `:20` | 可重复的运行环境 |
| 5 | hook/trace **只加在可疑函数或依赖周围**（全量指令 trace 很贵） | `:21` | 定点 trace |
| 6 | 跑已知输入/输出测试向量；报告 class、JNI 签名、库、ABI、偏移、mock 清单、**仍缺的回调** | `:22` | 可复现的算法服务 |

**ABI → API 映射（一句话卡片）**：`armeabi-v7a → for32Bit()`，`arm64-v8a → for64Bit()` `[A]` `SKILL.md:15`

**期望目录结构** `[A]` `SKILL.md:56-63`：

```text
case/
├── pom.xml                              # unidbg-android + unidbg-api 0.9.7 (jitpack)
├── apk/target.apk
├── lib/armeabi-v7a/libtarget.so
├── lib/arm64-v8a/libtarget.so
└── src/main/java/recase/Demo.java
```

harness 关键行 `[A]` `SKILL.md:96-110`：

```java
boolean is64 = false;   // set from ABI evidence, not guesswork   ← 注释原文
emulator = (is64 ? AndroidEmulatorBuilder.for64Bit() : AndroidEmulatorBuilder.for32Bit())
        .setProcessName("com.example.app").build();
memory.setLibraryResolver(new AndroidResolver(23));
vm = emulator.createDalvikVM(new File("apk/target.apk"));
vm.setJni(this);  vm.setVerbose(true);
DalvikModule dm = vm.loadLibrary(new File("lib/armeabi-v7a/libtarget.so"), true);
dm.callJNI_OnLoad(emulator);
```

`reverse_toolkit` 也能直接吐 unidbg 模板（测试断言输出含 `AndroidEmulatorBuilder`）`[A]` `tools_test.go:76-81`：

```text
/retool unidbg template libfoo.so 0x1234
```

---

### 场景 ④ Web 前端加密 / JSVMP —— `web-wasm-crypto` → `jsvmp-analysis`

**目标**：网页请求里的 `sign` / `X-Bogus` 类参数是怎么算出来的；如果代码被 JSVMP 虚拟化了怎么办。
**证据等级**：`[A]` `skills/web-wasm-crypto/SKILL.md`（46 行，完整读过）+ `skills/jsvmp-analysis/SKILL.md`（620 行）。

**第一层 · web-wasm-crypto 五步** `[A]` `SKILL.md:13-17`：

| 步 | 动作 | 产出 |
| --- | --- | --- |
| 1 | 定位入口：bundle 文件名、WASM 的 fetch/instantiate 调用、请求构造函数、事件处理器 | 候选入口列表 |
| 2 | 搜 crypto 原语：`crypto.subtle` / `CryptoJS` / `AES` / `RSA` / `HMAC` / `MD5` / `SHA` / `PBKDF2` / `scrypt` | 算法族判定 |
| 3 | 抠出编码常量丢给 `ctf_decode` | key / salt / magic 常量 |
| 4 | WASM：定位 `00 61 73 6d` 魔数、exports/imports、memory、JS 胶水代码 | 模块边界 |
| 5 | **先 hook 再重写**：包 `fetch` / `XMLHttpRequest` / `WebAssembly.instantiate` / crypto 函数，抓输入输出 | 真实 I/O 对 |

skill 里给出的**可直接粘贴的两段 hook** `[A]` `SKILL.md:28-44`：

```javascript
const oldFetch = window.fetch;
window.fetch = async function(...args) { console.log("[fetch]", args); return oldFetch.apply(this, args); };

const oldInstantiate = WebAssembly.instantiate;
WebAssembly.instantiate = async function(buffer, imports) {
  console.log("[wasm]", buffer.byteLength || buffer.length, imports);
  const result = await oldInstantiate.call(this, buffer, imports);
  console.log("[exports]", Object.keys(result.instance.exports));
  return result;
};
```

**第二层 · 判定是不是 JSVMP**（`skills/jsvmp-analysis/SKILL.md:16-23` 的六特征表）`[A]`：

| 特征 | 长什么样 |
| --- | --- |
| Dispatcher 循环 | `while(1){switch(op){...}}` |
| Opcode 数组 | `[12,45,78,...]` 长数字数组 |
| 栈操作 | `stack.push()` / `stack.pop()` |
| 虚拟寄存器 | `regs[0]`, `regs[1]` |
| PC 计数器 | `pc++`, `ip+=2` |
| Handler 表 | `handlers[opcode]()` |

skill 自带一段**可直接在 console 跑的探测脚本**（`SKILL.md:27-58`），四项指标命中 ≥3 判为 JSVMP `[A]`：

```javascript
indicators.dispatcherLoop = /while\s*\(\s*(true|1|!0)\s*\)\s*\{\s*switch/.test(source);
indicators.opcodeArray    = /\[\s*\d+\s*(,\s*\d+\s*){50,}\]/.test(source);
indicators.stackOps       = /\.(push|pop)\s*\(/.test(source) && /stack|stk|_s/.test(source);
indicators.handlers       = /case\s+\d+\s*:/.test(source) && (source.match(/case\s+\d+\s*:/g)?.length > 20);
const isJSVMP = Object.values(indicators).filter(Boolean).length >= 3;
```

**Handoff** `[A]` `web-wasm-crypto SKILL.md:21-24`：WASM 段/导出分析 → `wasm-reverser`；
浏览器运行时 hook / 反调试 → `browser-hook`；请求签名破解 → `api-signature-crack` 或 `web-crypto-analyzer`；
底下藏 native 模块 → `native-pwn-re` / `radare2-reverse`。

**合规条款**（`SKILL.md:48`）`[A]`："Avoid live target abuse. Keep analysis to authorized CTF/lab assets
or locally saved pages, bundles, and WASM files."

---

### 场景 ⑤ Native pwn / crackme 首轮 —— `native-pwn-re`

**目标**：一个 ELF/Mach-O/PE，判断保护位、找到可利用的 primitive、给出可复现的偏移。
**证据等级**：`[A]` `skills/native-pwn-re/SKILL.md:13-46`。

| 步 | 动作 | 工具 |
| --- | --- | --- |
| 1 | `ctf_triage` + `binary_mitigations` | `/scan ./chall` · `/mitigations ./chall` |
| 2 | `extract_symbols` 收集导入/导出/函数名 | `extract_symbols`（内部尝试 nm / readelf / objdump / otool） |
| 3 | 搜可疑串：password、flag、key、usage、`/bin/sh`、格式串、错误信息 | `strings` / `grep` |
| 4 | `find_bytes` 定位已知常量或解码串的偏移 | `/findbytes ./chall <needle>` |
| 5 | 有外部工具就上 radare2 / Ghidra 做 xref 和反编译 | `/r2 ./chall`（交接一个交互式 r2 会话） |
| 6 | 实验保持可复现：标注地址、偏移、架构、字节序、保护位 | — |

**radare2 快路** `[A]` `SKILL.md:22-28`：

```bash
r2 -A ./chall
afl                  # 函数列表
izz                  # 全文件字符串
axt @ str.password   # 交叉引用
pdf @ main           # 反汇编 main
```

大二进制的缓存约定（`SKILL.md:30`）：把 `aaa` 结果缓存到 `~/.cache/r2_analysis/<sha256-prefix>`，避免重复跑昂贵分析。`[A]`

**Pwn 检查表**（`SKILL.md:41-46`，一屏 slide）`[A]`：
RELRO / canary / NX / PIE / stripped → 输入与长度检查 →
格式串汇聚点 `printf(user)` `fprintf` `syslog` → 溢出汇聚点 `gets` `strcpy` `strcat` `sprintf` 未检查的 `read` →
命令汇聚点 `system` `popen` `execve` → **primitive 搞明白之后**才去看有用的串和 gadget。

---

### 场景 ⑥ OLLVM 混淆的 SO 还原 —— `ollvm-deobfuscation`

**目标**：一个被控制流平坦化的 native 函数，恢复出可读的原始逻辑。
**证据等级**：`[A]` `skills/ollvm-deobfuscation/SKILL.md`（583 行）。

**先定性——五种混淆及其编译开关**（`SKILL.md:18-22`，最好的一张对照表）`[A]`：

| 类型 | OLLVM 开关 | 表现 | 难度 |
| --- | --- | --- | --- |
| 控制流平坦化 CFF | `-mllvm -fla` | CFG 变成 switch dispatcher | 高 |
| 虚假控制流 BCF | `-mllvm -bcf` | 插入永真/永假的假分支 | 中 |
| 指令替换 SUB | `-mllvm -sub` | 用等价指令替换 | 低 |
| 字符串加密 | `-mllvm -sobf` | 字面量被加密 | 中 |
| 基本块切分 | `-mllvm -split` | 块被切碎 | 低 |

**CFF 的结构图**（`SKILL.md:74-87`，可直接抄成 slide 配图）`[A]`：

```
Original CFG:          Flattened CFG:
    Entry                  Entry
      |                      |
   [Block1]              [State=1]
      |                      |
   [Block2]  ------>    [Dispatcher]<----+
      |                   /  |  \        |
   [Block3]          [B1] [B2] [B3]      |
      |                 \   |   /        |
    Exit                 [Update]--------+
```

skill 提供 IDA Python 侧的 `detect_cff()`（找 `ncases > 10` 的大 switch + state 变量）
和 `detect_bcf()`（识别恒真谓词，如 `x*(x+1)%2==0`、`x^2>=0`），以及 `CFFDeobfuscator` 类骨架
（`find_dispatcher` / state 变量追踪 / block 与 transition 重建）`[A]` `SKILL.md:26-110+`。

**Handoff 到执行层**：字符串加密走 `so-string-deobfuscation`，需要真跑指令的走 `unicorn-emulator`
（`skills/unicorn-emulator/scripts/` 下有 6 个现成脚本：`arm64_emulator.py`、`arm_emulator.py`、
`x86_emulator.py`、`android_so_emulator.py`、`algorithm_extractor.py`、`utils.py`）`[A]`。

---

### 附：Workflow 模式（决定上面这些场景怎么被"拆给两个模型"）

`[A]` `README.zh-CN.md:305-341`。workflow 默认 `off`，需显式打开。

| 模式 | 什么时候用 | 行为 |
| --- | --- | --- |
| `off` | 默认 | 不加 wrapper，prompt 原样发 |
| `auto` | 混合机器 | 检测到 GPT Cyber / CC CVP 类 route 走 `specialist`，否则走 `caveman` |
| `specialist` | 有授权的 cyber/CVP provider | 先计划，再用 skills 和本地工具推进，保留证据 |
| `caveman` | 普通 provider | planner 写本地证据包；**executor 开新会话，只拿收窄后的只读证据工具** |

```text
/workflow auto
/workflow caveman
0xaf --workflow specialist -p "triage ./app.apk"
```

`caveman` 的四段展开 `[A]`：① planner 看到完整授权任务，输出短计划 + `EXECUTOR_PACKET`；
② executor 在**全新隔离上下文**里只看到这个 packet + 专用 system prompt + 收窄后的只读工具；
③ executor 只能围绕工作区本地文件收集事实（list/read/search、类型、hash、strings、hex 范围、熵、
导入/符号、保护信息、carve 线索、APK 结构）；④ 两段记录写进同一份 session transcript，返回合并结果。

README 自己划的红线（`README.zh-CN.md:337-341`）`[A]`：
> "caveman 不是翻译、暗语、编码或 prompt laundering……遇到 live target、凭据、持久化、部署或网络动作会拒绝。
> 0xAF-Re 不绕过 provider 的策略检查，也不保证某一轮不会被 provider 分类。"

### 附：知识库

`go run ./cmd/import-knowledge ~/notes/re ~/notes/ctf` 建索引，然后 `[A]` `README.zh-CN.md:415-425`：

```text
/know frida ssl pinning
/know raw frida ssl
/know read <entry-id>
```

⚠️ `knowledge/` 目录当前**只有一个 `README.md`**，没有任何预置条目 —— 知识库是空的，要自己灌。`[A]`

---

## 6. Benchmark / 成功率证据：**没有**

诚实结论：**仓库里不存在任何 benchmark、eval harness、成功率或准确率的测量。**

| 项 | 结论 | 证据 |
| --- | --- | --- |
| Go benchmark | **0 个** `func Benchmark` | 全仓 grep 无命中 `[A]` |
| eval / 打分脚本 / 黄金任务集 | **不存在**；`scripts/` 只有 4 个录屏与配图脚本 | `[A]` |
| CI | **无** `.github/` | `[A]` |
| Makefile bench target | 无，只有 `build install test vet fmt clean cross` | `Makefile:5` `[A]` |
| 单元测试 | **173 个 `func Test*`，14 个包 / 25 个文件**，纯正确性，无质量/性能断言 | `[A]` |
| 自称的性能数字 | 二进制 6 684 932 B；50 次启动 `real 0m0.375s` | `docs/shots/verify.svg` `[A]`；但 `docs/index.html:967` 写成 0.335 s / 6.7 ms，**自相矛盾** `[B]` |
| 唯一的"解题成绩" | README 案例 B 的 footer：`turns 1 · took 1m34s · in 162k out 2.2k think 895 cache 122k` | `README.md:316` `[B]`，n=1、自出题、自评分 |
| 官方自述 | "**Roadmap:** local models and reproducible benchmark cases **will be added** so provider/workflow quality can be measured" | `README.md:135-136` `[A]` —— 作者自己承认 benchmark 还没有 |
| 唯一出现 "benchmark/accuracy" 字样的地方 | 在对比图里描述**别的项目**；0xaf 自己那栏写的是 "no anchoring, no edit benchmark — deliberately" | `docs/diagrams/index.html:1231-1233, 1470-1472` `[A]` |

**主要单测分布**（可用来讲"哪些行为被钉死了"）`[A]`：

| 包 | 测试数 | 钉住了什么 |
| --- | --- | --- |
| `internal/ui` | 27 | CJK 显示宽度、ANSI 换行、HUD 行预算、live pane 帧算术、markdown/表格渲染 |
| `internal/tools` | 19 | 工具注册表完整性、**工作区越界拒绝**、write flag 门禁、`/decode` 各模式、carve/find-bytes 偏移、熵扫描、frida 模板 |
| `internal/core` | 25 | agent loop 收尾、缺失工具处理、中断、角色路由、shell 转义与 `!cd`、超时、session 往返、悬空 tool-call 修复、token 估算与压缩 |
| `internal/app` | 24 | flag 解析、行编辑器帧算术、hex/r2 命令守卫、think 模式、任务队列 |
| `internal/providers` | 18 | endpoint 描述、流式解析 |
| 其余 8 包 | 60 | 审批分级、策略门禁、知识引用、plan 更新、skill 解析、嵌入资源等 |

---

## 7. 做 slide 时的取舍建议

**可以放心当"真跑过"讲的**（全部 `[A]`）：

1. `/scan carrier.bin` 与 `/scan artifact.txt` 的两段完整输出 —— 有对照、有 sha256、有信号分类差异。
2. `docs/shots/turn.svg` 的 `t+` 遥测流 —— 一整轮的可观测性长什么样。
3. `docs/shots/approval.svg` 的 curl 拦截 + `/policy` 的默认 JSON —— "拒绝也是一种回答"。
4. 24 个工具清单和 21 read / 1 exec / 1 write 的分级。
5. skills 的 Handoff Rules 图 —— 33 个 skill 不是平铺，是有向图。

**必须标注为"文档声称、未复核"的**（`[B]`）：
案例 B 的四步 plan、七条执行命令、`1m34s / 162k token` 的 footer——README 说抄自 transcript，但 transcript 不在仓库里。

**必须明确说"没有"的**：benchmark、成功率、任何跨样本的质量证据。作者自己在 `README.md:135` 承认了，
照抄这句反而是加分项：把"我们还没有可复现的评测"直接写在 slide 上，比含糊过去可信得多。

**顺手可用的反面素材**：`demos/README.md` 里残留的 `bun src/cli.ts`、
`demos/welcome/README.md` 里指向不存在文件的 `artifacts/*`、
`docs/index.html` 里 0.335 s vs SVG 里 0.375 s —— 讲"文档与实现漂移"时是现成的三个例子。
