(function(){var D=[["l","xu.html","毛诗序"],["l","zhounan.html","周南"],["l","shaonan.html","召南"],["l","beifeng.html","邶风"],["l","yongfeng.html","鄘风"],["l","weifeng.html","卫风"],["l","wangfeng.html","王风"],["l","zhengfeng.html","郑风"],["l","qifeng.html","齐风"],["l","weifeng2.html","魏风"],["l","tangfeng.html","唐风"],["l","qinfeng.html","秦风"],["l","chenfeng.html","陈风"],["l","guifeng.html","桧风"],["l","caofeng.html","曹风"],["l","binfeng.html","豳风"],["l","xiaoya.html","小雅"],["l","daya.html","大雅"],["l","songzhou.html","周颂"],["l","lusong.html","鲁颂"],["l","shangsong.html","商颂"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
