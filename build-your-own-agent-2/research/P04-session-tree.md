# P04：会话是一棵树 —— session 模型与持久化

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | commit 日期 | 2026-08-01 14:38:13 +0200 | `git log -1 --date=iso` |
> | commit 标题 | `fix(tui): normalize source filenames` | 同上 |
> | workspace 版本 | `0.83.0` | `packages/agent/package.json:3` |
> | 取证日期 | 2026-08-02 | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开确认。
> 行号会随上游漂移 —— PPT 引用必须带短 hash **`583f153`**。

---

## 0. 先把地图画对：**三套 session 实现，不是一套**

这是本篇最容易讲错的地方。仓库里同时存在三层东西，名字都叫 session：

| | **① 产品路径** | **② SDK 路径（harness）** | **③ SQLite 后端** |
|---|---|---|---|
| 顶层类型 | `SessionManager`（`packages/coding-agent/src/core/session-manager.ts:855`，**1712 行**） | `Session` 接口 + `StoreSession`（`packages/agent/src/harness/session/session.ts:214` / `:253`，528 行） | `SqliteSessionConnection`（`packages/storage/sqlite-node/src/sqlite/storage/index.ts:68`，349 行） |
| entry 种类 | **9 种** | **11 种** | 同 harness 的 11 种 |
| 存储 | JSONL，**同步** `appendFileSync` | 由 `SessionStore` 决定：memory / JSONL，**异步** | SQLite，异步 + 事务 |
| leaf 指针 | **只在内存里**（`private leafId`，`session-manager.ts:866`） | **持久化**（`leaf` entry / `LeafEntry`） | 持久化在 `sessions.active_leaf_id` 列 |
| 谁在用 | `pi` CLI（`packages/coding-agent/src/main.ts:294/304/319/380/387/393/402`） | `AgentHarness`（`packages/agent/src/harness/agent-harness.ts:179` `private session: Session`） | **目前只有测试**（见 0.1） |

**0.1 关键否定事实（跑命令验证）**：

```bash
$ grep -rn "pi-storage-sqlite" --include="*.json" --include="*.ts" . | grep -v node_modules
package-lock.json:5733:  "name": "@earendil-works/pi-storage-sqlite-node",
packages/storage/sqlite-node/package.json:2: "name": "@earendil-works/pi-storage-sqlite-node",

$ grep -rn "harness/session\|SessionRepository" packages/coding-agent/src packages/server/src packages/client/src
# （无输出）
```

→ **SQLite 后端在本 commit 上没有任何生产消费者**：`createSqliteSessionStore` 的调用点全部在 `packages/agent/test/harness/sqlite-*.test.ts`。同样，`packages/coding-agent` 完全不碰 `packages/agent/src/harness/session/`。

> 上 PPT 的说法：**产品今天跑的是 JSONL + 同步写；SQLite 是同一个 `SessionStore` 接口下正在孵化的第二实现，先有接口再换引擎。**

**0.2 还有一份"未来设计文档"，不要当成代码**：`packages/agent/docs/harness-v2.md` 描述了 v4 格式（每行带 `kind` 标签、多 lane、`leases` 写者租约表）。当前代码里 header 硬编码 `version: 3`、没有 `kind` 字段（`packages/agent/src/harness/session/jsonl-store.ts:41-49`、`:81`），`branch-entries.ts` / `repo.ts` 这两个文档里点名的文件根本不存在。**引用 harness-v2.md 时必须标注"设计稿，未实现"。**

---

## 1. 数据结构：entry 有哪几种，树怎么表达

### 1.1 树的表达方式：**父指针 + 一个 leaf 指针**，没有 children 数组

所有 entry 继承同一个基类（`packages/coding-agent/src/core/session-manager.ts:46-51`）：

```ts
export interface SessionEntryBase {
	type: string;
	id: string;
	parentId: string | null;   // ★★ 唯一的树结构字段
	timestamp: string;
}
```

harness 侧一模一样（`packages/agent/src/harness/types.ts:375-380`，字段名逐字相同）。

- **父指针**：`parentId`。`null` = 根。
- **leaf 指针**：产品侧 `SessionManager.leafId`（`session-manager.ts:866`），harness 侧 `StoreSession.leafId`（`session/session.ts:258`），SQLite 侧 `sessions.active_leaf_id` 列（`packages/storage/sqlite-node/src/sqlite/migrations/001_initial.sql:6`）。
- **children 是现算的**：`getChildren(parentId)` 全表扫 `byId` 过滤（`session-manager.ts:1210-1218`）；`getTree()` 先建 map 再挂父子（`:1310-1348`）。文件里**从不存 children**。

