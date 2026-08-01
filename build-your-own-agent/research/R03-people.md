# R03：Agent 领域关键人物谱

> 采集时间：2026-08-01（GitHub 数据均为该日通过 GitHub REST API 实测）
> 语言：简体中文；专有名词保留英文。
> 人称：全文使用中性表述（直呼姓名或用「其」/「该人」），不做性别推断。
> 标注约定：
> - **【一手】** = 本人主页 / 本人博客 / 官方公告 / arXiv 元数据 / GitHub API 实测
> - **【二手】** = 媒体报道、百科、聚合站
> - **【待核实】** = 存在分歧或仅有单一弱来源

---

## 0. 一页速查表

| # | 姓名 | 代表作 | 代表作首次公开日 | 当前身份（2026-08） |
|---|---|---|---|---|
| 1 | Shunyu Yao 姚顺雨 | ReAct / SWE-bench / SWE-agent / τ-bench | ReAct arXiv v1 2022-10-06 | 腾讯首席 AI 科学家（2025-12 官宣） |
| 2 | Harrison Chase | LangChain / LangGraph | LangChain 首次提交 2022-10-24 | LangChain 联合创始人兼 CEO |
| 3 | Toran Bruce Richards | AutoGPT | 2023-03-30 发布 | Significant Gravitas / AutoGPT 创始人 |
| 4 | Yohei Nakajima | BabyAGI | 博文 2023-03-28，repo 2023-04-03 | Untapped Capital 普通合伙人（GP） |
| 5 | Scott Wu | Cognition / Devin | Devin 2024-03-12 发布 | Cognition 联合创始人兼 CEO |
| 6 | Paul Gauthier | Aider | repo 2023-05-09 | Aider AI 创始人 |
| 7 | Mario Zechner (badlogic) | libGDX → pi | pi repo 2025-08-09 | Earendil Inc. 团队成员/股东（2026-04-08 起） |
| 8 | Can Bölük (can1357) | NoVmp/ByePg → oh-my-pi | oh-my-pi 2025-12-31 | 安全研究员 / 逆向工程师；oh-my-pi 作者 |
| 9 | Erik S. + Barry Zhang（Anthropic） | Building Effective Agents | 2024-12-19 | Anthropic |
| 9b | Anthropic Applied AI team | Effective context engineering | 2025-09-29 | Anthropic |
| 10a | Carlos E. Jimenez / John Yang / Ofir Press | SWE-bench / SWE-agent | 2023-10-10 / 2024-05-06 | Princeton 相关（见正文） |
| 10b | Mike A. Merrill / Alexander G. Shaw | Terminal-Bench / Harbor | repo 2025-01-17；2.0 2025-11-07 | Stanford / Laude Institute |
| 10c | Peter Steinberger | OpenClaw（基于 pi） | Warelay 2025-11-24 | 2026-02-14 宣布加入 OpenAI |
| 10d | Armin Ronacher (mitsuhiko) | Flask → Earendil | Earendil 成立于 2025 | Earendil 联合创始人 |

---

## 1. Shunyu Yao（姚顺雨）

**全名**：Shunyu Yao / 姚顺雨。

**身份沿革（按时间）**
- 清华大学交叉信息研究院（「姚班」）本科；普林斯顿大学计算机科学博士（导师方向：NLP + RL）。【二手】<https://news.sciencenet.cn/htmlnews/2025/12/557483.shtm>
- 个人主页长期自述：「I am a researcher at OpenAI. I study agents.」【一手】<https://ysymyth.github.io/>（该页在采集时仍为此表述，属于**未及时更新**，不可作为当前身份依据）
- 2024 年博士毕业后加入 OpenAI 任研究员，参与 Operator、Deep Research 等 agent 产品。加入月份存在分歧：Caixin 称「June 2024」，中文媒体称「2024 年 8 月」。**【待核实：2024-06 还是 2024-08】** <https://www.caixinglobal.com/2026-01-27/in-depth-tencent-bets-its-ai-future-on-28-year-old-from-openai-102408553.html> / <https://news.sciencenet.cn/htmlnews/2025/12/557483.shtm>
- 2025-09 前后离开 OpenAI（量子位报道标题「姚顺雨离职OpenAI，开启下半场」，2025-09）。【二手】<https://www.qbitai.com/2025/09/331194.html>
- **2025-12-17**：Bloomberg 报道腾讯任命该前 OpenAI 研究员为首席 AI 科学家（CEO/总裁办公室），直接向总裁刘炽平汇报，并兼任新设 AI Infra 部负责人。【二手，强】<https://www.bloomberg.com/news/articles/2025-12-17/tencent-appoints-former-openai-researcher-its-chief-ai-scientist> ；SCMP 同日报道 <https://www.scmp.com/tech/big-tech/article/3336811/tencent-restructures-ai-operations-promotes-high-profile-recruit-chief-ai-scientist>
- **【待核实：官宣日期分歧】** 部分中文源称腾讯内部公告为 12-07，科学网文章日期为 12-21，Bloomberg/SCMP/Caixin 均指向 **12-17**。PPT 上建议只写「2025 年 12 月」或写「2025-12-17（Bloomberg）」。

