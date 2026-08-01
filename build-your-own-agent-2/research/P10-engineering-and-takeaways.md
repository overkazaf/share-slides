# P10：pi-mono 工程规范与「可抄清单」取证

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `pi-mono`（`earendil-works`） | 本地 clone |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/agent/package.json:3`、`packages/coding-agent/package.json:3` |
> | 本地路径 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开验证。
> 行号会随上游提交漂移 —— PPT 上引用时**必须带 commit 短 hash `583f153`**。
> 所有数字均由 `find` / `wc -l` / `grep -c` 实测，未估算。

---

## 0. 一句话总结这一章

pi 不是「一个人随手写的玩具」。它有 **386 个测试文件 / 99331 行测试代码**、**10 条 GitHub Actions 流水线**、**一条把 7 个子检查串成一句话的 `npm run check`**、**12113 行用户文档**，以及一个专门用来做**模型行为评测**的 `packages/evals`。

但它也**不做**很多"标准工程"会做的事：没有 ESLint（用 Biome 一把梭）、没有覆盖率门禁（只有 harness 一处配了 coverage）、没有 e2e CI（真实 provider 的测试全靠环境变量 `skipIf` 自动跳过）、没有 major 版本（`AGENTS.md:122` 明写 "No major releases"）。

这一章的价值不在"pi 有多规范"，而在**它把哪些规范做成了机器可执行的一条命令**。第 6 节的 12 条就是这个提炼。

---

## 1. 测试

### 1.1 体量实测

```bash
$ find packages -path '*/node_modules' -prune -o -type f \
    \( -name '*.test.ts' -o -name '*.test.mjs' -o -name '*.spec.ts' \) -print | wc -l
386
$ find ... -print0 | xargs -0 wc -l | tail -1
99331 total
```

| 包 | 测试文件数 |
|---|---|
| `coding-agent` | 195 |
| `ai` | 122 |
| `tui` | 30 |
| `agent` | 19 |
| `server` | 7 |
| `client` | 6 |
| `evals` | 4 |
| `protocol` | 3 |
| **合计** | **386** |

对照的生产代码体量（`packages/*/src/**/*.ts`，排除 `*.generated.ts`）：**111505 行**。
`packages/*/test/**/*.ts`（含非 `.test.ts` 的 fixture/harness）：**102982 行**。

> **可上 PPT 的比值**：测试代码 ≈ 生产代码的 **0.89 倍**（99331 / 111505）。近似 1:1。

生成代码只有 727 行（`packages/ai/src/image-models.generated.ts` 609 行 + `packages/ai/src/models.generated.ts` 118 行），且 `AGENTS.md:24` 硬性禁止手改：

> `Never modify packages/ai/src/models.generated.ts directly; update packages/ai/scripts/generate-models.ts instead, then regenerate.`

### 1.2 框架：Vitest 为主，node:test 为辅

- 7 个包用 Vitest：`packages/ai/package.json:59`、`packages/agent/package.json:26`、`packages/coding-agent/package.json:41`、`packages/server/package.json:38`、`packages/client/package.json:24`、`packages/protocol/package.json:18` 全是 `"test": "vitest --run"`。
- **`packages/tui` 例外**，用 Node 内置 test runner（`packages/tui/package.json:10`）：
  ```
  "test": "node --test --test-reporter=dot --test-reporter-destination=stdout test/*.test.ts"
  ```
  30 个 `.test.ts` 文件。
- 根目录还有一层：`package.json:34` `"test:scripts": "node --test scripts/*.test.mjs"` —— **构建脚本自己也有测试**（`scripts/sync-versions.test.mjs`，75 行）。
- 根 `test` 聚合（`package.json:33`）：`npm run test:scripts && npm run test --workspaces --if-present`。

### 1.3 一个值得抄的细节：共享 vitest 基座 + 源码 alias

`vitest.base.ts:5-13` 导出 `workspaceSourcePaths`，把 `@earendil-works/pi-ai`、`pi-agent-core`、`pi-tui` 等包名 alias 到**源码 `src/index.ts`**，而不是 `dist/`：

```ts
alias: [
  { find: /^@earendil-works\/pi-ai$/, replacement: workspaceSourcePaths.aiIndex },
  { find: /^@earendil-works\/pi-agent-core$/, replacement: workspaceSourcePaths.agentIndex },
  ...
]                                          // vitest.base.ts:17-30
```

效果：**monorepo 里跑测试不需要先 build**。各包配置用 `mergeConfig(baseConfig, ...)` 继承（`packages/coding-agent/vitest.config.ts:5`、`packages/evals/vitest.config.ts:4`）。

`packages/coding-agent/vitest.config.ts:12-13` 还默认强制离线：

```ts
// Tests run offline by default; opt in with allowNetwork() from test/test-network-env.ts.
env: { PI_OFFLINE: "1" },
```

### 1.4 怎么跑：`./test.sh` 而不是 `npx vitest`

`AGENTS.md:30` 是硬规矩：

> `Never run the full vitest suite directly: it includes e2e tests that activate when endpoint/auth env vars are present. For all non-e2e tests, run ./test.sh from the repo root.`

`test.sh` 79 行，干的事是 **把环境变量清空重建**（`test.sh:40-64`）：

- `mktemp -d "$TMPDIR/pi-test.XXXXXX"` 造一个假 `HOME`（`test.sh:7,11`）
- 白名单式 env：`env -i "${test_env[@]}" npm test`（`test.sh:79`）—— `env -i` 意为**从空环境启动**，只注入列表里的变量
- 禁掉 git 全局配置和交互：`GIT_CONFIG_GLOBAL=/dev/null`、`GIT_TERMINAL_PROMPT=0`、`GIT_ASKPASS=$(type -P false)`（`test.sh:53-56`）
- 禁本地 LLM：`PI_NO_LOCAL_LLM=1`（`test.sh:62`）
- 禁 EC2 元数据探测：`AWS_EC2_METADATA_DISABLED=true`（`test.sh:63`）
- 清理时先验证目录归属才 `rm -rf`（`test.sh:20-33`，靠 `.pi-test-owned` 标记文件）

因为没有任何 API key 被注入，所有真实 provider 的 e2e 测试自动跳过。

### 1.5 e2e 的跳过机制：`describe.skipIf`

`packages/ai/test` + `packages/agent/test` 下共 **372 处 `skipIf`**（`grep -rn "skipIf" | wc -l`）。样式（`packages/ai/test/abort.test.ts:101-113`）：

```ts
describe.skipIf(!process.env.GEMINI_API_KEY)("Google Provider Abort", () => { ... });
describe.skipIf(!process.env.OPENAI_API_KEY)("OpenAI Completions Provider Abort", () => { ... });
```

**没有 key 就静默跳过，有 key 就真打网络**。仓库里 6 个文件名带 `e2e` 的测试文件（`find ... -name '*e2e*.test.ts' | wc -l` = 6）。

### 1.6 faux provider：agent 测试的核心基础设施

这是 pi 测试体系里最值得抄的一件东西。

- 实现：`packages/ai/src/providers/faux.ts`（**541 行**）
- 注册入口：`packages/ai/src/compat.ts:160` `export function registerFauxProvider(...)`
- 便捷构造器：`fauxText()` `:49`、`fauxThinking()` `:53`、`fauxToolCall()` `:57`、`fauxAssistantMessage()` `:73`
- 核心 API：`setResponses(responses: FauxResponseStep[])`（`packages/ai/src/providers/faux.ts:501`）—— **把 LLM 的回复序列写死**

也就是说 pi 把「假 LLM」做成了一个**正式的 provider**（和 openai/anthropic 平级注册进 registry），而不是测试里的 mock 层。测试里注册它、给它一个假 key、指定回复序列，然后跑真实的 `AgentSession`：

```ts
const fauxProvider: FauxProviderRegistration = registerFauxProvider({ ... });  // test/suite/harness.ts:103
fauxProvider.setResponses([]);                                                // :106
await authStorage.modify(model.provider, async () => ({ type: "api_key", key: "faux-key" }));  // :117
```

`packages/coding-agent/test/suite/harness.ts` 共 225 行，是整个 suite 的统一入口。

### 1.7 测试组织：`test/suite/` + 按 issue 号命名的回归目录

`packages/coding-agent/test/suite/README.md`（16 行）逐条写死规矩：

| 行号 | 规矩 |
|---|---|
| `:6` | Use `test/suite/harness.ts` |
| `:7` | Use the faux provider from `packages/ai/src/providers/faux.ts` |
| `:8` | Do not use real provider APIs, real API keys, network calls, or paid tokens |
| `:9` | Keep these tests CI-safe and deterministic |
| `:10` | Do not use or extend the legacy `test/test-harness.ts` path unless a missing capability forces it |
| `:14` | Name regression tests as `<issue-number>-<short-slug>.test.ts` |

实测布局：

```
packages/coding-agent/test/*.test.ts              132 个（历史遗留 + 单元）
packages/coding-agent/test/suite/*.test.ts          8 个（新的 harness 体系）
packages/coding-agent/test/suite/regressions/       44 个（按 issue 号命名）
```

回归文件名实例：`packages/coding-agent/test/suite/regressions/7209-model-selector-filter-resets-selection.test.ts`（128 行）、`5217-compaction-reason.test.ts`（95 行）。

`AGENTS.md:33` 同样写死：`Put issue-specific regressions under packages/coding-agent/test/suite/regressions/ named <issue-number>-<short-slug>.test.ts`。

### 1.8 覆盖率：只有一处

全仓唯一配了 coverage 的是 `packages/agent/vitest.harness.config.ts:14-21`：

```ts
coverage: {
  provider: "v8",
  all: true,
  include: ["src/harness/**/*.ts", "src/agent.ts", "src/agent-loop.ts"],
  reporter: ["text", "html", "lcov"],
  reportsDirectory: "coverage/harness",
}
```

对应脚本 `packages/agent/package.json:27` `"test:harness": "vitest --run --config vitest.harness.config.ts"`。
**注意**：这个 config 不在 `npm test` 的默认路径上（默认是 `vitest --run`），也不在 CI 里。即 pi **没有覆盖率门禁**。

---

## 2. `packages/evals`：模型行为评测，不是单元测试

这是 pi 工程体系里第二个特别值得抄的东西，也是最容易被忽略的。

### 2.1 它是什么

`packages/evals/README.md:3-5`：

> Pi evals are behavioral, model-backed checks for Pi workflows. They adapt a real `AgentSession` to `vitest-evals`, run it in isolated temporary project and agent directories, and attach native Pi session artifacts.

关键词：**behavioral**（行为级，不是函数级）、**model-backed**（真调模型，花钱）、**real AgentSession**（不是 mock）。

包是 private 的（`packages/evals/package.json:4` `"private": true`），不发 npm。版本跟随 lockstep（`:3` `0.83.0`）。

### 2.2 体量

```
packages/evals/README.md                     153 行
packages/evals/src/pi-harness.ts             257 行   ← AgentSession → vitest-evals 适配层
packages/evals/src/extensions.eval.ts        140 行   ← 真正的评测用例
packages/evals/src/smoke.eval.ts              17 行
packages/evals/src/vitest-evals/summary.ts   438 行   ← 统计/lift 计算
packages/evals/src/vitest-evals/harness-table.ts 193 行
packages/evals/src/vitest-evals/artifacts.ts 113 行
packages/evals/src/vitest-evals/reporter.ts  111 行
packages/evals/src/vitest-evals/setup.ts       8 行
packages/evals/scripts/run-evals.mjs          97 行
                                    合计    1527 行
