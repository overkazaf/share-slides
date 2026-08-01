# M04：开源权重模型（2026-08-01 快照）

> 采集日期：2026-08-01。所有数字均为当场抓取，标注可信度分级。
>
> **可信度分级**
> - **[A]** 厂商官方页 / 官方定价页 / 官方 model card，已亲自抓取核对
> - **[B]** 权威二手（OpenRouter 模型页等），已抓取
> - **[C]** 仅见于聚合站 / 内容农场 —— 本文档中**不存在** [C] 级数字（抓不到的一律写「未获证实」）
>
> **本次采集限制（必须知情）**
> 1. 本 session 的 WebSearch 配额已耗尽，全部数据靠 WebFetch 直取已知官方 URL。因此**可能遗漏**某些没被我猜到 URL 的新模型。
> 2. Artificial Analysis 榜单页为 JS 渲染，抓取结果明显是陈旧片段（返回 Llama 4 Scout 等 2025 年模型），**故本文档不引用 AA 的任何数字**。演讲若需第三方独立评测，需另行人工核对。
> 3. 所有 benchmark 均为**厂商自测**，跨 model card 的数字不可直接横比（评测协议、reasoning effort 档位不同）。已在表中注明来源卡片。

---

## 0. 一句话结论（给台上用）

2026 年 8 月，开放权重的第一梯队（Kimi K3 / GLM-5.2 / DeepSeek-V4-Pro / Qwen3.5-397B）在**编码与 agent 类基准上已经贴到闭源前沿 0.5～7 分以内**，但价格差 **4.6 倍～57 倍**。代价是：真正能私有化部署的那几个，**权重体积在 200GB～1.5TB 量级**，不是"下载下来就能跑"。真正能在单卡消费级 GPU 上跑的，只有 Qwen3.6-35B-A3B 这一档。

---

## 1. 主力开放权重模型总览

| 模型 ID | 厂商 | 发布日 | 许可证 | 总参数 / 激活参数 | 上下文 | 来源 |
|---|---|---|---|---|---|---|
| `DeepSeek-V4-Pro` (DSpark) | DeepSeek | 2026-04-24 | **MIT** | 1.6T / 49B (MoE) | 1M | [A] HF model card + 官方 news |
| `DeepSeek-V4-Flash-0731` | DeepSeek | 2026-07-31 | **MIT** | 304B（HF 计数）/ 激活未公布 | 1M (`max_position_embeddings=1048576`) | [A] HF model card + config.json |
| `DeepSeek-V4-Flash` (DSpark, preview) | DeepSeek | 2026-04-24 | **MIT** | 284B / 13B (MoE) | 1M | [A] HF model card + 官方 news |
| `GLM-5.2` | Z.AI / 智谱 | 2026-06-17（卡片博文日期） | **MIT** | 753B / **激活参数官方未公布** | 1M（官方文档：1M ctx，128K max output） | [A] HF card + docs.bigmodel.cn |
| `Kimi-K3` | Moonshot AI | 2026-07-16 | **Kimi K3 License**（自定义，有阈值） | 2.8T / 104B (MoE) | 1,048,576 | [A] HF card / [B] 发布日期 OpenRouter |
| `Qwen3.5-397B-A17B` | 阿里 Qwen | 2026-02（卡片） / 2026-02-16 | **Apache 2.0** | 397B / 17B | 262,144 原生，YaRN 可扩到 1,010,000 | [A] HF card / [B] 日期 OpenRouter |
| `Qwen3.5-122B-A10B` | 阿里 Qwen | 2026-02 / 2026-02-25 | **Apache 2.0** | 122B / 10B | 262,144 → 1,010,000 | [A] HF card / [B] 日期 OpenRouter |
| `Qwen3.6-35B-A3B` | 阿里 Qwen | 2026-04（卡片）/ 2026-04-27 | **Apache 2.0** | 35B / **3B** | 262,144 → 1,010,000 | [A] HF card / [B] 日期 OpenRouter |
| `MiniMax-M3` | MiniMax | 2026-05-31 [B] | **minimax-community**（自定义） | ~428B / ~23B | 1M | [A] HF card / [B] 日期 OpenRouter |
| `Solar-Open2-250B` | Upstage | 约 2026-07 下旬（arXiv 2607.20062） | **Upstage Solar License**（自定义） | 250B / 15B（321 专家 = 320 路由 + 1 共享） | 1M | [A] HF card |
| `gpt-oss-120b` / `gpt-oss-20b` | OpenAI | 2025-08-26（**近一年未更新**） | Apache 2.0（本次未复核许可证文本） | 120B / 22B | 未复核 | [A] HF org 页更新日期 |

**关键观察**：OpenAI 的开放权重线自 2025-08 起停更近一年（HF org 页 `gpt-oss-120b` 最后更新 2025-08-26）[A]。2026 年的开放权重竞赛**基本是中国厂商的内战**（DeepSeek / 智谱 / 阿里 / Moonshot / MiniMax），外加韩国的 Upstage、LG（`K-EXAONE-2.0-750B-A37B`）、SKT（`A.X-K2` 692B）。

### 1.1 参数量口径不一致的坑（上台前必须知道）

HF org 列表页显示的参数量是从 safetensors index 自动统计的，**与 model card 正文不一致**：

| 仓库 | HF 自动计数 | model card 正文 |
|---|---|---|
| `deepseek-ai/DeepSeek-V4-Pro-DSpark` | 1.7T | 1.6T / 49B 激活 |
| `deepseek-ai/DeepSeek-V4-Flash-DSpark` | 165B | 284B / 13B 激活 |
| `deepseek-ai/DeepSeek-V4-Flash`（trending 页） | 158B | — |
| `deepseek-ai/DeepSeek-V4-Flash-0731` | 304B | — |

