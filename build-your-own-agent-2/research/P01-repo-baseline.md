# P01：pi-mono 仓库总览与工程基线

> 本文所有数字都是在下述基线上**自己跑命令**算出来的，命令原文附在每张表下方。
> 所有 `路径:行号` 都已实际 `Read`/`cat -n` 打开确认。

---

## 0. 取证基线（务必随引用一起上 PPT）

| 项 | 值 | 出处 / 命令 |
|---|---|---|
| 仓库 | `https://github.com/earendil-works/pi.git` | `git remote -v` |
| commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95`（短 `583f153`） | `git log -1 --format=%H` |
| commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --format=%ci` |
| workspace 版本 | `0.83.0` | `packages/coding-agent/package.json:3`、`packages/agent/package.json:3`、`packages/ai/package.json:3` |
| monorepo 根版本 | `0.0.3`（根 `package.json` 是 private 壳，版本号不参与发布） | `package.json` `"version": "0.0.3"` |
| 本地路径 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
| 取证日期 | 2026-08-02 | — |
| **克隆深度** | **shallow clone**（`.git/shallow` 存在，`git rev-parse --is-shallow-repository` → `true`） | 见下方「⚠️ 重要限制」 |

**⚠️ 重要限制（影响第 6 节）**：本地是浅克隆，`git log` 只有 **162 条** commit、**3 个 tag**（`v0.82.0` / `v0.82.1` / `v0.83.0`），最早 commit 是 2026-07-24。**因此本地 git 历史不能用来讲"项目总提交数/总寿命"**。第 6 节的发布节奏改用 `packages/coding-agent/CHANGELOG.md`（完整、随包发布、可交叉验证）作为权威数据源。

```bash
$ git rev-parse HEAD
583f153d502aa8e958eefdb9af0fbd3344e68f95
$ git rev-parse --is-shallow-repository
true
$ git log --oneline | wc -l
     162
$ git tag
v0.82.0
v0.82.1
v0.83.0
```

---

## 1. monorepo 包结构：9 个包

`package.json:5-13` 的 `workspaces` 声明：

```json
"workspaces": [
	"packages/*",
	"packages/storage/*",
	"packages/coding-agent/examples/extensions/with-deps",
	"packages/coding-agent/examples/extensions/custom-provider-anthropic",
	"packages/coding-agent/examples/extensions/custom-provider-gitlab-duo",
	"packages/coding-agent/examples/extensions/sandbox",
	"packages/coding-agent/examples/extensions/gondolin"
]
```

> 注意：workspace glob 里那 5 条 `examples/extensions/*` 是**示例扩展**自带 `package.json`，不是产品包。**产品包共 9 个**：`packages/*` 8 个 + `packages/storage/sqlite-node` 1 个。

### 1.1 九个包一句话职责 + 实测规模

| # | 包名（npm） | 目录 | 一句话职责（取自各自 `package.json` 的 `description`） | src 文件数 | src 行数 |
|---|---|---|---|---|---|
| 1 | `@earendil-works/pi-coding-agent` | `packages/coding-agent` | 带 read/bash/edit/write 工具与会话管理的编码 agent CLI —— **产品本体** | 183 | **56,431** |
| 2 | `@earendil-works/pi-ai` | `packages/ai` | 统一多厂商 LLM API，自动模型发现与 provider 配置 | 169 | 21,429 |
| 3 | `@earendil-works/pi-tui` | `packages/tui` | 差分渲染的终端 UI 库 | 37 | 14,184 |
| 4 | `@earendil-works/pi-agent-core` | `packages/agent` | 通用 agent（传输抽象 / 状态管理 / 附件） —— **agent 内核 + harness** | 37 | 10,368 |
| 5 | `@earendil-works/pi-server` | `packages/server` | 实验性 server 包 | 30 | 4,281 |
| 6 | `@earendil-works/pi-storage-sqlite-node` | `packages/storage/sqlite-node` | pi-agent-core 会话的 Node sqlite 存储后端 | 13 | 1,796 |
| 7 | `@earendil-works/pi-evals` | `packages/evals` | 评测（**`private: true`，不发布**） | 8 | 1,277 |
| 8 | `@earendil-works/pi-protocol` | `packages/protocol` | 传输无关的 CBOR 远程会话协议 | 8 | 1,233 |
| 9 | `@earendil-works/pi-client` | `packages/client` | 基于分帧 CBOR 字节的远程会话客户端 | 10 | 1,233 |
| | **合计** | | | **495** | **112,232** |