```

**只有 2 个 `.eval.ts` 文件**（`smoke` + `extensions`），但支撑它们的基础设施有 1000+ 行。这个比例本身就是结论：evals 的成本主要在 harness 和统计，不在用例。

### 2.3 怎么跑

```bash
npm run eval -- --provider openai --model gpt-5.6-sol      # README:12
PI_PROVIDER=openai PI_MODEL=gpt-5.6-sol npm run eval        # README:18
```

根 `package.json:29` 转发到 workspace：`"eval": "npm run eval --workspace=@earendil-works/pi-evals --"`，再到 `packages/evals/package.json` `"eval": "node scripts/run-evals.mjs"`。

`run-evals.mjs:9-15` 每次运行生成一个带时间戳 + UUID 的 artifact 目录：

```js
resolve(packageRoot, ".eval", `${new Date().toISOString().replaceAll(":", "-")}_${randomUUID()}`)
```

`run-evals.mjs:22-60` 解析 `--provider` / `--model`，**必须成对给**（`:53` `"CLI model selection requires both --provider and --model."`），其余参数原样转发 vitest。

vitest 配置（`packages/evals/vitest.config.ts:7-14`）关键差异：

```ts
fileParallelism: false,          // :9   评测串行跑，避免互相干扰
include: ["src/**/*.eval.ts"],   // :10  只收 .eval.ts
testTimeout: 120000,             // :11  2 分钟，因为真的在等模型
reporters: ["vitest-evals/reporter", "./src/vitest-evals/reporter.ts"],  // :14 双 reporter
```

### 2.4 怎么评：三种判据

**(a) 硬断言**（用于契约和 smoke）。`packages/evals/src/smoke.eval.ts:8-16` 全文：

```ts
it("runs a basic prompt end to end", async ({ run }) => {
  const result = await run("What's the capital of France? Respond with only the city name.");
  expect(result.output.trim()).toBe("Paris");
  expect(result.errors).toEqual([]);
  expect(result.usage.provider).toBe(process.env.PI_PROVIDER);
  expect(result.usage.model).toBe(process.env.PI_MODEL);
  expect(result.usage.totalTokens).toBeGreaterThan(0);
});
```

**(b) judge 打分**（确定性或模型打分）。README:114-117 的模式：

```ts
const TargetTaskJudge = createJudge<string, string>("TargetTaskJudge", ({ output }) => ({
  score: output === "expected result" ? 1 : 0,
}));
```

**(c) baseline vs candidate 的 lift 对比** —— 这是 pi evals 的核心方法论。

`README:136-138` 明确了纪律：

> Comparative suites should record correctness with deterministic or model-backed judges and set `judgeThreshold: null`. This keeps a low score as an observation instead of making the Vitest invocation fail. Use hard assertions only for suite invariants and infrastructure contracts.

即：**评测分数低不算测试失败**，只算一次观测。硬断言只用于基础设施契约。

统计口径（`README:144-150`，实现在 `packages/evals/src/vitest-evals/summary.ts`）：

- 分组 key = repetition + (`input.id` 或输入的 SHA-256 canonical JSON hash)（`harness-table.ts:110` `deriveEvalGroupKey`）
- 每个 candidate **只与声明的 baseline 比**
- pass 判定：单次运行的平均 judge score ≥ 1
- **lift = candidate pass rate − baseline pass rate，单位是百分点**（`summary.ts:35` `lift: number | null`）
- token / latency / cost 是**独立的 candidate−baseline 配对差值**，不混进 lift

多次重复由 `evalHarnessTable(...)`（`harness-table.ts:157`）配合 `describe.for(...)` 展开，`repetitions` 必须是正整数（`harness-table.ts:125-127` 会抛 `TypeError`）。README:123 的示例用 `repetitions: 6`。

### 2.5 隔离与产物

`pi-harness.ts:122` 每次 run 造临时根目录：`const root = await mkdtemp(join(tmpdir(), "pi-eval-"));`
`pi-harness.ts:229` 结束后 `await rm(root, { recursive: true, force: true })`，并且 cleanup 失败会和主错误一起包成 `AggregateError`（`:236`）。

删目录**之前**先把原生 session JSONL 快照下来（README:140-141），常量定义在 `packages/evals/src/vitest-evals/artifacts.ts:13`：

```ts
export const PI_SESSION_SNAPSHOT_ARTIFACT = "piSessionJsonl";
```

产物落到 `.eval/<timestamp>_<uuid>/`，`runs.jsonl` 索引所有 run，`sessions/` 存 JSONL 附件。README:33-34 明确警告这些文件含 prompt / 回复 / 源码 / 工具输出。

### 2.6 harness 的可配置维度

`packages/evals/src/pi-harness.ts:35-44`：

```ts
type PiCodingAgentHarnessOptions = {
  name?: string;
  model?: { provider: string; id: string };
  noTools?: CreateAgentSessionOptions["noTools"];
  transformSystemPrompt?: (defaultPrompt: string) => string;
};
```

加上 `output`（`:43`）把 `AgentSession` 投影成 JSON-safe 结果。`packages/evals/src/extensions.eval.ts:22-37` 的用法就是把 system prompt 是否含某段文字、扩展加载错误、扩展源码全都投影出来当断言对象：

```ts
systemPromptHasGuidelines: session.systemPrompt.includes("\nGuidelines:\n"),   // :28
systemPromptHasPiDocs: session.systemPrompt.includes("\nPi documentation (read only"),  // :29
extensionErrors: extensions.errors,                                            // :30
```

**这意味着 evals 可以直接评测 "换了 system prompt 之后 agent 会不会写对扩展"** —— 这正是自建 harness 最需要但最少人做的东西。

输入可以是单条 prompt，也可以是 prompt / reload 序列（`pi-harness.ts:28`）：

```ts
export type PiCodingAgentInput = string | Array<{ type: "prompt"; content: string } | { type: "reload" }>;
```

`reload` 用于「上一条 prompt 刚创建了扩展，需要重启 session 才能用」的场景（README:76-85）。

---

## 3. CI：10 条流水线

`ls .github/workflows | wc -l` = **10**，共 **1885 行 YAML**。

| 文件 | 行数 | 触发 | 干什么 |
|---|---|---|---|
| `ci.yml` | 42 | push main / PR to main | 主干门禁：build → check → test |
| `pr-gate.yml` | 128 | `pull_request_target` opened | **未授权贡献者的 PR 自动关闭** |
| `issue-gate.yml` | 129 | issue opened | 未授权贡献者的 issue 自动关闭 |
| `approve-contributor.yml` | 223 | issue_comment created | 维护者回 `lgtm`/`lgtmi` → 写入 `.github/APPROVED_CONTRIBUTORS` 并 push |
| `issue-triage-labels.yml` | 142 | issue reopened/labeled | 三态标签维护 |
| `remove-inprogress-on-close.yml` | 31 | issue closed | 摘掉 `inprogress` 标签 |
| `issue-analysis.yml` | 688 | issue（带触发标签） | **用 pi 自己分析 issue**（见 3.4） |
| `build-binaries.yml` | 325 | push tag `v*` / dispatch | 发布：构建二进制 → 草稿 Release → 发 npm → 公开 Release |
| `npm-audit.yml` | 31 | 每天 cron `37 7 * * *` | `npm audit --omit=dev --audit-level=moderate` + `npm audit signatures` |
| `publish-model-catalog.yml` | 146 | workflow_run / PR / cron `17 8-13 * * 1-5` | 生成 + 校验 + 发布模型目录 JSON |

### 3.1 `ci.yml`（42 行，全文可上 PPT）

只有一个 job `build-check-test`（`:14`），5 步：

```yaml
- run: npm ci --ignore-scripts     # :33  ← 注意 --ignore-scripts
- run: npm run build               # :36
- run: npm run check               # :39
- run: npm test                    # :42
```

前置装系统依赖（`:26-30`）：cairo/pango/jpeg/gif/rsvg（给 canvas 用）+ `fd-find` + `ripgrep`，并把 `fdfind` 软链成 `fd`。**说明 pi 的工具层真的依赖 `rg` 和 `fd` 二进制**。

并发控制（`:9-11`）：`group: ci-${{ github.ref }}` + `cancel-in-progress: true`。

**CI 里没有 lint 单独步骤** —— lint 被 `npm run check` 吞了（见第 4 节）。**CI 里也没有 evals** —— 评测要花钱，不进 CI。

### 3.2 供应链纪律：Action 全部 SHA 钉死

```bash
$ grep -rh "uses: " .github/workflows/ | sort -u
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4.3.0
uses: actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3 # v9.0.0
uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
uses: oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6 # v2.2.0

