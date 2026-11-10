(function(){var D=[["g","第一回至第十回"],["l","001.html","第一回·辟香港通商初发达　卖料泡穷汉得奇逢"],["l","002.html","第二回·察嗜好货郎逐利　发储藏夫妇秤金"],["l","003.html","第三回·开店铺广交亡命　充汉奸再发洋财"],["l","004.html","第四回·区牧蕃初登写字楼　陶庆云引见咸水妹"],["l","005.html","第五回·学洋话陶庆云著书　犯乡例花雪畦追月"],["l","006.html","第六回·五木无灵少爷卖猪仔　一条妙计财主仗洋人"],["l","007.html","第七回·洋奴得意别有原因　土老赴席许多笑话"],["l","008.html","第八回·花雪畦领略狠心法　杭森娘演说发财人"],["l","009.html","第九回·世态炎凉寸心生变幻　荣枯得失数语决机关"],["l","010.html","第十回·舒云旃历举得意人　知微子喝破发财诀"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
