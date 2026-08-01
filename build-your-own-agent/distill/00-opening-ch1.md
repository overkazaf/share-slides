# 深度蒸馏 · 开篇 P1–4 + CH1 定义 P5–7

> 素材范围：`slides/s01-cover.html`、`s01b-thesis.html`、`s01c-about.html`、`s02-toc.html`、`s02b-ch1.html`、`s03-what-is-agent.html`、`s04-spectrum.html`；`script/00-opening.md`、`script/01-ch1.md`；`research/R04`、`R05`；`OUTLINE.md`、`NOTES.md`。
> 凡本次未在上述文件中核实到一手来源的，一律标「待核实」。

---

## 1. 本章一句话

**「是不是 agent」不是分类问题，是一个可测量的量：下一步由谁决定 —— 而这个量之所以值得测，是因为你唯一能自己攥住的工程杠杆（harness），正好长在「模型决定」那一侧。**

开篇四页 + CH1 三页，实质上只在做一件事：**把一个营销词收敛成一条可证伪的判据**，并顺手给出「为什么这条判据对听众有经济价值」（= 模型买不到差异化，壳才是你的）。

---

## 2. 论点链

### 论点 1 · 全场主张：模型定上限，harness 定兑现

**断言**：能力天花板由模型给定，实际交付由模型之外的那层壳决定；因此值得投入的不是训模型，是做 harness。

**凭什么**
- 页面一手：`s01b-thesis.html:17-18` —— 「16 个模型 × 180 个真实修 bug 任务，只换『编辑工具格式』一个变量」，同一模型 `6.7% → 68.3%`，全体平均 +15pp。
- 出处口径见 `script/00-opening.md:71`：Can Bölük《The Harness Problem》，2026-02-12；讲者自述「原文我核过，但我没有自己复跑」，且原博客已跳转 stencil.so。
- 反向证据同样是页面一手：`NOTES.md:80-84` —— Terminal-Bench 官方榜 22 个模型换 harness，**中位数只挪 5.39 分**，7 个模型 ≥10 分，最大 20.90 分；而同一 harness 换模型极差 **70.7pp**。故 NOTES 自己给出的结论是「模型是主项，harness 是约 1/4 量级的次项」。
- 「harness 空间不随模型变强而缩小」有独立一手支撑：`R04:74-85`，Anthropic《Harness design for long-running application development》(2026-03-24)，同一造应用任务：单 agent 20 分钟/$9 崩坏 vs 完整 harness 6 小时/$200 可用 vs V2 简化版 3h50m/$124.70 可用；原文 *"the space of interesting harness combinations doesn't shrink as models improve. Instead, it moves."*

**反方 / 边界**
- Bölük 原作者自陈「**越弱的模型收益越大**」(`NOTES.md:80`)，所以 6.7→68.3 是弱模型极值，不是普适倍数。
- 最扎心的反例在 `NOTES.md:89`：Gemini 3 Pro 套通用 harness 73.93%，套 Google 自家 Gemini CLI 只有 65.84% —— 说明 harness 的方向也可能是**负的**，不是「加了就赚」。
- ⚠️ **内部数字打架**：`script/00-opening.md:73` 说「同一个模型套四种 harness 极差 18.4pp」，而 `NOTES.md:81` 的口径是「22 个模型，中位数 5.39，最大 20.90」。两个口径（4 种 harness 的极差 vs 22 模型分布）不是同一个统计量，讲稿与备忘没有对齐，**上台前必须统一，否则会被当场问穿**。「18.4」在本次读到的文件中无一手出处 —— 待核实。
- 「全体平均 +15pp」只在 `s01b-thesis.html` 页面上出现，本次读到的 R04/R05 中未见对应一手条目 —— 待核实。

---

### 论点 2 · Agent 的最小定义 = 一个闭环，三个必要条件

**断言**：Agent = `模型决策 → tool_calls → 环境真实执行 → observation 回灌` 的循环；缺工具退成 chatbot，缺循环退成提示链，缺反馈退成开环生成。

**凭什么**
- 页面：`s03-what-is-agent.html:87-97` 的图例三条 + 「三者缺一，就不算 agent」。
- 循环骨架有三份可交叉印证的一手定义（`R05:30-55`）：Anthropic 三阶段 *gather context / take action / verify results*；Claude Agent SDK 五步循环 *"until it produces a response with no tool calls"*；OpenAI Agents SDK 三步循环，final output 判据 *"produces text output with the desired type, and there are no tool calls"*。
- 「harness」这个词本身也有官方定义可挂：`R05:36` —— *"Claude Code serves as the agentic harness around Claude: it provides the tools, context management, and execution environment…"*；`R04:50` HF 术语表给了公式 **Agent = Model + Harness**。
- 「上下文是这台机器唯一的内存 / append-only」有实现级证据：`R05:290` pi `session.ts:339` 追加 entry 时 `parentId: this.leafId`；`R05:254` Claude Code transcript 是 append-only JSONL。

