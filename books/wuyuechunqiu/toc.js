(function(){var D=[["l","j01.html","吴太伯传第一"],["l","j02.html","吴王寿梦传第二"],["l","j03.html","王僚使公子光传第三"],["l","j04.html","阖闾内传第四"],["l","j05.html","夫差内传第五"],["l","j06.html","越王无余外传第六"],["l","j07.html","勾践入臣外传第七"],["l","j08.html","勾践归国外传第八"],["l","j09.html","勾践阴谋外传第九"],["l","j10.html","勾践伐吴外传第十"],["l","x1.html","佚文"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
