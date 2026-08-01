#!/usr/bin/env python3
"""把 slides/*.html 分片 + deck.css + deck.js 合成单文件自包含演示 out/index.html"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
SLIDES = ROOT / "slides"
OUT = ROOT

FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '  <link href="https://fonts.googleapis.com/css2?'
        'family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">')

TITLE = "如何打造自己的 Agent · Chapter 4 · re-agent：把逆向写进骨架"


def build():
    parts = sorted(SLIDES.glob("s*.html"))
    if not parts:
        sys.exit("no slides found in %s" % SLIDES)

    body = []
    for p in parts:
        html = p.read_text(encoding="utf-8").strip()
        if not html:
            sys.exit("empty slide: %s" % p.name)
        body.append("<!-- ===== %s ===== -->\n%s" % (p.name, html))

    css = (ROOT / "deck.css").read_text(encoding="utf-8")
    js = (ROOT / "deck.js").read_text(encoding="utf-8")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{TITLE}</title>
  {FONT}
  <style>
{css}
  </style>
</head>
<body>
  <div id="progress" style="width:0"></div>

  <div id="stage-wrap">
    <div id="stage">
{chr(10).join(body)}
    </div>
  </div>

  <div id="hud">
    <span id="counter">01/{len(parts)}</span>
    <button id="btn-prev" title="上一页 ←">‹</button>
    <button id="btn-next" title="下一页 →">›</button>
    <button id="btn-ov" title="总览 O">⊞</button>
  </div>

  <div id="overview">
    <h2>总览 · 点击跳转 · ESC 返回</h2>
    <div id="ov-grid"></div>
  </div>

  <script>
{js}
  </script>
</body>
</html>
"""
    dest = OUT / "index.html"
    dest.write_text(doc, encoding="utf-8")
    kb = len(doc.encode("utf-8")) / 1024
    print(f"✓ {dest}  ({len(parts)} slides, {kb:.0f} KB)")


if __name__ == "__main__":
    build()