**反方 / 边界**
- ⚠️ **本页自相矛盾**：标题下副文写「**判据只有一条**」(`s03:5`)，图例却写「**三者缺一**」(`s03:97`)。一条 vs 三条不是同一套判据 —— 「谁决定下一步」是决策权口径，「有工具/有循环/有反馈」是结构口径。**建议改口径**：三条是**结构必要条件**（长得像 agent），一条是**性质判据**（是不是 agent）。一个代码写死的 while 循环里塞工具和反馈，三条全满足，但依然是 workflow。这个反例讲出来，本页的严谨度立刻上一个台阶。
- OpenAI 的定义比这三条**多一条**（`R05:507`）：agent 还要能 *"recognize when a workflow is complete"* 并且 *"in case of failure, halt execution and transfer control back to the user"*。**「能把控制权交还给人」在本页图上完全没有**。
- 页面把「模型这轮不再要工具 ⇒ 循环收敛」画成唯一退出口 (`s03:75`)，这只是 `R05:59-68` 那张判停表 8 类里的 1 类（详见「被低估的点」②）。
- 口径诚实度这一点做得对：`script/01-ch1.md:38` 明说这不是某家官方架构图，是讲者为讲清楚做的抽象，定义边界来自 Anthropic《Building Effective Agents》，骨架可对照 pi-mono `packages/agent`。

---

### 论点 3 · 护栏必须装在「③ 环境执行」这一段

**断言**：权限、沙箱、审批要装在工具调用真正落地的那一格，装在别处都晚了（`s03:76`）。

**凭什么**
- 页面自己给的机理：`s03:60` —— 「副作用发生在这里」。①② 都还在「想」，只有 ③ 动了外面的世界。
- 更硬的一手机理在 `R05:464`（D5）：Claude Code 文档原文 *"Actions that affect remote systems (databases, APIs, deployments) **can't be checkpointed**, which is why Claude asks before running commands with external side effects."*
- 旁证：`R05:263` —— `/rewind` 的已知限制里，**Bash 命令造成的 `rm/mv/cp` 改动追不回来**；官方定位 checkpoint 是 "local undo"，Git 才是 "permanent history"。

**反方 / 边界**
- 这条在页面上是**断言，不是论证**。它成立的真正理由不是「副作用在这里」（这是同义反复），而是「**③ 是整条链上唯一不可回滚的一格**」。建议把讲法换成后者 —— 可证伪、可推广（凡是不可回滚的动作都要在执行前拦）。
- 边界：并非所有护栏都能后置到 ③。工具集的裁剪、`allowed-tools` 预授权 (`R04:66`) 本质是**前馈**护栏，装在 ② 甚至装在 harness 配置里。用 Böckeler 的分类学讲更准：**Guides（前馈，行动前引导）+ Sensors（反馈，行动后自纠）**，`R04:55`。「只装在 ③」是个过强的说法。

---

### 论点 4 · 「是不是 agent」是连续刻度，不是二选一

**断言**：Chatbot → 提示链 → 工作流 → Agent → 多智能体，是一条「决策权交出去多少」的连续谱；五个盒子只是采样点。

**凭什么**
- 分类依据是逐字一手：`R05:13`、`R05:149-150` —— workflow = *"systems where LLMs and tools are orchestrated through **predefined code paths**"*；agent = *"systems where LLMs **dynamically direct their own processes and tool usage**, maintaining control over how they accomplish tasks."*（Anthropic《Building Effective AI Agents》，2024-12-19）
- 页面把两端代价对称写全了（`s04:91-97`）：左端「可预测·可测试·可复现·便宜·出事好定位 / 代价：没写过的分支就抓瞎」，右端「能吃长尾·能自我纠错·能处理没预设过的情况 / 代价：贵·慢·难复现·出事难归因」。这与一手取舍原文一致（`R05:168`）：*"Agentic systems often trade latency and cost for better task performance."*
- 「连续」这一点讲稿反复强调（`script/01-ch1.md:62`），并主动承认可以做出卡在 03 和 04 之间的系统。
- 工程准则（`s04:106`）：不要问「该不该上 agent」，要问「这一段决策能不能写死」；正解是 **workflow 骨架 + 局部 agent**。这条有整张判据表撑腰：`R05:456-497` 的 D1–D7 / A1–A6 / N1–N5 / S1–S2，每条都挂了一手出处。

