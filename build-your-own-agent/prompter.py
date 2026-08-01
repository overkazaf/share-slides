#!/usr/bin/env python3
"""把 script/*.md 编成一个自包含的提词器页面 prompter.html。

用法：python3 prompter.py && open prompter.html

页面里：
  ← →     上/下一页（跟 slides 的页码一一对应）
  空格/↓  往下滚一屏   ↑ 往上滚
  A       自动滚动开关，[ ] 调速度
  + -     调字号        F 展开/收起全文（默认只看提词）
  /       搜索          O 页面总览
"""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
SCRIPT = ROOT / "script"
OUT = ROOT / "prompter.html"

SEC_RE = re.compile(r"^## +P(\d+) +·? *(.*)$")
# 讲稿里的小节标题，如 **怎么讲**：
BLOCK_RE = re.compile(r"^\*\*(提词|一句话主旨|怎么讲|别漏了说|可能被问|过渡到下一页|收尾)\*\*[：:]?\s*(.*)$")

BLOCK_KEY = {
    "提词": "cue",
    "一句话主旨": "gist",
    "怎么讲": "say",
    "别漏了说": "must",
    "可能被问": "qa",
    "过渡到下一页": "next",
    "收尾": "next",
}


def inline(text):
    """极简 markdown 行内渲染。"""
    t = html.escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    # 舞台提示 [停] [慢] [指屏] 高亮
    t = re.sub(r"\[([^\]\[]{1,12})\]", r'<span class="cue">[\1]</span>', t)
    return t


def render_lines(lines):
    """把一段讲稿行渲染成 HTML。"""
    out, in_ul = [], False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if in_ul and line.startswith("  "):  # 列表项的续行（Q/A 的 A 行）
            out.append(f"<li class='cont'>{inline(line.strip())}</li>")
            continue
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if line.startswith("> "):
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        else:
            out.append(f"<p>{inline(line)}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def parse():
    pages = {}
    for f in sorted(SCRIPT.glob("*.md")):
        if f.name == "README.md":
            continue
        cur = None
        for raw in f.read_text(encoding="utf-8").splitlines():
            m = SEC_RE.match(raw)
            if m:
                cur = {"n": int(m.group(1)), "title": m.group(2).strip(),
                       "blocks": {}, "order": []}
                pages[cur["n"]] = cur
                key = None
                continue
            if cur is None:
                continue
            if raw.strip() == "---":
                cur = None
                continue
            bm = BLOCK_RE.match(raw)
            if bm:
                key = BLOCK_KEY[bm.group(1)]
                cur["blocks"].setdefault(key, [])
                cur["order"].append(key) if key not in cur["order"] else None
                if bm.group(2).strip():
                    cur["blocks"][key].append(bm.group(2))
                continue
            if cur["order"]:
                cur["blocks"][cur["order"][-1]].append(raw)
    return [pages[k] for k in sorted(pages)]


LABEL = {"cue": "提词", "gist": "一句话主旨", "say": "怎么讲", "must": "别漏了说",
         "qa": "可能被问", "next": "过渡"}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--fs:26px}
body{background:#05070d;color:#e8edf5;font-family:"PingFang SC","Microsoft YaHei",
 -apple-system,"JetBrains Mono",monospace;line-height:1.9;-webkit-font-smoothing:antialiased}
#bar{position:fixed;top:0;left:0;right:0;height:46px;display:flex;align-items:center;gap:14px;
 padding:0 18px;background:rgba(5,7,13,.94);border-bottom:1px solid #182234;z-index:20;font-size:13px}
#bar .pg{color:#22d3ee;font-weight:700;font-size:15px;min-width:60px}
#bar .ttl{color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
#bar .st{color:#475569;font-size:11px;white-space:nowrap}
#bar .st b{color:#34d399}
#bar button{background:#111a2b;color:#94a3b8;border:1px solid #223049;border-radius:6px;
 padding:4px 10px;font:inherit;font-size:12px;cursor:pointer}
