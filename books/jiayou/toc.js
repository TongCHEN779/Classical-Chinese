(function(){var D=[["l","juan01.html","卷一·几策一首"],["l","juan02.html","卷二·权书上"],["l","juan03.html","卷三·权书下"],["l","juan04.html","卷四·衡论上"],["l","juan05.html","卷五·衡论下"],["l","juan06.html","卷六·六经论"],["l","juan07.html","卷七·洪范论"],["l","juan08.html","卷八·太玄论"],["l","juan09.html","卷九·史论"],["l","juan10.html","卷十·书一首"],["l","juan11.html","卷十一·书五首"],["l","juan12.html","卷十二·书九首"],["l","juan13.html","卷十三·书八首"],["l","juan14.html","卷十四·谱"],["l","juan15.html","卷十五·杂文二十一首"],["l","juan16.html","卷十六·杂诗二十七首"],["l","buyi.html","补遗"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