**反方 / 边界**
- ⚠️ **谱系条第 5 格是轴的断裂**（详见「最容易被挑刺的地方」）：多智能体并不比单 agent「更多把决策权交给模型」。
- ⚠️ **页面与讲稿对不上**：`s04:59-60` 在 03 号格里列了「提示链 / 路由 / 并行 / 编排者-执行者 / 评估-优化，**共五类**」，但 02 号格已经是提示链；而 `script/01-ch1.md:69` 的解释是「我把提示链拎出来当 02 了，所以 03 只剩四类」。**讲稿描述的是旧版页面**。要么改页面（03 写「另四类」），要么改讲稿。现状是同一页上提示链出现两次。
- 讲稿自己承认最弱的一环（`script/01-ch1.md:73`）：「怎么判断这一段能不能写死？我没有量化判据，这是经验活。」—— 但 `R05:456-497` 里其实已经有 20 条带出处的判据（尤其 D5 不可回滚副作用、D6 写操作串行化、S2 工具重叠而非工具数量）。**这是本章最大的一处素材浪费**：明明有可给的答案，讲稿却答了「没有」。

---

### 论点 5 · 开篇的元论点：结论先行 + 出处纪律

**断言**：把五条结论摆在第 2 页，把「二手转述的数字一律不上页」这条规矩摆在第 3 页 —— 可信度本身是这场分享的产品。

**凭什么**
- `s01c-about.html:15`：「凡是只在二手转述里见过的数字，一律不上页」。
- `NOTES.md:49-69` 是这条规矩的执行记录：两轮独立证伪式核查共打回 **49 条**（第一轮时间线/人物 18 条、第二轮模型数据 31 条），逐条比对后**没有一条落在幻灯片上**，并列了「故意没上页」的清单（如 Sonnet 5 的 HLE 34.6%/OSWorld 78.5% 实属 Sonnet 4.6；Devin「95%」实为 89%；gpt-oss-120b 官方 card 是 117B/5.1B）。
- 讲者对自己唯一的软肋也做了公开标注（`NOTES.md:102-105`）：P37 页脚四个 arXiv 编号来自研究笔记转述，未逐个点开验证。

**反方 / 边界**
- ⚠️ **口径不一致**：`s01c-about.html:42` 与 `script/00-opening.md:103` 写的是「**18 处**经独立核查被打回」，`NOTES.md:49` 写的是「共 **49 条**（18 + 31）」。页面只说了第一轮的数字。被追问会当场对不上 —— 要么把页面改成 49，要么讲的时候明说「页面写的是第一轮 18 条，加上模型数据那轮一共 49 条」。
- 「16 份研究笔记」= R01–R10 + M01–M06，与 `research/` 目录实际文件数一致（已核）。

---

## 3. 被低估的点

### ① 判据的真正稀缺物不是「自主性」，是「不可回滚性」

页面把护栏挂在「副作用」上，但一手材料给的是更锋利的东西：`R05:464` 那句 *"can't be checkpointed"*，配合 `R05:263` 的 `/rewind` 限制（Bash 的 `rm/mv/cp` 追不回、subagent 的编辑不在本 session checkpoint 内、symlink 跳过不还原）。

推论：**整个 agent 工程的安全边界，等于「你能 checkpoint 到哪一层」**。Cursor 只 checkpoint 代码快照（`R05:311-314`）；Claude Code 把代码与对话拆成两个可独立回滚的维度（`R05:260`）；pi 干脆让日志本身就是树（`R05:283-292`）。这三者不是功能差异，是**可回滚边界**的三个位置。CH1 只要埋一句「护栏 = 不可回滚点的前置闸门」，CH3 的 loop/graph 两页就有了统一的解释轴。

### ② 「判停」不是一个布尔值，是一个枚举 —— 而且是 harness 最诚实的自画像

`s03:75` 只画了「模型不再要工具 ⇒ 退出」。真实一手（`R05:59-70`）有八类：无 tool_call / 显式 done 工具 / max_turns / **预算上限 `max_budget_usd`（且子 agent 花费计入总额）** / 用户中断 steering / 错误终止 / 宿主关闭 `worker_shutting_down` / 结构化输出重试耗尽。

最有讲头的一条：Claude Agent SDK 的 `ResultMessage.subtype` 就是现成的判停枚举 —— `success` / `error_max_turns` / `error_max_budget_usd` / `error_during_execution` / `error_max_structured_output_retries`，**且只有 `success` 携带 `result` 字段**。

