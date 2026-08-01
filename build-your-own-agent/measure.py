import pathlib
ROOT=pathlib.Path(__file__).parent
src=(ROOT/"index.html").read_text(encoding="utf-8")
CHECK = r"""
<script>
window.addEventListener('load',function(){setTimeout(function(){
  var out=[],slides=document.querySelectorAll('.slide');
  slides.forEach(function(sl,i){
    var prev=sl.style.display; sl.style.display='flex';
    sl.querySelectorAll('.figure').forEach(function(f,j){
      var r=f.getBoundingClientRect();
      var svg=f.querySelector(':scope > svg');
      var vb=svg?(svg.getAttribute('viewBox')||'').split(/\s+/).map(Number):null;
      var box=(r.width-(f.classList.contains('plain')?0:28));
      var boxh=(r.height-(f.classList.contains('plain')?0:24));
      out.push('S'+(i+1)+' fig'+j+
        ' 容器='+Math.round(box)+'x'+Math.round(boxh)+' (比'+(box/boxh).toFixed(2)+')'+
        (vb&&vb.length===4?' viewBox='+vb[2]+'x'+vb[3]+' (比'+(vb[2]/vb[3]).toFixed(2)+')'+
          ' 建议高='+Math.round(vb[2]*boxh/box):' [无svg]'));
    });
    sl.style.display=prev;
  });
  var pre=document.createElement('pre');pre.id='m-out';pre.textContent='M_BEGIN\n'+out.join('\n')+'\nM_END';
  document.body.appendChild(pre);
},900)});
</script>
"""
(ROOT/"m.html").write_text(src.replace("</body>",CHECK+"\n</body>"),encoding="utf-8")