**代表作与可核查日期（arXiv 元数据实测）**

| 作品 | arXiv ID | v1 提交日（预印本） | 正式会议 | 作者列表 |
|---|---|---|---|---|
| ReAct: Synergizing Reasoning and Acting in Language Models | 2210.03629 | **2022-10-06** | ICLR 2023 | Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao |
| Tree of Thoughts | 2305.10601 | **2023-05-17** | NeurIPS 2023 | Shunyu Yao, Dian Yu, Jeffrey Zhao, Izhak Shafran, Thomas L. Griffiths, Yuan Cao, Karthik Narasimhan |
| SWE-bench | 2310.06770 | **2023-10-10** | ICLR 2024（Oral） | Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, Karthik Narasimhan |
| SWE-agent | 2405.15793 | **2024-05-06** | NeurIPS 2024 | John Yang, Carlos E. Jimenez, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, Ofir Press |
| τ-bench | 2406.12045 | **2024-06-17** | — | Shunyu Yao, Noah Shinn, Pedram Razavi, Karthik Narasimhan |

出处：arXiv API（`https://export.arxiv.org/api/query?id_list=<id>`）实测；网页版分别为 <https://arxiv.org/abs/2210.03629>、<https://arxiv.org/abs/2305.10601>、<https://arxiv.org/abs/2310.06770>、<https://arxiv.org/abs/2405.15793>、<https://arxiv.org/abs/2406.12045>。

**另一篇关键文本**：博文《The Second Half》，**2025-04-10** 发表于个人站，核心论点「tldr: We're at AI's halftime.」——主张 RL 终于泛化，AI 的下半场重心从「训练/解题」转向「定义问题与评测」。【一手】<https://ysymyth.github.io/The-Second-Half/>

**一句话「改变了什么」**
> 把「让模型思考」和「让模型动手」缝成一个循环（ReAct），并且用 SWE-bench / τ-bench 把「agent 好不好」变成一个可以打分的工程问题——**先定义了范式，又定义了尺子**。

---

## 2. Harrison Chase

**全名**：Harrison Chase。**身份**：LangChain 联合创始人兼 CEO（另一位联合创始人为 Ankush Gola）。

**可核查事实**
- **LangChain 仓库首次提交：2022-10-24T21:51:15Z**，提交信息为 `initial commit`，作者署名 Harrison Chase。【一手，GitHub API 实测】仓库创建时间 2022-10-17T02:58:36Z。<https://github.com/langchain-ai/langchain>
- 本人博文《Reflections on Three Years of Building LangChain》（**2025-10-20**）自述：「Almost exactly 3 years ago, I pushed the first lines of code to `langchain`」；公司成立于 **2023 年 2 月**；LangSmith 2023 年夏 beta；LangGraph「2023 年夏开始开发、2024 年初发布」；同日宣布 **1.25 亿美元融资、12.5 亿美元估值**，并称月下载量 8000 万。【一手】<https://www.langchain.com/blog/three-years-langchain>
- LangGraph 仓库创建时间 **2023-08-09**（GitHub API 实测），当前 38,590 stars。
- LangGraph v0.1 + LangGraph Cloud 正式发布公告：**2024-06-28**。【一手（官方博客）】<https://blog.langchain.com/langgraph-cloud/>
- LangChain / LangGraph 1.0 GA：2025 年 10 月（与上述博文同期）。<https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available>

**一句话「改变了什么」**
> 把「调 LLM」从一次性 API 调用变成了可组合的**编排层**；随后又用 LangGraph 承认了一件事——agent 不是链，是**带状态的图**，需要可控、可恢复、可观测。

---

## 3. Toran Bruce Richards（网名 Significant Gravitas / Torantulino）

**全名**：Toran Bruce Richards。GitHub 账号 `Torantulino`，自述所在地 UK，X 账号 `@SigGravitas`。【一手，GitHub API 实测】<https://github.com/Torantulino>

**可核查事实**
- **AutoGPT 发布日：2023-03-30**；创建者为 Significant Gravitas Ltd. 创始人 Toran Bruce Richards。【二手】<https://en.wikipedia.org/wiki/AutoGPT>
- GitHub 仓库 `Significant-Gravitas/AutoGPT` **创建于 2023-03-16T09:21:07Z**（早于对外发布日约两周），采集时 **185,746 stars**。【一手，GitHub API 实测】<https://github.com/Significant-Gravitas/AutoGPT>
- **2023 年 10 月**，Significant Gravitas Ltd. 完成 **1200 万美元** 风险融资。【二手】<https://en.wikipedia.org/wiki/AutoGPT>
- 当前状态：仓库仍在活跃维护（最后 push 2026-07-31）。**【公开资料有限】** 关于本人 2025–2026 年的具体动向，除 LinkedIn 自述「Founder & CEO at AutoGPT」外无高质量公开信源。<https://uk.linkedin.com/in/toran-richards>

