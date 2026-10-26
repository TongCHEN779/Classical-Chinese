(function () {
  var tip = document.getElementById('tip');
  var cur = null;
  var toc = document.querySelector('.toc');
  var narrow = matchMedia('(max-width: 800px)');
  if (toc) {
    function fitToc() { toc.open = !narrow.matches; }
    fitToc();
    narrow.addEventListener('change', fitToc);
    toc.addEventListener('click', function (e) {
      if (narrow.matches && e.target.closest('a')) toc.open = false;
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && narrow.matches && toc.open) {
        toc.open = false;
        toc.querySelector('summary').focus();
      }
    });
  }

  function place(el, x, y) {
    var rects = el.getClientRects(), r = rects[0];
    for (var i = 0; i < rects.length; i++) {
      if (y >= rects[i].top - 2 && y <= rects[i].bottom + 2) { r = rects[i]; break; }
    }
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.max(8, Math.min(x - w / 2, window.innerWidth - w - 8));
    var top = r.top - h - 8;
    if (top < 48) top = r.bottom + 8;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function show(el, x, y) {
    if (cur && cur !== el) cur.classList.remove('on');
    cur = el; el.classList.add('on');
    tip.textContent = el.dataset.t;
    tip.hidden = false;
    place(el, x, y);
  }
  function hide() {
    if (cur) cur.classList.remove('on');
    cur = null; tip.hidden = true;
  }
  function center(el) {
    var r = el.getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2];
  }
  var sent = function (t) { return t.closest ? t.closest('.s') : null; };

  document.addEventListener('pointerover', function (e) {
    if (e.pointerType !== 'mouse') return;
    var s = sent(e.target); if (s) show(s, e.clientX, e.clientY);
  });
  document.addEventListener('pointermove', function (e) {
    if (e.pointerType !== 'mouse' || !cur) return;
    var s = sent(e.target); if (s === cur) place(cur, e.clientX, e.clientY);
  });
  document.addEventListener('pointerout', function (e) {
    if (e.pointerType !== 'mouse') return;
    var s = sent(e.target); if (s && s === cur && !s.contains(e.relatedTarget)) hide();
  });
  document.addEventListener('click', function (e) {
    var s = sent(e.target);
    if (s && e.pointerType !== 'mouse' && e.detail !== 0 && matchMedia('(hover: none)').matches) {
      if (cur === s) hide(); else show(s, e.clientX, e.clientY);
    } else if (!s && matchMedia('(hover: none)').matches) hide();
  });
  document.addEventListener('focusin', function (e) {
    var s = sent(e.target); if (s) { var c = center(s); show(s, c[0], c[1]); }
  });
  document.addEventListener('focusout', function (e) { if (sent(e.target)) hide(); });
  window.addEventListener('scroll', hide, { passive: true });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });

  document.querySelectorAll('.note-btn').forEach(function (b) {
    b.addEventListener('click', function () {
      var box = document.getElementById(b.getAttribute('aria-controls'));
      var open = b.getAttribute('aria-expanded') === 'true';
      b.setAttribute('aria-expanded', String(!open));
      box.hidden = open;
    });
  });
})();