再叠一个对照：OpenAI Agents SDK `DEFAULT_MAX_TURNS = 10`（`run_config.py:43`），而 Claude Agent SDK **默认无上限**。同一个「循环」，两家的默认安全姿态相反 —— 这一句话就能让听众意识到「判停」是设计决策而非实现细节。

### ③ 多智能体的收益方向，与谱系条的方向相反

`s04:80` 已经写对了一半：「主收益是上下文隔离，不是人多力量大」。但更反直觉的是 **2026 年的收敛结论**（`R05:394`，Cognition《Multi-Agents: What's Actually Working》2026-04-22）：

> *"Multi-agent systems work best today when **writes stay single-threaded** and the additional agents contribute **intelligence rather than actions**."*

意思是：**多智能体真正работающая 的形态，是把「动作权」收回来、只把「判断力」分出去** —— 这在「决策权交出去多少」这条轴上是**往左走**，不是往右走。

配套的两条硬旁证：
- 对手方观察（`R05:376`，Cognition 2025-06-12）：Claude Code 的 subagent *"never does work in parallel… usually only tasked with answering a question, not writing any code."* 而 Anthropic 自己说 *"Subagents act as intelligent filters"*（`R05:345`）—— **对撞的两派在这一点上其实完全一致**。
- 数量级（`R04:120` / `R05:430`）：subagent 只回传 **1,000–2,000 tokens** 的凝练摘要。这才是「隔离」的实际单位。

---

## 4. 最容易被挑刺的地方 + 怎么答

### 挑刺 A（最致命）：「你的谱系条第 5 格坐标轴断了」

**质疑**：轴写的是「谁决定下一步」，从左到右是决策权递交。但 05 多智能体相对 04 单 agent，交出去的**不是决策权，是并行度和上下文隔离**。按你自己的轴，多智能体应该跟 04 同刻度甚至更左。

**怎么答（认下来，然后升级）**：
> 「说得对，这一格我画在轴上是有妥协的。多智能体加的不是决策权，是**隔离度**。而且 2026 年的收敛结论恰恰是反的 —— Cognition 那句 *writes stay single-threaded, additional agents contribute intelligence rather than actions*，本质是把动作权收回来、只把判断力分出去，在我这条轴上是**往左走**。所以准确的说法是：**05 不是 04 的延长线，是 04 的正交维度**。我把它并排画，是为了让大家在同一页看到全部形态，代价是这一格的轴义不严格。CH3 那页会把它单独拎出来对撞。」

配套加固：`R05:171` 那条误引警告可以顺手送出去 —— **orchestrator-workers 是 workflow，不是 multi-agent**，编排骨架仍写在代码里，只有子任务的划分交给中心 LLM。这句话一说，听众会相信你分得清层级。

### 挑刺 B：「判据到底是一条还是三条？」

**怎么答**：
> 「三条是**结构必要条件** —— 长得像 agent 要有工具、有循环、有反馈。一条是**性质判据** —— 是不是 agent，看下一步由谁决定。反例现成：一个 for 循环里塞 read/bash、每轮把结果回灌，三条全满足，但路径写死在代码里，它是 workflow。所以三条筛形态，一条定性质。」（页面建议改：把副标改成「结构上三条，性质上一条」。）

### 挑刺 C：「6.7% → 68.3% 是不是标题党？」

**怎么答**（`NOTES.md:87` 的现成答法，照抄即可）：
> 「那是最弱模型上的极值，原作者自己写了『越弱的模型收益越大』。Terminal-Bench 官方榜 22 个模型换 harness 的中位数只挪 5.39 分。两个数我都放上来了，就是不想只讲好听的。诚实的结论是：模型是主项，harness 是约 1/4 量级的次项 —— 但主项你买不到差异化，次项才是你能攥住的。」
> ⚠️ 上台前先把讲稿里那个「18.4pp」和备忘里的「5.39 / 20.90 / 70.7pp」统一，别两套数并存。

### 挑刺 D：「Anthropic 的定义凭什么算数？」

**怎么答**（`script/01-ch1.md:65` 已备好，态度是加分项）：
> 「它是一篇 2024 年 12 月的工程博客，不是标准，也不是论文。我用它是因为它够干脆 —— *predefined code paths* vs *dynamically direct their own processes*，一句话就能落刀。学术界的 agent 定义范围宽得多。我采的是这个口径，全场都按这个口径。」
> 可加一句 OpenAI 的交叉印证（`R05:506`）：*"Applications that integrate LLMs but don't use them to control workflow execution—simple chatbots, single-turn LLMs, or sentiment classifiers—are not agents."* 两家独立表述、同一条边界。

### 挑刺 E：「RAG 算不算？Claude Code / Cursor 落在哪格？」

