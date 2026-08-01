# P08：TUI —— 终端就是这个产品的界面

> **取证基线（务必随引用一起上 PPT）**
>
> | 项 | 值 | 出处 |
> |---|---|---|
> | 仓库 | `pi-mono`（`@earendil-works/pi-*`） | `packages/tui/package.json:35` |
> | commit | `583f153d502aa8e958eefdb9af0fbd3344e68f95` | `git rev-parse HEAD` |
> | 版本 | `0.83.0` | `packages/tui/package.json:3` |
> | 取证日期 | 2026-08-02 | — |
> | 本地路径 | `/Users/overkazaf/playground/research/pi/pi-mono` | — |
>
> 下文所有 `路径:行号` 均相对仓库根 `pi-mono/`，均已在上述 commit 上实际打开验证。
> 行号会随上游提交漂移 —— PPT 上引用必须带短 hash `583f153`。

---

## 0. 先给规模数字（都是实测，命令附上）

```bash
$ find packages/tui/src -name '*.ts' | wc -l
37
$ find packages/tui/src -name '*.ts' | xargs wc -l | tail -1
14184 total
$ find packages/tui/test -name '*.ts' | xargs wc -l | tail -1
14839 total
$ ls packages/tui/src/components/*.ts | wc -l
17
$ grep -ro '\\x1b\[[^"]*' packages/tui/src --include='*.ts' | wc -l
226
```

四个数字，PPT 上放一张表就够：

| 项 | 数值 |
|---|---|
| `src` 源码 | **14 184 行** / 37 个文件 |
| `test` 测试 | **14 839 行** / 36 个文件（**测试比源码还多 655 行**） |
| 组件文件 | 17 个 |
| 硬编码 ANSI 转义序列出现次数 | 226 处 |
| 运行时依赖 | **2 个**：`get-east-asian-width@1.6.0`、`marked@18.0.5`（`packages/tui/package.json:38-41`） |

最大的三个文件（`wc -l` 实测）：

| 文件 | 行数 | 干什么 |
|---|---|---|
| `packages/tui/src/components/editor.ts` | 2 351 | 多行编辑器（软换行、undo、kill-ring、粘贴折叠、自动补全） |
| `packages/tui/src/keys.ts` | 1 401 | 按键解析（Kitty 协议 / modifyOtherKeys / legacy 三套） |
| `packages/tui/src/utils.ts` | 1 303 | 宽度计算、ANSI 感知的切片/换行/截断 |
| `packages/tui/src/tui.ts` | 1 223 | `TuiBase`：组件树、焦点、overlay、渲染调度 |

---

## 1. 渲染模型：**可变的、增量差分的、行级的**

### 1.1 结论先行

- **不是 append-only（提交式）**。屏幕上任何一行都可能被就地改写。
- **不是每帧全屏重绘**。默认路径是"只重画 firstChanged..lastChanged 这一段"。
- 但**有 5 个明确的降级到全量重绘的触发条件**，每一个都在代码里有 `logRedraw(reason)`。

package.json 的 description 自己就写了（`packages/tui/package.json:4`）：

> `"Terminal User Interface library with differential rendering for efficient text-based applications"`

### 1.2 组件契约：`render(width) => string[]`

`packages/tui/src/tui.ts:23-47`，整个渲染体系只有 4 个成员：

```ts
export interface Component {
	render(width: number): string[];        // :29  给宽度，还我若干行字符串
	handleInput?(data: string): void;       // :34
	wantsKeyRelease?: boolean;              // :40
	invalidate(): void;                     // :46
}
```

**没有虚拟 DOM、没有 cell buffer、没有 (x,y) 坐标系。**组件产出的就是"带 ANSI 的字符串数组"。整棵树的合成 = `Container.render()` 把孩子的行**首尾相接**（`tui.ts:235-244`）：

```ts
render(width: number): string[] {
	const lines: string[] = [];
	for (const child of this.children) {
		const childLines = child.render(width);
		for (const line of childLines) lines.push(line);
	}
	return lines;
}
```

硬约束写在 `packages/coding-agent/docs/tui.md:24`：

> `render(width)` — Return array of strings (one per line). Each line **must not exceed `width`**.

**违反了会崩**，而且是刻意崩的 —— `packages/tui/src/tui-main-screen.ts:413-439`：

```ts
if (!isImage && visibleWidth(line) > width) {
	const crashLogPath = path.join(this.logDirectory, "pi-crash.log");
	fs.writeFileSync(crashLogPath, crashData);   // 把所有行连宽度一起 dump
	this.stop();                                  // 先恢复终端状态
	throw new Error([
		`Rendered line ${i} exceeds terminal width (${visibleWidth(line)} > ${width}).`,
		"This is likely caused by a custom TUI component not truncating its output.",
		"Use visibleWidth() to measure and truncateToWidth() to truncate lines.",
	].join("\n"));
}
```

> 上 PPT 的点：**宁可崩掉并写 crash log，也不让一行超宽把终端的自动折行搞乱**。因为一旦终端自己折了行，差分渲染赖以定位的"行号 ↔ 屏幕行"映射就永久错位了。

### 1.3 两个渲染后端，共享一个 `TuiBase`

| | `TuiMainScreen` | `TuiAltScreen` |
|---|---|---|
| 文件 | `packages/tui/src/tui-main-screen.ts`（552 行） | `packages/tui/src/tui-alt-screen.ts`（805 行） |
| 屏幕 | 主屏 + 终端原生 scrollback | 备用屏（`\x1b[?1049h`，`tui-alt-screen.ts:32`） |
| 滚动归谁 | 终端 | **应用自己**（`ScrollView`、鼠标滚轮、OSC 133 跳转） |
| 差分粒度 | 逻辑行区间 `[firstChanged, lastChanged]` | 屏幕行逐行比对（0..height-1） |
| 谁在用 | `uiMode: "regular"`（**默认**） | `uiMode: "fullscreen"` |

选择点（**composition root**）在 `packages/coding-agent/src/modes/interactive/interactive-mode.ts:340-346`：

```ts
export function createInteractiveTui(options: InteractiveTuiOptions): TUI {
	const terminal = options.terminal ?? new ProcessTerminal();
	if (options.uiMode === "fullscreen") {
		return new TuiAltScreen(terminal, options.showHardwareCursor, options.logDirectory, { openUrl: openBrowser });
	}
	return new TuiMainScreen(terminal, options.showHardwareCursor, options.logDirectory);
}
```

默认值（`packages/coding-agent/src/core/settings-manager.ts:1129`）：

```ts
return this.settings.uiMode === "fullscreen" ? "fullscreen" : "regular";
```

→ **默认跑的是主屏差分渲染**，历史留在终端 scrollback 里，能用鼠标选、能用终端自己的搜索。

### 1.4 主屏差分算法（`tui-main-screen.ts:146-513`，一个 368 行的 `doRender()`）

**步骤 1｜整树渲染**（`:163`）：

```ts
let newLines = this.render(width);
```

注意：**每一帧都把整棵组件树重新 render 一遍**。省的不是"计算行"，是"写终端的字节"。

**步骤 2｜合成 overlay**（`:166-168`）→ **步骤 3｜抠出光标标记**（`:171`）→ **步骤 4｜给每行补 reset**（`:173`）。

**步骤 5｜五个降级到全量重绘的判定**，逐条列（这张表本身就是一页 PPT）：

| # | 条件 | 行号 | 是否 clear scrollback |
|---|---|---|---|
| ① | 首次渲染（`previousLines.length === 0`） | `:229-233` | **否**（假定屏幕干净） |
| ② | 终端**宽度**变了 | `:236-240` | 是 |
| ③ | 终端**高度**变了 **且不是 Termux** | `:245-249` | 是 |
| ④ | 内容缩短到低于历史高水位 `maxLinesRendered`，且没有 overlay | `:254-258` | 是 |
| ⑤ | 第一个变化行在上一帧视口顶部之上（`firstChanged < prevViewportTop`） | `:348-352` | 是 |

③ 的注释是整份代码里最有画面感的一段（`:242-244`）：

```
// Height changes normally need a full re-render to keep the visible viewport aligned,
// but Termux changes height when the software keyboard shows or hides.
// In that environment, a full redraw causes the entire history to replay on every toggle.
```

→ **Android 手机上弹出软键盘 = 终端高度变化 = 整段历史重播一遍**。为这一个场景专门开了个 `isTermuxSession()`（`:42-44`，判 `process.env.TERMUX_VERSION`）。

**步骤 6｜差分**（`:260-286`）—— 朴素的首尾扫描，不是 Myers diff：

```ts
for (let i = 0; i < maxLines; i++) {
	const oldLine = i < this.previousLines.length ? this.previousLines[i] : "";
	const newLine = i < newLines.length ? newLines[i] : "";
	if (oldLine !== newLine) {
		if (firstChanged === -1) firstChanged = i;
		lastChanged = i;
	}
}
```

**步骤 7｜只写 `[firstChanged, renderEnd]`**（`:385-442`）：

```ts
const renderEnd = Math.min(lastChanged, newLines.length - 1);
for (let i = firstChanged; i <= renderEnd; i++) {
	if (i > firstChanged) buffer += "\r\n";
	buffer += "\x1b[2K";     // 清当前行
	buffer += line;
}
```

