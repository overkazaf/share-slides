# M02：OpenAI 模型线与 Codex（2026-08-01 快照）

> 数据可信度分级：**[A]** 官方页面，本人当场抓取核对；**[B]** 权威二手，已抓取；**[C]** 仅见于聚合站，未获一手证实。
> 采集时间：2026-08-01。所有数字均当场抓取，无一条来自训练记忆。

## 0. 抓取条件说明（重要）

- `openai.com` 与 `help.openai.com` 对自动抓取返回 **403**，本次未能使用。
- 实际可用的一手源是 OpenAI 文档站的**两个新域名**（旧域名已 301/308 跳转）：
  - `platform.openai.com/docs/*` → **301** → `developers.openai.com/api/docs/*`（API / 模型 / 定价 / changelog）
  - `developers.openai.com/codex*` → **308** → `learn.chatgpt.com/docs*`（Codex 产品文档）
- 本次 WebSearch 配额已耗尽，全部结果来自直接 URL 抓取，故覆盖面以官方文档站为主。

---

## 1. 在售模型总表（价格 = 美元 / 每百万 token）

价格来自 <https://developers.openai.com/api/docs/pricing> **[A]**；
上下文窗口 / 推理档位 / 知识截止来自各自的 `developers.openai.com/api/docs/models/<id>` 页 **[A]**；
发布日来自 <https://developers.openai.com/api/docs/changelog> **[A]**。

### 1.1 GPT-5.6 家族（当前旗舰，2026-07-09 发布）

| 模型 ID | 发布日 | 上下文窗口 | 最大输出 | 输入 | 缓存输入 | 输出 | 定位 |
|---|---|---|---|---|---|---|---|
| `gpt-5.6-sol` | 2026-07-09 [A] | 1,050,000 [A] | 128,000 [A] | $5.00 [A] | $0.50 [A] | $30.00 [A] | 前沿能力（flagship capability） |
| `gpt-5.6-terra` | 2026-07-09 [A] | 1,050,000 [A] | 128,000 [A] | $2.00 [A] | $0.20 [A] | $12.00 [A] | 智能与成本平衡，日常主力 |
| `gpt-5.6-luna` | 2026-07-09 [A] | 1,050,000 [A] | 128,000 [A] | $0.20 [A] | $0.02 [A] | $1.20 [A] | 高并发、低成本 |

- 三者知识截止均为 **Feb 16, 2026** [A]。
- 推理档位：模型列表页对 GPT-5.6 三款标注 **none / low / medium / high / xhigh / max** [A]。
  注意：**`max` 档是 5.6 家族新增的**，5.5 及更早只到 `xhigh`。单个模型详情页未复述档位列表，故此项以列表页为准。
- changelog 原文：「Released the GPT-5.6 model family, including GPT-5.6 Sol for frontier capability, GPT-5.6 Terra for a balance of intelligence and cost, and GPT-5.6 Luna for efficient, high-volume workloads」[A]

### 1.2 GPT-5.5 / 5.4（上一代前沿，面向专业工作）

| 模型 ID | 发布日 | 上下文窗口 | 最大输出 | 输入 | 缓存输入 | 输出 | 知识截止 |
|---|---|---|---|---|---|---|---|
| `gpt-5.5` | 2026-04-24 [A] | 1,050,000 [A] | 128,000 [A] | $5.00 [A] | $0.50 [A] | $30.00 [A] | Dec 01, 2025 [A] |
| `gpt-5.5-pro` | 未获证实 | 未获证实 | 未获证实 | $30.00 [A] | — | $180.00 [A] | 未获证实 |
| `gpt-5.4` | 2026-03-05 [A] | 1,050,000 [A] | 128,000 [A] | $2.50 [A] | $0.25 [A] | $15.00 [A] | Aug 31, 2025 [A] |
| `gpt-5.4-mini` | 未获证实 | 未获证实 | 未获证实 | $0.75 [A] | $0.075 [A] | $4.50 [A] | 未获证实 |
| `gpt-5.4-nano` | 未获证实 | 未获证实 | 未获证实 | $0.20 [A] | $0.02 [A] | $1.25 [A] | 未获证实 |
| `gpt-5.4-pro` | 未获证实 | 未获证实 | 未获证实 | $30.00 [A] | — | $180.00 [A] | 未获证实 |

- `gpt-5.5` 推理档位：「none, low, medium (default), high and xhigh」[A]（medium 为默认）
- `gpt-5.4` 推理档位：「none (default), low, medium, high and xhigh」[A]（**none 为默认**）
- changelog：5.5 =「a new frontier model for complex professional work」；5.4 =「our newest frontier model for professional work」[A]

