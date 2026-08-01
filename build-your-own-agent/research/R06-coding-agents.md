# R06｜2026 年主流 Coding Agent 全景

> **数据快照日期：2026-08-01**（除非另行标注）
> **产出人**：资料采集研究员 ｜ **用途**：技术演讲 PPT 素材
> 所有 GitHub star / license / archived / pushed_at 字段，均于 2026-08-01 通过 `api.github.com/repos/{org}/{repo}` 实时拉取，属一手数据。

---

## 0. 严谨性说明（先读这段）

本笔记把证据分成三级，正文中会标注：

| 标记 | 含义 |
|---|---|
| **【一手】** | 厂商官网 / 官方 changelog / 官方 blog / GitHub API / 官方 leaderboard / 本地仓库文件 |
| **【二手】** | 主流媒体（Forbes、CNBC、The Register、TechCrunch）、Hacker News 元数据（点赞/评论/日期由 Algolia API 返回） |
| **【存疑】** | 仅有 SEO 内容农场/聚合站佐证，或多方说法冲突 —— **不要直接上 PPT** |

### 本轮踩到的三个「AI 内容农场陷阱」（可以当反面案例讲）

1. 多篇 2026 年博客称 **pi 的作者是 Armin Ronacher（Flask 作者）**。
   → **错误**。本地仓库 `LICENSE` 明写 `Copyright (c) 2025 Mario Zechner`；Pragmatic Engineer 2026-04-29 的专访也确认作者是 Mario Zechner，Armin Ronacher 只是**长期用户**。
   来源：`/Users/nongjiawu/playground/research/pi/pi-mono/LICENSE`；<https://newsletter.pragmaticengineer.com/p/building-pi-and-what-makes-self-modifying>
2. 抓取 `ampcode.com/manual` 时，摘要模型输出「Amp 是 Anthropic 做的」。
   → **错误**。Amp 出自 Sourcegraph，2025 年 12 月已 spin out 成独立公司 Amp Frontier Corporation。来源：<https://sourcegraph.com/blog/why-sourcegraph-and-amp-are-becoming-independent-companies>
3. 各家 SWE-bench 聚合站（llm-stats / benchlm / codeant / steel.dev）给出的「第一名」互相打架（96.0% / 95.5% / 95.0% / 97.0% 都有人报）。
   → 官方 `swebench.com` / `verified.swebench.com` 在本次抓取中返回不可解析内容。**SWE-bench Verified 的具体分数一律标注为「聚合站数据，待核实」**。

---

## 1. 十九款产品逐个核实

> 排序：先「厂商闭源系」，再「开源 CLI 系」，最后 pi。

### 1.1 Claude Code（Anthropic）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商/作者 | Anthropic | 【一手】<https://code.claude.com/docs/en/changelog> |
| 形态 | CLI 为主 + IDE 扩展（VS Code/JetBrains）+ Web/移动端远程会话 + SDK/Agent SDK | 【一手】官方 changelog |
| 开源与否 | **闭源**（npm 分发的是编译产物）。2026-03-31 曾因 npm 包内残留 source map 发生「源码泄露」事件 | 【二手】HN 47584540，2026-03-31，2095 分 / 1022 评论 |
| 核心架构 | 单进程 agent loop + 工具调用；CLAUDE.md 上下文文件；Skills / Subagents / Plugins / Hooks / MCP；沙箱（`sandbox.network.strictAllowlist`）；**subagent 可嵌套到 depth 3**（2.1.219 起，此前为 1） | 【一手】changelog 2.1.219 |
| 定价 | 订阅制：Free / Pro $20（年付 $17）/ Max 起 $100 / Team 标准席 $20（月付 $25）、**高级席 $100（月付 $125，Claude Code 需高级席）** / Enterprise $20/席 + API 用量。所有付费档含 Claude Code | 【一手】<https://claude.com/pricing> |
| 最新版本 | **v2.1.220，2026-07-25**（v2.1.219，2026-07-24 引入 `claude-opus-5` 为默认 Opus 模型，1M context，fast mode $10/$50 per Mtok） | 【一手】官方 changelog |
| 一句话差异化 | 事实上的行业基线：模型 × harness 一体化调优，生态（Skills/Plugins/Hooks）最完整，代价是完全绑定 Anthropic。 | |

**争议点（可上 PPT 的「幸福的烦恼」）**：
- 2026-02～04 大规模「模型变笨了」质疑，Anthropic 发布官方事故复盘：HN 47660925（2026-04-06，1364 分 / 753 评论）与 47878905（2026-04-23，942 分 / 732 评论，链接 <https://www.anthropic.com/engineering/april-23-postmortem>）。
- 2026-06-30「Claude Code 在请求里做隐写标记」讨论，HN 48734373，**2445 分 / 750 评论**（本次检索到的 2026 年 coding agent 相关最高热度帖）。

### 1.2 OpenAI Codex（CLI + Cloud）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | OpenAI | 【一手】<https://github.com/openai/codex> |
| 形态 | **CLI（开源）+ Codex Cloud（chatgpt.com/codex，云端异步）+ IDE 扩展 + ChatGPT App 内 Auto-review** | 【一手】GitHub releases + 【二手】releasebot |
| 开源与否 | **CLI 开源，Apache-2.0**，102,942 stars（2026-08-01 API 实测）；云端服务闭源 | 【一手】GitHub API |
| 核心架构 | Rust 实现 CLI；AGENTS.md 上下文约定；native subagents、MCP、hooks、auto-review、thread forking、remote Code Mode hosting、plugin marketplace | 【一手】GitHub releases notes；【二手】releasebot |
| 定价 | 随 ChatGPT Plus/Pro/Business/Enterprise 订阅；也可 API key 自付。**2026-07 将 auto-review 从 GPT-5.4 换到 GPT-5.6 Luna，官方称成本约降 10×**（此条为【存疑】，仅聚合站佐证） | 【存疑】 |
| 最新版本 | **稳定版 v0.146.0，2026-07-29**；预发布 v0.147.0-alpha.4，2026-07-31 | 【一手】<https://github.com/openai/codex/releases> |
| 一句话差异化 | 唯一「开源 CLI + 官方云端异步执行」双形态的一线厂商方案；本地/云端可同一套 AGENTS.md。 | |

