(function(){var D=[["l","p001.html","第一回　托遗言续编现形记　述情话剖说厌世心"],["l","p002.html","第二回　论农工弟兄言志　攀瓜葛堂属交通"],["l","p003.html","第三回　认亲戚席上生风　论字画室中谈古"],["l","p004.html","第四回　赵青云默识宦谱　余宝光偷填官凭"],["l","p005.html","第五回　游张园通判姘妻　借病房中丞盗嫂"],["l","p006.html","第六回　借手谈明修栈道　品鼻烟暗度陈仓"],["l","p007.html","第七回　借公报私当场点眼　抚棺痛哭别有伤心"],["l","p008.html","第八回　赵大令成名飞过海　王三太箴语勖官方"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