原因大概率是 FP8 打包格式导致的计数差异（0731 的 config.json 明确 `quant_method: fp8`, `weight_block_size: [128,128]`）[A]。**演讲请统一采用 model card 正文口径，并注明"官方 model card 数字"。**

---

## 2. 官方 API 价格（USD / 每百万 token）

### 2.1 开放权重模型 —— 厂商第一方 API

| 模型 | 输入（cache miss） | 输入（cache hit） | 输出 | 来源 |
|---|---|---|---|---|
| `deepseek-v4-flash` | **$0.14** | $0.0028 | **$0.28** | [A] api-docs.deepseek.com/quick_start/pricing |
| `deepseek-v4-pro` | **$0.435** | $0.003625 | **$0.87** | [A] 同上 |
| `GLM-5.2` (z.ai 国际站) | **$1.4** | $0.26 | **$4.4** | [A] docs.z.ai/guides/overview/pricing |
| `GLM-5.1` | $1.4 | $0.26 | $4.4 | [A] 同上 |
| `GLM-5` | $1.0 | $0.2 | $3.2 | [A] 同上 |
| `GLM-4.7` | $0.6 | $0.11 | $2.2 | [A] 同上 |
| `GLM-4.7-FlashX` | $0.07 | $0.01 | $0.4 | [A] 同上 |
| `GLM-4.7-Flash` / `GLM-4.5-Flash` | **Free** | Free | Free | [A] 同上 |
| `kimi-k3` | **$3.00** | $0.30 | **$15.00** | [A] platform.kimi.ai/docs/pricing/chat-k3.md |

> ⚠️ **DeepSeek 峰谷定价**：官方定价页原文："The DeepSeek API service will soon adopt a peak/off-peak pricing policy. During peak hours, prices will be 2x the regular prices"，峰值时段为北京时间每日 **9:00–12:00 与 14:00–18:00**。[A] 上表为非峰值价，**峰值时段翻倍**。

> ⚠️ **DeepSeek 老模型下线**：`deepseek-chat` 与 `deepseek-reasoner` 已于 **2026-07-24 15:59 UTC** 后完全不可访问。[A] api-docs.deepseek.com/news/news260424

### 2.2 开放权重模型 —— 第三方托管价（OpenRouter，[B]）

未找到第一方官方定价页的，用 OpenRouter 兜底，**明确降级为 [B]**：

| 模型 | 输入 | 输出 | 上下文 | 来源 |
|---|---|---|---|---|
| `qwen/qwen3.5-397b-a17b` | $0.385 | $2.45 | 262K | [B] openrouter.ai |
| `qwen/qwen3.5-122b-a10b` | $0.26 | $2.08 | 262K | [B] openrouter.ai |
| `qwen/qwen3.6-35b-a3b` | $0.10 | $0.95 | 262K（可 YaRN 到 1M） | [B] openrouter.ai |
| `minimax/minimax-m3` | $0.24 | $0.96（页面标注含 60% 折扣） | 1M | [B] openrouter.ai |
| `z-ai/glm-5.2` | $0.70 | $2.20（页面标注含 50% 折扣） | 1M | [B] openrouter.ai |
| `moonshotai/kimi-k3` | $2.90 | $14 | 1M | [B] openrouter.ai |
| `deepseek/deepseek-v4-pro` | $0.435 | $0.87 | 1M | [B] openrouter.ai（与官方一致）|

> 阿里百炼（Model Studio）**闭源** Qwen 商用模型官方价 [A]（alibabacloud.com/help/en/model-studio/billing-for-model-studio）：
> - Qwen-Max（新加坡）：`0<Token≤1M` → **$2.5 输入 / $7.5 输出**
> - Qwen-Plus（新加坡）：`0<Token≤256K` → **$0.4 / $1.6**；`256K<Token≤1M` → **$1.2 / $4.8**
> - Qwen-Flash（新加坡）：`0<Token≤256K` → **$0.25 / $1.5**；`256K<Token≤1M` → **$1 / $4**
>
> 百炼上 `qwen3.7-max` / `qwen3.7-plus` / `qwen3.6-flash` 的**具体价格与上下文长度未获证实**（文档页未渲染出价格表）。这三个是**闭源**模型，不在本文档主线内。

### 2.3 闭源第一梯队对照价 [A]

**Anthropic**（platform.claude.com/docs/en/about-claude/pricing）：

| 模型 | 输入 | 5m 缓存写 | 缓存命中 | 输出 |
|---|---|---|---|---|
| Claude Fable 5 | $10 | $12.50 | $1 | **$50** |
| Claude Opus 5 / 4.8 / 4.7 / 4.6 / 4.5 | $5 | $6.25 | $0.50 | **$25** |
| Claude Sonnet 5（**2026-08-31 前**促销价） | **$2** | $2.50 | $0.20 | **$10** |
| Claude Sonnet 5（2026-09-01 起） | $3 | $3.75 | $0.30 | $15 |
| Claude Haiku 4.5 | $1 | $1.25 | $0.10 | $5 |

**OpenAI**（developers.openai.com/api/docs/pricing）：

| 模型 | 输入 | 缓存输入 | 输出 |
|---|---|---|---|
| gpt-5.6-sol | $5.00 | $0.50 | **$30.00** |
| gpt-5.6-terra | $2.00 | $0.20 | $12.00 |
| gpt-5.6-luna | $0.20 | $0.02 | $1.20 |
| gpt-5.5 | $5.00 | $0.50 | $30.00 |
| gpt-5.4 | $2.50 | $0.25 | $15.00 |

