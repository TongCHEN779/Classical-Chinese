(function(){var D=[["l","p001.html","第一回　谱新词开卷说痴情　借导言老人商了愿"],["l","p002.html","第二回　订新亲文章欣有价　惊噩耗快婿忽无踪"],["l","p003.html","第三回　南海县演出无头案　朱婉贞初遇丧心人"],["l","p004.html","第四回　心旷神怡贪观花埭景　手忙脚乱遍觅掌中珠"],["l","p005.html","第五回　祸起萧墙恶人施毒手　羁身暗室淑女悄投缳"],["l","p006.html","第六回　返芳魂再遭磨折　筹妙策强作周旋"],["l","p007.html","第七回　机警芳心百般运计　淋漓箴血一纸呈词"],["l","p008.html","第八回　李明府推敲知底蕴　朱婉贞仓猝又沉沦"],["l","p009.html","第九回　遇救援一命重生　完节操三番就死"],["l","p010.html","第十回　情扰成魔魂游幻境　死而复活夜走尼庵"],["l","p011.html","第十一回　老尼姑粲说淫欲情　朱婉贞历遍灾晦病"],["l","p012.html","第十二回　三折肱名医愈烈女　一帆风侠士送娇娃"],["l","p013.html","第十三回　朱婉贞归家诉别绪　陈六皆劝酒试奸徒"],["l","p014.html","第十四回　信胡言访求到西粤　寻劣弟踪迹走湖南"],["l","p015.html","第十五回　奸诈人到底藏奸　节烈女奔丧守节"],["l","p016.html","第十六回　苦志廿年旁枝承嗣续　归人万里意外庆团圆"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