$ grep -rh "uses: " .github/workflows/ | grep -v "@[0-9a-f]\{40\}" | sort -u
（无输出）
```

**34 处 `uses:`、6 个不同 action、0 个用 tag/branch 引用**。全部 40 位 commit SHA + 注释标版本号。

`build-binaries.yml:18` 还有 `permissions: {}`（默认零权限），每个 job 再单独声明最小权限：`build` 只有 `contents: read`（`:29-30`），`publish-npm` 是 `contents: read` + `id-token: write`（`:73-74`）。

### 3.3 贡献者门禁（`pr-gate.yml`，128 行）

逻辑（`pr-gate.yml:19-128`）：

1. 白名单 bot 直接放行：`dependabot[bot]`、`sentry[bot]`、`claude[bot]`（`:21`）
2. 有仓库 `admin`/`maintain`/`write` 权限 → 放行（`:102`）
3. 否则读 `.github/APPROVED_CONTRIBUTORS`（`:19`, `:107`），每行 `<username> <capability>`，capability ∈ `{issue, pr}`（`:20`, `:66-79`）
4. capability === `'pr'` → 放行（`:111`）
5. 否则**评论 + 关闭 PR**（`:85-98`, `:128`）

`.github/APPROVED_CONTRIBUTORS` 实测 **325 行**。

关闭时的评论文案（`:119-125`）自带引导：开 issue → 求维护者回 `lgtm`。`lgtmi` 只解锁 issue，`lgtm` 解锁 issue + PR。命令必须在回复开头（可跟在 `@mention` 后）或结尾。

### 3.4 `issue-analysis.yml`（688 行）：用 pi 分析 pi 的 issue

这是全仓最长的 workflow。结构：

- `authorize` job（`:65`）：`Verify sender permission`（`:74`）
- `analyze` job（`:254`）：
  - 造高熵工作目录名（`:267`，防路径猜测）
  - 三平台装系统依赖：Linux `:287` / macOS `:294` / Windows `:304`
  - 写 `auth.json`（`:332`）—— 来自 `PI_AUTH_JSON` secret（文件头注释 `:14` 说明）
  - **`Run pi /is`**（`:355`）—— 跑 pi 自己的 `/is` 斜杠命令做 issue 分析；失败抛 `pi /is failed with exit code ${exitCode}`（`:415`）
  - 刷新后的 `auth.json` 持久化回去（`:418`）
  - 导出 session 文件（`:487`）→ 上传成 gist（`:539`）
  - 评论出 session 导入指令（`:571`），正文里给的命令是 `pi "/ir ${gistId}"`（`:632`）
  - 失败时评论（`:650`）+ 摘掉触发标签（`:674`）

> **这条可以直接上 PPT**：pi 用 pi 来分析自己的 issue，产物是一个可以 `pi "/ir <gist>"` 重放的完整 session。这就是"agent 自举"的具体样子。

### 3.5 发布流水线 `build-binaries.yml`（325 行）

4 个 job，顺序严格：

```
build → stage-github-release → publish-npm → publish-github-release
                     └──────────────────────────────┘
                              cleanup（失败时删草稿 Release）