**一句话「改变了什么」**
> 用一个「给目标、自己拆任务、自己调工具、自己循环」的玩具，让整个行业第一次**肉眼看见** autonomous agent 的形状——也第一次肉眼看见它会卡在死循环里。

---

## 4. Yohei Nakajima

**全名**：Yohei Nakajima。**身份**：Untapped Capital 普通合伙人（GP）；GitHub 资料 company 字段即为 `Untapped Capital`。【一手，GitHub API 实测】<https://github.com/yoheinakajima>

**可核查事实**
- 概念性博文《Task-driven Autonomous Agent Utilizing GPT-4, Pinecone, and LangChain for Diverse Applications》，**发布于 2023-03-28**。【一手】<https://yoheinakajima.com/task-driven-autonomous-agent-utilizing-gpt-4-pinecone-and-langchain-for-diverse-applications/>
- 博文《Birth of BabyAGI》标注 **Posted April 1, 2023**，自述整个项目（代码 + 文章）「took about 3 hours over the course of two days」。【一手】<https://yoheinakajima.com/birth-of-babyagi/>
- GitHub 仓库 `yoheinakajima/babyagi` **创建于 2023-04-03T00:40:27Z**，采集时 22,343 stars。【一手，GitHub API 实测】<https://github.com/yoheinakajima/babyagi>
- **区分提醒（PPT 易错点）**：BabyAGI 的「日期」有三个，不要混用——**博文 2023-03-28** ≠ **命名/发布博文 2023-04-01** ≠ **GitHub 仓库 2023-04-03**。
- 常见说法「约 100 行 Python」属二手概括，建议 PPT 上写「百行量级」而非精确行数。【二手】<https://www.ibm.com/think/topics/babyagi>

**一句话「改变了什么」**
> 把 autonomous agent 压缩成一张**能一眼看完的循环图**（创建任务 → 排优先级 → 执行 → 回写记忆），让「agent 是什么」不再需要论文，只需要一屏代码。

---

## 5. Scott Wu

**全名**：Scott Wu。**身份**：Cognition（Cognition AI / Cognition Labs）联合创始人兼 CEO；联合创始人还有 Steven Hao（CTO）、Walden Yan（CPO）。此前是 Lunchclub 联合创始人兼 CTO；三届 IOI 金牌。【二手】<https://research.contrary.com/company/cognition>

**可核查事实**
- **Devin 发布：2024-03-12**，被称为「世界上第一个自主 AI 软件工程师」；发布时 SWE-bench 成绩 **13.86%（通常引作 13%）**。【二手】<https://siliconangle.com/2024/03/12/cognition-launches-devin-generative-ai-powered-coding-engineer/>
- **2025-07**：Cognition 收购 Windsurf 的 IP、产品、品牌与剩余工程团队（此前 Google 以 24 亿美元 licensing deal 挖走 Windsurf CEO Varun Mohan 等人）。【二手】<https://research.contrary.com/company/cognition>
- **2025-09-08**：CNBC 报道 Cognition 估值达 **102 亿美元**（收购 Windsurf 两个月后）。【二手，强】<https://www.cnbc.com/2025/09/08/cognition-valued-at-10point2-billion-two-months-after-windsurf-.html>
- **2026-05 前后**：多家媒体报道 Cognition 融资 **10 亿美元、估值 260 亿美元**，并援引 Scott Wu 说法「Devin 写了公司约 95% 的代码」。**【待核实：具体日期与「95%」口径】** 该数字来自访谈转述，非公司披露文件。<https://thenextweb.com/news/cognition-just-raised-1-billion-at-a-26-billion-valuation-and-90-of-its-own-code-is-written-by-its-ai> / <https://techcrunch.com/2026/05/29/cognitions-scott-wu-says-ai-coding-agents-shouldnt-replace-humans/>

**一句话「改变了什么」**
> 第一个把 coding agent 当作**产品形态**（而不是编辑器插件）推向市场的人——「AI 同事」这个叙事，以及随后所有「SWE-bench 打多少分」的军备竞赛，都从这里开始。

---

## 6. Paul Gauthier

**全名**：Paul Gauthier。**身份**：Aider 作者；Aider AI 创始人。

