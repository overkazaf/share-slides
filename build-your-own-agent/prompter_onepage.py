#!/usr/bin/env python3
"""把 script/*.md 编成**一页**提词器 prompter.html。

跟分页版的区别：全场 26 页的提词摊在同一页上，从头滚到尾。
每段开头有一条醒目的「▶ 切到 P{n}」横幅 —— 滚到它，就是该你按翻页键的时候。
顶部固定条实时显示「现在讲哪页 / 下一步切到哪页」。

用法：python3 prompter_onepage.py && open prompter.html
键位：↓ / 空格 下一段（自动滚到位）· ↑ 上一段 · F 展开全文 · + - 字号 · G 回到顶部
"""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
SCRIPT = ROOT / "script"
OUT = ROOT / "prompter.html"

SEC_RE = re.compile(r"^## +P(\d+) +·? *(.*)$")
BLOCK_RE = re.compile(r"^\*\*(提词|一句话主旨|怎么讲|别漏了说|可能被问|过渡到下一页|收尾)\*\*[：:]?\s*(.*)$")
KEY = {"提词": "cue", "一句话主旨": "gist", "怎么讲": "say", "别漏了说": "must",
       "可能被问": "qa", "过渡到下一页": "next", "收尾": "next"}


def inline(t):
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\[([^\]\[]{1,12})\]", r'<i class="cue-tag">[\1]</i>', t)
    return t


def render(lines):
    out, ul = [], False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if ul:
                out.append("</ul>"); ul = False
            continue
        if line.startswith(("- ", "* ")):
            if not ul:
                out.append("<ul>"); ul = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if ul and line.startswith("  "):
            out.append(f"<li class='cont'>{inline(line.strip())}</li>")
            continue
        if ul:
            out.append("</ul>"); ul = False
        out.append(f"<p>{inline(line[2:] if line.startswith('> ') else line)}</p>")
    if ul:
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
                cur = {"n": int(m.group(1)), "title": m.group(2).strip(), "b": {}, "order": []}
                pages[cur["n"]] = cur
                continue
            if cur is None or raw.strip() == "---":
                if raw.strip() == "---":
                    cur = None
                continue
            bm = BLOCK_RE.match(raw)
            if bm:
                k = KEY[bm.group(1)]
                cur["b"].setdefault(k, [])
                if k not in cur["order"]:
                    cur["order"].append(k)
                if bm.group(2).strip():
                    cur["b"][k].append(bm.group(2))
                continue
            if cur["order"]:
                cur["b"][cur["order"][-1]].append(raw)
    return [pages[k] for k in sorted(pages)]


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--fs:23px}
body{background:#05070d;color:#e8edf5;line-height:1.85;
 font-family:"PingFang SC","Microsoft YaHei",-apple-system,"JetBrains Mono",monospace;
 -webkit-font-smoothing:antialiased;padding-bottom:70vh}
#bar{position:fixed;top:0;left:0;right:0;z-index:30;display:flex;align-items:center;gap:16px;
 height:52px;padding:0 20px;background:rgba(5,7,13,.96);border-bottom:1px solid #1b2537;font-size:13px}