类注释自己就把模型讲清楚了（`session-manager.ts:845-851`）：

> Manages conversation sessions as append-only trees stored in JSONL files. Each session entry has an id and parentId forming a tree structure. The "leaf" pointer tracks the current position. Appending creates a child of the current leaf. Branching moves the leaf to an earlier entry, allowing new branches without modifying history.

### 1.2 产品路径：**9 种 entry**（全枚举 + 定义行号）

union 定义在 `packages/coding-agent/src/core/session-manager.ts:144-153`：

| # | `type` 字面量 | interface | 定义行 | 独有字段 | 进 LLM context？ |
|---|---|---|---|---|---|
| 1 | `"message"` | `SessionMessageEntry` | `:53-56` | `message: AgentMessage` | ✅ |
| 2 | `"thinking_level_change"` | `ThinkingLevelChangeEntry` | `:58-61` | `thinkingLevel` | ❌（只改状态） |
| 3 | `"model_change"` | `ModelChangeEntry` | `:63-67` | `provider` / `modelId` | ❌（只改状态） |
| 4 | `"compaction"` | `CompactionEntry` | `:69-80` | `summary` / `firstKeptEntryId` / `tokensBefore` / `details?` / `usage?` / `fromHook?` | ✅（投影成 compactionSummary 伪消息） |
| 5 | `"branch_summary"` | `BranchSummaryEntry` | `:82-92` | `fromId` / `summary` / `details?` / `usage?` / `fromHook?` | ✅ |
| 6 | `"custom"` | `CustomEntry` | `:104-108` | `customType` / `data?` | ❌（注释 `:102`：`Does NOT participate in LLM context`） |
| 7 | `"label"` | `LabelEntry` | `:111-115` | `targetId` / `label` | ❌ |
| 8 | `"session_info"` | `SessionInfoEntry` | `:118-121` | `name?` | ❌ |
| 9 | `"custom_message"` | `CustomMessageEntry` | `:135-141` | `customType` / `content` / `details?` / `display` | ✅ |

投影规则的唯一权威是 `sessionEntryToContextMessages()`（`:383-408`）：命中 1/4/5/9 才产出消息，其余 `return []`（`:407`）。

另外 header 不是 entry（`SessionHeader`，`:32-39`）：`type:"session"` / `version?` / `id` / `timestamp` / `cwd` / `parentSession?`。`FileEntry = SessionHeader | SessionEntry`（`:156`）。

### 1.3 SDK 路径：**11 种**，多出来的两种是重点

union 在 `packages/agent/src/harness/types.ts:453-464`。相对产品路径多两种：

| 多出的 | 定义行 | 字段 | 意义 |
|---|---|---|---|
| `"active_tools_change"` | `:398-401` | `activeToolNames: string[]` | 工具集变更也进树，`buildContext()` 能还原（`session/session.ts:53-55`） |
| **`"leaf"`** | `:448-451` | `targetId: string \| null` | ★★ **把"当前叶子"本身写成一条 entry**，leaf 指针从此可持久化 |

`CompactionEntry` 在 harness 侧还多了一个 `retainedTail?: AgentMessage[]`（`types.ts:408`），且 `firstKeptEntryId` 变成可选（`:406`）。

`leaf` entry 的语义只有一行（`packages/storage/sqlite-node/src/sqlite/storage/shared.ts`，`leafIdAfterEntry`）：

```ts
export function leafIdAfterEntry(entry: SessionTreeEntry): string | null {
	return entry.type === "leaf" ? entry.targetId : entry.id;
}
```

harness 的 append 队列里对应地写（`packages/agent/src/harness/session/session.ts:343`）：

```ts
this.leafId = entry.type === "leaf" ? entry.targetId : entry.id;
```

---

## 2. 持久化格式：JSONL 还是 SQLite？写入同步还是异步？

### 2.1 三个后端并存，接口统一

`SessionStore` 接口 6 个方法（`packages/agent/src/harness/types.ts:552-563`）：`create` / `load` / `list` / `appendEntry` / `delete` / `fork`，并且 `extends AsyncDisposable`。三个实现：

| 后端 | 文件 | 行数 | 写入语义 |
|---|---|---|---|
| memory | `packages/agent/src/harness/session/memory-store.ts` | 130 | `state.entries.push(entry)`（`:51`） |
| JSONL | `packages/agent/src/harness/session/jsonl-store.ts` | 438 | `await this.fs.appendFile(...)`（`:277`）**异步** |
| SQLite | `packages/storage/sqlite-node/src/sqlite/session-store.ts` | 276 | 一条 entry 一个事务（`storage/index.ts:302`） |

产品路径的 `SessionManager` 不实现这个接口，是独立的第四份实现。

