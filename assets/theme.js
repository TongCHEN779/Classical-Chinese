(function () {
  var KEY = "theme", root = document.documentElement;
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function system() { return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
  function apply(t) { if (t === "dark" || t === "light") root.setAttribute("data-theme", t); else root.removeAttribute("data-theme"); }
  apply(stored());
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "theme-toggle";
    function current() { return root.getAttribute("data-theme") || system(); }
    function label() { var d = current() === "dark"; btn.textContent = d ? "☀" : "☾"; btn.title = d ? "切换为浅色背景" : "切换为深色背景"; btn.setAttribute("aria-label", btn.title); }
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      apply(next); try { localStorage.setItem(KEY, next); } catch (e) {}
      label();
    });
    label();
    document.body.appendChild(btn);
    // 总目录很长时，把当前页滚到侧栏中部
    var cur = document.querySelector(".toc.side li.cur"), box = document.querySelector(".toc.side");
    if (cur && box && box.scrollHeight > box.clientHeight) {
      box.scrollTop = Math.max(0, cur.offsetTop - box.clientHeight / 3);
    }
  });
})();