现成答案质量已经够高（`script/01-ch1.md:42`、`:75`），照讲即可：标准 RAG 检索一次生成一次 → 不算；能自己决定检索几轮 → 滑到 agent 侧。Claude Code 主体在 04，内部大量写死的 workflow 段落 —— 这正是「workflow 骨架 + 局部 agent」的现实样子。

---

## 5. 可以砍掉的

| 位置 | 判断 | 理由 |
|---|---|---|
| **P4 目录里「编号顺序和视觉顺序不一样」那段解释**（`script/00-opening.md:130-131`、`:139`） | **砍**，或压成半句 | 这是排版事故的补丁，不是内容。花 15 秒教听众读版式，收益为零。真要修，改页面（把 CH1–CH7 按视觉顺序排）比在台上解释便宜。 |
| **P5 章扉页整页**（`s02b-ch1.html`） | **压到 10 秒**（讲稿自己定的是 30 秒） | 页面唯一的新信息是那句承诺（判据只有一条），而它在 P6 副标题里会原样再出现一次。进度点的视觉约定说一次就够。 |
| **P3「你能带走什么」四条**（`s01c-about.html:21-26`） | **砍到两条** | 四条里「共同词汇」「决策表」是真承诺，「选型依据」「能抄的工程模式」实际是 CH5/CH7 的预告，与 P4 目录重复。开篇连着三页（P2 结论 / P3 收获 / P4 目录）都在做「预告」，密度太低。 |
| **P1 封面副标题里的五个术语罗列** | 保留但**不要念** | 讲稿花了一段说「现在听不懂没关系」（`script/00-opening.md:19`）。这段安抚本身比术语更占时间；扫一眼就过。 |
| **P2 第 4、5 条**（验证器 / 「壳只能自己焊」） | **保留，但只念标题** | 这两条的证据分别在 P27 和 P31/P39，此处展开等于讲两遍。第 1–3 条是 CH1–CH3 的直接前提，值得慢讲。 |
| **不要砍**：P2 第 1 条的双向数字、P6 的三条必要条件、P7 的两端代价对称注解 | — | 这三处是全场可信度的承重墙。尤其 P7 两端代价，`script/01-ch1.md:63` 说得对：「这页的诚实度全在这两列小字上」。 |

**净效果**：开篇 4 页从「结论 + 自我介绍 + 收获 + 目录」压成「结论 + 一句自我定位 + 目录」，能省下的时间正好补给 P7 的谱系条断裂说明和判停枚举 —— 都是提升严谨度的地方。

---

## 6. 接到下一章的那一句

> 「这条边界画完了，但它是**画在 2026 年这个时间点上的**。`predefined code paths` 和 `dynamically direct their own processes` 这两句话，是 Anthropic 在 2024 年 12 月写下的 —— 那之前，大家想的是『让模型自己想办法』；那之后，重心整个搬到了『工程化那层壳』。所以下一章我不讲观点，只用**可核查的日期**把这段位移串一遍：它是怎么从会推理，到会动手，到撞墙，再到 harness 成为一等公民的。」

（衔接依据：`OUTLINE.md:39-40` 的 CH2 论点行、`s02-toc.html:32-33`。若要给 CH2 埋一个具体钩子，`NOTES.md:111` 那条最硬 —— **2025-09-29 一天之内三件事**：Anthropic 发 context engineering 博客、SDK 改名 Claude Agent SDK、Claude Code 2.0。这三件事在 `R04:32`、`R04:109`、`R05:268` 都有独立一手锚点。）

---

## 附：本章需要在上台前处理的四处不一致（按优先级）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| 1 | `script/00-opening.md:73` vs `NOTES.md:81` | 「四种 harness 极差 18.4pp」 vs 「22 模型中位数 5.39 / 最大 20.90」，且 18.4 无一手出处（待核实） | 统一口径，只讲 NOTES 那套（有 22 个样本、有分布） |
| 2 | `s04-spectrum.html:59-60` vs `script/01-ch1.md:69` | 页面 03 格列了含提示链在内的五类，讲稿说 03 只剩四类 | 改页面文字为「另四类：路由 / 并行 / 编排者-执行者 / 评估-优化」 |
| 3 | `s01c-about.html:42` vs `NOTES.md:49` | 「18 处被打回」 vs 「共 49 条」 | 页面改 49，或讲的时候补一句分轮口径 |
| 4 | `s03-what-is-agent.html:5` vs `:97` | 「判据只有一条」 vs 「三者缺一」 | 副标改为「结构上三条，性质上一条」，并准备好那个 for-loop 反例 |
