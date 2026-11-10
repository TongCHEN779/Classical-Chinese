(function(){var D=[["l","p01.html","序"],["l","p02.html","明刻本·前集"],["l","p03.html","明刻本·后集"],["l","p04.html","清刻本·修身"],["l","p05.html","清刻本·应酬"],["l","p06.html","清刻本·评议"],["l","p07.html","清刻本·闲适"],["l","p08.html","清刻本·概论"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
