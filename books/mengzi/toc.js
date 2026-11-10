(function(){var D=[["l","juan01.html","梁惠王上"],["l","juan02.html","梁惠王下"],["l","juan03.html","公孙丑上"],["l","juan04.html","公孙丑下"],["l","juan05.html","滕文公上"],["l","juan06.html","滕文公下"],["l","juan07.html","离娄上"],["l","juan08.html","离娄下"],["l","juan09.html","万章上"],["l","juan10.html","万章下"],["l","juan11.html","告子上"],["l","juan12.html","告子下"],["l","juan13.html","尽心上"],["l","juan14.html","尽心下"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
