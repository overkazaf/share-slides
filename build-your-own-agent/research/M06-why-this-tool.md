# M06：「为什么这样用」的量化依据

> 采集日期：2026-08-01
> 用途：服务单页 PPT 「笔者的武器库 —— 每个工具的模型特点 + 为什么这样用 + 数据支撑」
> 采集约束：**所有数字均当场抓取来源页面**，未使用训练记忆。抓不到的一律标「未获证实」。

## 0. 可信度分级说明（上台前请照此口径）

| 等级 | 含义 | 本文件中的典型来源 |
|---|---|---|
| **[A]** | 厂商官方页 / 官方定价页 / 官方 model card / 榜单官方站，**已亲自抓取核对** | platform.claude.com、developers.openai.com、docs.x.ai、api-docs.deepseek.com、together.ai、tbench.ai、swebench.com、support.google.com |
| **[B]** | 权威二手 / 同行评议或预印本论文 / 独立研究机构，**已抓取** | arXiv、Chroma Research、Aider 官方榜、Vectara |
| **[C]** | 只见于聚合站、内容农场、或仅通过搜索摘要见到而未亲自打开原文 | 见 §10「[C] 隔离区」——**绝不与 [A] 混排** |

⚠️ 本次采集中 WebSearch 配额已耗尽，全程改用 DuckDuckGo HTML 端点 + 直接 WebFetch 官方 URL 完成。部分官方站（openai.com/index/*、dl.acm.org）返回 403，相关条目已标注「未获证实」。

---

## 1. 主张：「深度重构用 Claude Code」——编辑-执行-验证闭环的价值

### 1.1 最强证据：同一个模型，换 harness 分数差 18.4 个百分点

Terminal-Bench 2.0 官方榜（tbench.ai）的设计前提就是**评测「agent harness + model」组合而非孤立模型**。同一个 Claude Opus 4.6 在不同脚手架下：

| Agent / Harness | 模型 | 准确率 | 榜内排名 | 等级 |
|---|---|---|---|---|
| Meta-Harness | Claude Opus 4.6 | **76.4% ± 2.4** | 11 | [A] |
| Capy | Claude Opus 4.6 | 75.3% ± 2.4 | 14 | [A] |
| Terminus 2 | Claude Opus 4.6 | 62.9% ± 2.7 | 36 | [A] |
| Claude Code | Claude Opus 4.6 | **58.0% ± 2.9** | 50 | [A] |

**极差 = 18.4 个百分点（76.4 − 58.0），同一模型。**
来源：https://www.tbench.ai/leaderboard/terminal-bench/2.0（榜单页原文："A Terminal-Bench team member ran the evaluation and verified the results. Displaying 142 of 142 available entries"）

反向验证——**同一个 harness，换模型分差更大**：

| Agent | 模型 | 准确率 | 等级 |
|---|---|---|---|
| Codex CLI | GPT-5.5 | 82.2% ± 2.2（榜首区，rank 4） | [A] |
| Codex CLI | GPT-5.2 | 62.9% ± 3.0 | [A] |
| Codex CLI | GPT-5.1-Codex-Max | 60.4% ± 2.7 | [A] |
| Codex CLI | GPT-5 | 49.6% ± 2.9 | [A] |
| Codex CLI | GPT-5-Codex | 44.3% ± 2.7 | [A] |
| Codex CLI | GPT-5-Mini | 31.9% ± 3.0 | [A] |
| Codex CLI | GPT-5-Nano | 11.5% ± 2.3 | [A] |

→ 同 harness 换模型极差 **70.7pp**；同模型换 harness 极差 **18.4pp**。
**上台可用的诚实结论**：模型是主项，脚手架是不可忽略的次项（约模型效应的 1/4 量级）；且 Terminal-Bench 榜上 Claude Code 的默认配置分数**并不是最高**——这条数据支持「闭环脚手架是独立变量」，但**不支持**「Claude Code 分数最高」。别讲成后者。

### 1.2 SWE-bench 的评测方式本身就是「必须真跑测试」

| 事实 | 数值 / 原文 | 等级 |
|---|---|---|
| SWE-bench Verified 规模 | **500 engineer-confirmed solvable problems** | [A] |
| 原始 SWE-bench 规模 | 2,294 real GitHub issues | [A]（swebench.com 站内） |
| 评测方式（官方原文） | "applying their generated patches to real-world repositories and **running the repository's tests** to verify if the issue is resolved. The evaluation is performed in a **containerized Docker environment**" | [A] |
| 计分口径 | Instances resolved = "Number of instances where the patch fixed the issue"；Resolution rate = "Percentage of submitted instances successfully resolved" | [A] |

来源：https://www.swebench.com/SWE-bench/ 、https://www.swebench.com/SWE-bench/guides/evaluation/

> **演讲用法**：SWE-bench Verified 与 HumanEval/MBPP 类纯生成基准的根本差别是——前者的分数**只能由沙箱里真实跑通的测试产生**，模型「看起来写对了」不计分。这就是「编辑-执行-验证闭环」被量化的地方。
> ⚠️ 注：官方评测指南页**未**给出 FAIL_TO_PASS / PASS_TO_PASS 的文字定义（该定义在 harness reference 与论文中），故本文件不引用这两个术语的具体口径。

### 1.3 执行反馈 vs 单次生成：一篇预印本给出了 pp 级差值

| 指标 | 数值 | 等级 |
|---|---|---|
| AgentForge（强制 Docker 沙箱执行验证）在 SWE-bench Lite | **40.0% resolution** | [B] |
| 相对单代理基线的提升 | **+26 至 28 个百分点** | [B] |

论文原文（摘要，已抓取）："We introduce execution-grounded verification as a first-class principle: every code change must survive sandboxed execution before propagation... AGENTFORGE achieves 40.0% resolution on SWE-BENCH Lite, outperforming single-agent baselines by 26–28 points. **Ablations confirm that execution feedback and role decomposition each independently drive performance.**"
来源：https://arxiv.org/abs/2604.13120

### 1.4 「闭环 > 复杂脚手架」的官方旁证

SWE-agent 官方站公告原文："**July 24: Mini-SWE-Agent achieves 65% on SWE-bench verified in 100 lines of python!**"
来源：https://swe-agent.com/latest/ 等级 **[A]**（项目官方文档站）

> 演讲用法：100 行 Python 的极简 bash 循环拿到 65% —— 说明真正起作用的是**「跑一下再改」这个动作**，不是脚手架的复杂度。

### 1.5 Anthropic 官方对「验证-迭代」能力的定性口径

Claude Opus 5 官方发布页原文："**Opus 5 is much stronger at verifying its work and iterating carefully until it succeeds**"。等级 [A]，来源 https://www.anthropic.com/news/claude-opus-5
⚠️ 这是**定性**表述，官方**未**给出对应的量化 delta。上台时不要把它包装成数字。

---

## 2. 主张：「长时并行/批量 PR 用 Codex 云端」

### 2.1 官方能给到的（[A]）

| 项 | 原文 / 数值 | 来源 |
|---|---|---|
| 并行能力（定性） | "**Run tasks in parallel** and start work from the web, GitHub, Linear, or Slack." | learn.chatgpt.com/docs/cloud |
| 长任务隔离（定性） | "**Give longer tasks dedicated environments** and let them continue while you work on something else." | learn.chatgpt.com/docs/cloud |
| 容器状态缓存 | "Codex caches container state for **up to 12 hours**" | learn.chatgpt.com/docs/environments/cloud-environment |
| 配额窗口 | "Local messages and cloud chats **share a five-hour window**" | learn.chatgpt.com/docs/pricing |
| 网络策略 | 云端沙箱**默认关闭外网**，可按 environment 配置；官方建议保持"as limited as possible"以防 prompt injection 与数据外泄 | learn.chatgpt.com/docs/cloud/internet-access |

### 2.2 各档位配额（[A]，learn.chatgpt.com/docs/pricing）

| 套餐 | 每 5 小时窗口内的本地消息数（随模型浮动） | 云端 chat |
|---|---|---|
| Plus | 10 – 2,000 | 共用同一 5 小时窗口 |
| Pro 5x | 50 – 10,000 | 共用同一 5 小时窗口 |
| Pro 20x | 200 – 40,000 | 共用同一 5 小时窗口 |
| Business | 同 Plus（10 – 2,000） | 共用同一 5 小时窗口 |
| API Key | 按 token 计费，"pay only for the tokens Codex uses, based on API pricing" | — |

Codex 内 credit 计价（每 1M tokens，[A]）：GPT-5.6 Sol 125 / 12.5 缓存 / 750 输出；GPT-5.6 Terra 50 / 5 / 300；GPT-5.6 Luna 5 / 0.5 / 30；GPT-5.4 62.50 / 6.25 / 375；GPT-5.4 mini 18.75 / 1.875 / 113。

### 2.3 ❌ 未获证实（重要，别在台上瞎报）

| 想要的数字 | 状态 |
|---|---|
| **并发任务上限**（同时能跑几个云端任务） | **未获证实** —— learn.chatgpt.com/docs/cloud、/docs/environments/cloud-environment、/docs/pricing 三页均无数值；help.openai.com 与 openai.com/index/introducing-codex/ 返回 403 无法核对 |
| **单任务时长上限 / 超时** | **未获证实** —— 官方文档未给出分钟数 |
| **沙箱 CPU / RAM / 磁盘规格** | **未获证实** |
| 「典型任务耗时 1–30 分钟」这类说法 | **未获证实** —— 本次未抓到任何官方页含此表述，请勿引用 |

> **上台建议措辞**：「Codex 云端的并行是官方明确宣称的产品能力（原文 'Run tasks in parallel'），配额按 5 小时窗口计；但**并发上限和单任务时长上限 OpenAI 没有公开数字**——这一点我不编。」

---

## 3. 主张：「跨仓库检索用子代理扇出」

**这是本份笔记里官方数字最硬的一条。** 全部来自 Anthropic 工程博客原文（[A]，https://www.anthropic.com/engineering/multi-agent-research-system）：

| 维度 | 官方原文口径 | 数值 |
|---|---|---|
| **Token 放大（agent vs chat）** | "agents typically use about **4× more tokens** than chat interactions" | 4× |
| **Token 放大（multi-agent vs chat）** | "multi-agent systems use about **15× more tokens** than chats" | 15× |
| **效果提升** | "a multi-agent system with **Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents** outperformed single-agent Claude Opus 4 by **90.2%** on our **internal research eval**" | +90.2% |
| **为什么有效（归因）** | "three factors explained **95%** of the performance variance in the BrowseComp evaluation"，其中 "**token usage by itself explains 80%** of the variance" | 80% / 95% |
| **典型扇出宽度** | "the lead agent spins up **3-5 subagents in parallel**"；"subagents use **3+ tools in parallel**" | 3–5 |
| **按任务复杂度的扇出配方** | "Simple fact-finding requires just **1 agent with 3-10 tool calls**, direct comparisons might need **2-4 subagents with 10-15 calls each**, and complex research might use **more than 10 subagents**" | 见原文 |
| **并行化的时间收益** | "These changes **cut research time by up to 90%** for complex queries" | −90% |
| **工具描述优化的收益** | "resulted in a **40% decrease in task completion time** for future agents using the new description" | −40% |

> **一句话卖点（严格按官方口径）**：**烧 15 倍 token，换 90.2% 的内部研究评测提升**；而且官方自己做了归因——**光是「用掉了多少 token」这一个变量就解释了 BrowseComp 上 80% 的表现方差**。所以子代理扇出的本质是「用可并行的 token 预算买覆盖面」。
> ⚠️ 严格注意三点：① 90.2% 是**相对提升**不是绝对分数；② 评测是 Anthropic **内部 research eval**，非公开榜；③ 15× 与 90.2% 分别出自博客不同段落，是两个独立口径，不是同一次实验的配对数据。

---

## 4. 主张：「长文档消化用 Gemini Notebook」

### 4.1 官方容量数字（[A]，support.google.com/gemininotebook/answer/16213268）

| 档位 | 笔记本数 | **每本 source 数** | 每日对话数 | Audio Overview/日 | Video Overview/日 |
|---|---|---|---|---|---|
| Standard（免费） | 100 | **50** | 50 | 3 | 3 |
| Plus | 200 | **100** | 200 | 6 | 6 |
| Pro | 500 | **300** | 500 | 20 | 20 |
| Ultra (20TB) | 500 | **500** | 2,500 | 100（cinematic 2） | 100 |
| Ultra (30TB) | 500 | **600** | 5,000 | 200（cinematic 10） | 200 |

官方原文："Daily quotas are reset after 24 hours; monthly quotas are reset after 30 days."

**单 source 上限（[A]，support.google.com/notebooklm/answer/16269187）**：
> "The current limit is **500,000 words per source** or up to **200MB** for local uploads."
> "Get 100 notebooks, with up to 50 sources each and 500,000 words each."（免费档表述）

### 4.2 由官方数字推导的「相对通用长上下文的优势」

> ⚠️ 以下是**由 [A] 数字做的算术推导**，不是官方直接宣称，请在台上说明是推算。

| 对比 | 计算 | 结果 |
|---|---|---|
| 单个 source 上限 500,000 words | 按英文 1 word ≈ 1.33 tokens 粗估 | ≈ **66.5 万 tokens**——**单篇文档就逼近一个完整 1M 上下文窗口** |
| Pro 档 300 sources × 500,000 words | — | 理论上限 **1.5 亿 words**（≈ 200M tokens 量级） |
| 免费档 50 × 500,000 words | — | 理论上限 **2,500 万 words** |
| 对照：Claude 4.6+ / Mythos Preview 上下文窗口 | 官方 [A]："include the full **1M token context window** at standard pricing" | 1M tokens ≈ 75 万 words |

→ **量级差约两个数量级（Pro 档 200M tokens 级 vs 1M tokens 窗口）**。这是「source-grounded 检索」相对「把全部内容塞进上下文」的**容量维度**优势，且是可由官方数字算出来的。

### 4.3 幻觉率：有公开数据，但是 [B] 且样本单一

arXiv 2509.25498《Not Wrong, But Untrue: LLM Overconfidence in Document-Based Queries》，等级 **[B]**，https://arxiv.org/abs/2509.25498

| 系统 | 输出中含 ≥1 处幻觉的比例 |
|---|---|
| 全体平均 | **30%** |
| Gemini | 约 **40%** |
| ChatGPT | 约 **40%** |
| **NotebookLM** | **13%** |

- 语料：**300 篇文档**，主题为美国 TikTok 诉讼与政策
- 关键定性发现（原文）：错误类型不是编造实体或数字，而是 "models added **unsupported characterizations of sources** and **transformed attributed opinions into general statements**" —— 论文称之为 "**interpretive overconfidence**"（诠释性过度自信）

> **诚实版讲法**：「有一篇 2025 年的新闻业场景研究，在 300 篇 TikTok 诉讼文档上比过：通用 Gemini/ChatGPT 约 40% 的回答至少含一处幻觉，**NotebookLM 是 13%**——**约 1/3**。但注意两点：① 单一语料、单一领域，不能当通用结论；② 它剩下的 13% 错法很阴——不是瞎编数字，而是**把「某人的观点」悄悄转述成「事实」**。所以 source-grounded 降低的是『无中生有』，不降低『过度诠释』。」

**引用准确率（citation accuracy）本身：未获证实。** Google 官方 FAQ 只有定性表述——"Gemini Notebook answers questions based on the information provided in your uploaded sources."、"If your source content is too short, Gemini Notebook references the entire document without a cited individual text from your source."——**没有任何引用正确率百分比**。ACM 上的 NotebookLM misalignment 论文（10.1145/3711670.3764628）返回 403，未能核对。

---

## 5. 主张：「实时舆情用 Grok」

### 5.1 能力是可验证的（[A]，docs.x.ai）

**X Search 工具**（https://docs.x.ai/developers/tools/x-search）：

| 参数 / 能力 | 原文 |
|---|---|
| 检索类型 | "**keyword search, semantic search, user search, and thread fetch on X**" |
| 时间窗过滤 | `from_date` / `to_date`，**ISO8601 格式** |
| 账号白/黑名单 | `allowed_x_handles`（**最多 20**）/ `excluded_x_handles`（**最多 20**） |
| 多模态 | `enable_image_understanding`、`enable_video_understanding` |
| 定位 | 文档称其提供 "access to **real-time** social media content" |

**Web Search 工具**（https://docs.x.ai/developers/tools/web-search）：
- `allowed_domains`（**最多 5**）/ `excluded_domains`（**最多 5**）
- 官方约束原文："`allowed_domains` cannot be set together with `excluded_domains` in the same request"
- `enable_image_understanding`、`enable_image_search`

### 5.2 官方定价（[A]，https://docs.x.ai/developers/pricing）

| 服务端工具 | 价格 |
|---|---|
| **X Search** | **$5 / 1,000 calls** |
| **Web Search** | **$5 / 1,000 calls** |

对照：Claude API 的 web search 是 **$10 / 1,000 searches**（[A], platform.claude.com/docs/en/about-claude/pricing）→ **xAI 检索单价为 Anthropic 的 1/2**。

### 5.3 Grok 模型定价与上下文（[A]）

| 模型 | 上下文 | 输入 $/1M | 缓存输入 $/1M | 输出 $/1M |
|---|---|---|---|---|
| grok-4.5（<200k） | 500k | $2.00 | $0.30 | $6.00 |
| grok-4.5（≥200k） | 500k | $4.00 | $0.60 | $12.00 |
| grok-4.3（<200k） | **1M** | $1.25 | $0.20 | $2.50 |
| grok-4.3（≥200k） | 1M | $2.50 | $0.40 | $5.00 |
| grok-4.20-0309-reasoning（<200k） | 1M | $1.25 | $0.20 | $2.50 |
| grok-4.20-multi-agent-0309（<200k） | 1M | $1.25 | $0.20 | $2.50 |
| grok-build-0.1（<200k） | 256k | $1.00 | $0.20 | $2.00 |

> 注意「≥200k 输入时单价翻倍」是 xAI 的明确阶梯定价——**长上下文在 Grok 上不是免费的**，这与 Anthropic「1M 窗口按标准价，900k 请求与 9k 请求同单价」形成直接对比（见 §7.3）。

### 5.4 ❌ 未获证实

| 想要的数字 | 状态 |
|---|---|
| X 数据的**索引延迟 / 新鲜度 SLA**（几秒 / 几分钟内可检索到新推文） | **未获证实** —— docs.x.ai 全站未给出任何延迟数值或新鲜度保证 |
| 覆盖的推文总量 / 索引规模 | **未获证实** |

> **上台建议措辞**：「Grok 的实时性，**可验证的部分**是：官方 X Search 工具支持 `from_date`/`to_date` 精确时间窗、支持指定最多 20 个账号、支持 thread fetch，$5/千次调用。**不可验证的部分**是：xAI 从来没公布过『新推文多久能被检索到』的延迟指标。所以我只能说『它有一等公民的 X 检索通道』，不能说『它比别人快 N 秒』。」

---

## 6. 主张：「批量/私有化用开源权重」——价格差多少倍

### 6.1 原始定价（全 [A]，均为官方定价页）

**Anthropic**（platform.claude.com/docs/en/about-claude/pricing）

| 模型 | 输入 $/MTok | 5m 缓存写 | 1h 缓存写 | 缓存命中 | 输出 $/MTok |
|---|---|---|---|---|---|
| Claude Fable 5 | $10 | $12.50 | $20 | $1 | **$50** |
| Claude Mythos 5（限量） | $10 | $12.50 | $20 | $1 | $50 |
| **Claude Opus 5** | **$5** | $6.25 | $10 | $0.50 | **$25** |
| Claude Opus 4.8 / 4.7 / 4.6 / 4.5 | $5 | $6.25 | $10 | $0.50 | $25 |
| Claude Sonnet 5（至 2026-08-31 促销价） | **$2** | $2.50 | $4 | $0.20 | **$10** |
| Claude Sonnet 5（2026-09-01 起） | $3 | $3.75 | $6 | $0.30 | $15 |
| Claude Sonnet 4.6 / 4.5 | $3 | $3.75 | $6 | $0.30 | $15 |
| Claude Haiku 4.5 | $1 | $1.25 | $2 | $0.10 | $5 |

**OpenAI**（developers.openai.com/api/docs/pricing）

| 模型 | 输入 $/1M | 缓存输入 | 输出 $/1M |
|---|---|---|---|
| gpt-5.6-sol | $5.00 | $0.50 | **$30.00** |
| gpt-5.6-terra | $2.00 | $0.20 | $12.00 |
| gpt-5.6-luna | $0.20 | $0.02 | $1.20 |
| gpt-5.5 | $5.00 | $0.50 | $30.00 |
| gpt-5.4 | $2.50 | $0.25 | $15.00 |
| gpt-5.3-codex | $1.75 | $0.175 | $14.00 |
| gpt-5 | $1.25 | $0.125 | $10.00 |
| gpt-5-nano | $0.05 | $0.005 | $0.40 |
| gpt-5.5-cyber | $12.50 | $1.25 | $75.00 |

**DeepSeek 官方**（api-docs.deepseek.com/quick_start/pricing）

| 模型 | 上下文 | 最大输出 | 输入（缓存命中） | 输入（未命中） | 输出 |
|---|---|---|---|---|---|
| deepseek-v4-flash | 1M | 384K | $0.0028/1M | **$0.14/1M** | **$0.28/1M** |
| deepseek-v4-pro | 1M | 384K | $0.003625/1M | **$0.435/1M** | **$0.87/1M** |

官方原文：峰谷定价 —— "During **peak hours, prices will be 2x** the regular prices"，峰时为北京时间 **9:00–12:00 与 14:00–18:00**。上表为平时价。

**Together AI 开源权重托管**（together.ai/pricing）

| 模型 | 输入 $/1M | 输出 $/1M |
|---|---|---|
| **gpt-oss-120B** | **$0.15** | **$0.60** |
| MiniMax M3 | $0.30 | $1.20 |
| Kimi K2.6 | $1.20 | $4.50 |
| GLM-5.2 | $1.40 | $4.40 |
| Qwen3.5-397B-A17B | $0.60 | $3.60 |
| Qwen3.7-Max | $1.25 | $3.75 |
| DeepSeek V4 Pro | $1.74（缓存 $0.20） | $3.48 |
| Kimi K3 | $3.00 | $15.00 |
| Llama 3.3 70B | $1.04 | $1.04 |
| Qwen3.5 9B | $0.17 | $0.25 |
| Llama 3 8B Instruct Lite | $0.14 | $0.14 |

自建对照（Together 专用实例，[A]）：**NVIDIA HGX H100 $5.49/小时**，**HGX B200 $8.99/小时**。

### 6.2 倍数（由上表 [A] 数字直接相除，**推导**）

**输出 token 价倍数**（agent 场景对输出最敏感）：

| 对比对 | 计算 | **倍数** |
|---|---|---|
| Claude Fable 5 ÷ deepseek-v4-flash | 50 ÷ 0.28 | **178.6×** |
| Claude Opus 5 ÷ deepseek-v4-flash | 25 ÷ 0.28 | **89.3×** |
| gpt-5.6-sol ÷ gpt-oss-120B | 30 ÷ 0.60 | **50.0×** |
| Claude Opus 5 ÷ gpt-oss-120B | 25 ÷ 0.60 | **41.7×** |
| Claude Opus 5 ÷ deepseek-v4-pro（官方） | 25 ÷ 0.87 | **28.7×** |
| Claude Opus 5 ÷ Kimi K2.6 | 25 ÷ 4.50 | **5.6×** |
| Claude Opus 5 ÷ GLM-5.2 | 25 ÷ 4.40 | **5.7×** |

**输入 token 价倍数**：

| 对比对 | 计算 | **倍数** |
|---|---|---|
| Claude Opus 5 ÷ deepseek-v4-flash | 5 ÷ 0.14 | **35.7×** |
| Claude Opus 5 ÷ gpt-oss-120B | 5 ÷ 0.15 | **33.3×** |
| Claude Opus 5 ÷ deepseek-v4-pro | 5 ÷ 0.435 | **11.5×** |

**混合场景（更接近真实 coding agent：1M 输入 + 100k 输出，均未命中缓存）**：

| 模型 | 计算 | 单次成本 | 相对最便宜项 |
|---|---|---|---|
| Claude Fable 5 | 1×10 + 0.1×50 | **$15.00** | 89.3× |
| Claude Opus 5 | 1×5 + 0.1×25 | **$7.50** | 44.6× |
| gpt-5.6-sol | 1×5 + 0.1×30 | $8.00 | 47.6× |
| gpt-5.3-codex | 1×1.75 + 0.1×14 | $3.15 | 18.8× |
| Claude Sonnet 5（促销价） | 1×2 + 0.1×10 | $3.00 | 17.9× |
| GLM-5.2 (Together) | 1×1.40 + 0.1×4.40 | $1.84 | 11.0× |
| gpt-oss-120B (Together) | 1×0.15 + 0.1×0.60 | **$0.21** | 1.25× |
| deepseek-v4-flash（官方，平时） | 1×0.14 + 0.1×0.28 | **$0.168** | **1×（基准）** |

> **一句话卖点**：「同一个 1M-in / 100k-out 的任务，**Claude Fable 5 是 $15.00，DeepSeek V4 Flash 是 $0.168 —— 差 89 倍**。这就是为什么『重活用旗舰、量活用开源权重』不是省钱癖好，是数量级问题。」

### 6.3 别忽略的隐性变量（全 [A]）

| 变量 | 事实 | 影响 |
|---|---|---|
| **分词器变化** | Anthropic 官方："Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer... This tokenizer produces **approximately 30% more tokens for the same text**." | Opus 4.7+ 的**实际账单**要在标价上再乘约 1.3 |
| **Batch API** | Anthropic / OpenAI 均为 **50% 折扣**（Anthropic 原文："a 50% discount on both input and output tokens"） | 批量场景旗舰模型成本折半，上面的倍数相应减半 |
| **Prompt caching** | Anthropic：缓存命中 = **0.1× 基础输入价**；5m 写 1.25×、1h 写 2×。官方原文："caching pays off after just **one cache read** for the 5-minute duration, or after **two cache reads** for the 1-hour duration" | 重复上下文场景可把输入成本压到 1/10 |
| **DeepSeek 峰谷** | 峰时 **2×**（北京时间 9–12、14–18） | 批处理排到谷时可保住上表价格 |
| **数据驻留** | Anthropic：`inference_geo: "us"` 对 4.6+ 施加 **1.1× 倍率**；Bedrock/GCP 区域端点也是 **10% 溢价** | 私有化/合规诉求会额外加价 10% |
| **xAI 长上下文阶梯** | ≥200k 输入时单价 **翻倍** | Grok 长文场景成本非线性 |

---

## 7. 上下文窗口的边际收益：「窗口大 ≠ 用得好」

### 7.1 NoLiMa（arXiv 2502.05167）—— 本主题最锋利的数字 **[B]**

论文摘要原文（已抓取）：
> "We evaluate **13 popular LLMs** that claim to support contexts of **at least 128K tokens**. While they perform well in short contexts (<1K), performance degrades significantly as context length increases. **At 32K, for instance, 11 models drop below 50% of their strong short-length baselines.** Even GPT-4o, one of the top-performing exceptions, experiences a reduction from an almost-perfect baseline of **99.3% to 69.7%**."

| 数字 | 值 |
|---|---|
| 受测模型数（均宣称 ≥128K 上下文） | **13** |
| 在 **32K**（仅为宣称能力的 1/4）处跌破短上下文基线 **50%** 的模型数 | **11 / 13** |
| GPT-4o（表现最好的例外之一）：<1K → 32K | **99.3% → 69.7%**（−29.6pp） |

关键机制（原文）：NoLiMa 刻意让 needle 与问题**词面重叠最小化**，逼模型做潜在关联推理；作者归因于 "the increased difficulty the **attention mechanism** faces in longer contexts when literal matches are absent"。并且 "**Even models enhanced with reasoning capabilities or CoT prompting struggle** to maintain performance in long contexts."

> **一句话卖点**：「13 个宣称支持 128K 以上的模型，**在 32K —— 也就是它们宣称能力的四分之一处 —— 就有 11 个跌到短上下文基线的一半以下**。窗口标称值是营销数字，可用值是另一回事。」

### 7.2 Chroma《Context Rot》**[B]**（https://www.trychroma.com/research/context-rot）

| 项 | 值 / 原文 |
|---|---|
| 受测模型 | "We evaluate **18 LLMs**, including the state-of-the-art GPT-4.1, Claude 4, Gemini 2.5, and Qwen3 models." |
| NIAH 扩展设计 | **8 个输入长度 × 11 个 needle 位置** |
| 重复词任务的长度阶梯 | 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, **10000** 词 |
| **LongMemEval 关键对照** | 聚焦 prompt **≈ 300 tokens** vs 完整 prompt **≈ 113k tokens** —— "we see **significantly higher performance on focused prompts** compared to full prompts"（全体模型一致） |
| 干扰项效应 | "**Even a single distractor** reduces performance relative to the baseline (needle only)" |
| needle-问题相似度效应 | "performance degrades more quickly in input length with **lower similarity** needle-question pairs" |
| 行为崩坏起点 | Gemini 家族约 **500–750 词**开始生成随机词；Qwen3-8B 约 **5000 词** |
| 拒答率（说明实验干净） | **69 / 194,480 = 0.035%** |

⚠️ **重要诚实声明**：Chroma 报告的 LongMemEval 与重复词实验**主要以图表呈现，正文未给出配对的百分比数值**。因此**不要在 PPT 上写「300 tokens 得 X%、113k tokens 得 Y%」这种数字**——原文没有。可引用的是「≈300 tokens vs ≈113k tokens 的对照设计」+「全体模型一致地在聚焦 prompt 上显著更好」这一定性结论，以及 18 个模型、0.035% 拒答率这两个硬数字。

> **组合讲法**：「两份独立研究，一份 13 个模型（NoLiMa）、一份 18 个模型（Chroma），结论一致：**长上下文的失效不是在窗口边界发生的，是从很早就开始线性腐蚀的**。NoLiMa 给出了可上台的硬数字：32K 处 11/13 跌破半线。Chroma 给出了机制：**只要一个干扰项**就够了。」

### 7.3 对照：厂商侧的「窗口不加价」承诺 **[A]**

Anthropic 官方原文："Claude 4.6 and later models and Claude Mythos Preview include the full **1M token context window at standard pricing**. (A **900k-token request is billed at the same per-token rate as a 9k-token request**.)"

→ **成本上窗口是免费的，认知上窗口不是免费的**。这正是「上下文工程 / 检索 / 子代理扇出」存在的经济理由：不是为了省钱，是为了保住准确率。

---

## 8. 同一任务在不同模型上的成本差异（公开对比）

### 8.1 Aider Polyglot Benchmark —— 同一套题、同一个 harness、跨模型总花费

基准定义（[A]，aider.chat 官方榜）："**225 challenging Exercism coding exercises** across **C++, Go, Java, JavaScript, Python, and Rust**"。所有条目跑同一批 225 题。

| 模型 | 正确率 | **整轮总成本** | 每百分点成本 | 等级 |
|---|---|---|---|---|
| o3-pro (high) | 84.9% | **$146.32** | $1.72 | [B]⚠️ |
| **gpt-5 (high)** | **88.0%** | **$29.08** | $0.33 | [A] |
| gpt-5 (medium) | 86.7% | $17.69 | $0.20 | [A] |
| o3 (high) | 81.3% | $21.23 | $0.26 | [A] |
| DeepSeek-V3.2-Exp (Reasoner) | 74.2% | $1.30 | $0.018 | [A] |
| **DeepSeek-V3.2-Exp (Chat)** | **70.2%** | **$0.88** | **$0.013** | [A] |
| DeepSeek R1 (0528) | 71.4% | $4.80 | $0.067 | [A] |
| Kimi K2 | 59.1% | $1.24 | $0.021 | [A] |
| Qwen3 235B A22B | 59.6% | $0.00（本地/免费端点） | — | [A] |
| Qwen3 32B | 40.0% | $0.76 | $0.019 | [A] |

来源：https://aider.chat/docs/leaderboards/ 及原始数据文件 https://raw.githubusercontent.com/Aider-AI/aider/main/aider/website/_data/polyglot_leaderboard.yml

**最干净的可上台配对（两次独立抓取一致，标 [A]）**：

> **同一套 225 题：gpt-5 (high) 花 $29.08 拿 88.0%；DeepSeek-V3.2-Exp (Chat) 花 $0.88 拿 70.2%。**
> **成本差 33 倍，分数差 17.8 个百分点。**
> 换算：用 gpt-5 (high) 每多拿 1 个百分点，要多花 **$1.58**（(29.08−0.88) ÷ 17.8）。

⚠️ **数据不一致提示（必须在上台前复核）**：两次抓取该榜时，「pass_rate > 65% 区间内最贵条目」的口径不一致 —— 页面版返回 o3-pro (high) $146.32 / 84.9%，YAML 版返回 gpt-5 (high) $29.08 / 88.0%。**o3-pro 的 $146.32 标为 [B]⚠️，若要在 PPT 上用「166 倍成本差」这个更劲爆的数字，请务必先自己开一次 aider.chat/docs/leaderboards/ 核对 o3-pro 那一行。** 保守起见，建议台上只用已双重确认的 33 倍。

### 8.2 Anthropic 官方的「同成本比效果 / 同效果比成本」口径 **[A]**

Claude Opus 5 发布页（https://www.anthropic.com/news/claude-opus-5）原文：

| 评测 | 官方原文 |
|---|---|
| **CursorBench 3.2** | "at max effort, the model performs **within 0.5% of Fable 5's peak score, but at half the cost per task**" |
| **OSWorld 2.0** | "Opus 5 **outperforms every other model at any given cost**, surpassing Fable 5's best result at **just over a third of the cost**" |
| **Zapier AutomationBench** | "Opus 5's pass rate is **around 1.5× the next-best model for the same cost per task**" |
| **ARC-AGI 3** | "Opus 5's score is **three times as high as the next-best model**" |
| **Frontier-Bench v0.1** | "Opus 5 surpasses all other models, and **more than doubles Opus 4.8's performance at a lower cost**" |
| 定价 | "**$5 per million input tokens and $25 per million output tokens** (the same as Opus 4.8)" |
| Fast mode | "around **2.5 times the default speed**" at "**twice Opus 5's base price**"（即 $10/$50） |

> **演讲用法**：注意 Anthropic 官方现在**已经不报单一分数了，改报「成本-效果曲线」**（"outperforms every other model at any given cost"）。这本身就是一个可讲的行业信号：**2026 年比的不是分数，是每美元的分数。**
> ⚠️ 这些都是 Anthropic 自报的内部/合作方评测，**不是中立第三方**。台上请注明来源。

### 8.3 一个可直接算的运行时成本样例 **[A]**

Anthropic 官方 Managed Agents 计费示例（platform.claude.com 原文）：
一小时 Opus 5 编码 session，消耗 50,000 输入 + 15,000 输出：

| 项 | 计算 | 成本 |
|---|---|---|
| 输入 | 50,000 × $5 / 1,000,000 | $0.25 |
| 输出 | 15,000 × $25 / 1,000,000 | $0.375 |
| Session runtime | 1.0 小时 × **$0.08/session-hour** | $0.08 |
| **合计** | | **$0.705** |

开启 prompt caching 后（其中 40,000 输入为缓存命中）→ **$0.525**（降 25.5%）。

其他运行时价格（[A]）：Code execution 每组织每月 **1,550 免费小时**，超出 **$0.05/小时/容器**；Web fetch **不额外收费**；Web search **$10/1,000 次**。

---

## 9. 一页 PPT 直接可用的「五个最硬数字」

| # | 数字 | 支撑主张 | 等级 | URL |
|---|---|---|---|---|
| 1 | **15× token 换 +90.2%** —— 多智能体比单智能体多用约 15 倍 token，在 Anthropic 内部 research eval 上高出 90.2%；且 **token 用量本身解释了 BrowseComp 上 80% 的表现方差** | 子代理扇出 | [A] | https://www.anthropic.com/engineering/multi-agent-research-system |
| 2 | **32K 处 11/13 跌破半线** —— 13 个宣称 ≥128K 上下文的模型，在 32K 时 11 个跌到短上下文基线 50% 以下；GPT-4o 从 99.3% → 69.7% | 窗口大 ≠ 用得好 | [B] | https://arxiv.org/abs/2502.05167 |
| 3 | **同模型换 harness 差 18.4pp** —— Terminal-Bench 2.0 上 Claude Opus 4.6：Meta-Harness 76.4% / Terminus 2 62.9% / Claude Code 58.0% | 闭环脚手架是独立变量 | [A] | https://www.tbench.ai/leaderboard/terminal-bench/2.0 |
| 4 | **同任务成本差 33 倍** —— Aider Polyglot 同一套 225 题：gpt-5 (high) $29.08 / 88.0% vs DeepSeek-V3.2-Exp (Chat) $0.88 / 70.2%（每多 1pp 需多花 $1.58） | 批量用开源权重 | [A] | https://aider.chat/docs/leaderboards/ |
| 5 | **输出 token 价差 89 倍** —— Claude Opus 5 $25/MTok vs DeepSeek V4 Flash $0.28/MTok（官方定价页直接相除；对 Fable 5 的 $50 则为 **178.6 倍**） | 私有化/批量的经济性 | [A] | https://platform.claude.com/docs/en/about-claude/pricing + https://api-docs.deepseek.com/quick_start/pricing |

**备选第 6 个（幻觉率，若需要 Notebook 的支撑）**：NotebookLM **13%** vs Gemini/ChatGPT **约 40%**（300 篇 TikTok 诉讼文档语料，全体平均 30%）—— [B]，https://arxiv.org/abs/2509.25498

---

## 10. 未获证实清单（**上台绝不能编的部分**）

| 想要的数字 | 状态与原因 |
|---|---|
| Codex 云端**并发任务上限** | **未获证实**。官方三页文档均无数值；help.openai.com、openai.com/index/introducing-codex/ 返回 403 |
| Codex 云端**单任务时长上限 / 超时** | **未获证实**。唯一相关官方数字是「容器状态缓存 up to 12 hours」，那不是任务时长 |
| Codex 云端**沙箱 CPU / RAM / 磁盘规格** | **未获证实** |
| 「Codex 任务典型耗时 1–30 分钟」 | **未获证实** —— 本次未抓到任何官方页含此表述。**请勿引用。** |
| Grok / X Search 的**索引延迟或新鲜度 SLA** | **未获证实**。docs.x.ai 只有 "real-time" 的定性表述，无任何秒/分钟级指标 |
| Gemini Notebook 的**引用准确率（citation accuracy）百分比** | **未获证实**。Google 官方 FAQ 只有定性；ACM 论文 10.1145/3711670.3764628 返回 403 未能核对 |
| Chroma Context Rot 报告中 LongMemEval「聚焦 vs 完整 prompt」的**配对百分比** | **不存在于原文**。报告以图表呈现，正文未给数值。只能引用「≈300 tokens vs ≈113k tokens」的实验设计与「全体模型一致更优」的定性结论 |
| Claude Opus 5 在 SWE-bench Verified / Terminal-Bench 的**官方分数** | **未获证实**。Opus 5 发布页只报 Frontier-Bench v0.1、CursorBench 3.2、ARC-AGI 3、Zapier AutomationBench、OSWorld 2.0 五项，且多为「相对/成本比」表述，无绝对 SWE-bench 数字 |
| SWE-bench 的 FAIL_TO_PASS / PASS_TO_PASS **官方文字定义** | 官方评测指南页未给出（在 harness reference 与论文中）。本文件未引用该口径 |

### [C] 隔离区 —— **不要放进 PPT，仅供你自己做背景判断**

以下条目仅通过搜索摘要见到，**未亲自打开原文核对**，或来自非权威站点：

| 内容 | 出处 | 为什么是 [C] |
|---|---|---|
| 「前沿 agent 在每个任务上平均执行测试 **8.8 次**；分析了 7,745 条 SWE-bench Verified agent traces + 3,000 次受控修复尝试」 | agentpatterns.ai/verification/execution-budgeting-program-repair/ | 非机构官方站，未打开原文，方法学不明 |
| 「SWE-bench 初始 RAG 基线 **1.96%** → SWE-agent **12.47%**」 | 搜索摘要，未核对原始论文 | 数字很可能正确（属 2023–2024 经典结果），但**本次未亲自抓到原文**，故不升级 |
| 「Claude Opus 4.5 在 SWE-bench Verified 拿 **80.9%**」 | programminghelper / codesota 等聚合站 | 纯聚合站；Anthropic 官方页未复核到 |
| 「Claude Opus 5 在 SWE-bench Pro **79.2%**」/「Opus 4.8 在 SWE-Bench Pro **69.2%**」 | codingfleet / aitoolsrecap | 纯聚合站 |
| 「NotebookLM 免费档 3–5 次 Audio Overview/天」 | superlore（经 DDG 摘要） | 与官方数字（Standard **3**/天）冲突，以官方为准 |
| Vectara HHEM 幻觉排行榜的**逐行分数**（如 gemini-2.5-pro 7.0%、claude-sonnet-4 10.3%） | github.com/vectara/hallucination-leaderboard（榜单本身权威，但本次抓取经摘要模型转述，逐行数值未逐一目视核对） | 榜单可信但**本次提取路径不可靠**；若要用，请自己打开 README 核对目标行 |