**可核查事实**
- GitHub 仓库 `Aider-AI/aider`（原 `paul-gauthier/aider`，已迁移到组织账号）**创建于 2023-05-09T18:57:49Z**，采集时 **47,848 stars**；提交榜首为 `paul-gauthier`，**12,649 次提交**（第二名 47 次，几乎是纯单人项目）。【一手，GitHub API 实测】<https://github.com/Aider-AI/aider>
- 早期提交（2023-05-28 前后）全部署名 `Paul Gauthier`。【一手，GitHub API 实测】
- 履历（Inktomi 联合创始人兼 CTO、后任 Groupon CTO、Geomagical Labs 工程 VP）见二手汇编，**建议 PPT 只用「Inktomi 联合创始人/CTO」这一条**，其余待核实。【二手】<https://self.md/people/paul-gauthier-aider/>
- **Aider polyglot benchmark**：225 道 Exercism 题，覆盖 C++/Go/Java/JavaScript/Python/Rust。【一手（官方文档）】<https://aider.chat/docs/leaderboards/>
- 本人在 X 上公布过一条对「harness 效应」极有说服力的数据：**同一模型换 edit format，GPT-4 Turbo 从 26% 变到 59%**（该数据被 can1357 的《The Harness Problem》引用）。**【待核实：原始推文/文档链接】** 建议引用时以 can1357 博文的转述为准，或直接引 aider 官方 benchmark 页。
- **当前状态【待核实】**：有二手报道称 aider.chat 官方 leaderboard 最后一次刷新为 **2025-11-20**，此后未随新模型更新；仓库最后 push 为 2026-05-22（GitHub API 实测）。<https://agentmarketcap.ai/blog/2026/04/06/aider-polyglot-leaderboard-2026-swe-bench-python-bias>

**一句话「改变了什么」**
> 最早系统性证明了「**编辑格式（edit format）本身就是能力**」——同一个模型，换一种让它改代码的方式，分数能差一倍。这是 harness 工程的第一块基石。

---

## 7. Mario Zechner（badlogic）— 重点核实项

**全名**：Mario Zechner。GitHub `badlogic`（display name 实测为 `Mario Zechner`，blog 字段 `https://mariozechner.at`，X `@badlogicgames`，7,160 followers）。【一手，GitHub API 实测】<https://github.com/badlogic>

**是不是 libGDX 的作者？—— 是。**
- Wikipedia 将 Mario Zechner 与 Nathan Sweet 列为 libGDX 原作者。【二手】<https://en.wikipedia.org/wiki/LibGDX>
- 本人 2026-04-08 博文中自述 libGDX 是自己的第一个大成功、「the most used game development framework on Android」，用户包括 Niantic（Ingress）与 Slay the Spire 的开发者；并称 **2016 年起把主导权交给核心贡献者团队**，且「I never commercialized libGDX」。【一手】<https://mariozechner.at/posts/2026-04-08-ive-sold-out/>
- 起源时间：多个二手源称 2009 年中从 Android 框架 AFX 演化而来。**【待核实：libGDX 的「诞生年」，2009 vs 2010，无一手确证】**

**RoboVM 经历（PPT 上很有戏剧性，务必标为本人自述）**
- 本人自述：受邀加入 RoboVM（由 Niklas Therning、Henric Müller 创建的 iOS AOT JVM），负责第一个商业闭源附加组件（调试器）；**「We sold RoboVM to Xamarin.」→ Xamarin 闭源了开源核心 → Xamarin 被 Microsoft 收购 → Microsoft 立刻关停 RoboVM**；本人作为社区负责人被迫写下那篇「Sorry, no more OSS」的公告。社区随后 fork 出 **MobiVM**，至今为 libGDX 提供 iOS 支持。【一手，自述】<https://mariozechner.at/posts/2026-04-08-ive-sold-out/>
- 这段经历是理解 pi 的许可与治理选择（MIT 不可谈判）的关键背景。

**pi 项目与其关系 —— 核实结论**

| 事实 | 值 | 出处 |
|---|---|---|
| pi 仓库创建时间 | **2025-08-09T14:03:50Z** | GitHub API 实测 |
| 原仓库路径 | `badlogic/pi-mono` → 现 **`earendil-works/pi`**（API 请求 `badlogic/pi-mono` 会 301 到 `earendil-works/pi`，且创建时间一致 → 是**仓库迁移**，不是新建） | GitHub API 实测 |
| 采集时 stars / forks | **81,525 stars / 10,065 forks** | GitHub API 实测（2026-08-01） |
| 许可 | MIT | GitHub API 实测 |
| 提交榜 | `badlogic` 3,462；`mitsuhiko`(Armin Ronacher) 454；其后为社区贡献者 | GitHub API 实测 |
| 设计宣言博文 | **2025-11-30**《What I learned building an opinionated and minimal coding agent》 | <https://mariozechner.at/posts/2025-11-30-pi-coding-agent/> |
| 「卖身」公告 | **2026-04-08**《I've sold out》 | <https://mariozechner.at/posts/2026-04-08-ive-sold-out/> |
| 归属结构 | pi 的 IP 归 Earendil 公司所有；本人成为 Earendil **股东**，并与 Armin、Colin 共同负责 pi 的全部技术决策（方向、路线图、合并与否、开源与否） | 同上，本人自述 |
| 许可承诺 | 核心「MIT licensed. It will stay MIT licensed…Non-negotiable.」；未来新增部分可能采用 Fair Source 或闭源 | 同上，本人自述 |
| 包名迁移 | `@mariozechner/pi-coding-agent` → `@earendil-works/pi-coding-agent`（README 实测为后者） | GitHub README 实测；博文中提到目标包名，**【待核实：博文写的是 `@earendil/pi`，实际发布为 `@earendil-works/pi-coding-agent`】** |