```bash
$ for d in packages/*/src packages/storage/*/src; do
    n=$(find "$d" -type f \( -name '*.ts' -o -name '*.tsx' \) | wc -l)
    l=$(find "$d" -type f \( -name '*.ts' -o -name '*.tsx' \) -exec cat {} + | wc -l)
    echo "$d files=$n lines=$l"; done
```

**规模的极端不均衡**：`coding-agent` 一个包占全部 src 的 **50.3%**（56431/112232）。前三个包（coding-agent / ai / tui）合计 **92,044 行 = 82.0%**。

`coding-agent/src` 内部再切一刀：

| 子目录 | 文件数 | 行数 | 说明 |
|---|---|---|---|
| `core/` | 73 | 27,951 | AgentSession、tools、extensions、compaction、session-manager |
| `modes/` | 52 | 18,862 | interactive TUI / json / rpc 等运行模式 |
| `utils/` | 30 | 3,291 | |
| `extensions/` | 6 | 1,391 | |
| `cli/` | 9 | 1,224 | |
| `client/` | 3 | 536 | |
| `bun/` | 3 | 55 | Bun 单文件二进制入口垫片 |

```bash
$ for d in packages/coding-agent/src/*/; do
    echo "$d $(find $d -name '*.ts' | wc -l) $(find $d -name '*.ts' -exec cat {} + | wc -l)"; done
```

> 上 PPT 的点：**UI（modes 18.8k）几乎和内核（core 27.9k）一个量级**。一个"agent 框架"里真正花力气的地方，不全在 agent。

### 1.2 依赖关系（grep 实测，只统计真实 `from "..."` 语句）

```bash
$ for d in agent ai client coding-agent evals protocol server tui storage/sqlite-node; do
    echo "--- $d"
    grep -rhoE 'from "(@earendil-works/pi-[a-z-]+)' packages/$d/src | sed 's/from "//' | sort | uniq -c | sort -rn
  done
```

实测结果（数字 = import 语句条数）：

| 消费方 → 被依赖方 | pi-ai | pi-agent-core | pi-tui | pi-protocol | pi-client | pi-coding-agent |
|---|---|---|---|---|---|---|
| `coding-agent` | **59** | **32** | **66** | 2 | 1 | (1，自引用¹) |
| `agent` | 14 | — | — | — | — | — |
| `server` | 2 | — | — | 10 | — | 7 |
| `client` | — | — | — | 7 | — | — |
| `storage/sqlite-node` | 1 | 12 | — | — | — | — |
| `evals` | 1 | — | — | — | — | 1 |
| `ai` | (4，自引用¹) | — | — | — | — | — |
| `protocol` | — | — | — | — | — | — |
| `tui` | — | — | — | — | — | — |

¹ 自引用不是真依赖：`ai` 的 4 条全在 `packages/ai/src/legacy-api-aliases.ts:28/33/39/44` 的 `@deprecated` **注释**里；`coding-agent` 的自引用在 `packages/coding-agent/src/core/extensions/loader.ts:66`，是给 jiti 虚拟模块表用的**字符串键**（`loader.ts:26` 注释明写 "avoiding a circular dependency"）。

**分层结论（无循环依赖）**：

```
        protocol   tui        ai           ← 第 0 层：零内部依赖（叶子）
           │        │       ╱  │
        client      │  agent-core          ← 第 1 层
           │        │    ╱   │
           └──── coding-agent │            ← 第 2 层（唯一的胖节点）
                    │      storage/sqlite-node
                 server                    ← 第 3 层
```

- **`protocol` / `tui` / `ai` 三个包对内零依赖**（grep 无任何 `@earendil-works/` import），可以单独拿出来用。
- `agent-core` 只依赖 `ai`（14 处），**不依赖 tui、不依赖 coding-agent** —— 这是"SDK 可独立分发"的代码级证据。
- `coding-agent` 是唯一同时吃 ai + agent-core + tui 的包，也是唯一提供 `pi` 二进制的包。

`package.json` 声明侧交叉验证（`dependencies` 里的 `@earendil-works/*`）：

| 包 | package.json 里声明的内部依赖 | 行号 |
|---|---|---|
| `agent` | `pi-ai ^0.83.0` | `packages/agent/package.json:31` 起 |
| `coding-agent` | `pi-agent-core` / `pi-ai` / `pi-client` / `pi-protocol` / `pi-tui`（全 `^0.83.0`） | `packages/coding-agent/package.json:45` 起 |
| `server` | `pi-ai` / `pi-coding-agent` / `pi-protocol` | — |
| `client` | `pi-protocol` | — |
| `storage/sqlite-node` | `pi-ai` / `pi-agent-core` | — |
| `protocol` / `tui` | 无 | — |