### 1.3 Cursor（Anysphere）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Anysphere, Inc. | |
| 形态 | **IDE（VS Code fork）为主 + Cursor CLI + Web/Slack + 云端 agent + iPad App** | 【一手】<https://cursor.com/changelog> |
| 开源与否 | **闭源** | |
| 核心架构 | 自研 Composer 系列模型 + 多模型路由；2026-07-22 上线 **Cursor Router**（Intelligence / Balance / Cost 三档智能路由）；多仓库云端 agent；Side Chats | 【一手】changelog |
| 定价 | 订阅 + 用量。2026-06 引入 Premium 档 $120/月（年付 $96/月）【存疑，仅聚合站】；2026-07-28 面向印度推出 **Cursor Start ₹649/月**【一手 changelog】。**Composer 2.5 定价：$0.50/M in、$2.50/M out；Fast 变体 $3.00/M in、$15.00/M out（Fast 为默认）** | 【一手】<https://cursor.com/blog/composer-2-5>（2026-05-18） |
| 最新版本 | changelog 最新条目 **2026-07-29（Cursor for iPad）**；版本号可见的最近一条为 **v3.11，2026-07-10**。Cursor 3.0 发布于 2026-04-02【存疑，仅聚合站】 | 【一手】changelog |
| 一句话差异化 | 唯一自研前沿编码模型 + IDE 一体化的玩家；正在从「AI 编辑器」转成「多 agent 调度平台 + 自有模型」。 | |

> **重磅（务必上 PPT）**：**2026-06-16，SpaceX 宣布将以 600 亿美元收购 Cursor 母公司 Anysphere，Anysphere 将成为其全资子公司，预计 2026 Q3 完成交割。**
> 【二手·主流媒体】<https://www.cnbc.com/2026/06/16/spacex-spcx-cursor-acquisition-ipo.html> ；<https://www.forbes.com/sites/siladityaray/2026/06/16/spacex-will-buy-ai-coding-firm-cursor-for-60-billion/>
> Forbes 提到该交易源自 2026 年 4 月双方的合作协议，其中 SpaceX 保留按里程碑以 100 亿或 600 亿美元收购的权利。

### 1.4 GitHub Copilot（agent mode / coding agent）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | GitHub / Microsoft | |
| 形态 | **IDE 内 agent mode（本地同步）+ GitHub 上的 coding agent（云端异步）+ Copilot CLI + Agent HQ / Mission Control** | 【一手】<https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent> |
| 开源与否 | **闭源**（部分 VS Code 侧 chat 扩展已开源，但服务端闭源） | |
| 核心架构 | coding agent 跑在 **GitHub Actions 驱动的一次性开发环境**，单会话上限 **59 分钟**；分支级权限隔离、防火墙沙箱；产出 PR 供人 review。agent mode 则在本地 IDE 直接改文件 | 【一手】GitHub Docs |
| 定价 | Free / Student 免费 / **Pro $10 / Pro+ $39 / Max $100 / Business $19 席 / Enterprise $39 席**。**2026-06-01 起用 GitHub AI Credits（$0.01/credit，按 token 计费）取代 Premium Request Units**；补全与 next-edit 不消耗 credits，只有 chat / agent mode / code review / CLI 消耗 | 【一手】<https://docs.github.com/en/copilot/get-started/plans>；AI Credits 生效日为【存疑，聚合站】 |
| 最新时间点 | Agent HQ 于 **GitHub Universe 2025-10-28** 发布，把 Anthropic / OpenAI / Google / Cognition / xAI 的第三方 agent 接入同一控制平面 | 【二手】<https://github.blog/news-insights/company-news/welcome-home-agents/>、Visual Studio Magazine |
| 一句话差异化 | 不做最强 agent，做**中立的 agent 控制平面 + 治理层**：谁家的 agent 都能进来，但都得走 GitHub 的分支、沙箱与审计。 | |

### 1.5 Windsurf → **Devin Desktop**（Cognition）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Cognition（2025 年收购 Codeium/Windsurf） | |
| 形态 | **IDE**（原 Windsurf），**2026-06-02 正式更名 Devin Desktop** | 【一手】<https://devin.ai/blog/windsurf-is-now-devin-desktop/>（2026-06-02） |
| 开源与否 | **闭源** | |
| 核心架构 | 默认界面变成 **Agent Command Center**（本地+云端 agent 的 Kanban 看板）；新增 **Spaces**（跨 agent 共享上下文，聚合 session / PR / 文件）；**原生支持 ACP**，可在同一窗口里跑 Codex / Claude Agent / OpenCode；本地 agent 由 **Devin Local** 接替 Cascade（官方称 token 效率提升最多 30%，Cascade 支持至 7 月 1 日） | 【一手】同上 |
| 定价 | 随 Devin 统一定价（见下） | |
| 一句话差异化 | 把 IDE 重新定义为「agent 舰队指挥舱」——**编辑器不再是主界面，看板才是**。 | |

### 1.6 Devin（Cognition）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Cognition | |
| 形态 | **四个面：Devin Desktop（IDE）/ Devin Cloud（云端自治 agent）/ Devin CLI / Devin Review** | 【一手】devin.ai blog 目录 |
| 开源与否 | **闭源** | |
| 定价（2026-08-01 官网实测） | **Free $0**（轻量额度）/ **Pro $20/月**（含前沿模型、Cloud agents、SWE 1.7 免费用）/ **Max $200/月** / **Teams $80/月 + $40/开发者席** / Enterprise 定制。官网**已不再公开 ACU 费率表**，改为配额 + 按需额度 | 【一手】<https://devin.ai/pricing> |
| 最新时间点 | 高频发版：Stacked PRs（2026-07-30）、Kimi K3 接入（2026-07-27）、Claude Opus 5 接入（2026-07-23）、Devin Outposts（2026-07-21）、Agentic MapReduce（2026-07-01） | 【一手】<https://devin.ai/blog> |
| 一句话差异化 | 从「一个自治工程师」转型成「一整套 agent 编队 + 自有 SWE 系列模型」的全栈厂商。 | |

### 1.7 Cline

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商/作者 | Cline（公司化） | |
| 形态 | **VS Code / JetBrains 扩展 + CLI + SDK（`@cline/sdk`）** | 【一手】GitHub README |
| 开源与否 | **开源，Apache-2.0**，**65,337 stars**（2026-08-01 API 实测），最近 push 2026-08-01 | 【一手】GitHub API |
| 核心架构 | Plan/Act 双模式；MCP 服务器接入；**多 agent 协作（coordinator 委派 specialist）**；插件系统（日志/审计/策略）；BYO-model，官方列 12+ provider | 【一手】GitHub README |
| 定价 | 工具本身免费开源，**BYOK 自付模型费**；另有 Cline 官方托管入口 | |
| 最新版本 | **v4.1.2，2026-07-31**（v4.1.0 把稳定版做成含新旧两套 SDK 变体的 A/B 灰度包） | 【一手】<https://github.com/cline/cline/releases> |
| 一句话差异化 | 「IDE 扩展起家、现在把 agent harness 抽成可嵌入 SDK」——最像**开源版 agent runtime 中间件**。 | |

### 1.8 Roo Code —— **已停运**

