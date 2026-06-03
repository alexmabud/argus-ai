/**
 * Gerador do manual em imagens — Argus AI.
 *
 * Reproduz as telas reais (CSS + markup do frontend) com dados ficticios
 * e gera PNGs anotados: posters (visao geral) e sequencias passo a passo
 * para os fluxos "Nova Abordagem" e "Consulta por IA".
 *
 * Renderizacao via Playwright/Chromium headless.
 */
import { chromium } from 'playwright';
import { readFileSync } from 'fs';

const css = readFileSync('app.css', 'utf8');

/* ---------- CSS extra do manual (badges, legenda, caption) ---------- */
const manualCss = `
  html, body { min-height: 0 !important; }
  body { overflow: visible; min-height: 0 !important; }
  .canvas { position: relative; min-height: 10px; }
  .col { max-width: 680px; margin: 0 auto; }
  /* Badge numerado ancorado a um elemento */
  .anno { position: relative; }
  .anno-badge {
    position: absolute; top: -16px; left: -16px; z-index: 60;
    width: 30px; height: 30px; border-radius: 50%;
    background: var(--color-primary); color: var(--color-bg);
    font-family: var(--font-display); font-weight: 700; font-size: 15px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 10px rgba(0,212,255,0.7), 0 0 22px rgba(0,212,255,0.35);
    border: 2px solid var(--color-bg);
  }
  .legend {
    margin-top: 22px; padding: 18px 20px; border-radius: 4px;
  }
  .legend h3 {
    font-family: var(--font-display); font-size: 13px; font-weight: 700;
    color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 14px; text-shadow: 0 0 8px rgba(0,212,255,0.4);
  }
  .legend-item { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 12px; }
  .legend-num {
    flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%;
    background: rgba(0,212,255,0.12); border: 1px solid var(--color-primary);
    color: var(--color-primary); font-family: var(--font-display); font-weight: 700;
    font-size: 12px; display: flex; align-items: center; justify-content: center;
  }
  .legend-txt { font-family: var(--font-body); font-size: 13.5px; color: var(--color-text); line-height: 1.45; padding-top: 2px; }
  .legend-txt b { color: var(--color-primary); font-weight: 600; }
  /* Caption das telas de passo */
  .cap {
    max-width: 620px; margin: 0 auto 16px; padding: 14px 18px; border-radius: 4px;
    border-left: 3px solid var(--color-primary);
    box-shadow: -3px 0 12px rgba(0,212,255,0.25);
    background: rgba(13,21,32,0.92);
  }
  .cap-step {
    font-family: var(--font-display); font-size: 11px; font-weight: 700;
    color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.12em;
  }
  .cap-title { font-family: var(--font-data); font-size: 19px; font-weight: 700; color: var(--color-text); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 2px; }
  .cap-desc { font-family: var(--font-body); font-size: 13px; color: var(--color-text-muted); margin-top: 6px; line-height: 1.45; }
  .lbl { font-family: var(--font-body); font-size: 11px; font-weight: 500; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; display: block; }
`;

/* ---------- Icones SVG reutilizados ---------- */
const icoSearch = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`;
const icoUser = `<svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/></svg>`;
const icoCar = `<svg width="16" height="16" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/></svg>`;
const icoChevron = `<svg width="16" height="16" style="color:var(--color-text-dim);flex-shrink:0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/></svg>`;
const icoCam = `<svg width="20" height="20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/></svg>`;

const avatarPlaceholder = (sz = 32) => `<div style="width:${sz}px;height:${sz}px;border-radius:4px;background:var(--color-surface-hover);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);border:1px solid var(--color-border);">${icoUser}</div>`;

const badge = (n) => `<span class="anno-badge">${n}</span>`;

/* ---------- Header desktop ---------- */
function header(searchValue = '') {
  return `
  <header class="app-header" style="position:static;">
    <button class="header-back-btn"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg></button>
    <span class="header-logo">ARGUS</span>
    <div class="header-search">
      <span class="search-icon">${icoSearch}</span>
      <input type="text" value="${searchValue}" placeholder="CONSULTAR BASE OPERACIONAL...">
    </div>
    <div style="flex:1"></div>
    <div class="header-status-leds">
      <div class="header-status-led"><span class="status-dot status-dot-online"></span><span>API</span></div>
      <div class="header-status-led"><span class="status-dot status-dot-online"></span><span>IA</span></div>
      <div class="header-status-led"><span class="status-dot status-dot-sync"></span><span>DB</span></div>
    </div>
    <div class="header-user-avatar"><span>AS</span></div>
  </header>`;
}

