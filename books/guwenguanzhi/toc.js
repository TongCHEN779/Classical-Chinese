(function(){var D=[["l","xu.html","序一、序二、例言"],["l","juan01.html","卷一·周文"],["l","juan02.html","卷二·周文"],["l","juan03.html","卷三·周文"],["l","juan04.html","卷四·战国文"],["l","juan05.html","卷五·秦汉文"],["l","juan06.html","卷六·汉文"],["l","juan07.html","卷七·六朝唐文"],["l","juan08.html","卷八·唐文"],["l","juan09.html","卷九·唐宋文"],["l","juan10.html","卷十·宋文"],["l","juan11.html","卷十一·宋文"],["l","juan12.html","卷十二·明文"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