```

设计要点（注释写在 `:25-26`）：

> Keep the public GitHub Release publication last. Binary assets are staged in a draft release first; cleanup removes the draft if later publishing fails.

- `build`（`:27`）：Bun + Node 双运行时（`:41` `oven-sh/setup-bun`，`:46` `setup-node`）→ hydrate 模型数据（`:52-53`）→ 造 source archive（`:55`）→ **从 source archive 构建二进制**（`:66`，而不是从工作区，保证可复现）→ 上传 artifact，保留 14 天（`:124-129`）
- `stage-github-release`（`:131`）：下载 artifact → **校验资产清单严格一致**（`:147`，不一致就 `diff -u` 打出来并 `exit 1`）→ 创建草稿 Release
- `publish-npm`（`:224`）：`environment: npm-publish` + `id-token: write`（`:71-74`）→ 重新 `npm ci --ignore-scripts` / build / check / **test**（`:254-263`，发布前再跑一遍全量）→ 升级 npm 到 `11.16.0`（`:265-268`）→ `node scripts/publish.mjs`（`:271`）
- `publish-github-release`（`:274`）：`gh release edit --draft=false`；如果 Release 已经不是草稿会直接报错退出（`:127-130` 区段）
- `cleanup`（`:303`）：`if: always() && ...`（`:309`）任一环节失败就删掉草稿 Release

`concurrency`（`:20-22`）：`cancel-in-progress: false` —— 发布流程**不允许被取消**。

`AGENTS.md:156` 对应说明：

> The `publish-npm` job uses npm trusted publishing through GitHub Actions OIDC with environment `npm-publish`; no local `npm publish`, `npm whoami`, OTP, or WebAuthn flow is required.

### 3.6 `npm-audit.yml`（31 行）

每天 07:37 UTC 跑（`:5` `cron: '37 7 * * *'`），两步：

```yaml
- run: npm ci --ignore-scripts --no-audit --no-fund      # :25
- run: npm audit --omit=dev --audit-level=moderate       # :28
- run: npm audit signatures --omit=dev                   # :31
```

`npm audit signatures` 是验证 registry 签名（防包被篡改），比单纯 audit 少见。

---

## 4. 代码规范

### 4.1 Biome 一把梭（没有 ESLint / Prettier）

`biome.json` 全文 41 行，版本钉在 `2.3.5`（`package.json:53`）。

**formatter**（`biome.json:19-25`）：

| 项 | 值 | 行号 |
|---|---|---|
| `indentStyle` | `tab` | `:22` |
| `indentWidth` | `3` | `:23` |
| `lineWidth` | `120` | `:24` |
| `formatWithErrors` | `false` | `:21` |

> **`indentWidth: 3` 是个很罕见的选择**（tab 宽度按 3 个字符渲染）。可以当彩蛋讲。

**linter**（`biome.json:3-18`）：`recommended: true`，然后**关掉 6 条**：

| 规则 | 状态 | 行号 |
|---|---|---|
| `style/noNonNullAssertion` | off | `:8` |
| `style/useConst` | **error**（升级） | `:9` |
| `style/useNodejsImportProtocol` | off | `:10` |
| `suspicious/noExplicitAny` | off | `:13` |
| `suspicious/noControlCharactersInRegex` | off | `:14` |
| `suspicious/noEmptyInterface` | off | `:15` |

注意矛盾点：Biome 层面 `noExplicitAny` 是 off，但 `AGENTS.md:15` 写 **"No `any` unless absolutely necessary"** —— 即 **any 靠人（和 AI）的自律，不靠 linter**。这是个有意思的取舍：linter 不报，review 会说。

**扫描范围**（`biome.json:26-40`）：只管 `packages/*/src`、`packages/*/test`、`packages/storage/*/{src,test}`、`packages/coding-agent/examples`；排除 `node_modules`、`test-sessions.ts`、`models.generated.ts`、`*.models.ts`。

### 4.2 `npm run check`：一条命令 = 7 个子检查

`package.json:18`：

```
biome check --write --error-on-warnings .
  && npm run check:pinned-deps
  && npm run check:ts-imports
  && npm run check:shrinkwrap
  && npm run check:install-lock:coding-agent
  && tsgo --noEmit
  && npm run check:browser-smoke
```

逐个拆：

| # | 命令 | 实现 | 行数 | 检查什么 |
|---|---|---|---|---|
| 1 | `biome check --write --error-on-warnings .` | Biome 2.3.5 | — | 格式 + lint，**warning 也当 error**，且 `--write` 直接改文件 |
| 2 | `check:pinned-deps` | `scripts/check-pinned-deps.mjs` | 63 | 所有外部直接依赖必须精确版本 |
| 3 | `check:ts-imports` | `scripts/check-ts-relative-imports.mjs` | 74 | 禁止 `.ts` 文件里出现相对 `.js` 导入 |
| 4 | `check:shrinkwrap` | `scripts/generate-coding-agent-shrinkwrap.mjs --check` | 365 | shrinkwrap 与 lockfile 一致 + 生命周期脚本白名单 |
| 5 | `check:install-lock:coding-agent` | `scripts/generate-coding-agent-install-lock.mjs --check` | 439 | 安装锁一致性 |
| 6 | `tsgo --noEmit` | `@typescript/native-preview` | — | 全仓类型检查（用的是 TS 原生 Go 实现的预览版） |
| 7 | `check:browser-smoke` | `scripts/check-browser-smoke.mjs` | 128 | esbuild 打浏览器包 + tree-shake 冒烟 |

`AGENTS.md:28` 的用法规定：

> After code changes (not docs): `npm run check` (full output, no tail). Fix all errors, warnings, and infos before committing. **Does not run tests.**

**"no tail"** 这条很有意思 —— 明确禁止 agent 用 `| tail` 截输出来假装通过。

#### 4.2.1 `check-pinned-deps.mjs`（63 行）

递归收集所有 `package.json`（`:9-22`，跳过 `.git`/`dist`/`node_modules`），对 `dependencies`/`devDependencies`/`optionalDependencies`（`:4`）逐条查：

- 跳过内部包（前缀 `@earendil-works/pi-`，`:24-26`）
- 跳过非 registry specifier（`workspace:`/`file:`/`link:`/`git+`/`https:` 等，`:28-30`）
- `npm:` 别名要剥壳后再查版本（`:32-38`）
- 剩下的必须匹配 `^\d+\.\d+\.\d+(-pre)?(\+meta)?$`（`:5`）

失败信息（`:54`）：`${file}: ${section}.${name} must be pinned, found ${specifier}`。

实证：`package.json:52-61` 的 devDeps 全是精确版本，没有一个 `^` 或 `~`。

#### 4.2.2 `check-ts-relative-imports.mjs`（74 行）

用 TypeScript compiler API 解析 AST（`:3` `import ts from "typescript"`），检查 4 种导入形态（`:47-62`）：`import` 声明、`export ... from`、动态 `import()`、`import("x").Type` 类型导入。

命中条件（`:23-25`）：相对路径（`^\.\.?/`）且以 `.js` 结尾。
报错（`:71`）：`Relative .js imports are not allowed in non-declaration .ts files:`

**为什么**：pi 用 Node 的 TypeScript strip-only 模式直跑 `.ts`，所以导入要写 `.ts` 后缀而不是传统的 `.js`。对应 `AGENTS.md:20` 的 erasable-syntax 规定。仓库里甚至有一个迁移脚本 `scripts/update-source-imports-to-ts.sh`。

### 4.3 pre-commit（husky，45 行）

`package.json:49` `"prepare": "husky"` + `package.json:57` `husky@9.1.7`。只有一个 hook：`.husky/pre-commit`。

流程（`.husky/pre-commit:4-45`）：

1. 记下当前 staged 文件列表（`:4`）
2. **`node scripts/check-lockfile-commit.mjs`**（`:6`）—— 失败直接退出
3. `npm run check`（`:13`）—— 上面那 7 项全跑
4. 如果 staged 文件命中 `packages/ai/*`、`packages/web-ui/*`、`package.json`、`package-lock.json`（`:22`），额外跑 `npm run check:browser-smoke`（`:31`）
5. **把被 `biome --write` 改过的文件重新 `git add`**（`:39-43`）—— 因为 check 会自动改格式

第 5 步是个细节：因为 `biome check --write` 会改文件，如果不 restage，提交进去的就是没格式化的版本。

#### `check-lockfile-commit.mjs`（120 行）

`:5-6`：读 `PI_ALLOW_LOCKFILE_CHANGE`，接受 `1`/`true`/`yes`。
`:34-35`：对比 `git show HEAD:package-lock.json` 和 `git show :package-lock.json`（暂存区），diff 出包级变更。

即：**默认禁止提交 lockfile 变更**，除非显式设 `PI_ALLOW_LOCKFILE_CHANGE=1`。对应 `AGENTS.md:43`。

### 4.4 `AGENTS.md`（162 行）：硬规矩逐条摘

这份文件是给**AI agent 看的开发规范**（`CONTRIBUTING.md:19` 明说：「If you use an agent, run it from the `pi` root directory so it picks up `AGENTS.md` automatically」）。共 11 节。

**对话风格**（`:3-10`）
- `:5` 答案短、精炼
- `:6` **commit / issue / PR 评论 / 代码里禁用 emoji**
- `:7` 不要客套废话（例："Thanks @user" 而非 "Thanks so much @user!"）
- `:8` 只用技术性散文，直接
- `:9` 用户提问时，**先回答问题，再动手改代码或跑命令**
- `:10` 回应反馈/分析时，**先明确说同意还是不同意**，再说改了什么

**代码质量**（`:12-24`）
- `:14` 大范围改动前、编辑未通读的文件前、被要求审计时，**必须完整读文件**，不许只看 grep 片段
- `:15` 非必要不用 `any`
- `:16` 只有一处调用点的单行 helper 要内联掉
- `:17` 外部 API 类型去 `node_modules` 里查，**不许猜**
- `:18` **禁止内联 import**（`await import()`、`import("pkg").Type`、动态类型导入），只准顶层 import
- `:19` 不许为了修「过时依赖引发的类型错误」而删代码或降级代码 —— **升级依赖**
- `:20` 根配置覆盖的目录只准用 erasable TypeScript 语法（Node strip-only）：**不准用参数属性、`enum`、`namespace`/`module`、`import =`、`export =`**
- `:21` 删功能或删看起来是有意为之的代码前**必须先问**
- `:22` **不做向后兼容**，除非用户明确要求
- `:23` 不许硬编码按键判断（如 `matchesKey(keyData, "ctrl+x")`），要加进 `DEFAULT_EDITOR_KEYBINDINGS` / `DEFAULT_APP_KEYBINDINGS`
- `:24` 不许手改 `models.generated.ts`

**命令**（`:26-35`）
- `:28` 改代码后跑 `npm run check`，**完整输出不许 tail**；error/warning/info 全部修完才提交；它不跑测试
- `:29` **不许主动跑 `npm run build` 或 `npm test`**，除非用户要求
- `:30` **绝不直接跑完整 vitest**，用 `./test.sh`；单测用 `node ../../node_modules/vitest/dist/cli.js --run test/specific.test.ts`
- `:31` 新建或改了测试文件，**必须跑到通过为止**
- `:32` `test/suite/` 用 `harness.ts` + faux provider，**不许真 API / key / 付费 token**
- `:33` issue 回归测试放 `regressions/`，命名 `<issue-number>-<short-slug>.test.ts`
- `:34` 临时脚本**写到 `/tmp` 文件里再跑**，不许在 `bash` 命令里塞多行脚本
- `:35` **除非用户要求，绝不 commit**

**依赖与安装安全**（`:37-43`）
- `:39` **依赖和 lockfile 变更视同被 review 的代码**；外部直接依赖钉死精确版本
- `:40` 本地用 `npm install --ignore-scripts`，CI 用 `npm ci --ignore-scripts`；**不许跑生命周期脚本**
- `:41` 依赖元数据变了用 `npm install --package-lock-only --ignore-scripts` 刷 lockfile
- `:42` shrinkwrap 需重生成时跑 `generate-coding-agent-shrinkwrap.mjs`；**带生命周期脚本的新依赖必须 review 并显式加白名单，绝不许静默添加**
- `:43` pre-commit 阻止提交 lockfile，除非 `PI_ALLOW_LOCKFILE_CHANGE=1`

**Git**（`:45-65`）—— 这一节的前提写得很清楚（`:47`）：**同一个 cwd 里可能同时跑着多个 pi session**，各改各的文件。

- `:51` **只提交你这个 session 改的文件**
- `:52` **显式列路径 `git add <path1> <path2>`，永不 `git add -A` / `git add .`**
- `:53` 提交前跑 `git status` 确认只 stage 了自己的文件
- `:54` `models.generated.ts` 永远可以捎带
- `:55` 消息格式：`{feat,fix,docs}[(ai,tui,agent,coding-agent)]: <message>`
- `:57-59` **绝不许跑**：`git reset --hard`、`git checkout .`、`git clean -fd`、`git stash`、`git add -A`、`git add .`、`git commit --no-verify`
- `:63` rebase 冲突只解自己改过的文件
- `:64` 冲突在没改过的文件里 → **中止并问用户**
- `:65` **绝不 force push**

**Issue / PR**（`:67-89`）
- `:73` review PR 时**不许 `gh pr checkout` / `git switch`** 挪工作区（除非明确要求）
- `:74` 用 `gh pr view/diff`、`gh api`、`git show` 对 fetch 到的 ref 操作
- `:79` 建 issue 要打 `pkg:*` 标签
- `:83` 评论**写到临时文件用 `--body-file` 发**，不许多行 markdown 走 `--body`
- `:85` **每条 AI 发的评论必须以 AI 生成免责声明结尾**（例："This comment is AI-generated by `/wr`"）
- `:89` 用 commit 关 issue 要**每个 issue 各写一次关键字**（`closes #1, closes #2`），共享关键字只会关第一个

**tmux 测 TUI**（`:91-102`）：给了完整可复制的 6 行脚本，用 80x24 的 tmux session 跑 `./pi-test.sh`，`capture-pane -p` 抓屏。

**Changelog**（`:104-118`）
- `:106` 每个包一份 `packages/*/CHANGELOG.md`
- `:108` `[Unreleased]` 下固定 5 个小节：`Breaking Changes` / `Added` / `Changed` / `Fixed` / `Removed`
- `:112` 新条目只进 `[Unreleased]`；**先读完整节再追加，不许重复建小节**
- `:113` **已发布版本的小节不可变**
- `:117-118` 内部改动挂 issue 链接；外部贡献挂 PR 链接 + `by [@username]`

**用户覆盖**（`:160-162`）：用户指令和本文件冲突时，**必须先要显式确认**再执行。

### 4.5 `CONTRIBUTING.md`（102 行）：给人看的

**哲学**（`:5-11`）：

> `:7` First things first: **pi's core is minimal**.
> `:9` If your feature does not belong in the core, it should be an extension. PRs that bloat the core will likely be rejected.

**唯一一条规则**（`:13-19`）：

> `:15` **You must understand your code.** If you cannot explain what your changes do and how they interact with the rest of the system, your PR will be closed.
> `:17` Using AI to write code is fine. Submitting AI-generated slop without understanding it is not.

**贡献门禁**（`:21-34`）：

- `:23` 新贡献者的 issue 和 PR **默认全部自动关闭**
- `:25` 周五到周日提交的 issue 不保证被 review
- `:31-32` `lgtmi` = 以后 issue 不被自动关；`lgtm` = issue + PR 都不被自动关
- `:34` 命令必须在回复开头或结尾

**issue 质量线**（`:36-48`）：

- `:38` 必须用两个 issue 模板之一（实测 `.github/ISSUE_TEMPLATE/` 下 `bug.yml` 45 行、`contribution.yml` 36 行、`package-report.yml` 49 行、`config.yml` 5 行）
- `:42` **一屏放不下就是太长**
- `:43` **用你自己的话写（不要用 LLM 生成正文；非要用就补一条明确标注 AI 的评论）**

**封禁**（`:50-54`）：

- `:52` 无视本文档两次，或用 agent 刷 issue → **永久封 GitHub 账号**
- `:54` 自动化大批量发 issue → 永久封号。原文："No taksies backsies."

**提 PR 前**（`:56-71`）：

```bash
npm run check
./test.sh
```
`:67` 两条都必须过。`:69` **不许改 `CHANGELOG.md`**，changelog 由维护者写。

---

## 5. 文档体量实测

### 5.1 `packages/coding-agent/docs/*.md`

**30 个文件，12113 行。**

| 排名 | 文件 | 行数 |
|---|---|---|
| 1 | `extensions.md` | **2984** |
| 2 | `rpc.md` | **1576** |
| 3 | `sdk.md` | **1186** |
| 4 | `tui.md` | 942 |
| 5 | `custom-provider.md` | 773 |
| 6 | `models.md` | 545 |
| 7 | `session-format.md` | 438 |
| 8 | `compaction.md` | 401 |
| 9 | `settings.md` | 321 |
| 10 | `providers.md` | 309 |
| 11 | `usage.md` | 303 |
| 12 | `themes.md` | 299 |
| 13 | `skills.md` | 231 |
| 14 | `packages.md` | 228 |
| 15 | `keybindings.md` | 211 |
| 16 | `quickstart.md` | 165 |
| 17 | `sessions.md` | 145 |
| 18 | `terminal-setup.md` | 142 |
| 19 | `termux.md` | 127 |
| 20 | `containerization.md` | 111 |
| 21 | `llama-cpp.md` | 99 |
| 22 | `prompt-templates.md` | 96 |
| 23 | `environment-variables.md` | 88 |
| 24 | `json.md` | 86 |
| 25 | `index.md` | 84 |
| 26 | `development.md` | 71 |
| 27 | `tmux.md` | 63 |
| 28 | `security.md` | 59 |
| 29 | `windows.md` | 17 |
| 30 | `shell-aliases.md` | 13 |

**分布特征**：前 3 篇（`extensions` + `rpc` + `sdk`）= 5746 行 = **总量的 47%**。这三篇都是**给二次开发者看的接口文档**，不是给终端用户的。

> **这条可上 PPT**：pi 的文档投入里，接近一半是在给"别人扩展我"写说明书。这是"可扩展 core"这个哲学（`CONTRIBUTING.md:7-11`）在文档层面的对应物。

`quickstart.md` 只有 165 行，`index.md` 84 行 —— **入门文档极短**。

### 5.2 全仓 markdown

```bash
$ find packages -path '*/node_modules' -prune -o -name '*.md' -print | wc -l
86
```

各包 README：

| 文件 | 行数 |
|---|---|
| `packages/ai/README.md` | **1662** |
| `packages/tui/README.md` | 854 |
| `packages/coding-agent/README.md` | 708 |
| `packages/agent/README.md` | 507 |
| `packages/evals/README.md` | 153 |
| `README.md`（根） | 113 |
| `packages/protocol/README.md` | 68 |
| `packages/client/README.md` | 64 |
| `packages/server/README.md` | 57 |
| **合计** | **4186** |

根 README 只有 113 行 —— 门面短，深度在包里。

加上根级治理文档：`AGENTS.md` 162 + `CONTRIBUTING.md` 102 + `SECURITY.md` 87。

### 5.3 `SECURITY.md`（87 行）：值得单独提

信任边界写得非常直白（`:11-17`）：

> Pi treats the local user account and files writable by that account as inside the same trust boundary as the Pi process itself. ... Reports that depend on such prior local write access are not security vulnerabilities unless they demonstrate how Pi grants that write access or crosses an operating-system privilege boundary.

以及关于 prompt injection 的态度（`:19-22`）：

> files like `AGENTS.md` or instructions in comments can be used to prompt inject the coding agent trivially and **this cannot be protected against**.

即 **pi 官方明确宣布：prompt injection 不在威胁模型内，靠用户只在可信仓库里跑 pi**。这是一条很有争议但很诚实的边界声明，做分享时值得对比其他 agent 的做法。

---

## 6. 发布流程

### 6.1 lockstep 版本：所有包一个号

`AGENTS.md:122`：

> **Lockstep versioning**: all packages share one version; every release updates all together. `patch` = fixes + additions, `minor` = breaking changes. **No major releases.**

注意这个语义**故意偏离 semver**：破坏性变更走 minor，永不发 major。

实现在 `scripts/sync-versions.js`（78 行）：

1. `:15-20` 找出所有 workspace 包（排除生成的 `coding-agent/install-lock`，`:12`）
2. `:21` 过滤出非 private 的包
3. `:29-37` **如果这些包版本不全一样 → 报错退出**：
   ```
   ERROR: Not all non-private packages have the same version.
   Expected lockstep versioning. Run one of: npm run version:patch / minor / major
   ```
4. `:43-68` 把所有包里指向内部包的依赖 specifier 改写成 `^${version}`
5. `:51-52` 有一条注释解释了为什么跳过 `npm:` 别名：
   > Registry aliases such as `npm:@earendil-works/pi-ai@0.1.2` are never workspace-linked, so lockstep bumping them would point at a version that is not published yet.

组合命令（`package.json:35`）：

```
"version:patch": "npm version patch -ws --no-git-tag-version
                  && node scripts/sync-versions.js
                  && npm install --package-lock-only --ignore-scripts"
