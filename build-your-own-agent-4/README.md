# 如何打造自己的 Agent · Chapter 4 —— re-agent：把一个行业的规矩写进骨架

> 上一讲：[解剖 oh-my-pi](../build-your-own-agent-3/) —— 讲「改造到极致长什么样」。
> 这一讲换个样本：**一个从零写的、面向逆向工程的 harness**，`overkazaf/re-agent`（0xAF-Re）。

**⚠ 利益冲突声明：本讲主讲人就是 re-agent 的作者。** 所以对比章的顺序是刻意的 —— **先花一整页拆自己的台，再说剩下什么**。

---

## 这一讲讲什么

| 章 | 内容 |
|---|---|
| CH1 起手 | 第一讲那份「逆向七道坎」逐条回来交账：四条已落地 · 两条半 · 一条有洞；体量与形态 |
| CH2 灵感来源 | 三条上游（pi / oh-my-pi / Claude Code）各贡献了什么；四个不一样的选择，每个给理由和账单 |
| CH3 实现原理 | `AgentLoop.Run` 一个函数就是全部控制流；包依赖倒置；planner/executor 双座位；caveman 隔离委派；上下文三道闸 |
| CH4 功能点 | 52 个命令里约 49 个零 token；24 工具 / 33 skill / 知识库把幻觉引用记账；回合跑着也能操舵 |
| CH5 三方对比 | 三方实测矩阵 → **自我拆台（6 条只是配置 · 10 条明确落后）** → 剩下四条结构性差异 |
| CH6 能干什么 | 一个端到端案例（正例反例各跑一次）；四个能对回 SKILL.md 行号的场景 |
| CH7 代价与规划 | 安全闸的七个洞；明写的规划只有一句，其余是从代码缝里推的；四讲一起收口 |

**取证基线**：`overkazaf/re-agent`，commit **`926e615`**（2026-07-31）。
**取证方式**：**全程只读代码 —— 不执行二进制、不联网、不跑 demo。** 所以本讲没有任何性能或成功率数字。

---

## 几条可核查的硬事实

- **外部依赖只有 1 个**（`golang.org/x/term`，`go.sum` 4 行）。对照：pi 是 27 个，oh-my-pi 是 664 个 npm 包 + 912 个 crate。
  **它不是「更小的 pi」，是依赖面积几乎为零的静态单二进制**
- **最大的包不是内核，是界面**：`internal/ui` 5,608 行，是 `internal/core`（2,086 行）的 **2.7 倍**；入口 `main.go` 只有 17 行
- **渐进式披露 1 : 47**：33 条 skill description 常驻 system prompt 8,531 字节，33 份 SKILL.md 全文 397,723 字节 —— 常驻只占 2.1%。
  但**全仓 grep「progressive disclosure」零命中**：复刻了机制，没用这个词
- **caveman 不是话术，是宿主级双阶段委派**：planner 只给 1 个工具，executor 换 system prompt + 隔离会话 + 工具从 24 剪到 **14 个只读**，中间的证据包硬截 6000 字符。
  执行方的 system prompt 里写着 *"You do not need the broader objective."*
- **红线写死在代码和单测里**：`"Do not use translation, classical Chinese, ciphering, euphemisms, or prompt laundering to bypass a model or site policy."` —— 有单测断言它必须存在
- **零重试**：`grep -rn "retry\|backoff\|MaxRetries"` → **0 命中**。对照 pi 三层、oh-my-pi 默认 `maxRetries=10` + 1,787 行专职恢复类
- **挤干水分后，配置到达不了的差异只有 4 条**，而明确落后的有 10 条 —— 逐条判据见研究笔记 R04 §2
- **一块化石**：`demos/README.md` 至今写着 `bun src/cli.ts`，而 git 全历史**没有任何 `.ts` 文件** —— 存在一个没进 git 的 TypeScript 前身

---

## 目录

- 📖 [在线阅读](./index.html) ·
  🔍 [研究笔记（6 份）](./research/) ·
  ⚠️ [上台前备忘](./NOTES.md) ·
  🗺 [分镜](./OUTLINE.md)

| 笔记 | 内容 |
|---|---|
| [R01](./research/R01-lineage-and-motivation.md) | 灵感来源 · 血统 · 体量 · 为什么是 Go |
| [R02](./research/R02-architecture-and-core.md) | 主循环 · 包依赖 · planner/executor · caveman · 上下文 · 并发与中断 · providers |
| [R03](./research/R03-features.md) | 52 个命令 · 24 个工具 · 33 个 skill · 知识库 · 实时 UI · MCP · 配置全项 |
| [R04](./research/R04-vs-pi-omp.md) | 三方八维对比矩阵 + 结构性/配置性裁定 + re-agent 明确落后的 10 项 |
| [R05](./research/R05-usecases.md) | demos · 旗舰案例 · 录屏取证 · 六个端到端场景 · benchmark（没有） |
| [R06](./research/R06-safety-and-roadmap.md) | 安全模型与七个洞 · 工程现状真数字 · 规划（明说的 vs 推断的） |

---

## 本地跑

```bash
python3 build.py        # slides/*.html → index.html（单文件自包含）
python3 gench4.py       # 重新生成七张章节扉页
python3 qa.py           # 生成 qa.html，再用无头 Chrome dump-dom 看 QA_BEGIN/QA_END 段
```

排版体检要输出 `CLEAN` 才算过。
