(function(){var D=[["l","p001.html","第一回 小才女代父题诗"],["l","p002.html","第二回 老御史为儿谋妇"],["l","p003.html","第三回 白太常难途托娇女"],["l","p004.html","第四回 吴翰林花下遇才人"],["l","p005.html","第五回 穷秀才辞婚富贵女"],["l","p006.html","第六回 丑郎君强作词赋人"],["l","p007.html","第七回 暗更名才子遗珠"],["l","p008.html","第八回 悄窥侍郎儿识货"],["l","p009.html","第九回 百花亭撇李寻桃"],["l","p010.html","第十回 一片石送鸿迎燕"],["l","p011.html","第十一回 有腾挪背地求人"],["l","p012.html","第十二回 没奈何当场出丑"],["l","p013.html","第十三回 苏秀才穷途卖赋"],["l","p014.html","第十四回 卢小姐后园赠金"],["l","p015.html","第十五回 秋试春闱双得意"],["l","p016.html","第十六回 花姨月姊两谈心"],["l","p017.html","第十七回 势位逼仓卒去官"],["l","p018.html","第十八回 山水游偶然得婿"],["l","p019.html","第十九回 错中错各不遂心"],["l","p020.html","第二十回 锦上锦大家如愿"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
