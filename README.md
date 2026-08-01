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

### 📐 [如何打造自己的 Agent —— 从 harness 到 re-agent](./build-your-own-agent/)

`2026` · 27 页 · 中文

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