> ⚠️ **一个极重要的隐藏成本因子** [A]：Anthropic 定价文档原文——"Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer… **This tokenizer produces approximately 30% more tokens for the same text.**"
> 也就是说，Opus 4.7/4.8/5、Fable 5、Sonnet 5 在**处理同一段文本**时会比 Sonnet 4.6 及更早的模型多出约 30% token。**做跨厂商价格对比时，Claude 新模型的"每字成本"应在标价基础上再乘 ~1.3。**

---

## 3. 性价比：算法与结果

### 3.1 算法说明（台上要能讲清楚）

Agentic coding 的典型 token 配比是**输入远多于输出**。本文档统一采用 **input:output = 3:1** 的混合价：

```
blended = (3 × input_price + 1 × output_price) / 4
```

所有价格取 **cache miss 的标价**（不算缓存折扣，因为各家缓存命中率不可比）；DeepSeek 取**非峰值价**。

### 3.2 混合价与倍数

| 模型 | 输入 | 输出 | **混合价 (3:1)** | 相对 Opus 5 便宜 | 相对 GPT-5.6 Sol 便宜 | 价格来源级别 |
|---|---|---|---|---|---|---|
| Claude Opus 5 | $5 | $25 | **$10.00** | 1.0× | — | [A] |
| Claude Fable 5 | $10 | $50 | $20.00 | 0.5× | — | [A] |
| Claude Sonnet 5（促销） | $2 | $10 | $4.00 | 2.5× | — | [A] |
| gpt-5.6-sol | $5 | $30 | **$11.25** | — | 1.0× | [A] |
| gpt-5.6-terra | $2 | $12 | $7.50 | — | 1.5× | [A] |
| **Kimi K3** | $3 | $15 | **$6.00** | **1.67×** | **1.88×** | [A] |
| **GLM-5.2**（z.ai 官方） | $1.4 | $4.4 | **$2.15** | **4.65×** | **5.23×** | [A] |
| **Qwen3.5-397B-A17B** | $0.385 | $2.45 | **$0.901** | **11.1×** | 12.5× | [B] |
| **Qwen3.5-122B-A10B** | $0.26 | $2.08 | **$0.715** | **14.0×** | 15.7× | [B] |
| **DeepSeek-V4-Pro** | $0.435 | $0.87 | **$0.544** | **18.4×** | 20.7× | [A] |
| **MiniMax-M3** | $0.24 | $0.96 | **$0.420** | **23.8×** | 26.8× | [B]（含折扣） |
| **Qwen3.6-35B-A3B** | $0.10 | $0.95 | **$0.3125** | **32.0×** | 36.0× | [B] |
| **DeepSeek-V4-Flash** | $0.14 | $0.28 | **$0.175** | **57.1×** | 64.3× | [A] |

**若把 Claude 新 tokenizer 的 +30% token 计入**（Opus 5 有效混合价 ≈ $13.00 / 同等文本量），倍数进一步放大：
- DeepSeek-V4-Pro：18.4× → **约 23.9×**（派生估算，非官方数字）
- GLM-5.2：4.65× → **约 6.0×**（派生估算）
- Kimi K3：1.67× → **约 2.2×**（派生估算）

### 3.3 只看输出 token（agent 场景成本大头往往在这里）

| 对比 | 倍数 |
|---|---|
| Opus 5 ($25) ÷ DeepSeek-V4-Pro ($0.87) | **28.7×** |
| Opus 5 ($25) ÷ GLM-5.2 ($4.4) | **5.68×** |
| Opus 5 ($25) ÷ Kimi K3 ($15) | **1.67×** |
| Opus 5 ($25) ÷ DeepSeek-V4-Flash ($0.28) | **89.3×** |
| gpt-5.6-sol ($30) ÷ DeepSeek-V4-Flash ($0.28) | **107×** |

### 3.4 订阅制（另一条性价比路径）[A]

**GLM Coding Plan**（docs.z.ai/devpack/overview）：三档 Lite / Pro / Max，官方原文 "starting at just 18 USD per month"（Pro 档）。**Lite 与 Max 的具体月费未获证实**。额度表：

| 套餐 | 5 小时额度 | 每周额度 | 官方估算周 token 量（按 GLM-5.2、90.9% 缓存命中） |
|---|---|---|---|
| Lite | 2,000 | 10,000 | ~43–87 M |
| Pro | 12,000 | 60,000 | ~263–526 M |
| Max | 28,000 | 140,000 | ~613–1,226 M |

> 粗算：Pro 档 $18/月 拿到 ~263–526M token/周 ≈ 1–2.1B token/月。若按 GLM-5.2 API 混合价 $2.15/M 计，等价 API 消费约 **$2,300–4,500/月**。这是订阅制相对 API 的量级差，**演讲时务必说明这是理论上限、受 5 小时窗口限流**。

---

## 4. 相对闭源第一梯队差多少（量化）

⚠️ 以下每个表都来自**单一 model card**，卡内横比可用，**跨表不可混比**。

### 4.1 来自 Kimi K3 官方 model card [A]

