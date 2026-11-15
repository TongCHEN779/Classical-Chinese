(function(){var D=[["l","x1.html","序"],["l","j01.html","卷一·论"],["l","j02.html","卷二·考"],["l","j03.html","卷三·序"],["l","j04.html","卷四·序"],["l","j05.html","卷五·题跋"],["l","j06.html","卷六·书"],["l","j07.html","卷七·赠序"],["l","j08.html","卷八·寿序"],["l","j09.html","卷九·策问"],["l","j10.html","卷十·传"],["l","j11.html","卷十一·碑文"],["l","j12.html","卷十二·墓志铭"],["l","j13.html","卷十三·墓志铭"],["l","j14.html","卷十四·记"],["l","j15.html","卷十五·赋"],["l","j16.html","卷十六·祭文"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
