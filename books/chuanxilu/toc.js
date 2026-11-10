(function(){var D=[["g","卷上"],["l","shang1.html","卷上·徐爱录（含引言、跋）"],["l","shang2.html","卷上·陆澄录"],["l","shang3.html","卷上·薛侃录"],["g","卷中"],["l","zhong1.html","卷中·钱德洪序、答顾东桥书"],["l","zhong2.html","卷中·答周道通、陆原静、欧阳崇一书"],["l","zhong3.html","卷中·答罗整庵、聂文蔚书及训蒙教约"],["g","卷下"],["l","xia1.html","卷下·陈九川录、黄修易录"],["l","xia2.html","卷下·黄省曾录"],["l","xia3.html","卷下·黄以方录（含钱德洪跋）"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