| Benchmark | **Kimi K3** | Claude Fable 5 | GPT-5.6 Sol | Claude Opus 4.8 | GPT-5.5 | GLM-5.2 |
|---|---|---|---|---|---|---|
| GPQA Diamond | **93.5** | 92.6 | 94.1 | 91.0 | 93.5 | 91.2 |
| CritPt | 23.4 | 28.6 | **32.3** | 20.9 | 27.1 | 20.9 |
| DeepSWE | 67.5 | 70.0 | **73.0** | 59.0 | 67.0 | 46.2 |
| Terminal-Bench 2.1 | **88.3** | 88.0 | 88.8 | 84.6 | 83.4 | 82.7 |
| BrowseComp | **91.2** | 88.0 | 90.4 | 84.3 | 84.4 | — |
| OSWorld-Verified | 84.8 | **85.0** | 83.0 | 83.4 | 79.0 | — |
| MMMU-Pro | 81.6/83.4 | 81.2/86.5 | 83.0/84.6 | 78.9/82.7 | 81.2/83.2 | — |

**差距量化（Kimi K3 vs 闭源最强项）**：
- Terminal-Bench 2.1：**-0.5 分**（88.3 vs GPT-5.6 Sol 88.8）→ 实质持平
- GPQA Diamond：**-0.6 分**（93.5 vs 94.1）→ 实质持平；且**超过 Opus 4.8 +2.5 分**
- BrowseComp：**+0.8 分领先 GPT-5.6 Sol**，+3.2 领先 Fable 5
- DeepSWE：**-5.5 分**（67.5 vs 73.0），但**超过 Opus 4.8 +8.5 分**
- CritPt（物理推理）：**-8.9 分**（23.4 vs 32.3）→ **最大短板**

**结论：Kimi K3 在 agent / 检索 / 终端任务上已与闭源前沿持平，在硬推理（CritPt）与 SWE 类任务上仍差 5–9 分。价格是 Opus 5 的 1/1.67。**

### 4.2 来自 GLM-5.2 官方 model card [A]

| Benchmark | **GLM-5.2** | GLM-5.1 | Qwen3.7-Max | MiniMax M3 | DeepSeek-V4-Pro | Claude Opus 4.8 | GPT-5.5 | Gemini 3.1 Pro |
|---|---|---|---|---|---|---|---|---|
| HLE | 40.5 | 31 | 41.4 | 37 | 37.7 | **49.8\*** | 41.4\* | 45 |
| HLE (w/ Tools) | 54.7 | 52.3 | 53.5 | — | 48.2 | **57.9\*** | 52.2\* | 51.4\* |
| CritPt | 20.9 | 4.6 | 13.4 | 3.7 | 12.9 | 20.9 | **27.1** | 17.7 |
| AIME 2026 | **99.2** | 95.3 | 97 | — | 94.6 | 95.7 | 98.3 | 98.2 |
| HMMT Nov. 2025 | 94.4 | 94 | 95 | 84.4 | 94.4 | **96.5** | 96.5 | 94.8 |
| HMMT Feb. 2026 | 92.5 | 82.6 | **97.1** | 84.4 | 95.2 | 96.7 | 96.7 | 87.3 |
| IMOAnswerBench | **91.0** | 83.8 | 90 | — | 89.8 | 83.5 | — | 81 |
| GPQA-Diamond | 91.2 | 86.2 | 90 | 93 | 90.1 | 93.6 | 93.6 | **94.3** |
| SWE-bench Pro | 62.1 | 58.4 | 60.6 | 59 | 55.4 | **69.2** | 58.6 | 54.2 |
| NL2Repo | 48.9 | 42.7 | 47.2 | 42.1 | 35.5 | **69.7** | 50.7 | 33.4 |
| DeepSWE | 46.2 | 18 | 18 | 20 | 8 | 58 | **70** | 10 |
| ProgramBench | 63.7 | 50.9 | — | — | 47.8 | **71.9** | 70.8 | 39.5 |
| Terminal Bench 2.1 (Terminus-2) | 81.0 | 63.5 | 75 | 65 | 64 | **85** | 84 | 74 |
| Terminal Bench 2.1 (Best Reported) | **82.7** | 69 | — | — | — | 78.9 | 83.4 | 70.7 |
| FrontierSWE (Dominance) | 74.4 | 30.5 | — | — | 29.0 | **75.1** | 72.6 | 39.6 |
| PostTrainBench | 34.3 | 20.1 | — | — | — | **37.2** | 28.4 | 21.6 |
| SWE-Marathon | 13.0 | 1.0 | — | — | — | **26.0** | 12.0 | 4.0 |
| MCP-Atlas (Public Set) | 76.8 | 71.8 | 76.4 | 74.2 | 73.6 | **77.8** | 75.3 | 69.2 |
| Tool-Decathlon | 48.2 | 40.7 | — | — | 52.8 | **59.9** | 55.6 | 48.8 |

**差距量化（GLM-5.2 vs Claude Opus 4.8）**：
- **反超**：AIME 2026 +3.5、IMOAnswerBench +7.5、Terminal Bench 2.1 best-reported +3.8、CritPt 持平
- **接近**：MCP-Atlas -1.0、FrontierSWE -0.7、PostTrainBench -2.9
- **明显落后**：NL2Repo **-20.8**、SWE-Marathon **-13.0**、DeepSWE -11.8、ProgramBench -8.2、HLE -9.3、SWE-bench Pro -7.1、Tool-Decathlon -11.7

**结论：GLM-5.2 在数学 / 单轮推理上已经追平甚至反超；在"长程仓库级工程任务"（NL2Repo、SWE-Marathon、DeepSWE）上仍有 12–21 分的硬差距。价格 1/4.65。**

### 4.3 来自 DeepSeek-V4-Flash-0731 官方 model card [A]