```

这个脚本**自己有测试**：`scripts/sync-versions.test.mjs`（75 行），由根 `test:scripts` 跑。

### 6.2 发哪些包：7 个

`scripts/publish.mjs:7-15`（全文可上 PPT）：

```js
const packages = [
  { directory: "packages/ai",                  name: "@earendil-works/pi-ai" },
  { directory: "packages/agent",               name: "@earendil-works/pi-agent-core" },
  { directory: "packages/protocol",            name: "@earendil-works/pi-protocol" },
  { directory: "packages/client",              name: "@earendil-works/pi-client" },
  { directory: "packages/storage/sqlite-node", name: "@earendil-works/pi-storage-sqlite-node" },
  { directory: "packages/tui",                 name: "@earendil-works/pi-tui" },
  { directory: "packages/coding-agent",        name: "@earendil-works/pi-coding-agent" },
];
```

**`packages/server` 和 `packages/evals` 不发**（evals 是 `private: true`，见 `packages/evals/package.json:4`）。

`publish.mjs` 只有 128 行，关键行为：

- `:51` dist 不存在直接抛错：`${directory}/dist does not exist. Run npm run build before publishing.`
- `:56` 用 `npm pack --dry-run --ignore-scripts --json` 先验证包内容
- `:103-108` 先查 npm 上是否已有该版本；已发布的**只验证内容不重发**（`:121-122` `Skipping ...: already published`）—— **幂等**
- `:126` 真发布：`npm publish --access public --provenance --ignore-scripts`

`--provenance` = npm 供应链溯源证明（配合 3.5 节的 OIDC trusted publishing）。

`package.json:39-40`：

```
"prepublishOnly": "npm run clean && npm run build && npm run check",
"publish": "npm run prepublishOnly && node scripts/publish.mjs",
```

### 6.3 `scripts/release.mjs`（247 行）：一条命令发一个版本

`package.json:45-47`：`release:patch` / `release:minor` / `release:major` → `node scripts/release.mjs <bump>`。

主流程（`release.mjs:181-247`，逐步骤有行号）：

| 步骤 | 行号 | 动作 |
|---|---|---|
| 0 | `:184-191` | `git status --porcelain` —— **工作区不干净直接退出** |
| 1 | `:194` | `bumpOrSetVersion()` → 跑 `npm run version:${target}`（`:116`） |
| 2 | `:198-199` | 更新所有 `CHANGELOG.md` 的 `[Unreleased]` → `[X.Y.Z]` |
| 3 | `:203-207` | 重生成发布产物：`generate:models` → `check:model-data` → `shrinkwrap:coding-agent` → `install-lock:coding-agent` |
| 4 | `:211-212` | `npm run check` |
| 5 | `:215-216` | `npm run build:offline` |
| 6 | `:219-220` | **`./test.sh`** —— 发布前跑全量隔离测试 |
| 7 | `:224-227` | `git commit -m "Release v${version}"` + `git tag v${version}` |
| 8 | `:231-233` | `addUnreleasedSection()` 给每个 changelog 加回新的 `[Unreleased]` |
| 9 | `:236-238` | `git commit -m "Add [Unreleased] section for next cycle"` |
| 10 | `:242-244` | `git push origin main` + `git push origin v${version}` |
| — | `:247` | 打印 `=== Prepared release v${version}; CI publishing starts after the tag push ===` |

即 **本地脚本只负责到 push tag 为止，npm 发布完全交给 CI**（3.5 节）。

有两个细节值得注意：

- `:71-97` `removeStaleWorkspaceLockEntries()` —— 清理 lockfile 里过期的 workspace 条目
- `:101-108` `stageChangedFiles()` 用 `git ls-files -m -o -d --exclude-standard` 显式列路径再 `git add --`，**没用 `git add -A`**（呼应 `AGENTS.md:52`）

### 6.4 发布前的人工闸门

`AGENTS.md:124-158` 给出 5 步流程，其中第 2 步（`:126-145`）是**必须人工做的本地冒烟测试**：

```bash
npm run release:local -- --out /tmp/pi-local-release --force
cd /tmp
/tmp/pi-local-release/node/pi --help / --version / --list-models / -p "Say exactly: ok" / （裸跑进交互）
/tmp/pi-local-release/bun/pi   --help / --version / --list-models / -p "Say exactly: ok" / （裸跑进交互）
```

`AGENTS.md:145` 要求：**交互模式必须在 tmux 里跑，提交一条 prompt 并等到模型回复才算通过。失败是发布阻塞项，除非用户明确接受风险。**

对应脚本 `scripts/local-release.mjs`（291 行），root `package.json:44` `"release:local"`。

第 3 步（`:149-152`）的命令带两个环境变量：

```bash
PI_ALLOW_LOCKFILE_CHANGE=1 npm_config_min_release_age=0 npm run release:patch
```

`:152` 解释了 `npm_config_min_release_age=0` 的原因：仓库平时有 npm 包龄闸门（新发布的包不允许马上被依赖），发布时会挡住 lockfile 刷新。

第 5 步（`:158`）：**publish 失败不许重跑 release 脚本**，因为 `publish.mjs` 幂等，直接重跑 tag workflow 即可。

### 6.5 依赖锁的三层结构

pi 对 `coding-agent`（唯一被终端用户 `npm i -g` 的包）做了三层锁：

| 层 | 文件 / 脚本 | 行数 | 作用 |
|---|---|---|---|
| 1 | `package-lock.json`（根） | — | 开发时的 workspace 锁 |
| 2 | `packages/coding-agent/npm-shrinkwrap.json`（由 `scripts/generate-coding-agent-shrinkwrap.mjs` 生成） | 365 | **随包发布的锁**，保证用户装到的传递依赖版本和 CI 一致 |
| 3 | `packages/coding-agent/install-lock/`（由 `scripts/generate-coding-agent-install-lock.mjs` 生成） | 439 | 安装期校验 |

两个生成脚本都支持 `--check` 模式（`generate-coding-agent-install-lock.mjs:22` `const checkOnly = args.has("--check")`），被 `npm run check` 调用（`package.json:21-22`）。

**生命周期脚本白名单**（`generate-coding-agent-install-lock.mjs:16-19`）：

```js
const allowedInstallScriptPackages = new Map([
  ["@google/genai@1.52.0", "preinstall is a no-op in the published package"],
  ["protobufjs@7.6.5",     "postinstall only warns about protobufjs version scheme mismatches"],
]);
```

**整个依赖树只有 2 个包被允许带安装脚本，而且每条都写了理由。** shrinkwrap 脚本里有同样的机制（`generate-coding-agent-shrinkwrap.mjs:13`），并且双向校验（`:250` 未在白名单里的会报错；`:257-259` 白名单里已不存在的包也会报错要求删掉）：

```
${lockPath} has install scripts (${packageId}). Review it and add it to allowedInstallScriptPackages if intentional.
allowed install-script package ${packageId} is no longer present; remove it from the allowlist
```

---

## 7. 【核心】一个人要自建 agent harness，从 pi 能抄走的 12 条

> 评级说明：
> **低** = 半天内可落地，基本是复制一个文件 / 一段配置；
> **中** = 1–3 天，需要按自己项目改造；
> **高** = 一周以上，或需要持续投入（花钱 / 花时间维护）。

---

### 抄 1｜把「假 LLM」做成一个正式 provider，而不是测试里的 mock

**证据**：`packages/ai/src/providers/faux.ts`（541 行）；注册入口 `packages/ai/src/compat.ts:160`；便捷构造 `faux.ts:49/53/57/73`；核心 API `faux.ts:501` `setResponses(responses: FauxResponseStep[])`；使用现场 `packages/coding-agent/test/suite/harness.ts:103-106`。

**为什么这是第一条**：agent 的绝大部分 bug 不在 LLM 里，在**你自己的循环、工具执行、状态机、压缩、恢复**里。只要能把 LLM 的输出序列写死，这些全部可以确定性测试。pi 把它做成 provider 而不是 mock，意味着**它走的是和真 provider 完全相同的代码路径**（registry、auth、stream 事件），mock 掉的只有网络那一层。

`packages/coding-agent/test/suite/harness.ts:117` 甚至给它配了个假 key `"faux-key"` 走完整的 auth storage 流程。

**抄的成本：中**。核心不难（一个吐预设 stream 事件的 provider），难在你的 provider 抽象要先足够干净才能塞得进去。反过来说：**如果你塞不进去，说明你的 provider 抽象有问题**，这本身就是信息。

---

### 抄 2｜`test.sh`：用 `env -i` 造一个空环境跑测试

**证据**：`test.sh`（79 行），关键 `test.sh:79` `env -i "${test_env[@]}" npm test`；白名单 `:40-64`；假 HOME `:7,11`；git 全禁 `:53-56`；带归属验证的清理 `:20-33`。规矩在 `AGENTS.md:30`（"Never run the full vitest suite directly"）和 `CONTRIBUTING.md:64`。

**解决什么**：agent 测试最容易"在我机器上过"的原因是它读了你的 `~/.config`、你的 git 全局配置、你的 API key、你的 shell 环境。`env -i` 一刀切断。

而且这条同时解决了一个 agent 特有的问题：**agent 会真的跑 git 命令**。`GIT_CONFIG_GLOBAL=/dev/null` + `GIT_TERMINAL_PROMPT=0` + `GIT_ASKPASS=false` + `GIT_EDITOR=true`（`:53-56`）保证测试里的 git 不会弹交互、不会读你的 user.name、不会去 push。

**抄的成本：低**。79 行 bash，改改变量名基本能直接用。**投入产出比全场最高的一条。**

---

### 抄 3｜真实 provider 测试用 `describe.skipIf(!process.env.X_API_KEY)` 自动降级

**证据**：`packages/ai/test/abort.test.ts:101-276` 连续 15+ 个 `describe.skipIf`，覆盖 Gemini / OpenAI Completions / OpenAI Responses / Azure / Anthropic / Mistral / Together / MiniMax / Xiaomi（4 个区）/ Qwen（2 个区）/ Kimi；全仓 `packages/ai/test` + `packages/agent/test` 共 **372 处 `skipIf`**。

**为什么**：agent 项目必然要接多个 provider，但没人有全部 provider 的 key。`skipIf` 让**同一份测试文件既是 CI 上的空跑、也是有 key 的人的真实 e2e**。不需要维护两套。

配合抄 2：`test.sh` 不注入任何 key，所以 `./test.sh` 天然只跑非 e2e 部分。**两条组合起来才完整。**

**抄的成本：低**。一行 `skipIf` 的事。

---

### 抄 4｜回归测试按 issue 号命名，单独放一个目录

**证据**：`packages/coding-agent/test/suite/regressions/`，实测 **44 个文件**；命名规则写死在两处：`AGENTS.md:33` 和 `packages/coding-agent/test/suite/README.md:14-15`（`<issue-number>-<short-slug>.test.ts`）。实例：`regressions/7209-model-selector-filter-resets-selection.test.ts`、`regressions/5217-compaction-reason.test.ts`。

**为什么对 agent 项目特别重要**：agent 的 bug 大量是「某个模型在某个特定上下文下的特定行为」，很难归类到某个模块。按 issue 号存档是唯一不用纠结分类的方案，而且**半年后看到文件名就能 `gh issue view 7209` 拿回全部上下文**。

44 个文件也是个可上 PPT 的数字：**pi 有 44 个被永久钉死的历史 bug。**

**抄的成本：低**。一个目录 + 一条命名约定。

---

### 抄 5｜`npm run check`：把所有非测试检查串成一条命令，且禁止 `| tail`

**证据**：`package.json:18`（7 个子检查串联）；子脚本 `scripts/check-pinned-deps.mjs`(63)、`check-ts-relative-imports.mjs`(74)、`generate-coding-agent-shrinkwrap.mjs --check`(365)、`generate-coding-agent-install-lock.mjs --check`(439)、`check-browser-smoke.mjs`(128)；纪律 `AGENTS.md:28`（"full output, no tail. Fix all errors, warnings, and infos"）；CI 调用 `.github/workflows/ci.yml:39`；pre-commit 调用 `.husky/pre-commit:13`；PR 前要求 `CONTRIBUTING.md:63`。

**关键设计**：**一个名字，四处复用**（本地手跑 / pre-commit / CI / 发布脚本 `release.mjs:212`）。贡献者只需要记住一个命令，你只需要维护一处定义。

`--error-on-warnings`（`package.json:18`）把 warning 提升成 error，杜绝"warning 慢慢攒"。

`AGENTS.md:28` 的 **"no tail"** 是专门写给 AI agent 的 —— 因为 agent 特别喜欢 `| tail -20` 省 token，然后漏掉前面的错误。

**抄的成本：低**。一行 npm script。子检查按需加。

---

### 抄 6｜pre-commit 只做两件事：拦 lockfile + 跑 check + 重新 stage

**证据**：`.husky/pre-commit`（45 行）：lockfile 闸 `:6`、check `:13`、条件式 browser smoke `:19-36`、**restage** `:39-43`；lockfile 闸实现 `scripts/check-lockfile-commit.mjs`（120 行，`:5-6` 读 `PI_ALLOW_LOCKFILE_CHANGE`，`:34-35` 对比 `HEAD:` 与 `:` 两份 lockfile）；规矩 `AGENTS.md:43`。

**两个非显然的点**：

1. **restage**（`:39-43`）：因为 `biome check --write` 会改文件，不 restage 就会提交未格式化的版本。很多人抄 pre-commit 会漏掉这步。
2. **lockfile 默认禁止提交**：agent 有能力自己 `npm install`，一不小心就把整个 lockfile 改了带进 commit。这个闸门是专门防 agent 的。

**抄的成本：低**。45 行 shell。

---

### 抄 7｜依赖：全部钉死 + `--ignore-scripts` + 生命周期脚本显式白名单（带理由）

**证据**：
- 钉死：`scripts/check-pinned-deps.mjs:5`（精确 semver 正则）、`:54`（失败信息）；实证 `package.json:52-61` devDeps 全精确版本
- `--ignore-scripts`：`ci.yml:33`、`npm-audit.yml:25`、`build-binaries.yml:254`、`release.mjs:131-132`、`publish.mjs:126`、`AGENTS.md:40`
- 白名单：`scripts/generate-coding-agent-install-lock.mjs:16-19`（**只有 2 个包，每个带理由字符串**）；双向校验 `generate-coding-agent-shrinkwrap.mjs:250,257-259`
- 规矩：`AGENTS.md:39`（"Treat npm dep and lockfile changes as reviewed code"）、`AGENTS.md:42`（"never add one silently"）

**为什么 agent 项目要格外狠**：coding agent 是**跑在开发者机器上、有文件读写和 shell 执行权限**的程序。它的依赖树被投毒 = 直接拿到开发机。`--ignore-scripts` 是最有效的单条防线。

白名单里写理由这个细节值得学：

```js
["@google/genai@1.52.0", "preinstall is a no-op in the published package"],
["protobufjs@7.6.5",     "postinstall only warns about protobufjs version scheme mismatches"],
```

半年后没人会记得为什么放行了这两个。

**抄的成本：中**。`check-pinned-deps.mjs` 63 行可以直接拿走（低），但 shrinkwrap/install-lock 那两个（365 + 439 行）是给"要发 npm 给终端用户装"的包准备的，你不发包就不需要。

---

### 抄 8｜CI 的 GitHub Action 全部用 40 位 SHA 钉死 + `permissions: {}` 默认零权限

**证据**：`grep -rh "uses: " .github/workflows/ | grep -v "@[0-9a-f]\{40\}"` **零输出**；34 处 `uses:`、6 个不同 action，全部 SHA + `# vX.Y.Z` 注释；`build-binaries.yml:18` `permissions: {}`；各 job 单独最小授权（`:29-30` `contents: read`；`:73-74` `contents: read` + `id-token: write`）。

