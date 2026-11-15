(function(){var D=[["l","x1.html","序"],["l","j01.html","卷之一·诗四言"],["l","j02.html","卷之二·诗"],["l","j03.html","卷之三·诗五言"],["l","j04.html","卷之四·诗五言"],["l","j05.html","卷之五·赋辞"],["l","j06.html","卷之六·记传赞述"],["l","j07.html","卷之七·疏祭文"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
