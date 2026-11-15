(function(){var D=[["l","z00.html","序例"],["l","z01.html","第一章　绪论"],["l","z02.html","第二章　李鸿章之位置"],["l","z03.html","第三章　李鸿章未达以前及其时中国之形势"],["l","z04.html","第四章　兵家之李鸿章（上）"],["l","z05.html","第五章　兵家之李鸿章（下）"],["l","z06.html","第六章　洋务时代之李鸿章"],["l","z07.html","第七章　中日战争时代之李鸿章"],["l","z08.html","第八章　外交家之李鸿章（上）"],["l","z09.html","第九章　外交家之李鸿章（下）"],["l","z10.html","第十章　投闲时代之李鸿章"],["l","z11.html","第十一章　李鸿章之末路"],["l","z12.html","第十二章　结论"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
