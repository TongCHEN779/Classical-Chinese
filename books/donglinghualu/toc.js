(function(){var D=[["g","序"],["l","xu.html","序"],["g","正文"],["l","juan01.html","卷一｜东都外城、旧京城、河道等"],["l","juan02.html","卷二｜御街、宣德楼前省府宫宇、朱雀门外街巷等"],["l","juan03.html","卷三｜马行街北诸医铺、大内西右掖门外街巷、大内前州桥东街巷等"],["l","juan04.html","卷四｜军头司、皇太子纳妃、公主出降等"],["l","juan05.html","卷五｜民俗、京瓦伎艺、娶妇等"],["l","juan06.html","卷六｜正月、元旦朝会、立春等"],["l","juan07.html","卷七｜清明节、三月一日开金明池琼林苑、驾幸临水殿观争标锡宴等"],["l","juan08.html","卷八｜四月八日、端午、六月六日崔府君生日二十四日神保观神生日等"],["l","juan09.html","卷九｜十月一日、天宁节、宰执亲王宗室百官入内上寿等"],["l","juan10.html","卷十｜冬至、大礼预教车象、车驾宿大庆殿等"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