> 注意一个不一致：`coding-agent/package.json` 声明了 `pi-client`，但 src 里只有 **1 处** import；`pi-protocol` 也只有 2 处。属于弱耦合。

---

## 2. 运行时与工具链

### 2.1 运行时：**Node 是第一公民，Bun 只用于打二进制**

| 事实 | 证据 |
|---|---|
| 引擎要求 `node >= 22.19.0` | `package.json:63-64`；`packages/coding-agent/package.json:104-105` 同样声明 |
| npm bin 入口 `pi` → `dist/cli.js` | `packages/coding-agent/package.json:9-10` |
| CLI 首行 shebang 是 **node** | `packages/coding-agent/src/cli.ts:1` `#!/usr/bin/env node` |
| CI 用 Node 22，**不装 Bun** | `.github/workflows/ci.yml:22-24`（`node-version: 22`） |
| **全仓 `package.json` 里 `bun` 只出现 1 次** | `grep -rn "bun" package.json packages/coding-agent/package.json` → 唯一命中 `packages/coding-agent/package.json:38` |

那唯一一次是 `build:binary`（`packages/coding-agent/package.json:38`）：

```
... && npm run build && bun build --compile ./dist/bun/cli.js ./src/utils/image-resize-worker.ts --outfile dist/pi && npm run copy-binary-assets
```

即 **Bun 的角色只有一个：`bun build --compile` 产出单文件可执行 `dist/pi`**。日常开发、测试、CI 全走 Node。`packages/coding-agent/src/bun/`（3 文件 / 55 行）就是给这条路径的入口垫片。

`AGENTS.md:131-145` 的发布 smoke 清单也印证了双轨：`/tmp/pi-local-release/node/pi` 与 `/tmp/pi-local-release/bun/pi` 各跑一遍 `--help / --version / --list-models / -p / 交互`。

### 2.2 `cli.ts` 只有 20 行

`packages/coding-agent/src/cli.ts`（`wc -l` = **20**）全文要点：

```ts
#!/usr/bin/env node                                  // :1
import { APP_NAME } from "./config.ts";              // :8   ★ 带 .ts 后缀
import { configureHttpDispatcher } from "./core/http-dispatcher.ts";
import { main } from "./main.ts";
process.title = APP_NAME;                            // :12
process.env.PI_CODING_AGENT = "true";                // :13
process.emitWarning = (() => {}) as typeof process.emitWarning;  // :14
configureHttpDispatcher();                           // :18
main(process.argv.slice(2));                         // :20
```

三个 bin 入口（全仓）：

| bin 名 | 目标 | 声明位置 | 源文件行数 |
|---|---|---|---|
| `pi` | `dist/cli.js` | `packages/coding-agent/package.json:9-10` | `src/cli.ts` = 20 行 |
| `pi-ai` | `dist/cli.js` | `packages/ai/package.json:43` | `packages/ai/src/cli.ts` = 118 行 |
| `server` | `./dist/legacy/cli.js` | `packages/server/package.json` `bin` | `packages/server/src/legacy/cli.ts` = 161 行 |

另有非 bin 的入口 `packages/coding-agent/src/rpc-entry.ts`（build 时同样 `chmod +x`，见 `packages/coding-agent/package.json:37`）。

### 2.3 编译器与 lint：`tsgo` + biome，**不用 bundler**

| 工具 | 版本 | 位置 |
|---|---|---|
| TypeScript | `5.9.3` | 根 `devDependencies` |
| `@typescript/native-preview`（提供 `tsgo`） | `7.0.0-dev.20260120.1` | 根 `devDependencies` |
| Biome（format + lint） | `2.3.5` | 根 `devDependencies` |
| esbuild | `0.28.1` | 根 `devDependencies`（仅脚本用） |
| jiti | `2.7.0` | 根 devDep **且** `coding-agent` 生产依赖（扩展加载） |
| vitest | 各包 devDep | 根 `vitest.base.ts` 提供 alias |

各包 `build` 就是 `tsgo -p tsconfig.build.json` + `shx` 拷资源（`packages/coding-agent/package.json:37`）——**没有 webpack/rollup/tsup**。

`tsconfig.base.json` 里两条决定性设置：

```jsonc
"erasableSyntaxOnly": true,        // :7   ★ 只允许可擦除语法
"allowImportingTsExtensions": true, // :18
"rewriteRelativeImportExtensions": true, // :19
```

`AGENTS.md:20` 把这条规则写成了纪律：

> Use only erasable TypeScript syntax (Node strip-only mode) …: no parameter properties, `enum`, `namespace`/`module`, `import =`, `export =` …