| 项 | 内容 | 证据 |
|---|---|---|
| 状态 | **仓库已归档，归档时间 2026-05-15**（GitHub API：`archived: true`，`pushed_at: 2026-05-15T18:08:47Z`）；README 明写「The Roo Code Extension was shut down on May 15th」 | 【一手】GitHub API + <https://github.com/RooCodeInc/Roo-Code> |
| 开源与否 | Apache-2.0，**24,364 stars**（定格值） | 【一手】GitHub API |
| 曾经的核心架构 | 多 Mode 架构（每个 mode 独立 system prompt / 工具权限 / 可绑不同模型）+ **Boomerang Tasks**（orchestrator 派生 sub-agent 并行）+ 原生 Ollama / LM Studio | 【二手】多方一致 |
| 继任者 | 官方 README 推荐 **ZooCode**（社区 fork，Apache-2.0，<https://github.com/Zoo-Code-Org/Zoo-Code>，<https://www.zoocode.dev/>）与回归 Cline；原团队转向 **Roomote**（roocode.com 已跳转） | 【一手】README；【二手】zoocode.dev |
| 一句话差异化（讲故事用） | **Boomerang Tasks 是「多 agent 编排」在 IDE 扩展里最早的量产实现，但项目本身没活过 2026 上半年。** | |

### 1.9 Aider

| 项 | 内容 | 证据 |
|---|---|---|
| 作者 | Paul Gauthier | |
| 形态 | **纯 CLI**（终端结对编程） | |
| 开源与否 | **开源，Apache-2.0**，**47,848 stars**（2026-08-01 实测） | 【一手】GitHub API |
| 核心架构 | repo map（tree-sitter 抽符号）+ diff/whole 等多种 edit format + 自动 git commit；无 MCP、无 subagent，极简单 agent | |
| 定价 | 免费开源，纯 BYOK | |
| **最新版本（有分歧，如实标注）** | GitHub Releases 最新 tag：**v0.86.0，2025-08-09**；PyPI `aider-chat` 最新：**0.86.2，2026-02-12**。GitHub API `pushed_at`：**2026-05-22**。→ **结论：2026 年发版节奏显著放缓，近三个月无新提交** | 【一手】<https://github.com/Aider-AI/aider/releases>、<https://pypi.org/project/aider-chat/>、GitHub API |
| 一句话差异化 | 开源 CLI agent 的「老前辈」和 polyglot benchmark 的发源地；**2026 年已明显退居二线**，适合当「代际更替」的对照组。 | |

### 1.10 OpenHands（原 OpenDevin）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | All Hands AI；GitHub 组织已从 `All-Hands-AI` 迁到 **`OpenHands/OpenHands`** | 【一手】GitHub API（`full_name: OpenHands/OpenHands`） |
| 形态 | **Web UI + CLI + Docker/K8s 自托管 + 云托管（app.all-hands.dev）+ SDK** | |
| 开源与否 | **开源，MIT**，**82,725 stars**（2026-08-01 实测） | 【一手】GitHub API |
| 核心架构 | agent 在**隔离的容器化 runtime** 里操作（浏览器 + shell + 编辑器 + Jupyter）；多 agent / microagent；模型无关（Claude / GPT / Gemini / Qwen / Llama 均可） | |
| 定价 | 自托管免费；All Hands Cloud 按用量；Enterprise 版含 K8s VPC 自托管、Agent Control Plane、SAML/SSO、RBAC | 【二手】 |
| 最新版本 | **v1.8.0，2026-07-30**（v1.7.x 同日连发） | 【一手】<https://github.com/All-Hands-AI/OpenHands/releases> |
| 一句话差异化 | **最「学术出身 + 企业自托管」的开源 agent**：容器化 runtime 是一等公民，SWE-bench 长期是它的主战场。 |

### 1.11 Gemini CLI —— **免费/消费者档已于 2026-06-18 停服**

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Google | |
| 形态 | CLI | |
| 开源与否 | **Apache-2.0，106,286 stars**（2026-08-01 实测），仓库**未归档**、仍在提交（pushed 2026-08-01） | 【一手】GitHub API |
| **关键事件** | **2026-05-19（Google I/O）Google 官方宣布把 Gemini CLI 迁移到 Antigravity CLI**；**2026-06-18 起，Gemini CLI 对免费用户、Google AI Pro、Ultra 全部停止服务**。**Antigravity CLI 是闭源 Go 二进制**。仅持有 Gemini Code Assist Standard/Enterprise 许可、或付费 API key 的组织可继续使用 Gemini CLI | 【一手】官方公告 <https://github.com/google-gemini/gemini-cli/discussions/27274>；<https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/> |
| 社区反应（**极佳的 PPT 素材**） | 官方公告帖收到 **296 个 downvote vs 6 个 upvote**；代表性评论包括「essentially working for free on a code base that will only be used in enterprises」「half baked Go binary」。HN 上 <https://news.ycombinator.com/item?id=48196867>（2026-05-19，406 分 / 210 评论）标题直接是「Gemini CLI will stop working from June 18, 2026」 | 【一手】GitHub discussion；【二手】HN Algolia API |
| 一句话差异化 | **2026 年最典型的「开源 CLI agent 被厂商收回」案例**：代码还是 Apache-2.0，但免费额度和主推路线全部转向闭源替代品。 |

> 补充【存疑】：多家博客称 Antigravity CLI 把免费额度从 1000 次/天降到约 20 次/天。仅聚合站佐证，**若上 PPT 请标注"据第三方报道"**。

### 1.12 Google Jules

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Google（Google Labs 出身） | |
| 形态 | **Web 为主（jules.google.com）+ GitHub Issue 打 `jules` label 直接派活 + Jules Tools CLI + REST API**；云端 VM 异步执行，产出 PR | 【一手】<https://jules.google/>、<https://jules.google/docs> |
| 开源与否 | **闭源** | |
| 分档（官网实测，官网未直接标价） | **Jules：15 任务/天，3 并发，Gemini 2.5 Pro** ｜ **Jules Pro：100 任务/天，15 并发，Gemini 3 Pro** ｜ **Jules Ultra：300 任务/天，60 并发，Gemini 3 Pro 优先** | 【一手】jules.google |
| 价格 | 【存疑】聚合站给出 Pro $19.99/月、Ultra $124.99/月，官网页面未直接列价；GA 时间点据称为 **Google I/O 2026（2026-05-19）** | 【存疑】 |
| 一句话差异化 | **纯异步 / 纯云端 / 任务配额计价**的代表：不进你的终端，只往你的仓库丢 PR。 |

