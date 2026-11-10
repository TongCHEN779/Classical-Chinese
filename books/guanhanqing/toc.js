(function(){var D=[["l","douee.html","感天动地窦娥冤"],["l","luzhailang.html","包待制智斩鲁斋郎"],["l","jiufengchen.html","赵盼儿风月救风尘"],["l","wangjiangting.html","望江亭中秋切鲙"],["l","hudiemeng.html","包待制三勘蝴蝶梦"],["l","jinxianchi.html","杜蕊娘智赏金线池"],["l","xietianxiang.html","钱大尹智宠谢天香"],["l","yujingtai.html","温太真玉镜台"],["l","danbianduosuo.html","尉迟恭单鞭夺槊"],["l","danfenghui.html","关大王独赴单刀会"],["l","feiyimeng.html","钱大尹智勘绯衣梦"],["l","wuhouyan.html","刘夫人庆赏五侯宴"],["l","kucunxiao.html","邓夫人苦痛哭存孝"],["l","peidu.html","山神庙裴度还带"],["l","chenmu.html","状元堂陈母教子"],["l","xishumeng.html","关张双赴西蜀梦"],["l","baiyueting.html","闺怨佳人拜月亭"],["l","tiaofengyue.html","诈妮子调风月"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
