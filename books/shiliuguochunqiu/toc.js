(function(){var D=[["l","p01.html","卷一·前赵录"],["l","p02.html","卷二·后赵录"],["l","p03.html","卷三·前燕录"],["l","p04.html","卷四·前秦录"],["l","p05.html","卷五·后秦录"],["l","p06.html","卷六·蜀录"],["l","p07.html","卷七·前凉录"],["l","p08.html","卷八·西凉录"],["l","p09.html","卷九·北凉录"],["l","p10.html","卷十·后凉录"],["l","p11.html","卷十一·后燕录"],["l","p12.html","卷十二·南凉录"],["l","p13.html","卷十三·南燕录"],["l","p14.html","卷十四·西秦录"],["l","p15.html","卷十五·北燕录"],["l","p16.html","卷十六·夏录"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
