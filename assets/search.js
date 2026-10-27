(function () {
  var input = document.getElementById('book-search');
  if (!input) return;
  var cards = Array.from(document.querySelectorAll('#book-list > li'));
  var status = document.getElementById('search-status');
  var empty = document.getElementById('search-empty');
  var variants = {'廂':'厢','遊':'游','滸':'浒','貫':'贯','實':'实','師':'师','閱':'阅','筆':'笔','記':'记','鹽':'盐','鐵':'铁','論':'论','齋':'斋','異':'异','經':'经','詩':'诗','書':'书','漢':'汉','劉':'刘','夢':'梦','紅':'红','樓':'楼','閑':'闲','閒':'闲','觀':'观','辭':'辞','國':'国','傳':'传','義':'义','蘭':'兰','蘇':'苏','軾':'轼','寬':'宽','吳':'吴','隨':'随','選':'选','賦':'赋','紀':'纪','學':'学','語':'语','說':'说','樂':'乐','華':'华'};
  function normalize(text) {
    return text.normalize('NFKC').toLowerCase().replace(/./g, function (ch) { return variants[ch] || ch; });
  }
  var texts = cards.map(function (card) { return normalize(card.textContent); });
  function filter() {
    var words = normalize(input.value).trim().split(/\s+/).filter(Boolean);
    var count = 0;
    cards.forEach(function (card, i) {
      var match = words.every(function (word) { return texts[i].includes(word); });
      card.hidden = !match;
      if (match) count++;
    });
    status.textContent = words.length ? '找到 ' + count + ' 本，共 ' + cards.length + ' 本' : '共 ' + cards.length + ' 本书';
    empty.hidden = count !== 0;
  }
  input.addEventListener('input', filter);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { input.value = ''; filter(); }
  });
  document.getElementById('search-clear').addEventListener('click', function () {
    input.value = ''; filter(); input.focus();
  });
  filter();
})();
