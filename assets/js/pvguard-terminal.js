/* PVGuard - animacion de la terminal de bienvenida.
   Todo el contenido ya esta en el HTML (funciona sin JavaScript);
   este script solo lo va "ejecutando" linea por linea.
   Se anima una vez por sesion; despues se muestra completo al instante. */
(function () {
  "use strict";

  var term = document.getElementById("pv-term");
  if (!term) return;

  var KEY = "pvguard_term_visto";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var seen = false;
  try { seen = sessionStorage.getItem(KEY) === "1"; } catch (e) {}
  if (reduce || seen) return;

  var lines = Array.prototype.slice.call(term.querySelectorAll(".t-line"));
  var skipBtn = document.getElementById("pv-term-skip");
  var skipped = false;
  var pending = [];

  // Guardar el texto de los comandos y vaciarlos para "teclearlos"
  var typed = lines.map(function (line) {
    var t = line.querySelector(".t-typed");
    if (!t) return null;
    var text = t.textContent;
    t.textContent = "";
    return { el: t, text: text };
  });

  term.classList.add("is-anim");
  if (skipBtn) skipBtn.hidden = false;

  function sleep(ms) {
    return new Promise(function (resolve) {
      if (skipped) return resolve();
      var id = setTimeout(resolve, ms);
      pending.push({ id: id, resolve: resolve });
    });
  }

  function finish() {
    lines.forEach(function (line, i) {
      line.classList.add("shown");
      if (typed[i]) typed[i].el.textContent = typed[i].text;
      line.querySelectorAll("li, .t-sec, .t-sec-total, .t-par").forEach(function (el) { el.classList.add("on"); });
    });
    var bar = term.querySelector(".t-bar i");
    var pct = term.querySelector(".t-pct");
    if (bar) bar.style.width = "100%";
    if (pct) pct.textContent = "100%";
    term.classList.remove("is-anim");
    if (skipBtn) skipBtn.hidden = true;
    try { sessionStorage.setItem(KEY, "1"); } catch (e) {}
  }

  function skip() {
    if (skipped) return;
    skipped = true;
    pending.forEach(function (p) { clearTimeout(p.id); p.resolve(); });
    pending = [];
    finish();
  }

  if (skipBtn) skipBtn.addEventListener("click", skip);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") skip(); });

  async function typeText(info) {
    for (var i = 1; i <= info.text.length; i++) {
      if (skipped) return;
      info.el.textContent = info.text.slice(0, i);
      await sleep(info.text.length > 40 ? 14 : 24);
    }
  }

  async function progress(line) {
    var bar = line.querySelector(".t-bar i");
    var pct = line.querySelector(".t-pct");
    for (var p = 0; p <= 100; p += 4) {
      if (skipped) return;
      if (bar) bar.style.width = p + "%";
      if (pct) pct.textContent = p + "%";
      await sleep(26);
    }
  }

  async function reveal(line, selector, delay) {
    var items = line.querySelectorAll(selector);
    for (var i = 0; i < items.length; i++) {
      if (skipped) return;
      items[i].classList.add("on");
      await sleep(delay);
    }
  }

  async function run() {
    await sleep(250);
    for (var i = 0; i < lines.length; i++) {
      if (skipped) return;
      var line = lines[i];
      line.classList.add("shown");

      if (typed[i]) {
        await typeText(typed[i]);
        await sleep(220);
      } else if (line.classList.contains("t-progress")) {
        await progress(line);
        await sleep(200);
      } else if (line.classList.contains("t-welcome")) {
        await sleep(120);
        await reveal(line, ".t-par", 260);
      } else if (line.classList.contains("t-block")) {
        await reveal(line, "li, .t-sec-total, .t-sec", 90);
        await sleep(150);
      } else {
        await sleep(160);
      }
    }
    if (!skipped) finish();
  }

  run();
})();
