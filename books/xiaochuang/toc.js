(function(){var D=[["l","yin.html","引"],["l","zixu.html","自叙"],["l","fanli.html","凡例"],["l","juan01.html","卷一·集醒"],["l","juan02.html","卷二·集情"],["l","juan03.html","卷三·集峭"],["l","juan04.html","卷四·集灵"],["l","juan05.html","卷五·集素"],["l","juan06.html","卷六·集景"],["l","juan07.html","卷七·集韵"],["l","juan08.html","卷八·集奇"],["l","juan09.html","卷九·集绮"],["l","juan10.html","卷十·集豪"],["l","juan11.html","卷十一·集法"],["l","juan12.html","卷十二·集倩"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
