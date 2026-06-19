/**
 * Watermark rastreável — Camada 1: overlay visual client-side.
 *
 * Injeta um div fixo (pointer-events: none) com a matrícula e o
 * horário atual em tile diagonal sobre toda a tela. Funciona como
 * deterrente: quem tirar screenshot captura automaticamente a
 * identidade do operador.
 *
 * Resiliências implementadas:
 * - MutationObserver recria o overlay se removido via DevTools.
 * - Timestamp atualizado a cada 10 s para registrar o momento do screenshot.
 * - Evento `storage` detecta logout em outra aba e para o overlay.
 * - Releitura de localStorage na inicialização restaura o overlay após F5.
 */

(function () {
  "use strict";

  var WM_ID = "__argus_wm__";
  var _matricula = null;
  var _interval = null;
  var _observer = null;

  function _now() {
    return new Date().toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function _esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function _buildBg(matricula) {
    var label = _esc(matricula) + " \xB7 " + _now();
    // Dupla camada (branco + sombra escura) para visibilidade em fundo claro e escuro.
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="110">' +
      '<text x="10" y="55" font-size="13" fill="rgba(0,0,0,0.07)"' +
      ' font-family="monospace" font-weight="bold"' +
      ' transform="rotate(-30 160 55) translate(1 1)">' + label + "</text>" +
      '<text x="10" y="55" font-size="13" fill="rgba(255,255,255,0.09)"' +
      ' font-family="monospace" font-weight="bold"' +
      ' transform="rotate(-30 160 55)">' + label + "</text>" +
      "</svg>";
    var b64 = btoa(unescape(encodeURIComponent(svg)));
    return 'url("data:image/svg+xml;base64,' + b64 + '")';
  }

  function _create() {
    var el = document.createElement("div");
    el.id = WM_ID;
    el.setAttribute("aria-hidden", "true");
    el.style.cssText =
      "position:fixed;top:0;left:0;width:100%;height:100%;" +
      "pointer-events:none;z-index:2147483647;" +
      "background-repeat:repeat;";
    el.style.backgroundImage = _buildBg(_matricula);
    document.body.appendChild(el);
    return el;
  }

  function _refresh() {
    var el = document.getElementById(WM_ID);
    if (el) el.style.backgroundImage = _buildBg(_matricula);
  }

  function _ensureOverlay() {
    if (_matricula && !document.getElementById(WM_ID)) _create();
  }

  function start(matricula) {
    stop();
    _matricula = matricula;
    _create();
    _interval = setInterval(_refresh, 10000);
    _observer = new MutationObserver(_ensureOverlay);
    _observer.observe(document.body, { childList: true, subtree: false });
  }

  function stop() {
    clearInterval(_interval);
    _interval = null;
    if (_observer) {
      _observer.disconnect();
      _observer = null;
    }
    var el = document.getElementById(WM_ID);
    if (el) el.remove();
    _matricula = null;
  }

  window.addEventListener("wm:start", function (e) {
    start(e.detail && e.detail.matricula);
  });
  window.addEventListener("wm:stop", stop);

  // Logout em outra aba (localStorage limpo) → para o overlay nesta aba.
  window.addEventListener("storage", function (e) {
    if (e.key === "argus_user" && !e.newValue) stop();
  });

  // Restaura o overlay após reload (F5) quando sessão ainda está ativa.
  try {
    var stored = localStorage.getItem("argus_user");
    if (stored) {
      var u = JSON.parse(stored);
      if (u && u.matricula) start(u.matricula);
    }
  } catch (_e) {
    /* não bloqueia inicialização se localStorage estiver corrompido */
  }
})();
