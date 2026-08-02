#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成第四讲的七张章节扉页"""
import pathlib

ROOT = pathlib.Path(__file__).parent
SL = ROOT / "slides"

CH = [
    ("01", "起手", "cyan", "s03-ch1",
     "为什么还要第四个 harness？",
     "第一讲留了一份「逆向七道坎」清单。这一章先<b>逐条回来交账</b>，再把体量摊开。",
     [("05", "七道坎交账", "四条已落地 · 两条只做了一半 · 一条有实打实的洞"),
      ("06", "体量与形态", "两万四千行 · 一个外部依赖 · 五天 · 一个人")],
     "本讲每个数字都自己跑命令量过，<b>不引用项目自己写的数</b> —— 因为它自己那张对比图的数就对不上。"),

    ("02", "灵感来源", "violet", "s06-ch2",
     "从哪里抄的，又刻意不抄什么？",
     "抄什么容易讲，<b>不抄什么才见判断</b>。这一章两页，一页讲流入，一页讲取舍。",
     [("08", "三条上游", "pi 给结构 · omp 给代价意识 · Claude Code 给 skill 格式"),
      ("09", "四个不一样的选择", "换语言 · 不造 provider · 换安全姿态 · 换优化目标")],
     "硬证据：7 张架构图里<b>有 2 张画的不是自己</b>，而且首个 commit 就在 —— 研究竞品是设计输入。"),

    ("03", "实现原理", "emerald", "s09-ch3",
     "一个人写的 agent 内核，长什么样？",
     "本章是全场重头。<b>五页拆完内核</b>：循环 · 包边界 · 双模型 · caveman · 上下文。",
     [("11", "一个函数就是全部控制流", "241 行，骨架和教科书一模一样，差别全在包在外面那层"),
      ("12", "包依赖为什么这么指", "最大的包不是内核，是界面 —— 而这正好是个设计声明"),
      ("13", "两个座位", "规划一个模型，动手另一个，默认就跨厂商"),
      ("14", "caveman 模式", "模型太谨慎不干活，解法不是换说法，是换结构"),
      ("15", "上下文三道闸", "逆向最要命的是工具输出那道")],
     "时间不够，整场只抓这一章 —— <b>这五页的结构可以直接抄进你自己的 harness</b>。"),

    ("04", "功能点", "orange", "s15-ch4",
     "它到底给了你哪些趁手的东西？",
     "三页：<b>不花钱的那条路</b>、工具与知识、以及「你能看着它干活」。",
     [("17", "廉价路", "52 个命令里约 49 个零 token，11 个直接绕过 agent loop"),
      ("18", "工具 · skill · 知识库", "24 / 33 / 而幻觉引用被显式记了账"),
      ("19", "看着它干活", "回合还在跑，你就能插话、改任务、换模型")],
     "本章每页仍然配一条代价 —— <b>零 token 很爽，但绕过 loop 也绕过了 loop 上的闸</b>。"),

    ("05", "三方对比", "slate", "s19-ch5",
     "和 pi、oh-my-pi 比，差异到底在哪？",
     "本章顺序是刻意的：<b>先摆矩阵 → 再拆自己的台 → 最后才说剩下什么</b>。",
     [("21", "三方对比矩阵", "三个仓库都在本机，同一批命令量一遍"),
      ("22", "自我拆台", "六条其实只是配置，十条明确落后"),
      ("23", "剩下四条", "换语言换分发 · 把别的 agent 当 provider · 隔离委派 · 一个 interface")],
     "讲自家项目最大的风险是读者的怀疑不够。<b>所以先花一整页把水分挤干。</b>"),

    ("06", "能干什么", "amber", "s23-ch6",
     "具体能干什么？举得出例子吗？",
     "两页：一个<b>端到端的完整链路</b>，四个<b>能对回 skill 原文行号</b>的场景。",
     [("25", "端到端案例", "最值钱的不是它解出来了，是它反例也跑了一次"),
      ("26", "四个场景", "CTF 分诊 · APK 签名 · SO 转服务 · 混淆墙")],
     "本章取证等级是全场最低的一章 —— <b>旗舰案例的 transcript 不在仓库里，标 [B]</b>，页上写明。"),

    ("07", "代价与规划", "rose", "s26-ch7",
     "洞在哪，接下来往哪走？",
     "两页收口：<b>先把安全闸的洞摊开</b>，再谈规划；最后把四讲一起收一次。",
     [("28", "代价页与规划页", "七个洞 · 明写的规划只有一句 · 其余是我从代码缝里推的"),
      ("29", "四讲收口", "通用层开源之后，壁垒到底在哪")],
     "规划分两栏是硬规矩：<b>项目承诺的，和我推断的，不许混为一谈。</b>"),
]

TOTAL = len(CH)

TPL = """<section class="slide chapter" data-ch="CH{no} {name}" data-title="第 {no} 章 · {name}">
  <div class="chapter-inner">
    <div>
      <div class="ch-no">{no}</div>
      <h1>{name}</h1>
      <div class="ch-q"><b>{q}</b></div>
      <div class="ch-sub">{sub}</div>
      <div class="ch-prog">{prog}</div>
    </div>
    <div>
      <ul class="ch-list">
        <div class="ch-list-h">本章内容</div>
{items}
      </ul>
      <div class="ch-sub" style="margin-top:22px;border-color:var(--{color})">{tail}</div>
    </div>
  </div>
  <div class="s-foot">
    <span class="src">第 {no} 章 / 共 {total} 章</span>
    <span class="spacer"></span>
    <span class="pg"></span>
  </div>
</section>
"""

for idx, (no, name, color, fname, q, sub, items, tail) in enumerate(CH):
    prog = "".join(
        '<span class="%s"></span>' % ("done" if i < idx else ("on" if i == idx else ""))
        for i in range(TOTAL))
    items_html = "\n".join(
        '        <li><span class="n">%s</span><span class="t">%s<i>%s</i></span></li>' % it
        for it in items)
    html = TPL.format(no=no, name=name, color=color, q=q, sub=sub,
                      prog=prog, items=items_html, tail=tail, total=TOTAL)
    (SL / (fname + ".html")).write_text(html, encoding="utf-8")
    print("✓", fname)
