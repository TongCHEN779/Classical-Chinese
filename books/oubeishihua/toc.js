(function(){var D=[["l","x1.html","小引"],["l","j01.html","卷一·李青莲诗"],["l","j02.html","卷二·杜少陵诗"],["l","j03.html","卷三·韩昌黎诗"],["l","j04.html","卷四·白香山诗"],["l","j05.html","卷五·苏东坡诗"],["l","j06.html","卷六·陆放翁诗"],["l","j07.html","卷七"],["l","j08.html","卷八"],["l","j09.html","卷九·吴梅村诗"],["l","j10.html","卷十·查初白诗"],["l","j11.html","卷十一"],["l","j12.html","卷十二"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
