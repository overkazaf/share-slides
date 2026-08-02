# share-slides

技术分享合集 —— slides、逐页讲稿，以及**每条断言背后的研究笔记**。

**▶ 在线阅读：<https://overkazaf.github.io/share-slides/>**

---

## 为什么把研究笔记也放上来

大部分技术分享看完就完了，因为你没法验证它。

这个仓库的做法是：**把作业本一起交上来**。每份分享都附带研究笔记，里面标了每条数据的核实等级 ——

| 等级 | 含义 |
|---|---|
| **[A]** | 厂商官方页 / arXiv / npm·PyPI·GitHub API 机器时间戳，已亲自抓取核对 |
| **[B]** | 权威二手，已抓取 |
| **[C]** | 只见于聚合站 —— **一律不上页**，只写进备忘 |

slides 上只放 [A] 级事实。被打回的、拿不准的，连同"为什么没上页"一起写在各分享的 `NOTES.md` 里。

发现哪里错了，**请直接提 Issue**。这类东西越多人挑越好。

---

## 目录

### 🛠 [如何打造自己的 Agent · Chapter 4 —— re-agent：把一个行业的规矩写进骨架](./build-your-own-agent-4/)

`2026` · 30 页 · 中文

前三讲拆的都是别人的 harness。这一讲拆一个**从零写的**：面向逆向工程的 `overkazaf/re-agent`（0xAF-Re）。

> **⚠ 利益冲突声明**：本讲主讲人就是 re-agent 的作者。所以对比章的顺序是刻意的 ——
> **先花一整页拆自己的台（6 条其实只是配置 · 10 条明确落后），再说剩下什么（4 条结构性差异）**。

| 章 | 内容 |
|---|---|
| CH1 起手 | 第一讲那份「逆向七道坎」逐条交账：四条已落地 · 两条半 · 一条有洞 |
| CH2 灵感来源 | pi 给结构 / oh-my-pi 给代价意识 / Claude Code 给 skill 格式；四个不一样的选择，每个给账单 |
| CH3 实现原理 | 一个函数就是全部控制流 · 包依赖倒置 · planner/executor 双座位 · caveman 隔离委派 · 上下文三道闸 |
| CH4 功能点 | 52 个命令里约 49 个零 token；24 工具 / 33 skill；知识库把幻觉引用记账 |
| CH5 三方对比 | 实测矩阵 → **自我拆台** → 剩下四条 |
| CH6 能干什么 | 端到端案例（正例反例各跑一次）+ 四个能对回 SKILL.md 行号的场景 |
| CH7 代价与规划 | 安全闸的七个洞；明写的规划只有一句；四讲一起收口 |

**取证基线**：`overkazaf/re-agent`，commit `926e615`（2026-07-31）。
**取证方式**：**全程只读代码 —— 不执行二进制、不联网、不跑 demo**，所以本讲没有任何性能或成功率数字。

**几条可核查的硬事实**：

- **外部依赖只有 1 个**（`golang.org/x/term`，`go.sum` 4 行）。对照 pi 的 27 个、oh-my-pi 的 664 npm 包 + 912 crate ——
  **它不是「更小的 pi」，是依赖面积几乎为零的静态单二进制**
- **最大的包不是内核，是界面**：`internal/ui` 5,608 行，是 `internal/core`（2,086 行）的 **2.7 倍**；入口 `main.go` 只有 17 行
- **渐进式披露 1 : 47**：skill 目录常驻 8,531 字节，全文 397,723 字节。但**全仓 grep「progressive disclosure」零命中** —— 复刻了机制，没用这个词
- **caveman 是宿主级双阶段委派**：planner 只给 1 个工具，executor 换 system prompt + 隔离会话 + 工具从 24 剪到 **14 个只读**，证据包硬截 6000 字符；
  执行方的 prompt 里写着 *"You do not need the broader objective."*，且红线（不许翻译、不许暗语、不许 prompt laundering）**有单测钉死**
