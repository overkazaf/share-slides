#!/usr/bin/env python3
"""量出每张 SVG 内容的真实包围盒，再把它缩放/居中到填满画布。

上一版只对齐了画布比例，图并没有变大——因为 viewBox 内部本来就留着空白边距。
这一版直接测 getBBox()，把内容映射到「容器比匹配的画布」上，图才真的铺满。
"""
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MARGIN = 5

PROBE = r"""
<script>
window.addEventListener('load',function(){setTimeout(function(){
  var out=[],slides=document.querySelectorAll('.slide');
  slides.forEach(function(sl,i){
    var prev=sl.style.display; sl.style.display='flex';
    var figs=sl.querySelectorAll('.figure');
    figs.forEach(function(f,j){
      var svg=f.querySelector(':scope > svg'); if(!svg) return;
      var r=f.getBoundingClientRect();
      var pad=f.classList.contains('plain')?0:1;
      var cw=r.width-(pad?28:0), ch=r.height-(pad?24:0);
      var vb=(svg.getAttribute('viewBox')||'').split(/\s+/).map(Number);
      var bb=null; try{ bb=svg.getBBox(); }catch(e){}
      if(!bb) return;
      out.push({slide:i+1,fig:j,cr:cw/ch,vbw:vb[2],vbh:vb[3],
                bx:+bb.x.toFixed(1),by:+bb.y.toFixed(1),bw:+bb.width.toFixed(1),bh:+bb.height.toFixed(1)});
    });
    sl.style.display=prev;
  });
  var pre=document.createElement('pre');pre.id='p-out';
  pre.textContent='P_BEGIN'+JSON.stringify(out)+'P_END';document.body.appendChild(pre);
},900)});
</script>
"""

src = (ROOT / "index.html").read_text(encoding="utf-8")
(ROOT / "p.html").write_text(src.replace("</body>", PROBE + "\n</body>"), encoding="utf-8")
dom = subprocess.run([CHROME, "--headless", "--disable-gpu", "--virtual-time-budget=6000",
                      "--dump-dom", f"file://{ROOT}/p.html"], capture_output=True, text=True).stdout
(ROOT / "p.html").unlink(missing_ok=True)
m = re.search(r'<pre id="p-out">(.*?)</pre>', dom, re.S)
if not m:
    sys.exit("probe failed")
import html as H
payload = H.unescape(m.group(1)).strip()
payload = payload[payload.index('P_BEGIN') + 7: payload.rindex('P_END')]
data = json.loads(payload)

slides = sorted(ROOT.glob('slides/*.html'))
by_slide = {}
for d in data:
    by_slide.setdefault(d['slide'], []).append(d)

report = []
for si, path in enumerate(slides, 1):
    items = by_slide.get(si)
    if not items:
        continue
    text = path.read_text(encoding='utf-8')
    parts = text.split('</svg>')
    fi = 0
    out = []
    for seg in parts:
        if '<svg' not in seg:
            out.append(seg); continue
        d = next((x for x in items if x['fig'] == fi), None)
        fi += 1
        if not d:
            out.append(seg); continue
        W, H = d['vbw'], d['vbh']
        # 画布比对齐容器比
        if W / H > d['cr']: W2, H2 = W, round(W / d['cr'])
        else:               W2, H2 = round(H * d['cr']), H
        bw, bh = d['bw'], d['bh']
        if bw <= 0 or bh <= 0:
            out.append(seg); continue
        s = min((W2 - 2 * MARGIN) / bw, (H2 - 2 * MARGIN) / bh)
        if s < 1.02:                       # 已经基本铺满，不动
            out.append(seg); continue
        tx = (W2 - bw * s) / 2 - d['bx'] * s
        ty = (H2 - bh * s) / 2 - d['by'] * s
        seg = re.sub(r'<svg viewBox="0 0 [\d.]+ [\d.]+"', f'<svg viewBox="0 0 {W2:g} {H2:g}"', seg, count=1)
        anchor = seg.find('</defs>')
        pos = anchor + 7 if anchor != -1 else seg.index('>', seg.index('<svg')) + 1
        seg = seg[:pos] + f'\n          <g transform="translate({tx:.1f},{ty:.1f}) scale({s:.4f})">' + seg[pos:] + '\n          </g>\n        '
        out.append(seg)
        report.append(f'S{si} #{fi-1}: 内容 {bw:.0f}x{bh:.0f} → 放大 {s:.2f}×，画布 {W:g}x{H:g}→{W2:g}x{H2:g}')
    path.write_text('</svg>'.join(out), encoding='utf-8')

print(f'=== 放大了 {len(report)} 张 ===')
for r in report: print(' ', r)
