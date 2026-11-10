(function(){var D=[["l","xu.html","郭璞序"],["l","kexu.html","李孟传刻方言序"],["l","p01.html","卷一"],["l","p02.html","卷二"],["l","p03.html","卷三"],["l","p04.html","卷四"],["l","p05.html","卷五"],["l","p06.html","卷六"],["l","p07.html","卷七"],["l","p08.html","卷八"],["l","p09.html","卷九"],["l","p10.html","卷十"],["l","p11.html","卷十一"],["l","p12.html","卷十二"],["l","p13.html","卷十三"],["l","ba.html","朱质跋李刻方言"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