### 1.13 Amp（原 Sourcegraph，现 Amp Frontier Corporation）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | **Amp Frontier Corporation** —— 2025 年 12 月从 Sourcegraph 分拆独立；Quinn Slack、Beyang Liu 创办 Amp Inc.，Dan Adler 接任 Sourcegraph CEO | 【一手】<https://sourcegraph.com/blog/why-sourcegraph-and-amp-are-becoming-independent-companies>、<https://ampcode.com/news/amp-inc> |
| 形态 | **CLI（`amp` / `amp -x`）+ Web（ampcode.com，线程管理/分享/远程控制）+ VS Code / JetBrains / Neovim / Zed 插件 + Slack** | 【一手】<https://ampcode.com/manual> |
| 开源与否 | **闭源** | |
| 核心架构 | agent 有 `low / medium / high / ultra` 四档 effort；**Orbs**（可编程/事件驱动的 agent 容器，2026-06-30「Agents in Orbs」、2026-07-23「Event Driven Orbs」）；多人协作 Multiplayer（2026-07-22）；自定义 agent（2026-06-19） | 【一手】<https://ampcode.com/news> |
| 定价 | **信用点制**：可纯按量（最低充值 $5，无需订阅），LLM 成本对个人/非企业团队**零加价透传**；企业版贵 50% 且需一次性 $1,000 起购；**2026-07-18 上线月度订阅**。**Amp Free**：2025-10-21 上线（广告支持），**2026-03-30 宣布去掉广告**（当时广告年化收入已 >$1000 万，但官方直言「ads don't pay for enough frontier tokens to make a difference」），保留每日 $10 免费额度并对低活跃用户暂停 | 【一手】<https://ampcode.com/manual>、<https://ampcode.com/news/amp-free-is-ad-free>（2026-03-30） |
| 最新时间点 | 新闻页最新条目 **2026-07-29** | 【一手】ampcode.com/news |
| 一句话差异化 | 商业模式实验最激进的一家：**广告 → 去广告 → 纯透传信用点 → 月订阅**，一年换了三种模式；产品上押注 Orbs（agent 容器化 + 事件驱动）。 |

### 1.14 opencode

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商/作者 | **Anomaly Co（`anomalyco`，即原 SST 团队；`sst/opencode` 已跳转）** | 【一手】GitHub API `full_name: anomalyco/opencode` |
| 形态 | **终端 TUI + 桌面 App（macOS/Windows/Linux）+ IDE 扩展 + ACP agent** | 【一手】GitHub README、zed.dev/acp |
| 开源与否 | **开源，MIT**，**191,697 stars**（2026-08-01 实测）—— **本轮统计中 star 数最高的 coding agent** | 【一手】GitHub API |
| 核心架构 | 完整 agent harness：tool loop、LSP 集成、session 管理、**build / plan / general 三种 agent 角色**；模型完全解耦（任意 provider，或用 OpenCode Zen 精选列表） | 【一手】GitHub README |
| 定价 | 工具免费，BYOK；OpenCode Zen 为可选托管入口 | |
| 最新版本 | **v1.18.10，2026-07-30** | 【一手】<https://github.com/anomalyco/opencode/releases> |
| 一句话差异化 | **开源阵营的「事实旗舰」**：功能对标 Claude Code，但模型可换、代码可读、协议开放。 |

### 1.15 Qwen Code（阿里通义）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | 阿里巴巴 / 通义千问团队（QwenLM） | |
| 形态 | **CLI（`qwen`）+ 交互/headless 双模式 + 桌面版 + VS Code / Zed / JetBrains 集成 + SDK** | 【一手】GitHub README |
| 开源与否 | **开源，Apache-2.0，26,480 stars**（2026-08-01 实测） | 【一手】GitHub API |
| 核心架构 | **起源于 Google Gemini CLI v0.8.2 的 fork**，但官方声明自 v0.1 起已独立演进为多协议 agent 框架；具备 Auto-Memory、Auto-Skills、SubAgents；provider 支持 OpenAI 兼容 / Anthropic / Gemini / Qwen / 阿里云 Coding Plan / OpenRouter / Fireworks / 本地端点 | 【一手】GitHub README |
| 定价 | 免费开源 + BYOK；配合阿里云 Coding Plan 或本地模型可零边际成本 | |
| 最新版本 | **v0.21.2，2026-07-31**（同日 nightly tag 为 `nightly.20260731`，可交叉验证日期） | 【一手】<https://github.com/QwenLM/qwen-code/releases> |
| 一句话差异化 | **中国厂商在开源 CLI agent 赛道最完整的一手**：模型开源 + harness 开源 + 可全本地运行。 |

### 1.16 Zed agent（Zed Industries）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Zed Industries（Atom / Tree-sitter 团队） | |
| 形态 | **原生编辑器（Rust）内的 Agent Panel** | |
| 开源与否 | **开源**，README 表述为 **主体 GPL-3.0-or-later，部分组件标注 Apache-2.0**（GitHub API 返回 `NOASSERTION`，因是混合许可）；**87,842 stars**（2026-08-01 实测） | 【一手】GitHub API + <https://github.com/zed-industries/zed> |
| 核心架构 | Agent Panel 支持「跟随 agent 在代码库里走位」（复用其多人协作基建）、可编辑的 unified diff 审阅、按工具粒度授权；**通过 ACP 接入外部 agent**（Claude Agent、Codex、OpenCode 等）；可接 MCP、可接 Ollama 本地模型 | 【一手】<https://zed.dev/ai> |
| 定价 | 编辑器免费开源；Zed Pro 提供托管模型额度；也可 BYOK / 本地模型 | 【一手】zed.dev/ai |
| **ACP（这是 Zed 最大的行业贡献）** | Agent Client Protocol，**Zed 于 2025 年 8 月首次发布，Apache 许可**；2025 年 10 月 JetBrains 加入；截至目前官网列出 **11 个编辑器**（Zed、JetBrains、VS Code、Neovim、Emacs、Obsidian、AionUI、Sidequery、aizen、DeepChat、Tidewave）与 **50+ agent**（Claude Agent、Codex CLI、GitHub Copilot、Cursor、Devin、OpenHands、Gemini CLI、Cline、Goose、Mistral Vibe 等） | 【一手】<https://zed.dev/acp> |
| 一句话差异化 | 自己不争「最强 agent」，而是**定义 agent 与编辑器之间的 USB-C 口（ACP）** —— 结果 Devin Desktop、Zed、JetBrains、VS Code 都插上了。 |

### 1.17 Continue —— **已停止维护**

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商 | Continue Dev, Inc. | |
| 形态 | VS Code / JetBrains 扩展 + CLI | |
| 开源与否 | **Apache-2.0，35,247 stars**（2026-08-01 实测）。README 明写「The `continuedev/continue` repository is no longer actively maintained and is read-only for all users」。**注意：GitHub API 显示 `archived: false` 且 `pushed_at: 2026-07-31`，与 README 表述不完全一致 —— 疑为用分支保护而非 archive 实现只读，此处如实标注分歧** | 【一手】GitHub API + README |
| 结局 | **2026-06 被 Cursor 收购**；发布最终版 **2.0.0**（覆盖 VS Code 扩展 / CLI / JetBrains 插件），云端数据于 **2026-07-15** 后删除。收购公告日期各方报道为 06-16（首页/FAQ 静默更新）至 06-18（正式宣布） | 【二手】<https://thenewstack.io/cursor-acquires-continue-coding/> 等 |
| 一句话差异化（讲故事用） | 「BYO-model 开源助手」这一代的代表，**在 2026 年被自己的闭源竞品收编**——和 Roo Code 一起构成本年度开源阵营的两次「阵亡」。 |

### 1.18 Goose（Block → Agentic AI Foundation）

