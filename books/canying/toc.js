(function(){var D=[["l","part01.html","第001—030段"],["l","part02.html","第031—060段"],["l","part03.html","第061—090段"],["l","part04.html","第091—120段"],["l","part05.html","第121—150段"],["l","part06.html","第151—180段"],["l","part07.html","第181—210段"],["l","part08.html","第211—240段"],["l","part09.html","第241—270段"],["l","part10.html","第271—300段"],["l","part11.html","第301—330段"],["l","part12.html","第331—360段"],["l","part13.html","第361—390段"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
