(function(){var D=[["l","p001.html","第一回 太平世才星降瑞"],["l","p002.html","第二回 圣明朝淑女献箴"],["l","p003.html","第三回 金闺女诗嘲狂士"],["l","p004.html","第四回 玉尺楼才压群英"],["l","p005.html","第五回 山人脸一抹便转"],["l","p006.html","第六回 才女心百折不回"],["l","p007.html","第七回 道路上美还遇美"],["l","p008.html","第八回 闺阁中才不让才"],["l","p009.html","第九回 误相逢才傲张寅"],["l","p010.html","第十回 巧作合诗骄平子"],["l","p011.html","第十一回 一首诗占尽假风光"],["l","p012.html","第十二回 三杯酒透出真消息"],["l","p013.html","第十三回 观旧句忽尔害相思"],["l","p014.html","第十四回 看梅花默然投臭味"],["l","p015.html","第十五回 悬彩笔直求淑女"],["l","p016.html","第十六回 扮青衣巧压才人"],["l","p017.html","第十七回 俏佳人代丑汉呈身"],["l","p018.html","第十八回 痴公子倩佳人画面"],["l","p019.html","第十九回 道路联姻奇作合"],["l","p020.html","第二十回 金銮报捷美团圆"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
