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
    // Linha 1: matrícula · data hora ; Linha 2: ARGUS.
    var data = new Date().toLocaleDateString("pt-BR");
    var line1 = _esc(matricula) + " \xB7 " + data + " " + _now();
    var line2 = "ARGUS";
    // Tile grande o bastante p/ conter o bloco rotacionado de 2 linhas; texto
    // centralizado (text-anchor=middle) e girado em torno do próprio centro,
    // então qualquer comprimento de linha cabe sem ser clipado.
    var W = 340, H = 180, cx = W / 2, cy = H / 2;
    var t = "rotate(-30 " + cx + " " + cy + ")";
    function bloco(fill, sombra) {
      return (
        '<text x="' + cx + '" y="' + cy + '" font-size="13" fill="' + fill + '"' +
        ' font-family="monospace" font-weight="bold" text-anchor="middle"' +
        ' transform="' + t + (sombra ? " translate(1 1)" : "") + '">' +
        '<tspan x="' + cx + '" dy="-3">' + line1 + "</tspan>" +
        '<tspan x="' + cx + '" dy="17">' + line2 + "</tspan>" +
        "</text>"
      );
    }
    // Dupla camada (sombra escura + branco) para visibilidade em fundo claro e escuro.
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '">' +
      bloco("rgba(0,0,0,0.045)", true) +
      bloco("rgba(255,255,255,0.06)", false) +
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