---

## 11. 汇总：主张 → 证据强度速查

| # | 用法主张 | 证据强度 | 可上台的最强一句 |
|---|---|---|---|
| 1 | 深度重构用 Claude Code（闭环价值） | **强（[A]+[B]）** | 同模型换 harness 差 18.4pp；SWE-bench 500 题必须在 Docker 里真跑测试才计分；执行验证式多代理在 SWE-bench Lite 比单代理高 26–28pp |
| 2 | 长时并行/批量 PR 用 Codex 云端 | **弱（能力 [A]，数字缺失）** | 官方明写 "Run tasks in parallel"、容器缓存 12 小时、配额按 5 小时窗口；**并发上限与单任务时长上限官方无公开数字** |
| 3 | 跨仓库检索用子代理扇出 | **最强（全 [A] 官方口径）** | 15× token → +90.2%；扇出宽度 3–5；token 用量单独解释 80% 方差 |
| 4 | 长文档消化用 Gemini Notebook | **中（容量 [A]，幻觉 [B]，引用准确率缺失）** | Pro 档 300 sources × 50 万词 ≈ 比 1M 窗口大两个数量级；幻觉率 13% vs 通用模型约 40%（单一语料） |
| 5 | 实时舆情用 Grok | **中（能力+价格 [A]，时效性无数字）** | X Search 原生支持 from_date/to_date + 20 个账号白名单，$5/千次；**新鲜度 SLA 未公开** |
| 6 | 批量/私有化用开源权重 | **强（全 [A] 官方定价，倍数为直接推导）** | 1M-in/100k-out 同一任务：Fable 5 $15.00 vs DeepSeek V4 Flash $0.168 → **89 倍** |
| 7 | 上下文窗口的边际收益 | **强（[B] 双实证）** | 32K 处 11/13 模型跌破短上下文基线的一半；GPT-4o 99.3%→69.7% |
| 8 | 跨模型同任务成本对比 | **强（[A]）** | Aider Polyglot 同 225 题：$29.08/88.0% vs $0.88/70.2% → 33 倍成本换 17.8pp |

