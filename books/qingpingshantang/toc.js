(function(){var D=[["l","p001.html","柳耆卿诗酒玩江楼记"],["l","p002.html","简帖和尚公案传奇"],["l","p003.html","西湖三塔记"],["l","p004.html","合同文字记"],["l","p005.html","风月瑞仙亭"],["l","p006.html","蓝桥记"],["l","p007.html","快嘴李翠莲记"],["l","p008.html","洛阳三怪记"],["l","p009.html","风月相思"],["l","p010.html","张子房慕道记"],["l","p011.html","阴骘积善"],["l","p012.html","陈巡检梅岭失妻记"],["l","p013.html","五戒禅师私红莲记"],["l","p014.html","刎颈鸳鸯会"],["l","p015.html","杨温拦路虎传"],["l","p016.html","花灯轿莲女成佛记"],["l","p017.html","曹伯明错勘赃记"],["l","p018.html","错认尸"],["l","p019.html","董永遇仙传"],["l","p020.html","戒指儿记"],["l","p021.html","羊角哀死战荆轲"],["l","p022.html","死生交范张鸡黍"],["l","p023.html","老冯唐直谏汉文帝"],["l","p024.html","汉李广世号飞将军"],["l","p025.html","夔关姚卞吊诸葛"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.innerHTML=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