**为什么 pi 会爆**：本人自述关键推力是 **Peter Steinberger 选择在 pi 之上构建 Warelay / Clawdbot / Moltbot / OpenClaw**；Earendil 官方公告亦称 pi 是「the minimal agent within OpenClaw」。【一手（双向印证）】<https://mariozechner.at/posts/2026-04-08-ive-sold-out/> + <https://earendil.com/posts/announcing-pi-and-lefos/>

**Earendil 侧事实**
- Earendil Inc. 为 **Public Benefit Corporation**，由 **Armin Ronacher** 与 **Colin Daymond Hanna** 于 **2025 年**创立。GitHub 组织 `earendil-works` 创建于 **2025-04-16**，location 字段为 **Austria**。【一手】<https://earendil.com/posts/announcing-pi-and-lefos/> + GitHub API 实测
- **2026-04-08** 官方公告：收购 pi 开源项目，Mario Zechner 加入并成为主要利益相关方；同日发布 Lefos（邮件形态的 agent）公开 alpha。早期投资方：Accel（Daniel Levine）、Balderton（Daniel Waterhouse），以及 n8n、OpenClaw、Revolut、Sentry、Slack 的创始人们。**未披露融资金额。**【一手】同上
- Armin Ronacher 同日发文《Mario and Earendil》：「Pi is, in my opinion, one of the most thoughtful coding agents and agent infrastructure libraries in this space.」【一手】<https://lucumr.pocoo.org/2026/4/8/mario-and-earendil/>

**一句话「改变了什么」**
> 在所有人往 harness 里塞功能的时候，反向证明了**「少即是能力」**：一个只有 4 个内置工具、上下文完全可见、其余全部靠 TypeScript 扩展的最小 agent 循环，反而成了别人（OpenClaw）搭楼的地基。

---

## 8. can1357 — 重点核实项

**真实身份：Can Bölük。** 不是匿名——GitHub 账号 `can1357` 的 name 字段实测即为 **「Can Bölük」**，location「The Netherlands」，blog `https://can.ac/`，X `@_can1357`，账号创建于 **2015-04-05**，bio 自述：

> "Security researcher and reverse engineer. Interested in Windows kernel development, low-level programming, static program analysis and cryptography."

【一手，GitHub API 实测】<https://github.com/can1357>

**逆向工程履历（核实结论：NoVmp 是本人的，Blackbone 不是）**

| 项目 | 创建时间 | stars | 说明 |
|---|---|---|---|
| `can1357/NoVmp` | 2020-08-16 | 2,161 | VMProtect x64 3.x 静态去虚拟化器，基于 VTIL |
| `can1357/ThePerfectInjector` | 2018-05-02 | 994 | Windows 注入技术 |
| `can1357/ByePg` | 2019-10-19 | 912 | 通用击破 PatchGuard（Win8–Win10，含 HVCI） |
| `can1357/NtRays` | 2021-11-30 | 675 | Hex-Rays microcode 插件，自动简化 Windows 内核反编译 |
| `can1357/selene` | 2024-09-25 | 447 | Ring 2 内核态半虚拟化 + LLVM 链接器 |
| `can1357/CVE-2018-8897` | 2018-05-13 | 422 | 内核权限任意代码执行 |
| `can1357/linux-pe` | 2020-01-15 | 349 | 无依赖的 COFF/PE 格式 C++ 描述 |
| `can1357/haruspex` | 2021-03-23 | 321 | 用推测执行探测 x86-64 指令集 |
| `can1357/pon` | 2026-07-02 | 538 | Python 3.14 的 JIT/AOT 原生编译器与运行时（Rust + Cranelift） |

【一手，GitHub API 实测】

> **重要纠正**：**Blackbone 不是 can1357 的项目**。`can1357/blackbone` 不存在；Blackbone（Windows memory hacking library，5,450 stars，创建于 2013-12-25）属于 **DarthTon**。<https://github.com/DarthTon/Blackbone>

