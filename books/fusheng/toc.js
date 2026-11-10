(function(){var D=[["l","j1.html","卷一 闺房记乐"],["l","j2.html","卷二 闲情记趣"],["l","j3.html","卷三 坎坷记愁"],["l","j4.html","卷四 浪游记快"],["l","j5.html","卷五 中山记历（伪续）"],["l","j6.html","卷六 养生记道（伪续）"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
