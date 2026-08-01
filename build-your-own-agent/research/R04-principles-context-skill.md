# R04 · Context Engineering / Harness / SKILL 的原理与出处

> 研究日期：2026-08-01
> 语言：简体中文（专有名词保留英文）
> 原则：每条日期/版本/人名/数字都附可核查 URL；不确定的标「⚠️ 待核实」；区分「预印本日 / 正式发表日 / 官方博客发布日」。

---

## 0. 一页结论（讲给工程师的版本）

1. **Harness ≠ 新概念，是老词新用**。它继承软件工程的 *test harness*（把被测物放进可控环境里跑）。在 LLM 语境下最早稳定出现的是「评测 harness」（EleutherAI `lm-evaluation-harness`，仓库建于 2020-08-28）。而**用 harness 指「agent 的外壳」是 2025 下半年才成为主流**——在此之前学术与评测圈（METR/ARC Evals、Anthropic 自己）一律用 **scaffold / scaffolding**。
2. **Context Engineering 是 2025 年 6 月被两条推文命名的**：Tobi Lütke（2025-06-19 UTC）先提，Karpathy（2025-06-25 UTC）跟进 "+1"。Anthropic 在 2025-09-29 给了它机制化定义：上下文是**有限资源**，因为 transformer 的 n² 注意力被摊薄 + 训练时长序列样本稀缺，形成「性能斜坡而非悬崖」。
3. **上下文腐化是有实证的**，不是玄学。锚点两篇：Liu et al. 2023《Lost in the Middle》（位置效应，U 型曲线，最差时不如不给文档）+ Chroma 2025-07-14《Context Rot》（18 个模型，长度本身就是自变量）。
4. **Compaction 有 6 条主流路线**，每条的成本结构不同：整段摘要（花一次推理）、工具结果清理（零推理但毁 KV cache）、外部记忆卸载、文件系统当记忆（Manus）、递诵（recitation）、子代理隔离。多智能体隔离是**有争议**的：Anthropic 说 +90.2%，Cognition 说别这么干。
5. **SKILL.md 的核心不是「写提示词」，是「分级加载的文件系统协议」**。官方三级：metadata ~100 tokens 常驻 → SKILL.md 正文 <5k tokens 触发时加载 → 资源/脚本按需（脚本只有 stdout 进上下文，代码本身零 token）。
6. **Skill 比 system prompt 强的本质是「延迟计费 + 组合性」**，不是「更聪明」。官方原话（Claude Code 文档）：*"Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it."*
7. **Progressive disclosure 是 1980 年代 HCI 的老概念**，可追到 Carroll & Carrithers 的 "Training Wheels"（CACM, 1984-08），Nielsen 在 2006-12-03 给了通用表述。有趣反差：Nielsen 说**超过 2 级就会迷路**，而 Agent Skills 明确用 **3 级**——因为读者从人变成了会 `grep` 的模型。

---

## 1. Harness：词源、准确含义、组成

### 1.1 溯源证据链（按时间排）

| 时间 | 事件 | 用词 | 出处 |
|---|---|---|---|
| （长期） | 软件工程中的 *test harness*：把被测代码放进受控环境执行并采集结果 | harness | 行业通用术语，本报告不主张单一首创者 |
| **2020-08-28** | EleutherAI 建 `lm-evaluation-harness` 仓库（`created_at: 2020-08-28T00:09:15Z`，描述 "A framework for few-shot evaluation of language models."） | **evaluation harness** | GitHub API `https://api.github.com/repos/EleutherAI/lm-evaluation-harness`；仓库 https://github.com/EleutherAI/lm-evaluation-harness |
| **2023-10-10** | SWE-bench 论文（Jimenez et al.），配套开源「evaluation harness」 | evaluation harness | https://arxiv.org/abs/2310.06770 |
| **2023-12-18** | ARC Evals / METR《Evaluating Language-Model Agents on Realistic Autonomous Tasks》（Kinniment et al.）：把 GPT-4 与「scaffolding software」组合成 agent | **scaffolding**（非 harness） | https://arxiv.org/abs/2312.11671 |
| **2025-01-06** | Anthropic《Claude SWE-Bench Performance》（Erik Schluntz）：全文用 scaffold/scaffolding，**未出现 "harness"** | **scaffold** | https://www.anthropic.com/engineering/swe-bench-sonnet |
| **2025-09-29** | Anthropic《Building agents with the Claude Agent SDK》（Thariq Shihipar）：出现一次 "the agent harness that powers Claude Code (the Claude Code SDK)" | **agent harness**（官方早期用例） | https://claude.com/blog/building-agents-with-the-claude-agent-sdk |
| **2025-11-26** | Anthropic《Effective harnesses for long-running agents》（Justin Young）：harness 进标题 | harness | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| **2026-02-05** | Mitchell Hashimoto《My AI adoption journey》提出 **harness engineering** | harness engineering | https://mitchellh.com/writing/my-ai-adoption-journey |
| **2026-03-24** | Anthropic《Harness design for long-running application development》（Prithvi Rajasekaran） | harness | https://www.anthropic.com/engineering/harness-design-long-running-apps |
| **2026-04-02** | Birgitta Böckeler（Thoughtworks）在 martinfowler.com 给出 inner/outer harness、guides/sensors 框架 | harness 分类学 | https://martinfowler.com/articles/harness-engineering.html |
| **2026-05-25** | Hugging Face《Harness, Scaffold, and the AI Agent Terms Worth Getting Right》（Sergio Paniego, Aritra Roy Gosthipaty）给出 harness/scaffold 的分层定义 | harness vs scaffold | https://huggingface.co/blog/agent-glossary |

**对「谁最早」的诚实回答**：
- 「评测 harness」义 → 可核查的最早锚点是 EleutherAI（2020-08）。
- 「agent 外壳」义 → **没有找到证据支持"OpenAI evals 最早这么用"这一说法**（o1 System Card, arXiv:2412.16720 文中未见 "harness"/"agentic harness"）。⚠️ **待核实**：是否存在 2024 年以前的公开 "agent harness" 用例。目前证据显示 2023–2024 主流用词是 **scaffold**，harness 的语义迁移发生在 2025 H2 → 2026 H1。
- 中文英文社区都有人把 harness 归给 Anthropic。可支撑的说法是：**Anthropic 是把它写进官方工程博客标题、并给出系统性方法论的第一方**（2025-11-26 起），而不是造词者。
- ⚠️ 英文维基百科有 "Agent harness" 词条，明确写「归属存在争议（attribution is contested）」，列出 Hashimoto（2026-02）、LangChain 的 Vivek Trivedy、OpenAI 2026 工程报告三条线。维基不是一手源，仅供交叉印证：https://en.wikipedia.org/wiki/Agent_harness

### 1.2 Harness 到底包含什么（每项都有出处）

**最短定义（HF 术语表, 2026-05-25）**
> Harness：*"The execution layer inside the agent: it calls the model, handles its tool calls, decides when to stop."*
> Scaffold：*"The behavior-defining layer around the model: system prompt, tool descriptions, how the model's responses get parsed, what it remembers across steps (context management)."*
> 公式：**Agent = Model + Harness**
> — https://huggingface.co/blog/agent-glossary