**博客（技术档案，一手）**：<https://blog.can.ac/>（`can.ac` 301 → `blog.can.ac`）
- 2018-04-26《Splitting Data from Code, Forgotten x86 Feature: Segmentation》
- 2018-04-28《Escaping SMEP Hell: Exploiting Capcom Driver In a Safe Manner》
- 2018-05-02《Making the Perfect Injector》
- 2018-05-11《Arbitrary Code Execution at Ring 0 using CVE-2018-8897》
- 2019-10-19《ByePg: Defeating Patchguard using Exception-hooking》
- 2020-04-11《Writing an optimizing IL compiler, for dummies, by a dummy: 0x1 Symbolic Expressions》
- 2021-03-22《Speculating the entire x86-64 Instruction Set In Seconds with This One Weird Trick》
- 2024-06-28《PgC: Garbage collecting Patchguard away》
- 2025-12-20《Reverse Engineering Hyperliquid ft. SetYesterdayUserVlm》
- 2025-12-25《Optimizing Bracha's Reliable Broadcast: Shaving Rounds off a 37-Year-Old Algorithm》
- **2026-02-12《I Improved 15 LLMs at Coding in One Afternoon. Only the Harness Changed.》**
- 2026-06-10《Snapcompact: SoTA Compaction — Instant, Local, Free. Pick 3》

**oh-my-pi（omp）**

| 事实 | 值 | 出处 |
|---|---|---|
| 仓库创建 | **2025-12-31T14:01:28Z** | GitHub API 实测 |
| stars / forks（2026-08-01） | **20,918 / 1,985** | GitHub API 实测 |
| 许可 / 官网 | MIT / <https://omp.sh> | GitHub API 实测 |
| 与 pi 的关系 | **是 pi 的硬分叉（保留了 git 历史）**：oh-my-pi 仓库里存在 2025-12-30 及更早、署名 `Mario Zechner` 的提交；贡献榜上 `badlogic` 有 1,343 次提交（继承自 pi 历史），`can1357` 本人 9,286 次 | GitHub API 实测（`commits?until=2026-01-02` 仍返回 Mario Zechner 的提交） |
| 定位 | 在 pi 的最小内核上加回「harness 工程」：hash-anchored 编辑、LSP、DAP 调试、Python 执行内核、subagent 编排、记忆系统、浏览器 | 仓库 description（GitHub API 实测） |

**《The Harness Problem》硬数据（2026-02-12，署名 Can Bölük）**
- 实验：**180 个 React 代码库 bug 修复任务 × 3 次运行 × 16 个 LLM**，每次全新会话、4 个可用工具。
- 引入的编辑格式 **Hashline**：每一行返回时带 2–3 字符的内容哈希，模型用稳定标识符定位编辑，而不是复述原文。
- 结果：**Grok Code Fast 1 从 6.7% → 68.3%（约 10 倍）**；MiniMax M2.1 通过率翻倍以上；Grok 4 Fast 输出 token **下降 61%**；16 个模型平均 **+15 个百分点**。
- 结论原话（转述）：「patch 是几乎所有模型最差的格式，hashline 对多数模型追平或超过 replace，**越弱的模型收益越大**。」
- 出处：<https://blog.can.ac/2026/02/12/the-harness-problem/>（302 → <https://stencil.so/blog/the-harness-problem>）
- **【待核实】** `blog.can.ac` 现重定向到 `stencil.so`，暗示与一家名为 **Stencil** 的实体有关联；`stencil.so` 首页内容极少，**无法确认公司性质、成立时间或其角色**，PPT 上不要写「其公司」。

**一句话「改变了什么」**
> 一个 Windows 内核逆向出身的人，用做 devirtualizer 的方法论去做 coding agent，然后拿出实验证明：**换一个编辑工具的表示方式，比换一个模型更有效**——把「harness 工程」从直觉变成了可复现的数字。

---

## 9. Anthropic 侧推动 agent 工程化的公开署名

**9a.《Building Effective Agents》**
- 发布日：**2024-12-19**（页面标注 "Published Dec 19, 2024"）
- 署名原文：**"Written by Erik S. and Barry Zhang."**（官方页面只给出 "Erik S."，全名 **Erik Schluntz** 见于二手转述，**【待核实：官方未在该页给出全名】**）
- 全文原句："This work draws upon our experiences building agents at Anthropic and the valuable insights shared by our customers, for which we're deeply grateful."
- 出处【一手】：<https://www.anthropic.com/engineering/building-effective-agents>
- 核心贡献：区分 **workflow**（预定义编排）与 **agent**（模型自行决定流程与工具），并给出 5 个可复用模式：prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer。同期 Simon Willison 的解读可作二手佐证 <https://simonwillison.net/2024/Dec/20/building-effective-agents/>

