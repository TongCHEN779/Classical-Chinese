(function(){var D=[["l","x1.html","李焘序"],["l","x2.html","自序"],["l","x3.html","杂说"],["l","j1.html","卷第一"],["l","j2.html","卷第二"],["l","j3.html","卷第三"],["l","j4.html","卷第四"],["l","j5.html","卷第五"],["l","j6.html","卷第六"],["l","j7.html","卷第七"],["l","j8.html","卷第八"],["l","j9.html","卷第九"],["l","j10.html","卷第十"],["l","x4.html","后序"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
