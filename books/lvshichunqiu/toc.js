(function(){var D=[["g","十二纪"],["l","p01.html","孟春纪"],["l","p02.html","仲春纪"],["l","p03.html","季春纪"],["l","p04.html","孟夏纪"],["l","p05.html","仲夏纪"],["l","p06.html","季夏纪"],["l","p07.html","孟秋纪"],["l","p08.html","仲秋纪"],["l","p09.html","季秋纪"],["l","p10.html","孟冬纪"],["l","p11.html","仲冬纪"],["l","p12.html","季冬纪"],["g","八览"],["l","p13.html","有始览"],["l","p14.html","孝行览"],["l","p15.html","慎大览"],["l","p16.html","先识览"],["l","p17.html","审分览"],["l","p18.html","审应览"],["l","p19.html","离俗览"],["l","p20.html","恃君览"],["g","六论"],["l","p21.html","开春论"],["l","p22.html","慎行论"],["l","p23.html","贵直论"],["l","p24.html","不苟论"],["l","p25.html","似顺论"],["l","p26.html","士容论"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
