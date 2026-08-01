# M01：Anthropic 模型线（2026-08-01 快照）

> 采集时间：2026-08-01。所有数字均为当场抓取，每条标注可信度等级与来源 URL。
> **[A]** 厂商官方页，已亲自抓取核对 ｜ **[B]** 权威二手，已抓取 ｜ **[C]** 仅见于聚合站/内容农场
> 本轮采集**全部来源均为 Anthropic 自有域名**（anthropic.com / claude.com / platform.claude.com / code.claude.com），因此绝大多数条目为 [A]。
> ⚠️ 抓取管道说明：news 类页面（anthropic.com/news/*）由抓取工具做了一次文本转换，正文数字已尽量还原为原句引用；凡两次抓取结果不一致的，一律标为「存疑」而非 [A]。

---

## 0. 一句话结论（给台上用）

2026-08-01 当天，Anthropic 在售模型是 **4 个梯队 + 1 个受限梯队**：
Fable 5（最强、$10/$50）→ Opus 5（主力、$5/$25）→ Sonnet 5（$2/$10 促销中）→ Haiku 4.5（$1/$5）；
Mythos 5 为 Project Glasswing 邀请制限量供应，**不对外自助开通**。

---

## 1. 当前在售模型总表

| 模型 | API model ID | 发布日 | 上下文（输入） | 最大输出 | 输入 $/MTok | 输出 $/MTok | 等级 |
|---|---|---|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | 2026-06-09 | 1M tokens | 128k | **$10** | **$50** | [A] |
| Claude Mythos 5（限量） | `claude-mythos-5` | 2026-06-09 | 1M tokens | 128k | **$10** | **$50** | [A] |
| Claude Opus 5 | `claude-opus-5` | 2026-07-24 | 1M tokens | 128k | **$5** | **$25** | [A] |
| Claude Sonnet 5 | `claude-sonnet-5` | 2026-06-30 | 1M tokens | 128k | **$2**（促销，至 2026-08-31）/ $3（9-1 起） | **$10**（促销）/ $15 | [A] |
| Claude Haiku 4.5 | `claude-haiku-4-5`（全 ID `claude-haiku-4-5-20251001`） | 2025-10-01（由 ID 日期推断） | 200k tokens | 64k | **$1** | **$5** | [A]（发布日为 ID 推断） |

来源：
- 规格/ID/上下文/输出：<https://platform.claude.com/docs/en/about-claude/models/overview.md> [A]
- 全量价格表：<https://platform.claude.com/docs/en/about-claude/pricing.md> [A]
- Fable 5 / Mythos 5 发布日与规格：<https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5.md> [A]
- Opus 5 发布日：<https://www.anthropic.com/news/claude-opus-5>（"Jul 24, 2026"，与 news 首页列表一致）[A]
- Sonnet 5 发布日：<https://www.anthropic.com/news/claude-sonnet-5>（"June 30, 2026"）[A]

### 1.1 补充：Batch API 下的输出上限
> "On the Message Batches API, Claude Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5, and Sonnet 4.6 support up to **300k output tokens** by using the `output-300k-2026-03-24` beta header."
[A] <https://platform.claude.com/docs/en/about-claude/models/overview.md>

### 1.2 补充：knowledge cutoff（可上台的冷知识）

| 模型 | Reliable knowledge cutoff | Training data cutoff | 等级 |
|---|---|---|---|
| Fable 5 | Jan 2026 | Jan 2026 | [A] |
| Opus 5 | **May 2026** | May 2026 | [A] |
| Sonnet 5 | Jan 2026 | Jan 2026 | [A] |
| Haiku 4.5 | Feb 2025 | Jul 2025 | [A] |

来源同 overview.md [A]。注意 Opus 5 的 cutoff（May 2026）比 Fable 5（Jan 2026）更新——这是**新模型不一定 cutoff 更早**的反直觉点。

---

## 2. Prompt caching：支持情况与折扣

**结论：所有 active 模型全部支持 prompt caching（automatic + explicit）。** [A]

### 2.1 折扣倍率（相对 base input price）

| 缓存操作 | 倍率 | 有效期 | 等级 |
|---|---|---|---|
| 5-minute cache write | **1.25x** base input | 5 分钟 | [A] |
| 1-hour cache write | **2x** base input | 1 小时 | [A] |
| Cache read（命中）| **0.1x** base input | 同上一次写入 | [A] |

> 官方原话："A cache hit costs **10% of the standard input price**, which means caching pays off after just one cache read for the 5-minute duration (1.25x write), or after two cache reads for the 1-hour duration (2x write)." [A]
> 来源：<https://platform.claude.com/docs/en/about-claude/pricing.md>

### 2.2 每模型缓存单价（$/MTok，绝对值）

| 模型 | Base Input | 5m Cache Write | 1h Cache Write | Cache Hit | Output | 等级 |
|---|---|---|---|---|---|---|
| Fable 5 / Mythos 5 | $10 | $12.50 | $20 | $1 | $50 | [A] |
| Opus 5 | $5 | $6.25 | $10 | $0.50 | $25 | [A] |
| Opus 4.8 / 4.7 / 4.6 / 4.5 | $5 | $6.25 | $10 | $0.50 | $25 | [A] |
| Sonnet 5（促销至 8-31）| $2 | $2.50 | $4 | $0.20 | $10 | [A] |
| Sonnet 5（9-1 起）| $3 | $3.75 | $6 | $0.30 | $15 | [A] |
| Sonnet 4.6 / 4.5 | $3 | $3.75 | $6 | $0.30 | $15 | [A] |
| Haiku 4.5 | $1 | $1.25 | $2 | $0.10 | $5 | [A] |
| Opus 4.1（deprecated）| $15 | $18.75 | $30 | $1.50 | $75 | [A] |

来源：<https://platform.claude.com/docs/en/about-claude/pricing.md> [A]

### 2.3 最小可缓存前缀长度（非常反直觉，不单调）

| 模型 | 最小可缓存 tokens | 等级 |
|---|---|---|
| **Opus 5 / Fable 5 / Mythos 5** | **512** | [A] |
| Opus 4.8 / Sonnet 5 / Sonnet 4.6 / Sonnet 4.5 / Opus 4.1 / Sonnet 4 | 1,024 | [A] |
| Mythos Preview / **Opus 4.7** | **2,048** | [A] |
| Haiku 3.5 | 2,048 | [A] |
| **Opus 4.6 / Opus 4.5 / Haiku 4.5** | **4,096** | [A] |

来源：<https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md> [A]
> 讲台看点：Opus 4.6 → 4.7 → 4.8 → 5 的最小值是 4096 → 2048 → 1024 → **512**，逐代减半但中间并不单调（Haiku 4.5 反而是最高的 4096）。低于阈值**不会报错**，只是静默不缓存（`cache_creation_input_tokens` 与 `cache_read_input_tokens` 都为 0）。[A]

---

## 3. 思考 / 推理档位控制（每模型差异）

| 模型 | Extended thinking（`thinking.type:"enabled"` + `budget_tokens`）| Adaptive thinking | effort 档位 | 默认 effort | 等级 |
|---|---|---|---|---|---|
| Fable 5 / Mythos 5 | **No** | **Yes（always on，不可关）** | low / medium / high / xhigh / max | high | [A] |
| Opus 5 | **No** | Yes | low / medium / high / xhigh / max | high | [A] |
| Sonnet 5 | **No** | Yes | low / medium / high / xhigh / max | high | [A] |
| Haiku 4.5 | **Yes** | **No** | **不支持 effort** | — | [A] |
| Opus 4.8 / 4.7 | No | Yes | low…max（含 xhigh）| high（API）| [A] |
| Opus 4.6 / Sonnet 4.6 | Yes（deprecated）| Yes | low / medium / high / max（**无 xhigh**）| high | [A] |

来源：
- 每模型 thinking 支持：<https://platform.claude.com/docs/en/about-claude/models/overview.md> [A]
- effort 档位与支持模型清单：<https://platform.claude.com/docs/en/build-with-claude/effort.md> [A]
- Fable 5 thinking 恒开：<https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5.md> [A]

### 3.1 硬约束（会 400 的）
- Fable 5 / Mythos 5：`thinking: {"type":"disabled"}` **不支持** [A]
- Opus 5：在 `xhigh` 或 `max` effort 下设 `thinking:{"type":"disabled"}` **返回 400**
  > 原话："On Claude Opus 5, thinking cannot be disabled at `xhigh` or `max` effort: requests that set `thinking: {"type": "disabled"}` at those levels return a 400 error." [A] <https://platform.claude.com/docs/en/build-with-claude/effort.md>
- `temperature` / `top_p` / `top_k`：**Claude Opus 4.7 及以后模型**设为非默认值返回 400
  [A] <https://platform.claude.com/docs/en/about-claude/model-deprecations.md>

### 3.2 官方推荐档位（原话）
- Opus 5："**Start with `high`, the default**, and adjust based on your evals: step up to `xhigh` for demanding coding and agentic work, or to `max` when a task justifies unconstrained token spending, and use `low` and `medium` liberally as your primary control for token cost and response time wherever your evals show quality holds." [A]
- Opus 5 额外提醒："Effort controls thinking volume, not visible response length: on Claude Opus 5, changing effort does not reliably shorten responses, so prompt for length instead." [A]
- Fable 5："Effort is the primary control for trading off intelligence, latency, and cost on Claude Fable 5. **Start with `high`, the default, for most tasks**… Lower effort settings on Claude Fable 5 still perform well and often exceed `xhigh` performance on prior models." [A]
- Sonnet 5："Claude Sonnet 5 defaults to `high` effort on the Claude API and Claude Code."；"Medium effort: Cost-saving step-down from the default. **Comparable to Claude Sonnet 4.6 at high effort.**" [A]
- Opus 4.7/4.8："**Start with `xhigh` for coding and agentic use cases**, and use `high` as the minimum for most intelligence-sensitive workloads." [A]

来源均为 <https://platform.claude.com/docs/en/build-with-claude/effort.md> [A]

---

## 4. 官方对每个模型「适合干什么」的原话

| 模型 | 官方原文（英文，来自 models overview 的 Description 栏）| 等级 |
|---|---|---|
| Claude Fable 5 | "Next-generation intelligence for **long-running agents**" | [A] |
| Claude Opus 5 | "For **complex agentic coding and enterprise work**" | [A] |
| Claude Sonnet 5 | "The best combination of **speed and intelligence**" | [A] |
| Claude Haiku 4.5 | "The **fastest** model with **near-frontier intelligence**" | [A] |

来源：<https://platform.claude.com/docs/en/about-claude/models/overview.md> [A]

补充原话（来自 news / docs 正文）：
- Fable 5："Claude Fable 5 is Anthropic's **most capable widely released model**, built for the most demanding reasoning and long-horizon agentic work." [A] <https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5.md>
- Opus 5："Opus 5 is designed to be **used every day**: it works more efficiently than other models." [A] <https://www.anthropic.com/news/claude-opus-5>
- Opus 5（news 首页摘要）："Opus 5 is a step change improvement for the Opus tier powering long-running agents while delivering improvements in coding and professional work." [A] <https://www.anthropic.com/news>
- Opus 5（订阅侧定位）："It's the **new default model on Claude Max**, and the **strongest model on Claude Pro**." [A] <https://www.anthropic.com/news/claude-opus-5>
- Sonnet 5："Claude Sonnet 5 is built to be **the most agentic Sonnet model yet**. It can make plans, use tools like browsers and terminals, and run autonomously at a level that, just a few months ago, required larger and more expensive models." [A] <https://www.anthropic.com/news/claude-sonnet-5>
- Fable 5 在 Claude Code 中的定位："Claude Fable 5 is the most capable model in Claude Code, **suited to tasks larger than a single sitting**. It sustains long autonomous sessions, investigates before acting, and verifies its work more often than smaller models." [A] <https://code.claude.com/docs/en/model-config>

---

## 5. Benchmark：官方公布了什么，以及**没**公布什么

### 5.1 ⚠️ 最重要的一条发现

**Anthropic 官方 Opus 5 与 Sonnet 5 的发布文中，均未出现 "SWE-bench Verified" 或 "Terminal-Bench"。** [A]
- Opus 5 页：抓取全文列举 benchmark，未见 SWE-bench / Terminal-Bench。<https://www.anthropic.com/news/claude-opus-5>
- Sonnet 5 页：明确核对「Does the page mention SWE-bench Verified or Terminal-Bench at all?」→ **"The page does not mention SWE-bench Verified or Terminal-Bench."** <https://www.anthropic.com/news/claude-sonnet-5>

→ **台上不要再拿 SWE-bench Verified 讲 Opus 5 / Sonnet 5**，官方已经换了一套 benchmark 叙事（Frontier-Bench、CursorBench、AutomationBench、OSWorld 2.0、ARC-AGI 3 等）。任何流传的 Opus 5 SWE-bench 分数都不是 Anthropic 官方口径。

### 5.2 Claude Opus 5 官方 benchmark（正文 vs 仅图表）

| Benchmark | 官方正文给的数值 | 是否只在图表 | 等级 |
|---|---|---|---|
| **Frontier-Bench v0.1** | 正文只给相对表述："Opus 5 surpasses all other models, and **more than doubles Opus 4.8's performance** at a lower cost per task." | 绝对分数仅在图表 | [A] |
| **CursorBench 3.2** | "at max effort, the model performs **within 0.5% of Fable 5's peak score**, but at **half the cost per task**" | 绝对分数仅在图表 | [A] |
| **ARC-AGI 3** | "Opus 5's score is **three times as high as the next-best model**." | 绝对分数仅在图表 | [A] |
| **Zapier AutomationBench** | "Opus 5's pass rate is **around 1.5× the next-best model** for the same cost per task." | 绝对分数仅在图表 | [A] |
| **OSWorld 2.0** | "Opus 5 outperforms every other model at any given cost, surpassing Fable 5's best result at **just over a third of the cost**." | 绝对分数仅在图表 | [A] |
| 内部 Life Sciences — 有机化学 | "it scores **10.2 percentage points higher than Opus 4.8** on our internal benchmark" | 正文给了差值，无绝对分 | [A] |
| 内部 Life Sciences — 蛋白质任务 | "it scores **7.7 percentage points higher**"（vs Opus 4.8） | 正文给了差值，无绝对分 | [A] |
| OSS-Fuzz（漏洞识别 / 利用开发） | 无数字，仅定性："exploit development 上 considerably less successful than Mythos 5" | 图表 | [A] |
| AA Coding Agent Index / GDPval-AA v2 / HLE / DeepSearchQA | 无正文数值 | **仅图表** | [A] |

来源：<https://www.anthropic.com/news/claude-opus-5> [A]

> **可直接上台的判断**：Opus 5 发布文**几乎全部用相对表述**（"three times"、"1.5×"、"more than doubles"、"10.2 percentage points"），绝对分数只落在图表里。这是一次明显的叙事转向：**从"分数榜"转到"同等成本下的能力/成本曲线"**。多处强调 cost per task（"at half the cost per task"、"just over a third of the cost"）。

### 5.3 Claude Sonnet 5 官方 benchmark

| Benchmark | 数值 | 等级 |
|---|---|---|
| Humanity's Last Exam (HLE) | 34.6%（no tools）/ 46.8%（with tools） | **存疑，勿直接上台** |
| OSWorld-Verified | 78.5% | **存疑，勿直接上台** |
| Firefox exploit development | 两代 Sonnet 均为 **0.0%** working exploits | [A] |
| BrowseComp | 仅图表，无正文数值 | [A] |

⚠️ **存疑原因（必须记录）**：对同一 URL 的两次独立抓取，对 HLE 数值的归属给出了**互相矛盾**的答案——第一次称 34.6%/46.8% 属于 Sonnet 5，第二次称 46.8% 是 Sonnet 5、而 34.6%/46.8% 是"Sonnet 4.6 updated"。在人工打开原页面确认前，**这两个数字按未获证实处理**。
OSWorld-Verified 78.5% 同样只出现在第一次抓取中，第二次抓取称正文无数值 → 一并存疑。
来源：<https://www.anthropic.com/news/claude-sonnet-5>

官方正文可用的原话（无歧义）：
> "Neither of the Sonnet models could successfully develop a working exploit (both scored **0.0%**)." [A]
> "We have now updated the chart so that it matches the methodology that we used… with a **10M token budget**." [A]

### 5.4 Claude Fable 5 的官方发布文
**未能定位到 URL。** 尝试过 `/news/claude-fable-5`、`/news/introducing-claude-fable-5`、`/news/claude-fable-5-and-claude-mythos-5`，**均返回 404**。
anthropic.com/news 首页列表中也未出现 Fable 5 的发布条目（最近条目里只有 6-30 的 "Redeploying Fable 5"）。
→ Fable 5 的能力/benchmark 数字**本轮未获证实**；技术规格以 platform docs 的 "Introducing Claude Fable 5 and Claude Mythos 5" 页为准（该页只有规格与 API 变更，**没有任何 benchmark 数字**）[A]。

---

## 6. Mythos-class 的当前状态（2026-08-01）

| 项目 | 状态 | 等级 |
|---|---|---|
| `claude-mythos-preview` | **已 deprecated**，官方要求迁移到 `claude-mythos-5` | [A] |
| `claude-mythos-5` | **Active，但非公开可用**：limited availability，仅 Project Glasswing 已批准客户 | [A] |
| 开通方式 | "**Access is invitation-only and there is no self-serve sign-up.**" 需联系 Anthropic / AWS / Google Cloud 客户团队 | [A] |
| 规格 | 与 Fable 5 完全相同：1M 上下文、128k 输出、$10/$50 | [A] |
| 关键差异 | **Mythos 5 不带 safety classifiers；Fable 5 带**。官方原文："Claude Mythos 5 shares Claude Fable 5's capabilities **without the safety classifiers**." | [A] |
| 定位 | "offered separately for **defensive cybersecurity workflows** as part of Project Glasswing" | [A] |
| 数据留存 | Fable 5 / Mythos 5 均需 **30 天数据留存**，**不支持 zero data retention**（属 Covered Models） | [A] |

来源：
- <https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5.md> [A]
- <https://platform.claude.com/docs/en/about-claude/models/overview.md> [A]
- <https://platform.claude.com/docs/en/about-claude/model-deprecations.md> [A]

### 6.1 Fable 5 的出口管制中断事件（讲台强故事）

| 日期 | 事件 | 等级 |
|---|---|---|
| 2026-06-09 | Fable 5 与 Mythos 5 发布 | [A] |
| 2026-06-12 | **美国政府对该模型实施出口管制**，Anthropic 对**所有用户**暂停访问（理由：无法实时核验国籍——"had no reliable way to verify nationality in real-time"） | [A] |
| 2026-06-30 | 出口管制解除 | [A] |
| 2026-07-01 | 全球恢复可用（Claude Platform / Claude.ai / Claude Code / Claude Cowork） | [A] |
| 2026-07-01 ~ 07-07 | 过渡期：Pro / Max / Team / 部分 Enterprise 计划内含 Fable 5，**上限为每周用量的 50%**；此后需 usage credits | [A] |

触发原因：亚马逊研究人员报告的一个 jailbreak——在特定提示下模型可识别软件漏洞。[A]
来源：<https://www.anthropic.com/news/redeploying-fable-5>

---

## 7. 已下线 / 已改名 / 即将退役

### 7.1 ⚠️ 4 天后就要退役的模型
**`claude-opus-4-1-20250805`（Claude Opus 4.1）：2026-06-05 deprecated，2026-08-05 退役。** 推荐替换：`claude-opus-4-8`。 [A]
（本笔记采集日 2026-08-01，距退役仅 4 天。）

### 7.2 已退役（请求会失败）

| 模型 | 退役日 | 官方推荐替换 | 等级 |
|---|---|---|---|
| `claude-opus-4-20250514` | 2026-06-15 | `claude-opus-4-8` | [A] |
| `claude-sonnet-4-20250514` | 2026-06-15 | `claude-sonnet-4-6` | [A] |
| `claude-3-haiku-20240307` | 2026-04-20 | `claude-haiku-4-5-20251001` | [A] |
| `claude-3-7-sonnet-20250219` | 2026-02-19 | `claude-sonnet-4-6` | [A] |
| `claude-3-5-haiku-20241022` | 2026-02-19 | `claude-haiku-4-5-20251001` | [A] |
| `claude-3-opus-20240229` | 2026-01-05 | `claude-opus-4-8` | [A] |
| `claude-3-5-sonnet-2024xxxx`（两个快照）| 2025-10-28 | `claude-sonnet-4-6` | [A] |

### 7.3 命名规则变化（会讲错的地方）
> "Every Claude model ID is a pinned snapshot. Models with a date in the ID (for example, `20250929`) are fixed to that specific release. **Starting with the Claude 4.6 generation, model IDs use a dateless format that is also a pinned snapshot, not an evergreen pointer.**" [A]
→ `claude-opus-5` 不是"永远指向最新 Opus"的别名，它就是一个固定快照。[A]
来源：<https://platform.claude.com/docs/en/about-claude/models/overview.md>

### 7.4 关于"改名"
- 没有发现任何当前模型被改名。
- **Haiku 没有 5 代**：截至 2026-08-01，Haiku 线最新仍是 **Haiku 4.5**（2025-10-01），已快一年没更新。[A]
- 各在售模型的 tentative retirement date（"not sooner than"）：Fable 5 → 2027-06-09；Opus 5 → 2027-07-24；Sonnet 5 → 2027-06-30；Opus 4.8 → 2027-05-28；Opus 4.7 → 2027-04-16；Opus 4.6 → 2027-02-05；Sonnet 4.6 → 2027-02-17；Haiku 4.5 → 2026-10-15。[A]
  （反推发布日：Opus 4.8 ≈ 2026-05-28、Opus 4.7 ≈ 2026-04-16、Opus 4.6 ≈ 2026-02-05、Sonnet 4.6 ≈ 2026-02-17 —— **此为推断，非官方明示**。）
来源：<https://platform.claude.com/docs/en/about-claude/model-deprecations.md> [A]

---

## 8. Claude Code 的订阅档位与价格

### 8.1 价格表（来自 claude.com/pricing，逐条原文）

| 档位 | 价格（原文） | 含 Claude Code | 等级 |
|---|---|---|---|
| Free | "$0" | 否（"Includes Claude Code" 出现在 Pro 档）| [A] |
| **Pro** | "**$17** Per month with annual subscription discount (**$200 billed up front**). **$20** if billed monthly." | 是（"Includes Claude Code"）| [A] |
| **Max（5x / 20x）** | "**From $100** Per month" ｜ 档位说明："**Choose 5x or 20x more usage than Pro**" | 是 | [A] |
| Team — Standard seat | "**$20** Per seat / month if billed annually. **$25** if billed monthly." | 是（"Includes Claude Code and Claude Cowork"）| [A] |
| Team — Premium seat | "**$100** Per seat / month if billed annually. **$125** if billed monthly." | 是 | [A] |
| Enterprise（self-serve）| "$20/seat. Usage cost scales with model and task." | 是 | [A] |
| Enterprise（sales-assisted）| 自定义，需联系销售 | 是 | [A] |

⚠️ **未获证实**：Max 20x 的确切月费。claude.com/pricing 页面在三次抓取中**只暴露 "From $100 / Per month"** 这一个数字，未分别列出 5x 与 20x 的价格（页面上应为交互式切换，静态抓取取不到）。**台上只说「Max 起价 $100/月，可选 5x 或 20x」，不要报 20x 的具体数字。**

各档位功能原文（claude.com/pricing）[A]：
- Free："Chat on web, iOS, Android, and on your desktop"；"Generate code and visualize data"
- Pro："More usage"；"Includes Claude Code"；"Ability to use more Claude models"
- Max："Choose 5x or 20x more usage than Pro"；"Higher output limits for all tasks"
- Team："All Claude features, plus more usage than Pro"；"Includes Claude Code and Claude Cowork"

来源：<https://claude.com/pricing> [A]

### 8.2 各档的用量口径（关键）

**口径 = 两个滚动窗口，不是「多少条消息」**：
> "each member's Claude Code usage draws from a per-seat allowance that resets on a **rolling five-hour window and a weekly window**. The allowance is **shared with Claude chat and Cowork**, and its size depends on the member's seat tier (Standard or Premium)." [A]
> 来源：<https://code.claude.com/docs/en/costs>

其他确证的口径细节 [A]（同上 URL）：
- 三种触发信息各不相同：
  - "You've hit your **session limit**" / "You've hit your **weekly limit**" → 订阅计划的座位用量窗口，**跨所有模型共享**，`/model` 换模型**不会**恢复访问（但能绕过 "You've hit your **Opus limit**" 这一模型级提示继续工作）
  - context / auto-compact 警告 → **不是**用量限制
  - API / 云厂商计划上的异常花费 → 通常是长会话未 `/clear`，或把 Opus 留作默认模型
- 超出座位额度后：开启 **usage credits** 才能继续（`/usage-credits` 命令）
- Team/Enterprise 的座位额度内用量**不按美元计量**（"Usage inside the seat allowance isn't metered in dollars."）
- 缓存生命周期与档位挂钩："The lifetime is **an hour on a subscription** and drops to **five minutes** once you're drawing on usage credits; on an API key or cloud provider, it's five minutes by default."

### 8.3 各档的默认模型（2026-08-01）

| 账户类型 | Claude Code 的 `default` 解析到 | 等级 |
|---|---|---|
| **Max / Team Premium / Enterprise pay-as-you-go / Anthropic API** | **Opus 5** | [A] |
| Claude Platform on AWS / Amazon Bedrock / Google Cloud Agent Platform | Opus 5 | [A] |
| **Pro / Team Standard / Enterprise 订阅座位** | **Sonnet 5** | [A] |
| Microsoft Foundry | Sonnet 4.5 | [A] |

> "**Fable 5 is not the default model on any account type.**" 需 `/model fable`、`model` 设置或 `best` 别名主动选择。[A]
来源：<https://code.claude.com/docs/en/model-config> [A]

### 8.4 1M 上下文在订阅侧的可用性

| Plan | Opus 用 1M 上下文 | Sonnet 4.6 用 1M 上下文 | 等级 |
|---|---|---|---|
| Max / Team / Enterprise | **订阅内含**（自动升级）| 需 usage credits | [A] |
| Pro | 需 usage credits | 需 usage credits | [A] |
| API / pay-as-you-go | 完全可用 | 完全可用 | [A] |

> "The 1M context window uses **standard model pricing with no premium for tokens beyond 200K**." [A]
来源：<https://code.claude.com/docs/en/model-config> [A]

### 8.5 Claude Code 的实际花费基准（企业侧，官方数字）
> "Across enterprise deployments, the average cost is around **$13 per developer per active day** and **$150–250 per developer per month**, with costs remaining **below $30 per active day for 90% of users**." [A]
> Agent teams："use approximately **7x more tokens** than standard sessions when teammates run in plan mode" [A]
> 后台空闲开销："typically **under $0.04 per session**" [A]
来源：<https://code.claude.com/docs/en/costs> [A]

### 8.6 Claude Code 的 effort 档位（与 API 略有出入）

| 模型 | Claude Code 内可用 effort | 等级 |
|---|---|---|
| Fable 5 | low / medium / high / xhigh / max | [A] |
| Opus 5、Sonnet 5、Opus 4.8、Opus 4.7 | low / medium / high / xhigh / max | [A] |
| Opus 4.6、Sonnet 4.6 | low / medium / high / max | [A] |

> "The default effort is **`high` on every model that supports effort, except Opus 4.7, which defaults to `xhigh`**." [A]
> 设了不支持的档位会**向下取最近可用档**（"`xhigh` runs as `high` on Opus 4.6"）。[A]
来源：<https://code.claude.com/docs/en/model-config> [A]

### 8.7 Claude Code 的安全分类器自动回退（很少见的公开细节）
> "**Fable 5**: biology-flagged requests re-run on **Opus 5**, and cybersecurity-flagged requests re-run on **Opus 4.8**." [A]
> "On **Opus 5**, you get those refusals from the first flagged request."（Opus 5 无 biology 回退目标）[A]
需 Claude Code v2.1.219+；Fable 5 需 v2.1.170+ 才在模型选择器出现。[A]
来源：<https://code.claude.com/docs/en/model-config> [A]

---

## 9. 其他可上台的量化数字（全部 [A]）

| 项目 | 数值 | 来源 |
|---|---|---|
| Batch API 折扣 | 输入输出**各 50% off** | pricing.md |
| Fast mode（研究预览，仅 Opus 5 / Opus 4.8，仅 Claude API）| **$10 / $50 per MTok**（= 基础价 2 倍）；速度 "around **2.5 times** the default speed" | pricing.md ＋ news/claude-opus-5 |
| Web search | **$10 per 1,000 searches** | pricing.md |
| Web fetch | **无额外费用** | pricing.md |
| Code execution | 每组织每月 **1,550 免费小时**，超出 **$0.05/小时/容器**；与 web search/fetch 同用时**免费** | pricing.md |
| Managed Agents 会话运行时 | **$0.08 per session-hour**（仅 `running` 状态计时，毫秒级计量）| pricing.md |
| `inference_geo: "us"`（数据驻留）| **1.1x** 价格乘数（Claude 4.6 及以后）| pricing.md |
| Bedrock/Google Cloud 区域端点 | 比 global 端点贵 **10%** | pricing.md |
| Tool-use system prompt token 开销 | Opus 5：**286**（auto/none）/ **406**（any/tool）；Opus 4.8：290/410；**Opus 4.7：675/804**；Sonnet 5：354/474 | pricing.md |
| Bash 工具定义额外 token | Opus 5 / 4.8 / 4.7：**325**；Opus 4.6 及更早：244 | pricing.md |
| 新 tokenizer 影响 | "Claude 4.7 and later models… use a newer tokenizer… produces approximately **30% more tokens** for the same text." | pricing.md |
| Managed Agents 计费示例 | Opus 5 一小时会话（5 万输入 + 1.5 万输出）= **$0.705**；开启缓存后 = **$0.525** | pricing.md |

来源：<https://platform.claude.com/docs/en/about-claude/pricing.md> 、<https://www.anthropic.com/news/claude-opus-5> [A]

---

## 10. 本轮未获证实 / 需人工复核的清单

| # | 项目 | 状态 |
|---|---|---|
| 1 | Claude Max **20x** 的确切月费 | **未获证实**（页面只暴露 "From $100"）|
| 2 | Sonnet 5 的 HLE（34.6% / 46.8%）与 OSWorld-Verified（78.5%）归属 | **存疑**（两次抓取结论矛盾，需人工打开原页确认）|
| 3 | Claude Fable 5 的官方 news 发布文 URL 及其 benchmark 数字 | **未找到**（多个候选 URL 均 404）|
| 4 | Opus 5 / Fable 5 / Sonnet 5 在 SWE-bench Verified、Terminal-Bench 上的官方分数 | **官方未公布**（Opus 5、Sonnet 5 两篇发布文均未提及这两个 benchmark）|
| 5 | Opus 5 各 benchmark 的**绝对分数** | **官方仅以图表呈现**，正文只有相对表述 |
| 6 | Haiku 4.5 的官方发布日 | 由 model ID `...-20251001` 推断为 2025-10-01，未在本轮抓到发布公告页 |
| 7 | Opus 4.8 / 4.7 / 4.6 / Sonnet 4.6 的发布日 | 由 deprecations 页的 "not sooner than YYYY+1" 反推，**属推断** |
| 8 | Free 档能用哪些模型 | claude.com/pricing 未明示 |

---

## 11. 来源清单（全部亲自抓取）

1. <https://platform.claude.com/docs/en/about-claude/models/overview.md> — 模型规格总表
2. <https://platform.claude.com/docs/en/about-claude/pricing.md> — 全量价格 / 缓存 / batch / 工具计费
3. <https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5.md> — Fable/Mythos 规格与 API 变更
4. <https://platform.claude.com/docs/en/about-claude/model-deprecations.md> — 生命周期与退役表
5. <https://platform.claude.com/docs/en/build-with-claude/effort.md> — effort 档位与推荐
6. <https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md> — 缓存最小长度与倍率
7. <https://www.anthropic.com/news/claude-opus-5> — Opus 5 发布（2026-07-24）
8. <https://www.anthropic.com/news/claude-sonnet-5> — Sonnet 5 发布（2026-06-30）
9. <https://www.anthropic.com/news/redeploying-fable-5> — Fable 5 出口管制中断与恢复
10. <https://www.anthropic.com/news> — 新闻索引（用于核对发布日）
11. <https://claude.com/pricing> — 订阅档位与价格
12. <https://code.claude.com/docs/en/costs> — Claude Code 用量口径与成本基准
13. <https://code.claude.com/docs/en/model-config> — Claude Code 默认模型 / effort / 1M 上下文 / 回退

**404 记录（已尝试但不存在）**：
- `https://platform.claude.com/docs/en/pricing.md`（正确路径是 `/docs/en/about-claude/pricing.md`）
- `https://www.anthropic.com/news/claude-fable-5`
- `https://www.anthropic.com/news/introducing-claude-fable-5`
- `https://www.anthropic.com/news/claude-fable-5-and-claude-mythos-5`
