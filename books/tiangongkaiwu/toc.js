(function(){var D=[["l","x1.html","自序"],["l","p01.html","乃粒第一"],["l","p02.html","乃服第二"],["l","p03.html","彰施第三"],["l","p04.html","粹精第四"],["l","p05.html","作咸第五"],["l","p06.html","甘嗜第六"],["l","p07.html","陶埏第七"],["l","p08.html","冶铸第八"],["l","p09.html","舟车第九"],["l","p10.html","锤锻第十"],["l","p11.html","燔石第十一"],["l","p12.html","膏液第十二"],["l","p13.html","杀青第十三"],["l","p14.html","五金第十四"],["l","p15.html","佳兵第十五"],["l","p16.html","丹青第十六"],["l","p17.html","曲蘖第十七"],["l","p18.html","珠玉第十八"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
