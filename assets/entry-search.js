(function () {
  var input = document.getElementById('entry-search');
  var list = document.getElementById('entry-list');
  if (!input || !list) return;
  var items = Array.from(list.querySelectorAll('li'));
  var status = document.getElementById('entry-status');
  var empty = document.getElementById('entry-empty');
  var variants = {'廂':'厢','遊':'游','滸':'浒','貫':'贯','實':'实','師':'师','閱':'阅','筆':'笔','記':'记','鹽':'盐','鐵':'铁','論':'论','齋':'斋','異':'异','經':'经','詩':'诗','書':'书','漢':'汉','劉':'刘','夢':'梦','紅':'红','樓':'楼','閑':'闲','閒':'闲','觀':'观','辭':'辞','國':'国','傳':'传','義':'义','蘭':'兰','蘇':'苏','軾':'轼','寬':'宽','吳':'吴','隨':'随','選':'选','賦':'赋','紀':'纪','學':'学','語':'语','說':'说','樂':'乐','華':'华','歸':'归','陽':'阳','脩':'修','舜':'舜','欽':'钦','曆':'历','點':'点','島':'岛','鳥':'鸟','雲':'云','門':'门','長':'长','與':'与','後':'后','為':'为','於':'于','東':'东','陳':'陈','鮑':'鲍','盧':'卢','龔':'龚','錢':'钱','謙':'谦','袁':'袁','閣':'阁','靜':'静','賣':'卖','獄':'狱','雜':'杂','讓':'让','慮':'虑','廬':'庐','蕪':'芜','樹':'树','園':'园','訓':'训','壽':'寿','驚':'惊','贈':'赠','獨':'独','來':'来','說':'说'};
  function normalize(text) {
    return text.normalize('NFKC').toLowerCase().replace(/./g, function (ch) { return variants[ch] || ch; });
  }
  var texts = items.map(function (li) { return normalize(li.textContent); });
  function filter() {
    var words = normalize(input.value).trim().split(/\s+/).filter(Boolean);
    var count = 0;
    items.forEach(function (li, i) {
      var match = words.every(function (word) { return texts[i].includes(word); });
      li.hidden = !match;
      if (match) count++;
    });
    status.textContent = words.length ? '找到 ' + count + ' 篇，共 ' + items.length + ' 篇' : '共 ' + items.length + ' 篇，可按篇名或作者筛选';
    empty.hidden = count !== 0;
  }
  input.addEventListener('input', filter);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { input.value = ''; filter(); }
  });
  document.getElementById('entry-clear').addEventListener('click', function () { input.value = ''; filter(); input.focus(); });
  filter();
})();
