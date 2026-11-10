(function(){var D=[["l","xu.html","叙（高诱）"],["l","juan01.html","卷一·原道训"],["l","juan02.html","卷二·俶真训"],["l","juan03.html","卷三·天文训"],["l","juan04.html","卷四·地形训"],["l","juan05.html","卷五·时则训"],["l","juan06.html","卷六·览冥训"],["l","juan07.html","卷七·精神训"],["l","juan08.html","卷八·本经训"],["l","juan09.html","卷九·主术训"],["l","juan10.html","卷十·缪称训"],["l","juan11.html","卷十一·齐俗训"],["l","juan12.html","卷十二·道应训"],["l","juan13.html","卷十三·氾论训"],["l","juan14.html","卷十四·诠言训"],["l","juan15.html","卷十五·兵略训"],["l","juan16.html","卷十六·说山训"],["l","juan17.html","卷十七·说林训"],["l","juan18.html","卷十八·人间训"],["l","juan19.html","卷十九·脩务训"],["l","juan20.html","卷二十·泰族训"],["l","juan21.html","卷二十一·要略"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
