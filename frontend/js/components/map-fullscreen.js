/**
 * Controle Leaflet reutilizável que expande o mapa para o tamanho total da
 * tela ao clicar num botão, usando a Fullscreen API nativa do browser (o
 * elemento vai para o "top layer", imune a containing blocks criados por
 * ancestrais com backdrop-filter/transform — ver glass-card). Esc e o botão
 * nativo do browser já saem da tela cheia sem código extra.
 *
 * Usado pelos 3 mapas do app (Relatório de Abordagens, Detalhe de Abordagem
 * e Ficha de Pessoa) — cada página só precisa chamar
 * `criarControleFullscreenMapa().addTo(mapaInst)` logo após criar o mapa.
 */

const ICONE_MAPA_EXPANDIR = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 00-2 2v3M16 3h3a2 2 0 012 2v3M8 21H5a2 2 0 01-2-2v-3M16 21h3a2 2 0 002-2v-3"/></svg>';
const ICONE_MAPA_RECOLHER = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3v4a2 2 0 01-2 2H3M15 3v4a2 2 0 002 2h4M9 21v-4a2 2 0 00-2-2H3M15 21v-4a2 2 0 012-2h4"/></svg>';

/**
 * Cria um L.Control com o botão de tela cheia para um mapa Leaflet.
 *
 * @returns {L.Control} Controle pronto para `.addTo(mapaInst)`.
 */
function criarControleFullscreenMapa() {
  const controle = L.control({ position: 'topright' });

  controle.onAdd = function (mapa) {
    const containerMapa = mapa.getContainer();
    const btn = L.DomUtil.create('button', 'leaflet-bar mapa-fullscreen-btn');
    btn.type = 'button';
    btn.title = 'Expandir mapa';
    btn.innerHTML = ICONE_MAPA_EXPANDIR;

    function emFullscreen() {
      return document.fullscreenElement === containerMapa;
    }

    function aoMudarFullscreen() {
      const cheio = emFullscreen();
      btn.innerHTML = cheio ? ICONE_MAPA_RECOLHER : ICONE_MAPA_EXPANDIR;
      btn.title = cheio ? 'Sair da tela cheia' : 'Expandir mapa';
      requestAnimationFrame(() => mapa.invalidateSize({ animate: false }));
    }

    function alternar() {
      if (emFullscreen()) {
        document.exitFullscreen();
      } else {
        containerMapa.requestFullscreen();
      }
    }

    L.DomEvent.disableClickPropagation(btn);
    L.DomEvent.disableScrollPropagation(btn);
    L.DomEvent.on(btn, 'click', alternar);
    containerMapa.addEventListener('fullscreenchange', aoMudarFullscreen);

    return btn;
  };

  return controle;
}