| 项 | 内容 | 证据 |
|---|---|---|
| 厂商/归属 | **由 Block 开源，现归 Agentic AI Foundation（Linux Foundation 旗下）托管**，仓库为 **`aaif-goose/goose`**（原 `block/goose` 跳转） | 【一手】GitHub API + <https://github.com/aaif-goose/goose>；起源公告 <https://block.xyz/inside/block-open-source-introduces-codename-goose> |
| 形态 | **Rust CLI + 桌面 App + API**；可作为 ACP agent 接入编辑器 | 【一手】README + zed.dev/acp |
| 开源与否 | **开源，Apache-2.0，52,037 stars**（2026-08-01 实测） | 【一手】GitHub API |
| 核心架构 | Rust 实现；**能力全部通过 MCP 扩展**（这是 goose 与 pi 的哲学分水岭）；支持 15+ provider 含 Ollama 本地；不限于写代码（工作流/研究/数据分析） | 【一手】README |
| 定价 | 完全免费开源 + BYOK | |
| 最新版本 | **v1.45.0，2026-07-29**（v1.44.0，2026-07-23 含 `goose review` 任意命令执行安全修复） | 【一手】<https://github.com/aaif-goose/goose/releases> |
| 一句话差异化 | **唯一进了中立基金会（Linux Foundation / AAIF）的主流 coding agent**——治理中立性是它现在最大的卖点。 |

### 1.19 pi（earendil-works/pi，原 badlogic/pi-mono）

| 项 | 内容 | 证据 |
|---|---|---|
| 作者/厂商 | **Mario Zechner（GitHub: badlogic，libGDX 作者）/ Earendil Inc.** | 【一手】本地 `LICENSE`：`Copyright (c) 2025 Mario Zechner`；<https://pi.dev/news/2026/5/7/pi-has-a-new-home> |
| 迁移历史 | **2026-05-07** 从 `badlogic/pi-mono` + `@mariozechner/*` scope 迁到 **`earendil-works/pi` + `@earendil-works/*`**，v0.74.0 是新 scope 首个版本；旧包 deprecate 但不 unpublish | 【一手】pi.dev/news |
| 形态 | **纯终端 CLI（TUI）**，四种运行模式：**interactive / print(JSON) / RPC（进程集成）/ SDK（嵌入自己的 App）** | 【一手】本地 `packages/coding-agent/README.md` |
| 开源与否 | **开源，MIT，81,528 stars**（2026-08-01 实测），最近 push 2026-08-01 | 【一手】GitHub API |
| 核心架构（**这是 pi 的全部卖点，务必准确**） | 极简内核 + 自扩展。默认只给模型 **4 个工具：read / write / edit / bash**。README「Philosophy」章节逐条声明**刻意不做**：<br>· **No MCP** —— 改用「带 README 的 CLI 工具」（Skills），或自己写 extension 加 MCP<br>· **No sub-agents** —— 用 tmux 起多个 pi 实例，或写 extension<br>· **No permission popups** —— 跑容器，或自己写确认流程（README 首页也明说 pi **不内置权限系统**，默认以启动用户权限运行）<br>· **No plan mode** —— 计划写文件<br>· **No built-in to-dos** —— "They confuse models"，用 TODO.md<br>· **No background bash** —— 用 tmux，要完整可观测性<br>扩展面：**TypeScript Extensions / Skills / Prompt Templates / Themes**，打包成 **Pi Packages** 经 npm 或 git 分发；extension 可访问工具、slash command、快捷键、事件、完整 TUI；改完 `/reload` 即生效 | 【一手】本地仓库 `packages/coding-agent/README.md` L491-507、`docs/usage.md` L299-303、根 `README.md` |
| 隔离方案 | 不内置沙箱，提供三种容器化范式：**Gondolin extension**（pi 与 provider 认证留宿主机，内置工具与 `!` 命令路由进本地 Linux micro-VM）、**纯 Docker**、**OpenShell** | 【一手】根 `README.md` + `packages/coding-agent/docs/containerization.md` |
| 定价 | 完全免费开源，纯 BYOK | |
| 最新版本 | **v0.83.0，2026-07-29**（本地 CHANGELOG 实测；`[Unreleased]` 段已在做 `--ui-mode fullscreen` 全屏 TUI、可拖拽滚动条、`registerMarkdownTransformer` 等） | 【一手】`packages/coding-agent/CHANGELOG.md` |
| 生态影响力 | **OpenClaw（Peter Steinberger）建立在 pi 之上**；Pragmatic Engineer 2026-04-29 专文《Building Pi, and what makes self-modifying software so fascinating》（作者 Gergely Orosz），文中 Armin Ronacher 作为**长期用户**出镜 | 【二手】<https://newsletter.pragmaticengineer.com/p/building-pi-and-what-makes-self-modifying>；【二手】Wikipedia/TechCrunch on OpenClaw |
| HN 热度 | 作者原文《What I learned building an opinionated and minimal coding agent》上 HN：**2026-02-01，421 分 / 173 评论**，<https://news.ycombinator.com/item?id=46844822>，原文 <https://mariozechner.at/posts/2025-11-30-pi-coding-agent/> | 【二手】HN Algolia API |
| 一句话差异化 | **别人做「功能越来越多的产品」，pi 做「你可以让它自己长出功能的内核」**——把 MCP / subagent / plan mode / 权限系统全部从内核踢到扩展层，用「自修改软件」换取行为可预测。 |

> **反差点（PPT 金句）**：pi 是本清单里唯一**明确拒绝 MCP** 的主流 agent，而 Goose 是唯一**把 MCP 当作全部扩展机制**的主流 agent。两者都是 Apache/MIT 开源、都在 5 万 star 以上。这一对可以直接做一页对比。

---

## 2. 榜单快照（2026 年）

### 2.1 Terminal-Bench 2.1（**官方榜，可信度最高**）

来源：<https://www.tbench.ai/leaderboard/terminal-bench/2.1>
**快照说明：抓取于 2026-08-01；页面最新提交日期为 2026-07-11。**
注意榜单是 **「harness × model」组合**，不是纯模型分。

| # | Agent(harness) | Model | 准确率 | 提交日 |
|---|---|---|---|---|
| 1 | **Claude Code** | Fable 5 | **83.8% ± 1.2%** | 2026-06-07 |
| 2 | **Codex** | GPT-5.5 | **83.1% ± 1.1%** | 2026-05-01 |
| 3 | Terminus 2 | Fable 5 | 80.4% ± 1.2% | 2026-06-05 |
| 4 | **Cursor CLI** | Grok 4.5 | 79.3% ± 1.5% | 2026-07-09 |
| 5 | Claude Code | Opus 4.8 | 78.9% ± 1.3% | 2026-07-09 |
| 6 | Codex | GPT-5.6 Terra | 78.4% ± 1.3% | 2026-07-11 |
| 7 | Terminus 2 | GPT-5.5 | 78.0% ± 1.2% | 2026-05-01 |
| 8 | mini-SWE-agent | Muse Spark 1.1 | 76.2% ± 1.2% | 2026-07-09 |
| 9 | Codex | GPT-5.6 Luna | 75.7% ± 1.3% | 2026-07-11 |
| 10 | Claude Code | Sonnet 5 | 74.6% ± 1.6% | 2026-07-09 |
| 11 | Terminus 2 | Gemini 3 Pro | 73.9% ± 1.3% | 2026-05-01 |
| 12 | Claude Code | Opus 4.7 | 68.9% ± 1.4% | 2026-05-01 |
| 14 | **Gemini CLI** | Gemini 3 Pro | 65.8% ± 1.4% | 2026-05-01 |
| 14 | **Gemini CLI** | Gemini 3.1 Pro | 65.8% ± 1.7% | 2026-05-05 |

