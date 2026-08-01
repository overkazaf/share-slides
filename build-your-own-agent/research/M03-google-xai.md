# M03：Google 与 xAI（2026-08-01 快照）

> 采集时间：2026-08-01。所有数字均当场抓取来源 URL 核对。
> 可信度分级：**[A]** 厂商官方页/官方定价页/官方 model card/榜单官方站（已亲自抓取）；**[B]** 权威二手（Artificial Analysis 等，已抓取）；**[C]** 仅见于聚合站/内容农场。
> 凡未抓到来源的，一律写「**未获证实**」，不写数字。

---

## 一、Google / Gemini 在售模型

### 1.1 模型规格 + 定价总表

上下文与发布日抓自 Google Cloud 官方 model 页；价格抓自 Gemini API 官方定价页（页面标注 Last Updated: **2026-07-30 UTC**）。

| 模型 ID | 发布日 | 状态 | 最大输入 tokens | 最大输出 tokens | 输入 $/1M | 输出 $/1M | 等级 |
|---|---|---|---|---|---|---|---|
| `gemini-3.6-flash` | **2026-07-21** | GA | **1,048,576** | 65,536 | $1.50 | $7.50 | [A] |
| `gemini-3.5-flash` | **2026-05-19** | GA | 1,048,576 | 65,536 | $1.50 | $9.00 | [A] |
| `gemini-3.5-flash-lite` | **2026-07-21** | GA | 1,048,576 | 65,536 | $0.30 | $2.50 | [A] |
| `gemini-3.1-flash-lite` | **2026-05-07** | GA | 1,048,576 | 65,536 | $0.25（文本/图/视频）<br>$0.50（音频） | $1.50 | [A] |
| `gemini-3.1-pro-preview` | **2026-02-19** | Public preview | 1,048,576 | 65,536 | $2.00（≤200k）<br>$4.00（>200k） | $12.00（≤200k）<br>$18.00（>200k） | [A] |
| `gemini-2.5-pro` | 2025-06-17 | GA | 1,048,576 | 65,536 | $1.25 / $2.50 | $10.00 / $15.00 | [A] |
| `gemini-2.5-flash` | 2025-06-17 | GA | 1,048,576 | 65,536 | $0.30（$1.00 音频） | $2.50 | [A] |
| `gemini-2.5-flash-lite` | 2025-07-22 | GA | 1,048,576 | 65,536 | $0.10（$0.30 音频） | $0.40 | [A] |

来源：
- 定价 [A] https://ai.google.dev/gemini-api/docs/pricing
- 规格/发布日 [A] `https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/{3-6-flash | 3-5-flash | 3-5-flash-lite | 3-1-flash-lite | 3-1-pro | 2-5-pro | 2-5-flash | 2-5-flash-lite}`
- GA 时间线交叉验证 [A] https://ai.google.dev/gemini-api/docs/changelog

**注意**：所有 Gemini 模型的 knowledge cutoff **未获证实**（官方 model 页未列出该字段）。

**上台讲的一句话**：Gemini 全系（含最便宜的 `gemini-2.5-flash-lite`，$0.10/1M 输入）统统是 **1,048,576 token 输入 / 65,536 token 输出**——上下文长度已经不是分层维度了。

### 1.2 定价档位与附加计费 [A]

| 项目 | 价格 |
|---|---|
| Batch / Flex 档 | 标准价的 **50%**（如 3.6 Flash：$0.75 / $3.75） |
| Priority 档 | 标准价的 **1.8 倍**（3.6 Flash：$2.70 / $13.50） |
| Context Caching 存储 | **$1.00 / 1M tokens / 小时** |
| Google Search grounding | Gemini 3.x 每月 **免费 5,000 次**，超出 **$14 / 1,000 次** |
| Google Maps grounding | **$14 / 1,000 次** |
| 数据使用 | 免费档内容会被用于改进产品；付费档不会 |

来源 [A] https://ai.google.dev/gemini-api/docs/pricing

### 1.3 各模型定位 + 官方 benchmark [A]

