# 《如何打造自己的 Agent》· 分镜脚本 v1

> 交付形态：单文件自包含 HTML 演示（cocoonAI / architecture-diagram 设计系统）
> 视觉：`#020617` 底 + 网格纹理，JetBrains Mono，语义色板
> 色板语义（沿用 skill 定义）：
> - 青 `#22d3ee`：入口 / 交互层 / 用户侧
> - 绿 `#34d399`：内核 / 循环 / 执行
> - 紫 `#a78bfa`：上下文 / 记忆 / 存储
> - 琥珀 `#fbbf24`：模型 / 外部服务 / 云
> - 玫红 `#fb7185`：痛点 / 边界 / 安全
> - 橙 `#fb923c`：总线 / 协议 / 消息
> - 灰 `#94a3b8`：泛化 / 环境

---

## 全局叙事线

```
是什么 → 怎么来的（人 + 时间线）→ 拆开看（技术点与原理）
      → 什么时候用（场景边界）→ 别人怎么做（全景）
      → 为什么是 pi（极客口味）→ oh-my-pi（极限形态）
      → 我的武器库 → 所以我要做 re-agent（下回分解）
```

一句话主张（贯穿全场）：
> **模型决定能力上限，harness 决定你能兑现多少。**
> 打造自己的 agent，不是训模型，是做那层 harness。

---

## 分镜（25 页）

| # | 标题 | 核心论点（一句话） | 视觉 | 资料来源 |
|---|------|-------------------|------|---------|
| 01 | 封面 | 如何打造自己的 Agent —— 从 harness 到 re-agent | 标题 + 脉冲点 + 副标 | — |
| 02 | 阅读地图 | 七章的问题链 | 章节导航图 | — |
| 03 | 什么是 Agent | LLM + 工具 + 循环 + 环境反馈，且**由模型决定下一步** | **图A** 最小闭环 | R04/R05 |
| 04 | Agent 不是什么 | 决策权谱系：Chatbot→Chain→Workflow→Agent→Multi-Agent | **图B** 谱系条 | R05（Anthropic 定义） |
| 05 | 演进 I（2022–2023） | 从「会推理」到「会动手」，然后撞墙 | **图C** 时间线上半 | R01 + FC |
| 06 | 演进 II（2024–2026） | 范式转移：从"让模型自己想办法"到"工程化 harness" | **图D** 时间线下半 | R02 + FC |
| 07 | 关键人物谱 | 每个节点背后是谁 | **图E** 人物卡阵列 | R03 + FC |
| 08 | 技术全景 | Agent 技术栈七层 | **图F** 分层大图（本场地图） | R04/R05/R10 |
| 09 | Harness | 模型之外的一切；pi 的 AgentHarness 是活教材 | **图G** harness 三层剖面 | R10 |
| 10 | Loop Engineering | 主循环状态机：判停、回灌、abort、错误恢复 | **图H** 状态机 | R05 + R10 |
| 11 | Graph Engineering | 会话是**树**不是线；DAG 编排 vs 自主循环 | **图I** session 树 + DAG | R05 + R10 |
| 12 | Context Engineering I | 上下文是预算，不是仓库：四类占用 + 注意力衰减 | **图J** 预算条 + context rot 曲线 | R04 |
| 13 | Context Engineering II | Compaction：pi 摘要压缩 vs omp 位图帧压缩 | **图K** 压缩前后 | R04 + R08 |
| 14 | SKILL | 渐进式披露：常驻几十 token，展开才是全文 | **图L** 三级加载 | R04 + R10 |
| 15 | Tools | 少而正交 / 错误可自愈 / 两级加载 + BM25 发现 | **图M** 工具面板 | R08 + R10 |
| 16 | Workflow vs Agent vs Subagent | 能写死就别让模型猜；上下文隔离才是子代理的真收益 | **图N** 三形态对比 | R05 |
| 17 | 可扩展性三件套 | MCP / Extension / Hook 各管一段 | **图O** 扩展点插槽 | R08 + R10 |
| 18 | 记忆与自进化 | memory / advisor-watchdog / TTSR：让 agent 记住并纠偏 | **图P** 记忆双层 | R08 |
| 19 | 适用场景矩阵 | 反馈可得性 × 任务确定性；写清**不适合**的一半 | **图Q** 2×2 矩阵 | R05 + R09 |
| 20 | 主流 Coding Agent 全景 | 开源/闭源 × 自扩展强弱 | **图R** 象限 + 对比表 | R06 |
| 21 | 为什么极客圈喜欢 pi | 自扩展 / 会话树 / 坦诚不做权限 / 可读 MIT / 晒真实 session | **图S** 爽点卡 | R07 |
| 22 | oh my pi 是什么 | pi 的极限 fork：Rust 热路径 + 位图压缩 + 记忆引擎 | **图T** pi vs omp 分层 | R08 |
| 23 | 笔者的武器库 | CC / Codex / NotebookLM / Grok…「任务类型 × 工具」对照 | **图U** 对照矩阵 | R09 Part A |
| 24 | 为什么做 re-agent | 通用 coding agent 干逆向为什么不好用（痛点五条） | **图V** 痛点→对策 | R09 Part B |
| 25 | re-agent 架构 + 预告 | 0xAF-Re：双模型分工 + 策略沙箱 + 逆向工具集；下回分解 | **图W** re-agent 架构 | 本地仓库取证 |

---

## 每页硬约束

- 每页**一个论点**，标题即结论，不写"关于 XX"。
- 正文文字 ≤ 6 行；细节进图或进"注脚"小字。
- 时间线/人物/数字**必须有出处**，页脚以极小字标注来源短链。
- 有争议的地方**两方都写**（如多 agent：Anthropic 支持 vs Cognition 反对）。
- 每章末尾一句"所以"，把论点接到下一章。

## re-agent 章节的事实底座（已本地取证）

- 仓库：`/Users/nongjiawu/playground/research/ohmypi/0xaf-re-agent`
- 定位：从 oh-my-pi 核心思想裁剪出的**逆向 / CTF 专用 agent**
- 架构：CLI/REPL → config + provider registry → AgentLoop → tool registry → JSONL session
- 路由模型：`planner=codex`（本地 codex exec, tmux）/ `executor=claude`（本地 claude -p, tmux）/ `auto` 由分类器决定；`grok` 作交叉复核
- 兜底 provider：codex-api / claude-api / grok / deepseek / glm / mock
- 工具集：list_files, read_file, write_file, grep, run_command, file_info, strings, hexdump, hash_file, extract_symbols
- 默认策略：读限工作区内 / 写需 `--write` / 网络需 `--allow-network` / 敏感路径需 `--allow-sensitive` / 阻断破坏性 shell
- 呼应第 24 页：re-agent 本身就是把 CC + Codex + Grok **编排**起来，而不是再造一个模型