/* ---------- Bottom nav ---------- */
function bottomNav(active) {
  const item = (key, label, svg) => `
    <button class="bottom-nav-btn ${active === key ? 'active' : ''}">
      <div class="nav-pill"><div class="nav-indicator"></div>${svg}<span class="bottom-nav-label">${label}</span></div>
    </button>`;
  return `<nav class="bottom-nav" style="position:static;margin-top:28px;">
    ${item('abordagem-nova', 'Abordagem', `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>`)}
    ${item('consulta', 'Consulta IA', `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`)}
    ${item('home', 'Início', `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`)}
    ${item('ocorrencias', 'Relatórios', `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M12 12v6"/><path d="m15 15-3-3-3 3"/></svg>`)}
    ${item('dashboard', 'Analítico', `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>`)}
  </nav>`;
}

/* ---------- Documento HTML completo ---------- */
function doc(bodyHtml, { pad = 28 } = {}) {
  return `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
  <style>${css}\n${manualCss}</style></head>
  <body class="dark" style="background:#050A0F;">
    <div class="canvas" style="padding:${pad}px;">${bodyHtml}</div>
  </body></html>`;
}

/* ===================================================================
   COMPONENTES DE DADOS (markup real, valores ficticios)
   =================================================================== */

const tagPessoa = (nome) => `<span style="background:rgba(0,212,255,0.15);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);font-family:var(--font-data);font-size:12px;padding:4px 8px;border-radius:4px;display:inline-flex;align-items:center;gap:4px;">${nome}<span style="color:var(--color-primary);font-size:14px;line-height:1;">&times;</span></span>`;

const tagVeiculo = (placa) => `<span style="background:rgba(0,255,136,0.15);color:var(--color-success);border:1px solid rgba(0,255,136,0.2);font-family:var(--font-data);font-size:12px;padding:4px 8px;border-radius:4px;display:inline-flex;align-items:center;gap:4px;">${placa}<span style="color:var(--color-success);font-size:14px;line-height:1;">&times;</span></span>`;

/* Card de abordado selecionado (com foto OK, CPF, DN, mae) */
function cardAbordado() {
  return `
  <div style="border-top:1px solid var(--color-border);padding-top:12px;">
    <div style="background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.35);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:8px;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
        <span style="font-family:var(--font-body);font-size:14px;color:var(--color-text);flex:1;">JOÃO PEREIRA DA SILVA</span>
        <span style="font-family:var(--font-data);font-size:11px;padding:4px 8px;border-radius:4px;display:inline-flex;align-items:center;gap:4px;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.2);">FOTO OK</span>
      </div>
      <div style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);"><span style="color:var(--color-text-dim);">CPF:</span> 123.***.***-00</div>
      <div style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);"><span style="color:var(--color-text-dim);">DN:</span> 12/05/1990 · 36 anos</div>
      <div style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);"><span style="color:var(--color-text-dim);">Mãe:</span> MARIA PEREIRA DA SILVA</div>
      <div style="font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);"><span style="color:var(--color-text-dim);">Endereço atual:</span> QNM 34, CEILÂNDIA SUL, BRASÍLIA, DF</div>
    </div>
  </div>`;
}

/* Card GPS capturado */
function cardGPS() {
  return `
  <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:8px;">
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Localização da abordagem</span>
      <span style="color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Atualizar GPS</span>
    </div>
    <p style="font-family:var(--font-data);font-size:14px;color:var(--color-text-muted);">QNM 34, Ceilândia Sul, Brasília - DF</p>
    <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);">-15.819700, -48.110300</p>
  </div>`;
}

/* Card de vinculo veiculo->abordado (estado: vinculado) */
function cardVinculo() {
  return `
  <div style="border-radius:8px;padding:16px;display:flex;flex-direction:column;gap:12px;border:1px solid rgba(0,255,136,0.4);background:rgba(0,255,136,0.05);">
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <div>
        <span style="font-family:var(--font-data);font-weight:700;font-size:16px;color:var(--color-text);">ABC-1D23</span>
        <span style="display:block;font-family:var(--font-data);font-size:12px;color:var(--color-text-muted);">GOL — PRATA</span>
      </div>
      <span style="color:var(--color-success);font-family:var(--font-data);font-size:12px;font-weight:600;text-transform:uppercase;">vinculado</span>
    </div>
    <div>
      <p style="font-family:var(--font-data);font-size:12px;color:var(--color-danger);margin-bottom:8px;font-weight:600;">Quem estava no veículo?</p>
      <div style="display:flex;flex-wrap:wrap;gap:8px;">
        <button style="font-family:var(--font-data);font-size:13px;padding:8px 12px;border-radius:4px;background:rgba(0,212,255,0.15);border:1px solid var(--color-primary);color:var(--color-primary);font-weight:600;">JOÃO PEREIRA DA SILVA</button>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
      <span style="font-family:var(--font-data);font-size:11px;padding:4px 8px;border-radius:4px;display:inline-flex;align-items:center;gap:4px;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.2);">FOTO OK</span>
    </div>
  </div>`;
}

/* Linha de resultado de pessoa (lista consulta) */
function rowPessoa({ nome, cpf, vulgo, mae, extra } = {}) {
  return `
  <div class="hov-list-card" style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;border:1px solid var(--color-border);background:var(--color-surface);">
    ${avatarPlaceholder(32)}
    <div style="flex:1;min-width:0;">
      <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);">${nome}</p>
      ${cpf ? `<p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">CPF: ${cpf}</p>` : ''}
      ${vulgo ? `<p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">Vulgo: ${vulgo}</p>` : ''}
      ${mae ? `<p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">Mãe: ${mae}</p>` : ''}
      ${extra ? `<p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);margin-top:2px;">${extra}</p>` : ''}
    </div>
    ${icoChevron}
  </div>`;
}

/* ===================================================================
   TELAS — ABORDAGEM
   =================================================================== */

/* Bloco "Pessoas abordadas" com tag + card (para poster e passo 3) */
function blocoPessoasPreenchido(withBadge) {
  return `
  <div class="${withBadge ? 'anno' : ''} glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    ${withBadge ? badge(1) : ''}
    <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoas abordadas</span>
    <div>
      <input type="text" value="" placeholder="Buscar por nome ou CPF...">
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">${tagPessoa('JOÃO PEREIRA DA SILVA')}</div>
    </div>
    ${cardAbordado()}
  </div>`;
}

/* Bloco veiculo preenchido com vinculo */
function blocoVeiculoPreenchido(withBadge) {
  return `
  <div class="${withBadge ? 'anno' : ''} glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    ${withBadge ? badge(3) : ''}
    <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Veículo envolvido na abordagem</span>
    <div>
      <input type="text" value="" placeholder="Buscar por placa...">
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">${tagVeiculo('ABC-1D23')}</div>
    </div>
    ${cardVinculo()}
  </div>`;
}

/* Bloco observacao */
function blocoObs(withBadge) {
  return `
  <div class="${withBadge ? 'anno' : ''}" ${withBadge ? 'style="position:relative;"' : ''}>
    ${withBadge ? badge(4) : ''}
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
      <label class="lbl" style="margin-bottom:0;">Observação</label>
      <span style="font-family:var(--font-data);font-size:11px;padding:4px 10px;border-radius:4px;background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);">VOZ</span>
    </div>
    <textarea class="input-upper" rows="3">ABORDAGEM DE ROTINA. INDIVÍDUO COLABOROU. NADA DE ILÍCITO LOCALIZADO.</textarea>
  </div>`;
}

const tituloAbordagem = `
  <div>
    <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.05em;margin:0;">NOVA ABORDAGEM</h2>
    <span style="font-family:var(--font-data);font-size:11px;font-weight:500;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">REGISTRO OPERACIONAL</span>
  </div>`;

function botaoRegistrar(withBadge) {
  return `<div class="${withBadge ? 'anno' : ''}" ${withBadge ? 'style="position:relative;"' : ''}>
    ${withBadge ? badge(5) : ''}
    <button class="btn btn-primary">Registrar Abordagem</button>
  </div>`;
}

/* POSTER ABORDAGEM */
function posterAbordagem() {
  const legend = `
  <div class="glass-card legend">
    <h3>Como registrar uma abordagem</h3>
    <div class="legend-item"><div class="legend-num">1</div><div class="legend-txt"><b>Pessoas abordadas</b> — busque por nome ou CPF. Se não existir, cadastre na hora. Para cada abordado: tire a <b>foto do rosto</b>, veja CPF, idade, nome da mãe e endereço já cadastrados.</div></div>
    <div class="legend-item"><div class="legend-num">2</div><div class="legend-txt"><b>Localização</b> — o <b>GPS é capturado automaticamente</b> e vira endereço. Use "Atualizar GPS" se precisar recapturar.</div></div>
    <div class="legend-item"><div class="legend-num">3</div><div class="legend-txt"><b>Veículo</b> — busque pela placa (ou cadastre). Indique <b>quem estava no veículo</b> para criar o vínculo e tire a foto do veículo.</div></div>
    <div class="legend-item"><div class="legend-num">4</div><div class="legend-txt"><b>Observação</b> — digite ou use o botão <b>VOZ</b> para ditar. O texto é padronizado em maiúsculas.</div></div>
    <div class="legend-item"><div class="legend-num">5</div><div class="legend-txt"><b>Registrar Abordagem</b> — salva tudo. Sem internet, vai para a fila offline e sincroniza sozinho depois.</div></div>
  </div>`;

  const gpsBadge = `<div class="anno" style="position:relative;">${badge(2)}${cardGPS()}</div>`;

  const body = `
  ${header('')}
  <div class="app-main" style="margin-top:0;padding:28px 20px 8px;">
    <div class="col" style="display:flex;flex-direction:column;gap:18px;">
      ${tituloAbordagem}
      ${blocoPessoasPreenchido(true)}
      ${gpsBadge}
      ${blocoVeiculoPreenchido(true)}
      ${blocoObs(true)}
      ${botaoRegistrar(true)}
      ${legend}
    </div>
  </div>
  ${bottomNav('abordagem-nova')}`;
  return doc(body, { pad: 0 });
}

/* PASSO: caption + conteudo (largura media) */
function stepFrame(step, title, desc, contentHtml, { active = null } = {}) {
  const cap = `<div class="cap"><div class="cap-step">${step}</div><div class="cap-title">${title}</div><div class="cap-desc">${desc}</div></div>`;
  const nav = active ? bottomNav(active) : '';
  const body = `
  <div style="max-width:660px;margin:0 auto;">
    ${cap}
    <div style="display:flex;flex-direction:column;gap:16px;">${contentHtml}</div>
    ${nav}
  </div>`;
  return doc(body, { pad: 30 });
}

/* a1 — buscar pessoa (dropdown aberto) */
function a1() {
  const content = `
  <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoas abordadas</span>
    <div style="position:relative;">
      <input type="text" value="JOÃO PEREIRA" placeholder="Buscar por nome ou CPF...">
      <div style="position:relative;z-index:20;width:100%;margin-top:4px;max-height:14rem;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.4);">
        <button style="width:100%;text-align:left;padding:8px 12px;font-family:var(--font-body);font-size:14px;color:var(--color-text);background:transparent;border:none;border-bottom:1px solid var(--color-border);">JOÃO PEREIRA DA SILVA <span style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);margin-left:8px;">123.***.***-00</span></button>
        <div style="padding:12px;font-family:var(--font-body);font-size:14px;color:var(--color-text-muted);">
          <button style="width:100%;text-align:left;color:var(--color-primary);font-family:var(--font-data);font-size:11px;font-weight:600;background:transparent;border:none;text-transform:uppercase;letter-spacing:0.05em;">+ Cadastrar novo abordado</button>
        </div>
      </div>
    </div>
  </div>`;
  return stepFrame('Abordagem · Passo 1', 'Buscar o abordado', 'Comece pela pessoa. Digite nome ou CPF — o sistema busca na base. Se já existe, selecione; se não, use "+ Cadastrar novo abordado".', content);
}

/* a2 — cadastrar nova pessoa (form inline) */
function a2() {
  const field = (label, val, ph) => `<div><label class="lbl">${label}</label><input type="text" class="input-upper" value="${val}" placeholder="${ph}"></div>`;
  const content = `
  <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:16px;display:flex;flex-direction:column;gap:12px;">
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <h3 style="font-family:var(--font-display);font-size:13px;font-weight:500;color:var(--color-text);margin:0;">Cadastrar novo abordado</h3>
      <span style="color:var(--color-text-muted);font-family:var(--font-data);font-size:11px;">Cancelar</span>
    </div>
    ${field('Nome *', 'JOÃO PEREIRA DA SILVA', 'Nome completo')}
    <div><label class="lbl">CPF</label><input type="text" value="123.456.789-00" placeholder="000.000.000-00"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div><label class="lbl">Data de nascimento</label><input type="text" value="12/05/1990" placeholder="DD/MM/AAAA"></div>
      ${field('Vulgo', 'MAGRINHO', 'Apelido')}
    </div>
    ${field('Nome da mãe', 'MARIA PEREIRA DA SILVA', 'Nome completo da mãe')}
    ${field('Endereço', 'QNM 34 CASA 12', 'Rua e número')}
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
      <div><label class="lbl">Estado (UF)</label><select style="width:100%;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:12px 14px;font-size:13px;color:var(--color-text);"><option>DF — Distrito Federal</option></select></div>
      ${field('Cidade', 'CEILÂNDIA', 'Cidade')}
      ${field('Bairro', 'CEILÂNDIA SUL', 'Bairro')}
    </div>
    <button class="btn btn-primary">Salvar e adicionar</button>
  </div>`;
  return stepFrame('Abordagem · Passo 2', 'Cadastrar novo abordado', 'Não encontrou? Cadastre em segundos. Só o nome é obrigatório. Ao informar endereço, selecione UF, cidade e bairro (cria na hora se não existir).', content);
}

/* a3 — abordado selecionado + foto + GPS */
function a3() {
  const content = `${blocoPessoasPreenchido(false)}${cardGPS()}`;
  return stepFrame('Abordagem · Passo 3', 'Abordado + foto + GPS', 'Com o abordado adicionado, toque em "TIRAR FOTO" para registrar o rosto (vira reconhecimento facial). O GPS já preencheu a localização sozinho.', content);
}

/* a4 — veiculo + vinculo */
function a4() {
  return stepFrame('Abordagem · Passo 4', 'Veículo e vínculo', 'Busque a placa (ou cadastre modelo/cor/ano + foto). Depois marque QUEM estava no veículo — esse vínculo é o que liga a pessoa ao carro nas consultas.', blocoVeiculoPreenchido(false));
}

/* a5 — observacao */
function a5() {
  return stepFrame('Abordagem · Passo 5', 'Observação e registro', 'Descreva a abordagem por texto ou toque em VOZ para ditar. Depois toque em "Registrar Abordagem". Sem internet, vai para a fila offline e sincroniza sozinho.', `${blocoObs(false)}<button class="btn btn-primary">Registrar Abordagem</button>`);
}

/* a6 — modal sucesso */
function a6() {
  const modal = `
  <div style="background:rgba(5,10,15,0.6);border-radius:8px;padding:36px 16px;display:flex;align-items:center;justify-content:center;">
    <div class="glass-card" style="padding:24px;border-radius:4px;max-width:384px;width:100%;display:flex;flex-direction:column;gap:20px;border:1px solid rgba(0,212,255,0.3);box-shadow:0 0 20px rgba(0,212,255,0.1);">
      <div style="display:flex;justify-content:center;">
        <div style="width:56px;height:56px;border-radius:4px;background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.3);display:flex;align-items:center;justify-content:center;">
          <svg style="width:32px;height:32px;color:var(--color-success);" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
        </div>
      </div>
      <div style="text-align:center;display:flex;flex-direction:column;gap:4px;">
        <h3 style="font-family:var(--font-display);font-size:16px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.05em;margin:0;">Abordagem registrada!</h3>
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-text-muted);">Abordagem #1287 registrada com sucesso.</p>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        <button class="btn btn-primary" style="width:100%;">Registrar nova abordagem</button>
        <button class="btn btn-secondary" style="width:100%;">Ir para página inicial</button>
      </div>
    </div>
  </div>`;
  return stepFrame('Abordagem · Passo 6', 'Confirmação', 'Pronto. O sistema confirma com o número da abordagem. Você pode registrar outra na sequência ou voltar ao início.', modal);
}

/* ===================================================================
   TELAS — CONSULTA
   =================================================================== */

const tituloConsulta = `
  <div>
    <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.08em;">Consulta Operacional</h2>
    <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Busca Integrada // Pessoa / Endereço / Veículo</p>
  </div>`;

const separadorOu = `<div style="display:flex;align-items:center;gap:12px;"><div style="flex:1;height:1px;background:var(--color-border);"></div><span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Ou</span><div style="flex:1;height:1px;background:var(--color-border);"></div></div>`;

/* Secao Pessoa (texto + facial). showResults: 'texto'|'foto'|null */
function secaoPessoa(showResults, withBadge) {
  let results = '';
  if (showResults === 'texto') {
    results = `
    <div style="display:flex;flex-direction:column;gap:6px;">
      <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">Resultados por nome/CPF (1)</p>
      ${rowPessoa({ nome: 'JOÃO PEREIRA DA SILVA', cpf: '123.***.***-00', vulgo: 'MAGRINHO', mae: 'MARIA PEREIRA DA SILVA' })}
    </div>`;
  }
  const facial = `
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="flex:1;height:1px;background:var(--color-border);"></div><span style="font-family:var(--font-data);font-size:10px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;">Ou</span><div style="flex:1;height:1px;background:var(--color-border);"></div>
    </div>
    <div class="hov-cta-card" style="width:100%;display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 12px;border-radius:4px;border:2px dashed rgba(0,212,255,0.3);background:rgba(0,212,255,0.03);">
      <div style="width:40px;height:40px;border-radius:4px;background:rgba(0,212,255,0.1);display:flex;align-items:center;justify-content:center;color:var(--color-primary);">${icoCam}</div>
      <div style="text-align:center;">
        <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-primary);">Reconhecimento Facial</p>
        <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Toque para enviar foto e comparar com o banco</p>
      </div>
    </div>`;
  return `
  <div class="${withBadge ? 'anno' : ''} glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    ${withBadge ? badge(1) : ''}
    <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoa</span>
    <div style="position:relative;">
      <input type="text" value="${showResults === 'texto' ? 'JOÃO PEREIRA' : ''}" placeholder="NOME COMPLETO OU CPF..." style="padding-left:40px;">
      <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--color-text-dim);">${icoUser}</span>
    </div>
    ${results}
    ${facial}
  </div>`;
}

/* Secao endereco. withResults bool */
function secaoEndereco(withResults, withBadge) {
  const field = (label, val, ph) => `<div><label class="lbl">${label}</label><input type="text" value="${val}" placeholder="${ph}"></div>`;
  let results = '';
  if (withResults) {
    results = `
    <div style="display:flex;flex-direction:column;gap:6px;">
      <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">Pessoas neste endereço (2)</p>
      ${rowPessoa({ nome: 'JOÃO PEREIRA DA SILVA', cpf: '123.***.***-00', extra: 'Cadastrado em 14/03/2026' })}
      ${rowPessoa({ nome: 'CARLOS ANTUNES ROCHA', cpf: '987.***.***-11', extra: 'Cadastrado em 02/01/2026' })}
    </div>`;
  }
  return `
  <div class="${withBadge ? 'anno' : ''} glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    ${withBadge ? badge(2) : ''}
    <div>
      <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Filtros por Endereço</span>
      <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Filtre abordados pelo local de residência cadastrado.</p>
    </div>
    <div style="display:flex;flex-direction:column;gap:10px;">
      ${field('Bairro', withResults ? 'CEILÂNDIA SUL' : '', 'Bairro...')}
      ${field('Cidade', withResults ? 'CEILÂNDIA' : '', 'Cidade...')}
      ${field('Estado (UF)', withResults ? 'DF' : '', 'DF')}
    </div>
    ${results}
  </div>`;
}

/* Secao veiculo. withResults bool */
function secaoVeiculo(withResults, withBadge) {
  let results = '';
  if (withResults) {
    results = `
    <div style="display:flex;flex-direction:column;gap:6px;">
      <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">Abordados vinculados (1)</p>
      <div class="hov-list-card" style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:4px;border:1px solid var(--color-border);background:var(--color-surface);">
        ${avatarPlaceholder(32)}
        <div style="flex:1;min-width:0;">
          <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);">JOÃO PEREIRA DA SILVA</p>
          <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">CPF: 123.***.***-00</p>
          <p style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);margin-top:2px;">Vinculado via: ABC-1D23 · GOL · PRATA · 2014</p>
        </div>
        <div style="width:32px;height:32px;border-radius:4px;background:var(--color-surface-hover);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);border:1px solid var(--color-border);">${icoCar}</div>
        ${icoChevron}
      </div>
    </div>`;
  }
  return `
  <div class="${withBadge ? 'anno' : ''} glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    ${withBadge ? badge(3) : ''}
    <div>
      <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Buscar por Veículo</span>
      <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);margin-top:2px;">Encontre o abordado pelo veículo com que foi visto.</p>
    </div>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div><label class="lbl">Placa</label><input type="text" value="${withResults ? 'ABC-1D23' : ''}" placeholder="ABC-1234..."></div>
      <div><label class="lbl">Modelo</label><input type="text" value="${withResults ? 'GOL' : ''}" placeholder="Modelo do veículo..."></div>
    </div>
    ${results}
  </div>`;
}

/* POSTER CONSULTA */
function posterConsulta() {
  const legend = `
  <div class="glass-card legend">
    <h3>Como consultar pela IA</h3>
    <div class="legend-item"><div class="legend-num">1</div><div class="legend-txt"><b>Pessoa</b> — busque por <b>nome ou CPF</b>, ou envie uma foto e a IA faz o <b>reconhecimento facial</b>, comparando com o banco e mostrando o % de semelhança.</div></div>
    <div class="legend-item"><div class="legend-num">2</div><div class="legend-txt"><b>Filtros por endereço</b> — liste todos os abordados que moram num bairro, cidade ou UF.</div></div>
    <div class="legend-item"><div class="legend-num">3</div><div class="legend-txt"><b>Busca por veículo</b> — informe a placa ou o modelo e veja quais abordados já foram vistos com aquele carro.</div></div>
    <div class="legend-item"><div class="legend-num">★</div><div class="legend-txt">Toque em qualquer resultado para abrir a <b>ficha completa</b> do abordado. A IA <b>só organiza dados já cadastrados</b> — nunca inventa fatos.</div></div>
  </div>`;
  const body = `
  ${header('')}
  <div class="app-main" style="margin-top:0;padding:28px 20px 8px;">
    <div class="col" style="display:flex;flex-direction:column;gap:16px;">
      ${tituloConsulta}
      ${secaoPessoa('texto', true)}
      ${separadorOu}
      ${secaoEndereco(true, true)}
      ${separadorOu}
      ${secaoVeiculo(true, true)}
      ${legend}
    </div>
  </div>
  ${bottomNav('consulta')}`;
  return doc(body, { pad: 0 });
}

/* c1 — busca por nome/CPF */
function c1() {
  return stepFrame('Consulta · Passo 1', 'Buscar por nome ou CPF', 'Digite o nome completo ou o CPF. A busca é instantânea e tolera erros de digitação. Toque no resultado para abrir a ficha.', secaoPessoa('texto', false), { });
}

/* c2 — reconhecimento facial com resultados */
function c2() {
  const preview = `
    <div style="display:flex;align-items:center;gap:10px;padding:8px;background:rgba(0,212,255,0.05);border-radius:4px;border:1px solid rgba(0,212,255,0.2);">
      <div style="width:48px;height:48px;border-radius:4px;background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);flex-shrink:0;">${icoUser}</div>
      <div style="flex:1;min-width:0;">
        <p style="font-family:var(--font-body);font-size:12px;color:var(--color-primary);font-weight:500;">suspeito_camera_03.jpg</p>
        <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.05em;">Analisando base operacional...</p>
      </div>
    </div>`;
  const conf = (nome, cpf, pct, color) => `
    <div class="hov-list-card" style="padding:10px;border-radius:4px;border:1px solid var(--color-border);background:var(--color-surface);">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:40px;height:40px;border-radius:4px;background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;color:var(--color-text-dim);flex-shrink:0;border:1px solid var(--color-border);">${icoUser}</div>
        <div style="flex:1;min-width:0;">
          <p style="font-family:var(--font-body);font-size:13px;font-weight:500;color:var(--color-text);">${nome}</p>
          <p style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);">CPF: ${cpf}</p>
          <div style="margin-top:6px;display:flex;align-items:center;gap:8px;">
            <div style="flex:1;height:4px;background:var(--color-surface-hover);border-radius:2px;overflow:hidden;"><div style="height:100%;border-radius:2px;width:${pct}%;background:${color};"></div></div>
            <span style="font-family:var(--font-data);font-size:12px;font-weight:700;color:${color};">${pct}%</span>
          </div>
        </div>
      </div>
    </div>`;
  const content = `
  <div class="glass-card" style="padding:16px;border-radius:4px;display:flex;flex-direction:column;gap:12px;">
    <span style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;">Pessoa</span>
    ${preview}
    <div style="display:flex;flex-direction:column;gap:6px;">
      <p style="font-family:var(--font-data);font-size:11px;font-weight:600;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.08em;">Resultados por foto (3)</p>
      ${conf('JOÃO PEREIRA DA SILVA', '123.***.***-00', 92, 'var(--color-success)')}
      ${conf('MÁRCIO DOS SANTOS', '456.***.***-22', 71, '#FFD700')}
      ${conf('PESSOA SEM NOME', '—', 58, 'var(--color-danger)')}
    </div>
  </div>`;
  return stepFrame('Consulta · Passo 2', 'Reconhecimento facial', 'Envie uma foto e a IA compara com todos os rostos do banco. Cada resultado mostra o % de semelhança: verde (alta), amarelo (média), laranja (baixa).', content);
}

/* c3 — filtro por endereco */
function c3() {
  return stepFrame('Consulta · Passo 3', 'Filtrar por endereço', 'Quer saber quem mora numa área? Preencha bairro, cidade e/ou UF e veja todos os abordados com endereço cadastrado ali.', secaoEndereco(true, false));
}

/* c4 — busca por veiculo */
function c4() {
  return stepFrame('Consulta · Passo 4', 'Buscar por veículo', 'Informe a placa (ou modelo/cor) e descubra quais abordados já foram vistos com aquele veículo — o vínculo criado na abordagem.', secaoVeiculo(true, false));
}

/* ===================================================================
   RENDER
   =================================================================== */
const screens = [
  { name: 'abordagem_poster', html: posterAbordagem(), w: 1120 },
  { name: 'abordagem_passo1_buscar', html: a1(), w: 760 },
  { name: 'abordagem_passo2_cadastrar', html: a2(), w: 760 },
  { name: 'abordagem_passo3_foto_gps', html: a3(), w: 760 },
  { name: 'abordagem_passo4_veiculo', html: a4(), w: 760 },
  { name: 'abordagem_passo5_observacao', html: a5(), w: 760 },
  { name: 'abordagem_passo6_sucesso', html: a6(), w: 760 },
  { name: 'consulta_poster', html: posterConsulta(), w: 1120 },
  { name: 'consulta_passo1_nome_cpf', html: c1(), w: 760 },
  { name: 'consulta_passo2_facial', html: c2(), w: 760 },
  { name: 'consulta_passo3_endereco', html: c3(), w: 760 },
  { name: 'consulta_passo4_veiculo', html: c4(), w: 760 },
];

const browser = await chromium.launch();
for (const s of screens) {
  const page = await browser.newPage({ viewport: { width: s.w, height: 800 }, deviceScaleFactor: 2 });
  await page.setContent(s.html, { waitUntil: 'networkidle' });
  try { await page.evaluate(() => document.fonts.ready); } catch {}
  await page.waitForTimeout(250);
  const out = new URL('./out/' + s.name + '.png', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
  await page.locator('.canvas').screenshot({ path: out });
  await page.close();
  console.log('rendered', s.name);
}
await browser.close();
console.log('DONE');