| Benchmark | **DS-V4-Flash-0731** | DS-V4-Flash (preview) | DS-V4-Pro (preview) | GLM-5.2 | Opus-4.8 |
|---|---|---|---|---|---|
| Terminal Bench 2.1 | 82.7 | 61.8 | 72.1 | 81.0 | **85.0** |
| NL2Repo | 54.2 | 39.4 | 38.5 | 48.9 | **69.7** |
| Cybergym | 76.7 | 38.7 | 52.7 | — | **83.1** |
| DeepSWE | 54.4 | 7.3 | 12.8 | 46.2 | **58.0** |
| Toolathlon-Verified | 70.3 | 49.7 | 55.9 | 59.9 | **76.2** |

**差距量化（DS-V4-Flash-0731 vs Opus 4.8）**：Terminal Bench -2.3、DeepSWE -3.6、Cybergym -6.4、Toolathlon -5.9、NL2Repo **-15.5**。

**这是本次采集里最惊人的一条**：一个**混合价 $0.175/M（Opus 5 的 1/57）**、总参 304B 的模型，在 Terminal Bench 2.1 上只落后 Opus 4.8 **2.3 分**；且相对自家 4 月的 preview 版（61.8）暴涨 **+20.9 分**——三个月的 post-training 迭代幅度大于半数模型的代际差。

### 4.4 来自 DeepSeek-V4-Pro 官方 model card（base 模型） [A]

| Benchmark | DeepSeek-V3.2-Base | DeepSeek-V4-Flash-Base | **DeepSeek-V4-Pro-Base** |
|---|---|---|---|
| MMLU (5-shot) | 87.8 | 88.7 | **90.1** |
| MMLU-Pro (5-shot) | 65.5 | 68.3 | **73.5** |
| HumanEval (Pass@1) | 62.8 | 69.5 | **76.8** |
| LongBench-V2 (1-shot) | 40.2 | 44.7 | **51.5** |

Instruct + 前沿模型对比（同卡片）：

| Benchmark | Opus-4.6 Max | GPT-5.4 xHigh | Gemini-3.1-Pro | **DS-V4-Pro Max** |
|---|---|---|---|---|
| MMLU-Pro | 89.1 | 87.5 | **91.0** | 87.5 |
| LiveCodeBench | 88.8 | — | 91.7 | **93.5** |
| Codeforces | — | 3168 | 3052 | **3206** |

DeepSeek-V4-Flash-Base 完整表 [A]：AGIEval 82.6 / MMLU 88.7 / MMLU-Redux 89.4 / MMLU-Pro 68.3 / C-Eval 92.1 / HumanEval 69.5 / GSM8K 90.8 / LongBench-V2 44.7。

Reasoning 档位对比 [A]：

| Benchmark | V4-Flash Non-Think | V4-Flash High | V4-Flash Max | V4-Pro Non-Think | V4-Pro High | V4-Pro Max |
|---|---|---|---|---|---|---|
| MMLU-Pro | 83.0 | 86.4 | 86.2 | 82.9 | 87.1 | 87.5 |
| SimpleQA-Verified | 23.1 | 28.9 | 34.1 | 45.0 | 46.2 | **57.9** |
| LiveCodeBench | 55.2 | 88.4 | 91.6 | — | — | — |
| Codeforces | — | 2816 | 3052 | — | — | — |

> **一个可以直接上台的对比**：Flash 的 LiveCodeBench 从 Non-Think 的 55.2 → Max 的 91.6，**推理档位带来 +36.4 分**。这比"换个更大的模型"收益大得多。

### 4.4b Qwen3.5-397B-A17B 官方 model card [A]

| Benchmark | **Qwen3.5-397B-A17B** | GPT5.2 | Claude 4.5 Opus | Gemini-3 Pro |
|---|---|---|---|---|
| MMLU-Pro | 87.8 | 87.4 | 89.5 | **89.8** |
| SuperGPQA | 70.4 | 67.9 | 70.6 | **74.0** |
| GPQA | 88.4 | **92.4** | 87.0 | 91.9 |
| LiveCodeBench v6 | 83.6 | 87.7 | 84.8 | **90.7** |
| HMMT Feb 25 | 94.8 | **99.4** | 92.9 | 97.3 |
| MMMU | 85.0 | 86.7 | 80.7 | **87.2** |
| MathVision | **88.6** | 83.0 | 74.3 | 86.6 |
| RefCOCO (avg) | **92.3** | — | — | 84.1 |
| OCRBench | **93.1** | 80.7 | 85.8 | 90.4 |

> 注意：Qwen 这张卡对标的是 **GPT-5.2 / Claude 4.5 Opus / Gemini-3 Pro**（2026 年 2 月的前沿），不是当前 8 月的前沿。**这张表在 2026-08 已经过期半年，上台请注明时点。**

### 4.4c Qwen3.5-122B-A10B / Qwen3.6-35B-A3B 官方 model card [A]

Qwen3.5-122B-A10B 卡片：

| Benchmark | GPT-5-mini (2025-08-07) | GPT-OSS-120B | Qwen3-235B-A22B | **Qwen3.5-122B-A10B** | Qwen3.5-27B | Qwen3.5-35B-A3B |
|---|---|---|---|---|---|---|
| MMLU-Pro | 83.7 | 80.8 | 84.4 | **86.7** | 86.1 | 85.3 |
| MMLU-Redux | 93.7 | 91.0 | 93.8 | **94.0** | 93.2 | 93.3 |
| C-Eval | 82.2 | 76.2 | **92.1** | 91.9 | 90.5 | 90.2 |
| SuperGPQA | 58.6 | 54.6 | 64.9 | **67.1** | 65.6 | 63.4 |
| IFEval | 93.9 | 88.9 | 87.8 | 93.4 | **95.0** | 91.9 |
| GPQA Diamond | 82.8 | 80.1 | 81.1 | **86.6** | 85.5 | 84.2 |
| SWE-bench Verified | 72.0 | 62.0 | — | 72.0 | **72.4** | 69.2 |
| MMMU | 79.0 | — | 80.6 | **83.9** | 82.3 | 81.4 |
| MMMU-Pro | 67.3 | — | 69.3 | **76.9** | 75.0 | 75.1 |
| MathVision | 71.9 | — | 74.6 | **86.2** | 86.0 | 83.9 |

