/* PVGuard - menu movil, archivo y busqueda */
(function () {
  "use strict";

  // Menu en movil
  var nav = document.querySelector(".tabs-outer");
  var toggle = document.querySelector(".nav-toggle");
  if (nav && toggle) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
  document.querySelectorAll(".sub-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var li = btn.parentElement;
      var open = li.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  // Cerrar submenus abiertos al tocar fuera
  document.addEventListener("click", function (ev) {
    document.querySelectorAll(".has-sub.open").forEach(function (li) {
      if (!li.contains(ev.target)) {
        li.classList.remove("open");
        var b = li.querySelector(".sub-toggle");
        if (b) b.setAttribute("aria-expanded", "false");
      }
    });
  });

  // Selector "Archivo del Blog"
  var archive = document.querySelector(".archive-select");
  if (archive) {
    archive.addEventListener("change", function () {
      if (archive.value) window.location.href = archive.value;
    });
  }

  // Busqueda (pagina /buscar/)
  var results = document.getElementById("search-results");
  if (!results || !window.PVGUARD_SEARCH_INDEX) return;

  var input = document.getElementById("search-input");
  var status = document.getElementById("search-status");
  var params = new URLSearchParams(window.location.search);
  var q = (params.get("q") || "").trim();
  if (input) input.value = q;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function norm(s) {
    return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  function highlight(text, terms) {
    var out = esc(text);
    terms.forEach(function (t) {
      if (!t) return;
      var re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }

  if (!q) { status.textContent = "Escribe un término y presiona Buscar."; return; }
  status.textContent = "Buscando \"" + q + "\"...";

  fetch(window.PVGUARD_SEARCH_INDEX)
    .then(function (r) { return r.json(); })
    .then(function (posts) {
      var terms = norm(q).split(/\s+/).filter(Boolean);
      var hits = posts.map(function (p) {
        var title = norm(p.title), body = norm(p.text), tags = norm((p.tags || []).join(" "));
        var score = 0;
        for (var i = 0; i < terms.length; i++) {
          var t = terms[i];
          var inT = title.indexOf(t) > -1, inG = tags.indexOf(t) > -1, inB = body.indexOf(t) > -1;
          if (!inT && !inG && !inB) return null;
          score += (inT ? 10 : 0) + (inG ? 5 : 0) + (inB ? 1 : 0);
        }
        return { p: p, score: score };
      }).filter(Boolean).sort(function (a, b) { return b.score - a.score; });

      status.textContent = hits.length
        ? hits.length + " resultado(s) para \"" + q + "\""
        : "Sin resultados para \"" + q + "\".";

      results.innerHTML = hits.map(function (h) {
        var p = h.p;
        var idx = norm(p.text).indexOf(terms[0]);
        var start = Math.max(0, idx - 80);
        var snippet = (start > 0 ? "…" : "") + p.text.substr(start, 220) + "…";
        return '<li><a class="r-title" href="' + esc(p.url) + '">' + esc(p.title) + "</a>" +
          '<div class="r-meta">' + esc(p.date) + (p.tags && p.tags.length ? " · " + esc(p.tags.join(", ")) : "") + "</div>" +
          '<div class="r-snippet">' + highlight(snippet, q.split(/\s+/)) + "</div></li>";
      }).join("");
    })
    .catch(function () { status.textContent = "No se pudo cargar el índice de búsqueda."; });
})();