来源：https://deepmind.google/models/gemini/ 及其子页 `/flash/`、`/flash-lite/`、`/pro/`、`/deep-think/`

**Gemini 3.6 Flash** — 定位「Best for token efficiency in coding, knowledge work, and multimodal tasks」

| Benchmark | 分数 |
|---|---|
| SWE-Bench Pro | 58.7% |
| Terminal-bench 2.1 | 78.0% |
| OSWorld-Verified（agentic computer use） | 83.0% |
| MLE-Bench | 63.9% |
| DeepSWE v1.1 | 49% |
| CharXiv（无工具 / 有工具） | 85.2% / 89.4% |
| GDM-MRCR v2 @128k / @1M | 91.8% / **54.0%** |
| GDPVal-AA v2 | 1421（Elo） |

官方原话：「reduced output token usage by **17%** compared to 3.5 Flash, according to Artificial Analysis Index」

> 演讲可用的反差点：**1M 上下文窗口 ≠ 1M 可用**。同一模型 MRCR v2 在 128k 是 91.8%，拉到 1M 掉到 **54.0%**。这是 Google 自己的官方数字。

**Gemini 3.5 Flash-Lite** — 「Best for low-latency and high throughput agentic tasks」
- SWE-Bench Pro 54.2% ／ OSWorld-Verified 74.0% ／ Terminal-bench 2.1 54.0% ／ 长上下文 128k 平均 72.2%
- 官方原话：「delivering **350 output tokens per second** according to the Artificial Analysis Index」

**Gemini 3.1 Pro（Preview）** — 「Best for complex tasks and bringing creative concepts to life」
- Humanity's Last Exam（Search + Code）51.4% ／ ARC-AGI-2 **77.1%** ／ GPQA Diamond **94.3%** ／ SWE-Bench Verified 80.6% ／ LiveCodeBench Pro Elo 2887 ／ MMMU-Pro 80.5% ／ MMMLU 92.6%

**Gemini 3.1 Deep Think** — 「Best for modern challenges across science, research and engineering」，基于 3.1 Pro 的推理模式
- ARC-AGI-2 **84.6%** ／ IMO 2025 81.5% ／ 国际物理奥赛 2025 87.7% ／ 国际化学奥赛 2025 82.8% ／ Codeforces Elo **3455** ／ MMMU-Pro 81.5%
- 上下文窗口、发布日、订阅档位要求：**未获证实**（官方页未列）

---

## 二、Gemini Notebook（原 NotebookLM）

### 2.1 改名：确切时间与官方公告 [A]

**2026-07-16**，Google Workspace Updates 博客发布《NotebookLM is now Gemini Notebook》。

- 公告 URL [A] https://workspaceupdates.googleblog.com/2026/07/notebooklm-now-gemini-notebook.html
- 官方原话：「We're renaming NotebookLM to Gemini Notebook」，同时换新 logo
- 生效范围：Rapid Release 与 Scheduled Release 双通道，自 2026-07-16 起；标注为 Extended rollout（功能可见性可能超过 15 天）
- 覆盖对象：全部 Google Workspace 客户、Workspace Individual 订阅者、以及有 NotebookLM 访问权的个人 Google 账号
- 管理员无需操作：「Automatic redirects will ensure existing shared notebooks and user links continue to work.」

**域名迁移，实测可复现（2026-08-01 亲自 curl 验证）** [A]：
```
https://notebooklm.google.com/  →  HTTP 302  →  https://notebook.google.com/
```
营销站 https://notebooklm.google/ 页面 `<title>` 现为：**「Gemini Notebook | AI Research Tool & Thinking Partner」**

帮助中心也已迁移：`support.google.com/notebooklm/*` → `support.google.com/gemininotebook/*`，站点标题「Gemini Notebook Help」。

### 2.2 硬上限：源材料容量（最适合上 PPT 的部分）[A]

来源 [A] https://support.google.com/gemininotebook/answer/16269187（FAQ）