### 2.2 产品路径：**JSONL + 全同步**

`packages/coding-agent/src/core/session-manager.ts` 顶部导入的全是 `fs` 同步 API（`:4-15`：`appendFileSync` / `closeSync` / `existsSync` / `mkdirSync` / `openSync` / `readdirSync` / `readSync` / `statSync` / `writeFileSync`）。

```bash
$ grep -c "appendFileSync\|writeFileSync\|openSync\|readSync\|existsSync\|statSync\|closeSync\|mkdirSync\|readdirSync" \
    packages/coding-agent/src/core/session-manager.ts
40
$ grep -c "await " packages/coding-agent/src/core/session-manager.ts
10          # 10 处 await 全在 static list/listAll 的目录扫描里
```

**为什么选同步**：写路径 `_appendEntry`（`:1044-1049`）是同步函数，被 agent 事件回调直接调用；一旦异步化，"消息落盘"与"UI 渲染"之间就出现窗口，崩溃时会丢尾。代码用同步换了一个强不变式：**`appendMessage()` 返回时，这一行已经在磁盘上**。

```ts
private _appendEntry(entry: SessionEntry): void {   // :1044
	this.fileEntries.push(entry);
	this.byId.set(entry.id, entry);
	this.leafId = entry.id;        // ★ 叶子指针前移
	this._persist(entry);
}
```

### 2.3 一个很有产品味道的细节：**文件到第一条 assistant 消息才创建**

`_persist`（`session-manager.ts:1015-1042`）：

```ts
const hasAssistant = this.fileEntries.some((e) => e.type === "message" && e.message.role === "assistant");
if (!hasAssistant) {
	if (this.flushed) appendFileSync(this.sessionFile, `${JSON.stringify(entry)}\n`);   // :1021
	else this.flushed = false;                                                          // :1024
	return;
}
if (!this.flushed) {
	const fd = openSync(this.sessionFile, "wx");        // :1030 "wx" = 存在即报错，不覆盖
	for (const e of this.fileEntries) writeFileSync(fd, `${JSON.stringify(e)}\n`);      // :1033
	this.flushed = true;
} else {
	appendFileSync(this.sessionFile, `${JSON.stringify(entry)}\n`);                     // :1040
}
```

效果：`pi` 起来敲了半句就退出 → **磁盘上不留空 session 文件**；第一条 assistant 回复到达时，把内存里攒的所有 entry 一次性 flush 成完整文件。

文件命名（`:952-953`、目录编码 `:476-481`）：

```
~/.pi/agent/sessions/--<cwd 去斜杠替换成 - >--/<ISO时间戳 : . 换成 - >_<sessionId>.jsonl
```

harness 的 JSONL store 用**完全相同**的编码规则（`jsonl-store.ts:173-175` `encodeCwd`、`:187` 文件名），这是两条路径唯一刻意对齐的地方。

### 2.4 id 生成：session id 和 entry id 用的不是同一个东西

| | 生成方式 | 行号 |
|---|---|---|
| session id | `uuidv7()`（完整） | `session-manager.ts:208-210` |
| entry id | `randomUUID().slice(0, 8)`，**碰撞重试 100 次**，失败退回完整 uuid | `session-manager.ts:221-228` |
| harness entry id | `uuidv7().slice(-8)`，同样重试 100 次 | `session/session.ts:325-331` |

→ entry id 只有 8 个十六进制字符，是为了 `/tree` 选择器和日志里肉眼可读；碰撞靠 `byId.has()` 现场检测。

### 2.5 版本与迁移：**只有 3 个版本，v1→v2 是"给线性日志补上树"**

`CURRENT_SESSION_VERSION = 3`（`session-manager.ts:30`）。

- `migrateV1ToV2`（`:231-257`）：给每条 entry **补发 `id`，并把 `parentId` 设成前一条的 id** —— 也就是把一条线**直接接成一条单链树**；顺带把 `firstKeptEntryIndex`（下标）翻译成 `firstKeptEntryId`（指针）。
- `migrateV2ToV3`（`:260-275`）：`role: "hookMessage"` → `role: "custom"`。
- 触发点：`_setSessionFile` 里 `if (migrateToCurrentVersion(this.fileEntries)) this._rewriteFile();`（`:917-919`）。**这是全代码库唯一一处会重写整个 session 文件的地方**（`_rewriteFile`，`:979-989`，`openSync(..., "w")`）。

> 上 PPT 的点：**"会话是树"不是从第一天就有的。v1 是线性 JSONL，v2 才引入 `id/parentId`，迁移逻辑就是把老的线性日志当成"退化的树"重新贴指针。**