- **零重试**：`grep -rn "retry\|backoff\|MaxRetries"` → **0 命中**；对照 pi 三层、oh-my-pi 默认 `maxRetries=10` + 1,787 行专职恢复类
- **测试比 0.17×**（pi 0.885×、omp 0.74×），零 CI、零 lint 配置，`mcp` / `types` / `util` 三个包**零测试** —— 而路径包含检查正好住在 `util` 里
- **一块化石**：`demos/README.md` 至今写着 `bun src/cli.ts`，而 git 全历史**没有任何 `.ts` 文件**

- 📖 [在线阅读](./build-your-own-agent-4/) ·
  🔍 [研究笔记（6 份）](./build-your-own-agent-4/research/) ·
  ⚠️ [上台前备忘](./build-your-own-agent-4/NOTES.md) ·
  🗺 [分镜](./build-your-own-agent-4/OUTLINE.md)

---

### 🔬 [如何打造自己的 Agent · Chapter 2 —— 解剖 pi：把一个 harness 拆到底](./build-your-own-agent-2/)

`2026` · 28 页 · 中文

承接第 (1) 讲。这一讲只干一件事：**把 pi 的源码逐层拆开**。

| 章 | 内容 |
|---|---|
| CH1 起手 | 9 个包 / 11.2 万行的体量表；一个结构事实：它有**两套**编排层 |
| CH2 循环 | 双层 while 与四个判停点；中断与出错不靠抛异常；差异清单 |
| CH3 会话 | 一个 `parentId` 撑起整棵树；同步写 JSONL 与恢复路径 |
| CH4 上下文 | system prompt 组装；压缩的切点算法；SKILL 渐进式披露 |
| CH5 工具 | 定义 7 个默认给 4 个；`edit` 匹配算法；「没有权限弹窗」复核 |
| CH6 外壳 | 33 个扩展钩子；两万行模型接入层；一万四千行自绘 TUI |
| CH7 抄走 | 12 条可抄清单，每条带 `路径:行号` 与落地成本 |

**取证基线**：`earendil-works/pi`，commit `583f153`（2026-08-01），版本 **0.83.0**，全部本地实测。

**几条可核查的硬事实**：

- **教科书循环 6 行，真实产品 121 + 517 行**：多出来的九成代码在处理「跑到一半，世界变了」——
  用户插话、token 过期、模型被换、输出被截断、按了 Ctrl-C
- **主循环里 0 行重试代码、0 个 timer、没有迭代上限**：重试放在循环之外，3 次 2/4/8 秒退避，
  且**重试前把错误消息从喂给模型的上下文里摘掉，但仍留在 session 文件里**
- **内核自带上下文只有 ≈1,311 token**，而 pi 自己仓库的 `AGENTS.md` 是 ≈2,683 token —— **项目文件是内核的两倍**
- **`edit` 的「模糊匹配」就是两次 `indexOf`**：中间只做五类确定性归一化；多处命中一律报错，**绝不选第一个**
- **「不做权限弹窗」实测成立且比宣传更彻底**：全仓 grep `permission` 三处命中，全是注释和许可证；**连路径沙箱都没有**
- **本讲复核并修正了第 (1) 讲的 3 处说法**（含一处把 oh-my-pi 的规矩记到了 pi 头上），全部写在备忘里

- 📖 [在线阅读](./build-your-own-agent-2/) ·
  🔍 [研究笔记（10 份）](./build-your-own-agent-2/research/) ·
  ⚠️ [上台前备忘](./build-your-own-agent-2/NOTES.md) ·
  🗺 [分镜](./build-your-own-agent-2/OUTLINE.md)

---

### 📐 [如何打造自己的 Agent · Chapter 1 · Getting Started —— 从 harness 到 re-agent](./build-your-own-agent/)

`2026` · 26 页 · 中文