**为什么**：`actions/checkout@v4` 这种 tag 引用是**可以被重新指向**的。2024 年以来已有多起 action 供应链事件走的就是这条路。SHA 钉死是唯一的防线。

`permissions: {}` 更狠：默认什么权限都没有，每个 job 自己申请。`pr-gate.yml:10-13` 就只申请了 `contents: read` + `issues: write` + `pull-requests: write`。

**抄的成本：低**。一次性把所有 `@vX` 换成 SHA（`gh api repos/OWNER/REPO/commits/vX --jq .sha`），之后靠 Dependabot 维护。

---

### 抄 9｜lockstep 版本 + 一个会自我校验的 sync 脚本

**证据**：规矩 `AGENTS.md:122`（"all packages share one version ... No major releases"）；实现 `scripts/sync-versions.js`（78 行）：校验 `:29-37`（版本不一致直接 `exit 1` 并打印该跑哪条命令）、改写内部依赖 `:43-68`、跳过 npm 别名的理由注释 `:51-52`；组合命令 `package.json:35-37`；**脚本自己有测试** `scripts/sync-versions.test.mjs`（75 行），由 `package.json:34` `test:scripts` 跑。

**为什么 agent 项目需要**：agent 天然会拆成多包（LLM 抽象 / 循环内核 / 工具 / TUI / 协议）。这些包之间的版本组合是笛卡尔积，一旦允许独立版本，用户装出一个不兼容组合是迟早的事。lockstep 把组合数降到 1。

