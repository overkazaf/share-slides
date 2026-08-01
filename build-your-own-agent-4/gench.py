#!/usr/bin/env python3
"""生成 7 个章扉页：章号 / 章名 / 本章要回答的问题 / 本章小目录 / 读完的收获 / 全书进度。"""
import pathlib

S = pathlib.Path(__file__).parent / 'slides'

CH = [
    ('s02b-ch1.html', '01', '定义', 'cyan', 1,
     'Agent 到底是什么？',
     '先把词说清楚。这一章不谈技术细节，只解决一件事：<b>什么算 agent，什么不算</b> —— 以及为什么这个边界值得认真划。',
     '读完这章你会知道：判断一个系统是不是 agent，只需要看一条 —— <b>下一步做什么，是代码写死的，还是模型现场决定的</b>。',
     [('06', '什么是 Agent', '能自己决定下一步、并能真的动手改变环境的循环'),
      ('07', '决策权谱系', '对话 → 提示链 → 工作流 → 智能体 → 多智能体，是连续的')]),

    ('s04b-ch2.html', '02', '演进', 'amber', 2,
     '它是怎么一步步走到今天的？',
     '这一章全部用<b>可核查的日期</b>串起来：arXiv 提交日、GitHub 首次 commit、npm 发布时间戳、官方博客。凡是只在二手转述里见过的，一律不上页。',
     '读完这章你会知道：2023 年那场热潮为什么退了，以及 2025 年下半年<b>真正的转折点发生在哪一天</b>。',
     [('09', '演进 I（2022–2023）', '从会推理，到会动手，然后撞墙'),
      ('10', '演进 II（2024–2026）', '范式转移：从「怎么跟模型说话」到「怎么给模型搭工位」'),
      ('11', '关键人物谱', '每个节点背后是谁 —— 本场两个主角都不在 AI 圈')]),

    ('s07b-ch3.html', '03', '原理', 'violet', 3,
     '拆开看，到底有哪些技术点？',
     '本场最长的一章，12 页。每页一个技术点，讲清<b>它解决什么问题、原理是什么、代价在哪</b>。所有实现细节都对着 pi 与 oh-my-pi 的源码取证。',
     '读完这章你会知道：所谓「造一个 agent」，具体要造的是<b>哪五层</b>，以及每层最容易在哪翻车。',
     [('13–14', '全景与 harness', '七层栈 · 包在模型外面的那台机器'),
      ('15–16', '循环与图', '主循环状态机 · 会话树与 DAG 编排'),
      ('17–18', '上下文与压缩', '注意力预算 · 摘要式压缩与位图帧压缩'),
      ('19–20', 'SKILL 与工具', '渐进式披露 · 工具集是接口设计'),
      ('21–22', '编排与多智能体', '五种 workflow 模式 · 相隔 24 小时的对撞'),
      ('23–24', '扩展点与记忆', '六种扩展方式 · 三个记忆尺度、两个纠偏时机')]),

    ('s19b-ch4.html', '04', '场景', 'rose', 4,
     '什么时候该用，什么时候千万别用？',
     '技术讲完了，该讲边界。这一章只有一页，但它可能是最该被记住的一页 —— <b>因为它管的是「别做什么」</b>。',
     '读完这章你会知道：上线前该问自己哪三个问题，以及哪四类事情<b>无论如何都别交给 agent</b>。',
     [('26', '适用场景矩阵', '反馈可得性 × 任务确定性 —— 甜点区只有一格')]),

    ('s20b-ch5.html', '05', '全景', 'slate', 5,
     '别人都怎么做的？我该选谁？',
     '把 2026 年主流的 coding agent 放进同一张坐标图。重点不是排名，是<b>看清分野在哪</b> —— 以及那个空着的象限说明了什么。',
     '读完这章你会知道：选型时真正该看的维度不是「谁更强」，而是<b>「这层壳能不能改」</b>。',
     [('28', '主流 coding agent 全景', '内核大小 × 开源程度 · 三种交互面 · 选型血泪')]),

    ('s21b-ch6.html', '06', '样本', 'emerald', 6,
     '极客圈为什么偏爱 pi？oh my pi 又是什么？',
     '前面讲的都是通则，这一章看两个具体样本 —— 一个把「最小」做到极致，一个把「最全」做到极致。<b>它们出自同一条血脉，却走向了两个反方向</b>。',
     '读完这章你会知道：为什么 pi 的卖点是一份「刻意不做」的清单，以及维护一个深度 fork 的成本该<b>怎么量化</b>。',
     [('30', 'pi 的「刻意不做」清单', 'No MCP / No sub-agents / No permission popups…'),
      ('31', 'oh my pi 与 FORK.md', '63 万行 TS + 7 万行 Rust，以及那套 tier 成本模型')]),

    ('s23b-ch7.html', '07', '实践', 'orange', 7,
     '我每天在用什么？我要造什么？',
     '从「别人怎么做」回到「我怎么做」。先摊开我的武器库和选型依据，再讲清楚<b>为什么通用 agent 干逆向不行</b>，最后是 re-agent。',
     '读完这章你会知道：一个垂直领域的 agent 该怎么起步，以及<b>为什么这件事现在一个人就能干</b>。',
     [('33', '日常武器库', '模型特点 · 选型依据 · 可量化对照'),
      ('34', '逆向的七道坎', '每一条都挂了可核查的来源'),
      ('35', 're-agent 架构', '把七道坎写进骨架里'),
      ('36', 're-agent 预告', '给谁用 · 为什么是我 · 为什么适合一人公司')]),
]

for fn, no, name, color, idx, q, desc, gain, items in CH:
    prog = ''.join(
        '<span class="%s"></span>' % ('on' if i + 1 == idx else ('done' if i + 1 < idx else ''))
        for i in range(7))
    lis = '\n'.join(
        '        <li><span class="n">%s</span><span class="t">%s<i>%s</i></span></li>' % (p, t, s)
        for p, t, s in items)
    html = f'''<section class="slide chapter" data-ch="CH{no} {name}" data-title="第 {no} 章 · {name}">
  <div class="chapter-inner">
    <div>
      <div class="ch-no">{no}</div>
      <h1>{name}</h1>
      <div class="ch-q"><b>{q}</b></div>
      <div class="ch-sub">{desc}</div>
      <div class="ch-prog">{prog}</div>
    </div>
    <div>
      <ul class="ch-list">
        <div class="ch-list-h">本章内容</div>
{lis}
      </ul>
      <div class="ch-sub" style="margin-top:22px;border-color:var(--{color})">{gain}</div>
    </div>
  </div>
  <div class="s-foot">
    <span class="src">第 {no} 章 / 共 7 章</span>
    <span class="spacer"></span>
    <span class="pg"></span>
  </div>
</section>
'''
    (S / fn).write_text(html, encoding='utf-8')
    print('wrote', fn)