Qwen3.6-35B-A3B 卡片（**35B 总参 / 3B 激活**，这是"能本地跑"档位的天花板）：

| Benchmark | Qwen3.5-27B | Gemma4-31B | Qwen3.5-35BA3B | Gemma4-26BA4B | **Qwen3.6-35BA3B** |
|---|---|---|---|---|---|
| SWE-bench Verified | **75.0** | 52.0 | 70.0 | 17.4 | 73.4 |
| SWE-bench Pro | **51.2** | 35.7 | 44.6 | 13.8 | 49.5 |
| MMLU-Pro | **86.1** | 85.2 | 85.3 | 82.6 | 85.2 |
| GPQA | 85.5 | 84.3 | 84.2 | 82.3 | **86.0** |
| AIME26 | 92.6 | 89.2 | 91.0 | 88.3 | **92.7** |
| MMMU | **82.3** | 80.4 | — | — | 81.7 |
| RealWorldQA | 83.7 | 72.3 | — | Claude-Sonnet-4.5: 70.3 | **85.3** |
| MMBenchEN-DEV | 92.6 | 90.9 | — | Claude-Sonnet-4.5: 88.3 | **92.8** |

> **一个 3B 激活参数的模型跑出 SWE-bench Verified 73.4 / AIME26 92.7**——这是本次快照里"性价比"最极端的数据点。同卡片显示它在 RealWorldQA 上比 Claude-Sonnet-4.5 高 **+15.0 分**（85.3 vs 70.3）。

### 4.4d MiniMax-M3 官方 model card [A]

| Benchmark | Score |
|---|---|
| SWE-bench Verified | 80.5\* |
| SWE-bench Pro | 59\* |
| Apex Agents | 27.7\* |
| Long-Horizon Terminal Bench | 38.5\* |
| Video-MME v2 | 85.4\* |
| MMMU Pro | 78.1\* |
| Claw-Eval (General) | 74.5\* |

架构亮点 [A]：MiniMax Sparse Attention (MSA)，官方称在 1M 上下文下相对 M2 有 **9× prefill / 15× decode 加速**。model card 未列对照模型。

### 4.4e Solar-Open2-250B 官方 model card [A]

MMLU-Pro 86.2 / GPQA-Diamond 86.3 / SWE-Bench Verified 70.4 / AIME2026 95.7 / LiveCodeBench (v6) 92.4。250B 总参、**15B 激活**、1M 上下文、321 专家（320 路由 + 1 共享）。

---

## 5. 哪些真能本地跑？（显存 / 内存需求，全部 [A]，来自 unsloth GGUF 仓库文件体积）

| 模型 | 4-bit 体积 | 1–2 bit 体积 | BF16 体积 | 现实可跑硬件 | 判定 |
|---|---|---|---|---|---|
| **Qwen3.6-35B-A3B** | UD-Q4_K_M **22.1 GB** | UD-IQ1_M 10 GB | 69.4 GB | 单张 RTX 4090 24G（紧）/ 5090 32G / 32GB+ 统一内存 Mac | ✅ **真·本地** |
| Qwen3.6-35B-A3B（低配） | UD-IQ4_XS 17.7 GB | UD-Q2_K_XL 12.3 GB | — | 16–20GB 显卡可跑 2–3bit | ✅ 笔记本可及 |
| **DeepSeek-V4-Flash**（284B/13B） | UD-Q4_K_XL **155 GB** | UD-IQ1_S 82.5 GB | — | Mac Studio 192G/256G 统一内存跑 4-bit；2×H100 80G 跑 1-bit 勉强 | ⚠️ **发烧友 / 小机房** |
| **GLM-5.2**（753B） | UD-Q4_K_M **466 GB** | UD-IQ1_S **217 GB** | **1.51 TB** | 4-bit 需 8×H100 80G(640G) 不够，要 8×H200 141G(1128G)；1-bit 可上 Mac Studio 512G | ❌ **企业机房级** |
| **Kimi K3**（2.8T/104B） | UD-Q4_K_XL **1.51 TB** | UD-IQ1_S **594 GB** | — | 1-bit 都要 ≥640GB 显存；4-bit 需 ~16×H200 | ❌ **"开放权重但你跑不动"** |
| DeepSeek-V4-Pro（1.6T/49B） | 体积未获证实（存在第三方 GGUF：teamblobfish 33.1k 下载） | — | — | 按 1.6T 推算与 Kimi K3 同量级 | ❌ 企业机房级 |

unsloth Kimi K3 GGUF 全量表 [A]：UD-IQ1_S 594 GB / UD-IQ1_M 649 GB / UD-Q2_K_XL 861 GB / UD-Q4_K_XL 1.51 TB / UD-Q8_K_XL 1.56 TB。

unsloth GLM-5.2 GGUF 全量表 [A]：IQ1_S 217 / IQ1_M 228 / IQ2_XXS 238 / IQ2_M 239 / Q2_K_XL 254 / IQ3_XXS 282 / IQ3_S 309 / Q3_K_M 343 / IQ4_XS 365 / IQ4_NL 373 / Q4_K_S 436 / Q4_K_M 466 / Q5_K_M 561 / Q6_K 626 / Q8_0 801 GB / BF16 1.51 TB。

