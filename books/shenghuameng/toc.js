(function(){var D=[["l","p001.html","第一回 贡副使宽恩御变 康公子大义诛凶"],["l","p002.html","第二回 老书生临江附异梦 小秀才旅店得奇闻"],["l","p003.html","第三回 安排巧计淫尼借巧遇以兴灾 硬拉奸情烈妇为奸夫而殉节"],["l","p004.html","第四回 太守为怜才公堂鞫鬼 臬台因选婿雪舫惊诗"],["l","p005.html","第五回 女婿忒多心欲兼才美 丈人偏作色故阻良缘"],["l","p006.html","第六回 真淑女赚杀假春容 假小姐吓走真才子"],["l","p007.html","第七回 神君里怒斩白蛇精 王屋山大破黄衣寨"],["l","p008.html","第八回 东园赓雅调自许同心 南国有佳人再谐连理"],["l","p009.html","第九回 白公堤青天遭霹雳 毘陵道黑夜走佳人"],["l","p010.html","第十回 虎头寨一女子屈服众英雄 豹尾关两袿裳权成双伉俪"],["l","p011.html","第十一回 非奸细计赚白衣军 是夫妻误认绿林妇"],["l","p012.html","第十二回 解重围偷儿报恩兼成伟绩 脱貔貅佳人换相并受荣封"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