官方原话逐字：
> 「Get **100 notebooks**, with up to **50 sources** each and **500,000 words** each.」
> 「Have daily limits of **50 chat queries** and **3 audio generations**.」
> 「The current limit is **500,000 words per source** or up to **200MB** for local uploads. **There's no page limit.**」

导入失败的三个官方判定条件：
1. 单源超过 500,000 词
2. 文件超过 200MB
3. 原始 PDF 被复制保护（copy-protected）

**分格式的细颗粒上限** [A] https://support.google.com/gemininotebook/answer/16215270
- Google Slides：**最多 100 张幻灯片**
- Google Sheets：**限制在 100k tokens**
- 单源通用：**500,000 词 或 200MB**（上传文件）
- 免费用户：**每个 notebook 最多 50 个源**
- YouTube：只支持公开视频，且**必须有字幕**（用户上传或自动生成）；**72 小时内上传的视频可能不可用**
- Google Drive 源：**每几分钟自动同步一次**（auto-updated and will sync every few minutes）

**支持的源类型全清单** [A]（同上）：
PDF / Google Docs / Google Slides / Google Sheets / Word (.docx) / PowerPoint (.pptx) / txt / Markdown (.md) / CSV / ePub / 网页 URL / YouTube URL / 粘贴文本 / Gemini Chats（把对话作为源）/ 音频（mp3、wav、m4a、aac、aiff、amr、flac 系、ogg、opus、wma 等）/ 图片（jpg、png、webp、heic、heif、avif、bmp、gif、tif、ico、jp2 等）

### 2.3 免费档 vs 付费档：完整官方对照表 [A]

来源 [A] https://support.google.com/gemininotebook/answer/16213268（逐字抓取表格）

| 项目 | Standard（免费） | in Plus | in Pro | in Ultra (20TB) | in Ultra (30TB) |
|---|---|---|---|---|---|
| **Notebooks** | 100/用户 | 200/用户 | 500/用户 | 500/用户 | 500/用户 |
| **Sources** | **50/notebook** | 100/notebook | 300/notebook | 500/notebook | **600/notebook** |
| Chats | 50/天 | 200/天 | 500/天 | 2.5K/天 | 5K/天 |
| Audio Overviews | 3/天 | 6/天 | 20/天 | 100/天 | 200/天 |
| Video Overviews | 3/天 | 6/天 | 20/天（Cinematic 2/天） | 100/天（Cinematic 10/天） | 200/天（Cinematic 20/天） |
| Reports | 10/天 | 20/天 | 100/天 | 500/天 | 1K/天 |
| Flashcards | 10/天 | 20/天 | 100/天 | 500/天 | 1K/天 |
| Quizzes | 10/天 | 20/天 | 100/天 | 500/天 | 1K/天 |
| Mind Maps | 10/天 | 20/天 | 100/天 | 500/天 | 1K/天 |
| Deep Research | **10/月** | 3/天 | 20/天 | 75/天 | 200/天 |
| Data Tables / Infographics / Slide Decks | Limited | More limits | High limits | Higher limits | Highest limits |
| Watermark Removal | No | No | No | **Yes** | Yes（Infographics 与 Slide Decks） |
| Earlier Access | Standard | Early | Priority | Priority | Priority |

其它官方细则 [A]：
- 开通方式：Standard「Sign up free of charge by using your gmail account」；Plus/Pro/Ultra 分别对应 Google AI Plus / Pro / Ultra 订阅
- 「Sharing a notebook does not change the source limit for any collaborator.」
- 「Daily quotas are reset after 24 hours; monthly quotas are reset after 30 days.」
- 首次加源时自动生成的那一份 report/flashcards/infographic/slide deck/audio/video overview **不计入配额**
- 数据：「Your data is protected, and is not used to train Gemini Notebook unless you provide feedback.」Workspace / Workspace for Education 用户即使点赞踩也不会被人工审阅、不用于训练
- **Enterprise 档**（Gemini Notebook for Enterprise / Gemini Enterprise Standard、Plus、Frontline）：「**5X or more** notebook artifacts」，附 VPC-SC、IAM 控制；文件留在客户自己的 GCP project 内，遵守数据区域化

### 2.4 当前能力清单 [A]