代价是每次发版所有包都要发。pi 接受了这个代价。

`No major releases` + `minor = breaking` 这个反 semver 的选择也值得讲：**在快速迭代期，major 号只会给人"我可以不升级"的错觉。**

**抄的成本：低**。78 行 node 脚本，加 `npm version -ws --no-git-tag-version` 一条命令。

---

### 抄 10｜发布 = 本地脚本推 tag，CI 负责真正发包（OIDC trusted publishing）

**证据**：
- 本地：`scripts/release.mjs`（247 行）—— 工作区必须干净 `:184-191`、bump `:194`、改 changelog `:198-199`、重生成产物 `:203-207`、`check` `:212`、`build:offline` `:216`、**`./test.sh`** `:220`、commit+tag `:224-227`、加回 `[Unreleased]` `:231-238`、push main + tag `:242-244`；末行 `:247` 明说 "CI publishing starts after the tag push"
- CI：`.github/workflows/build-binaries.yml` 4 job 串联；`publish-npm` 用 `environment: npm-publish` + `id-token: write`（`:71-74`）；发布前**再跑一遍** ci/build/check/test（`:254-263`）；`node scripts/publish.mjs`（`:271`）
- 幂等：`publish.mjs:103-108` 先查已发布，`:121-122` 已发布的跳过
- 溯源：`publish.mjs:126` `npm publish --access public --provenance --ignore-scripts`
- 失败恢复纪律：`AGENTS.md:158`（"The publish helper is idempotent ... Do not rerun npm run release:patch"）
- 草稿 Release 保护：`build-binaries.yml:25-26` 注释 + `cleanup` job `:303-320`

**三个可以直接抄的模式**：

1. **本地脚本止步于 push tag** —— 本地不碰 npm token
2. **publish 幂等** —— 部分失败时可以安全重跑整条流水线
3. **先发草稿 Release、npm 成功后才转公开、任一失败就删草稿**（`:309` 的 `if: always() && ...` 条件）—— 避免"GitHub 上有 v0.83.0 但 npm 上没有"的半发布状态

**抄的成本：中**。release.mjs 的骨架（247 行）可以直接改，OIDC trusted publishing 需要在 npm 侧配一次。

---

### 抄 11｜`AGENTS.md`：把开发规范写成给 AI 看的可执行指令

**证据**：`AGENTS.md`（162 行，11 节）。上文 4.4 节逐条摘过。关键的几条：
- `:52` **永不 `git add -A` / `git add .`**（前提在 `:47`：同一 cwd 可能并发跑多个 pi session）
- `:57-59` 黑名单 7 条 git 命令（`reset --hard`、`checkout .`、`clean -fd`、`stash`、`add -A`、`add .`、`commit --no-verify`）
- `:28` `npm run check` **full output, no tail**
- `:29` **不许主动 build / test**
- `:35` **除非用户要求，绝不 commit**
- `:34` 临时脚本写 `/tmp` 文件再跑，不许在 bash 里塞多行
- `:14` 大改动前必须完整读文件，不许只看 grep 片段
- `:85` **每条 AI 发的评论必须带 AI 免责声明**
- `:160-162` 用户指令与本文件冲突时**先要显式确认**

`CONTRIBUTING.md:19` 明确了它的加载方式：「run it from the `pi` root directory so it picks up `AGENTS.md` automatically」。

**为什么这条是本节最"元"的一条**：pi 是一个 coding agent，它自己的开发也大量用 agent 完成。`AGENTS.md` 是**它给自己写的 system prompt 的一部分**。规矩的内容（尤其 Git 那节）不是抽象的最佳实践，而是**从"多个 agent 并发改同一个仓库会互相踩"这个真实事故里长出来的**。

`:47` 那句话是全文最有信息量的一句：

> Multiple pi sessions may be running in this cwd at the same time, each modifying different files. Git operations that touch unstaged, staged, or untracked files outside your own changes will stomp on other sessions' work.

**抄的成本：低**（写文件）到 **中**（要真的从自己的事故里提炼规矩，而不是抄一份别人的）。直接复制 pi 的 162 行没有意义 —— **有意义的是"每次 agent 干了蠢事，就往这个文件加一条"这个机制。**