**最宽定义（Böckeler, 2026-04-02）**
> Harness = *"everything in an AI agent except the model itself"*；分 **inner harness**（模型厂商内置：system prompt、代码检索机制、编排系统）与 **outer harness**（使用者自建：skills、结构性测试、linter/类型检查、LSP、自定义 review agent、性能测试、日志规范）。
> 又分 **Guides**（前馈：*"anticipate the agent's behaviour and aim to steer it before it acts"*）与 **Sensors**（反馈：*"observe after the agent acts and help it self-correct"*）。
> — https://martinfowler.com/articles/harness-engineering.html

**组件清单（合并官方出处）**

| 组件 | 官方出处 |
|---|---|
| **Agent loop**：`gather context → take action → verify work → repeat` | Anthropic Agent SDK 博客, 2025-09-29 |
| **工具集与工具描述**（自洽、少重叠、参数无歧义；"若人类工程师都说不清该用哪个工具，agent 更不行"） | Anthropic《Effective context engineering》, 2025-09-29 |
| **System prompt 组装 / altitude**（在"硬编码脆弱逻辑"与"含糊到假设共识"之间的 Goldilocks 区；用 XML 标签或 Markdown 标题分节） | 同上 |
| **上下文管理**：compaction、tool-result clearing、memory 工具、file system | Anthropic Platform 文档 https://platform.claude.com/docs/en/build-with-claude/compaction |
| **权限 / 批准**：`allowed-tools` 预授权、workspace trust、`disableSkillShellExecution` 策略 | Claude Code 文档 https://code.claude.com/docs/en/skills |
| **子代理 / 上下文隔离**：并行 + 上下文清洁；子代理返回 1,000–2,000 tokens 的凝练摘要 | Anthropic《Effective context engineering》, 2025-09-29 |
| **持久化**：git 仓库、JSON feature list、`claude-progress.txt`、`init.sh` | Anthropic《Effective harnesses for long-running agents》, 2025-11-26 |
| **校验（verification）**：规则型反馈（lint）、视觉反馈（截图/Playwright）、LLM-as-judge | Anthropic Agent SDK 博客, 2025-09-29；Anthropic《Harness design》, 2026-03-24 |
| **UI / 交互层** | ⚠️ **待核实**：常被口头算进 harness，但上述一手源的正式定义**都未把 UI 列入**。HF 术语表把 harness 限定为「执行层」，Böckeler 限定为「模型之外的一切」（这才涵盖 UI）。演讲中若提 UI 建议用 Böckeler 的宽定义。 |

### 1.3 一个反直觉的实证：harness 的空间不会随模型变强而缩小

Anthropic《Harness design for long-running application development》（2026-03-24, Prithvi Rajasekaran）用同一个"造应用"任务对比：

| 配置 | 时长 | 成本 | 结果 |
|---|---|---|---|
| 单 agent | 20 分钟 | $9 | 核心功能崩坏 |
| 完整 harness（V1，planner/generator/evaluator 三 agent） | 6 小时 | $200 | 可用应用 |
| V2 harness（简化，Opus 4.6） | 3h50m | $124.70 | 可用 |

关键句：
> *"every component in a harness encodes an assumption about what the model can't do on its own."*
> *"the space of interesting harness combinations doesn't shrink as models improve. Instead, it moves."*
— https://www.anthropic.com/engineering/harness-design-long-running-apps

**讲稿用法**：这是对「模型变强 → 脚手架会被拆掉」这一预测的直接反例。V2 的确拆掉了 sprint 分解，但整体 harness 没消失，只是重心迁移。

---

## 2. Context Engineering：出处与核心论点

### 2.1 命名时刻（推文，附 UTC 时间）

| 人 | 时间（UTC） | 内容 | 出处 |
|---|---|---|---|
| Tobi Lütke（Shopify CEO） | **2025-06-19 03:01:43** | *"I really like the term 'context engineering' over prompt engineering. It describes the core skill better…"* | 推文 https://twitter.com/tobi/status/1935533422589399127 （时间由 snowflake ID `1935533422589399127` 解码得出；转引自 Simon Willison https://simonwillison.net/2025/Jun/27/context-engineering/ ） |
| Andrej Karpathy | **2025-06-25 15:54:25** | *"+1 for 'context engineering' over 'prompt engineering'. People associate prompts with short task descriptions you'd give an LLM in your day-to-day use. When in every industrial-strength LLM app, context engineering is the delicate art and science of filling the context window…"* | 推文 https://twitter.com/karpathy/status/1937902205765607626 （时间由 snowflake ID 解码；转引自 Simon Willison 同上） |

Karpathy 列举的 context engineering 组成（转引自 Simon Willison 2025-06-27 的整理）：任务描述与说明 / few-shot 示例 / RAG / 相关多模态数据 / 工具 / 状态与历史 / 信息压缩 / 对 LLM 心理特性的理解。

> ⚠️ **注意**：`x.com` 直接抓取返回 HTTP 402，无法拿到全文原文快照。上面 Karpathy 首句为搜索结果与 Simon Willison 引用一致的部分；**推文完整原文请以推文本身为准**。时间戳是从推文 ID 用 Twitter snowflake 算法（epoch=1288834974657ms）本地推算的，可独立复算。

### 2.2 Anthropic 官方论点（一手，机制层）

《Effective context engineering for AI agents》
- 发布：**2025-09-29**
- 作者：Anthropic Applied AI team — Prithvi Rajasekaran, Ethan Dixon, Carly Ryan, Jeremy Hadfield（另有 Rafi Ayub, Hannah Moran, Cal Rueb, Connor Jennings 等贡献）
- URL：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

**核心论点（机制，不是口号）**

1. **定义迁移**：prompt engineering = "writing and organizing LLM instructions"（一次性任务）；context engineering = *"curating and maintaining the optimal set of tokens (information) during LLM inference"*（在 agent 循环里反复策展）。
2. **注意力预算（attention budget）**：把 LLM 类比人类工作记忆，注意力是有限预算。
3. **为什么会腐化（两条机制）**：
   - 架构层：transformer 每个 token 要 attend 到所有 token，**n 个 token 有 n² 对关系**；上下文变长，捕捉这些关系的能力被摊薄。
   - 训练分布层：模型在短序列上见得多，处理长程依赖的专用参数少 → 所以是 **"performance gradient rather than a hard cliff"**（性能斜坡，不是悬崖）。
4. **System prompt 的"海拔（altitude）"**：两种失败模式——过度规定（硬编码脆弱逻辑）与规定不足（假设共享上下文）；目标是 *"specific enough to guide behavior effectively, yet flexible enough to provide the model with strong heuristics"*。
5. **Just-in-time 检索**：从"推理前 embedding 预取"转向"运行时用轻量标识符（文件路径、query、链接）动态加载"。类比人类：*"we generally don't memorize entire corpuses of information, but rather introduce external organization and indexing systems like file systems, inboxes, and bookmarks."*
6. **长任务三招**：compaction、structured note-taking（如 `NOTES.md`）、sub-agent 架构（子代理返回 **1,000–2,000 tokens** 的摘要）。文中给的例子：Claude 玩 Pokémon 的 agent 跨 **1,234 步**维持精确计数；Claude Code 用「压缩上下文 + 最近访问的 5 个文件」重启。
7. **总纲**：*"Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome."*