来自帮助中心目录（16 篇 Get started 文章，https://support.google.com/gemininotebook/）：
source-grounded 聊天（Use chat）、Create & add notes、**Mind Maps**、**Audio Overview**、**Video Overviews**（含 Cinematic 变体）、**Flashcards / Quizzes**、**Infographic**、**Slide Deck**、**Reports**、**Deep Research**、**Data Tables**、public notebooks & featured notebooks、移动 App、Notebooks in Gemini Apps、Change mode、Change output language。

source-grounded 的官方约束原话 [A]：
> 「Gemini Notebook answers questions based on the information provided in your uploaded sources. If the answer isn't in the source material, it won't provide a response.」

---

## 三、Gemini CLI 现状（核实「2026-06-18 免费/消费者档停服」）

### 3.1 结论：传闻属实，但**停的不是 Gemini CLI 本身，是消费者档的接入资格**

**官方原文（最硬的一条）** [A] https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
> 「Starting **June 18, 2026**, Gemini Code Assist IDE extensions stopped serving requests for the **Gemini Code Assist for individuals, Google AI Pro, and Google AI Ultra** tiers.」
> 「Access to Gemini Code Assist IDE extensions and Gemini CLI using **Gemini Code Assist Standard or Enterprise** subscriptions **remain unchanged**.」

**官方产品站横幅（2026-08-01 实抓）** [A] https://codeassist.google/
> 「Unpaid tier (Gemini Code Assist for individuals) and Google One users only: **Gemini CLI and Gemini Code Assist IDE extensions will be replaced by Antigravity CLI and Antigravity on June 18th.** Please migrate to avoid disruption.」

同时 codeassist.google 站点标题已改为「**Gemini Code Assist for teams and businesses**」——个人免费产品线在品牌层面已经消失。

### 3.2 现在还剩什么

| 通道 | 现状 | 等级 |
|---|---|---|
| 「Login with Google」个人账号免费档（60 req/min、1,000 req/day） | **已停**（2026-06-18 起） | [A] |
| Google AI Pro / Ultra 订阅走 CLI | **已停**（2026-06-18 起） | [A] |
| Gemini Code Assist **Standard** 订阅 | 继续可用，Gemini CLI 打勾 | [A] |
| Gemini Code Assist **Enterprise** 订阅 | 继续可用，且「Increased agent usage：Do more with Gemini Code Assist agent mode and the Gemini CLI with **increased daily usage limits**」 | [A] |
| **Gemini API Key**（付费 API 计费） | 继续可用 | [A] |
| **Vertex AI** | 继续可用 | [A] |
| 开源仓库本身 | **活着且高频发版** | [A] |

**Gemini Code Assist 官方价格** [A] https://cloud.google.com/gemini/pricing（逐字抓取）

| 版本 | 月度承诺 | 12 个月承诺 |
|---|---|---|
| Gemini Code Assist **Standard** | **$0.031232877 / 1 hour** | $0.026027397 / 1 hour |
| Gemini Code Assist **Enterprise** | **$0.073972603 / 1 hour** | $0.061643836 / 1 hour |

> 换算（按 730 小时/月，本笔记自算，非官方标注）：Standard ≈ **$22.80/月**（年付 ≈ $19.00/月）；Enterprise ≈ **$54.00/月**（年付 ≈ $45.00/月）。上台如果要报月价，建议注明「按 730h 折算」。

Standard 与 Enterprise 都明确包含 **Gemini CLI ✓**；Enterprise 额外含 Code customization、Gemini in Apigee 等。

### 3.3 仓库还在剧烈更新 [A] https://github.com/google-gemini/gemini-cli/releases

| 版本 | 日期 |
|---|---|
| v0.55.0-nightly.20260801.gf47d6c6f7 | 2026-08-01（pre-release） |
| v0.54.0-preview.1 | 2026-07-31 |
| **v0.53.1**（最新稳定） | 2026-07-31 |
| v0.54.0-preview.0 | 2026-07-28 |
| v0.53.0 | 2026-07-28 |

