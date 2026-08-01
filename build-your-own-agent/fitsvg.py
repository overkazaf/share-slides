#!/usr/bin/env python3
"""把每张 SVG 的 viewBox 宽高比对齐到它实际所在容器的宽高比。

原理：SVG 用 preserveAspectRatio=meet 等比缩放。若画布比 ≠ 容器比，
就会 letterbox 留白、图被迫缩小。做法是**扩大较小的那一维**（不动内容尺寸），
再把原内容整体居中平移——图因此按最大可能尺寸渲染，且不裁不挤。
容器比由 measure.py 实测得到。
"""
import re, pathlib, sys

# (文件名, 图序号) -> 实测容器宽高比
RATIOS = {
    ('s02-map.html', 0): 2.31,
    ('s03-what-is-agent.html', 0): 2.62,
    ('s04-spectrum.html', 0): 2.75,
    ('s05-timeline-1.html', 0): 2.31,
    ('s07-people.html', 0): 2.75,
    ('s08-stack.html', 0): 2.75,
    ('s09-harness.html', 0): 1.08,
    ('s10-loop.html', 0): 1.72,
    ('s11-graph.html', 0): 1.38,
    ('s11-graph.html', 1): 1.38,
    ('s12-context-1.html', 0): 3.24,
    ('s13-context-2.html', 0): 1.68,
    ('s14-skill.html', 0): 1.39,
    ('s15-tools.html', 0): 2.90,
    ('s16-workflow.html', 0): 2.90,
    ('s17-multiagent.html', 0): 2.90,
    ('s18-extensibility.html', 0): 7.34,
    ('s19-memory.html', 0): 1.14,
    ('s19-memory.html', 1): 1.14,
    ('s20-scenarios.html', 0): 1.39,
    ('s21-landscape.html', 0): 1.39,
    ('s22-pi.html', 0): 1.69,
    ('s23-ohmypi.html', 0): 1.39,
    ('s23-ohmypi.html', 1): 0.89,
    ('s26-re-arch.html', 0): 1.68,
}

TOL = 0.03
S = pathlib.Path(__file__).parent / 'slides'
changed = []

for fn in sorted(p.name for p in S.glob('*.html')):
    path = S / fn
    text = path.read_text(encoding='utf-8')
    if '<svg' not in text:
        continue
    parts = text.split('</svg>')
    idx = 0
    out = []
    for i, seg in enumerate(parts):
        if '<svg' not in seg:
            out.append(seg)
            continue
        m = re.search(r'<svg viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', seg)
        if not m:
            out.append(seg); idx += 1; continue
        W, H = float(m.group(1)), float(m.group(2))
        rc = RATIOS.get((fn, idx))
        idx += 1
        if rc is None:
            out.append(seg); continue
        rs = W / H
        if abs(rs - rc) / rc <= TOL:
            out.append(seg); continue

        if rs > rc:                      # 画布太扁 → 补高
            W2, H2 = W, round(W / rc)
        else:                            # 画布太高 → 补宽
            W2, H2 = round(H * rc), H
        dx, dy = round((W2 - W) / 2), round((H2 - H) / 2)

        seg = seg.replace(m.group(0), f'<svg viewBox="0 0 {W2:g} {H2:g}"', 1)
        # 在 </defs> 之后（或 <svg ...> 开标签之后）开一个居中 g
        anchor = seg.find('</defs>')
        pos = anchor + len('</defs>') if anchor != -1 else seg.index('>', seg.index('<svg')) + 1
        seg = seg[:pos] + f'\n          <g transform="translate({dx},{dy})">' + seg[pos:]
        out.append(seg)
        changed.append(f'{fn} #{idx-1}: {W:g}x{H:g} (比{rs:.2f}) → {W2:g}x{H2:g} (比{rc:.2f})  平移({dx},{dy})')

    # 每个被改过的 svg 闭合前补 </g>
    res = []
    idx2 = 0
    for i, seg in enumerate(out):
        if i < len(out) - 1:   # 该段后面跟着一个 </svg>
            if '<g transform="translate(' in seg and seg.count('<svg') == 1:
                seg = seg + '\n          </g>\n        '
        res.append(seg)
    path.write_text('</svg>'.join(res), encoding='utf-8')

print(f'=== 已适配 {len(changed)} 张 ===')
for c in changed:
    print(' ', c)
