(function(){var D=[["l","juan01.html","学而第一"],["l","juan02.html","为政第二"],["l","juan03.html","八佾第三"],["l","juan04.html","里仁第四"],["l","juan05.html","公冶长第五"],["l","juan06.html","雍也第六"],["l","juan07.html","述而第七"],["l","juan08.html","泰伯第八"],["l","juan09.html","子罕第九"],["l","juan10.html","乡党第十"],["l","juan11.html","先进第十一"],["l","juan12.html","颜渊第十二"],["l","juan13.html","子路第十三"],["l","juan14.html","宪问第十四"],["l","juan15.html","卫灵公第十五"],["l","juan16.html","季氏第十六"],["l","juan17.html","阳货第十七"],["l","juan18.html","微子第十八"],["l","juan19.html","子张第十九"],["l","juan20.html","尧曰第二十"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
