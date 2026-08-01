import pathlib, re, subprocess, json
ROOT = pathlib.Path(__file__).parent
src = (ROOT/"index.html").read_text(encoding="utf-8")

CHECK = r"""
<script>
window.addEventListener('load', function(){
  setTimeout(function(){
    var out=[], slides=document.querySelectorAll('.slide');
    slides.forEach(function(sl,i){
      var prev=sl.style.display; sl.style.display='flex';
      var sb=sl.getBoundingClientRect();
      // 1) HTML 元素越界
      sl.querySelectorAll('*').forEach(function(el){
        if(el.tagName==='svg'||el.closest('svg')) return;
        var r=el.getBoundingClientRect();
        if(r.width===0&&r.height===0) return;
        if(r.bottom>sb.bottom-8||r.right>sb.right-4||r.top<sb.top-4||r.left<sb.left-4){
          out.push('S'+(i+1)+' OVERFLOW <'+el.tagName.toLowerCase()+' class="'+(el.className&&el.className.baseVal===undefined?el.className:'')+'"> '+
            'box='+Math.round(r.left-sb.left)+','+Math.round(r.top-sb.top)+','+Math.round(r.right-sb.left)+','+Math.round(r.bottom-sb.top)+
            ' txt="'+(el.textContent||'').trim().slice(0,40)+'"');
        }
      });
      // 2) 主体溢出容器（滚动条）
      sl.querySelectorAll('.cards,.s-body,.figure,table').forEach(function(el){
        if(el.scrollHeight>el.clientHeight+3) out.push('S'+(i+1)+' SCROLL-Y '+el.className+' '+el.scrollHeight+'>'+el.clientHeight);
        if(el.scrollWidth>el.clientWidth+3) out.push('S'+(i+1)+' SCROLL-X '+el.className+' '+el.scrollWidth+'>'+el.clientWidth);
      });
      // 3) SVG 内 text 超出 viewBox
      sl.querySelectorAll('svg').forEach(function(svg){
        var vb=(svg.getAttribute('viewBox')||'').split(/\s+/).map(Number);
        if(vb.length!==4) return;
        svg.querySelectorAll('text').forEach(function(t){
          try{
            var bb=t.getBBox();
            if(bb.x+bb.width>vb[0]+vb[2]+1||bb.y+bb.height>vb[1]+vb[3]+1||bb.x<vb[0]-1){
              out.push('S'+(i+1)+' SVG-TEXT-OUT x='+Math.round(bb.x)+' w='+Math.round(bb.width)+' end='+Math.round(bb.x+bb.width)+'/'+ (vb[0]+vb[2]) +
                ' y='+Math.round(bb.y+bb.height)+'/'+(vb[1]+vb[3])+' "'+t.textContent.slice(0,34)+'"');
            }
          }catch(e){}
        });
      });
      sl.style.display=prev;
    });
    var pre=document.createElement('pre'); pre.id='qa-out';
    pre.textContent='QA_BEGIN\n'+(out.length?out.join('\n'):'CLEAN')+'\nQA_END';
    document.body.appendChild(pre);
  }, 900);
});
</script>
"""
qa = src.replace("</body>", CHECK + "\n</body>")
(ROOT/"qa.html").write_text(qa, encoding="utf-8")
print("qa.html written")
