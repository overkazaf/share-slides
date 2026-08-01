# 解剖 pi：把一个 agent harness 拆到底

> 《如何打造自己的 Agent》**第 (2) 讲** · 2026 · 中文
> 上一讲：[从 harness 到 re-agent](../build-your-own-agent/) —— 讲「是什么、需要哪几样」。
> 这一讲只干一件事：**把 pi 的源码逐层拆开**，看真实产品的 harness 比伪代码多出了什么。

**▶ 在线阅读：[index.html](./index.html)**（← → 翻页，`O` 总览，`F` 全屏）

---

## 取证基线

全场每一个行号、每一个数字都钉在同一个 commit 上：

| 项 | 值 |
|---|---|
| 仓库 | `earendil-works/pi`（旧路径 `badlogic/pi-mono`） |
| commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95`（短 `583f153`） |
| commit 日期 | 2026-08-01 14:38:13 +0200 |
| workspace 版本 | **0.83.0** |
| 取证日期 | 2026-08-02 |

**口径规矩**：

- 页面上出现的行号一律相对仓库根，且带短 hash `583f153` —— 行号会随上游漂移，不带 hash 的行号是不可核查的。
- 行数 / 文件数 / 数量**一律本地实测**（命令写在研究笔记里）；引用官方口径时明确写「官方口径」。
- 与第 (1) 讲说法冲突的地方，**明说是复核结果**，并给出新证据。

---

## 章节

| 章 | 问题 | 内容 |
|---|---|---|
| CH1 起手 | 为什么值得逐行读它 | 体量表；一个结构事实：它有两套编排层 |
| CH2 循环 | while(true) 之外还有什么 | 双层循环与判停；abort 穿透三层；差异清单 |
| CH3 会话 | 为什么说会话是树 | entry 类型与树结构；落盘与恢复 |
| CH4 上下文 | prompt 怎么拼、满了怎么办 | system prompt 组装；compaction；SKILL 渐进式披露 |
| CH5 工具 | 为什么只给四个 | 工具清单；edit 匹配算法；权限「刻意不做」复核 |
| CH6 外壳 | 内核之外的三坨工程量 | 扩展面；模型接入层；自绘 TUI |
| CH7 抄走 | 哪些能搬走 | 12 条可抄清单，每条带证据与成本 |

---

## 研究笔记

每一份都是对着源码打开文件核对出来的，不是转述：

| 文件 | 选题 |
|---|---|
| [P01](./research/P01-repo-baseline.md) | 仓库总览与工程基线 |
| [P02](./research/P02-agent-loop.md) | 主循环逐行拆解 |
| [P03](./research/P03-two-orchestration-layers.md) | AgentSession vs AgentHarness |
| [P04](./research/P04-session-tree.md) | 会话树与持久化 |
| [P05](./research/P05-context-engineering.md) | prompt 组装 / compaction / SKILL |
| [P06](./research/P06-tools.md) | 工具层 |
| [P07](./research/P07-extensibility.md) | 扩展面 |
| [P08](./research/P08-tui.md) | TUI |
| [P09](./research/P09-ai-layer.md) | 模型接入层 |
| [P10](./research/P10-engineering-and-takeaways.md) | 工程规范与可抄清单 |

---

## 本地构建

```bash
python3 build.py       # slides/*.html + deck.css + deck.js → 单文件 index.html
python3 prompter.py    # 生成提词器页面（讲稿不进仓库）
```

---

发现哪里错了，**直接提 Issue**。行号、数字、结论，随便挑。