注释直接说了为什么不是"从 firstChanged 一直画到底"（`:383-384`）：

> "Only render changed lines (firstChanged to lastChanged), not all lines to end. This reduces flicker when only a single line changes (e.g. spinner animation)."

**步骤 8｜整个 buffer 一次 write，外面包同步输出**（`:356`、`:463`、`:495`）：

```ts
let buffer = "\x1b[?2026h";   // Begin Synchronized Update (CSI 2026)
… 拼接所有移动/清行/内容 …
buffer += "\x1b[?2026l";      // End
this.terminal.write(buffer);  // ★ 一次系统调用
```

> 上 PPT 的点：**一帧 = 一次 `write()`，外面裹 CSI 2026**。终端在 `2026h`/`2026l` 之间不刷新，所以用户看不到"画一半"的中间态 —— 这是无闪烁的关键，不是靠双缓冲。

### 1.5 备用屏差分（`tui-alt-screen.ts:753-804`）

更简单，因为有绝对定位可用：

```ts
for (let row = 0; row < height; row++) {
	if (!fullRedraw && !imagesNeedRedraw && screen[row] === this.previousScreen[row]) continue;
	buffer += `\x1b[${row + 1};1H\x1b[2K${screen[row] ?? ""}`;   // :788 绝对定位 + 清行 + 内容
}
```

全量重绘条件只有 3 个（`:771-776`）：首帧、宽变、高变；外加"这一行涉及图片"的特判。

### 1.6 渲染调度：16ms 节流 + nextTick 合并

`packages/tui/src/tui.ts:745-786`：

```ts
private static readonly MIN_RENDER_INTERVAL_MS = 16;   // :332

requestRender(force = false): void {
	if (force) { /* resetRenderState + process.nextTick 立刻画 */ }   // :745-762
	if (this.renderRequested) return;                                 // :763 ★ 去重
	this.renderRequested = true;
	process.nextTick(() => this.scheduleRender());
}

private scheduleRender(): void {
	const elapsed = performance.now() - this.lastRenderAt;
	const delay = Math.max(0, TuiBase.MIN_RENDER_INTERVAL_MS - elapsed);   // :773
	this.renderTimer = setTimeout(() => { … this.doRender(); … }, delay);
}
```

→ **上限 62.5 fps**。流式输出时一秒钟可能来几百个 text delta，最多只画 62 帧。

### 1.7 全量重绘次数是**被测试断言的公开指标**

`packages/tui/src/tui.ts:288`、`:373`：

```ts
readonly fullRedraws: number;              // TUI 接口成员
get fullRedraws(): number { return this.fullRedrawCount; }
```

在测试里当断言用 —— `packages/coding-agent/test/edit-tool-no-full-redraw.test.ts:130-143`：

```ts
const redrawsBeforeResult = tui.fullRedraws;
const clearsBeforeResult = terminal.fullClearCount;
component.updateResult({ … }, false);
tui.requestRender(); await waitForRender();
expect(tui.fullRedraws).toBe(redrawsBeforeResult);        // ★ edit 工具出结果不许触发全量重绘
expect(terminal.fullClearCount).toBe(clearsBeforeResult);
```

`packages/tui/test/tui-render.test.ts:362-369` 反向断言：

```ts
assert.ok(tui.fullRedraws > initialRedraws, "Height change should trigger full redraw");
```

> 上 PPT 的点：**"这次改动有没有让终端闪一下"被写成了 CI 断言。**

调试开关（`tui-main-screen.ts:219-226`）：`PI_DEBUG_REDRAW=1` 把每次全量重绘的原因写进 `~/.pi/agent/pi-debug.log`。

---

## 2. 组件 / 控件体系

### 2.1 基础件清单：**16 个 class + 1 个 Container**

`grep -n "^export class" packages/tui/src/components/*.ts` 实测：

| 组件 | 位置 | 行数 | 说明 |
|---|---|---|---|
| `Text` | `components/text.ts:7` | 106 | 多行文本 + 自动换行 + 背景色函数；有 `(text,width)` 缓存（`:39-48`） |
| `TruncatedText` | `components/truncated-text.ts:7` | 65 | 单行截断 |
| `Box` | `components/box.ts:14` | 137 | padding + 背景 |
| `Spacer` | `components/spacer.ts:6` | 28 | 空行 |
| `Editor` | `components/editor.ts:270` | **2 351** | 主输入框，见第 3 节 |
| `Input` | `components/input.ts:19` | 447 | 单行输入 |
| `Markdown` | `components/markdown.ts:112` | 861 | 基于 `marked`，带语法高亮 |
| `Image` | `components/image.ts:25` | 127 | Kitty / iTerm2 内联图片 |
| `Loader` | `components/loader.ts:17` | 92 | 转圈（`extends Text`） |
| `CancellableLoader` | `components/cancellable-loader.ts:13` | 40 | 带 abort |
| `SelectList` | `components/select-list.ts:40` | 229 | 选择列表（模糊搜索） |
| `SettingsList` | `components/settings-list.ts:34` | 249 | 设置开关列表 |
| `ScrollView` | `components/scroll-view.ts:16` | 195 | `extends Container`，应用自管滚动 |
| `VStack` / `HStack` | `components/v-stack.ts:3` / `h-stack.ts:5` | 24 / 44 | 都 `extends Stack`（`components/stack.ts`，154 行） |
| `AltScreenFlashContainer` | `components/alt-screen-flash.ts:13` | 51 | 备用屏的角落提示 |
| `Container` | `tui.ts:211` | — | 纵向拼接，无缓存（`tui.ts:235-244`） |

### 2.2 组合方式：**只有两种**

1. **主屏 = 纯纵向拼接**。`Container.addChild()` 往下摞，没有布局引擎。README 明说（`packages/tui/README.md:83`）：

> "`VStack` and `HStack` allocate constrained regions, while `ScrollView` owns scrolling for one region. **These semantics are intentionally unavailable on `TuiMainScreen`**, where the terminal owns scrollback."

2. **备用屏 = 有约束布局**。`packages/tui/src/layout.ts`（398 行）引入 `LayoutRect` / `LayoutBox` / `LayoutFrame`（`:10-36`），有真正的 `x/y/width/height` 和裁剪矩形 `clip`（`:20`）。布局期有 render 缓存（`layout.ts:62-75`）：

```ts
function renderCached(context: LayoutContext, component: Component, width: number): string[] {
	let widths = context.renderCache.get(component);
	…
	let lines = widths.get(safeWidth);
	if (!lines) { lines = component.render(safeWidth); widths.set(safeWidth, lines); }
	return lines;
}
```

### 2.3 Overlay：`TuiBase` 内建的模态栈

`tui.ts:534-627` `showOverlay(component, options)` 返回 `OverlayHandle`（`:173-186`：`hide / setHidden / isHidden / focus / unfocus / isFocused`）。

定位系统（`OverlayOptions`，`tui.ts:126-162`）：**9 个 anchor**（`OverlayAnchor`，`:86-95`）+ `offsetX/Y` + 绝对/百分比 `row/col` + 四边 `margin` + **响应式回调** `visible(termWidth, termHeight) => boolean`（`:159`）。

百分比解析（`:111-120`）：

```ts
const match = value.match(/^(\d+(?:\.\d+)?)%$/);
if (match) return Math.floor((referenceSize * parseFloat(match[1])) / 100);
```

合成到底层行的函数是导出的纯函数 `compositeTuiLine(baseLine, overlayLine, startCol, overlayWidth, totalWidth)`（`tui.ts:253-282`），它做的事：把底行按列切成 before/after，中间塞 overlay，两侧各补一个 `SEGMENT_RESET`（`tui.ts:250`）：

```ts
const SEGMENT_RESET = "\x1b[0m\x1b]8;;\x07";   // SGR reset + OSC 8 超链接关闭
```

> 上 PPT 的点：**"overlay 不是新画一层，而是把两个字符串按终端列宽切开再缝起来"**。缝合点两边各插一个 reset，防止底层的颜色/超链接泄漏到浮层里 —— 这个 bug 专门有回归测试 `packages/tui/test/tui-overlay-style-leak.test.ts` 和 `regression-overlay-cjk-boundary.test.ts`。

### 2.4 失效模型：手动 `invalidate()`，没有响应式

约定写死在 `packages/coding-agent/docs/tui.md:504`：

> "Call `invalidate()` when state changes, then use the injected `tui.requestRender()` to trigger re-render."

叶子组件自己做 `(text, width)` 二元组缓存 —— `packages/tui/src/components/markdown.ts:153-157`：

```ts
if (this.cachedLines && this.cachedText === this.text && this.cachedWidth === width) {
	return this.cachedLines;
}
```

`Container` **没有**缓存（`tui.ts:235-244` 每次都重新拼），`Container.invalidate()` 只是递归下发（`tui.ts:229-233`）。

主题切换时 TUI 对**所有**组件（含 overlay）调 `invalidate()`（`tui.ts:671-674`）：

```ts
override invalidate(): void {
	super.invalidate();
	for (const overlay of this.overlayStack) overlay.component.invalidate?.();
}
```

`docs/tui.md:506-607` 用整整 100 行讲一个坑：**组件如果把主题色"烤进"字符串再缓存，清缓存不够，必须在 `invalidate()` 里重建内容**。

---

## 3. 输入处理

### 3.1 三级流水线

```
process.stdin (raw mode)
  └─> StdinBuffer.process()            packages/tui/src/stdin-buffer.ts:287
        ├─ 'data'  每次一条完整转义序列   :397
        └─ 'paste' 括号粘贴的完整内容     :328 / :362
  └─> ProcessTerminal 转发              packages/tui/src/terminal.ts:181-199
  └─> TuiBase.handleTerminalInput()     packages/tui/src/tui.ts:788-862
  └─> focusedComponent.handleInput()    packages/tui/src/tui.ts:859
```

### 3.2 第一级：`StdinBuffer` —— 把碎片拼成完整序列

问题写在文件头注释（`stdin-buffer.ts:5-13`）：

```
For example, the mouse SGR sequence `\x1b[<35;20;5m` might arrive as:
- Event 1: `\x1b`
- Event 2: `[<35`
- Event 3: `;20;5m`
```

`isCompleteSequence()`（`:29-78`）按序列类型分派完整性判定，**5 种转义序列各有一个终止条件**：

| 类型 | 前缀 | 完整判定 | 行号 |
|---|---|---|---|
| CSI | `ESC [` | 末字节落在 `0x40..0x7E` | `:84-126` |
| OSC | `ESC ]` | 以 `ESC \` 或 `BEL` 结尾 | `:132-143` |
| DCS | `ESC P` | 以 `ESC \` 结尾（XTVersion 回包） | `:150-161` |
| APC | `ESC _` | 以 `ESC \` 结尾（Kitty 图形回包） | `:168-179` |
| SS3 | `ESC O` | 后跟 1 个字符 | `:66-69` |
| 老式鼠标 | `ESC [ M` | 固定 6 字节 | `:43-46` |

拼不完整就等，超时 **10ms** 强刷（`:284` `this.timeoutMs = options.timeout ?? 10`，`:379-386`）。

一个具体到吓人的兼容 hack（`:210-230`）—— WezTerm 开 Kitty 键盘协议时把 Escape 键按下发成裸 `\x1b`、松开发成完整 CSI-u，两者粘连成 `\x1b\x1b[27;...u`：

```ts
if (candidate === "\x1b\x1b") {
	const nextChar = remaining[seqEnd];
	if (nextChar === "[" || nextChar === "]" || nextChar === "O" || nextChar === "P" || nextChar === "_") {
		sequences.push(ESC);   // 只吐第一个 ESC，从第二个重新解析
		pos += 1;
		break;
	}
}
```

来源标注得很老实（`stdin-buffer.ts:16-17`）：

```
Based on code from OpenTUI (https://github.com/anomalyco/opentui)
MIT License - Copyright (c) 2025 opentui
```

### 3.3 第二级：键盘协议协商

`packages/tui/src/terminal.ts:15-17`：

```ts
const DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS = 7;
const KITTY_KEYBOARD_PROTOCOL_QUERY = `\x1b[>${DESIRED_KITTY_KEYBOARD_PROTOCOL_FLAGS}u\x1b[?u\x1b[c`;
```

flags = 7 = 1|2|4，注释写明（`:214-218`）：

```
- 1 = disambiguate escape codes
- 2 = report event types (press/repeat/release)
- 4 = report alternate keys (shifted key, base layout key)
```

**为什么后面跟一个 DA 查询 `\x1b[c`**（`:210-213`）：

> "The trailing DA query is a sentinel supported by terminals that do not know Kitty keyboard protocol; receiving DA before a Kitty response enables modifyOtherKeys fallback **without a startup timeout**."

→ **不靠超时判断降级，靠"哪个回包先到"**。降级路径 `enableModifyOtherKeys()` 写 `\x1b[>4;2m`（`:320-324`）。

三套按键编码都要认（`keys.ts`）：

| 编码 | 解析函数 | 行号 |
|---|---|---|
| Kitty CSI-u | `parseKittySequence()` | `:587-651`；正则 `KITTY_CSI_U_REGEX` 在 `:1333` |
| xterm modifyOtherKeys | `parseModifyOtherKeysSequence()` | `:696-702` |
| Legacy（`ESC[A`、`ESC[1;5D` …） | `LEGACY_KEY_SEQUENCES` / `LEGACY_SHIFT_SEQUENCES` / `LEGACY_CTRL_SEQUENCES` 三张表 | `:368-420` |

**`matchesKey(data, keyId)` 一个函数 385 行**（`keys.ts:820-1204`）。这是整份取证里最能说明"终端输入有多脏"的数字。

修饰键位掩码（`keys.ts:292-299`）：

```ts
const MODIFIERS = { shift: 1, alt: 2, ctrl: 4, super: 8 } as const;
const LOCK_MASK = 64 + 128; // Caps Lock + Num Lock
```

`LOCK_MASK` 存在的理由：Kitty 协议会把 CapsLock/NumLock 也编进修饰位，不掩掉的话开了大写锁定所有快捷键就失效。

Windows 专门加载了一个原生 `.node`（`terminal.ts:338-366`）：

```ts
// On Windows, add ENABLE_VIRTUAL_TERMINAL_INPUT (0x0200) to the stdin console handle
// … Without this, libuv's ReadConsoleInputW discards modifier state and Shift+Tab arrives as plain \t.
const nativePath = path.join("native", "win32", "prebuilds", `win32-${arch}`, "win32-console-mode.node");
```

macOS Terminal.app 的 Shift+Enter 走"本机修饰键探测"（`terminal.ts:14`、`:44-47`、`native-modifiers.ts`，59 行）：

```ts
const APPLE_TERMINAL_SHIFT_ENTER_SEQUENCE = "\x1b[13;2u";
export function normalizeAppleTerminalInput(data, isAppleTerminal, isShiftPressed) {
	if (isAppleTerminal && data === "\r" && isShiftPressed) return APPLE_TERMINAL_SHIFT_ENTER_SEQUENCE;
	return data;
}
```

文档承认这个方案的边界（`packages/coding-agent/docs/terminal-setup.md:13`）：

> "This fallback only works when pi runs on the same Mac as Terminal.app. It cannot detect the local keyboard over remote SSH."

### 3.4 粘贴：括号粘贴 + 大粘贴折叠成 marker

启用（`terminal.ts:146-147`）：

```ts
// Enable bracketed paste mode - terminal will wrap pastes in \x1b[200~ ... \x1b[201~
process.stdout.write("\x1b[?2004h");
```

`StdinBuffer` 检出粘贴区间后发独立的 `'paste'` 事件（`stdin-buffer.ts:337-368`），`ProcessTerminal` 再把它**重新包上标记**丢回去（`terminal.ts:195-199`）：

```ts
this.stdinBuffer.on("paste", (content) => {
	this.inputHandler(`\x1b[200~${content}\x1b[201~`);
});
```

`Editor` 里再拆一次（`components/editor.ts:627-651`），然后进 `handlePaste()`（`:1156-1222`）。这个函数做 4 件事：

1. **CSI-u 反解码**（`:1168-1173`）—— tmux popup 开 `extended-keys-format=csi-u` 时会把粘贴内容里的控制字节重编码成 `ESC [ <cp> ; 5 u`：

```ts
const decodedText = pastedText.replace(/\x1b\[(\d+);5u/g, (match, code) => {
	const cp = Number(code);
	if (cp >= 97 && cp <= 122) return String.fromCharCode(cp - 96);
	…
});
```

2. **过滤不可打印字符**，只留 `\n` 和 `>= 32`（`:1179-1182`）
3. **路径粘贴自动补空格**（`:1186-1192`）：粘的内容以 `/`、`~`、`.` 开头且光标前是单词字符 → 前面补一个空格
4. **大粘贴折叠**（`:1197-1212`）—— **阈值：> 10 行 或 > 1000 字符**：

```ts
if (pastedLines.length > 10 || totalChars > 1000) {
	this.pasteCounter++;
	this.pastes.set(pasteId, filteredText);
	const marker = pastedLines.length > 10
		? `[paste #${pasteId} +${pastedLines.length} lines]`
		: `[paste #${pasteId} ${totalChars} chars]`;
	this.insertTextAtCursorInternal(marker);
	return;
}
```

原文存在 `Map<number, string>` 里（`editor.ts:309`），提交时才展开（`expandPasteMarkers()`，`:985`；`getExpandedText()`，`:998`）。

**marker 在编辑时是一个原子字素**：`segmentWithMarkers()`（`editor.ts:34-51`）把 `[paste #1 +123 lines]` 合并成单个 segment，于是光标移动、删词、换行都把它当一个字符处理（`:32-36` 注释原文："This makes cursor movement, deletion, word-wrap, etc. treat paste markers as single units."）。

> 上 PPT 的点：**粘 500 行日志，输入框里只占一个 token 宽的 `[paste #1 +500 lines]`，但送给模型的是原文。**这是"终端输入框"这个媒介独有的产品设计。

### 3.5 多行编辑：`Editor` 2 351 行都干了什么

按方法名分类（`grep "^	private \|^	public " components/editor.ts`）：

| 能力 | 关键方法 | 行号 |
|---|---|---|
| 视觉行 ↔ 逻辑行映射 | `layoutText()` / `buildVisualLineMap()` / `findVisualLineAt()` | `:893` / `:1732` / `:1762` |
| 上下移动保持"目标列" | `computeVerticalMoveColumn()` | `:1477` |
| 删除到行首/行尾 | `deleteToStartOfLine()` / `deleteToEndOfLine()` | `:1521` / `:1556` |
| 按词删/移 | `deleteWordBackwards()` / `deleteWordForward()` / `moveWordBackwards()` | `:1588` / `:1633` / `:1869` |
| Emacs kill-ring | `yank()` / `yankPop()` | `:1894` / `:1909`（`src/kill-ring.ts`，46 行） |
| Undo | `pushUndoSnapshot()` | `:2012`（`src/undo-stack.ts`，28 行） |
| 历史 | `addToHistory()` / `navigateHistory()` | `:399` / `:427` |
| 字符跳转（类 vim `f`/`F`） | `jumpMode` + `jumpToChar()` | `:607-625` |
| 自动补全 | `setAutocompleteProvider()` | `:389`（`src/autocomplete.ts`，786 行） |

换行 vs 提交（`:787-820`）：`tui.input.newLine`（`shift+enter` / `ctrl+j`）插换行，`tui.input.submit`（`enter`）提交；另有 `shouldSubmitOnBackslashEnter()`（`:1249-1259`）处理"行尾反斜杠 + Enter"。

CJK 感知的软换行（`utils.ts:54` 的 `cjkBreakRegex`，`editor.ts:193-194`）：

```ts
const isCjk = !isPasteMarker(grapheme) && cjkBreakRegex.test(grapheme);
const nextIsCjk = !isPasteMarker(next.segment) && cjkBreakRegex.test(next.segment);
```

→ 中文没有空格，得按字断行。

### 3.6 快捷键表

**分两层，合计 79 条**（实测）：

```bash
$ sed -n '61,159p' packages/tui/src/keybindings.ts | grep -c 'defaultKeys'
37      # TUI 基础层
$ sed -n '64,207p' packages/coding-agent/src/core/keybindings.ts | grep -c 'defaultKeys'
42      # 应用层
```

两层是用 **TypeScript 模块增强**拼起来的，不是运行时字符串拼接 —— `packages/coding-agent/src/core/keybindings.ts:60-62`：

```ts
declare module "@earendil-works/pi-tui" {
	interface Keybindings extends AppKeybindings {}
}
```

`packages/tui/src/keybindings.ts:7-49` 的 `interface Keybindings` 是**开放的**，下游包 `extends` 进去，于是 `Keybinding` 联合类型自动扩容，`kb.matches(data, "app.interrupt")` 才能通过类型检查。运行时则是 `packages/coding-agent/src/core/keybindings.ts:64-65` 直接 spread：

```ts
export const KEYBINDINGS = {
	...TUI_KEYBINDINGS,
	"app.interrupt": { defaultKeys: "escape", description: "Cancel or abort" },
```

> 上 PPT 的点：**"TUI 库定义 37 条，产品层再加 42 条，类型系统全程有效"** —— 这是把 TUI 当 SDK 做的直接后果。

**TUI 基础层 37 条**，全部列在 `packages/tui/src/keybindings.ts:61-159`（`TUI_KEYBINDINGS`，`as const satisfies KeybindingDefinitions`）。

**编辑器（21 条，`keybindings.ts:62-124`）**：

| id | 默认键 | 行号 |
|---|---|---|
| `tui.editor.cursorUp` / `cursorDown` | `up` / `down` | `:62-63` |
| `tui.editor.cursorLeft` | `left`, **`ctrl+b`** | `:64-67` |
| `tui.editor.cursorRight` | `right`, **`ctrl+f`** | `:68-71` |
| `tui.editor.cursorWordLeft` | `alt+left`, `ctrl+left`, **`alt+b`** | `:72-75` |
| `tui.editor.cursorWordRight` | `alt+right`, `ctrl+right`, **`alt+f`** | `:76-79` |
| `tui.editor.cursorLineStart` | `home`, **`ctrl+a`** | `:80-83` |
| `tui.editor.cursorLineEnd` | `end`, **`ctrl+e`** | `:84-87` |
| `tui.editor.jumpForward` / `jumpBackward` | `ctrl+]` / `ctrl+alt+]` | `:88-95` |
| `tui.editor.pageUp` / `pageDown` | `pageUp` / `pageDown` | `:96-97` |
| `tui.editor.deleteCharBackward` | `backspace` | `:98-101` |
| `tui.editor.deleteCharForward` | `delete`, **`ctrl+d`** | `:102-105` |
| `tui.editor.deleteWordBackward` | **`ctrl+w`**, `alt+backspace` | `:106-109` |
| `tui.editor.deleteWordForward` | `alt+d`, `alt+delete` | `:110-113` |
| `tui.editor.deleteToLineStart` | **`ctrl+u`** | `:114-117` |
| `tui.editor.deleteToLineEnd` | **`ctrl+k`** | `:118-121` |
| `tui.editor.yank` / `yankPop` | **`ctrl+y`** / **`alt+y`** | `:122-123` |
| `tui.editor.undo` | `ctrl+-` | `:124` |

加粗的全是 **readline/Emacs 传统键位** —— `ctrl+a/e/b/f/k/u/w/y` + `alt+b/f/y`。**这不是自己发明的，是照抄 GNU readline。**

**通用输入（4 条，`:125-128`）**：`newLine` = `shift+enter`,`ctrl+j`；`submit` = `enter`；`tab` = `tab`；`copy` = `ctrl+c`。

**选择列表（6 条，`:129-140`）**：`up`/`down`/`pageUp`/`pageDown`/`enter`/`escape`+`ctrl+c`。

**备用屏视口（6 条，`:141-158`）**：`pageUp`/`pageDown`/`ctrl+shift+up`(上一个语义提示符)/`ctrl+shift+down`/`home`/`end`。

**应用层 42 条**，定义在 `packages/coding-agent/src/core/keybindings.ts:64-207`（类型白名单 `AppKeybindings` 在 `:13-56`）。全局编辑器上下文的 16 条：

| id | 默认键 | 行号 |
|---|---|---|
| `app.interrupt` | `escape` | `:66` |
| `app.clear` | `ctrl+c` | `:67` |
| `app.exit` | `ctrl+d`（编辑器为空时才触发，否则落回删除字符） | `:68` |
| `app.suspend` | `ctrl+z`；**Windows 上是 `[]`（无默认）** | `:69-72` |
| `app.thinking.cycle` | `shift+tab` | `:73-76` |
| `app.model.cycleForward` / `cycleBackward` | `ctrl+p` / `shift+ctrl+p` | `:77-84` |
| `app.model.select` | `ctrl+l` | `:85` |
| `app.tools.expand` | `ctrl+o` | `:86` |
| `app.thinking.toggle` | `ctrl+t` | `:87-90` |
| `app.editor.external` | `ctrl+g` | `:95-98` |
| `app.message.copy` | `ctrl+x` | `:99-102` |
| `app.message.followUp` | `alt+enter` | `:103-106` |
| `app.message.dequeue` | `alt+up` | `:107-110` |
| `app.clipboard.pasteImage` | `ctrl+v`；**Windows 上 `alt+v`** | `:111-114` |
| `app.session.new/tree/fork/resume` | **`[]`（有 id 无默认键，留给用户绑）** | `:115-118` |

其余 26 条是**上下文局部**的（session picker 9 条 `:135-154`、models selector 6 条 `:155-178`、tree 导航 4 条 `:119-134`、tree filter 7 条 `:179-206`）。

**平台差异直接写进 `defaultKeys`**（`:69-72`、`:111-114`、`:119-126`）：

```ts
"app.suspend": { defaultKeys: process.platform === "win32" ? [] : "ctrl+z", … },
"app.clipboard.pasteImage": { defaultKeys: process.platform === "win32" ? "alt+v" : "ctrl+v", … },
"app.tree.foldOrUp": { defaultKeys: process.platform === "darwin" ? ["alt+left","ctrl+left"] : ["ctrl+left","alt+left"], … },
```

macOS 那条只是**换了个顺序** —— 因为 `/hotkeys` 帮助里显示第一个键，Mac 用户看到的应该是 `alt+left`。

**同一个键在不同上下文复用**是常态：`ctrl+d` 是"删除后一个字符"（`tui.editor.deleteCharForward`）、"退出"（`app.exit`，`:68`）、"删除会话"（`app.session.delete`，`:147-150`）、"树过滤器重置"（`app.tree.filter.default`，`:179-182`）四种身份。之所以不冲突，是因为**每个 picker 组件只查询自己那一组 id**。

**绕过注册表硬编码的极少**，全部找出来只有这些：

| 键 | 位置 | 为什么 |
|---|---|---|
| `shift+ctrl+d` | `packages/tui/src/tui.ts:819` | 隐藏 debug 钩子 `onDebug`，故意不进任何注册表 |
| `shift+backspace` / `shift+delete` | `packages/tui/src/components/editor.ts:748` / `:752` | 与注册表的删除绑定 **OR** 起来做兜底 |
| `shift+space` | `packages/tui/src/components/editor.ts:876` | — |
| `ctrl+c` | `.../interactive/components/config-selector.ts:491` | 启动配置选择器（此时全局 keybindings 还没装好） |
| `ctrl+c` / `escape` | `.../interactive/components/scoped-models-selector.ts:351` / `:362` | — |

主编辑器路径上的 `ctrl+c` / `escape` / `ctrl+d` / `shift+tab` / `ctrl+o` **全部走注册表**（`.../interactive/components/custom-editor.ts:37, 45, 60, 71`）。`custom-editor.ts:60` 的 `app.exit` 还有一层条件：`getText().length === 0` 才退出，否则落回编辑器做删除字符。

### 3.7 键位可完全自定义

`KeybindingsManager`（`keybindings.ts:180-256`）：用户绑定覆盖默认（`:212-216`），并且**检测用户配置内部的冲突**（`:196-210`，`getConflicts()` 在 `:235`）。

用户配置文件：**`~/.pi/agent/keybindings.json`**（独立文件，不是 `settings.json` 里的字段）——`packages/coding-agent/src/core/keybindings.ts:348-352`：

```ts
static create(agentDir: string = getAgentDir()): KeybindingsManager {
	const configPath = join(agentDir, "keybindings.json");
	const userBindings = KeybindingsManager.loadFromFile(configPath);
	return new KeybindingsManager(userBindings, configPath);
}
```

挂载点在 `packages/coding-agent/src/modes/interactive/interactive-mode.ts:505-506`（`KeybindingsManager.create()` + `setKeybindings(...)` 设为全局单例）。`/reload` 斜杠命令走 `reload()`（`core/keybindings.ts:354-357`）热更新。

还带**配置迁移**：`KEYBINDING_NAME_MIGRATIONS`（`core/keybindings.ts:209-269`）把旧的扁平名（`interrupt` / `clear` / `exit` / `cycleThinkingLevel`…）自动改写成 `app.*` / `tui.*` 命名空间 id，启动时原地重写用户文件（`packages/coding-agent/src/migrations.ts:157-172`）。

全局单例 `getKeybindings()` / `setKeybindings()`（`packages/tui/src/keybindings.ts:258-269`），组件里统一 `const kb = getKeybindings(); kb.matches(data, "tui.editor.xxx")`（`editor.ts:604` 起，全文件 33 处）。

文档直接给了 Emacs 版和 Vim 版的完整 JSON（`docs/keybindings.md:184-211`）。

### 3.7.1 扩展注册快捷键：有仲裁规则

- 接口：`registerShortcut(shortcut: KeyId, options: { description?; handler })` —— `packages/coding-agent/src/core/extensions/types.ts:1257-1264`
- 实现：存进 `extension.shortcuts` Map —— `packages/coding-agent/src/core/extensions/loader.ts:267-275`
- **仲裁**：`getShortcuts(resolvedKeybindings)` —— `packages/coding-agent/src/core/extensions/runner.ts:494-536`

规则很直白（`runner.ts:69-89`）：有一张 **18 条的保留键名单** `RESERVED_KEYBINDINGS_FOR_EXTENSION_CONFLICTS`（`app.interrupt` / `app.clear` / `app.exit` / `app.suspend` / `app.thinking.cycle` / `app.model.*` / `app.tools.expand` / `app.editor.external` / `app.message.copy` / `app.message.followUp` / `tui.input.submit` / `tui.select.confirm` / `tui.select.cancel` / `tui.input.copy` / `tui.editor.deleteToLineEnd`）。注释写明范围：

```
// Only editor-global shortcuts are reserved here. Picker-specific bindings are not.
```

撞上保留键 → **扩展被 skip 并告警**；撞上其他内置键 → **扩展胜出**（`runner.ts:509-523`）。分发优先级也高：`custom-editor.ts:31-33` 里扩展 shortcut 在**所有 app keybinding 之前**判定。`/hotkeys` 帮助会追加一张 Extensions 表（`interactive-mode.ts:5913-5929`）。

> 上 PPT 的点：**"哪些键扩展不许抢"被写成一张 18 条的显式白名单，而不是先到先得。**这是把 TUI 当公共 SDK 之后必然要付的税。

### 3.8 全局输入监听 + Ctrl+C 语义

`TuiBase.handleTerminalInput()`（`tui.ts:788-862`）的顺序：

1. 吃掉 OSC 11 背景色回包（`:789`）、色彩方案回包（`:792`）
2. 跑一遍全局 `inputListeners`，**任何一个返回 `{consume:true}` 就截断**，返回 `{data}` 可以改写（`:796-811`）
3. 吃掉 cell size 回包（`:814`）
4. 全局 debug 键 `shift+ctrl+d`（`:819-822`）
5. 焦点校正（overlay 变不可见时重定向，`:826-850`）
6. 交给焦点组件（`:854-861`），**除非是 key release 且组件没声明 `wantsKeyRelease`**（`:856-858`）

Ctrl+C 的注释写得很清楚（`:852-853`）：

```
// Pass input to focused component (including Ctrl+C)
// The focused component can decide how to handle Ctrl+C
```

raw mode 下 Ctrl+C 不产生 SIGINT，得自己处理 —— README 的 Quick Start 就把这件事当成必读项（`packages/tui/README.md:41-47`）。

### 3.9 退出时的输入排空

`ProcessTerminal.drainInput()`（`terminal.ts:368-404`），注释说明动机（`terminal.ts:59-63`）：

> "Drain stdin before exiting to prevent Kitty key release events from leaking to the parent shell **over slow SSH connections**."

`stop()` 里还有一处（`terminal.ts:443-446`）：

```
// Pause stdin to prevent any buffered input (e.g., Ctrl+D) from being re-interpreted
// after raw mode is disabled. This fixes a race condition where Ctrl+D could close
// the parent shell over SSH.
```

> 上 PPT 的点：**"退出时不把残留按键漏给父 shell"这种事，现成库不会替你想。**

---

## 4. 流式输出落到屏幕：**逐跳行号**

一个 text delta 从 provider 到像素，**11 跳**：

| # | 位置 | 干了什么 |
|---|---|---|
| ① | `packages/ai/src/api/anthropic-messages.ts:630-640` | provider SSE `content_block_delta` → `stream.push({ type:"text_delta", delta, partial: output })`。`partial` 是**就地累加的完整 AssistantMessage** |
| ② | `packages/agent/src/agent-loop.ts:317` | `for await (const event of response)` 消费 |
| ③ | `packages/agent/src/agent-loop.ts:327-347` | `context.messages[last] = event.partial`（整条替换）→ `emit({ type:"message_update", message: {...partialMessage} })` |
| ④ | `packages/agent/src/agent.ts:404-408` | `runAgentLoop(..., (event) => this.processEvents(event), ...)` |
| ⑤ | `packages/agent/src/agent.ts:529-576` | `this._state.streamingMessage = event.message`；`for (const listener of this.listeners) await listener(event, signal)` ← **`await`，慢监听者会反压 agent 循环** |
| ⑥ | `packages/coding-agent/src/core/agent-session.ts:393` | `this._unsubscribeAgent = this.agent.subscribe(this._handleAgentEvent)` |
| ⑦ | `packages/coding-agent/src/core/agent-session.ts:619, 622` | 先给扩展（`_emitExtensionEvent`），再给 UI（`_emit`，同步扇出，`:548-552`） |
| ⑧ | `packages/coding-agent/src/modes/interactive/interactive-mode.ts:2914-2918` | `this.session.subscribe(async (event) => { await this.handleEvent(event); })` |
| ⑨ | `.../interactive-mode.ts:3000-3003` | `case "message_update"` → `this.streamingComponent.updateContent(this.streamingMessage, true)` |
| ⑩ | `.../components/assistant-message.ts:89-114` | **`this.contentContainer.clear()` 然后重建全部 `Markdown` 子组件** |
| ⑪ | `.../interactive-mode.ts:3031` | `this.ui.requestRender()` → `tui.ts:767 scheduleRender`（16ms 合并）→ `tui-main-screen.ts:146 doRender()` → `terminal.write(buffer)` |

### 4.1 第 ⑩ 跳是整条链上最"贵"的一步

`packages/coding-agent/src/modes/interactive/components/assistant-message.ts:89-114`：

```ts
updateContent(message: AssistantMessage, isStreaming = this.isStreaming): void {
	this.lastMessage = message;
	this.isStreaming = isStreaming;
	this.contentContainer.clear();                          // :94 ★ 全清
	…
	for (let i = 0; i < message.content.length; i++) {
		const content = message.content[i];
		if (content.type === "text" && content.text.trim()) {
			this.contentContainer.addChild(
				new Markdown(content.text.trim(), this.outputPad, 0, this.markdownTheme, undefined, {  // :110-114 ★ 全新对象
					transform: createMarkdownTransform("assistant", this.isStreaming, this.markdownTransformers),
				}),
			);
		}
	…
```

**每一个 text delta 都把所有 `Markdown` 子组件扔掉重建**。因为是新对象，`Markdown` 的 `(text,width)` 缓存（`markdown.ts:153-157`）在流式期间**永远是冷的** —— 每帧都要重新跑 `marked` 解析 + ANSI 换行。

**但是**这个代价被两层挡住了：

- **第 16ms 节流**（`tui.ts:773`）：一秒最多 62 次
- **第 `previousLines` 逐行字符串比对**（`tui-main-screen.ts:264-274`）：重建出来的行如果内容一样，`oldLine !== newLine` 为 false，**一个字节都不往终端写**

→ 流式追加一段文字，实际只有**最后 1~2 行**进入 `[firstChanged, lastChanged]` 区间。

> 上 PPT 的点：**"上层随便重建，下层按字符串比对兜底"是这套设计的核心交易。**牺牲 CPU（重复渲染字符串）换取实现简单（无需增量数据结构）+ IO 最小（终端只收变化的行）。终端的瓶颈从来是字节 IO 和终端自己的重排，不是 JS 的字符串拼接。

### 4.2 OSC 133 语义标记也在这一跳打上

`assistant-message.ts:78-87`：

```ts
override render(width: number): string[] {
	const lines = super.render(width);
	if (this.hasToolCalls || lines.length === 0) return lines;
	lines[0] = OSC133_ZONE_START + lines[0];
	lines[lines.length - 1] = OSC133_ZONE_END + OSC133_ZONE_FINAL + lines[lines.length - 1];
	return lines;
}
```

`TuiAltScreen` 靠这个实现"跳到上/下一条消息"（`tui-alt-screen.ts:42-43`、`:250-268`）：

```ts
const OSC133_PROMPT_START = /^\x1b\]133;A(?:\x07|\x1b\\)/;
private scrollToPrompt(direction: -1 | 1): void {
	…
	if (!OSC133_PROMPT_START.test(lines[row] ?? "")) continue;
```

主屏渲染前会把 zone 前缀剥掉再进差分（`tui-alt-screen.ts:759`：`.replace(OSC133_ZONE_PREFIX, "")`）。

---

## 5. 终端兼容性：这才是那 14k 行真正的去处

### 5.1 宽字符 / emoji 宽度

**唯一的运行时依赖之一就是干这个的**：`get-east-asian-width@1.6.0`（`package.json:39`）。

`graphemeWidth(segment)`（`utils.ts:173-234`）—— 单个字素簇宽度，**7 个分支**：

| 分支 | 返回 | 行号 |
|---|---|---|
| Tab | **3**（不是 4，不是 8） | `:174-176` |
| 终端占位组合符 | 码点个数 | `:178-181` |
| 零宽簇 | 0 | `:183-186` |
| RGI Emoji（含 ZWJ 序列、肤色） | **2** | `:188-191` |
| Regional Indicator（U+1F1E6..U+1F1FF，国旗半边） | **2** | `:200-205` |
| 基本码点 | `eastAsianWidth(cp)` | `:207` |
| 尾随可见码点（印度语系、半/全角形式、泰/老挝 AM 元音） | 逐个加 | `:209-231` |

Regional Indicator 那段注释是"为什么必须自己写"的最佳例证（`:200-202`）：

```
// Regional indicator symbols (U+1F1E6..U+1F1FF) are often rendered as
// full-width emoji in terminals, even when isolated during streaming.
// Keep width conservative (2) to avoid terminal auto-wrap drift artifacts.
```

→ **流式输出时国旗 emoji 会被劈成两半**（先来 🇨 再来 🇳），单独一半在终端里仍然按 2 格渲染。要是按 Unicode 规范算 1 格，行宽就会算错，触发终端自动折行，差分渲染的行号映射就毁了。这条专门有回归测试：`packages/tui/test/regression-regional-indicator-width.test.ts`。

`visibleWidth(str)`（`utils.ts:239-294`）：

- **快路径**：纯 ASCII 直接 `str.length`（`:245-247`）
- **LRU 缓存**（`:249-253`、`:285-291`，`WIDTH_CACHE_SIZE` 上限）
- Tab → 3 空格（`:257-259`）
- 单遍剥掉 CSI / OSC / APC（`:260-276`，含自定义的 `CURSOR_MARKER`）
- `Intl.Segmenter` 分字素簇后逐个 `graphemeWidth` 累加（`:280-282`）

Emoji 判定用了两级（`utils.ts:27-48`）：先跑一个廉价的 `couldBeEmoji()` 启发式，命中了才跑 `/^\p{RGI_Emoji}$/v` 正则 —— 注释原话："a fast heuristic to avoid the expensive rgiEmojiRegex test"（`:22-25`）。

### 5.2 ANSI：不是 strip，是"结构化理解"

`utils.ts` 里一整套 ANSI 感知工具（导出的 6 个 + 内部的一堆）：

| 函数 | 行号 | 用途 |
|---|---|---|
| `extractAnsiCode(str, pos)` | `:405` | 从任意位置抠出一个完整转义码 + 长度 |
| `stripTerminalSequences(str)` | `:297` | 剥掉 ANSI/OSC/APC 保留可见文本 |
| `normalizeTerminalOutput(str)` | `:378` | 规范化 |
| `wrapTextWithAnsi(text, width)` | `:809` | **换行时把样式在每个新行重新打开** |
| `truncateToWidth(...)` | `:1030` | 截断并补 reset |
| `sliceByColumn` / `sliceWithWidth` / `extractSegments` | `:1172` / `:1177` / `:1232` | 按**列**（不是按字符）切 |
| `getOsc8LinkAtColumn(line, column)` | `:343` | 点击位置反查超链接（备用屏鼠标用） |
| `applyBackgroundToLine(...)` | `:1008` | 把背景色铺到整行宽 |

内部还有一个 `AnsiCodeTracker`（`updateTrackerFromText`，`:706`），换行时用它记住"当前打开了哪些 SGR + 是否在一个 OSC 8 链接里"，然后在下一行开头重新发一遍。

**每行结尾无条件补 reset**（`tui.ts:1120-1129`）：

```ts
protected applyLineResets(lines: string[]): string[] {
	const reset = SEGMENT_RESET;   // "\x1b[0m\x1b]8;;\x07"
	for (let i = 0; i < lines.length; i++) {
		if (!isImageLine(lines[i])) lines[i] = normalizeTerminalOutput(lines[i]) + reset;
	}
	return lines;
}
```

文档把这条契约明写给扩展作者（`docs/tui.md:29`）：

> "The TUI appends a full SGR reset and OSC 8 reset at the end of each rendered line. **Styles do not carry across lines.** … use `wrapTextWithAnsi()` so styles are preserved for each wrapped line."

### 5.3 Resize

订阅（`terminal.ts:150`）：

```ts
process.stdout.on("resize", this.resizeHandler);
```

`resizeHandler` 就是 `() => this.requestRender()`（`tui.ts:679-682`），走正常调度；宽/高变化的判定在 `doRender()` 里做（`tui-main-screen.ts:150-151`）。

**启动时主动补一次 SIGWINCH**（`terminal.ts:152-156`）：

```ts
// Refresh terminal dimensions - they may be stale after suspend/resume
// (SIGWINCH is lost while process is stopped). Unix only.
if (process.platform !== "win32") process.kill(process.pid, "SIGWINCH");
```

→ `ctrl+z` 挂起期间改了终端大小，恢复后 `process.stdout.columns` 是旧值。自己给自己发一个信号强刷。

宽度回退链（`terminal.ts:465-471`）：`process.stdout.columns` → `$COLUMNS` → **80**；行数 → `$LINES` → **24**。

### 5.4 Alt screen

进（`tui-alt-screen.ts:187`）：

```ts
`${ENTER_ALT_SCREEN}${DISABLE_AUTOWRAP}${this.mouseEnabled ? ENABLE_MOUSE : ""}\x1b[2J\x1b[H\x1b[?25l`
```

`ENTER_ALT_SCREEN = "\x1b[?1049h"`（`:32`）。注意**同时关掉了自动折行** —— 因为应用自己保证不超宽。

出（`:199`、`:203-207`）：删掉 Kitty 图片 → 关鼠标 → 恢复自动折行 → 退备用屏 → **然后把完整文档打印到主屏**：

```ts
const documentLines = this.render(width).map((line) => line.replace(OSC133_ZONE_PREFIX, ""));
```

> 上 PPT 的点：**全屏模式退出时把整段会话吐回 scrollback**，这样用户 `ctrl+z` / 退出后还能翻历史。这是"备用屏"最大的产品缺陷，pi 用一次额外渲染补上了。

主屏模式的退出处理更细（`tui-main-screen.ts:67-75`）：写一个空格、把光标移到内容末尾、`\r\n` —— 保证 shell 提示符不会覆盖最后一行。

### 5.5 终端能力探测：**12 个分支的硬编码白名单**

`packages/tui/src/terminal-image.ts:68-128`，`detectCapabilities()` 返回 `{ images, trueColor, hyperlinks }`：

| 判定条件 | images | trueColor | hyperlinks | 行号 |
|---|---|---|---|---|
| `$TMUX` 或 `TERM=tmux*` | **null** | 看 `$COLORTERM` | **探测 tmux** | `:77-79` |
| `TERM=screen*` | null | 看 `$COLORTERM` | false | `:82-84` |
| `$KITTY_WINDOW_ID` / `TERM_PROGRAM=kitty` | kitty | true | true | `:86-88` |
| Ghostty | kitty | true | true | `:90-92` |
| WezTerm | kitty | true | true | `:94-96` |
| Warp | kitty | true | true | `:99-101` |
| iTerm2 | **iterm2** | true | true | `:103-105` |
| `$WT_SESSION`（Windows Terminal） | null | true | true | `:107-109` |
| VSCode | null | true | true | `:111-113` |
| Alacritty | null | true | true | `:115-117` |
| JetBrains JediTerm | null | true | **false** | `:119-121` |
| 兜底（未知终端） | null | 看 `$COLORTERM` | **false** | `:127` |

tmux 那条最有意思 —— 它**真的去执行 tmux 命令问**（`terminal-image.ts:50-62`）：

```ts
function probeTmuxHyperlinks(): boolean {
	const termfeatures = execSync("tmux display-message -p '#{client_termfeatures}'", {
		encoding: "utf8", timeout: 250, stdio: ["ignore", "pipe", "ignore"],
	});
	return termfeatures.split(",")…
}
```

注释（`:45-48`）："tmux only re-emits them when its `client_termfeatures` lists `hyperlinks`, and strips them otherwise."

兜底为什么保守（`:123-126`）：

```
// Unknown terminal: be conservative. OSC 8 is rendered invisibly as "just text" on
// terminals that swallow it, which means the URL disappears from the rendered output.
// Default to the legacy `text (url)` behavior unless we have positively identified a
// hyperlink-capable terminal above.
```

### 5.6 还问终端要了这些信息（DSR / OSC 查询）

| 查询 | 序列 | 用途 | 行号 |
|---|---|---|---|
| Kitty 键盘协议 + DA sentinel | `\x1b[>7u\x1b[?u\x1b[c` | 键盘协议协商 | `terminal.ts:17` |
| Cell 像素尺寸 | `\x1b[16t` | 算图片占几行 | `tui.ts:727` |
| 背景色 | `\x1b]11;?\x07`（OSC 11） | 自动配主题 | `tui.ts:1193` |
| 亮/暗色方案 | `\x1b[?996n`（DSR） | 同上 | `tui.ts:1220` |
| 色方案变更订阅 | `\x1b[?2031h` / `l` | 系统切深色模式时跟随 | `tui.ts:686`、`:716` |
| 进度指示 | `\x1b]9;4;3\x07`（OSC 9;4），**每 1000ms 重发保活** | 任务栏进度条 | `terminal.ts:11-13`、`:509-523` |

回包都在 `handleTerminalInput()` 里被优先"吃掉"（`tui.ts:789-794`、`:814`），不会漏给焦点组件。cell size 回包解析（`tui.ts:900-918`）拿到后会 `invalidate()` 所有组件让图片重排。

### 5.7 内联图片：两套协议 + Kitty 的行占位补偿

`isImageLine(line)` 判前缀 `\x1b_G`（Kitty）或 iTerm2 前缀（`terminal-image.ts:146-155`）。

主屏渲染时对图片行做特殊处理（`tui-main-screen.ts:186-197`、`:390-409`）：Kitty 图片的 `r=N` 参数声明它占 N 行，需要先吐 N-1 个 `\r\n` 占位、再 `\x1b[N-1A` 回到起点、写图片、再 `\x1b[N-1B` 下来。`getKittyImageReservedRows()`（`:95-107`）算实际保留了几行。

差分时还要**把变化区间扩展到整个图片块**（`expandChangedRangeForKittyImages`，`:109-130`），并**显式删除旧图片**（`deleteChangedKittyImages`，`:132-144`）—— 因为 Kitty 图片是"放置"不是"字符"，覆盖不掉，必须删。

iTerm2 在备用屏里直接退化成文本，README 给了理由（`packages/tui/README.md:660`）：

> "iTerm2 inline images fall back to text because the iTerm2 protocol **cannot delete or crop placements** during viewport repainting."

### 5.8 IME（中日韩输入法）：硬件光标定位

自定义 APC 标记（`tui.ts:74-79`）：

```ts
/** Cursor position marker - APC (Application Program Command) sequence.
 *  This is a zero-width escape sequence that terminals ignore. */
export const CURSOR_MARKER = "\x1b_pi:c\x07";
```

流程：组件在光标位置吐这个标记 → `extractCursorPosition()`（`tui.ts:1149-1167`）**只扫底部一屏**找到它、算出可见列、**从行里剥掉** → `positionHardwareCursor()`（`tui-main-screen.ts:520-551`）把真光标移过去。

为什么要这么绕（`docs/tui.md:55`）：

> "The cursor remains hidden by default. This keeps the fake cursor rendering, while still positioning the hardware cursor **for terminals that track IME candidate windows with hidden cursors**."

`docs/tui.md:85` 还写了一条容器组件的坑：

> "Without this propagation, typing with an IME (Chinese, Japanese, Korean, etc.) will show the candidate window in the wrong position on screen."

→ **中文输入法候选框位置**这件事，是靠一个自定义 APC 序列 + 每帧扫描一屏文本实现的。

---

## 6. 为什么一个 agent 项目要自己写 14k 行 TUI

### 6.1 证据 A：依赖里**一个 TUI 库都没有**

```bash
$ grep -rn '"ink"\|"blessed"\|"@opentui\|"terminal-kit"\|"react"' --include=package.json packages/
# （无输出）
```

`packages/tui/package.json:37-44`：

```json
"dependencies": {
	"get-east-asian-width": "1.6.0",
	"marked": "18.0.5"
},
"devDependencies": {
	"@xterm/headless": "5.5.0",
	"chalk": "5.6.2"
}
```

**运行时依赖 = 2 个，一个算宽度、一个解析 Markdown。**其余全是自己写的，包括 ANSI 解析、按键解析、换行、截断、差分、布局、鼠标、选区、图片。

主消费方 `packages/coding-agent/package.json:45-66` 的 20 个依赖里也没有任何 TUI 框架，`@earendil-works/pi-tui` 就是它的 UI 层（`:50`）。

`@xterm/headless` 只在**测试**里（`packages/tui/test/virtual-terminal.ts:1-30`），用来做真实终端模拟器断言：

```ts
export class VirtualTerminal implements Terminal {
	private xterm: XtermTerminalType;
	constructor(columns = 80, rows = 24) {
		this.xterm = new XtermTerminal({ cols: columns, rows: rows, disableStdin: true, allowProposedApi: true });
```

> 上 PPT 的点：**它不用现成 TUI 库来渲染，却用一个真的终端模拟器来验证自己渲染对不对。**这是 14 839 行测试的技术底座。

### 6.2 证据 B：TUI 是**对外产品接口**，不是内部实现

`pi-tui` 是**独立发布的 npm 包**（`packages/tui/package.json:1`：`@earendil-works/pi-tui`），有自己的 README（854 行）、自己的 keywords、自己的 `prepublishOnly`。

而且它是**扩展 API 的一部分**：

- 扩展渲染自定义 UI：`ctx.ui.custom((tui, theme, keybindings, done) => ...)`（`docs/tui.md:93-102`）
- 扩展注册快捷键：`pi.registerShortcut(...)`（`docs/extensions.md:1606`）
- 扩展**替换整个输入编辑器**：`ctx.ui.setEditorComponent((tui, theme, keybindings) => new VimEditor(...))`（`docs/tui.md:904-906`）
- 扩展替换 footer：`ctx.ui.setFooter((tui, theme, footerData) => ...)`（`docs/tui.md:827`）
- 扩展加 widget：`ctx.ui.setWidget(...)`（`docs/tui.md:798-801`）
- 工具自定义渲染：`renderCall` / `renderResult` 返回 `Component`（`docs/tui.md:421`）
- 编译成 Bun 单文件二进制时，`pi-tui` 在 `VIRTUAL_MODULES` 白名单里，让扩展能 `import` 它

`docs/tui.md` 整整 943 行都在教扩展作者怎么写组件，第 1 行原话：

> "pi can create TUI components. Ask it to build one for your use case."

→ **TUI 不是"渲染层"，是 pi 的插件 SDK 的一半。**用 Ink 就意味着扩展作者得写 React，还得跟 pi 共享一个 React 运行时 —— 对一个用 jiti 无沙箱加载任意 .ts 扩展的架构来说，这是不可接受的耦合。

### 6.3 证据 C：那些"库替你做不了"的注释

把散落在代码里的**具体兼容 hack** 汇总成一张表，这是最能说服人的一页：

| # | 场景 | 位置 |
|---|---|---|
| 1 | WezTerm 的 Escape 按下/松开粘连成 `\x1b\x1b[27;...u` | `stdin-buffer.ts:210-230` |
| 2 | Termux 软键盘弹出改变终端高度 → 禁掉高度变化触发的全量重绘 | `tui-main-screen.ts:242-249` |
| 3 | Apple Terminal 不发 Shift+Enter → 读本机修饰键状态伪造 | `terminal.ts:14, 44-47` + `native-modifiers.ts` |
| 4 | Windows libuv 丢修饰键 → 加载原生 `.node` 开 `ENABLE_VIRTUAL_TERMINAL_INPUT` | `terminal.ts:332-366` |
| 5 | tmux popup 把粘贴内容里的控制字节重编码成 CSI-u | `editor.ts:1163-1173` |
| 6 | tmux 是否转发 OSC 8 超链接 → `execSync("tmux display-message ...")` 问它 | `terminal-image.ts:45-62` |
| 7 | 慢速 SSH 上退出时 Kitty key release 泄漏给父 shell | `terminal.ts:59-63, 368-404` |
| 8 | SSH 上缓冲的 Ctrl+D 在退出 raw mode 后关掉父 shell | `terminal.ts:443-446` |
| 9 | `ctrl+z` 挂起期间 resize，SIGWINCH 丢失 | `terminal.ts:152-156` |
| 10 | 国旗 emoji 流式时被劈成两半，宽度要保守取 2 | `utils.ts:200-205` |
| 11 | Caps/Num Lock 被 Kitty 编进修饰位，要掩掉 | `keys.ts:299` |
| 12 | iTerm2 图片协议无法删除/裁剪 → 备用屏里退化成文本 | `README.md:660` |
| 13 | Kitty 图片是"放置"不是字符，差分时必须显式删旧图 | `tui-main-screen.ts:132-144` |
| 14 | 未知终端吞掉 OSC 8 会让 URL 消失 → 默认降级成 `text (url)` | `terminal-image.ts:123-127` |
| 15 | Ghostty 的 `alt+backspace` 需要用户手改配置 | `docs/terminal-setup.md:19-23` |

**15 条，全部有代码或文档出处。**每一条都是"我踩过、我修了"，没有一条是通用 TUI 库会替你处理的。

`docs/terminal-setup.md`（142 行）、`termux.md`（127 行）、`tmux.md`（63 行）、`windows.md`（17 行）—— **349 行用户文档专门讲终端怎么配。**

### 6.4 反证：它确实抄了能抄的

- `StdinBuffer` 明确标注来自 OpenTUI（`stdin-buffer.ts:16-17`，MIT）
- `graphemeWidth` 明确标注基于 string-width 库（`utils.ts:170-171`）
- 键位默认值照抄 GNU readline（见 3.6 节加粗项）
- Markdown 用 `marked`，东亚宽度用 `get-east-asian-width`，测试用 `@xterm/headless`

> 上 PPT 的点：**不是 NIH。是"把算法抄进来，把 IO 和兼容性握在自己手里"。**

---

## 7. 对自建 agent 的启发

### 7.1 必须自己写的（三条，都有本文的证据支撑）

**① 输入层的按键解析。**没有任何库能替你决定"Shift+Enter 在你的产品里是换行还是提交"，也没有库替你处理 Apple Terminal / Windows / tmux / WezTerm 各自的怪癖。pi 花了 `keys.ts` 1 401 行 + `matchesKey()` 385 行。

**② 输出层的宽度契约。**只要你想做增量渲染，就必须精确知道每一行占几列。emoji / CJK / 组合字符 / ANSI 混在一起时，"字符串长度"毫无意义。pi 的做法是**把违约行为变成 crash + crash log**（`tui-main-screen.ts:413-439`），而不是默默截断。

**③ 流式内容的"重建 + 比对"边界。**你的消息组件可以每个 delta 全量重建（简单），但你必须在写终端之前做一次逐行字符串比对（`tui-main-screen.ts:264-274`）。这一条比对是全部性能收益的来源。

### 7.2 可以省掉的（四条）

**① 布局引擎。**主屏模式下 pi **没有**布局，只有 `Container` 纵向拼接（`tui.ts:235-244`）。VStack/HStack/ScrollView 只在全屏模式存在，而全屏**不是默认**（`settings-manager.ts:1129`）。**如果你只做聊天式 agent，"一列往下摞"就够了。**

**② 响应式 / 虚拟 DOM。**pi 是手动 `invalidate()` + `requestRender()`（`docs/tui.md:504`）。组件缓存就是一个 `(text, width)` 二元组（`markdown.ts:153-157`）。

**③ 备用屏 / 鼠标 / 选区 / 图片。**`tui-alt-screen.ts` 805 行 + `terminal-image.ts` 559 行 ≈ **1 364 行，占 src 的 9.6%**，全部可以砍掉不影响核心体验。默认模式根本不进备用屏。

**④ 精细的能力探测。**`detectCapabilities()` 的 12 分支（`terminal-image.ts:68-128`）可以简化成"全部 `{images:null, trueColor:true, hyperlinks:false}`"，代价只是没有内联图片和可点击链接。

### 7.3 最小可用 TUI 的行数预算（基于本文的实测拆解）

| 必须 | 参照 pi 的文件 | 大致行数 |
|---|---|---|
| `Component` 契约 + `Container` + 渲染调度 | `tui.ts` 的 `TuiBase` 骨架（去掉 overlay 约 400 行） | ~250 |
| 主屏差分 `doRender` | `tui-main-screen.ts`（去掉 Kitty 图片相关约 150 行） | ~250 |
| 宽度 + ANSI 切片/换行 | `utils.ts` 的 `graphemeWidth`/`visibleWidth`/`wrapTextWithAnsi`/`truncateToWidth` | ~400 |
| stdin 分帧 | `stdin-buffer.ts` | ~430 |
| 按键匹配（只支持 legacy + 一种现代协议） | `keys.ts` 裁剪版 | ~400 |
| 单个多行编辑器（不要 kill-ring / 补全 / 粘贴折叠） | `editor.ts` 裁剪版 | ~600 |
| `Text` + `Markdown`（用 marked） | `text.ts` + `markdown.ts` 裁剪版 | ~300 |

**≈ 2 600 行**能跑起来一个能用的 agent TUI。pi 的 14 184 行里，剩下的 **11 584 行（82%）是兼容性、全屏模式、图片、鼠标、overlay、自动补全，以及可插拔给扩展用的公共 API**。

### 7.4 三条可以直接抄的设计决策

1. **`render(width) => string[]` 这个契约本身。**没有坐标、没有 buffer、没有生命周期。任何人 20 分钟能写一个组件。整个 `docs/tui.md`（943 行）都建立在这一个签名上。
2. **一帧一次 `write()`，外面包 CSI 2026。**（`tui-main-screen.ts:356/463/495`）无闪烁的最低成本方案，比双缓冲简单一个数量级。
3. **把"全量重绘次数"做成公开可断言的指标。**（`tui.ts:288`、`edit-tool-no-full-redraw.test.ts:143`）UI 性能回归从此可以进 CI，不用靠肉眼。

---

## 8. 最适合上 PPT 的 5 条硬事实

1. **14 184 行源码，14 839 行测试，运行时只有 2 个依赖（算东亚宽度的 `get-east-asian-width` + Markdown 的 `marked`）。全仓 `grep` 不到任何 TUI 框架 —— 没有 Ink、没有 blessed、没有 React。**
   `packages/tui/package.json:37-44`；`find packages/tui/src -name '*.ts' | xargs wc -l` = 14184；`packages/tui/test` = 14839

2. **渲染是"每帧整树重渲 → 与上一帧逐行字符串比对 → 只把 `[firstChanged, lastChanged]` 这一段写进终端 → 整个字节流包在 CSI 2026 同步输出里一次 `write()`"。上限 62.5 fps（`MIN_RENDER_INTERVAL_MS = 16`）。**
   `tui-main-screen.ts:163`（整树渲染）、`:264-274`（逐行比对）、`:385-442`（只写变化段）、`:356/:463/:495`（CSI 2026 + 单次 write）、`tui.ts:332`（16ms）

3. **一行超过终端宽度 = 主动崩溃**：先把所有行连宽度 dump 进 `pi-crash.log`，恢复终端状态，再抛错说"用 `visibleWidth()` 量、用 `truncateToWidth()` 截"。因为一旦终端自己折了行，差分渲染的行号映射就永久错位。
   `tui-main-screen.ts:413-439`

4. **粘贴超过 10 行或 1000 字符，输入框里折叠成一个原子 token `[paste #1 +500 lines]`，原文存在 `Map` 里，提交时才展开。**这个 marker 在光标移动、删词、软换行时被当成**单个字素**处理。
   `components/editor.ts:1197-1212`（阈值与 marker）、`:309`（`pastes` Map）、`:34-51`（原子分词）、`:985/:998`（展开）

5. **那 14k 行的真正去处是 15 条具体的终端怪癖修复**：Termux 软键盘改高度会重播全部历史、Apple Terminal 不发 Shift+Enter 要读本机修饰键、Windows 要加载原生 `.node` 才能区分 Shift+Tab、tmux 要 `execSync` 问它转不转发 OSC 8、慢速 SSH 上退出时 Kitty key release 会漏给父 shell、流式时半个国旗 emoji 宽度必须保守取 2……
   见 6.3 节表格，逐条有 `路径:行号`

---

*取证完成 2026-08-02，基线 commit `583f153`。*