#bar button:hover{color:#e8edf5;border-color:#34d399}
#prog{position:fixed;top:46px;left:0;height:2px;background:#22d3ee;z-index:21;width:0;transition:width .2s}
#wrap{padding:86px 6vw 60vh;max-width:1500px;margin:0 auto}
.pg-sec{display:none}
.pg-sec.on{display:block;animation:fade .18s ease}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
h2{font-size:calc(var(--fs) * .82);color:#fff;font-weight:700;margin-bottom:26px;line-height:1.5;
 border-left:4px solid #22d3ee;padding-left:14px}
.blk{margin:0 0 34px}
.blk>.lb{display:inline-block;font-size:12px;letter-spacing:.12em;color:#0b1220;background:#64748b;
 padding:2px 10px;border-radius:4px;margin-bottom:14px;font-weight:700}
.blk.cue>.lb{background:#22d3ee}
.blk.gist>.lb{background:#a78bfa}.blk.say>.lb{background:#34d399}
.blk.must>.lb{background:#fbbf24}.blk.qa>.lb{background:#fb923c}.blk.next>.lb{background:#22d3ee}
.blk.cue{margin-bottom:28px}
.blk.cue ul{margin:0}
.blk.cue li{font-size:calc(var(--fs) * 1.34);color:#fff;font-weight:600;line-height:1.62;
 padding-left:30px;margin-bottom:16px;letter-spacing:.01em}
.blk.cue li::before{content:"—";color:#22d3ee;font-weight:700}
.blk.cue li b{color:#34d399}
.blk.cue .cue{color:#fb7185;font-size:.7em;vertical-align:middle}
.blk.gist p{font-size:calc(var(--fs) * .96);color:#c4b5fd}
.blk.say p{font-size:var(--fs);color:#f1f5f9;margin-bottom:22px}
.blk.must,.blk.qa,.blk.next{font-size:calc(var(--fs) * .72);color:#94a3b8}
.blk.next p{color:#67e8f9}
p{margin-bottom:14px}
ul{list-style:none;margin-bottom:14px}
li{padding-left:20px;position:relative;margin-bottom:9px}
li::before{content:"▸";position:absolute;left:0;color:#475569}
li.cont{padding-left:34px;color:#cbd5e1}
li.cont::before{content:""}
b{color:#fff;font-weight:700}
.blk.must b,.blk.qa b{color:#e2e8f0}
i{font-style:normal;color:#fbbf24}
code{background:#111a2b;color:#67e8f9;padding:1px 6px;border-radius:4px;font-size:.86em}
.cue{color:#fb7185;font-weight:700}
blockquote{border-left:3px solid #334155;padding-left:14px;color:#94a3b8;margin-bottom:14px}
body.cues .blk.gist,body.cues .blk.say,body.cues .blk.must,body.cues .blk.qa{display:none}
body.cues .blk.next{font-size:calc(var(--fs) * .78)}
/* 没写提词块的页面，收起模式下退回显示「怎么讲」 */
body.cues .pg-sec.nocue .blk.say,body.cues .pg-sec.nocue .blk.gist{display:block}
#ov{position:fixed;inset:0;background:rgba(3,6,14,.97);z-index:40;display:none;overflow:auto;padding:70px 5vw}
#ov.on{display:block}
#ov .g{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
#ov .c{background:#0c1421;border:1px solid #1e293b;border-radius:8px;padding:11px 13px;cursor:pointer;font-size:13px}
#ov .c:hover{border-color:#34d399}
#ov .c .n{color:#22d3ee;font-weight:700;margin-right:8px}
#ov .c .t{color:#cbd5e1}
#find{position:fixed;top:60px;left:50%;transform:translateX(-50%);z-index:50;display:none;
 background:#0c1421;border:1px solid #334155;border-radius:8px;padding:8px 12px}
#find.on{display:block}
#find input{background:transparent;border:none;outline:none;color:#e8edf5;font:inherit;font-size:15px;width:340px}
mark{background:#fbbf24;color:#0b1220;border-radius:2px}
"""

JS = """
const secs=[...document.querySelectorAll('.pg-sec')];
let i=0, auto=false, spd=1.1, raf=null;
const bar=document.getElementById('pgno'), ttl=document.getElementById('pgttl'),
      prog=document.getElementById('prog'), st=document.getElementById('st');
function show(n){
  i=Math.max(0,Math.min(secs.length-1,n));
  secs.forEach((s,k)=>s.classList.toggle('on',k===i));
  const s=secs[i];
  bar.textContent=s.dataset.n+'/'+DECK_TOTAL;
  ttl.textContent=s.dataset.title;
  prog.style.width=((i+1)/secs.length*100)+'%';
  window.scrollTo(0,0);
  localStorage.setItem('prompter-pos',i);
}
function tick(){ if(auto){ window.scrollBy(0,spd); } raf=requestAnimationFrame(tick); }
function setAuto(v){ auto=v; renderStatus(); }
function setMode(){
  const full=!document.body.classList.contains('cues');
  document.getElementById('btn-full').textContent = full? '收起全文 F' : '展开全文 F';
  renderStatus();
}
function renderStatus(){
  const full=!document.body.classList.contains('cues');
  st.innerHTML = (full?'全文':'<b>提词</b>') + ' · ' + (auto? '自动滚 ×'+spd.toFixed(1) : '手动');
}
document.addEventListener('keydown',e=>{
  if(document.getElementById('find').classList.contains('on') && e.key!=='Escape') return;
  const k=e.key;
  if(k==='ArrowRight'||k==='PageDown'){show(i+1);e.preventDefault()}
  else if(k==='ArrowLeft'||k==='PageUp'){show(i-1);e.preventDefault()}
  else if(k===' '){window.scrollBy(0,window.innerHeight*0.72);e.preventDefault()}
  else if(k==='ArrowDown'){window.scrollBy(0,90);e.preventDefault()}
  else if(k==='ArrowUp'){window.scrollBy(0,-90);e.preventDefault()}
  else if(k==='a'||k==='A'){setAuto(!auto)}
  else if(k===']'){spd=Math.min(6,spd+0.3);setAuto(auto)}
  else if(k==='['){spd=Math.max(0.2,spd-0.3);setAuto(auto)}
  else if(k==='+'||k==='='){bump(2)}
  else if(k==='-'){bump(-2)}
  else if(k==='f'||k==='F'){
    const full=document.body.classList.toggle('cues')===false;
    localStorage.setItem('prompter-full',full?'1':'0'); setMode();
  }
  else if(k==='o'||k==='O'){document.getElementById('ov').classList.toggle('on')}
  else if(k==='/'){openFind();e.preventDefault()}
  else if(k==='Escape'){document.getElementById('ov').classList.remove('on');closeFind()}
});
function bump(d){
  const cur=parseInt(getComputedStyle(document.documentElement).getPropertyValue('--fs'));
  const v=Math.max(14,Math.min(52,cur+d));
  document.documentElement.style.setProperty('--fs',v+'px');
  localStorage.setItem('prompter-fs',v);
}
function openFind(){const f=document.getElementById('find');f.classList.add('on');f.querySelector('input').focus()}
function closeFind(){const f=document.getElementById('find');f.classList.remove('on');f.querySelector('input').blur()}
document.getElementById('findi').addEventListener('keydown',e=>{
  if(e.key==='Escape'){closeFind();return}
  if(e.key!=='Enter')return;
  const q=e.target.value.trim(); if(!q)return;
  for(let k=1;k<=secs.length;k++){
    const j=(i+k)%secs.length;
    if(secs[j].textContent.includes(q)){show(j);closeFind();break}
  }
});
document.querySelectorAll('#ov .c').forEach(c=>c.addEventListener('click',()=>{
  show(+c.dataset.i); document.getElementById('ov').classList.remove('on');
}));
document.getElementById('btn-prev').onclick=()=>show(i-1);
document.getElementById('btn-next').onclick=()=>show(i+1);
document.getElementById('btn-auto').onclick=()=>setAuto(!auto);
document.getElementById('btn-ov').onclick=()=>document.getElementById('ov').classList.toggle('on');
document.getElementById('btn-full').onclick=()=>{
  const full=document.body.classList.toggle('cues')===false;
  localStorage.setItem('prompter-full',full?'1':'0'); setMode();
};
const fs=localStorage.getItem('prompter-fs');
if(fs) document.documentElement.style.setProperty('--fs',fs+'px');
if(localStorage.getItem('prompter-full')!=='1') document.body.classList.add('cues');
show(+(localStorage.getItem('prompter-pos')||0));
setAuto(false); setMode(); tick();
"""


def build():
    pages = parse()
    if not pages:
        raise SystemExit("script/ 里没解析到任何 P<n> 小节")

    body, cards = [], []
    for idx, p in enumerate(pages):
        blocks = []
        for key in ["cue", "gist", "say", "must", "qa", "next"]:
            if key not in p["blocks"]:
                continue
            content = render_lines(p["blocks"][key])
            if not content.strip():
                continue
            blocks.append(
                f'<div class="blk {key}"><span class="lb">{LABEL[key]}</span>{content}</div>')
        t = html.escape(p["title"])
        nocue = "" if "cue" in p["blocks"] else " nocue"
        body.append(
            f'<section class="pg-sec{nocue}" data-n="{p["n"]}" data-title="{t}">'
            f'<h2>P{p["n"]} · {t}</h2>{"".join(blocks)}</section>')
        cards.append(
            f'<div class="c" data-i="{idx}"><span class="n">{p["n"]}</span>'
            f'<span class="t">{t}</span></div>')

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>提词器 · 如何打造自己的 Agent（{len(pages)} 页）</title>
<style>{CSS}</style></head><body>
<div id="bar">
  <span class="pg" id="pgno">1/{len(pages)}</span>
  <span class="ttl" id="pgttl"></span>
  <span class="st" id="st"></span>
  <button id="btn-prev">‹ 上一页</button>
  <button id="btn-next">下一页 ›</button>
  <button id="btn-full">展开全文 F</button>
  <button id="btn-auto">自动滚 A</button>
  <button id="btn-ov">总览 O</button>
</div>
<div id="prog"></div>
<div id="find"><input id="findi" placeholder="搜讲稿内容，回车跳转，Esc 关闭"></div>
<div id="wrap">{''.join(body)}</div>
<div id="ov"><div class="g">{''.join(cards)}</div></div>
<script>const DECK_TOTAL={len(pages)};{JS}</script>
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"✓ {OUT}  ({len(pages)} 页)")


if __name__ == "__main__":
    build()
