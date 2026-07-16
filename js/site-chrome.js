// ══════════════════════════════════════════════════════════════════
// SITE CHROME — cabeçalho, rodapé e leads compartilhados entre as
// páginas do Pandora Data SP (Início, Sobre, Blog e artigos).
// Editar aqui muda em todas as páginas de uma vez.
// ══════════════════════════════════════════════════════════════════

const SUPABASE_URL = 'https://sobmjqounukzbplrmhkr.supabase.co';
const SUPABASE_KEY = 'sb_publishable_o5fTXnmp8hhp76WymPJ_MQ_MuJUhvfY';
async function saveLead(payload) {
  try {
    const res = await fetch(SUPABASE_URL + '/rest/v1/leads_vendidos', {
      method: 'POST',
      headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY, 'Content-Type': 'application/json', 'Prefer': 'return=minimal' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      console.error('Erro ao salvar lead:', res.status, await res.text());
      return false;
    }
    return true;
  } catch (e) { console.error('Erro ao salvar lead:', e); return false; }
}

const SITE_WORDMARK = `<svg class="wordmark" viewBox="0 0 1375.79 376.12" xmlns="http://www.w3.org/2000/svg" fill="currentColor"><path d="M356.75,22.3v64.36h19.36V14.48l-19.36,7.82ZM14.48,0l7.86,19.37h331.48l7.82-19.37H14.48ZM353.82,356.71H22.34l-7.86,19.41h347.16l-7.82-19.41ZM19.36,22.3L0,14.44v347.25l19.36-7.86V22.3ZM356.75,289.42v64.4l19.36,7.82v-72.22h-19.36Z"/><path d="M200.09,121.97h-48.95v18.17h48.81c19.05,0,30.65,10.13,30.65,27.54s-11.59,28.03-30.65,28.03h-48.81v67.42h21.54v-49.26h27.41c31.67,0,52.06-16.7,52.06-46.33s-20.39-45.57-52.06-45.57Z"/><path d="M377.49,121.97h-23.9l-54.1,141.15h21.85l13.01-35.04h60.98l12.79,35.04h23.01l-53.65-141.15ZM340.85,210.62l24.16-65.07,23.76,65.07h-47.93Z"/><path d="M593.71,121.97v107.26l-72.58-107.26h-23.59v141.15h20.08v-110.37l74.31,110.37h21.85V121.97h-20.08Z"/><path d="M735.75,121.97h-44.55v141.15h44.55c44.11,0,71.11-30.51,71.11-71.24s-25.94-69.91-71.11-69.91ZM734.86,244.33h-21.99v-103.76h21.99c32.56,0,49.83,19.5,49.83,51.3s-17.41,52.46-49.83,52.46Z"/><path d="M939.98,119.04c-40.91,0-71.86,31.49-71.86,73.29s30.96,73.73,71.86,73.73,71.64-32.11,71.64-73.73-30.78-73.29-71.64-73.29ZM939.98,246.55c-29.94,0-49.43-24.03-49.43-54.23s19.5-53.97,49.43-53.97,49.21,23.63,49.21,53.97-19.5,54.23-49.21,54.23Z"/><path d="M1151.49,206.8c21.41-5.11,34.16-20.65,34.16-40.86,0-28.16-19.5-43.97-51.88-43.97h-52.77v17.99h51.43c19.94,0,31.36,9.1,31.36,25.98s-11.42,25.94-31.36,25.94h-51.43v71.24h21.68v-53.08h25.94l35.18,53.08h25.94l-38.24-56.32Z"/><path d="M1322.13,121.97h-23.9l-53.97,141.15h21.72l13.01-35.04h60.98l12.79,35.04h23.01l-53.65-141.15ZM1285.49,210.62l24.16-65.07,23.9,65.07h-48.06Z"/></svg>`;
const SITE_WA_ICON_14 = `<svg class="icon" viewBox="0 0 24 24" style="width:14px;height:14px;color:#fff"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>`;
const SITE_WA_ICON_15 = `<svg class="icon" viewBox="0 0 24 24" style="width:15px;height:15px;color:#fff"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>`;
const SITE_MENU_ICON = `<svg class="icon" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg>`;
const SITE_SYMBOL = `<svg class="logo-sym" viewBox="0 0 585.31 585.31" xmlns="http://www.w3.org/2000/svg" fill="currentColor"><path d="M0,36.63v512.04l48.47-19.64V56.21L0,36.63ZM536.89,56.21v472.83l48.42,19.64V36.63l-48.42,19.58ZM56.27,536.84l-19.64,48.47h512.04l-19.58-48.47H56.27ZM36.63,0l19.64,48.42h472.83L548.68,0H36.63Z"/><path d="M311.64,118.15h-124.49v46.17h124.1c48.47,0,77.87,25.75,77.87,70.07s-29.4,71.19-77.87,71.19h-124.1v171.45h54.81v-125.22h69.68c80.51,0,132.29-42.47,132.29-117.76s-51.78-115.91-132.29-115.91Z"/></svg>`;
const SITE_ICON_INSTAGRAM = `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r=".6" fill="currentColor" stroke="none"/></svg>`;
const SITE_ICON_YOUTUBE = `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10.3 9.3l5 2.7-5 2.7V9.3z" fill="currentColor" stroke="none"/></svg>`;

function siteNavLinks(current, base) {
  const cur = (name) => current === name ? ' class="current"' : '';
  return `
    <a href="${base}index.html"${cur('inicio')}>Início</a>
    <a href="${base}sobre.html"${cur('sobre')}>Sobre</a>
    <a href="${base ? 'index.html' : 'blog/index.html'}"${cur('blog')}>Blog</a>`;
}

function renderHeader(current, base) {
  base = base || '';
  const el = document.getElementById('siteHeader');
  if (!el) return;
  el.outerHTML = `
<header class="site">
  <div class="wrap header-inner">
    <a href="${base}index.html" class="logo-lockup">
      <span class="logo-full">
        ${SITE_WORDMARK}
        <div class="logo-divider"></div>
        <span class="logo-sub">Data SP</span>
      </span>
      ${SITE_SYMBOL}
      <span class="logo-mobile-text">Pandora Data SP</span>
    </a>
    <nav class="site-nav">${siteNavLinks(current, base)}</nav>
    <a href="https://wa.me/5511945240721" target="_blank" class="nav-cta desktop-only">
      ${SITE_WA_ICON_14}
      Falar com Alex
    </a>
    <button class="menu-btn" id="menuBtn" aria-label="Abrir menu">
      ${SITE_MENU_ICON}
    </button>
  </div>
  <div class="mobile-nav" id="mobileNav">${siteNavLinks(current, base)}
    <a href="https://wa.me/5511945240721" target="_blank" class="nav-cta">
      ${SITE_WA_ICON_15}
      Falar com Alex
    </a>
  </div>
</header>`;
}

function renderFooter(base) {
  base = base || '';
  const el = document.getElementById('siteFooter');
  if (!el) return;
  el.outerHTML = `
<footer class="site">
  <div class="wrap footer-grid">
    <div>
      ${SITE_WORDMARK}
      <p class="footer-desc">Ferramenta gratuita de consulta de imóveis vendidos, com dados oficiais da Prefeitura de São Paulo (ITBI).</p>
      <div class="footer-pilar"><img src="${base}img/logo_pandora.png" alt="Logo da Rede Pilar"><span>Parceiro Rede Pilar</span></div>
    </div>
    <div class="footer-col">
      <h4>Navegação</h4>
      <a href="${base}index.html">Início</a>
      <a href="${base}sobre.html">Sobre</a>
      <a href="${base ? 'index.html' : 'blog/index.html'}">Blog</a>
    </div>
    <div class="footer-col">
      <h4>Pandora Homes</h4>
      <div class="line">Alex Fontes</div>
      <div class="line">CRECI 205029-F</div>
      <a href="https://www.pandorahomes.com.br" target="_blank">pandorahomes.com.br</a>
    </div>
    <div class="footer-col">
      <h4>Contato</h4>
      <a href="tel:+5511945240721">(11) 94524-0721</a>
      <a href="mailto:alexccfontes@gmail.com">alexccfontes@gmail.com</a>
      <div class="footer-social">
        <a href="https://instagram.com/homespandora" target="_blank" title="Instagram">${SITE_ICON_INSTAGRAM}</a>
        <a href="https://www.youtube.com/@HomesPandora" target="_blank" title="YouTube">${SITE_ICON_YOUTUBE}</a>
      </div>
    </div>
  </div>
  <div class="wrap footer-bottom">
    <span>© 2026 Pandora Homes</span>
    <span>Dados: Prefeitura de São Paulo (ITBI)</span>
  </div>
</footer>`;
}

function formatPhoneBR(digits) {
  digits = digits.slice(0, 11);
  if (digits.length <= 2) return digits.length ? `(${digits}` : '';
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

function applyPhoneMask(el) {
  if (!el) return;
  el.setAttribute('inputmode', 'tel');
  el.addEventListener('input', () => {
    el.value = formatPhoneBR(el.value.replace(/\D/g, ''));
  });
}

// Mesmo padrão de máscara de moeda usado no Alex OS (js/masks.js: applyBrCurrencyMask)
function applyBrCurrencyMask(el) {
  if (!el) return;
  el.setAttribute('inputmode', 'numeric');
  el.addEventListener('input', () => {
    const raw = el.value.replace(/\D/g, '');
    if (!raw) { el.value = ''; return; }
    const num = parseInt(raw, 10) / 100;
    el.value = 'R$ ' + num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  });
}

function initSiteChrome(current, base) {
  renderHeader(current, base);
  renderFooter(base);
  const menuBtn = document.getElementById('menuBtn');
  const mobileNav = document.getElementById('mobileNav');
  if (menuBtn && mobileNav) {
    menuBtn.addEventListener('click', () => { mobileNav.classList.toggle('open'); });
  }
  applyPhoneMask(document.getElementById('ctaWhats'));
  applyPhoneMask(document.getElementById('expTelefone'));
  applyPhoneMask(document.getElementById('ctaWhatsB'));
  applyBrCurrencyMask(document.getElementById('ctaValorB'));
}
