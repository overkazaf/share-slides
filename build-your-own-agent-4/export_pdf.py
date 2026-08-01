#!/usr/bin/env python3
"""把 index.html 导成 1280×720 的 PDF：如何打造自己的Agent.pdf

用法：python3 build.py && python3 export_pdf.py

做法：生成一份打印版 HTML —— 所有 .slide 从「绝对定位 + 只显示当前页」
改成「顺序排列 + 每页一张」，去掉 HUD/进度条/总览层，再交给
Chrome headless 的 --print-to-pdf。
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "index.html"
TMP = ROOT / "print.html"
OUT = ROOT / "如何打造自己的Agent.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PRINT_CSS = """
<style id="print-override">
  @page { size: 1280px 720px; margin: 0; }
  html, body { overflow: visible !important; background: #020617 !important; }
  #stage-wrap { position: static !important; display: block !important; }
  #stage { width: 1280px !important; height: auto !important; transform: none !important; }
  .slide {
    position: relative !important;
    inset: auto !important;
    display: flex !important;
    width: 1280px !important;
    height: 720px !important;
    animation: none !important;
    break-after: page;
    page-break-after: always;
    overflow: hidden;
  }
  .slide:last-child { break-after: auto; page-break-after: auto; }
  #hud, #progress, #overview, #toast { display: none !important; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
</style>
"""


def main():
    if not SRC.exists():
        sys.exit("先跑 python3 build.py")
    html = SRC.read_text(encoding="utf-8")
    n = len(re.findall(r'<section class="slide', html))

    # 去掉翻页脚本：它会在加载后给 .slide 加 display:none
    html = re.sub(r"<script>.*?</script>", "", html, flags=re.S)
    html = html.replace("</head>", PRINT_CSS + "</head>")
    TMP.write_text(html, encoding="utf-8")

    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         "--virtual-time-budget=20000", f"--print-to-pdf={OUT}",
         f"file://{TMP}"],
        capture_output=True, check=False)
    TMP.unlink(missing_ok=True)

    if not OUT.exists():
        sys.exit("导出失败：没生成 PDF")
    size = OUT.stat().st_size / 1024 / 1024
    print(f"✓ {OUT.name}  ({n} 页源 · {size:.1f} MB)")


if __name__ == "__main__":
    main()
