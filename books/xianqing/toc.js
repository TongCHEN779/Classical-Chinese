(function(){var D=[["l","yuhuaixu.html","余怀序"],["l","youtongxu.html","尤侗序"],["l","fanli.html","凡例七则·四期三戒"],["l","juan01.html","卷一·词曲部上"],["l","juan02.html","卷二·词曲部下、演习部"],["l","juan03.html","卷三·声容部"],["l","juan04.html","卷四·居室部、器玩部"],["l","juan05.html","卷五·饮馔部、种植部"],["l","juan06.html","卷六·颐养部"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
