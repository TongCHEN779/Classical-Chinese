(function(){var D=[["l","j1.html","帝王世纪第一"],["l","j2.html","帝王世纪第二"],["l","j3.html","帝王世纪第三"],["l","j4.html","帝王世纪第四"],["l","j5.html","帝王世纪第五"],["l","j6.html","帝王世纪第六"],["l","j7.html","帝王世纪第七"],["l","j8.html","帝王世纪第八"],["l","j9.html","帝王世纪第九"],["l","j10.html","帝王世纪第十"],["l","x1.html","附录"],["l","x2.html","补遗"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
