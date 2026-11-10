(function(){var D=[["l","xu.html","国语解叙"],["l","p01.html","卷一　周语上"],["l","p02.html","卷二　周语中"],["l","p03.html","卷三　周语下"],["l","p04.html","卷四　鲁语上"],["l","p05.html","卷五　鲁语下"],["l","p06.html","卷六　齐语"],["l","p07.html","卷七　晋语一"],["l","p08.html","卷八　晋语二"],["l","p09.html","卷九　晋语三"],["l","p10.html","卷十　晋语四"],["l","p11.html","卷十一　晋语五"],["l","p12.html","卷十二　晋语六"],["l","p13.html","卷十三　晋语七"],["l","p14.html","卷十四　晋语八"],["l","p15.html","卷十五　晋语九"],["l","p16.html","卷十六　郑语"],["l","p17.html","卷十七　楚语上"],["l","p18.html","卷十八　楚语下"],["l","p19.html","卷十九　吴语"],["l","p20.html","卷二十　越语上"],["l","p21.html","卷二十一　越语下"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