### 2.3 Manus 的六条工程教训（一手，生产环境）

《Context Engineering for AI Agents: Lessons from Building Manus》
- 发布：**2025-07-18**（周五）
- 作者：Yichao 'Peak' Ji（Manus 联合创始人 / 首席科学家）
- URL：https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

| # | 教训 | 机制 | 硬数字 |
|---|---|---|---|
| 1 | **Design Around the KV-Cache** | 稳定前缀（不要在 system prompt 里放时间戳）；上下文只追加（append-only）；确定性序列化；自托管开 prefix caching（vLLM） | Manus 平均 **input : output ≈ 100 : 1**；Claude Sonnet 上 **cached $0.30/MTok vs uncached $3.00/MTok（10×）** |
| 2 | **Mask, Don't Remove** | 不动态增删工具定义（会击穿 KV-cache 且模型会引用不存在的历史工具），改用**状态机 + 解码时 logits masking** + 响应预填充（Auto/Required/Specified）+ 一致的工具命名前缀 | — |
| 3 | **Use the File System as Context** | 文件系统 = 无限、持久的外部记忆；把重上下文的观测（网页、PDF）从上下文里丢掉，但**保留 URL/路径** → 可恢复的压缩 | — |
| 4 | **Manipulate Attention Through Recitation** | 全程创建并反复重写 `todo.md`，把目标推进模型的近端注意力窗口，抵抗 lost-in-the-middle 漂移 | 平均任务约 **50 次工具调用** |
| 5 | **Keep the Wrong Stuff In** | 保留失败动作与错误栈；模型看到错误会隐式更新内部信念，降低重复概率。错误恢复被视为真正 agentic 行为的标志 | — |
| 6 | **Don't Get Few-Shotted** | 上下文里高度重复的同构模式会让模型过度泛化/幻觉；在序列化模板、措辞、动作顺序上注入受控变异 | — |

其他可引句：框架被重写 **4 次**；他们戏称这个手工架构搜索过程为 **"Stochastic Graduate Descent"**。
补充推文（**2025-07-23 16:41 UTC**，由 ID `1948060791636410404` 解码）：*"Context engineering can also overfit - not just to specific model families, but also to today's model limitations via premature optimization."* — https://x.com/peakji/status/1948060791636410404

### 2.4 社区分类法

- **LangChain《Context Engineering for Agents》，2025-07-02**（署名 The LangChain Team；相关演讲由 Lance Martin 主讲）：四类 **Write / Select / Compress / Isolate**。
  - Write：*"Saving it outside the context window to help an agent perform a task."*（scratchpad、memory）
  - Select：*"Pulling it into the context window…"*（memory 选取、工具选取用 RAG、知识检索）
  - Compress：*"Retaining only the tokens required to perform a task."*（摘要、裁剪）
  - Isolate：*"Splitting it up to help an agent perform a task."*（多 agent、沙箱、state schema）
  - URL：https://www.langchain.com/blog/context-engineering-for-agents
- **Drew Breunig《How Long Contexts Fail》，2025-06-22**：四种失效模式 —— Context **Poisoning**（幻觉进入上下文并被反复引用）/ **Distraction**（上下文长到压过训练所学）/ **Confusion**（无关信息被拿去生成）/ **Clash**（上下文内部互相冲突）。
  URL：https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html

---

## 3. 上下文腐化的实证研究

### 3.1 《Lost in the Middle: How Language Models Use Long Contexts》

- **作者**：Nelson F. Liu (Stanford), Kevin Lin (UC Berkeley), John Hewitt (Stanford), Ashwin Paranjape (Samaya AI), Michele Bevilacqua (Samaya AI), Fabio Petroni (Samaya AI), Percy Liang (Stanford)
- **arXiv v1（预印本）**：**2023-07-06**；**v3**：2023-11-20 — https://arxiv.org/abs/2307.03172
- **正式发表**：Transactions of the ACL (TACL)。⚠️ arXiv 页面 journal-ref 显示 "TACL, 2023"，而通行引用为 **TACL Vol. 12 (2024), pp. 157–173**。**卷期以 TACL 官网为准，此处标待核实**。
- 项目页：https://nelsonliu.me/papers/lost-in-the-middle

**结论与硬数字（均出自论文正文 §2.3 / Table 1）**

- **U 型曲线**：性能在相关信息位于**最开头（primacy bias）或最末尾（recency bias）**时最高，位于**中间**时显著下降。
- 原文：*"For example, when relevant information is placed in the middle of its input context, GPT-3.5-Turbo's performance on the multi-document question task is lower than its performance when predicting without any documents (i.e., the closed-book setting; 56.1%)."*
- 原文：*"GPT-3.5-Turbo's multi-document QA performance can drop by more than 20%—in the worst case, performance in 20- and 30-document settings is lower than performance without any input documents."*
- **Table 1（closed-book / oracle 准确率）**：

| 模型 | Closed-Book | Oracle |
|---|---|---|
| LongChat-13B (16K) | 35.0% | 83.4% |
| MPT-30B-Instruct | 31.5% | 81.9% |
| GPT-3.5-Turbo | **56.1%** | 88.3% |
| GPT-3.5-Turbo (16K) | 56.0% | 88.6% |
| Claude-1.3 | 48.3% | 76.1% |
| Claude-1.3 (100K) | 48.2% | 76.4% |

- **扩展上下文模型并不更会用上下文**：*"Extended-context models are not necessarily better at using input context."* 在 10 / 20 文档设置下，GPT-3.5-Turbo（4K）与 GPT-3.5-Turbo-16K 的位置-性能曲线几乎重合。
- **合成 key-value 检索任务**（75/140/300 对 UUID）：Claude-1.3 与 Claude-1.3(100K) 几乎全对；GPT-3.5-Turbo / GPT-3.5-Turbo(16K) / MPT-30B-Instruct 在中间位置最差。
- **RAG 边际收益递减**：检索 50 篇 vs 20 篇，仅提升 **~1.5%（GPT-3.5-Turbo）/ ~1%（claude-1.3）**。原文：*"model performance saturates long before retriever recall saturates."*
- **一个可操作的缓解手段**：**query-aware contextualization**（把 query 同时放在文档**前和后**）→ key-value 任务接近完美，但对 multi-doc QA 几乎无改善。
- 另外：encoder-decoder 模型在**训练序列长度以内**对位置更鲁棒，超出训练长度后同样出现 U 型；即使是未指令微调的 base 模型也有 U 型。

### 3.2 《Context Rot: How Increasing Input Tokens Impacts LLM Performance》

- **作者**：Kelly Hong, Anton Troynikov, Jeff Huber（Chroma 技术报告）
- **发布**：**2025-07-14**
- URL：https://research.trychroma.com/context-rot （301 → https://www.trychroma.com/research/context-rot ）；复现代码 https://github.com/chroma-core/context-rot

**评测规模**：**18 个模型** — Claude Opus 4 / Sonnet 4 / Sonnet 3.7 / Sonnet 3.5 / Haiku 3.5；o3、GPT-4.1（+mini/nano）、GPT-4o、GPT-4 Turbo、GPT-3.5 Turbo；Gemini 2.5 Pro / 2.5 Flash / 2.0 Flash；Qwen3-235B-A22B / 32B / 8B。