配套的 CI 检查是 `scripts/check-ts-relative-imports.mjs`（`check-ts-relative-imports.mjs:23-25` 定义"相对 `.js` 说明符"为违规），保证源码里写 `./main.ts` 而不是 `./main.js`。

> 上 PPT 的点：**pi 的源码可以直接被 `node --experimental-strip-types` 跑**，这是它敢把"扩展 = 一个 .ts 文件、jiti 直接 import"当成核心机制的前提。

### 2.4 根 `package.json` 的关键脚本

| 脚本 | 行号 | 干什么 |
|---|---|---|
| `build` | `:16` | **手写的固定顺序串行构建**：tui → ai → agent → storage/sqlite-node → protocol → client → coding-agent → server（没有 turbo/nx，顺序即拓扑序） |
| `check` | `:18` | `biome check --write --error-on-warnings .` + `check:pinned-deps` + `check:ts-imports` + `check:shrinkwrap` + `check:install-lock:coding-agent` + `tsgo --noEmit` + `check:browser-smoke` —— **7 道关卡串一行** |
| `test` | `:33` | `test:scripts`（`node --test scripts/*.test.mjs`）+ 各 workspace `vitest --run` |
| `version:patch/minor/major` | `:35-37` | `npm version -ws --no-git-tag-version` + `scripts/sync-versions.js` + `npm install --package-lock-only --ignore-scripts` |
| `prepublishOnly` | `:39` | `clean && build && check` |
| `publish` | `:40` | `prepublishOnly && node scripts/publish.mjs` |
| `release:patch/minor/major` | `:45-47` | `node scripts/release.mjs <level>` |
| `prepare` | `:49` | `husky` |

`scripts/` 目录：**30 个可执行脚本、6,963 行**。

```bash
$ find scripts -type f \( -name '*.mjs' -o -name '*.js' -o -name '*.ts' -o -name '*.sh' \) | wc -l
      30
$ find scripts -type f \( -name '*.mjs' -o -name '*.js' -o -name '*.ts' -o -name '*.sh' \) -exec cat {} + | wc -l
    6963
```

---

## 3. 依赖治理：27 个外部生产依赖

### 3.1 全仓外部生产依赖去重后 = **27 个**

```bash
$ python3 - <<'EOF'
import json,glob
ext=set()
for f in glob.glob('packages/*/package.json')+glob.glob('packages/storage/*/package.json'):
    p=json.load(open(f))
    for k in p.get('dependencies',{}):
        if not k.startswith('@earendil-works/'): ext.add(k)
print(len(ext)); print(sorted(ext))
EOF
27
```

| 包 | 外部生产依赖数 | 清单 |
|---|---|---|
| `coding-agent` | **16**（+4 个内部） | `@silvia-odwyer/photon-node` `chalk` `cross-spawn` `diff` `glob` `highlight.js` `hosted-git-info` `ignore` `jiti` `minimatch` `proper-lockfile` `semver` `typebox` `undici` `yaml` `@earendil-works/pi-tui`… |
| `ai` | **11** | `@anthropic-ai/sdk` `@aws-sdk/client-bedrock-runtime` `@google/genai` `@mistralai/mistralai` `@opentelemetry/api` `@smithy/node-http-handler` `http-proxy-agent` `https-proxy-agent` `openai` `partial-json` `typebox` |
| `agent` | **4**（+1 内部） | `diff` `ignore` `typebox` `yaml` |
| `tui` | **2** | `get-east-asian-width` `marked` |
| `protocol` | **1** | `typebox` |
| `client` | **0**（只有 `pi-protocol`） | — |
| `server` | **0**（只有 3 个内部） | — |
| `storage/sqlite-node` | **0**（只有 2 个内部） | — |
| `evals` | **0**（`private: true`，全部在 devDeps） | — |

**最小化的硬证据（不是感觉，是数字）**：

1. **`ai` 的 11 个依赖里有 6 个是厂商 SDK**（Anthropic / AWS Bedrock / Google / Mistral / OpenAI / smithy），去掉厂商 SDK 后真正的"工具库"只有 `partial-json`、`typebox`、两个 proxy-agent、`@opentelemetry/api`。
2. **`agent-core`（agent 内核，10,368 行）只有 4 个外部依赖**：`diff` / `ignore` / `typebox` / `yaml`。**没有** zod、没有 lodash、没有 rxjs、没有任何 DI 框架。
3. **`tui`（14,184 行的终端 UI 库）只有 2 个外部依赖**：`get-east-asian-width`（字宽计算）+ `marked`（markdown）。没有 ink、没有 blessed、没有 React。
4. **全仓统一用 `typebox@1.3.7` 做 schema**（agent / ai / coding-agent / protocol 四个包都列了它，同一个精确版本），无第二套校验库。
5. `client` / `server` / `storage-sqlite-node` **零外部生产依赖**。

