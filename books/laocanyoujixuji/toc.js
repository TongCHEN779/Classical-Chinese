(function(){var D=[["l","xu.html","自序"],["l","p01.html","第一回　元机旅店传龙语　素壁丹青绘马鸣"],["l","p02.html","第二回　宋公子蹂躏优昙花　德夫人怜惜灵芝草"],["l","p03.html","第三回　阳偶阴奇参大道　男欢女悦证初禅"],["l","p04.html","第四回　九转成丹破壁飞　七年返本归家坐"],["l","p05.html","第五回　俏逸云除欲除静　德慧生救人救澈"],["l","p06.html","第六回　斗姥宫中逸云说法　观音庵里环翠离尘"],["l","p07.html","第七回　银汉浮槎仰瞻月姊　森罗宝殿伏见阎王"],["l","p08.html","第八回　血肉飞腥油锅炼骨　语言积恶石磨研魂"],["l","p09.html","第九回　德业积成阴世富　善缘发动化身香"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