---

### 抄 12｜`packages/evals`：把「换 prompt 有没有变好」变成可测量的 lift 数字

**证据**：
- 定位 `packages/evals/README.md:3-5`（"behavioral, model-backed checks ... adapt a real `AgentSession`"）
- 私有不发包 `packages/evals/package.json:4`
- 运行 `packages/evals/scripts/run-evals.mjs`（97 行）；每次运行独立 artifact 目录 `:9-15`
- 配置 `packages/evals/vitest.config.ts:9-14`：串行（`fileParallelism: false`）、`testTimeout: 120000`、双 reporter
- 隔离 `packages/evals/src/pi-harness.ts:122`（`mkdtemp`）+ `:229`（`rm -rf`）+ `:236`（cleanup 失败包成 `AggregateError`）
- 产物快照常量 `packages/evals/src/vitest-evals/artifacts.ts:13` `PI_SESSION_SNAPSHOT_ARTIFACT = "piSessionJsonl"`
- 可变维度 `pi-harness.ts:35-44`（`model` / `noTools` / `transformSystemPrompt` / `output`）
- 多轮输入 `pi-harness.ts:28`（prompt / reload 序列）
- 对比框架 `packages/evals/src/vitest-evals/harness-table.ts:157` `evalHarnessTable`；分组 key `:110` `deriveEvalGroupKey`；repetitions 校验 `:125-127`
- 统计口径 `packages/evals/src/vitest-evals/summary.ts:33-37`（`baselinePassRate` / `candidatePassRate` / `lift` / `baselineWins` / `candidateWins`）
- **纪律** `README:136-138`：`judgeThreshold: null`，**低分是观测不是失败**；硬断言只用于基础设施契约
- 实例 `packages/evals/src/extensions.eval.ts:28-30`（把 system prompt 内容、扩展加载错误直接投影成断言对象）

**为什么这是压轴**：自建 agent harness 的人都会遇到同一个问题 —— **改了 system prompt / 换了工具描述 / 加了个 skill，怎么知道变好了还是变坏了？** 绝大多数人的答案是"跑几个例子看看感觉"。

pi 给的答案是一套完整的方法论：
1. 同一批输入，跑 baseline 和 candidate 两个 harness
2. 每个跑 N 次（`repetitions`）
3. 用 judge 打分，score ≥ 1 算 pass
4. **lift = candidate pass rate − baseline pass rate（百分点）**
5. token / latency / cost 单独算配对差值，不混进 lift
6. **分数低不让 CI 挂**

第 6 点是最容易被抄错的。把评测当断言会导致两个后果：CI 因为模型抖动天天红，然后大家开始降阈值直到它没意义。pi 的做法是让评测只产出观测，人来看趋势。

**抄的成本：高**。理由有三：
- 基础设施本身就有 1000+ 行（`pi-harness.ts` 257 + `summary.ts` 438 + `harness-table.ts` 193 + `artifacts.ts` 113 + `reporter.ts` 111）
- **每跑一次都真的花钱**（`testTimeout: 120000` 就是在等模型）
- 需要持续维护 judge 的可信度

但注意 pi 自己也只写了 **2 个 `.eval.ts` 文件**。**起步版本可以很小**：抄 `smoke.eval.ts`（17 行）的形态先建一条「端到端还活着」的评测，等真的要做 prompt A/B 时再上 `evalHarnessTable`。

---

### 12 条成本汇总

| # | 条目 | 成本 | 核心证据 |
|---|---|---|---|
| 1 | faux provider 做成正式 provider | 中 | `packages/ai/src/providers/faux.ts:501` |
| 2 | `env -i` 隔离测试脚本 | **低** | `test.sh:79` |
| 3 | `skipIf` 自动降级 e2e | **低** | `packages/ai/test/abort.test.ts:101` |
| 4 | 按 issue 号命名回归测试 | **低** | `test/suite/README.md:14`（44 个文件） |
| 5 | 一条 `npm run check` 串 7 检查 | **低** | `package.json:18` |
| 6 | pre-commit：lockfile 闸 + check + restage | **低** | `.husky/pre-commit:39-43` |
| 7 | 依赖钉死 + `--ignore-scripts` + 白名单带理由 | 中 | `generate-coding-agent-install-lock.mjs:16-19` |
| 8 | Action SHA 钉死 + `permissions: {}` | **低** | `build-binaries.yml:18` |
| 9 | lockstep 版本 + 自校验 sync 脚本 | **低** | `scripts/sync-versions.js:29-37` |
| 10 | 本地推 tag / CI 用 OIDC 发包 + 幂等 | 中 | `publish.mjs:103-126`、`build-binaries.yml:71-74` |
| 11 | `AGENTS.md` 可执行开发规范 | 低→中 | `AGENTS.md:47-59` |
| 12 | evals：baseline vs candidate lift | **高** | `summary.ts:33-37`、`README:136-138` |

**7 条低成本 / 3 条中 / 1 条中偏高 / 1 条高。**
如果只有一天时间，抄 **2 → 5 → 6 → 4 → 8** 这五条（全低成本），就能拿到 pi 工程纪律里最实用的部分。

---

## 8. 最适合上 PPT 的 5 条硬事实

1. **测试代码 99331 行 vs 生产代码 111505 行，比值 0.89 —— 近似 1:1。**
   386 个测试文件，其中 `coding-agent` 占 195 个、`ai` 占 122 个。
   *（`find + wc -l` 实测；`packages/*/src/**/*.ts` 排除 `*.generated.ts`）*

2. **`npm run check` 一条命令 = 7 个子检查，在 4 个地方被复用：本地、pre-commit、CI、发布脚本。**
   biome（warning 当 error）→ 依赖钉死 → `.ts` 导入规范 → shrinkwrap → install-lock → `tsgo --noEmit` → 浏览器冒烟。
   `AGENTS.md:28` 还专门写了一条给 AI 的纪律：**"full output, no tail"**。
   *（`package.json:18`、`.husky/pre-commit:13`、`ci.yml:39`、`release.mjs:212`）*

3. **34 处 GitHub Action 引用，100% 用 40 位 commit SHA 钉死，0 个用 tag；`build-binaries.yml` 顶层 `permissions: {}` 默认零权限。**
   整个 `coding-agent` 依赖树里只有 **2 个包**被允许带 npm 生命周期脚本，白名单里每条都写了放行理由。
   *（`grep -v "@[0-9a-f]\{40\}"` 零输出；`build-binaries.yml:18`；`generate-coding-agent-install-lock.mjs:16-19`）*

4. **12113 行用户文档，30 篇；前 3 篇 `extensions.md`(2984) + `rpc.md`(1576) + `sdk.md`(1186) 占 47%，全是给二次开发者的接口文档。**
   而 `quickstart.md` 只有 165 行。文档投入的重心不在"怎么用"，在"怎么扩展我"。
   *（`wc -l packages/coding-agent/docs/*.md`）*

5. **`packages/evals` 用 1527 行基础设施支撑 2 个评测文件，产出的是「lift = candidate pass rate − baseline pass rate（百分点）」，而且明确规定评测低分不算测试失败（`judgeThreshold: null`）。**
   这是"改了 prompt 到底有没有变好"这个问题唯一可测量的答案形态。
   *（`packages/evals/README.md:136-150`；`src/vitest-evals/summary.ts:33-37`）*

---

## 附：本文所有实测命令

```bash
# 测试体量
find packages -path '*/node_modules' -prune -o -type f \
  \( -name '*.test.ts' -o -name '*.test.mjs' -o -name '*.spec.ts' \) -print | wc -l           # 386
find packages -path '*/node_modules' -prune -o -type f \
  \( -name '*.test.ts' -o -name '*.test.mjs' -o -name '*.spec.ts' \) -print0 \
  | xargs -0 wc -l | tail -1                                                                  # 99331
find packages -path '*/node_modules' -prune -o -path '*/src/*' -name '*.ts' \
  ! -name '*.generated.ts' -print0 | xargs -0 wc -l | tail -1                                 # 111505
find packages -path '*/node_modules' -prune -o -path '*/test/*' -name '*.ts' -print0 \
  | xargs -0 wc -l | tail -1                                                                  # 102982
ls packages/coding-agent/test/suite/regressions/ | wc -l                                      # 44
grep -rn "skipIf" packages/ai/test packages/agent/test | wc -l                                # 372
find packages -path '*/node_modules' -prune -o -name '*e2e*.test.ts' -print | wc -l           # 6

# CI
ls .github/workflows | wc -l                                                                  # 10
wc -l .github/workflows/*                                                                     # 1885 total
grep -rh "uses: " .github/workflows/ | grep -v "@[0-9a-f]\{40\}" | sort -u                    # 空
wc -l .github/APPROVED_CONTRIBUTORS                                                           # 325

# 文档
wc -l packages/coding-agent/docs/*.md | sort -rn                                              # 12113 total / 30 篇
find packages -path '*/node_modules' -prune -o -name '*.md' -print | wc -l                    # 86
wc -l README.md AGENTS.md CONTRIBUTING.md SECURITY.md                                         # 113/162/102/87

# evals
wc -l packages/evals/README.md packages/evals/src/*.ts \
      packages/evals/src/vitest-evals/*.ts packages/evals/scripts/run-evals.mjs               # 1527 total

# 脚本
wc -l scripts/*.mjs scripts/*.js scripts/*.ts                                                 # 6547 total
```
