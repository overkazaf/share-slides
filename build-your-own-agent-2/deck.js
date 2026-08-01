/* 演示框架运行时：等比缩放 / 键盘导航 / 缩略图总览 */
(function () {
  var stage = document.getElementById('stage');
  var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var progress = document.getElementById('progress');
  var counter = document.getElementById('counter');
  var overview = document.getElementById('overview');
  var ovGrid = document.getElementById('ov-grid');
  var cur = 0;

  /* --- 等比缩放到视口 --- */
  function fit() {
    var pad = 0;
    var sx = (window.innerWidth - pad) / 1280;
    var sy = (window.innerHeight - pad) / 720;
    var s = Math.min(sx, sy);
    stage.style.transform = 'scale(' + s + ')';
  }
  window.addEventListener('resize', fit);
  fit();

  /* --- 页码 / 页脚注入 --- */
  slides.forEach(function (el, i) {
    var foot = el.querySelector('.s-foot .pg');
    if (foot) foot.textContent = String(i + 1).padStart(2, '0') + ' / ' + String(slides.length).padStart(2, '0');
  });

  function show(i) {
    if (i < 0) i = 0;
    if (i > slides.length - 1) i = slides.length - 1;
    slides[cur].classList.remove('active');
    cur = i;
    slides[cur].classList.add('active');
    progress.style.width = ((cur + 1) / slides.length * 100) + '%';
    counter.textContent = String(cur + 1).padStart(2, '0') + '/' + slides.length;
    if (location.hash !== '#' + (cur + 1)) history.replaceState(null, '', '#' + (cur + 1));
    Array.prototype.forEach.call(ovGrid.children, function (c, j) {
      c.classList.toggle('cur', j === cur);
    });
  }

  /* --- 缩略图总览 --- */
  slides.forEach(function (el, i) {
    var d = document.createElement('div');
    d.className = 'ov-item';
    d.innerHTML = '<div class="n">' + String(i + 1).padStart(2, '0') + '</div>' +
      '<div class="t">' + (el.dataset.title || '') + '</div>' +
      '<div class="c">' + (el.dataset.ch || '') + '</div>';
    d.onclick = function () { toggleOverview(false); show(i); };
    ovGrid.appendChild(d);
  });
  function toggleOverview(on) {
    if (on === undefined) on = !overview.classList.contains('on');
    overview.classList.toggle('on', on);
  }

  /* --- 键盘 --- */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { toggleOverview(false); return; }
    if (e.key === 'o' || e.key === 'O') { toggleOverview(); return; }
    if (overview.classList.contains('on')) return;
    switch (e.key) {
      case 'ArrowRight': case 'ArrowDown': case ' ': case 'PageDown': case 'n':
        e.preventDefault(); show(cur + 1); break;
      case 'ArrowLeft': case 'ArrowUp': case 'PageUp': case 'p':
        e.preventDefault(); show(cur - 1); break;
      case 'Home': show(0); break;
      case 'End': show(slides.length - 1); break;
      case 'f': case 'F':
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen();
        break;
    }
  });

  /* --- 点击左右半屏翻页 --- */
  document.getElementById('stage-wrap').addEventListener('click', function (e) {
    if (overview.classList.contains('on')) return;
    if (e.target.closest('#hud')) return;
    show(e.clientX < window.innerWidth * 0.32 ? cur - 1 : cur + 1);
  });

  document.getElementById('btn-prev').onclick = function (e) { e.stopPropagation(); show(cur - 1); };
  document.getElementById('btn-next').onclick = function (e) { e.stopPropagation(); show(cur + 1); };
  document.getElementById('btn-ov').onclick = function (e) { e.stopPropagation(); toggleOverview(); };

  var start = parseInt((location.hash || '#1').slice(1), 10);
  show(isNaN(start) ? 0 : start - 1);
})();