从「什么是 agent」讲到「怎么造一个」。

| 章 | 内容 |
|---|---|
| CH1 定义 | Agent 的最小闭环；决策权谱系 |
| CH2 演进 | 2022–2026 时间线（带日期与出处）；关键人物谱 |
| CH3 原理 | 七层技术栈 · harness · loop / graph engineering · context engineering · SKILL · 工具 · 五种 workflow 模式 · 多智能体之争 · 六种扩展点 · 记忆与纠偏 |
| CH4 场景 | 适用场景矩阵与四条硬红线 |
| CH5 全景 | 主流 coding agent 的四象限 |
| CH6 样本 | pi 的「刻意不做」清单；oh-my-pi 与 FORK 成本模型 |
| CH7 实践 | 模型对照与选型依据；逆向的七道坎；re-agent |

**几条可核查的硬事实**：

- **换 harness 到底值多少分**：Terminal-Bench 官方榜 22 个模型，中位数挪动 **5.39 分**，最大 **20.90 分**；
  而同一个 harness 换模型极差 **70.7pp**。→ 模型是主项，harness 是约 1/4 量级的次项，**但主项买不到差异化**
- **最扎心的一条**：Gemini 3 Pro 套通用 harness 拿 73.93%，套 Google 自家 Gemini CLI 只有 65.84%
- **窗口大 ≠ 用得好**：Gemini 3.6 Flash 的长上下文召回，128k 下 91.8%，拉到 1M 掉到 **54.0%**（官方自己的数）
- **progressive disclosure 的代码级证据**：pi 的 `Skill` 结构体里**根本没有 content 字段**
- **开放权重的真实位置**：单点基准贴到前沿 0.5–7 分、价格差 4.6–57 倍，
  但**长程仓库级任务仍差 12–21 分**，且第一梯队权重 200GB–1.5TB

- 📖 [在线阅读](./build-your-own-agent/) ·
  📄 [PDF](./build-your-own-agent/如何打造自己的Agent.pdf) ·
  🔍 [研究笔记](./build-your-own-agent/research/) ·
  ⚠️ [上台前备忘](./build-your-own-agent/NOTES.md)

---

## 本地跑 / 二次创作

每份分享都是**一堆分片 HTML + 一个构建脚本**，没有前端工程链，clone 下来就能改：

```bash
cd build-your-own-agent

python3 build.py        # slides/*.html → index.html（单文件自包含）
python3 qa.py           # 排版体检：元素越界 / 容器溢出 / SVG 文字出框
python3 fitcontent.py   # 量 SVG 内容包围盒，自动缩放填满画布
```

改完记得跑一遍 `qa.py`，输出 `CLEAN` 才算过。

**设计系统**：深色 `#020617` + 网格底纹，JetBrains Mono，语义色板（青=交互层 / 绿=内核 / 紫=上下文 / 琥珀=模型 / 玫红=边界与痛点 / 橙=总线）。
出自 [Cocoon AI](mailto:hello@cocoon-ai.com) 的 architecture-diagram 设计规范。

**导出 PDF**（深色保真）：

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=25000 \
  --print-to-pdf=out.pdf file://$PWD/index.html
```

> 深色背景要靠 CSS 里的 `print-color-adjust: exact`，否则 Chrome 会按「省墨」丢掉所有背景色。

---

## 交流

- **指错 / 补充** → [Issues](https://github.com/overkazaf/share-slides/issues)
- **实时交流** → [Discord](https://discord.gg/vrjd7wQ8) —— 逆向、agent、工具链
- **深入讨论** → [Discussions](https://github.com/overkazaf/share-slides/discussions)
- **跟进后续** → Watch 本仓库

---

## 许可

- 内容（slides、讲稿、研究笔记）：**CC BY 4.0**
- 代码（构建脚本、样式）：**MIT**

引用第三方资料时均已标注来源；如有归属错误请提 Issue，我会尽快更正。