> **退役预告 [A]**：`learn.chatgpt.com` changelog 2026-07-31 条目——「GPT-5.4 and GPT-5.4 mini retire from Codex on August 31」，迁移目标分别为 GPT-5.6 Terra 与 Luna。**即本月底 Codex 端 5.4 线下线**，这是讲「为什么现在要换型号」的现成锚点。

### 1.3 GPT-5.3-Codex（唯一在售的 Codex 专用 API 模型）

| 模型 ID | 发布日 | 上下文窗口 | 最大输出 | 输入 | 缓存输入 | 输出 | 推理档位 | 知识截止 |
|---|---|---|---|---|---|---|---|---|
| `gpt-5.3-codex` | 2026-02-24 [A] | 400,000 [A] | 128,000 [A] | $1.75 [A] | $0.175 [A] | $14.00 [A] | low / medium / high / **xhigh** [A] | Aug 31, 2025 [A] |

- changelog 原文：2026-02-24「Released `gpt-5.3-codex` to the Responses API for specialized coding tasks」[A]
- **只在 Responses API 上提供**（不是 Chat Completions）[A]
- 定价与 `gpt-5.2` 完全相同（$1.75 / $14.00），可作为「专用模型不必更贵」的论据。
- 注意：官方定价页把它单列在 **Codex Models** 分组下，是该分组里**唯一**的条目 [A]。没有 `gpt-5.4-codex` / `gpt-5.6-codex` 之类的后继专用型号在售——5.4 之后 Codex 直接用通用型号。

### 1.4 GPT-5.2 / 5.1 / 5（仍在售的老型号）

| 模型 ID | 发布日 | 上下文窗口 | 最大输出 | 输入 | 缓存输入 | 输出 | 知识截止 |
|---|---|---|---|---|---|---|---|
| `gpt-5.2` | 2025-12-11 [A] | 400,000 [A] | 128,000 [A] | $1.75 [A] | $0.175 [A] | $14.00 [A] | Aug 31, 2025 [A] |
| `gpt-5.2-pro` | 未获证实 | 未获证实 | 未获证实 | $21.00 [A] | — | $168.00 [A] | 未获证实 |
| `gpt-5.1` | 2025-11-13 [A] | 400,000 [A] | 128,000 [A] | $1.25 [A] | $0.125 [A] | $10.00 [A] | Sep 30, 2024 [A] |
| `gpt-5` | 2025-08-07 [B] | 400,000 [A] | 128,000 [A] | $1.25 [A] | $0.125 [A] | $10.00 [A] | Sep 30, 2024 [A] |
| `gpt-5-mini` | 未获证实 | 未获证实 | 未获证实 | $0.25 [A] | $0.025 [A] | $2.00 [A] | 未获证实 |
| `gpt-5-nano` | 未获证实 | 未获证实 | 未获证实 | $0.05 [A] | $0.005 [A] | $0.40 [A] | 未获证实 |
| `gpt-5-pro` | 未获证实 | 未获证实 | 未获证实 | $15.00 [A] | — | $120.00 [A] | 未获证实 |

- `gpt-5.2` / `gpt-5.1` 推理档位：均为「none (default), low, medium, high」，其中 **5.2 多一档 xhigh**，5.1 没有 [A]
- `gpt-5` 推理档位用的是**旧命名**：「minimal, low, medium, high」[A] —— 是 `minimal` 而非 `none`，这是 5 → 5.1 的 API 断点
- `gpt-5` 发布日 **2025-08-07** 来自 Wikipedia **[B]**，OpenAI 官方 changelog 未回溯到该条目
- changelog 5.1 原文：「especially proficient in: Steerability and faster responses when less thinking's required, Code generation and coding use cases, Agentic workflows」[A]
- changelog 5.2 原文：「improvements over the previous GPT-5.1 in: General intelligence, Instruction following, Accuracy and token efficiency, Multimodality—especially vision, Code generation—especially front-end UI creation」[A]

### 1.5 演进速览（可直接做时间轴页）