> 上 PPT 的点：**一个 11 万行的 agent 框架，外部生产依赖 27 个；扣掉 6 个厂商 SDK 只剩 21 个。**

### 3.2 供应链加固：**8 道措施，全部有代码/配置为证**

| # | 措施 | 证据（路径:行号） |
|---|---|---|
| 1 | **直接外部依赖一律锁死精确版本**（内部包才用 `^`） | `.npmrc:1` `save-exact=true`；`scripts/check-pinned-deps.mjs:5` 的 `exactVersionPattern` 正则、`:24-26` 豁免 `@earendil-works/pi-` 前缀；`README.md:79` |
| 2 | **新版本冷却期 2 天** | `.npmrc:2` `min-release-age=2`；`README.md:80` 明说是 "avoid same-day dependency releases" |
| 3 | **lockfile 当代码审** + pre-commit 拦截 | `.husky/pre-commit:6-9` 调 `scripts/check-lockfile-commit.mjs`；该脚本 `:5-6` 只认 `PI_ALLOW_LOCKFILE_CHANGE=1/true/yes`；`AGENTS.md:43`、`README.md:81` |
| 4 | **发布包内嵌 shrinkwrap 锁死传递依赖** | `packages/coding-agent/npm-shrinkwrap.json` 存在（62,222 字节，`lockfileVersion: 3`，**142 条 packages 记录、136 条带 `integrity` 哈希**）；`packages/coding-agent/package.json:27` `files` 数组含它；`README.md:83` |
| 5 | **lifecycle script 显式白名单**（默认拒绝） | `scripts/generate-coding-agent-shrinkwrap.mjs:13-16` —— 全仓**只允许 2 个**：`@google/genai@1.52.0`（"preinstall is a no-op"）、`protobufjs@7.6.5`（"postinstall only warns"）；`:249-251` 不在名单直接报错；`:257-260` 名单里的包若已消失也报错（防止白名单腐烂） |
| 6 | **全链路 `--ignore-scripts`** | `.github/workflows/ci.yml:33` `npm ci --ignore-scripts`；`.github/workflows/npm-audit.yml:25` `npm ci --ignore-scripts --no-audit --no-fund`；`README.md:54/85`；`AGENTS.md:40` |
| 7 | **每日定时 npm audit + 签名校验** | `.github/workflows/npm-audit.yml:5` `cron: '37 7 * * *'`；`:28` `npm audit --omit=dev --audit-level=moderate`；`:30` `npm audit signatures --omit=dev` |
| 8 | **GitHub Action 按 commit SHA 钉死**（不用可变 tag） | `.github/workflows/ci.yml:18` `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`、`:21` `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0`；npm-audit.yml 同样处理 |

另有 `overrides`（`package.json:67-73`）强制统一 `protobufjs@7.6.5` / `rimraf@6.1.2`，以及 `packages/coding-agent/install-lock/`（独立的 `package.json` + `package-lock.json`，由 `scripts/generate-coding-agent-install-lock.mjs` 生成并被 `npm run check` 校验，`package.json:22`）。

lockfile 规模实测：

```bash
$ python3 -c "import json;d=json.load(open('package-lock.json'));ps=d['packages'];print(len(ps), sum(1 for v in ps.values() if 'integrity' in v))"
425 396      # 根 lockfile：425 条记录，396 条带 integrity
$ python3 -c "import json;d=json.load(open('packages/coding-agent/npm-shrinkwrap.json'));ps=d['packages'];print(d['lockfileVersion'], len(ps), sum(1 for v in ps.values() if 'integrity' in v))"
3 142 136    # 发布用 shrinkwrap：142 条，136 条带 integrity
```

> 上 PPT 的点：**根 lockfile 425 条 → 发布给 npm 用户的 shrinkwrap 只剩 142 条**。开发期依赖没有一条流进用户机器。

### 3.3 CI 关卡（`.github/workflows/` 共 10 个 workflow）

`ci.yml` 主流程（`:14-42`）：checkout（SHA 钉死）→ setup-node 22 → `apt install libcairo2-dev … fd-find ripgrep` + `ln -s fdfind fd`（`:29-30`，说明 **grep/find 工具依赖系统级 `rg`/`fd`**）→ `npm ci --ignore-scripts` → `build` → `check` → `test`。