harness 侧对 v1/v2 一律拒绝：`parseHeader` 里 `header.version !== 3` 直接抛 `unsupported session version`（`jsonl-store.ts:81-86`）。

### 2.6 SQLite 后端长什么样

`packages/storage/sqlite-node/src/sqlite/migrations/`，两个迁移文件，**7 张表 + 10 个索引**（`grep -c "CREATE TABLE"` = 6 + 1；`grep -c "CREATE .*INDEX"` = 10 + 0）：

| 表 | 用途 | 出处 |
|---|---|---|
| `sessions` | 一行一个 session，含 `active_leaf_id`（**leaf 指针持久化成一列**） | `001_initial.sql:1-8` |
| `session_entries` | 一行一个 entry，`(session_id, id)` 主键，`entry_seq` 唯一索引 | `001_initial.sql:14-25` |
| `session_sequences` | 每 session 的 `next_seq` | `001_initial.sql:33-36` |
| `branch_entries` | **分支读缓存**：`(session_id, branch_id, entry_id, entry_seq)` | `001_initial.sql:38-44` |
| `session_materialized` | 每 session 一行 JSON 汇总（消息数、token、成本、当前模型） | `001_initial.sql:52-55` |
| `entry_materialized` | 目前只物化 `label`（`session-materialized.ts:329-336`） | `001_initial.sql:57-63` |
| `branch_tips` | `PRIMARY KEY (session_id, tip_id)` + `UNIQUE (session_id, branch_id)` | `002_branch_tips.sql:1-8` |

PRAGMA 配置（`session-store.ts:34-36`）：`journal_mode=WAL` / `synchronous=FULL` / `busy_timeout=5000`。

一次 `appendEntry` 在**一个事务**里做 6 件事（`storage/index.ts:271-300`）：取 seq → insert entry → advance seq → update 汇总 → insert 物化行 → `UPDATE sessions SET active_leaf_id` → 更新分支缓存。

---

## 3. 分叉 / 回退 / rewind / branch：改指针还是重写文件？

**答案是三种都有，取决于哪一层。**下表是全篇最该上 PPT 的一张：

| 操作 | 入口 | 实现 | **改指针还是写文件** |
|---|---|---|---|
| `/tree` 导航（无摘要） | `interactive-mode.ts:4722` `showTreeSelector()` → `agent-session.ts:3058` | `SessionManager.branch(id)`（`session-manager.ts:1360-1365`） | **纯内存改指针**，一个字节都不写 |
| `/tree` 导航到根 | `agent-session.ts:3055` | `resetLeaf()`（`:1372-1374`） | 纯内存，`leafId = null` |
| `/tree` + 摘要 | `agent-session.ts:3040` | `branchWithSummary()`（`:1381-1405`） | 改指针 **+ 追加一条 `branch_summary` entry** |
| `/fork`（重编某条 user 消息） | `interactive-mode.ts:4679` → `agent-session-runtime.ts:262` | `createBranchedSession(targetLeafId)`（`:1412-1512`） | **新建一个 session 文件** |
| `/clone` | `interactive-mode.ts:4709` `fork(leafId, {position:"at"})` | 同上 | 新文件 |
| `--fork`（跨目录） | `main.ts:304` | `SessionManager.forkFrom()`（`:1579-1630`） | 新文件，逐行复制全部 entry（`:1623-1627`） |
| harness `navigateTree` | `agent-harness.ts:842-931` | `session.moveTo()`（`session/session.ts:497-518`） | **追加一条 `leaf` entry**（`setLeafId`，`:354-361`） |
| harness `repository.fork` | `repository.ts:60-70` | `store.fork(...)` | 新文件 / 新 session 行 |

### 3.1 `branch()` 就三行

```ts
branch(branchFromId: string): void {                       // session-manager.ts:1360
	if (!this.byId.has(branchFromId)) throw new Error(`Entry ${branchFromId} not found`);
	this.leafId = branchFromId;
}
```

注释（`:1354-1359`）明写：`Existing entries are not modified or deleted.`

**下一条 `appendXXX()` 的 `parentId` 就是这个新 leaf**（`appendMessage`，`:1058-1064`）：

```ts
const entry: SessionMessageEntry = {
	type: "message", id: generateId(this.byId), parentId: this.leafId, timestamp: ..., message,
};
```

→ 分叉在物理上就是"同一个 parentId 出现了第二个孩子"。旧分支永远躺在文件里。

### 3.2 `/fork` 会新建文件，而且要**重链父指针**

`createBranchedSession`（`:1412-1512`）的精髓在于 label 处理（`:1419-1428`）：