**六组实验设计**
1. **NIAH 扩展 · needle-question 语义相似度**（用 5 个 embedding 模型算余弦相似度，needle 相似度区间 0.445–0.829）
2. **干扰项（distractors）**：baseline（只有 needle）/ 1 个干扰项 / 4 个干扰项，随机位置
3. **needle-haystack 主题相关性**：Paul Graham 随笔 vs arXiv 论文两种 haystack
4. **haystack 结构**：逻辑连贯的原文 vs 句子随机打乱
5. **LongMemEval**：focused（~300 tokens）vs full（~113k tokens），306 条清洗后 prompt
6. **重复词复制任务**：25–10,000 词序列中插入 1 个唯一词，要求原样复现

**核心结论**
> *"Models do not use their context uniformly; instead, their performance grows increasingly unreliable as input length grows."*
> *"LLMs do not maintain consistent performance across input lengths."*

- **即使只有 1 个干扰项**也会低于 baseline；4 个干扰项进一步复合退化。
- **needle 与 question 语义相似度越低，随长度增长衰减越快**。
- **反直觉**：把 haystack 句子**随机打乱**后，模型表现**反而更好**（比逻辑连贯的原文更好）。
- LongMemEval focused → full 之间 Claude 系掉幅明显；Claude Opus 4 在模糊时倾向保守弃权。
- 重复词任务：在 500–750 词区间开始生成**输入中根本不存在的词**；Claude Opus 4 有 **2.89%** 的拒答率，GPT-4.1 有 **2.55%**。

**Anthropic 官方对 context rot 的引述与定义**（Claude Cookbook）：
> *"as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases."*
— https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools

---

## 4. Compaction / 上下文压缩：主流做法分类与取舍

### 4.0 一张对照表

| 路线 | 代表实现 | 触发/默认值 | 成本 | 主要取舍 |
|---|---|---|---|---|
| A. 整段摘要（rolling summary） | Anthropic API `compact_20260112`；Claude Code auto-compact | 默认 `input_tokens = 150,000`，最小 50,000 | **多一次采样**（计费+延迟） | 高层事实保得住，冷僻细节丢失 |
| B. 工具结果清理（结构化裁剪） | Anthropic API `clear_tool_uses_20250919` | 默认 trigger 100,000 tokens；默认保留最近 **3** 个 tool_use | **零推理成本**（纯机械编辑） | **会击穿 prompt 前缀缓存**；仅适用于可重取的结果 |
| C. 外部记忆卸载 | Anthropic `memory_20250818` memory tool | agent 自主决定何时写 | 存储由调用方实现，写入不额外收费 | 需要模型自律；记忆质量取决于写入策略 |
| D. 文件系统当记忆 | Manus | 丢观测保 URL/路径 | 重取有往返开销 | **可恢复的"无损"压缩**；依赖来源仍可访问 |
| E. 递诵（recitation） | Manus `todo.md`；Anthropic `NOTES.md` | 每轮重写 | 每轮小额 token | 直接对抗 lost-in-the-middle；靠重复占用近端注意力 |
| F. 子代理隔离 | Anthropic orchestrator-worker；Claude Code `context: fork` | 每个子代理独立上下文窗口 | **token 消耗大幅上升** | 见 §4.6 的争议 |
| G.（补充）工具目录代码化 | Anthropic code execution with MCP | 工具定义变成文件系统上的 TS 文件 | 需要代码执行沙箱 | 150k → 2k tokens |

### 4.1 A/B/C 的官方机制与实测数字（一手）

**Compaction（官方 API 文档）** — https://platform.claude.com/docs/en/build-with-claude/compaction
> *"When compaction is enabled, Claude automatically summarizes your conversation when it reaches the configured token threshold. The API: 1. Detects when input tokens reach your specified trigger threshold. 2. Generates a summary… 3. Creates a `compaction` block containing the summary. 4. Continues the response with the compacted context."*
> *"The API automatically drops all content blocks prior to the `compaction` block."*
- 默认 trigger：`{"type": "input_tokens", "value": 150000}`；`value` 最小 50,000。
- 唯一支持的 trigger 类型是 `input_tokens`。
- 可选 `pause_after_compaction`（默认 false）、`instructions`（自定义摘要提示词，会**完全替换**默认提示词）。
- 计费：compaction 是**额外一次采样步骤**，计入速率限制与账单；`usage.iterations` 数组里会看到一个 `compaction` iteration 加一个 `message` iteration。
- Beta header：`compact-2026-01-12`。

**Tool-result clearing** — Claude Cookbook（官方）
> *"Tool-result clearing addresses the bloat from tool use itself… Clearing drops old, re-fetchable results while keeping the record that the call happened."*
- 类型 `clear_tool_uses_20250919`；默认 trigger 100,000 tokens；默认 `keep: {tool_uses: 3}`；可配 `clear_at_least`、`exclude_tools`（例如排除 memory）、`clear_tool_inputs`。
- **机制**：把 `tool_result` 内容块换成短占位符，**保留 `tool_use` 记录**（模型仍知道调用发生过）。不动 user 消息与 assistant 推理。
- **实测（cookbook 的 research agent 案例）**：清掉 8 次文件读取中的 7 次，单次释放 **~163K tokens**，上下文峰值 **335K → 173K（-48%）**。
- **代价**：无推理成本，但**使已缓存的 prompt 前缀失效**——所以要用 `clear_at_least` 保证每次清理"值回缓存重写"。
- Beta header：`context-management-2025-06-27`。

**Memory tool** — 类型 `memory_20250818`，客户端实现存储后端，命令集 `view / create / str_replace / insert / delete / rename`；系统提示会自动注入协议（"always view your memory directory before doing anything else"）。

**未做管理的 baseline（cookbook 实测）**：research agent 在大语料上——1M 窗口下完成，峰值 **335,279 tokens**（5 轮）；200K 窗口下**撞硬上限**（3 轮，168,242 tokens）。末态上下文构成：文件读取结果 **~322,946 tokens（96.3%）**、工具调用记录 ~6,287（1.9%）、agent 推理文本 ~5,660（1.7%）。
> **这是最好的一张 PPT 图**：96.3% 的上下文是工具输出，不是"对话"。

**官方效果数字**（《Managing context on the Claude Developer Platform》，**2025-09-29**）— https://claude.com/blog/context-management
- memory tool + context editing 组合：比 baseline **提升 39%**
- 仅 context editing：**提升 29%**
- 100 轮网页搜索评测中：**token 消耗降低 84%**，且完成了原本会因上下文耗尽而失败的工作流

### 4.2 D · 文件系统当记忆（Manus）

机制：把网页、PDF 这类"重"观测从上下文里删掉，**只保留 URL / 文件路径**——因为内容随时可重取，所以这是**可恢复的压缩**而非有损截断。
取舍：省 token，但增加往返；一旦来源失效就真丢了。
出处：https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

### 4.3 E · 递诵（recitation）

机制：把目标清单反复重写到上下文**尾部**，利用 recency bias 把注意力拉回目标，规避 lost-in-the-middle。Manus 用 `todo.md`；Anthropic 用 `NOTES.md` 一类的 structured note-taking。
取舍：每轮固定小额 token 成本，换取长任务的目标不漂移。