### 3.4 一个非常适合讲的「文档滞后」案例 [A]/[B]

- 截至 **2026-08-01**，仓库 README **仍然写着**免费档：「60 requests/min and 1,000 requests/day」——而这个档位 6 周前（06-18）就已停服。[A] https://raw.githubusercontent.com/google-gemini/gemini-cli/main/README.md
- 有人 **2026-06-17** 就开了 issue 要求清理，标题「docs: remove references to deprecated consumer and free tiers」，**至今 open**。[A] https://github.com/google-gemini/gemini-cli/issues/27998
- 配套 PR #27997 于 2026-07-02 **关闭且未合并**（`merged=false`）。[A] https://github.com/google-gemini/gemini-cli/pull/27997
- PR 描述逐字：「these services (including Gemini Code Assist for individuals, Google AI Pro/Ultra, and the unpaid Free Tier) **will stop serving requests on June 18, 2026**.」
- 真实用户报错（2026-07-21，issue #28473）：`IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals... migrate to Antigravity`。同一 issue 还吐槽「模型自己还在说 CLI 免费档 60 req/min、1,000 req/day 是有效的」。[A] https://github.com/google-gemini/gemini-cli/issues/28473

> 讲稿钩子：官方文档说停了，README 说没停，模型自己也说没停，用户拿到 `IneligibleTierError`。这是「AI 时代文档与事实脱节」的现成标本。

### 3.5 迁移路径：Antigravity CLI [A] https://antigravity.google/docs/cli/gcli-migration

- 目标产品：**Antigravity CLI**，文档标注版本 **v1.1.9**
- 首次启动自动检测既有 profile，交互式迁移配置与 token
- Extensions → Plugins：`agy plugin import gemini`
- Skills 路径：`.gemini/skills/` → `.agents/skills/`
- MCP：从 `settings.json` 内联移到独立 `mcp_config.json`
- `GEMINI.md` 需重命名对齐新结构
- 迁移文档中**未列**任何 deadline 日期、配额或免费档信息 → **未获证实**

---

## 四、xAI / Grok

> 注意一个品牌信号：xAI 官方 release notes 中出现「Grok 4.5, **SpaceXAI's** model for coding...」；arena.ai 榜单上 Grok 系列的 Organization 字段也标为 **SpaceXAI**。两处独立信源一致。[A] docs.x.ai/developers/release-notes + [A] arena.ai/leaderboard/text。改名/合并的具体公告与时间：**未获证实**。

### 4.1 当前模型：ID / 上下文 / 价格 [A]

来源 [A] https://docs.x.ai/developers/pricing 与 https://docs.x.ai/developers/models

| 模型 ID | 上下文 | 输入 $/1M | 缓存输入 $/1M | 输出 $/1M | 发布日 |
|---|---|---|---|---|---|
| `grok-4.5`（<200k） | **500k** | $2.00 | $0.30 | $6.00 | **2026-07-08** [A] |
| `grok-4.5`（≥200k） | 500k | $4.00 | $0.60 | $12.00 | 同上 |
| `grok-4.3`（<200k） | **1M** | $1.25 | $0.20 | $2.50 | **未获证实** |
| `grok-4.3`（≥200k） | 1M | $2.50 | $0.40 | $5.00 | 未获证实 |
| `grok-4.20-0309-reasoning`（<200k / ≥200k） | 1M | $1.25 / $2.50 | $0.20 / $0.40 | $2.50 / $5.00 | **2026-03-10** [A] |
| `grok-4.20-0309-non-reasoning` | 1M | 同上 | 同上 | 同上 | 2026-03-10 [A] |
| `grok-4.20-multi-agent-0309` | 1M | 同上 | 同上 | 同上 | 2026-03-10 [A] |
| `grok-build-0.1`（<200k / ≥200k） | **256k** | $1.00 / $2.00 | $0.20 / $0.40 | $2.00 / $4.00 | **2026-05-19**（early access）[A] |