10 个 workflow 全清单：`ci.yml`、`npm-audit.yml`、`pr-gate.yml`、`issue-gate.yml`、`issue-triage-labels.yml`、`issue-analysis.yml`、`approve-contributor.yml`、`remove-inprogress-on-close.yml`、`build-binaries.yml`、`publish-model-catalog.yml`（外加 `.github/APPROVED_CONTRIBUTORS` 名单文件）。

---

## 4. 代码规模分布：源码 / 测试 / 文档 / 示例

### 4.1 总表（全部实测）

| 类别 | 文件数 | 行数 | 命令 |
|---|---|---|---|
| **源码**（`packages/*/src`，含 `storage/*`） | 495 | **112,232** | `find packages/*/src packages/storage/*/src -name '*.ts*' \| wc -l` |
| **测试**（`packages/*/test/**`，`*.test.ts*`） | 386 | **99,331** | `find packages -name '*.test.ts*' -not -path '*/node_modules/*' -not -path '*/dist/*'` |
| **文档**（全仓 `*.md`，排除 node_modules/.git） | 97 | **34,595** | `find . -name '*.md' -not -path './.git/*' -not -path '*/node_modules/*'` |
| **示例**（`coding-agent/examples`，仅 `.ts`） | 99 | **15,824** | `find packages/coding-agent/examples -name '*.ts' -not -path '*/node_modules/*'` |
| **工程脚本**（`scripts/`） | 30 | 6,963 | 见 2.4 |
| （参考）packages 下全部 `.ts/.tsx` | 1,025 | 234,497 | — |

**测试/源码 = 99,331 / 112,232 = 0.885**。

### 4.2 测试分布：**一行测试代码都不在 `src` 里**

```bash
$ find packages/*/src packages/storage/*/src -name '*.test.ts*' | wc -l
       0
```

**`src` 目录零测试文件**，全部集中在各包 `test/`：

| 包 | test 文件数 | test 行数 | test/src 行数比 |
|---|---|---|---|
| `coding-agent` | 195 | 42,887 | 0.76 |
| `ai` | 122 | 30,138 | 1.41 |
| `tui` | 30 | 14,164 | **1.00** |
| `agent` | 19 | 8,572 | 0.83 |
| `server` | 7 | 1,386 | 0.32 |
| `client` | 6 | 1,061 | 0.86 |
| `protocol` | 3 | 660 | 0.54 |
| `evals` | 4 | 463 | 0.36 |
| `storage/sqlite-node` | **0** | **0** | **0**（待核实：为何唯一无测试） |

> `tui` 的测试行数（14,164）几乎等于源码行数（14,184），差 20 行。`ai` 的测试是源码的 1.41 倍——多 provider 适配天然需要矩阵测试。

`AGENTS.md:30` 还规定了**禁止直接跑全量 vitest**（会激活需要真实 endpoint/auth 的 e2e）：

> Never run the full vitest suite directly … For all non-e2e tests, run `./test.sh` from the repo root.

### 4.3 文档：34,595 行 md

| 位置 | 文件数 | 行数 |
|---|---|---|
| `packages/coding-agent/docs/` | 30 | **12,113** |
| 根目录 | 6（`README.md` / `AGENTS.md` / `CONTRIBUTING.md` / `SECURITY.md` / `LICENSE` 非 md / `tui-plan.md`） | — |
| `packages/coding-agent/CHANGELOG.md` | 1 | **5,232** |
| 其余（各包 README、examples README 等） | — | — |
| **合计** | **97** | **34,595** |

`docs/` 的 30 篇：`compaction` `containerization` `custom-provider` `development` `environment-variables` `extensions` `index` `json` `keybindings` `llama-cpp` `models` `packages` `prompt-templates` `providers` `quickstart` `rpc` `sdk` `security` `session-format` `sessions` `settings` `shell-aliases` `skills` `terminal-setup` `termux` `themes` `tmux` `tui` `usage` `windows`（+ `docs.json` + `images/`）。

> 单看 `tui-plan.md` 一个文件就 36,414 字节，是仓库根第二大的非 lockfile 文本。

### 4.4 示例：99 个 `.ts` / 15,824 行

```bash
$ find packages/coding-agent/examples -type f -not -path '*/node_modules/*' | wc -l
     134
$ ls -d packages/coding-agent/examples/extensions/*/ | wc -l
       9      # 9 个多文件扩展示例（含自带 package.json 的 with-deps/sandbox/gondolin 等）
$ ls packages/coding-agent/examples/extensions/*.ts | wc -l
      69      # 69 个单文件扩展示例
$ ls packages/coding-agent/examples/sdk | wc -l
      14      # 14 个 SDK 示例（01-minimal.ts … ）
```