#bar .now{color:#22d3ee;font-weight:700;font-size:16px;white-space:nowrap}
#bar .ttl{color:#94a3b8;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#bar .nxt{color:#0b1220;background:#fbbf24;font-weight:700;padding:5px 12px;border-radius:6px;white-space:nowrap}
#bar .keys{color:#475569;font-size:11px;white-space:nowrap}
#prog{position:fixed;top:52px;left:0;height:2px;background:#22d3ee;z-index:31;width:0}
#wrap{max-width:1180px;margin:0 auto;padding:80px 5vw 0}
section{padding:8px 0 26px;border-bottom:1px dashed #16203200}
section.on .flag{background:#22d3ee;color:#04121a}
section.on{background:linear-gradient(90deg,rgba(34,211,238,.06),transparent 60%)}
.flag{display:inline-flex;align-items:center;gap:10px;background:#101a2b;color:#7dd3fc;
 border:1px solid #22d3ee55;border-radius:8px;padding:6px 14px;font-weight:700;
 font-size:calc(var(--fs)*.72);letter-spacing:.02em}
.flag .pg{font-size:calc(var(--fs)*.92)}
h2{font-size:calc(var(--fs)*.82);color:#fff;margin:14px 0 16px;font-weight:700;line-height:1.5}
.cue li{font-size:calc(var(--fs)*1.12);color:#fff;font-weight:600;margin:0 0 12px;padding-left:30px;
 position:relative;line-height:1.6}
.cue li::before{content:"—";position:absolute;left:0;color:#22d3ee}
.cue li b{color:#34d399}
.cue-tag{font-style:normal;color:#fb7185;font-weight:700;font-size:.78em}
.next{margin-top:14px;color:#67e8f9;font-size:calc(var(--fs)*.7);border-left:3px solid #164e63;padding-left:12px}
.full{display:none;margin-top:16px;border-left:2px solid #1e293b;padding-left:16px}
body.full .full{display:block}
.full h4{color:#64748b;font-size:12px;letter-spacing:.1em;margin:14px 0 6px;font-weight:700}
.full p,.full li{font-size:calc(var(--fs)*.68);color:#94a3b8;margin-bottom:8px}
.full li{padding-left:18px;position:relative;list-style:none}
.full li::before{content:"▸";position:absolute;left:0;color:#334155}
.full li.cont{padding-left:32px}.full li.cont::before{content:""}
.full b{color:#cbd5e1}
code{background:#111a2b;color:#67e8f9;padding:1px 6px;border-radius:4px;font-size:.85em}
ul{list-style:none}
hr{border:none;border-top:1px solid #111a29;margin:6px 0 0}
@media print{#bar,#prog{display:none}body{background:#fff;color:#000;padding:0}
 .flag{border:1px solid #000;color:#000;background:#eee}.cue li{color:#000}}
"""

JS = """
const secs=[...document.querySelectorAll('section')];
const bar=document.getElementById('now'),ttl=document.getElementById('ttl'),
      nxt=document.getElementById('nxt'),prog=document.getElementById('prog');
let i=0;
function paint(){
  secs.forEach((s,k)=>s.classList.toggle('on',k===i));
  const s=secs[i];
  bar.textContent='你在讲　第 '+s.dataset.n+' 页';
  ttl.textContent=s.dataset.title;
  const n=secs[i+1];
  nxt.textContent = n ? ('讲完这段 → 翻到第 '+n.dataset.n+' 页') : '讲完啦 · 留时间答问';
  prog.style.width=((i+1)/secs.length*100)+'%';
  localStorage.setItem('op-pos',i);
}
function go(k){ i=Math.max(0,Math.min(secs.length-1,k));
  window.scrollTo({top:secs[i].offsetTop-70,behavior:'smooth'}); paint(); }
// 手动滚动时同步高亮
let t=null;
window.addEventListener('scroll',()=>{ clearTimeout(t); t=setTimeout(()=>{
  const y=window.scrollY+90; let k=0;
  secs.forEach((s,j)=>{ if(s.offsetTop<=y) k=j; });
  if(k!==i){ i=k; paint(); }
},80);});
document.addEventListener('keydown',e=>{
  const k=e.key;
  if(k==='ArrowDown'||k===' '||k==='PageDown'){go(i+1);e.preventDefault()}
  else if(k==='ArrowUp'||k==='PageUp'){go(i-1);e.preventDefault()}
  else if(k==='g'||k==='G'){go(0)}
  else if(k==='f'||k==='F'){document.body.classList.toggle('full');
    localStorage.setItem('op-full',document.body.classList.contains('full')?'1':'0')}
  else if(k==='+'||k==='='){bump(2)} else if(k==='-'){bump(-2)}
});
function bump(d){const c=parseInt(getComputedStyle(document.documentElement).getPropertyValue('--fs'));
  const v=Math.max(14,Math.min(46,c+d));document.documentElement.style.setProperty('--fs',v+'px');
  localStorage.setItem('op-fs',v);}
const fs=localStorage.getItem('op-fs'); if(fs)document.documentElement.style.setProperty('--fs',fs+'px');
if(localStorage.getItem('op-full')==='1')document.body.classList.add('full');
go(+(localStorage.getItem('op-pos')||0));
"""


def build():
    pages = parse()
    body, LB = [], {"gist": "一句话主旨", "say": "怎么讲", "must": "别漏了说", "qa": "可能被问"}
    for p in pages:
        t = html.escape(p["title"])
        cue = render(p["b"].get("cue", [])) or "<p>（这页还没写提词，看下面的详细讲法）</p>"
        nxt = render(p["b"].get("next", []))
        full = "".join(f'<h4>{LB[k]}</h4>{render(p["b"][k])}'
                       for k in ["gist", "say", "must", "qa"] if p["b"].get(k))
        body.append(
            f'<section data-n="{p["n"]}" data-title="{t}">'
            f'<div class="flag"><span class="pg">这里翻到　第 {p["n"]} 页</span></div>'
            f'<h2>{t}</h2><div class="cue">{cue}</div>'
            + (f'<div class="next">接下去这么说 · {nxt}</div>' if nxt else "")
            + (f'<div class="full">{full}</div>' if full else "")
            + "<hr></section>")

    OUT.write_text(f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>提词稿 · 如何打造自己的 Agent · 第一讲</title>
<style>{CSS}</style></head><body>
<div id="bar"><span class="now" id="now"></span><span class="ttl" id="ttl"></span>
<span class="nxt" id="nxt"></span>
<span class="keys">空格/↓ 讲下一段 · ↑ 退回去 · F 看详细讲法 · +/- 调字号 · G 回开头</span></div>
<div id="prog"></div>
<div id="wrap">{''.join(body)}</div>
<script>{JS}</script></body></html>""", encoding="utf-8")
    print(f"✓ {OUT}  （单页 · {len(pages)} 段）")


if __name__ == "__main__":
    build()
