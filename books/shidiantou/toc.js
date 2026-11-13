(function(){var D=[["l","p001.html","第一回 郭挺之榜前认子"],["l","p002.html","第二回 卢梦仙江上寻妻"],["l","p003.html","第三回 王本立天涯求父"],["l","p004.html","第四回 瞿凤奴情愆死盖"],["l","p005.html","第五回 莽书生强图鸳侣"],["l","p006.html","第六回 乞丐妇重配鸾俦"],["l","p007.html","第七回 感恩鬼三古传题旨"],["l","p008.html","第八回 贪婪汉六院卖风流"],["l","p009.html","第九回 玉箫女再世玉环缘"],["l","p010.html","第十回 王孺人离合团鱼梦"],["l","p011.html","第十一回 江都市孝妇屠身"],["l","p012.html","第十二回 侯官县烈女歼仇"],["l","p013.html","第十三回 唐玄宗恩赐纩衣缘"],["l","p014.html","第十四回 潘文子契合鸳鸯冢"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