**扩展示例合计 78 项（69 单文件 + 9 目录）**，SDK 示例 14 个（`01-minimal.ts` / `02-custom-model.ts` / `03-custom-prompt.ts` / `04-skills.ts` / `05-tools.ts` / `06-extensions.ts` / `07-context-files.ts` / `08-prompt-templates.ts` / `09-api-keys-and-oauth.ts` / `10-settings.ts` …）。

**示例被当成发布产物**：`packages/coding-agent/package.json:27` 的 `files` 数组包含 `"docs"` 和 `"examples"`；`copy-binary-assets` 脚本里 `shx cp -r docs dist/ && shx cp -r examples dist/`。即 **npm 装 pi 会把 30 篇文档和 134 个示例文件一起装到本地**——这正是 system prompt 里"Pi documentation (read only when the user asks about pi itself)"能给出绝对路径的原因。

### 4.5 吃自己狗粮：`.pi/` 目录

```bash
$ find .pi -type f
.pi/extensions/redraws.ts        .pi/extensions/import-repro.ts
.pi/extensions/prompt-url-widget.ts  .pi/extensions/tps.ts
.pi/prompts/wr.md  .pi/prompts/pr.md  .pi/prompts/sa.md  .pi/prompts/cl.md  .pi/prompts/is.md
.pi/skills/add-llm-provider.md
.pi/npm/.gitignore  .pi/git/.gitignore
```

4 个自用扩展 + 5 个 prompt 模板 + 1 个 skill。仓库自己就是 pi 的一个 project。

---

## 5. 版本与发布节奏

### 5.1 权威数据源：`packages/coding-agent/CHANGELOG.md`

（本地 git 是浅克隆，不可用；见第 0 节）

```bash
$ grep -cE '^## ' packages/coding-agent/CHANGELOG.md
268                                    # 含 1 个 [Unreleased]
$ grep -E '^## \[[0-9]' packages/coding-agent/CHANGELOG.md | wc -l
267                                    # 带版本号的正式发布
$ grep -E '^## \[[0-9]' packages/coding-agent/CHANGELOG.md | head -1
## [0.83.0] - 2026-07-29
$ grep -E '^## \[[0-9]' packages/coding-agent/CHANGELOG.md | tail -1
## [0.10.0] - 2025-11-25
$ wc -l packages/coding-agent/CHANGELOG.md
    5232
```

| 项 | 值 |
|---|---|
| CHANGELOG 最早版本 | `0.10.0` — 2025-11-25 |
| CHANGELOG 最新已发布版本 | `0.83.0` — 2026-07-29 |
| 跨度 | **246 天** |
| 正式发布次数 | **267 次** |
| **平均发布频率** | **1.09 次 / 天** |
| 2026 年 7 月发布次数 | **12 次**（`grep -E '^## \[[0-9].*2026-07'`） |
| CHANGELOG 总行数 | 5,232 |
| 当前状态 | HEAD（`583f153`，2026-08-01）领先 `v0.83.0` 标签，`[Unreleased]` 段已有 6 条 Added + 9 条 Fixed |

> 0.10.0 → 0.83.0 走了 73 个 minor，246 天。**minor 号每 3.4 天涨一次**。

### 5.2 本地 shallow 历史里的提交密度（仅供参考，不代表项目全貌）

```bash
$ git log --format='%ad' --date=short | sort | uniq -c
   7 2026-07-24
   8 2026-07-25
   1 2026-07-26
   9 2026-07-27
   8 2026-07-29
  39 2026-07-30
  75 2026-07-31
  15 2026-08-01
```

7 月 30–31 两天 **114 次提交**——正好是 `v0.83.0`（7-29 打标）之后的密集迭代窗口。

### 5.3 tag 与发布流程

本地 3 个 tag（浅克隆所限）：

```bash
$ git log --tags --simplify-by-decoration --format='%h %ci %d' | head
845d6ff 2026-07-30 00:24:19 +0200  (tag: v0.83.0)
b4f2936 2026-07-25 14:37:11 +0200  (tag: v0.82.1)
083e616 2026-07-24 08:00:31 +0200  (tag: v0.82.0)
```

发布链路（`package.json:35-47` + `AGENTS.md:131-152`）：

```
npm run version:patch          # npm version -ws --no-git-tag-version + sync-versions.js + lock 刷新
npm run release:local          # 构建 + pack + 在仓库外建隔离的 npm / Bun 安装，跑 5 项 smoke
PI_ALLOW_LOCKFILE_CHANGE=1 npm_config_min_release_age=0 npm run release:patch
```