```ts
// Because labels are real tree entries, later entries can be children of labels;
// removing labels requires re-chaining the retained path to avoid orphaned subtrees.
const pathWithoutLabels: SessionEntry[] = [];
let pathParentId: string | null = null;
for (const entry of path) {
	if (entry.type === "label") continue;
	pathWithoutLabels.push({ ...entry, parentId: pathParentId });   // :1426 重链
	pathParentId = entry.id;
}
```

新 header 的 `parentSession` 指向上一个文件（`:1435-1442`），**session 之间也构成一棵树**（文件级的父指针）。

新文件同样遵守 2.3 的"有 assistant 才落盘"规则（`:1482-1488`）——注释里直接点名这是在修一个 duplicate-header bug。

### 3.3 **产品路径没有"回退/rewind"这种删除操作**

全仓搜不到删 entry 的路径：`getEntries()` 的注释就是契约（`session-manager.ts:1296-1300`）：

> The session is append-only: use appendXXX() to add entries, branch() to change the leaf pointer. **Entries cannot be modified or deleted.**

唯一改写文件的是 `_rewriteFile()`，只在版本迁移（`:917-919`）和 `createBranchedSession` 落新文件（`:1484`）时调用。

### 3.4 ⚠️ 一个真实的、可以当"设计教训"讲的缺口

**产品路径的 leaf 指针不持久化。**

- `branch()` 只改内存（`:1364`）。
- 重开文件时 `_buildIndex()` 把 leaf 恢复成**文件里最后一条 entry**（`:958-977`）：
  ```ts
  for (const entry of this.fileEntries) {
      if (entry.type === "session") continue;
      this.byId.set(entry.id, entry);
      this.leafId = entry.id;     // :966 —— 按"文件顺序"取最后一条，不是按树
  }
  ```

推论（严格）：`/tree` 跳到旧节点后，**如果不再追加任何 entry 就退出**，下次 resume 会回到文件末尾那条 entry 所在的分支，导航结果丢失。反过来，只要之后写了任何一条（新消息 / `branch_summary` / `label`），它就带着新的 `parentId` 落到文件末尾，重建时自然落回正确分支——所以日常用不出问题。

harness 侧就是为了堵这个洞才发明了 `LeafEntry`（`types.ts:448-451`）：`moveTo()` 会真的写一条 `{type:"leaf", targetId}` 进去（`session/session.ts:354-361`、`:504`），`array-session-reader.ts:24` 重建时 `leafId = entry.type === "leaf" ? entry.targetId : entry.id`。SQLite 侧更直接，`active_leaf_id` 就是一列。

> 上 PPT 的点：**同一个团队在两代实现里对同一个问题给了三种答案：内存变量 → 追加一条 leaf 事件 → 一个可更新的列。这是"事件日志 vs 可变状态"取舍的活教材。**

---

## 4. 恢复一个 session 的完整流程（逐跳行号）

以 `pi --continue` 为例，产品路径：

| # | 步骤 | 位置 |
|---|---|---|
| 1 | CLI 分派 | `packages/coding-agent/src/main.ts:386-388` `if (parsed.continue) return SessionManager.continueRecent(cwd, sessionDir)` |
| 2 | 找最近文件 | `session-manager.ts:1557-1565` → `findMostRecentSession(dir, ...)`（`:635`） |
| 3 | 构造 | `session-manager.ts:868-888`（private constructor）→ `_setSessionFile(file)`（`:895`） |
| 4 | 整文件读入 | `:898` `loadEntriesFromFile(this.sessionFile)`（实现 `:514-556`）：1 MiB 缓冲 + `StringDecoder` 手工切行；**坏行静默跳过**（`parseSessionEntryLine`，`:503-511`）；首行不是合法 header 就整个返回 `[]`（`:549-553`） |
| 5 | 取 sessionId | `:914-915` 从 header 拿，缺失就新生成 |
| 6 | 版本迁移 | `:917-919` `migrateToCurrentVersion()` → 命中就 `_rewriteFile()` |
| 7 | **建索引 + 定 leaf** | `:921` `_buildIndex()`（`:958-977`）：填 `byId`、`labelsById`、`labelTimestampsById`，`leafId = 最后一条 entry`（`:966`） |
| 8 | 标记已落盘 | `:922` `this.flushed = true` |
| 9 | 算上下文 | `sdk.ts:188` `const existingSession = sessionManager.buildSessionContext()` |
| 10 | 回溯路径 | `session-manager.ts:1284-1286` → `buildSessionContext(entries, leafId, byId)`（`:461-470`）→ `buildSessionPath()`（`:334-360`）：沿 `parentId` 一路 push 到根，最后 `reverse()` |
| 11 | 恢复状态 | `getSessionContextSettings(path)`（`:362-377`）：路径上最后一次 `thinking_level_change` / `model_change` / assistant 消息决定 thinkingLevel 与 model |
| 12 | **压缩感知裁剪** | `buildContextEntries()`（`:418-454`）：取路径上**最后一个** compaction（`:426-430`），输出 = `[compaction] + [firstKeptEntryId 起到 compaction 之前] + [compaction 之后全部]`（`:441-452`） |
| 13 | 投影成消息 | `:468` `.flatMap(sessionEntryToContextMessages)`（`:383-408`），顺带修补 `content == null` 的历史脏数据（`:388-393`） |
| 14 | 恢复模型 | `sdk.ts:196-204`：`modelRuntime.getModel(...)`，失败给 `modelFallbackMessage` |
| 15 | **注入 agent** | `sdk.ts:362-367` `if (hasExistingSession) { agent.state.messages = existingSession.messages; ... }` |
| 16 | 构造 AgentSession | `sdk.ts:376` `new AgentSession({ agent, sessionManager, ... })` |

