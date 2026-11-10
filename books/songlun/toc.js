(function(){var D=[["l","juan01.html","卷一·太祖"],["l","juan02.html","卷二·太宗"],["l","juan03.html","卷三·真宗"],["l","juan04.html","卷四·仁宗"],["l","juan05.html","卷五·英宗"],["l","juan06.html","卷六·神宗"],["l","juan07.html","卷七·哲宗"],["l","juan08.html","卷八·徽宗"],["l","juan09.html","卷九·钦宗"],["l","juan10.html","卷十·高宗"],["l","juan11.html","卷十一·孝宗"],["l","juan12.html","卷十二·光宗"],["l","juan13.html","卷十三·宁宗"],["l","juan14.html","卷十四·理宗"],["l","juan15.html","卷十五·度宗"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