**9b.《Effective context engineering for AI agents》**
- 发布日：**2025-09-29**（页面标注 "Published Sep 29, 2025"）
- 署名原文：**"Written by Anthropic's Applied AI team: Prithvi Rajasekaran, Ethan Dixon, Carly Ryan, and Jeremy Hadfield, with contributions from team members Rafi Ayub, Hannah Moran, Cal Rueb, and Connor Jennings."** 并致谢 Molly Vorwerck、Stuart Ritchie、Maggie Vo。
- 出处【一手】：<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- 官方推广推文（同期）：<https://x.com/AnthropicAI/status/1973098580060631341>

**一句话「改变了什么」**
> 把行业话语从「prompt engineering」推到了「**context engineering**」——问题不再是「怎么问」，而是「在有限注意力预算里，把哪些 token 放进去」。这是 harness 工程被正式命名的时刻。

---

## 10. 其他必须出现在时间线上的人

### 10a. SWE-bench / SWE-agent 团队（Princeton NLP）

- **Carlos E. Jimenez** — SWE-bench 一作、SWE-agent 二作。Princeton。个人站 <https://www.carlosejimenez.com/>（301 → <https://closji.com/>，采集时该页无有效简历信息，**【公开资料有限】**）。
- **John Yang** — SWE-agent 一作、SWE-bench 二作。
- **Ofir Press** — SWE-bench / SWE-agent 通讯位作者。个人站自述：PhD 于 University of Washington（导师 Noah Smith）；代表作 SWE-bench（ICLR 2024 Oral）、SWE-agent（NeurIPS 2024，「the first open-source agent to beat the 10% accuracy threshold on SWE-bench」）、SciCode（NeurIPS 2024）、AlgoTune（NeurIPS 2025）。二手称 2026 年为 Princeton 博士后。【一手 + 二手】<https://ofir.io/about/>
- **Karthik Narasimhan** — ReAct / ToT / SWE-bench / SWE-agent / τ-bench 五篇的共同作者，是把这条线串起来的资深作者（arXiv 元数据实测）。
- 仓库事实【一手，GitHub API 实测】：
  - `SWE-bench/SWE-bench`（原 `princeton-nlp/SWE-bench`）**创建于 2023-10-04**，5,539 stars。
  - `SWE-agent/SWE-agent` **创建于 2024-04-02**，19,971 stars。
- **一句话**：> 他们把「agent 能不能干活」从演示视频变成了**可复现的分数**，并顺手证明了 ACI（agent-computer interface，即 harness）本身是独立于模型的自变量。

### 10b. Terminal-Bench 团队（Stanford × Laude Institute）

- 核心：**Mike A. Merrill**（论文一作，Stanford CS 博士后）、**Alexander G. Shaw**（Laude Institute）；顾问包含 **Ludwig Schmidt**（Stanford，论文末位作者）、**Andy Konwinski**（Laude Institute）。二手另提 Chris Rytting。【二手 + 论文作者表】
- 仓库 `harbor-framework/terminal-bench`（原 `laude-institute/terminal-bench`）**创建于 2025-01-17T22:34:26Z**，2,508 stars，官网 <https://www.tbench.ai>。【一手，GitHub API 实测】
- **Terminal-Bench 1.0 上线：2025 年 5 月**（官方 2.0 公告中提到「原始版本 5 月发布」；二手给出精确日 **2025-05-19**，**【待核实：精确到日的一手来源缺失】**）。
- **Terminal-Bench 2.0 + Harbor 发布：2025-11-07**（官方公告页日期 "Fri Nov 07 2025"，署名 Mike Merrill、Alex Shaw）。公告称社区已有 1,000 名 Discord 成员、100 名 GitHub 贡献者。【一手】<https://www.tbench.ai/news/announcement-2-0>
- 论文《Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces》**arXiv v1 2026-01-17**（arXiv:2601.11868），**85 位作者**（Mike A. Merrill + 84 人），**89 个任务**，摘要称前沿模型/agent 得分 **低于 65%**；ICLR 2026 会议论文。【一手】<https://arxiv.org/abs/2601.11868> / <https://openreview.net/pdf/417ac3236de7dbf3fc3414c51754dd239271663e.pdf>
- `harbor-framework/harbor` 仓库创建于 **2025-08-04**，3,723 stars。【一手，GitHub API 实测】
- **一句话**：> 把评测的战场从「改一个 Python repo 的 bug」搬到了**整个终端**——并且用 Harbor 把「benchmark」和「harness」正式拆成两件事。

### 10c. Peter Steinberger（pi 生态的引爆点）