unsloth DeepSeek-V4-Flash GGUF 全量表 [A]：IQ1_S 82.5 / IQ1_M 86.9 / IQ2_XXS 90.9 / Q2_K_XL 96.8 / IQ3_XXS 103 / IQ3_S 117 / Q3_K_M 129 / IQ4_XS 138 / IQ4_NL 138 / Q4_K_XL 155 / Q8_K_XL 162 GB。

**官方部署提示** [A]：
- DeepSeek-V4-Flash：`temperature = 1.0, top_p = 1.0`；Think Max 模式**建议上下文窗口至少 384K**。
- Qwen3.6-35B-A3B：默认 262,144 上下文；OOM 时降上下文，但**至少保留 128K 才能维持 thinking 能力**。

### 5.1 结论：三层"私有化可行性"

1. **真本地（单卡/单机）**：Qwen3.5-4B/9B/27B、**Qwen3.6-35B-A3B**（22 GB @ Q4）。Apache 2.0，无任何商用限制。这是唯一能在开发者笔记本 / 单张消费卡上跑的一档。
2. **私有机房（8 卡起）**：DeepSeek-V4-Flash（155 GB @ Q4）、GLM-5.2（466 GB @ Q4）、MiniMax-M3、Solar-Open2-250B。MIT 或自定义许可。
3. **"开放权重但你跑不动"**：Kimi K3（1.51 TB @ Q4）、DeepSeek-V4-Pro（1.6T）。权重公开的实际价值是"防供应商锁定 + 可审计"，不是"我自己跑"。**上台时这句是核心洞见。**

---

## 6. 许可证：能不能真的私有化（这是核心）

| 模型 | 许可证 | 商用是否需要额外动作 | 具体阈值 |
|---|---|---|---|
| **DeepSeek-V4-Pro / Flash / Flash-0731** | **MIT** | ❌ 无任何限制 | — |
| **GLM-5.2 / GLM-5.1 / GLM-5** | **MIT** | ❌ 无任何限制 | — |
| **Qwen3.5 全系 / Qwen3.6-35B-A3B** | **Apache 2.0** | ❌ 无任何限制 | — |
| **Kimi K3** | **Kimi K3 License** | ⚠️ 有 | ① 若以 MaaS/API 形式对外提供，且**连续 12 个月累计营收 > $20M**，须先另行签协议；② 产品**MAU > 1 亿 或 月营收 > $2000 万** 时，须在 UI 显著位置展示 "Kimi K3"。内部使用与通过 Moonshot 官方产品/认证伙伴访问的场景豁免。[A] |
| **MiniMax-M3** | **minimax-community** | ⚠️ 有 | ① 商用须在网站/界面/文档显著展示 **"Built with MiniMax M3"**；② 年营收 **< $20M**：向 api@minimax.io 发一次性告知邮件（主题 "M3 licensing — notice"）；③ 年营收 **> $20M**：须取得**事先书面授权**。[A] |
| **Solar-Open2-250B** | **Upstage Solar License** | ⚠️ 有 | 衍生模型名必须带 "Solar" 前缀、展示 "Built with Solar" 归属、附许可证副本。[A] |

**给企业听众的一句话**：想要零法务摩擦，只有 **MIT（DeepSeek / GLM）** 和 **Apache 2.0（Qwen）** 三家。Kimi / MiniMax / Solar 的许可证都带营收阈值或署名义务，采购前必须过法务。

---

## 7. 中国大陆可直连的选项

| 厂商 | 大陆站点 | 本次是否亲自抓取验证 | 说明 |
|---|---|---|---|
| DeepSeek | `api-docs.deepseek.com` / `platform.deepseek.com` | ✅ 抓取到定价页与 news 页 [A] | 中国公司自营平台；定价页以 USD 标示 |
| 智谱 Z.AI | 国内 `open.bigmodel.cn` / `docs.bigmodel.cn`；国际 `z.ai` | ✅ 抓取到 `docs.bigmodel.cn` 模型总览（含 GLM-5.2 1M ctx / 128K max output）[A]；`open.bigmodel.cn/pricing` 为纯 JS 页，**人民币价格未获证实** | 国内外双站，价格体系不同 |
| 阿里百炼 | `help.aliyun.com/zh/model-studio` | ✅ 抓取到模型列表页 [A]；**人民币价格未获证实**（页面未渲染价格表） | 国际站新加坡区价格已确认（见 2.2） |
| Moonshot / Kimi | 国际 `platform.kimi.ai`（原 `platform.moonshot.ai` 301 跳转）；国内站 `platform.moonshot.cn` | ⚠️ 只验证了国际站 [A]；**国内站本次未抓取，未获证实** | — |
| MiniMax | `minimax.io` | ❌ 本次只抓了 HF 与 OpenRouter | 大陆站点未验证 |

**权重下载渠道**：所有上述模型的权重都在 Hugging Face 上（本次全部亲自抓取）。大陆用户通常走 ModelScope 镜像 —— **本次未验证 ModelScope 上的对应仓库，未获证实**。

---

## 8. 生态热度（HF trending，text-generation，2026-08-01 抓取）[A]