**读法（可直接讲）**：
- 同一个模型（Fable 5）换 harness，从 Claude Code 的 83.8% 掉到 Terminus 2 的 80.4% —— **harness 值 3.4 个点**。
- 同一个 harness（Claude Code）换模型，Fable 5 83.8% → Sonnet 5 74.6% → Opus 4.7 68.9% —— **模型值 15 个点**。
- → 结论：**模型 > harness，但 harness 的 3-4 个点不是噪声**（误差棒约 ±1.2%）。

### 2.2 Terminal-Bench 2.0（官方榜，另一个快照）

来源：<https://www.tbench.ai/leaderboard/terminal-bench/2.0>（抓取于 2026-08-01）
Top 5：NexAU-AHE × GPT-5.5 **84.7%±2.1**（2026-05-14）｜ LemonHarness × Multiple 84.5%±2.6 ｜ Capy × GPT-5.5 83.1%±2.1 ｜ **Codex CLI × GPT-5.5 82.2%±2.2**（2026-04-23）｜ Polaris × Multiple 82.2%±2.8。
更下方：Droid × GPT-5.3-Codex 77.3%（2026-02-24）、Meta-Harness × Claude Opus 4.6 76.4%。

> ⚠️ 与 2.1 榜不可直接比较（题集与评测口径不同），**PPT 上二选一，不要混排**。

### 2.3 Terminal-Bench v2.1（Artificial Analysis 独立复测，**模型维度**）

来源：<https://artificialanalysis.ai/evaluations/terminalbench-v2-1>（抓取于 2026-08-01，页面未标注更新日期）
**GPT-5.6 Sol (xhigh) 89.5% ｜ Claude Opus 5 (Adaptive Reasoning, Max Effort) 89.1% ｜ GPT-5.6 Terra (max) 88.0%**（页面称已覆盖 182 个模型中的 27 个）。

> 与 tbench.ai 官方榜数值差距明显（89.5% vs 83.8%），**因为 AA 用自己的 harness 与 effort 设置跑**。若上 PPT，必须写清「不同评测方 / 不同 harness」，**不要合成一张表**。

### 2.4 SWE-bench Verified（**⚠️ 全部为聚合站数据，待核实**）

官方 `swebench.com` / `verified.swebench.com` 本次抓取失败（内容截断 / socket 关闭），**无一手数据**。
聚合站 steel.dev（自称最后更新 **2026-07-10**，且明说「some rows are independently benchmarked and some are team-reported」）：

| # | 模型 | % Resolved | 标注月份 |
|---|---|---|---|
| 1 | Claude Mythos 5 | 95.5% | 2026-06 |
| 2 | Claude Fable 5 | 95.0% | 2026-06 |
| 3 | Claude Mythos Preview | 93.9% | 2026-04 |
| 4 | Claude Opus 4.8 | 88.6% | 2026-05 |
| 5 | Claude Opus 4.7 | 87.6% | 2026-04 |
| 6 | GPT-5.6 Sol | 82.2% | 2026-07 |
| 7 | Claude Opus 4.5 | 80.9% | 2025-11 |
| 8 | Claude Opus 4.6 | 80.8% | 2026-02 |
| 9 | DeepSeek-V4-Pro-Max | 80.6% | 2026-04 |
| 10 | Gemini 3.1 Pro | 80.6% | 2026-02 |

其它聚合站同期给出的「第一名」还包括 Claude Opus 5 96.0%（llm-stats，称 2026-07-30）、97.0%（codeant，称 2026-07-22）—— **互相矛盾**。
**建议 PPT 表述**：「SWE-bench Verified 头部已进入 90%+ 区间并趋于饱和，前 3 名相差 ~1 个百分点；具体数字各聚合站口径不一，此处不列精确排名。」

### 2.5 SWE-bench Pro（Scale AI 公开集，**一手**）

来源：<https://labs.scale.com/leaderboard/swe_bench_pro_public>（抓取于 2026-08-01）
Muse Spark 1.1 **61.50±3.10%** ｜ gpt-5.4 (xHigh) 59.10±3.56% ｜ Muse Spark 55.00±3.60% ｜ claude-opus-4-6 (thinking) 51.90±3.61% ｜ gemini-3.1-pro (thinking) 46.10±3.60% ｜ claude-opus-4-5 45.89% ｜ claude-4-5-Sonnet 43.60% ｜ gemini-3-pro-preview 43.30%。
页面注：头部成绩为 **uncapped cost + 250 turn limit** 条件下取得。

> **这是最有价值的一张对照**：同一批模型，**SWE-bench Verified 90%+ ↔ SWE-bench Pro 只有 45-62%**。可以直接做一页「Verified 饱和了，难题还早得很」。

---

## 3. 三到四个可上 PPT 的分类维度 + 象限归属建议

### 维度 A：开源程度 × 模型耦合度（**首推，最能讲清 2026 年的分化**）

X 轴：**闭源专有 ←→ 宽松开源（MIT/Apache）**
Y 轴：**绑定自家模型 ←→ 模型完全可换（BYOK）**

| 象限 | 特征 | 归属 |
|---|---|---|
| **闭源 + 绑模型** | 垂直整合，模型与 harness 协同调优 | **Claude Code、Codex（云端部分）、Cursor、Devin / Devin Desktop、Jules** |
| **闭源 + 模型可换** | 卖 harness 与调度，不卖模型 | **GitHub Copilot（Agent HQ 明确接第三方 agent）、Amp、Windsurf 时期的多模型策略** |
| **开源 + 绑模型（弱）** | 开源但有明显主推模型 | **Gemini CLI（2026-06-18 后只服务企业档）、Qwen Code（主推 Qwen3-Coder 但全 provider 可用）** |
| **开源 + 模型完全可换** | 纯 harness，BYOK | **opencode、pi、Cline、OpenHands、Goose、Aider、Zed agent、（已停运）Roo Code、Continue** |

**讲法**：2026 年的分水岭不再是「有没有 AI」，而是 **「harness 和模型能不能解耦」**。右下象限（开源 + 可换模型）是 star 数增长最猛的一格（opencode 191.7k / OpenHands 82.7k / pi 81.5k / Cline 65.3k / Goose 52.0k）。