### 4.4 G · 工具目录代码化（token 效率的极端案例）

《Code execution with MCP: building more efficient AI agents》
- 发布：**2025-11-04**；作者：Adam Jones, Conor Kelly
- URL：https://www.anthropic.com/engineering/code-execution-with-mcp
- 机制：不再把所有 MCP 工具定义塞进上下文，而是把它们生成为文件系统上的 TypeScript 文件（`./servers/google-drive/getDocument.ts`），模型用 bash 按需读取；中间结果在执行环境里过滤/聚合，只有处理后的结果回到上下文。
> *"Models are great at navigating filesystems. Presenting tools as code on a filesystem allows models to read tool definitions on-demand, rather than reading them all up-front."*
- **硬数字：同一工作流 150,000 tokens → 2,000 tokens，降幅 98.7%。**

### 4.5 Claude Code 的具体实现（可讲的工程细节）

- Auto-compaction 后，Claude Code **重新挂载**每个 skill 的最近一次调用内容，**每个保留前 5,000 tokens，所有重挂 skill 共享 25,000 tokens 的总预算**，从最近调用的开始填；调过太多 skill 时，旧的会被整个丢弃。
  — https://code.claude.com/docs/en/skills
- Skill 正文一旦加载，**整个 session 都留在上下文里**（Claude Code 不会在后续轮次重读文件）：
  > *"When you or Claude invoke a skill, the rendered SKILL.md content enters the conversation as a single message and stays there for the rest of the session."*
  > *"Once a skill loads, its content stays in context across turns, so every line is a recurring token cost."*
- 重复调用同一 skill 且渲染内容相同 → 只追加一条"已加载"的短注记，不再复制正文（v2.1.202 起）。
- ⚠️ **待核实**：网上流传的 Claude Code 三层压缩（microcompact / full compact / session memory compact）与具体阈值公式（如 `autoCompactThreshold = effectiveWindow - 13,000`、200K 窗口约 167K 触发、缓冲区从 45,000 降到 ~33,000 tokens）**均来自第三方逆向分析博客，未在官方文档中找到对应表述**。上台前若要用这些数字，需自行验证。

### 4.6 F · 子代理隔离：一个真正的分歧点

**正方 — Anthropic《How we built our multi-agent research system》**
- 发布：**2025-06-13**；作者：Jeremy Hadfield, Barry Zhang, Kenneth Lien, Florian Scholz, Jeremy Fox, Daniel Ford
- URL：https://www.anthropic.com/engineering/multi-agent-research-system
- 数字：
  - *"multi-agent system with Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by **90.2%** on our internal research eval"*
  - *"agents typically use about **4×** more tokens than chat interactions"*；*"multi-agent systems use about **15×** more tokens than chats"*
  - BrowseComp 上，**token 用量单独解释 80% 的性能方差**，工具调用次数与模型选择解释另外 ~15%
- 论点：orchestrator-worker，子代理有独立上下文窗口，可并行探索、降低路径依赖。

**反方 — Cognition《Don't Build Multi-Agents》**
- 发布：**2025-06-12**（比 Anthropic 那篇早一天）；作者：Walden Yan
- URL：https://cognition.ai/blog/dont-build-multi-agents （301 → https://cognition.com/blog/dont-build-multi-agents ）
- 两条原则（原文）：
  1. *"Share context, and share full agent traces, not just individual messages"*
  2. *"Actions carry implicit decisions, and conflicting decisions carry bad results"*
- Flappy Bird 例子：一个子代理做了超级马里奥风格背景，另一个做了非游戏素材的鸟，最终 agent 无法拼合。
- 主张：多数场景用**单线程线性 agent**；上下文要溢出时，加一个**专门训练的压缩模型**把历史蒸馏成关键决策与事件。

**怎么讲这个分歧（建议措辞）**：两边的任务形态不同。Anthropic 的评测是**并行只读研究**（子任务之间几乎无隐式耦合），Cognition 说的是**协作写代码**（子任务之间充满隐式设计决策）。所以结论是"隔离的收益 ∝ 子任务之间的解耦程度"，而不是"多代理好/坏"。

---

## 5. Agent Skills / SKILL.md：官方规范与三级加载

### 5.1 官方 URL（一手）

| 内容 | URL |
|---|---|
| Agent Skills 概念与三级加载表 | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview |
| Skill 撰写最佳实践 | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices |
| 开放标准正式规范 | https://agentskills.io/specification |
| 开放标准首页（含采用方名单） | https://agentskills.io/ |
| Anthropic 工程博客（设计原理） | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills （**2025-10-16**，作者 Barry Zhang, Keith Lazuka, Mahesh Murag） |
| Claude Code 侧实现 | https://code.claude.com/docs/en/skills |
| 官方 Skills 仓库 | https://github.com/anthropics/skills |
| 规范开发仓库 | https://github.com/agentskills/agentskills |