**`grok-4.5` 补充规格** [A] https://docs.x.ai/developers/grok-4-5
- 别名：`grok-4.5-latest`、`grok-build-latest`
- 模态：文本 + 图像输入 → 文本输出
- 速率上限：**150 requests/second**、**50,000,000 tokens/minute**
- 区域：`us-east-1`、`us-west-2`
- 定位原话：「SpaceXAI's intelligent coding model for agentic software, engineering, and workflow tasks」
- 2026-07-17 起在 EU 的 API console 可用 [A]

**其它模态定价** [A]
| 项目 | 价格 |
|---|---|
| `grok-imagine-image` | $0.02 / 张 |
| `grok-imagine-image-quality` | $0.05 / 张 |
| `grok-imagine-video` | $0.050 / 秒 |
| `grok-imagine-video-1.5` | $0.080 / 秒（原生 1080p，T2V/I2V） |
| `grok-voice-think-fast-1.0` | $0.05/分钟音频 + $0.004/文本 |
| `grok-voice-think-fast-2.0` | $0.08/分钟音频 + $0.004/文本 |
| Speech-to-Text | $0.10/小时（REST）、$0.20/小时（流式） |
| Text-to-Speech | $15.00 / 1M 字符 |
| Batch API | 部分模型 **8 折**（20% discount） |
| Priority Processing | 标准价 **2 倍** |
| 存储 | 文件 $0.025/GiB/天；collections $0.10/GiB/天；下载 $0.20/GiB |
| 违规请求 | $0.05 / 次被标记请求 |

**关键发版时间线** [A] https://docs.x.ai/developers/release-notes（页面标注 Last updated: **2026-07-31**）
- 2026-07-31 `grok-imagine-video-1.5` 支持 T2V/I2V/参考图生视频，原生 1080p
- 2026-07-29 `grok-voice-think-fast-2.0`；`grok-voice-latest` 自 **2026-08-05** 起指向该模型
- 2026-07-17 Grok 4.5 在 EU 可用
- **2026-07-08 Grok 4.5 上线 API**（$2/1M 输入、$6/1M 输出，可配置 reasoning effort）
- 2026-06-15 Priority Processing（`service_tier: "priority"`）
- 2026-05-19 Grok Build 0.1（`grok-build-0.1`，early access）
- 2026-05-14 Grok Build（CLI/TUI）beta，`curl -fsSL https://x.ai/cli/install.sh | bash`
- **2026-03-10 Grok 4.20 与 Grok 4.20 Multi-agent 上线**
- 2026-01-28 Video Generation + 新版 Image Generation、Batch API

### 4.2 X Search / 实时检索：机制与限制 [A]

来源 [A] https://docs.x.ai/developers/tools/x-search

**它检索的是什么——官方原话逐字**：
> 「The X Search tool enables Grok to perform **keyword search, semantic search, user search, and thread fetch** on X (formerly Twitter). This powerful tool allows the model to access **real-time social media content**, analyze posts, and gather insights from X's vast data.」

→ 结论：**X Search 只搜 X 平台内容**，不是全网。全网检索是**另一个独立工具 `web_search`**（参数为 `allowed_domains` / `excluded_domains`，各最多 5 个；`enable_image_understanding`、`enable_image_search`）[A] https://docs.x.ai/developers/tools/web-search

**X Search 全部参数（官方表格逐字）** [A]

| 参数 | 说明 |
|---|---|
| `allowed_x_handles` | Only consider posts from specific X handles（**max 20**） |
| `excluded_x_handles` | Exclude posts from specific X handles（**max 20**） |
| `from_date` | Start date for search range（ISO8601） |
| `to_date` | End date for search range（ISO8601） |
| `enable_image_understanding` | Enable analysis of images in posts |
| `enable_video_understanding` | Enable analysis of videos in posts |

硬约束原话：「`allowed_x_handles` **cannot be set together with** `excluded_x_handles` in the same request.」

SDK 名称：xAI SDK `x_search`；OpenAI Responses API `x_search`；Vercel AI SDK `xai.tools.xSearch()`。

**工具调用计费** [A] https://docs.x.ai/developers/pricing