- 奥地利程序员，OpenClaw 作者。项目改名链条【二手，Wikipedia】：**Warelay（2025-11-24）→ CLAWDIS（2025-12-03）→ Clawdbot（2026-01-02）→ Moltbot（2026-01-27，因 Anthropic 商标投诉）→ OpenClaw（2026-01-30）**。
- 规模：Wikipedia 引用「截至 2026-03-02，247,000 stars / 47,700 forks」。
- **2026-02-14** 宣布加入 OpenAI，并成立 **OpenClaw Foundation** 承接项目治理。
- 出处：<https://en.wikipedia.org/wiki/OpenClaw> ；另有 CNBC 综述 <https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbot-moltbook.html>
- **与 pi 的关系**：OpenClaw 内部的最小 agent 就是 pi（Earendil 官方公告原话），且 Mario Zechner 自述这是 pi 出圈的关键推力。**注意：Wikipedia 的 OpenClaw 条目本身并未提到 pi**，因此这一关联应引 Earendil / Mario 的一手表述。

### 10d. Armin Ronacher（mitsuhiko）

- Flask、Jinja2 作者；GitHub bio 自述「Creator of the Flask framework. Founder of @earendil-works」。【一手，GitHub API 实测】<https://github.com/mitsuhiko>
- 个人站自述：奥地利人、常驻维也纳；「For a decade, I've been working on Sentry…」；2025 年离开 Sentry（站内有 "Leaving" 2025 相关文章）；「I founded Earendil.」**【待核实：离开 Sentry 的确切日期】** <https://lucumr.pocoo.org/about/>
- 在 pi 仓库贡献榜排第二（454 次提交，GitHub API 实测）。
- **一句话**：> 上一代 Python 生态的地基作者（Flask），这一代选择去做 agent harness 的地基——并且用一家 Public Benefit Corporation 的壳，去解决 Mario 在 RoboVM 时代被灼伤过的那个问题：**开源项目商业化后会不会被闭源**。

### 10e.（可选）Simon Willison

- 未在任务清单内，但其博客是本领域**日期最可靠的二手索引**之一（例如对 Building Effective Agents 的当日解读 2024-12-20、对 aider 的 2024-07-31 记录）。做时间线交叉验证时值得作为辅助信源，但不建议作为唯一出处。<https://simonwillison.net/2024/Dec/20/building-effective-agents/>

---

## 附录 A：GitHub 硬数据快照（2026-08-01 通过 GitHub REST API 实测）

| 仓库 | 创建时间 | stars | 备注 |
|---|---|---|---|
| `langchain-ai/langchain` | 2022-10-17 | 143,121 | 首次提交 2022-10-24 |
| `Significant-Gravitas/AutoGPT` | 2023-03-16 | 185,746 | |
| `yoheinakajima/babyagi` | 2023-04-03 | 22,343 | |
| `Aider-AI/aider` | 2023-05-09 | 47,848 | 作者提交 12,649 / 次名 47 |
| `langchain-ai/langgraph` | 2023-08-09 | 38,590 | |
| `SWE-bench/SWE-bench` | 2023-10-04 | 5,539 | |
| `SWE-agent/SWE-agent` | 2024-04-02 | 19,971 | |
| `harbor-framework/terminal-bench` | 2025-01-17 | 2,508 | |
| `harbor-framework/harbor` | 2025-08-04 | 3,723 | |
| **`earendil-works/pi`** | **2025-08-09** | **81,525** | 原 `badlogic/pi-mono`，forks 10,065 |
| `earendil-works/absurd` | 2025-10-20 | 2,291 | |
| **`can1357/oh-my-pi`** | **2025-12-31** | **20,918** | forks 1,985 |
| `earendil-works/gondolin` | 2026-02-03 | 1,853 | agent sandbox microvm |

## 附录 B：本次未能确证 / 需要二次核实的条目清单

1. 姚顺雨任命腾讯的**精确日期**（12-07 内部 / 12-17 Bloomberg / 12-21 科学网）——建议 PPT 写「2025 年 12 月」。
2. 姚顺雨加入 OpenAI 的月份（2024-06 vs 2024-08）。
3. Anthropic《Building Effective Agents》中 "Erik S." 的全名是否为 Erik Schluntz（官方页面未写全名）。
4. Terminal-Bench 1.0 的精确上线日（2025-05-19 仅见于二手）。
5. Cognition 2026 年 260 亿美元估值轮的精确日期与「Devin 写 95% 代码」的口径。
6. `stencil.so` 与 Can Bölük 的确切关系（仅有 `blog.can.ac` 302 重定向这一条证据）。
7. Armin Ronacher 离开 Sentry 的确切日期。
8. libGDX 的「诞生年」（2009 中期起源说仅见二手；Wikipedia 的 "initial release 2014-04-20" 指的是 1.0 版本，不是项目起点）。
9. Paul Gauthier 的完整职业履历（Inktomi 之外的部分仅见二手汇编站）。
10. Toran Bruce Richards 2025–2026 年的动向（公开资料有限）。