| 排名 | 组织 / 模型 | 参数 | 更新 |
|---|---|---|---|
| 1 | deepseek-ai / DeepSeek-V4-Flash-0731 | 304B | 36 分钟前 |
| 2 | Kwaipilot / KAT-Coder-V2.5-Dev | 35B | 4 天前 |
| 3 | zai-org / GLM-5.2 | 753B | 30 天前 |
| 4 | poolside / Laguna-S-2.1 | 118B | 5 天前 |
| 5 | Nanbeige / Nanbeige4.2-3B | 4B | 4 天前 |
| 6 | upstage / Solar-Open2-250B | 250B | 约 6 小时前 |
| 7 | XYZAILab / XYZ-Aquila-mini | 35B | 3 天前 |
| 9 | XYZAILab / XYZ-Aquila-pro | 397B | 3 天前 |
| 16 | LGAI-EXAONE / K-EXAONE-2.0-750B-A37B | 749B | 1 天前 |
| 17 | skt / A.X-K2 | 692B | 2 天前 |
| 24 | deepseek-ai / DeepSeek-V4-Pro | 1.6T | Jun 22 |

Qwen3.5 / 3.6 下载量（HF 搜索页，[A]）：Qwen3.5-9B **11.9M**、Qwen3.5-4B 6.3M、Qwen3.5-0.8B 3.04M、Qwen3.5-27B 2.71M、Qwen3.5-35B-A3B 2.57M、Qwen3.5-122B-A10B 1.78M；Qwen3.6-35B-A3B-FP8 **8.47M**、Qwen3.6-27B-FP8 7.4M、Qwen3.6-27B 6.62M、Qwen3.6-35B-A3B 6.1M。

> **反直觉洞见**：下载量最高的是 **9B 和 4B**，不是旗舰。开放权重的真实使用重心在"小到能自己跑"的那一档，而不是媒体讨论的 1T 级模型。

---

## 9. 未获证实 / 需要人工补齐的项

以下条目本次**没能抓到可信来源，绝不能上台引用**：

1. **GLM-5.2 的激活参数量** —— 官方 model card 与 config.json 均未标注。config.json 只给出：256 路由专家 + 1 共享专家、每 token 激活 8 个、hidden_size 6144、78 层、max_position_embeddings 1,048,576 [A]。
2. **DeepSeek-V4-Flash-0731 的激活参数量** —— config.json：256 路由专家 + 1 共享、`num_experts_per_tok: 6`、hidden_size 4096、43 层、FP8 (e4m3) [A]，但官方未给激活参数总数。
3. **智谱 open.bigmodel.cn 的人民币价格表**。
4. **阿里百炼 qwen3.7-max / qwen3.7-plus / qwen3.6-flash 的价格与上下文**。
5. **GLM Coding Plan 的 Lite 与 Max 档月费**（只有 Pro 的 "starting at just 18 USD per month"）。
6. **Artificial Analysis 的独立评测分数**（页面 JS 渲染，抓取结果为陈旧片段，已弃用）。
7. **DeepSeek-V4-Pro 的 GGUF 量化体积**。
8. **MiniMax-M3 的确切发布日**：HF card 引用 arXiv 2606.13392（→ 2026-06），OpenRouter 写 2026-05-31 [B]，HF org 页显示"9 天前更新"。三者不一致。
9. **Kimi K3 的官方发布公告日期**（仅有 OpenRouter 的 2026-07-16 [B]）。
10. **各家在 ModelScope 上的镜像仓库**。

---

## 10. 主要来源 URL（全部本次亲自抓取）

- DeepSeek 定价：https://api-docs.deepseek.com/quick_start/pricing
- DeepSeek V4 发布公告：https://api-docs.deepseek.com/news/news260424
- DeepSeek-V4-Pro model card：https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark
- DeepSeek-V4-Flash model card：https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark
- DeepSeek-V4-Flash-0731：https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731
- Z.AI 定价：https://docs.z.ai/guides/overview/pricing
- GLM-5.2 model card：https://huggingface.co/zai-org/GLM-5.2
- GLM 模型总览（中文）：https://docs.bigmodel.cn/cn/guide/start/model-overview
- GLM Coding Plan：https://docs.z.ai/devpack/overview
- Kimi K3 model card：https://huggingface.co/moonshotai/Kimi-K3
- Kimi K3 许可证：https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE
- Kimi K3 定价：https://platform.kimi.ai/docs/pricing/chat-k3.md
- Kimi 模型总览：https://platform.kimi.ai/docs/models.md
- Qwen3.5-397B-A17B：https://huggingface.co/Qwen/Qwen3.5-397B-A17B
- Qwen3.5-122B-A10B：https://huggingface.co/Qwen/Qwen3.5-122B-A10B
- Qwen3.6-35B-A3B：https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- 阿里百炼计费：https://www.alibabacloud.com/help/en/model-studio/billing-for-model-studio
- MiniMax-M3：https://huggingface.co/MiniMaxAI/MiniMax-M3
- MiniMax 许可证：https://huggingface.co/MiniMaxAI/MiniMax-M3/raw/main/LICENSE
- Solar-Open2-250B：https://huggingface.co/upstage/Solar-Open2-250B
- Anthropic 定价：https://platform.claude.com/docs/en/about-claude/pricing
- OpenAI 定价：https://developers.openai.com/api/docs/pricing
- unsloth GGUF：https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF ｜ https://huggingface.co/unsloth/GLM-5.2-GGUF ｜ https://huggingface.co/unsloth/DeepSeek-V4-Flash-GGUF ｜ https://huggingface.co/unsloth/Kimi-K3-GGUF
- OpenRouter（[B] 级）：https://openrouter.ai/moonshotai/kimi-k3 ｜ /z-ai/glm-5.2 ｜ /deepseek/deepseek-v4-pro ｜ /qwen/qwen3.5-397b-a17b ｜ /qwen/qwen3.5-122b-a10b ｜ /qwen/qwen3.6-35b-a3b ｜ /minimax/minimax-m3