| 工具 | 价格 |
|---|---|
| **X Search** | **$5 / 1,000 次调用** |
| Web Search | $5 / 1,000 次调用 |
| Code Execution | $5 / 1,000 次调用 |
| File Attachments | $10 / 1,000 次调用 |
| Collections Search | $2.50 / 1,000 次调用 |

2025-11-19 官方降价原话 [A]：「The price of agent tools drops by up to **50%** to **no more than $5 per 1000 successful calls**」——注意计费口径是 **successful calls**。

**时效性有多强 / 有没有公开的量化说明**：
- 官方仅有定性表述「real-time social media content」「X's vast data」
- **索引刷新频率、抓取延迟、可回溯的历史深度、单次返回结果条数上限、索引规模** —— 官方文档全部**未列**，**未获证实**
- 唯一可量化的时间控制手段就是 `from_date` / `to_date` 两个 ISO8601 参数
- GA 时间：**2025-10-15**，`web_search`、`x_search`、`code_execution` 三件套同时 GA [A] https://docs.x.ai/developers/release-notes

> 讲稿建议：X Search 最大的差异化是**独占语料**（X 全站帖子 + 语义检索 + thread fetch + 图/视频理解），而不是任何被公开量化的时效性指标。「$5/1000 次」和「max 20 handles」是全篇仅有的两个硬数字。

### 4.3 Grok 在公开榜单上的位置

**LMArena / arena.ai —— Text 总榜**（快照日期 **2026-07-27**，总票数 **7,496,121**）[A] https://arena.ai/leaderboard/text

Grok 全系位次：

| 排名 | 模型 | 分数 | 票数 |
|---|---|---|---|
| **23** | grok-4.20-beta1 | 1474 ± 5 | 26,598 |
| 27 | grok-4.20-beta-0309-reasoning | 1472 ± 4 | 61,762 |
| 30 | grok-4.20-multi-agent-beta-0309 | 1471 ± 4 | 60,452 |
| **35** | **grok-4.5** | 1468 ± 7 | 9,998 |
| 37 | grok-4.1-thinking | 1466 ± 3 | 65,116 |
| 43 | grok-4.1 | 1460 ± 3 | 67,322 |
| **73** | grok-4.3 | 1443 ± 4 | 48,239 |
| 88 | grok-4-1-fast-reasoning | 1431 ± 3 | 56,476 |
| 125 | grok-4-0709 | 1410 ± 4 | 41,317 |

→ **Grok 最高只到第 23 名，且是老型号 grok-4.20-beta1；最新旗舰 grok-4.5 排 35。Top-20 里一个 Grok 都没有。**

同榜 Gemini 位次 [A]：

| 排名 | 模型 | 分数 | 票数 |
|---|---|---|---|
| **10** | gemini-3.1-pro-preview | 1486 ± 3 | 86,683 |
| 12 | gemini-3-pro | 1486 ± 4 | 41,242 |
| **15** | gemini-3.6-flash | 1482 ± 8 | 6,065 |
| 18 | gemini-3.5-flash-high | 1476 ± 7 | 10,011 |

Top-5 供参考 [A]：1. claude-fable-5（1508±6）／2. claude-opus-4-6-thinking（1505±4）／3. claude-opus-4-7-thinking（1502±4）／4. claude-opus-4-6（1497±4）／5. claude-opus-5-max（1495±12）

**Artificial Analysis —— Intelligence Index** [B] https://artificialanalysis.ai/leaderboards/models（页面未标注快照日期，抓取于 2026-08-01）

| 排名 | 模型 | Index | 输出速度 | 价格 |
|---|---|---|---|---|
| 1 | Claude Opus 5 (max) | 61 | 54 tok/s | $2.34 |
| 4 | GPT-5.6 Sol (max) | 59 | 63 tok/s | $1.86 |
| 7 | Kimi K3 (max) | 57 | 35 tok/s | $0.86 |
| **11** | **Grok 4.5 (high)** | **54** | 56 tok/s | **$0.44** |
| 19 | Gemini 3.5 Flash | 50 | 172 tok/s | $0.69 |
| **20** | **Gemini 3.6 Flash** | **50** | **217 tok/s** | $0.56 |