| 日期 | 事件 | 级别 |
|---|---|---|
| 2025-08-07 | GPT-5 发布 | [B] |
| 2025-11-13 | GPT-5.1 | [A] |
| 2025-12-11 | GPT-5.2 | [A] |
| 2026-02-24 | **GPT-5.3-Codex**（Responses API，编码专用） | [A] |
| 2026-03-05 | GPT-5.4 | [A] |
| 2026-04-24 | GPT-5.5 | [A] |
| 2026-07-09 | **GPT-5.6 家族**（Sol / Terra / Luna） | [A] |
| 2026-08-31 | GPT-5.4 与 5.4-mini 从 Codex 退役（预告） | [A] |

**节奏**：11 个月 7 次前沿模型迭代，平均约 **47 天**一代。

**两处关键跃迁**：
1. **上下文窗口**：400K（GPT-5 → 5.3-codex）→ **1.05M**（5.4 起），提升 **2.6 倍** [A]
2. **推理档位**：`minimal`（5）→ `none`（5.1）→ 增 `xhigh`（5.2）→ 增 `max`（5.6）[A]

---

## 2. Codex 产品线形态（2026-08）

来源：<https://learn.chatgpt.com/docs>、`/docs/cli`、`/docs/cloud`、`/docs/cloud/internet-access`、`/docs/pricing` **[A]**

### 2.1 五种形态

| 形态 | 说明 | 级别 |
|---|---|---|
| ChatGPT 桌面 App | 内置 Codex | [A] |
| ChatGPT 网页版 | 浏览器内 | [A] |
| **Codex CLI** | 终端 agent，`curl -fsSL https://chatgpt.com/codex/install.sh \| sh` 安装 | [A] |
| **Codex IDE 扩展** | IDE 插件 | [A] |
| **Codex cloud** | 隔离云环境跑任务 | [A] |

### 2.2 CLI 要点 [A]

- 默认模型：**`gpt-5.6-sol`**，默认推理档 medium
- `/model` 切模型与推理档；`/permissions` 控制何时可免询问改文件、跑命令
- `codex exec` 用于非交互流水线；`/review` 做代码评审
- `codex cloud` 子命令：「browse active and completed chats, submit work to a configured environment, and apply the result to your local repository from the terminal」——**在终端里派活到云端，再把结果拉回本地仓库**
- 支持 skills / plugins / MCP servers
- 最新版本记录：CLI **0.145.0**（2026-07-21），新增分页 thread 历史、从 **Cursor 和 Claude Code 导入**、Amazon Bedrock 支持（「GPT-5.6 Sol as the default Bedrock model」）[A]

---

## 3. Codex 云端并行任务机制（PPT 核心论据）

### 3.1 官方明确写了的 [A]

**任务隔离与并行**（`learn.chatgpt.com/docs/cloud` 原文）：
- 「Run tasks in **isolated cloud environments**, work in parallel, and start work from the web, GitHub, Linear, or Slack.」
- 「**Run tasks in parallel and return as each task reaches a reviewable result.**」
- 「Give longer tasks **dedicated environments** and let them continue while you work on something else.」
- 「Start work in parallel **without tying up your local machine**.」

**环境可配置**：
- 「Configure the dependencies, tools, variables, and setup steps each repository needs.」——按仓库定义可复现环境

**任务入口**：Web、GitHub、Linear、Slack 四处发起 [A]

**交付方式**：「Review the summary and diff, request a follow-up, or open a pull request when the result is ready」——产出是 diff + 摘要，可直接开 PR [A]

**网络访问策略**（安全论据，`/docs/cloud/internet-access`）[A]：
- **默认关闭**：「By default, Codex blocks internet access during the **agent phase**.」
- 但 **setup 脚本阶段保留联网**，用于装依赖 —— 这是「装得上依赖但 agent 跑起来后出不去」的两段式设计
- 三档：**Off / On / Restricted**
- Restricted 支持**域名白名单**（预设 None、Common dependencies、All，可加自定义域名）
- 可限制 **HTTP 方法只允许 `GET`、`HEAD`、`OPTIONS`**（封掉 POST/PUT/PATCH/DELETE）—— 这条是防外泄的关键开关
- 官方风险提示原文：启用 agent 联网「increases security risk」，列举 prompt injection、代码/密钥外泄、恶意软件、许可证问题；文档给的具体例子是**GitHub issue 里的隐藏指令把 commit message 泄露到攻击者服务器**

### 3.2 计费与配额 [A]

- **Codex 用量含在 ChatGPT 订阅里**，不单独计费：「ChatGPT Work and Codex share usage.」
- **本地与云端共享同一个滚动窗口**：「The usage limits for local messages and cloud chats share a **five-hour window**.」
  —— 即**云端派活不是「免费的额外算力」，它和本地对话吃同一个池子**。这点对「为什么用它派活」的论证很关键，讲的时候别讲成白嫖。
