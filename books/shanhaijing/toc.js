(function(){var D=[["l","x1.html","郭璞序"],["l","j1.html","南山经"],["l","j2.html","西山经"],["l","j3.html","北山经"],["l","j4.html","东山经"],["l","j5.html","中山经"],["l","j6.html","海外南经"],["l","j7.html","海外西经"],["l","j8.html","海外北经"],["l","j9.html","海外东经"],["l","j10.html","海内南经"],["l","j11.html","海内西经"],["l","j12.html","海内北经"],["l","j13.html","海内东经"],["l","j14.html","大荒东经"],["l","j15.html","大荒南经"],["l","j16.html","大荒西经"],["l","j17.html","大荒北经"],["l","j18.html","海内经"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