注意第 15 步的 `else` 分支（`sdk.ts:368-374`）：新 session 会**主动写入** `model_change` + `thinking_level_change` 两条 entry，"为了 resume 时能还原"——这就是第 11 步的数据来源。

**harness 路径的对应流程**（更短，因为读被下推到 store）：
`repository.open(metadata)`（`repository.ts:48-50`）→ `store.load()` → `createSessionFromReader()`（`session/session.ts:522-528`）→ `(await reader.readHead()).leafId` → 之后每次 `getBranch()` 都走 `reader.readPathToRootOrCompaction(leafId)`（`:288-290`）。

harness 的路径回溯比产品路径**多一个早停**（`array-session-reader.ts:48-68`）：

```ts
while (current) {
	path.push(current);
	if (stopAtEntryId !== null && current.id === stopAtEntryId) break;
	if (current.type === "compaction") {
		if (current.retainedTail) break;                       // :59 有内联尾巴 → 立刻停
		stopAtEntryId = current.firstKeptEntryId ?? null;       // :60 否则回溯到保留边界为止
	}
	...
}
return path.reverse();
```

→ **产品路径先走完整条根路径再裁剪（O(全长)），harness 遇到 compaction 边界就不再往上走（O(有效上下文)）。** 这是两代实现的关键复杂度差。

---

## 5. 最近的性能改动：三个 commit 讲一个故事

`git log --oneline -50` 里 24 条与 session/sqlite 相关。三条是真正的性能修复：

### 5.1 `2366649` — 打开 session 不再数条目（2026-08-01 01:39:12 +0300）

`fix(agent): avoid counting entries when opening sessions`

从 `SessionHead` 里**删掉了 `entryCount` 字段**（`types.ts` 现状 `:537-539` 只剩 `leafId`）。SQL 里那个 `SELECT COUNT(*) FROM session_entries` 子查询被摘掉：

```diff
 `SELECT
     s.active_leaf_id,
-    (SELECT COUNT(*) FROM session_entries AS e WHERE e.session_id = s.id) AS entry_count,
     (s.active_leaf_id IS NULL OR EXISTS (...)) AS active_leaf_exists
  FROM sessions AS s WHERE s.id = ?`
```

数组后端同样从 `readHead` 里去掉了 `entries.length`（`array-session-reader.ts:31-37` 现状）。

> **打开一个 session 从"和条目数成正比"变成"一次主键查找"。** 而且这个字段根本没人用——删字段比优化查询便宜。

### 5.2 `5758361` — SQLite 会话操作线性化（2026-08-01 01:50:06 +0300）

合并进 `4488ad5 Merge pull request #7410 from earendil-works/fix/sqlite-session-linear-time`。两个改动：

**(a) `path.unshift` → `path.push` + `reverse()`**（现状 `storage/index.ts:143`、`:150`）：

```diff
-  path.unshift(current);
+  path.push(current);
...
-  return path;
+  return path.reverse();
```

`Array.unshift` 每次都要搬移整个数组 → **O(depth²)**；改成尾插 + 一次反转 → **O(depth)**。一行改动，标题里的 "linear time" 就是指这个。

**(b) 事务失败不再靠"手工回滚内存"**：旧代码在 `catch` 里把 `materializedState` / `byId` / `currentLeafId` / `activeBranchId` 四个字段逐一恢复；新代码改成**先算 next 值，事务提交成功后才赋值**（`storage/index.ts:262-267` 构造 `nextMaterializedState`，`:303-304` 提交后才写回）。`catch` 块从 4 行恢复变成纯抛错（`:305-308`）。

### 5.3 `e92bf60` — 分支缓存可扩展化（2026-08-01 10:08:56 +0300）