### 5.2 目录结构（规范原文）

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/           # Optional: templates, resources
└── ...               # Any additional files or directories
```

### 5.3 Frontmatter 字段（合并 Anthropic 文档 + agentskills.io 规范）

| 字段 | 必填 | 约束 |
|---|---|---|
| `name` | ✅ | 1–64 字符；仅小写字母/数字/连字符；不能以 `-` 开头或结尾；不能有连续 `--`；**必须与父目录名一致**；不能含 XML 标签；不能含保留词 `anthropic` / `claude` |
| `description` | ✅ | 1–1024 字符，非空；不能含 XML 标签；**必须同时说明"做什么"和"何时用"**；建议第三人称（"Processes Excel files…"，不要写 "I can help you…"）——因为它会被注入 system prompt |
| `license` | ❌ | 许可证名或指向捆绑的 LICENSE 文件 |
| `compatibility` | ❌ | ≤500 字符；环境要求（目标产品、系统依赖、是否需要网络） |
| `metadata` | ❌ | 任意 string→string 映射，供各家客户端存放规范外属性 |
| `allowed-tools` | ❌ | 空格分隔的预授权工具串，如 `Bash(git:*) Bash(jq:*) Read`。**实验性**，各实现支持度不一 |

Claude Code 额外扩展（非通用规范，见 https://code.claude.com/docs/en/skills）：`disable-model-invocation`、`user-invocable`、`context: fork`、`agent`、`background`。

### 5.4 Progressive disclosure 三级加载的**确切机制**（官方表格，逐字）

| Level | When loaded | Token cost | Content |
|---|---|---|---|
| **Level 1: Metadata** | Always (at startup) | **~100 tokens per Skill** | `name` and `description` from YAML frontmatter |
| **Level 2: Instructions** | When Skill is triggered | **Under 5k tokens** | SKILL.md body with instructions and guidance |
| **Level 3+: Resources** | As needed | **None until accessed** | Bundled files. Reference files load into context when read. Scripts run through bash, and only their output enters context |

— 表格出自 https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

**加载流程（官方给的 pdf-processing 例子，逐步）**
1. 启动：system prompt 里出现 `pdf-processing - Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.`
2. 用户请求："Extract the text from this PDF and summarize it"
3. Claude 执行 `bash: cat pdf-processing/SKILL.md` → 指令进入上下文
4. Claude 判断不需要填表 → **不读** `FORMS.md`
5. 按 SKILL.md 的指令完成任务

**三条架构性推论（官方逐字）**
- *"On-demand file access: … A Skill can include dozens of reference files, but if your task only needs the sales schema, that's the one file Claude loads. The rest stay on the filesystem and cost zero tokens."*
- *"Efficient script execution: When Claude runs `validate_form.py`, the script's code never loads into the context window. Only its output … consumes tokens."*
- *"No practical limit on bundled content: Files don't consume context until accessed."*

**Anthropic 工程博客的三级表述（2025-10-16，逐字）**
1. *"The metadata is the first level of progressive disclosure: it provides just enough information for Claude to know when each skill should be used without loading all of it into context."*
2. *"The actual body of this file is the second level of detail. If Claude thinks the skill is relevant to the current task, it will load the skill by reading its full SKILL.md into context."*
3. *"These additional linked files are the third level (and beyond) of detail, which Claude can choose to navigate and discover only as needed."*

另有 Anthropic 反复用的类比：*"Building a skill for an agent is like putting together an onboarding guide for a new hire."*

### 5.5 撰写约束（官方数值）

- SKILL.md 正文 **保持在 500 行以内**（"Keep SKILL.md body under 500 lines for optimal performance"）。
- 引用文件**只保持一层深度**（嵌套引用会导致 Claude 用 `head -100` 之类部分读取，拿到不完整信息）。
- 超过 100 行的 reference 文件**在顶部加目录**。
- 精简度测试（官方给的对照）：好例子 **约 50 tokens**，差例子 **约 150 tokens**（同样一段 "Extract PDF text"）。
- 官方核心原则：*"The context window is a public good."* / *"Default assumption: Claude is already very smart."*
- 自由度分级：high freedom（纯文字启发式）/ medium（带参数的伪代码或脚本）/ low（必须原样执行的脚本）。类比：*"Narrow bridge with cliffs on both sides"* vs *"Open field with no hazards"*。

### 5.6 Skill 与 RAG / prompt / 工具 的本质区别

| 维度 | RAG | System prompt / CLAUDE.md | MCP 工具 | **Agent Skill** |
|---|---|---|---|---|
| 何时决定加载 | **推理前**（由检索器按 embedding 相似度决定） | **永远在**（每轮都付费） | 工具定义**常驻**上下文 | **运行时由模型自己决定**（按 description 匹配） |
| 检索单位 | 文本块（chunk），可能断章 | 整段 | 工具 schema | **整个文件/目录**，模型可 `grep`、可分支导航 |
| 能否携带确定性执行 | ❌ | ❌ | ✅（远程调用） | ✅ **本地脚本，代码本身不进上下文，只有 stdout 进** |
| 版本化 / 可移植 | 取决于向量库 | 与产品耦合 | 需要跑一个 server | **一个 git 目录，跨产品通用（开放标准）** |
| 组合 | — | 单一巨块，互相干扰 | 工具数量膨胀会退化选择质量 | **多 skill 并存，只有各自的 ~100 tokens 常驻** |

**官方原话（可直接上 PPT）**
- 对比 prompt：*"Unlike prompts (conversation-level instructions for one-off tasks), Skills load on demand, so you don't have to repeat the same guidance across conversations."*（Anthropic Skills 概览）
- 对比 CLAUDE.md：*"Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it."*（Claude Code 文档）
- 对比 RAG 的方法论表述（Anthropic 称之为 just-in-time）：*"agents maintain lightweight identifiers (file paths, queries, links) and dynamically load data via tools at runtime"*；代价是 *"runtime exploration is slower than pre-computed retrieval"*，收益是"支持渐进披露、避免把无关内容一次性污染上下文"。

### 5.7 开放标准与生态（2025-12 起）

- agentskills.io 首页原话：*"The Agent Skills format was originally developed by Anthropic, released as an open standard, and has been adopted by a growing number of agent products. The standard is open to contributions from the broader ecosystem."*
- 该站列出的客户端（部分）：Claude / Claude Code、**OpenAI Codex**、Cursor、GitHub Copilot、VS Code、**Gemini CLI**、OpenHands、Goose (Block)、Amp、JetBrains Junie、Letta、Factory、Kiro、Mistral Vibe、Roo Code、Tabnine、Databricks Genie Code、Snowflake Cortex Code、Spring AI、Laravel Boost、Pulumi Neo、**pi**……
- ⚠️ **待核实**：「开放标准发布日 = 2025-12-18」「Linux Foundation 的 Agentic AI Foundation (AAIF) 于 2025-12-09 成立，Anthropic/OpenAI/Block 为创始成员，2026-02 已有 146 家成员」——这些均来自第三方报道（unite.ai / VentureBeat / paperclipped.de），**未在 anthropic.com 或 agentskills.io 上找到带日期的一手公告**。上台前需核实。
- 🎯 **与本 deck 直接相关**：agentskills.io 对 `pi` 的官方描述是 —— *"Pi is a minimal terminal coding harness. Adapt pi to your workflows, not the other way around."* 链接：https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md 。**"harness" 这个词就写在 pi 的一句话简介里**，可以作为开场钩子。

---

## 6. 为什么 skill 比塞进 system prompt 强：用数据说话

### 6.1 Token 经济学（全部基于官方数值）

**基础事实**（Anthropic 官方三级表）：
- Level 1 metadata：**~100 tokens / skill**，常驻
- Level 2 正文：**< 5,000 tokens**，触发时才加载
- → **单个 skill 的"常驻成本 : 满载成本" ≈ 1 : 50**

**推算（标注为推算，非官方数字）**：官方文档明确提到 *"Claude uses it to choose the right Skill from potentially **100+ available Skills**"*。

| 方案 | 常驻上下文成本 | 说明 |
|---|---|---|
| 100 个 skill，progressive disclosure | **≈ 10,000 tokens**（100 × 100） | 本次会话只有实际触发的 1–2 个正文被加载 |
| 100 份同等内容全塞 system prompt | **≈ 500,000 tokens**（100 × 5,000） | **超过 200K 上下文窗口 2.5 倍——根本装不下** |

> ⚠️ 这两行是**我基于官方 per-skill 数值做的算术推算**，不是 Anthropic 公布的实测数据。上 PPT 时请标注"按官方 per-skill 数值推算"。

**同一原理在工具定义上的官方实测**（不是推算）：把 MCP 工具定义从"全量塞上下文"改成"代码化 + 按需读取"，**150,000 tokens → 2,000 tokens，-98.7%**（Anthropic, 2025-11-04）。

### 6.2 注意力预算：省 token 只是副产品，真正的收益是提升信噪比

- Anthropic：n 个 token 有 **n² 对关系**，上下文越长，注意力越被摊薄 → "performance gradient rather than a hard cliff"。
- Chroma：**即使只加 1 个干扰项**，NIAH 的表现也会低于 baseline。
- Liu et al.：**最坏情况下，给 20/30 篇文档不如一篇都不给**（GPT-3.5-Turbo closed-book 56.1%）。
- Anthropic 关于工具的判据：*"If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better."*

→ **结论**：把 100 份 SOP 塞进 system prompt，即使窗口装得下，也会因为 99 份不相关内容抬高噪声底而变差。progressive disclosure 同时优化了**成本**和**准确率**，这两件事在这里是同向的。

### 6.3 组合性（compositionality）

- Anthropic：*"Skills extend Claude's capabilities by packaging your expertise into composable resources for Claude, transforming general-purpose agents into specialized agents that fit your needs."*
- Claude Code 的四级作用域与优先级（官方）：
  - Personal `~/.claude/skills/<name>/SKILL.md` → 所有项目
  - Project `.claude/skills/<name>/SKILL.md` → 本项目
  - Plugin `<plugin>/skills/<name>/SKILL.md` → 插件启用处
  - 覆盖顺序：**enterprise > personal > project**；skill 覆盖同名 bundled skill；plugin skill 用 `plugin-name:skill-name` 命名空间，不会冲突
  - **嵌套发现**：monorepo 子目录下的 `.claude/skills/` 在 Claude 首次读写该子目录文件时才变可用；同名时两者共存，用 `/apps/web:deploy` 这种路径前缀区分
- 这是 system prompt 做不到的：system prompt 是一个不可组合的巨块，两份互相矛盾的规范塞进去就是 **context clash**（Breunig 的四种失效模式之一）。

### 6.4 三个必须承认的反面（讲稿里不要只夸）

1. **Skill 不是免费的，只是延迟计费**。Claude Code 官方原话：*"Once a skill loads, its content stays in context across turns, so every line is a recurring token cost."* —— 加载之后它会在整个 session 里反复被计费。
2. **压缩会吃掉 skill**。Auto-compaction 后，每个 skill 只重挂**前 5,000 tokens**，且所有重挂 skill **共享 25,000 tokens 总预算**——调过很多 skill 时，旧的会被整个丢弃。
3. **description 的质量决定一切**。三级加载的第一级只有 ~100 tokens；如果 description 写成 "Helps with documents"，模型永远不会触发它。官方把 description 定位为 *"critical for skill selection"*。

---

## 7. Progressive Disclosure 的知识溯源（HCI）

### 7.1 时间线

| 时间 | 事件 | 出处 |
|---|---|---|
| **1984-08** | John M. Carroll & Caroline Carrithers, **"Training Wheels in a User Interface"**, *Communications of the ACM* **27(8): 800–806**。IBM 实验：把商用文字处理软件里典型的、易出错的状态设为"不可达"，结果**学得更快、成绩更好、理解测验分数更高**。这是"先藏起高级功能"这一做法**最早的实证支撑之一**。 | DOI 10.1145/358198.358218 https://dl.acm.org/doi/10.1145/358198.358218 |
| 1984 | 同作者另一篇：Carroll & Carrithers, "Blocking Learner Error States in a Training-Wheels System", *Human Factors* 26(4) | https://journals.sagepub.com/doi/10.1177/001872088402600402 |
| 1997 | ⚠️ Carroll & Rosson 后来承认 *"no empirical evidence exists regarding the effectiveness of progressive disclosure"*（其研究只覆盖单一应用=文字处理器、单一界面风格=菜单式）。**此句转引自 IxDF 术语表，未核对原文**。 | https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/progressive-disclosure |
| 2004 | Frank Spillers 的表述：*"sequences information and actions across several screens in order to reduce feelings of overwhelm for the user"* | 同上（IxDF 转引） |
| **2006-12-03** | **Jakob Nielsen, "Progressive Disclosure", NN/g Alertbox**。定义：*"Initially, show users only a few of the most important options. Offer a larger set of specialized options upon request."* 又：*"defers advanced or rarely used features to a secondary screen, making applications easier to learn and less error-prone."* | https://www.nngroup.com/articles/progressive-disclosure/ |
| **2025-10-16** | Anthropic 把它作为 Agent Skills 的**核心设计原则**：*"Progressive disclosure is the core design principle that makes Agent Skills flexible and scalable."* | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills |

### 7.2 关于「Nielsen 是否造词」

- **不是**。Nielsen 2006 那篇**没有声称原创，也没有给出引用/参考文献**（我逐条查过该页，未见 attribution 段落）。
- Nielsen 自己在 2000、2002 就说过 progressive disclosure 是最好的交互设计技术之一，2006 那篇是**首次给出系统化的可用性指南**。
- ⚠️ **待核实**：这个词的**首次书面出现**。业界常见的两种说法——(a) 源自 IBM 1980 年代内部设计指南，(b) 源自教学设计（instructional design）领域——**我没有找到可核查的一手证据**。**演讲中建议只讲"可追溯到 Carroll & Carrithers 1984 的 training wheels 研究"，不要断言谁造的词。**

### 7.3 最值得讲的一个反差（原创观点，可直接当包袱）

Nielsen 的硬约束：
> *"designs that go beyond 2 disclosure levels typically have low usability because users often get lost when moving between the levels."*

Agent Skills 明确用了 **3 级甚至 3+ 级**。为什么可以？

- Nielsen 的读者是**人**，跨层级会迷路，因为人的工作记忆很小、导航成本高。
- Agent Skills 的读者是**会 `ls`/`grep`/`cat` 的模型**——它的"导航成本"是一次 bash 调用，而它的"迷路"表现为读了不该读的文件（浪费 token），不是放弃任务。
- 但**约束并没有消失，只是换了形式**：Anthropic 官方明确要求"引用文件保持一层深度"，因为 *"Claude may partially read files when they're referenced from other referenced files"*（嵌套引用会触发 `head -100` 式部分读取，拿到不完整信息）。
- → **同一条 HCI 原则，在换了"用户"之后，约束从"层级数 ≤ 2"变成了"引用图深度 ≤ 1"。** 这是 40 年老原则在新载体上的重新参数化，不是被推翻。

---

## 8. 建议上 PPT 的硬事实（Top 12，都可核查）

1. **~100 tokens vs <5,000 tokens** —— Skill 的 metadata 常驻成本 vs 正文加载成本，差 **50 倍**。（Anthropic 官方三级表）
2. **150,000 → 2,000 tokens，-98.7%** —— 把 MCP 工具定义从"全塞上下文"改成"代码化按需读"。（Anthropic, 2025-11-04）
3. **GPT-3.5-Turbo closed-book = 56.1%** —— 相关文档放中间时，给 20/30 篇文档**不如一篇都不给**。（Liu et al. 2023, Table 1 + §2.3）
4. **上下文里 96.3% 是工具输出** —— Anthropic cookbook 实测 research agent 末态构成：文件读取 ~322,946 tokens（96.3%）/ 工具调用记录 1.9% / agent 推理 1.7%。
5. **context editing + memory = +39%；token -84%** —— 100 轮网页搜索评测。（Anthropic, 2025-09-29）
6. **cached $0.30/MTok vs uncached $3.00/MTok（10×）**，Manus 的 input:output ≈ **100:1** —— 所以"稳定前缀"是省钱的第一原理。（Manus, 2025-07-18）
7. **+90.2%（Anthropic 多代理）vs "Don't Build Multi-Agents"（Cognition，早一天发）** —— 同一个月、相反结论，差别在子任务是否解耦。
8. **单 agent 20 分钟 $9 做崩 vs 完整 harness 6 小时 $200 做出来** —— harness 的价值有价格标签。（Anthropic, 2026-03-24）
9. **"Context engineering" 被命名于 2025-06-19 / 06-25（UTC）** —— Tobi Lütke 先说，Karpathy 六天后 "+1"，然后 Anthropic 在 2025-09-29 给了机制化定义。
10. **n² 与"性能斜坡不是悬崖"** —— 上下文腐化的两条机制：transformer 的 n² 注意力被摊薄 + 训练时长序列样本稀缺。（Anthropic, 2025-09-29）
11. **Progressive disclosure 不是 2025 年的新词，可追到 1984 年 CACM 的 "Training Wheels"**；Nielsen 2006 说"超过 2 级用户会迷路"，Agent Skills 用了 3 级——因为读者从人变成了会 grep 的模型。
12. **2023–2024 大家说 scaffold，2025 下半年起才说 harness** —— Anthropic 自己 2025-01-06 的 SWE-bench 博客里"harness"一次都没出现，全篇 scaffold。

---

## 9. ⚠️ 待核实清单（上台前请逐条确认或删除）

| # | 待核实内容 | 现状 |
|---|---|---|
| 1 | 「OpenAI evals 最早把 harness 用于 agent」 | **未找到证据**。o1 System Card (arXiv:2412.16720) 中未见该词。建议不要在演讲中这样说。 |
| 2 | 「agent harness」一词的**首次**公开使用 | 归属存在争议（英文维基百科 "Agent harness" 词条明说 "attribution is contested"）。建议只讲证据链，不讲"谁最早"。 |
| 3 | Lost in the Middle 的 TACL 卷期 | arXiv 页面 journal-ref 显示 "TACL, 2023"；通行引用为 **TACL Vol. 12 (2024), pp. 157–173**。请以 TACL 官网为准。 |
| 4 | Agent Skills 开放标准的正式发布日（传 2025-12-18） | 仅见于第三方报道；agentskills.io 与 anthropic.com 上未找到带日期的一手公告。 |
| 5 | Linux Foundation / Agentic AI Foundation (AAIF) 成立日 2025-12-09、创始成员、146 家成员 | 全部来自第三方报道，未验证。 |
| 6 | Claude Code 三层压缩（microcompact / full compact / session memory compact）与阈值公式（`effectiveWindow - 13,000`、200K→~167K、缓冲 45,000→~33,000） | **全部来自第三方逆向博客**，官方文档未见。官方**已确认**的只有：auto-compaction 后 skill 重挂"每个前 5,000 tokens、总预算 25,000 tokens"。 |
| 7 | 「Anthropic 2026 Agentic Coding Trends Report 说 context engineering 是 2026 年的 load-bearing skill」，以及"有良好 context 文件的团队错误少 40%、任务快 55%" | 官方页面 https://resources.anthropic.com/2026-agentic-coding-trends-report **是需要填表下载的门禁页**，公开页面上无这些数字。引用来自第三方博客。**建议不用。** |
| 8 | Karpathy / Tobi Lütke 推文的**完整原文** | x.com 直接抓取返回 HTTP 402。时间戳由 snowflake ID 本地推算（可复算），文本仅有部分引用（来自 Simon Willison 2025-06-27 与搜索摘要）。 |
| 9 | Carroll & Rosson 1997 那句"no empirical evidence" | 转引自 IxDF 术语表，未核对原始论文。 |
| 10 | 「100 个 skill = 10k tokens vs 500k tokens」 | 是**我的算术推算**（基于官方 per-skill 数值），不是 Anthropic 公布的实测数。PPT 上请标注"推算"。 |
| 11 | lm-evaluation-harness 的最早 Zenodo DOI（曾传 10.5281/zenodo.5371628, 2021-09） | 该 DOI 现解析为 v0.4.12 (2026-05-11) 的记录，**未验证 2021 年那条**。已改用可验证的 GitHub `created_at: 2020-08-28`。 |

---

## 10. 全部一手 URL 索引

**Anthropic 官方**
- Effective context engineering for AI agents (2025-09-29) — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Managing context on the Claude Developer Platform (2025-09-29) — https://claude.com/blog/context-management
- Building agents with the Claude Agent SDK (2025-09-29) — https://claude.com/blog/building-agents-with-the-claude-agent-sdk
- Equipping agents for the real world with Agent Skills (2025-10-16) — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Code execution with MCP (2025-11-04) — https://www.anthropic.com/engineering/code-execution-with-mcp
- Effective harnesses for long-running agents (2025-11-26) — https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Harness design for long-running application development (2026-03-24) — https://www.anthropic.com/engineering/harness-design-long-running-apps
- How we built our multi-agent research system (2025-06-13) — https://www.anthropic.com/engineering/multi-agent-research-system
- Building effective agents (2024-12-19) — https://www.anthropic.com/engineering/building-effective-agents
- Claude SWE-Bench Performance (2025-01-06) — https://www.anthropic.com/engineering/swe-bench-sonnet

**Anthropic 官方文档 / Cookbook**
- Agent Skills overview（三级加载表） — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Skill authoring best practices — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Compaction API — https://platform.claude.com/docs/en/build-with-claude/compaction
- Context editing — https://platform.claude.com/docs/en/build-with-claude/context-editing
- Memory tool — https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- Cookbook: memory, compaction, and tool clearing — https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
- Claude Code · Extend Claude with skills — https://code.claude.com/docs/en/skills

**开放标准**
- https://agentskills.io/ ｜ https://agentskills.io/specification ｜ https://github.com/agentskills/agentskills ｜ https://github.com/anthropics/skills

**论文 / 技术报告**
- Lost in the Middle (arXiv v1 2023-07-06) — https://arxiv.org/abs/2307.03172
- Context Rot (Chroma, 2025-07-14) — https://www.trychroma.com/research/context-rot ｜ https://github.com/chroma-core/context-rot
- SWE-bench (2023-10-10) — https://arxiv.org/abs/2310.06770
- Evaluating Language-Model Agents on Realistic Autonomous Tasks (METR/ARC Evals, 2023-12) — https://arxiv.org/abs/2312.11671
- Training Wheels in a User Interface (CACM 27(8), 1984-08) — https://dl.acm.org/doi/10.1145/358198.358218

**社区 / 分类法**
- Manus: Context Engineering for AI Agents (2025-07-18) — https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Cognition: Don't Build Multi-Agents (2025-06-12) — https://cognition.com/blog/dont-build-multi-agents
- LangChain: Context Engineering for Agents (2025-07-02) — https://www.langchain.com/blog/context-engineering-for-agents
- Drew Breunig: How Long Contexts Fail (2025-06-22) — https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html
- Simon Willison: Context engineering (2025-06-27) — https://simonwillison.net/2025/Jun/27/context-engineering/
- Mitchell Hashimoto: My AI adoption journey (2026-02-05) — https://mitchellh.com/writing/my-ai-adoption-journey
- Birgitta Böckeler: Harness engineering for coding agent users (2026-04-02) — https://martinfowler.com/articles/harness-engineering.html
- Hugging Face: Harness, Scaffold, and the AI Agent Terms Worth Getting Right (2026-05-25) — https://huggingface.co/blog/agent-glossary
- Jakob Nielsen: Progressive Disclosure (2006-12-03) — https://www.nngroup.com/articles/progressive-disclosure/
- IxDF Glossary: Progressive Disclosure — https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/progressive-disclosure
- EleutherAI lm-evaluation-harness — https://github.com/EleutherAI/lm-evaluation-harness