`AGENTS.md:145` 明写：**"Failures are release blockers unless the user explicitly accepts the risk."**（Node 与 Bun 两条安装路径都要过 `--help / --version / --list-models / -p / 交互` 五项。）

`AGENTS.md:152` 还解释了为什么发布时要临时关掉冷却期：`min-release-age` 的 2 天门禁会挡住刚发布的 workspace 包自身。

---

## 6. 待核实

| # | 疑点 | 为什么没定论 | 怎么核实 |
|---|---|---|---|
| 1 | 项目真实总提交数、总寿命、贡献者数 | 本地是 **shallow clone**，`git log` 只有 162 条、最早 2026-07-24；`git shortlog` 同样不可信 | `git fetch --unshallow` 后重跑；或用 GitHub API `/repos/earendil-works/pi` |
| 2 | `v0.10.0` 之前是否还有更早版本 | CHANGELOG 最后一条就是 `0.10.0 - 2025-11-25`，没有 `0.9.x` | 查 npm registry `npm view @earendil-works/pi-coding-agent time` |
| 3 | `storage/sqlite-node` 为什么 0 个测试文件 | `find packages/storage -name '*.test.ts*'` 无输出，且该包 `devDependencies` 为空、无 `test` script | 看 CI 是否另有覆盖；或看 `packages/agent/test` 里是否间接测了它 |
| 4 | 27 个外部生产依赖里，真正进入 `pi` 二进制的是哪些 | shrinkwrap 142 条是 npm 安装视角；Bun `--compile` 会做 tree-shake，实际内联集合未测 | 分析 `dist/pi` 或 `scripts/agent-treeshake-smoke-entry.ts` |
| 5 | `packages/web-ui` | `.husky/pre-commit:22` 的 browser-smoke 触发条件里出现 `packages/web-ui/*`，但该目录在本 commit **不存在** | 可能是历史遗留或未合并分支；查上游 |
| 6 | `README.md` 提到的 3 种容器化模式 | 本文未展开 | 读 `packages/coding-agent/docs/containerization.md` |
| 7 | `coding-agent` 声明依赖 `pi-client` 但 src 只 1 处 import | 是否为 dead dependency 未确认 | `grep -rn "pi-client" packages/coding-agent/src` 定位那一处用途 |

---

## 7. 最适合上 PPT 的 5 条硬事实

1. **11.2 万行源码，只有 27 个外部生产依赖；agent 内核包 `pi-agent-core`（10,368 行）只依赖 4 个：`diff` / `ignore` / `typebox` / `yaml`。** 没有 zod、没有 lodash、没有 DI 框架，全仓统一 `typebox@1.3.7` 一套 schema。
   （`packages/agent/package.json:31` 起；`python3` 遍历全部 9 个 `package.json` 的 `dependencies` 去重实测）

2. **测试 99,331 行 / 源码 112,232 行 = 0.885，且 `src` 目录里一个测试文件都没有——386 个测试全在各包 `test/` 下。** `pi-tui` 的测试行数（14,164）和它的源码行数（14,184）只差 20 行。
   （`find packages/*/src -name '*.test.ts*' | wc -l` → **0**）

3. **Node 是唯一运行时，Bun 只干一件事：`bun build --compile` 打单文件二进制。** 全仓所有 `package.json` 里 `bun` 只出现 **1 次**，就在 `packages/coding-agent/package.json:38`；CI（`.github/workflows/ci.yml:22-24`）根本不装 Bun。而 `pi` 的 CLI 入口 `src/cli.ts` 只有 **20 行**。

4. **供应链加固 8 道措施，其中最狠的是"lifecycle script 默认拒绝 + 硬编码白名单只放行 2 个包"。** `scripts/generate-coding-agent-shrinkwrap.mjs:13-16` 全文只有 `@google/genai@1.52.0` 和 `protobufjs@7.6.5`，各附一句人肉审计理由；白名单里的包一旦消失也会报错（`:257-260`）。配套还有 `.npmrc:2` 的 `min-release-age=2`（新版本冷却 2 天）和 GitHub Action 按 40 位 SHA 钉死。

5. **246 天发了 267 个版本，平均每天 1.09 次；0.10.0 → 0.83.0，minor 号每 3.4 天涨一次。** 而这个高速迭代的项目把 30 篇文档 + 134 个示例文件**一起打进 npm 包**（`packages/coding-agent/package.json:27` 的 `files` 含 `docs`/`examples`）——发布给用户的 shrinkwrap 只有 142 条依赖记录，而开发期根 lockfile 有 425 条。
