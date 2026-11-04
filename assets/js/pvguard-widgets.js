/* PVGuard - widgets de la barra lateral:
   1) Contador de visitas (Abacus, gratuito y sin cuenta)
   2) Informacion del visitante (solo se muestra al propio visitante; no se guarda) */
(function () {
  "use strict";

  var API = "https://abacus.jasoncameron.dev";

  function ls(key, val) {
    try {
      if (val === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, val);
    } catch (e) { return null; }
  }
  function ss(key, val) {
    try {
      if (val === undefined) return sessionStorage.getItem(key);
      sessionStorage.setItem(key, val);
    } catch (e) { return null; }
  }
  function fmt(n) { return Number(n || 0).toLocaleString("es-PE"); }
  function today() {
    try {
      return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit" })
        .format(new Date()).replace(/-/g, "");
    } catch (e) {
      var d = new Date();
      return "" + d.getFullYear() + String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
    }
  }
  function getJSON(url, ms) {
    var ctrl = window.AbortController ? new AbortController() : null;
    var t = ctrl ? setTimeout(function () { ctrl.abort(); }, ms || 6000) : null;
    return fetch(url, { cache: "no-store", signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) {
        if (t) clearTimeout(t);
        if (r.status === 404) return { value: 0 };
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
  }

  /* ---------------- 1) Contador ---------------- */
  var stats = document.getElementById("pv-stats");
  if (stats) {
    var ns = stats.getAttribute("data-ns") || "pvguard-github-io";
    var base = parseInt(stats.getAttribute("data-base") || "0", 10) || 0;
    var day = today();
    var totalEl = document.getElementById("pv-total");
    var viewsEl = document.getElementById("pv-today-views");
    var visEl = document.getElementById("pv-today-visitors");

    function odometer(n) {
      var s = String(n);
      totalEl.innerHTML = "";
      for (var i = 0; i < s.length; i++) {
        var sp = document.createElement("span");
        sp.textContent = s[i];
        sp.style.animationDelay = (i * 60) + "ms";
        totalEl.appendChild(sp);
      }
      totalEl.setAttribute("aria-label", fmt(n) + " vistas totales");
    }
    odometer(base);

    // Cada carga de pagina suma una vista; el visitante del dia se cuenta una sola vez por navegador.
    var countedVisitor = ls("pvguard_visitante_dia") === day;
    var reqs = [
      getJSON(API + "/hit/" + ns + "/vistas"),
      getJSON(API + "/hit/" + ns + "/vistas-" + day),
      getJSON(API + (countedVisitor ? "/get/" : "/hit/") + ns + "/visitantes-" + day)
    ];
    Promise.all(reqs.map(function (p) { return p.catch(function () { return null; }); }))
      .then(function (r) {
        if (r[0] && typeof r[0].value === "number") odometer(base + r[0].value);
        viewsEl.textContent = r[1] && typeof r[1].value === "number" ? fmt(r[1].value) : "—";
        visEl.textContent = r[2] && typeof r[2].value === "number" ? fmt(r[2].value) : "—";
        if (r[2] && !countedVisitor) ls("pvguard_visitante_dia", day);
        if (!r[0]) stats.classList.add("offline");
      });
  }

  /* ---------------- 2) Informacion del visitante ---------------- */
  var box = document.getElementById("pv-visitor");
  if (!box) return;

  function set(k, v) {
    var el = box.querySelector('[data-k="' + k + '"]');
    if (el) el.textContent = v || "—";
  }
  function flag(cc) {
    if (!cc || cc.length !== 2) return "";
    return String.fromCodePoint.apply(null, cc.toUpperCase().split("").map(function (c) { return 127397 + c.charCodeAt(0); }));
  }
  function browser(ua) {
    var m;
    if ((m = ua.match(/Edg\/(\d+)/))) return "Edge " + m[1];
    if ((m = ua.match(/OPR\/(\d+)/))) return "Opera " + m[1];
    if ((m = ua.match(/Brave/))) return "Brave";
    if ((m = ua.match(/Firefox\/(\d+)/))) return "Firefox " + m[1];
    if ((m = ua.match(/Chrome\/(\d+)/))) return "Chrome " + m[1];
    if ((m = ua.match(/Version\/(\d+).*Safari/))) return "Safari " + m[1];
    return "Desconocido";
  }
  function os(ua) {
    var m;
    if (/Windows NT 10/.test(ua)) return "Windows 10/11";
    if (/Windows NT/.test(ua)) return "Windows";
    if ((m = ua.match(/Android (\d+)/))) return "Android " + m[1];
    if ((m = ua.match(/(iPhone|iPad).*OS (\d+)/))) return "iOS " + m[2];
    if (/Mac OS X/.test(ua)) return "macOS";
    if (/CrOS/.test(ua)) return "ChromeOS";
    if (/Linux/.test(ua)) return "Linux";
    return "Desconocido";
  }

  var ua = navigator.userAgent || "";
  set("lang", navigator.language || "—");
  set("browser", browser(ua));
  set("os", os(ua));

  var cached = null;
  try { cached = JSON.parse(ss("pvguard_geo") || "null"); } catch (e) {}

  function countryName(g) {
    try {
      if (g.cc && window.Intl && Intl.DisplayNames) return new Intl.DisplayNames(["es"], { type: "region" }).of(g.cc.toUpperCase());
    } catch (e) {}
    return g.country || "—";
  }
  function show(g) {
    set("ip", g.ip);
    set("country", countryName(g) + (g.cc ? " " + flag(g.cc) : ""));
    set("region", g.region);
    set("city", g.city);
  }

  if (cached) { show(cached); return; }

  getJSON("https://ipwho.is/?fields=ip,success,country,country_code,region,city", 5000)
    .then(function (d) {
      if (!d || d.success === false) throw new Error("ipwho");
      return { ip: d.ip, country: d.country, cc: d.country_code, region: d.region, city: d.city };
    })
    .catch(function () {
      return getJSON("https://get.geojs.io/v1/ip/geo.json", 5000).then(function (d) {
        return { ip: d.ip, country: d.country, cc: d.country_code, region: d.region, city: d.city };
      });
    })
    .then(function (g) {
      show(g);
      try { ss("pvguard_geo", JSON.stringify(g)); } catch (e) {}
    })
    .catch(function () {
      ["ip", "country", "region", "city"].forEach(function (k) { set(k, "no disponible"); });
    });
})();
