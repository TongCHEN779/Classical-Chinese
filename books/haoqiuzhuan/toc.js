(function(){var D=[["l","p001.html","第一回"],["l","p002.html","第二回"],["l","p003.html","第三回"],["l","p004.html","第四回"],["l","p005.html","第五回"],["l","p006.html","第六回"],["l","p007.html","第七回"],["l","p008.html","第八回"],["l","p009.html","第九回"],["l","p010.html","第十回"],["l","p011.html","第十一回"],["l","p012.html","第十二回"],["l","p013.html","第十三回"],["l","p014.html","第十四回"],["l","p015.html","第十五回"],["l","p016.html","第十六回"],["l","p017.html","第十七回"],["l","p018.html","第十八回"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
