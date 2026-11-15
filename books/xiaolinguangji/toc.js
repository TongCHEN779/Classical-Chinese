(function(){var D=[["l","j01.html","古艳部"],["l","j02.html","腐流部"],["l","j03.html","术业部"],["l","j04.html","形体部"],["l","j05.html","殊禀部"],["l","j06.html","闺风部"],["l","j07.html","世讳部"],["l","j08.html","僧道部"],["l","j09.html","贪吝部"],["l","j10.html","贫窭部"],["l","j11.html","讥刺部"],["l","j12.html","谬误部"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