合并进 `a116523 Merge pull request #7431 from earendil-works/refactor/sqlite-branch-cache`。**+605 / −110**，新增 `branch-cache.ts`（199 行）、`002_branch_tips.sql`（12 行）、`sqlite-branch-cache.test.ts`（224 行）。

问题：改之前每次分叉都调 `materializeBranch()` **把整条根路径重新物化一遍**（旧代码 `for (const entry of ...) INSERT INTO branch_entries`）。深会话上每次分叉都是 O(n) 写。

新方案的两个不变式（`branch-cache.ts` + `002_branch_tips.sql:1-8` 的 `PRIMARY KEY (session_id, tip_id)`）：

1. **每条 entry 至少属于一个 branch**；一个 branch 存的是**完整根路径**。
2. **tip 唯一**：新 entry 永远在末尾，所以没有两个 branch 共享 tip → "有没有分支以 X 结尾" 是一次主键点查。

于是 `appendEntryToBranchCache`（`branch-cache.ts:138-199`）分三种情况：

| 情况 | 代价 | 行号 |
|---|---|---|
| 根 entry | 建新 branch，写 1 行 | `:146-155` |
| **父就是某分支的 tip（绝大多数情况）** | `UPDATE branch_tips SET tip_id`，**写 1 行** | `:157-163` → `extendBranch` `:121-136` |
| 父不是 tip（真分叉） | 复制 `entry_seq <= parent.seq` 的行成新 branch + 1 行 + 1 tip | `:184-198` |

修复（cache 失配）才走 `rebuildCachedBranch()`（`:72-119`），用 **`WITH RECURSIVE path(...)`** 在 SQL 里一次递归出整条根路径（`:92-105`），包在 `SAVEPOINT rebuild_branch_cache` 里（`:78`、`:109`、`:112-113`）。

读侧 `readPathToRootOrCompaction`（`storage/index.ts:74-123`）也因此变成：点查 branch（`:76`）→ 只取 compaction 类型的行定位起点（`:78-113`）→ **区间扫 `entry_seq BETWEEN startSeq AND leafSeq`**（`branch-cache.ts:26-41`）。校验 `isValidCachedPath()`（`:153-164`）逐条核对 `parentId` 链，不一致就 `repairBranchCache()` 回退到权威父指针（`:121-122`、`:125-134`）。

> **缓存是可丢弃的**：`branch_entries` / `branch_tips` 全是从 `parent_id` 派生的；`002_branch_tips.sql:10-11` 直接 `DELETE FROM branch_tips; DELETE FROM branch_entries;` 把旧缓存清空重建。上 PPT 一句话：**父指针是真相，分支表只是索引。**

### 5.4 同批次还有两条结构性提交（不是性能，但同源）

- `62f3c61 feat(agent): add per-session store queues` → `KeyedOperationQueue`（`packages/agent/src/harness/session/keyed-operation-queue.ts`，69 行）：**按 session key 串行，跨 session 并行**，默认并发上限 4（`jsonl-store.ts:39` `DEFAULT_MAX_CONCURRENT_OPERATIONS = 4`）；`list()` 走 `enqueueBarrier`（`:244`）等所有 key 排空。
- `9c3b271 fix(agent): make session search query-only` / `977ec83 refactor/remove-session-search-index` → 搜索退化成扫描（`repository.ts:89-101` `findSessionEntryMatches`，`JSON.stringify(entry).toLowerCase().includes(...)`），索引被整个删掉。

---

## 6. 严格结论：「会话是树不是线」到底成立到什么程度

分四条讲，每条给判定。

### ✅ 成立①：**数据模型上是彻底的树**

`parentId` 是唯一结构字段，`getTree()`（`session-manager.ts:1310-1348`）真的会产出多叉结构，且显式处理**多根**：`parentId === null` 或 `parentId === entry.id` 是根（`:1325`），**父找不到的孤儿也当根**（`:1331-1333`）。子节点按 timestamp 排序，并且用显式栈避免深树爆栈（`:1339-1345`）。

### ✅ 成立②：**append-only，旧分支永不删除**

`branch()` 注释（`:1354-1359`）与 `getEntries()` 注释（`:1296-1300`）都写死了 "not modified or deleted"。全仓没有删 entry 的代码路径。压缩也不删——`CompactionEntry` 只是让**读路径**跳过旧条目（`buildContextEntries`，`:441-452`）。

### ⚠️ 打折①：**送进 LLM 的永远是一条线**

`buildSessionPath()`（`:334-360`）从 leaf 沿 `parentId` 单向回溯，`while (current)` 每步只取一个父。**树只用于存储与导航；推理时永远退化成根→leaf 的单链。** 兄弟分支的内容想进上下文，只有一条路：`branch_summary` entry（`:1381-1405`）把被抛弃的那条路径**摘要成一段文本**再挂到新位置。