- 按**模型档位**分别计额度，5 小时滚动窗口内的消息数区间：

| 套餐 | GPT-5.6 Sol | Terra | Luna |
|---|---|---|---|
| Plus | 10–100 | 25–200 | 250–2,000 |
| Pro 5x | 50–500 | 125–1,000 | 1,250–10,000 |
| Pro 20x | 200–2,000 | 500–4,000 | 5,000–40,000 |
| Business | 同 Plus | 同 Plus | 同 Plus |

（区间形式为官方给法，实际值随任务复杂度浮动）[A]

- **超额买 credits**：「can purchase additional credits to continue working」，rate card 按「Credits per 1M tokens」计，分 Input / Cached Input / Output。已核到的样例：**GPT-5.6 Terra = 50 credits/1M 输入，300 credits/1M 输出** [A]
- 图像生成消耗额度更快：「3–5x faster on average」[A]
- 套餐价格：Business「$20 / user / month」年付；个人 Free $0 起，Pro 档 $100–$200/月区间（对应 Pro 5x / Pro 20x）[A]
- API Key 走 usage-based 按 token 计价 [A]

### 3.3 明确「未获证实」的部分 —— 上台别讲

以下是 PPT 上容易想当然、但**官方文档没有公开**的，本次抓取全部落空：

| 问题 | 状态 |
|---|---|
| 每个任务是否独立 container / VM（具体虚拟化形态） | **未获证实**。官方只说「isolated cloud environments」「dedicated environments」，没有 container / VM / sandbox 的技术措辞 |
| 并发任务数上限（能同时跑几个） | **未获证实**。文档反复说 parallel，但**从未给出并发数字** |
| 单任务超时时长 | **未获证实** |
| 单任务的 CPU / 内存 / 磁盘规格 | **未获证实** |
| 云任务是否按任务另行计费 | **部分证实**：确认与本地共享 5 小时窗口；但「一个云任务折算几条消息」未公开 |
| 仓库是否每任务独立 clone | **未获证实**（合理推断，但无原文） |

尝试过但拿不到的地址：`help.openai.com/...`（403）、`learn.chatgpt.com/docs/cloud/environments`、`/docs/cloud/tasks`、`/docs/cloud/quickstart`、`/docs/cloud/code-review`、`/docs/limits`（均 404）、`github.com/openai/codex` README（未含云端并发描述）。

**建议话术**：讲「隔离环境 + 并行 + 结果就绪即返回 + 默认断网」这四点（全部有官方原文背书），**回避具体并发数字**。如果听众追问上限，答「官方未公开」比编一个数字安全。

---

## 4. 来源清单

| # | URL | 级别 | 用途 |
|---|---|---|---|
| 1 | https://developers.openai.com/api/docs/pricing | [A] | 全部单价 |
| 2 | https://developers.openai.com/api/docs/models | [A] | GPT-5.6 家族规格与推理档位 |
| 3 | https://developers.openai.com/api/docs/models/gpt-5.3-codex | [A] | Codex 专用模型规格 |
| 4 | https://developers.openai.com/api/docs/models/gpt-5.6-sol / -terra / -luna | [A] | 1.05M 上下文、知识截止 |
| 5 | https://developers.openai.com/api/docs/models/gpt-5.5 / gpt-5.4 / gpt-5.2 / gpt-5.1 / gpt-5 | [A] | 上下文、推理档位、知识截止 |
| 6 | https://developers.openai.com/api/docs/changelog | [A] | 各版本发布日 |
| 7 | https://learn.chatgpt.com/docs | [A] | Codex 五种形态 |
| 8 | https://learn.chatgpt.com/docs/cli | [A] | CLI 默认模型、命令 |
| 9 | https://learn.chatgpt.com/docs/cloud | [A] | 并行任务原文表述 |
| 10 | https://learn.chatgpt.com/docs/cloud/internet-access | [A] | 网络策略、安全风险 |
| 11 | https://learn.chatgpt.com/docs/pricing | [A] | 套餐额度、credits、5 小时窗口 |
| 12 | https://learn.chatgpt.com/docs/changelog | [A] | CLI 0.145.0、5.4 退役预告 |
| 13 | https://en.wikipedia.org/wiki/GPT-5 | [B] | 仅用于 GPT-5 发布日 2025-08-07 |

**本笔记无 [C] 级数据**——没能一手证实的，一律写「未获证实」，未从聚合站补缺。
