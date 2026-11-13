(function(){var D=[["l","p001.html","卷一·情贞类"],["l","p002.html","卷二·情缘类"],["l","p003.html","卷三·情私类"],["l","p004.html","卷四·情侠类"],["l","p005.html","卷五·情豪类"],["l","p006.html","卷六·情爱类"],["l","p007.html","卷七·情痴类"],["l","p008.html","卷八·情感类"],["l","p009.html","卷九·情幻类"],["l","p010.html","卷十·情灵类"],["l","p011.html","卷十一·情化类"],["l","p012.html","卷十二·情媒类"],["l","p013.html","卷十三·情憾类"],["l","p014.html","卷十四·情仇类"],["l","p015.html","卷十五·情芽类"],["l","p016.html","卷十六·情报类"],["l","p017.html","卷十七·情秽类"],["l","p018.html","卷十八·情累类"],["l","p019.html","卷十九·情疑类"],["l","p020.html","卷二十·情鬼类"],["l","p021.html","卷二十一·情妖类"],["l","p022.html","卷二十二·情外类"],["l","p023.html","卷二十三·情通类"],["l","p024.html","卷二十四·情迹类"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