### ⚠️ 打折②：**树只在单个文件内成立；`/fork` 会把树切成两个文件**

`/fork` 走 `createBranchedSession()`（`agent-session-runtime.ts:318`）→ 抽出根到 target 的路径写进**新文件**，新 header 的 `parentSession` 指向旧文件（`session-manager.ts:1441`）。于是存在**两层树**：文件内的 entry 树 + 文件间的 session 树。而 `/tree` 选择器（`interactive-mode.ts:4722-4723`）只能看到**当前文件**的那棵。

换句话说：**在一个 session 文件里，`/tree` 能真正跳分支；一旦 `/fork`，分叉就升格成两个文件，你在新文件里再也看不见兄弟分支。**

### ⚠️ 打折③：**"当前在树的哪个位置"在产品路径上不是持久状态**

见 3.4：`leafId` 是内存字段，重建时按文件顺序取最后一条（`:966`）。**树的形状是持久的，树上的游标不是。** harness 用 `LeafEntry`、SQLite 用 `active_leaf_id` 列各自补了这一刀。

### 一句话总结

> **pi 的 session 是"存储层的树 + 推理层的线"：`parentId` 让历史成为一棵永不删枝的树，但每次调模型时只沿一条根→叶路径线性化。树的价值不在于让模型看到分支，而在于让人可以零成本地跳回去重来。**

---

## 最适合上 PPT 的 5 条硬事实

1. **树只靠一个字段撑起来。** `SessionEntryBase` 只有 4 个字段，结构信息全在 `parentId: string | null`（`packages/coding-agent/src/core/session-manager.ts:46-51`）。文件里不存 children，`getChildren()` 是遍历 `byId` 现算的（`:1210-1218`）。产品路径 **9 种** entry（union `:144-153`），SDK 路径 **11 种**（`packages/agent/src/harness/types.ts:453-464`），多出的是 `active_tools_change` 和 **`leaf`**。

2. **产品今天用的是 JSONL + 全同步写，而且第一条 assistant 消息之前不落盘。** `session-manager.ts` 有 40 处同步 fs 调用、只有 10 处 `await`（全在目录扫描）；`_persist()` 的 `hasAssistant` 判断（`:1018-1027`）让"敲一半就退出"不留空文件，首条 assistant 到达时用 `openSync(file, "wx")` 一次性 flush（`:1030-1034`）。**SQLite 后端已经写完（7 表 10 索引）但本 commit 上零生产消费者**（`grep -rn "pi-storage-sqlite"` 只命中它自己的 package.json 和 lockfile）。

3. **分叉有三种物理形态，讲清楚就赢了。** `/tree` 导航 = 纯内存改 `leafId`，一个字节不写（`branch()`，`:1360-1365`，函数体三行）；`/tree`+摘要 = 改指针 + 追加一条 `branch_summary`（`:1381-1405`）；`/fork` = **新建一个 session 文件**并把 label 摘掉后重链 `parentId`（`createBranchedSession`，`:1412-1512`，重链在 `:1422-1428`）。**从头到尾没有任何删除操作**——`getEntries()` 注释就是契约：`Entries cannot be modified or deleted`（`:1296-1300`）。

4. **两次真实的复杂度修复，都在 2026-08-01 当天。** `5758361 fix(agent): make SQLite session operations linear` 把根路径回溯的 `path.unshift()` 换成 `path.push()` + `reverse()`（`storage/index.ts:143/150`），O(depth²) → O(depth)；`e92bf60 fix(agent): make SQLite branch caching scalable`（+605/−110）新增 `branch_tips` 表，让"父是某分支的 tip"成为一次主键点查，**常见的线性追加从"重新物化整条根路径"降到写 1 行**（`branch-cache.ts:157-163`）。附赠一条：`2366649` 直接从 `SessionHead` 里**删掉 `entryCount` 字段**——打开 session 不再 `COUNT(*)`。

5. **"会话是树"成立，但要打两个折。** ① 送进 LLM 的永远是一条线：`buildSessionPath()` 沿 `parentId` 单链回溯（`:334-360`），兄弟分支只能靠 `branch_summary` 变成一段文本才进得来。② **树的形状持久，树上的游标不持久**：`branch()` 只改内存 `leafId`，重开文件时 `_buildIndex()` 把 leaf 恢复成"文件里最后一条 entry"（`:966`）——harness 为此专门发明了 `leaf` entry 类型（`types.ts:448-451`），SQLite 则把它做成 `sessions.active_leaf_id` 一列。**同一个问题，三代实现给了三种答案。**
