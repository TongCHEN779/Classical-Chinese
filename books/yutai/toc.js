(function(){var D=[["l","xu.html","序"],["l","j01.html","卷一·枚乘、李延年、苏武等"],["l","j02.html","卷二·魏文帝、甄皇后、刘勋妻王氏等"],["l","j03.html","卷三·陆机、陆云、张协等"],["l","j04.html","卷四·王僧达、颜延之、鲍照等"],["l","j05.html","卷五·江淹、丘迟、沈约等"],["l","j06.html","卷六·吴均、王僧孺、张率等"],["l","j07.html","卷七·梁武帝、皇太子、邵陵王纶等"],["l","j08.html","卷八·萧子显、王筠、刘孝绰等"],["l","j09.html","卷九·司马相如、乌孙公主、汉成帝时等"],["l","j10.html","卷十·贾充、孙绰、王献之等"]];var t=document.querySelector('.toc.side');if(!t)return;var ul=t.querySelector('ul'),cur=t.getAttribute('data-cur'),tp=t.querySelector('template');
D.forEach(function(d){var li=document.createElement('li');
if(d[0]==='g'){li.className='grp';li.textContent=d[1];}
else if(d[0]==='x'){var s=document.createElement('span');s.textContent=d[1];li.appendChild(s);}
else{var a=document.createElement('a');a.href=d[1];a.textContent=d[2];li.appendChild(a);
if(d[1]===cur){li.className='cur';a.setAttribute('aria-current','page');if(tp)li.appendChild(tp.content.cloneNode(true));}}
ul.appendChild(li);});})();
