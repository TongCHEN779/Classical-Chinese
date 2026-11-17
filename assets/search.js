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
  var letters = Array.from(document.querySelectorAll('#letter-bar .letter'));
  var letter = '';
  letters.forEach(function (btn) {
    btn.disabled = !cards.some(function (card) { return card.dataset.letter === btn.dataset.letter; });
    btn.addEventListener('click', function () {
      letter = letter === btn.dataset.letter ? '' : btn.dataset.letter;
      filter();
    });
  });
  var PAGE = 10;
  var page = 1;
  var pager = document.getElementById('pager');
  var matches = cards.slice();
  function render() {
    var pages = Math.max(1, Math.ceil(matches.length / PAGE));
    if (page > pages) page = pages;
    var from = (page - 1) * PAGE, to = from + PAGE;
    cards.forEach(function (card) { card.hidden = true; });
    matches.forEach(function (card, i) { card.hidden = !(i >= from && i < to); });
    if (!pager) return;
    pager.innerHTML = '';
    pager.hidden = pages <= 1;
    function btn(label, target, opts) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      opts = opts || {};
      if (opts.current) b.setAttribute('aria-current', 'page');
      if (opts.disabled) b.disabled = true;
      b.addEventListener('click', function () {
        page = target;
        render();
        var top = document.getElementById('book-list');
        if (top && top.scrollIntoView) top.scrollIntoView({block: 'start'});
      });
      pager.appendChild(b);
    }
    btn('上一页', page - 1, {disabled: page === 1});
    var last = 0;
    for (var p = 1; p <= pages; p++) {
      if (p !== 1 && p !== pages && Math.abs(p - page) > 2) continue;      // 页数多时只显示首尾与当前页前后
      if (last && p - last > 1) {
        var gap = document.createElement('span');
        gap.textContent = '…';
        gap.className = 'gap';
        pager.appendChild(gap);
      }
      btn(String(p), p, {current: p === page});
      last = p;
    }
    btn('下一页', page + 1, {disabled: page === pages});
  }
  function filter() {
    var words = normalize(input.value).trim().split(/\s+/).filter(Boolean);
    var filtering = words.length > 0 || letter !== '';
    letters.forEach(function (btn) { btn.setAttribute('aria-pressed', btn.dataset.letter === letter ? 'true' : 'false'); });
    matches = cards.filter(function (card, i) {
      return (!letter || card.dataset.letter === letter) &&
        words.every(function (word) { return texts[i].includes(word); });
    });
    page = 1;
    var pages = Math.max(1, Math.ceil(matches.length / PAGE));
    status.textContent = !filtering ? '共 ' + cards.length + ' 个条目，每页 ' + PAGE + ' 个，第 ' + page + ' / ' + pages + ' 页' :
      '找到 ' + matches.length + ' 个，共 ' + cards.length + ' 个' + (letter ? '（首字母 ' + letter + '）' : '');
    empty.hidden = matches.length !== 0;
    render();
  }
  input.addEventListener('input', filter);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { input.value = ''; letter = ''; filter(); }
  });
  document.getElementById('search-clear').addEventListener('click', function () {
    input.value = ''; letter = ''; filter(); input.focus();
  });
  filter();
})();