### 维度 B：交互面（终端 / 编辑器 / 云端异步）

| 形态 | 归属 | 心智模型 |
|---|---|---|
| **CLI / 终端优先** | Claude Code、Codex CLI、pi、opencode、Aider、Goose、Qwen Code、Gemini CLI、Amp CLI、Devin CLI、Cursor CLI | 「结对」——人在场，秒级打断 |
| **IDE / 编辑器优先** | Cursor、Devin Desktop（原 Windsurf）、Zed agent、Cline、（已停运）Roo Code、Continue、Copilot agent mode | 「陪审」——看 diff、逐个 approve |
| **云端异步 / PR 优先** | Jules、Copilot coding agent、Codex Cloud、Devin Cloud、OpenHands Cloud、Amp Orbs | 「外包」——人不在场，收 PR |

**2026 年的新观察**：**三个面正在被同一个协议缝合。** ACP（Zed 起草，Apache 许可）已被 **11 个编辑器、50+ agent** 采纳，Devin Desktop 2026-06-02 更名时直接原生支持；GitHub Agent HQ 在仓库侧做了同样的事。**「agent 与前端解耦」是 2026 年最重要的架构趋势。**

### 维度 C：单 agent ←→ 多 agent 编排

| 层级 | 归属 | 说明 |
|---|---|---|
| **纯单 agent（刻意）** | **pi**（明确 No sub-agents，要多开就 tmux）、**Aider** | 追求行为可预测 |
| **内置 subagent** | Claude Code（**可嵌套到 depth 3**，v2.1.219）、Codex（native subagents）、opencode（build/plan/general 三角色）、Qwen Code（SubAgents） | |
| **显式编排 / 看板** | **Devin Desktop 的 Agent Command Center（Kanban）**、**GitHub Agent HQ / Mission Control**、Cursor 云端多 agent、Amp Orbs（事件驱动容器）、（已停运）Roo Code Boomerang Tasks | 从「一个 agent」升级到「一队 agent 的调度器」 |

### 维度 D：自扩展能力 & 扩展哲学（**pi 主场，建议作为过渡到主讲内容的一页**）

| 扩展路线 | 代表 | 立场 |
|---|---|---|
| **拒绝 MCP，靠代码级扩展** | **pi**（TypeScript Extensions / Skills / Prompt Templates / Themes → Pi Packages 走 npm）；作者另有专文《What if you don't need MCP?》 | 内核最小，能力全靠你自己长 |
| **MCP 即一切** | **Goose**（Rust CLI，能力全部通过 MCP 获得） | 内核最小，能力靠标准协议接 |
| **全都要（大而全）** | **Claude Code**（Skills + Subagents + Plugins + Hooks + MCP + Sandbox） | 产品化，开箱即用 |
| **SDK 化 / 可嵌入** | **Cline SDK（`@cline/sdk`）**、pi 的 RPC + SDK 模式、OpenHands SDK、Codex plugin marketplace | 把 harness 当中间件卖/送 |

**建议的四象限图（一页 PPT）**：
X 轴 = 内核大小（Minimal ←→ Batteries-included）；Y 轴 = 开源程度（Closed ←→ Permissive OSS）。
- 左上（**极简 + 开源**）：**pi**、Aider、Goose
- 右上（**大而全 + 开源**）：opencode、Cline、OpenHands、Qwen Code
- 右下（**大而全 + 闭源**）：Claude Code、Cursor、Devin、Copilot、Amp、Jules
- 左下（**极简 + 闭源**）：**基本没人**——这一格空着本身就是个论点：闭源产品没有做极简的商业动机。

---

## 4. 「开源 CLI agent 阵营」的极客圈口碑差异

> 以下 HN 数据（标题 / 分数 / 评论数 / 日期 / objectID）均通过 **Hacker News Algolia API** 拉取，可逐条复查：`https://news.ycombinator.com/item?id={objectID}`。

### 4.1 opencode：热度天花板，也是争议中心

| 事件 | 日期 | 分数 / 评论 | 链接 |
|---|---|---|---|
| **OpenCode – Open source AI coding agent**（登上 HN 首位） | **2026-03-20** | **1,274 / 618** | <https://news.ycombinator.com/item?id=47460525> |
| **Anthropic blocks third-party use of Claude Code subscriptions** | **2026-01-09** | **625 / 513** | <https://news.ycombinator.com/item?id=46549823>（指向 `anomalyco/opencode` issue #7410） |
| **Anthropic takes legal action against OpenCode** | **2026-03-19** | **483 / 398** | <https://news.ycombinator.com/item?id=47444748>（指向 `anomalyco/opencode` PR #18186） |
| **Claude Code sends 33k tokens before reading the prompt; OpenCode sends 7k** | **2026-07-12** | **706 / 396** | <https://news.ycombinator.com/item?id=48883275> |
| **Unauthenticated remote code execution in OpenCode** | **2026-01-11** | **432 / 142** | <https://news.ycombinator.com/item?id=46581095> |
| **Annoying and alarming things about OpenCode**（"stop using opencode"） | **2026-07-20** | **420 / 289** | <https://news.ycombinator.com/item?id=48978112> |

**口碑画像**：opencode 在极客圈是**「开源正统性」的旗手**（1274 分登顶、191.7k star），但同时是**安全与工程质量批评的焦点**（1 月的未授权 RCE、7 月的「stop using opencode」）。它的高光时刻恰恰来自与 Anthropic 的两次冲突（1 月封 OAuth、3 月法务动作）——**「被大厂封杀」本身成了它最好的营销**。

### 4.2 Gemini CLI：开源阵营最惨烈的一次「反噬」

- **官方公告帖 `google-gemini/gemini-cli` Discussion #27274 的投票是 296 downvote vs 6 upvote**（一手）。代表性评论：*"essentially working for free on a code base that will only be used in enterprises"*、*"half baked Go binary"*。
- HN《Gemini CLI will stop working from June 18, 2026》：**2026-05-19，406 分 / 210 评论**，<https://news.ycombinator.com/item?id=48196867>。
- The Register 同日报道标题即《Bye-bye, Gemini CLI; Google nudges devs toward Antigravity》（2026-05-20）。
- 更早的信任裂痕：《Addressing Antigravity Bans and Reinstating Access》（Discussion #20632）也上过 HN，**2026-02-28，254 分 / 216 评论**。

**口碑画像**：**「Apache-2.0 也保护不了你」**——代码仍开源，但免费额度与产品路线全部转向闭源 Go 二进制。这是 2026 年开源 CLI agent 阵营最被反复引用的警世案例，直接强化了「选一个模型可换、社区自治的 harness」的论调。

### 4.3 pi：小而美路线的口碑

