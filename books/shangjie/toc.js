(function(){var D=[["g","第一回至第十回"],["l","001.html","第一回·碧玉楼周子言摆酒　青莲阁何少鹤开灯"],["l","002.html","第二回·巨商阔少一诺千金　冶业娼条深情蜜意"],["l","003.html","第三回·老挡手苦口谏东家　小东家发标换挡手"],["l","004.html","第四回·电报传来火油飞涨　下堂求去艳帜仍张"],["l","005.html","第五回·海底枪笆居奇垄断　空中楼阁看戏搭台"],["l","006.html","第六回·巨商破产接四连三　小鬼当家瞎三话四"],["l","007.html","第七回·杜筱岑兴高采烈　林幼竹丧气垂头"],["l","008.html","第八回·施媚术欢场常态　发怪论商界奇谈"],["l","009.html","第九回·林幼竹欢场觅协理　马扁人异地遇良朋"],["l","010.html","第十回·女艺员重义轻财　假名士寡廉鲜耻"],["g","第十一回至第十六回"],["l","011.html","第十一回·宝素珠巧骗坤伶　海狗肾周旋光棍"],["l","012.html","第十二回·刻字匠揿头割耳　老东翁仗义疏财"],["l","013.html","第十三回·小二爷暗地偷情　大老官当堂吃苦"],["l","014.html","第十四回·谈来历史委实希奇　吞到药丸果然灵验"],["l","015.html","第十五回·几盆粥菜借尸还魂　一纸名单奇情怪状"],["l","016.html","第十六回·小玩耍独出头钱　大排场发行钞票"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