---

## 附录：本次全部已抓取来源 URL

**[A] 官方源**
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/news/claude-opus-5
- https://platform.claude.com/docs/en/about-claude/pricing
- https://developers.openai.com/api/docs/pricing
- https://learn.chatgpt.com/docs/cloud
- https://learn.chatgpt.com/docs/environments/cloud-environment
- https://learn.chatgpt.com/docs/pricing
- https://docs.x.ai/developers/pricing
- https://docs.x.ai/developers/tools/x-search
- https://docs.x.ai/developers/tools/web-search
- https://api-docs.deepseek.com/quick_start/pricing
- https://www.together.ai/pricing
- https://www.tbench.ai/leaderboard/terminal-bench/2.0
- https://www.swebench.com/SWE-bench/
- https://www.swebench.com/SWE-bench/guides/evaluation/
- https://swe-agent.com/latest/
- https://aider.chat/docs/leaderboards/ ＋ https://raw.githubusercontent.com/Aider-AI/aider/main/aider/website/_data/polyglot_leaderboard.yml
- https://support.google.com/gemininotebook/answer/16213268?hl=en
- https://support.google.com/notebooklm/answer/16269187?hl=en

**[B] 权威二手 / 论文**
- https://arxiv.org/abs/2502.05167 （NoLiMa）
- https://arxiv.org/abs/2604.13120 （AgentForge）
- https://arxiv.org/abs/2509.25498 （Not Wrong, But Untrue）
- https://www.trychroma.com/research/context-rot
- https://github.com/vectara/hallucination-leaderboard （榜单权威，本次提取路径不可靠，见 §10）

**抓取失败（403/404，相关数字已标未获证实）**
- https://openai.com/index/introducing-codex/ （403）
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan （403）
- https://dl.acm.org/doi/10.1145/3711670.3764628 （403）
- https://docs.x.ai/docs/guides/live-search （404，已由 /developers/tools/* 替代）