- 作者原文《What I learned building an opinionated and minimal coding agent》上 HN：**2026-02-01，421 分 / 173 评论**（<https://news.ycombinator.com/item?id=46844822>，原文 <https://mariozechner.at/posts/2025-11-30-pi-coding-agent/>）。
- Pragmatic Engineer **2026-04-29** 专文，把 pi 定位成 *"a preview of how self-modifiable software might look in the future"*，并引用 Zechner 的动机：**Claude Code 功能堆积后行为变得不可预测，所以他刻意不加功能**。
- 生态外溢：**OpenClaw（Peter Steinberger，2025-11 首发，数月内 18 万+ star；作者已于 2026-02 加入 OpenAI）建立在 pi 之上**。HN 上也有开发者把 pi 的模块化工具定义直接抽成 MCP 工具复用（HN 48169701，2026-05-17）：*"If you just rip the LLM out of Pi you can teleport any AI in the world into the harness."*

**口碑画像**：pi 的讨论量不如 opencode（421 vs 1274），但**评价质量与"被二次开发"的密度更高**——它更像开发者的**基础设施**而非终端产品。极客圈对它的正面评价集中在两点：**行为可预测**、**能被彻底改造**。

### 4.4 阵营内部的口碑差异总结

| 项目 | 极客圈标签 | 主要正面 | 主要负面 |
|---|---|---|---|
| **opencode** | 「开源旗舰 / 反抗军」 | star 第一、功能对标闭源、模型自由 | 安全事故（RCE）、代码质量与「臃肿」批评 |
| **pi** | 「极客的极客工具」 | 可预测、可自我改造、代码可读 | 门槛高、无 MCP/无 subagent 劝退普通用户 |
| **Goose** | 「治理最干净」 | 进了 Linux Foundation/AAIF、Rust、纯 MCP | 讨论热度相对低，缺乏爆款时刻 |
| **Cline** | 「务实的 IDE 派」 | Plan/Act 心智清晰、SDK 化 | 从扩展转 SDK 期间的 A/B 灰度让用户体感不稳 |
| **Aider** | 「值得尊敬的前辈」 | repo map / edit format 的开创者 | **2026 年发版停滞**（GitHub 最新 tag 仍是 2025-08） |
| **OpenHands** | 「企业自托管首选」 | 容器化 runtime、K8s、MIT | 部署重、上手成本高 |
| **Gemini CLI** | 「前车之鉴」 | 曾经 106k star、1M context | **被厂商在 2026-06-18 收回消费者档** |
| **Roo Code / Continue** | 「阵亡者」 | Boomerang Tasks / BYO-model 的先驱 | 一个归档（2026-05-15），一个被 Cursor 收编（2026-06） |

---

## 5. 待核实清单（**不要直接上 PPT**）

1. **SWE-bench Verified 具体排名与分数**：官方站抓取失败，聚合站互相矛盾（95.5% / 96.0% / 97.0% 三个版本）。
2. **Cursor 3.0 发布日 2026-04-02** 与 **Premium 档 $120/月**：仅聚合站佐证，官方 changelog 未直接确认。
3. **GitHub AI Credits 于 2026-06-01 取代 PRU** 的确切生效日：官方 docs 只描述机制未标日期。
4. **Jules 的具体价格（Pro $19.99 / Ultra $124.99）**：官网只列任务配额未列价。
5. **Antigravity CLI 免费额度「1000/天 → 约 20/天」**：仅第三方报道。
6. **OpenAI「auto-review 换 GPT-5.6 Luna 后成本降 10×」**：仅聚合站。
7. **`continuedev/continue` 的归档状态**：README 说 read-only，GitHub API 说 `archived: false` 且 2026-07-31 仍有 push —— 存在分歧。
8. **Anthropic 2026-05-06 把 Claude Code 用量上限翻倍 / 与「SpaceX Colossus 1」算力合作**：仅聚合站，且涉及第三方公司名称，**建议直接删除不用**。
9. **Terminal-Bench 2.0 官方榜是否仍在更新**：页面未标注 last-updated，最新提交日为 2026-05-14。
10. **模型代号（Fable 5 / Mythos 5 / Muse Spark / GPT-5.6 Sol/Terra/Luna / Grok 4.5）**：均出现在官方 leaderboard（tbench.ai）或厂商 blog（devin.ai）中，但**部分未经厂商一手发布页确认**，若 PPT 要点名模型，建议只用 tbench.ai 官方榜里出现过的写法。

---

## 6. 附：一手数据原始表（2026-08-01 GitHub API 实测）

| repo | SPDX License | Stars | Archived | Last push |
|---|---|---|---|---|
| `anomalyco/opencode` | MIT | **191,697** | false | 2026-08-01 |
| `google-gemini/gemini-cli` | Apache-2.0 | 106,286 | false | 2026-08-01 |
| `openai/codex` | Apache-2.0 | 102,942 | false | 2026-08-01 |
| `zed-industries/zed` | NOASSERTION（GPL-3.0-or-later 为主 + Apache-2.0 组件） | 87,842 | false | 2026-08-01 |
| `OpenHands/OpenHands`（原 All-Hands-AI） | MIT | 82,725 | false | 2026-08-01 |
| **`earendil-works/pi`** | **MIT** | **81,528** | false | 2026-08-01 |
| `cline/cline` | Apache-2.0 | 65,337 | false | 2026-08-01 |
| `aaif-goose/goose`（原 block/goose） | Apache-2.0 | 52,037 | false | 2026-07-31 |
| `Aider-AI/aider` | Apache-2.0 | 47,848 | false | **2026-05-22** |
| `continuedev/continue` | Apache-2.0 | 35,247 | false（README 称已只读） | 2026-07-31 |
| `QwenLM/qwen-code` | Apache-2.0 | 26,480 | false | 2026-08-01 |
| `RooCodeInc/Roo-Code` | Apache-2.0 | 24,364 | **true** | **2026-05-15** |

### 各产品最新版本 / 时间点速查（2026-08-01）

| 产品 | 最新版本 | 日期 | 来源级别 |
|---|---|---|---|
| Claude Code | v2.1.220 | 2026-07-25 | 一手 |
| Codex CLI | v0.146.0（stable） | 2026-07-29 | 一手 |
| Cursor | v3.11 / changelog 最新条目 | 2026-07-10 / 2026-07-29 | 一手 |
| Cline | v4.1.2 | 2026-07-31 | 一手 |
| opencode | v1.18.10 | 2026-07-30 | 一手 |
| **pi** | **v0.83.0** | **2026-07-29** | **一手（本地 CHANGELOG）** |
| Qwen Code | v0.21.2 | 2026-07-31 | 一手 |
| OpenHands | v1.8.0 | 2026-07-30 | 一手 |
| Goose | v1.45.0 | 2026-07-29 | 一手 |
| Aider | v0.86.0（GH tag）/ 0.86.2（PyPI） | 2025-08-09 / 2026-02-12 | 一手（有分歧） |
| Devin Desktop（原 Windsurf） | 更名生效 | 2026-06-02 | 一手 |
| Gemini CLI | 消费者档停服 | 2026-06-18 | 一手 |
| Roo Code | 归档 | 2026-05-15 | 一手 |
| Continue | v2.0.0（最终版） | 2026-06 | 二手 |
