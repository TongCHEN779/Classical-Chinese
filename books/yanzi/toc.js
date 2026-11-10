(function(){var D=[["g","内篇（卷一至卷六）"],["l","juan01.html","卷一·内篇谏上"],["l","juan02.html","卷二·内篇谏下"],["l","juan03.html","卷三·内篇问上"],["l","juan04.html","卷四·内篇问下"],["l","juan05.html","卷五·内篇杂上"],["l","juan06.html","卷六·内篇杂下"],["g","外篇（卷七、卷八）"],["l","juan07.html","卷七·外篇上"],["l","juan08.html","卷八·外篇下"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