→ 交叉验证的结论：Grok 4.5 在**盲测人类偏好**（arena，#35）远差于在**自动化能力评测**（AA Index，#11）。同一模型两个榜差 24 位，值得在台上点一句。
→ Gemini 3.6 Flash 在 AA 上是 Top-20 里**输出速度最快**的（217 tok/s），与 Google 官方主打的「token efficiency」叙事一致。
→ 注意：AA 榜 Top-20 中**未见 Gemini 3.1 Pro**，可能是分档命名或未收录，**未获证实**，不要在台上说「Gemini Pro 没进前 20」。

---

## 五、抓不到 / 未获证实清单（台上别讲）

| 项 | 状态 |
|---|---|
| 所有 Gemini 模型的 knowledge cutoff | 官方 model 页无此字段 |
| Gemini 3.1 Deep Think 的上下文窗口、发布日、订阅门槛 | 官方页未列 |
| Google AI Plus / Pro / Ultra 的具体月费美元数 | one.google.com 价格由 JS 按地区注入，抓到的是 `/mo` 占位符 |
| `grok-4.3` 的发布日 | xAI release notes 2026 年条目中完全没有该模型 |
| X Search 的索引刷新频率、延迟、历史深度、单次返回条数上限、索引规模 | 官方文档全无量化说明 |
| Antigravity CLI 的免费档 / 配额 / 迁移 deadline | 迁移文档未列 |
| xAI → SpaceXAI 更名的官方公告与时间 | 仅在 release notes 措辞与 arena.ai 组织字段中间接出现；x.ai 主站被 Cloudflare 拦截（HTTP 403），无法抓取 |
| Grok 消费者订阅（SuperGrok / X Premium+）价格 | x.ai 被 Cloudflare 拦截，未抓到 |

---

## 六、全部来源 URL 汇总

**[A] Google**
- https://ai.google.dev/gemini-api/docs/pricing （Last Updated 2026-07-30 UTC）
- https://ai.google.dev/gemini-api/docs/changelog
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-6-flash （及 3-5-flash / 3-5-flash-lite / 3-1-flash-lite / 3-1-pro / 2-5-pro / 2-5-flash / 2-5-flash-lite）
- https://deepmind.google/models/gemini/ ／ /flash/ ／ /flash-lite/ ／ /pro/ ／ /deep-think/
- https://cloud.google.com/gemini/pricing
- https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
- https://codeassist.google/
- https://antigravity.google/docs/cli/gcli-migration

**[A] Gemini Notebook**
- https://workspaceupdates.googleblog.com/2026/07/notebooklm-now-gemini-notebook.html
- https://support.google.com/gemininotebook/answer/16269187 （FAQ / 限额）
- https://support.google.com/gemininotebook/answer/16213268 （档位对照表）
- https://support.google.com/gemininotebook/answer/16215270 （源类型与格式上限）
- https://notebooklm.google/ ／ https://notebooklm.google.com/（302 → notebook.google.com）

**[A] Gemini CLI 仓库**
- https://github.com/google-gemini/gemini-cli/releases
- https://raw.githubusercontent.com/google-gemini/gemini-cli/main/README.md
- https://github.com/google-gemini/gemini-cli/issues/27998
- https://github.com/google-gemini/gemini-cli/pull/27997
- https://github.com/google-gemini/gemini-cli/issues/28473

**[A] xAI**
- https://docs.x.ai/developers/pricing
- https://docs.x.ai/developers/models
- https://docs.x.ai/developers/grok-4-5
- https://docs.x.ai/developers/tools/x-search
- https://docs.x.ai/developers/tools/web-search
- https://docs.x.ai/developers/release-notes （Last updated 2026-07-31）

**[A] 榜单官方站**
- https://arena.ai/leaderboard/text （快照 2026-07-27，7,496,121 票）

**[B] 权威二手**
- https://artificialanalysis.ai/leaderboards/models

**[C]** 无。本笔记未采用任何聚合站或内容农场数据。
