(function(){var D=[["l","lisao.html","离骚"],["l","jiuge.html","九歌"],["l","tianwen.html","天问"],["l","jiuzhang.html","九章"],["l","yuanyou.html","远游"],["l","buju.html","卜居"],["l","yufu.html","渔父"],["l","jiubian.html","九辩"],["l","zhaohun.html","招魂"],["l","dazhao.html","大招"],["l","xishi.html","惜誓"],["l","zhaoyinshi.html","招隐士"],["l","qijian.html","七谏"],["l","aishiming.html","哀时命"],["l","jiuhuai.html","九怀"],["l","jiutan.html","九叹"],["l","jiusi.html","九思"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
