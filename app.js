// ===================================================================
// Convexa News — app.js
// Frontend: notícias, cotações, indicadores, busca, favoritos, tema
// ===================================================================

// ===== STATE =====
const state = {
  currentPage: 'noticias',
  newsCategory: 'todas',
  stockData: {},
  fiiData: {},
};

const VALID_PAGES = ['noticias', 'acoes', 'fiis', 'etfs', 'internacional', 'cripto', 'indicadores', 'analises'];

// ===== SEGURANÇA: escape de conteúdo vindo de feeds externos =====
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
function safeUrl(u) {
  return /^https?:\/\//i.test(u || '') ? esc(u) : '';
}

// ===== FAVORITOS =====
let favs = new Set();
try { favs = new Set(JSON.parse(localStorage.getItem('convexa_favs') || '[]')); } catch {}

function isFav(tk) { return favs.has(tk); }

function toggleFav(tk) {
  if (favs.has(tk)) favs.delete(tk); else favs.add(tk);
  localStorage.setItem('convexa_favs', JSON.stringify([...favs]));
  refreshCurrentTable();
}

function favBtnHtml(tk) {
  return `<button class="fav-btn ${isFav(tk) ? 'faved' : ''}" title="Favoritar"
    onclick="event.stopPropagation();toggleFav('${esc(tk)}')">${isFav(tk) ? '★' : '☆'}</button>`;
}

// ===== TEMA (claro/escuro) =====
function setTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  localStorage.setItem('convexa_theme', dark ? 'dark' : 'light');
  const btn = document.getElementById('themeBtn');
  if (btn) btn.textContent = dark ? '☀' : '☾';
}
function toggleTheme() {
  setTheme(document.documentElement.dataset.theme !== 'dark');
}
(function initTheme() {
  const saved = localStorage.getItem('convexa_theme');
  const dark = saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(dark);
})();

// ===== CARREGAMENTO DOS JSONs (gerados pelo coletor.py via GitHub Actions) =====
let dadosJson = null;

async function loadDadosJson() {
  try {
    const resp = await fetch('./dados.json?t=' + Date.now());
    dadosJson = await resp.json();
    const all = [
      ...Object.values(dadosJson.stocks || {}),
      ...Object.values(dadosJson.fiis || {}),
      ...Object.values(dadosJson.etfs || {}),
      ...Object.values(dadosJson.us_stocks || {}),
      ...Object.values(dadosJson.crypto || {}),
    ];
    all.forEach(s => {
      state.stockData[s.stock] = s;
      state.fiiData[s.stock] = s;
    });
    updateFreshness();
    return true;
  } catch (e) {
    console.warn('dados.json não encontrado, usando BrAPI como fallback.');
    return false;
  }
}

function updateFreshness() {
  const el = document.getElementById('dataFreshness');
  if (el && dadosJson?.atualizado_em) el.textContent = `Dados atualizados em ${dadosJson.atualizado_em}`;
}

async function loadNoticias() {
  try {
    const resp = await fetch('./noticias.json?t=' + Date.now());
    const data = await resp.json();
    if (data && data.all && data.all.length > 0) {
      renderNewsDynamic(data);
      return;
    }
  } catch (e) {
    console.warn('noticias.json não encontrado, usando dados estáticos.');
  }
  renderNews();
}

async function loadAnalises() {
  try {
    const resp = await fetch('./analises.json?t=' + Date.now());
    const data = await resp.json();
    if (Array.isArray(data) && data.length > 0) {
      renderAnalysesData(data);
      return;
    }
  } catch (e) {
    console.warn('analises.json não encontrado, usando dados estáticos.');
  }
  renderAnalyses();
}

// ===== TEMPO RELATIVO =====
function tempoRelativo(isoOrText) {
  if (!isoOrText) return '';
  if (!/^\d{4}-\d{2}-\d{2}T/.test(isoOrText)) return isoOrText;
  try {
    const pub = new Date(isoOrText);
    const now = new Date();
    const mins = Math.floor((now - pub) / 60000);
    if (mins < 1) return 'agora';
    if (mins < 60) return `${mins} min`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    return `${Math.floor(hrs / 24)}d`;
  } catch { return isoOrText; }
}

// ===== NAVEGAÇÃO + HASH ROUTING =====
function pageFromHash() {
  const h = location.hash.replace(/^#\/?/, '');
  return VALID_PAGES.includes(h) ? h : 'noticias';
}

function switchPage(page) {
  state.currentPage = page;
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  const section = document.getElementById('page-' + page);
  if (section) section.classList.add('active');
  document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.page === page);
  });
  if (location.hash !== '#/' + page) history.replaceState(null, '', '#/' + page);
  if (page === 'indicadores') loadIndicadores();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchPageGated(btn.dataset.page));
});

window.addEventListener('hashchange', () => {
  const p = pageFromHash();
  if (p !== state.currentPage) switchPageGated(p);
});

// ===== RELÓGIO / STATUS DO MERCADO =====
function updateClock() {
  const now = new Date();
  document.getElementById('tickerClock').textContent =
    now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const h = now.getUTCHours() - 3;
  const isOpen = h >= 10 && h < 17 && now.getUTCDay() > 0 && now.getUTCDay() < 6;
  document.getElementById('marketStatus').textContent = isOpen ? 'Aberto' : 'Fechado';
}
setInterval(updateClock, 1000);
updateClock();

// ===== BRAPI (fallback em tempo real para o ticker) =====
let brapiAllStocks = [];
let brapiAllIndexes = [];

async function loadBrapiList() {
  try {
    const resp = await fetch('https://brapi.dev/api/quote/list');
    const data = await resp.json();
    brapiAllStocks = data.stocks || [];
    brapiAllIndexes = data.indexes || [];
    return true;
  } catch (e) {
    console.warn('BrAPI list error:', e);
    return false;
  }
}

function findStock(ticker) {
  return brapiAllStocks.find(s => s.stock === ticker);
}

// ===== TICKER BAR =====
function tickerItemsHtml(items) {
  let html = '';
  for (let rep = 0; rep < 2; rep++) {
    items.forEach(s => {
      if (s.price == null) return;
      const up = (s.change || 0) >= 0;
      const priceStr = s.price > 1000
        ? s.price.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
        : s.price?.toFixed(2);
      html += `<div class="ticker-item">
        <span class="ticker-symbol">${esc(s.symbol)}</span>
        <span class="ticker-price">${priceStr}</span>
        <span class="ticker-change ${up ? 'up' : 'down'}">${up ? '↗' : '↘'}${up ? '+' : ''}${s.change?.toFixed(2)}%</span>
      </div><div class="ticker-divider"></div>`;
    });
  }
  return html;
}

function loadTickerDataFromJson() {
  if (!dadosJson) return false;
  const tickerList = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'WEGE3', 'BBAS3', 'ABEV3', 'SUZB3'];
  const items = [];
  if (dadosJson.indices) {
    Object.values(dadosJson.indices).forEach(idx => items.push({ symbol: idx.stock, price: idx.close, change: idx.change }));
  }
  if (dadosJson.dolar?.close) items.push({ symbol: 'USD/BRL', price: dadosJson.dolar.close, change: dadosJson.dolar.change });
  if (dadosJson.euro?.close) items.push({ symbol: 'EUR/BRL', price: dadosJson.euro.close, change: dadosJson.euro.change });
  const di = diTickerItem();
  if (di) items.push(di);
  if (dadosJson.stocks) {
    tickerList.forEach(t => {
      const s = dadosJson.stocks[t];
      if (s) items.push({ symbol: s.stock, price: s.close, change: s.change });
    });
  }
  if (!items.length) return false;
  document.getElementById('tickerTrack').innerHTML = tickerItemsHtml(items);
  return true;
}

function loadTickerData() {
  if (!brapiAllStocks.length) return;
  const tickerList = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'WEGE3', 'BBAS3', 'ABEV3', 'SUZB3', 'RENT3', 'B3SA3', 'MGLU3', 'LREN3'];
  const items = [];
  const di = diTickerItem();
  if (di) items.push(di);
  tickerList.forEach(t => {
    const s = findStock(t);
    if (s) items.push({ symbol: s.stock, price: s.close, change: s.change });
  });
  const html = tickerItemsHtml(items);
  if (html) document.getElementById('tickerTrack').innerHTML = html;
}

// ===== NEWS (fallback estático) =====
const NEWS_DATA_STATIC = {
  headline: {
    title: 'BNDES vende R$ 3 bilhões em ações da Petrobras e amplia desinvestimentos em maio',
    summary: 'Banco de fomento também vendeu posições em Axia (R$ 500 mi) e Copel (R$ 280 mi). Mercadante afirma que recursos serão direcionados para inovação, IA e transição digital.',
    source: 'InfoMoney', time: '2026-05-29T14:00:00Z', tickers: ['PETR4', 'CPLE3'], url: '',
  },
  featured: [
    { title: 'Bitcoin estabiliza em US$ 77 mil com volatilidade em mínima de 9 meses', summary: 'Mercado cripto aguarda definição sobre tensão EUA-Irã. ETFs de BTC registram saída de US$ 1,26 bi.', source: 'Exame', time: '2026-05-29T12:00:00Z', tickers: ['BTC', 'ETH'], url: '' },
    { title: 'Focus: mercado eleva IPCA 2026 para 5,04% pela 11ª semana consecutiva', summary: 'Expectativa de Selic terminal sobe para 14,75%. Dólar oscila entre R$ 4,99 e R$ 5,05.', source: 'Valor Econômico', time: '2026-05-29T10:30:00Z', tickers: ['ITUB4', 'BBDC4'], url: '' },
  ],
  categories: [
    { id: 'todas', label: 'Todas' },
    { id: 'acoes', label: 'Ações' },
    { id: 'fundos', label: 'FIIs' },
    { id: 'economia', label: 'Economia' },
    { id: 'internacional', label: 'Internacional' },
    { id: 'cripto', label: 'Cripto' },
    { id: 'analise', label: 'Análises' },
  ],
  all: [
    { title: 'BNDES vende R$ 3 bi em Petrobras, R$ 500 mi em Axia e R$ 280 mi em Copel', source: 'Money Times', time: '2026-05-29T14:00:00Z', cat: 'acoes', url: '' },
    { title: 'Ibovespa opera com baixa liquidez; bancos avançam e Petrobras recua', source: 'InfoMoney', time: '2026-05-29T13:30:00Z', cat: 'acoes', url: '' },
    { title: 'Dólar oscila entre R$ 4,99 e R$ 5,05; Focus eleva IPCA para 5,04%', source: 'CNN Brasil', time: '2026-05-29T10:00:00Z', cat: 'economia', url: '' },
  ],
};

let NEWS_DATA = Object.assign({}, NEWS_DATA_STATIC);

function renderNewsDynamic(data) {
  NEWS_DATA = {
    headline: data.headline || NEWS_DATA_STATIC.headline,
    featured: data.featured || [],
    categories: NEWS_DATA_STATIC.categories,
    all: data.all || [],
    atualizado_em: data.atualizado_em || '',
  };
  renderNews();
}

function tickerTagsHtml(tickers) {
  return (tickers || []).map(t => `<span class="ticker-tag">${esc(t)}</span>`).join('');
}

function renderNews() {
  const h = NEWS_DATA.headline;
  if (!h) return;

  const heroTitle = document.getElementById('heroTitle');
  const hUrl = safeUrl(h.url);
  heroTitle.innerHTML = hUrl
    ? `<a class="hero-link" href="${hUrl}" target="_blank" rel="noopener">${esc(h.title)}</a>`
    : esc(h.title);
  document.getElementById('heroSummary').textContent = h.summary || '';
  const tickersHtml = tickerTagsHtml(h.tickers);
  document.getElementById('heroMeta').innerHTML = `
    <span class="hero-source">${esc(h.source)}</span><span>·</span><span>${esc(tempoRelativo(h.time))}</span>
    ${tickersHtml ? `<span>·</span><div class="hero-tickers">${tickersHtml}</div>` : ''}`;

  document.getElementById('featuredCards').innerHTML = (NEWS_DATA.featured || []).map(f => {
    const fUrl = safeUrl(f.url);
    const inner = `
      <div class="featured-meta">
        <span>${esc(f.source)}</span><span>·</span><span>${esc(tempoRelativo(f.time))}</span>
        ${f.exclusive ? '<span class="exclusive-badge">EXCLUSIVO</span>' : ''}
      </div>
      <div class="featured-title">${esc(f.title)}</div>
      <div class="featured-summary">${esc(f.summary || '')}</div>
      ${(f.tickers || []).length ? `<div class="featured-tickers">${tickerTagsHtml(f.tickers)}</div>` : ''}`;
    return `<div class="featured-card">${fUrl ? `<a href="${fUrl}" target="_blank" rel="noopener">${inner}</a>` : inner}</div>`;
  }).join('');

  document.getElementById('catFilters').innerHTML = NEWS_DATA.categories.map(c =>
    `<button class="cat-btn ${c.id === state.newsCategory ? 'active' : ''}" onclick="filterNews('${c.id}')">${esc(c.label)}</button>`
  ).join('');

  renderNewsList();
}

function filterNews(cat) {
  state.newsCategory = cat;
  document.querySelectorAll('.cat-btn').forEach(b =>
    b.classList.toggle('active', b.textContent === NEWS_DATA.categories.find(c => c.id === cat)?.label));
  renderNewsList();
}

function renderNewsList() {
  const items = state.newsCategory === 'todas'
    ? NEWS_DATA.all
    : NEWS_DATA.all.filter(n => n.cat === state.newsCategory);

  if (!items.length) {
    document.getElementById('newsGrid').innerHTML =
      '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-secondary)">Nenhuma notícia disponível ainda. O robô atualiza a cada hora.</div>';
    return;
  }

  document.getElementById('newsGrid').innerHTML = items.map(n => {
    const nUrl = safeUrl(n.url);
    const inner = `
      <div class="news-item-meta">
        <span class="news-item-source">${esc(n.source)}</span>
        <span>·</span>
        <span>⏱ ${esc(tempoRelativo(n.time))}</span>
        ${(n.tickers || []).length ? `<span>·</span>${tickerTagsHtml(n.tickers)}` : ''}
      </div>
      <div class="news-item-title">
        <span>${esc(n.title)}</span>
        <span class="news-arrow">→</span>
      </div>`;
    return `<div class="news-item">${nUrl ? `<a href="${nUrl}" target="_blank" rel="noopener">${inner}</a>` : inner}</div>`;
  }).join('');
}

// ===== LISTAS DE ATIVOS (fallback BrAPI) =====
const BR_TICKERS = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3', 'WEGE3', 'RENT3', 'BBAS3', 'MGLU3', 'SUZB3', 'B3SA3', 'RADL3', 'LREN3', 'AXIA3'];
const FII_TICKERS = ['HGLG11', 'XPLG11', 'KNRI11', 'MXRF11', 'VISC11', 'HGRE11', 'IRDM11', 'XPML11', 'VILG11'];
const US_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA'];
const CRYPTO_TICKERS = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP'];
const ETF_TICKERS = ['BOVA11', 'SMAL11', 'IVVB11', 'HASH11', 'GOLD11', 'DIVO11', 'XFIX11', 'BOVV11', 'NASD11', 'SPXI11', 'MATB11', 'TECK11'];
const CRYPTO_NAMES = { BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana', ADA: 'Cardano', XRP: 'Ripple', BNB: 'BNB', DOGE: 'Dogecoin' };

// ===== FORMATAÇÃO =====
function formatMktCap(v, moeda = 'R$') {
  if (v >= 1e12) return moeda + ' ' + (v / 1e12).toFixed(1) + 'T';
  if (v >= 1e9) return moeda + ' ' + (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return moeda + ' ' + (v / 1e6).toFixed(0) + 'M';
  return v ? v.toString() : '—';
}
function formatVol(v) {
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(0) + 'K';
  return v ? v.toString() : '—';
}
function fmtPreco(close) {
  if (close == null) return '—';
  return close > 1000
    ? close.toLocaleString('pt-BR', { maximumFractionDigits: 2 })
    : close.toFixed(2);
}
function changeHtml(change) {
  const up = (change || 0) >= 0;
  return `<span class="stock-change ${up ? 'up' : 'down'}">${up ? '↗' : '↘'} ${up ? '+' : ''}${change?.toFixed(2) || '0.00'}%</span>`;
}

// ===== SPARKLINE =====
function sparkSvg(spark, trendUp, w = 90, h = 28) {
  if (!spark || spark.length < 2) return '<span class="perf-value">—</span>';
  const min = Math.min(...spark), max = Math.max(...spark);
  const range = max - min || 1;
  const pts = spark.map((v, i) =>
    `${(i / (spark.length - 1) * w).toFixed(1)},${(h - 2 - ((v - min) / range) * (h - 4)).toFixed(1)}`
  ).join(' ');
  const color = trendUp ? 'var(--green)' : 'var(--red)';
  return `<span class="spark-cell"><svg class="spark-svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round"/>
  </svg></span>`;
}

function sparkCell(s) {
  const trendUp = s.perf_12m != null ? s.perf_12m >= 0 : (s.spark ? s.spark[s.spark.length - 1] >= s.spark[0] : true);
  return sparkSvg(s.spark, trendUp);
}

// ===== SETORES =====
const SETOR_PT = {
  'Financial Services': 'Bancos', 'Banking': 'Bancos',
  'Energy': 'Energia', 'Utilities': 'Energia',
  'Basic Materials': 'Mineração',
  'Consumer Cyclical': 'Varejo', 'Consumer Defensive': 'Consumo',
  'Industrials': 'Industrial', 'Healthcare': 'Saúde',
  'Technology': 'Tecnologia', 'Communication Services': 'Telecom',
  'Real Estate': 'Imóveis',
};

const SETOR_COR = {
  'Bancos':     { dot: '#2563eb', bg: 'rgba(37,99,235,0.08)' },
  'Energia':    { dot: '#ea580c', bg: 'rgba(234,88,12,0.08)' },
  'Mineração':  { dot: '#854d0e', bg: 'rgba(133,77,14,0.08)' },
  'Varejo':     { dot: '#7c3aed', bg: 'rgba(124,58,237,0.08)' },
  'Consumo':    { dot: '#0891b2', bg: 'rgba(8,145,178,0.08)' },
  'Industrial': { dot: '#059669', bg: 'rgba(5,150,105,0.08)' },
  'Saúde':      { dot: '#dc2626', bg: 'rgba(220,38,38,0.08)' },
  'Tecnologia': { dot: '#6366f1', bg: 'rgba(99,102,241,0.08)' },
  'Telecom':    { dot: '#0284c7', bg: 'rgba(2,132,199,0.08)' },
  'Imóveis':    { dot: '#16a34a', bg: 'rgba(22,163,74,0.08)' },
};

function traduzirSetor(s) {
  return SETOR_PT[s] || s || 'Outros';
}

// ===== ORDENAÇÃO DE TABELAS =====
const sortState = {};      // tableId -> { key, dir }
const tableRefreshers = {}; // tableId -> fn

function applySort(tableId, arr) {
  const s = sortState[tableId];
  if (!s) return arr;
  return [...arr].sort((a, b) => {
    let va = a[s.key], vb = b[s.key];
    if (typeof va === 'string' || typeof vb === 'string') {
      va = String(va || ''); vb = String(vb || '');
      return s.dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    }
    va = va ?? -Infinity; vb = vb ?? -Infinity;
    return s.dir === 'asc' ? va - vb : vb - va;
  });
}

function setupSorting() {
  document.querySelectorAll('.stock-table th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const tableId = table.querySelector('tbody').id;
      const key = th.dataset.sort;
      const cur = sortState[tableId];
      sortState[tableId] = { key, dir: cur && cur.key === key && cur.dir === 'desc' ? 'asc' : 'desc' };
      table.querySelectorAll('th .sort-arrow').forEach(a => a.remove());
      const arrow = document.createElement('span');
      arrow.className = 'sort-arrow';
      arrow.textContent = sortState[tableId].dir === 'desc' ? '▼' : '▲';
      th.appendChild(arrow);
      (tableRefreshers[tableId] || (() => {}))();
    });
  });
}

function refreshCurrentTable() {
  Object.values(tableRefreshers).forEach(fn => fn());
}

// Retorna lista de ativos de uma categoria: dados.json primeiro, fallback BrAPI
function getAtivos(tickers, categoria) {
  if (dadosJson && dadosJson[categoria] && Object.keys(dadosJson[categoria]).length) {
    return Object.values(dadosJson[categoria]);
  }
  return tickers.map(t => findStock(t)).filter(Boolean);
}

const LOADING_ROW = cols => `<tr><td colspan="${cols}" class="loading-text">Atualizando dados...</td></tr>`;

// ===== CÉLULA DE ATIVO (favorito + ícone + nome) =====
function stockCellHtml(s, iconStyle = '') {
  return `<div class="stock-cell">
    ${favBtnHtml(s.stock)}
    <div class="stock-icon" style="${iconStyle}">${esc((s.stock || '').slice(0, 4))}</div>
    <div class="stock-name-wrap">
      <span class="stock-ticker">${esc(s.stock)}</span>
      <span class="stock-name">${esc(s.name || '')}</span>
    </div>
  </div>`;
}

// ===== PÁGINA: AÇÕES BR =====
let acoesData = [];
let acoesSetorAtivo = 'todas';

function buildSetorBar(data) {
  const contagem = {};
  data.forEach(s => {
    const pt = traduzirSetor(s.sector);
    contagem[pt] = (contagem[pt] || 0) + 1;
  });

  const bar = document.getElementById('setorBar');
  const countEl = document.getElementById('countTodas');
  if (countEl) countEl.textContent = data.length;

  bar.querySelectorAll('[data-setor]:not([data-setor="todas"]):not([data-setor="favoritos"])').forEach(c => c.remove());

  Object.entries(contagem)
    .sort((a, b) => b[1] - a[1])
    .forEach(([setor, qtd]) => {
      const cor = SETOR_COR[setor] || { dot: '#71717a', bg: 'rgba(0,0,0,0.05)' };
      const chip = document.createElement('button');
      chip.className = 'setor-chip' + (acoesSetorAtivo === setor ? ' active' : '');
      chip.dataset.setor = setor;
      chip.onclick = () => filterAcoes(setor);
      chip.innerHTML = `
        <span class="chip-dot" style="background:${cor.dot}"></span>
        ${esc(setor)}
        <span class="chip-count">${qtd}</span>`;
      bar.appendChild(chip);
    });
}

function filterAcoes(setor) {
  acoesSetorAtivo = setor;
  document.querySelectorAll('#setorBar .setor-chip').forEach(c => {
    c.classList.toggle('active', c.dataset.setor === setor);
  });
  renderAcoesTable();
}

function renderAcoesTable() {
  let filtered = acoesSetorAtivo === 'todas'
    ? acoesData
    : acoesSetorAtivo === 'favoritos'
      ? acoesData.filter(s => isFav(s.stock))
      : acoesData.filter(s => traduzirSetor(s.sector) === acoesSetorAtivo);
  filtered = applySort('tbAcoes', filtered);
  document.getElementById('tbAcoes').innerHTML = filtered.length
    ? filtered.map(renderAcoesRow).join('')
    : `<tr><td colspan="7" class="loading-text">${acoesSetorAtivo === 'favoritos' ? 'Clique na ☆ de um ativo para adicioná-lo aos favoritos' : 'Nenhuma ação nesta categoria'}</td></tr>`;
}

function renderAcoesRow(s) {
  const setor_pt = traduzirSetor(s.sector);
  const cor = SETOR_COR[setor_pt] || { dot: '#71717a', bg: 'rgba(0,0,0,0.05)' };
  return `<tr onclick="openBrapiDetail('${esc(s.stock)}')">
    <td>${stockCellHtml(s)}</td>
    <td><span class="stock-price">R$ ${fmtPreco(s.close)}</span></td>
    <td>${changeHtml(s.change)}</td>
    <td>${sparkCell(s)}</td>
    <td><span class="perf-value">${s.volume ? formatVol(s.volume) : '—'}</span></td>
    <td><span class="perf-value">${s.market_cap ? formatMktCap(s.market_cap) : '—'}</span></td>
    <td>
      <span style="display:inline-flex;align-items:center;gap:5px;background:${cor.bg};color:${cor.dot};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">
        <span style="width:5px;height:5px;border-radius:50%;background:${cor.dot};flex-shrink:0;"></span>
        ${esc(setor_pt)}
      </span>
    </td>
  </tr>`;
}

function loadBRStocks() {
  const data = getAtivos(BR_TICKERS, 'stocks');
  data.forEach(s => state.stockData[s.stock] = s);
  acoesData = data;
  buildSetorBar(data);
  renderAcoesTable();
}
tableRefreshers.tbAcoes = renderAcoesTable;

// ===== PÁGINA: FIIs =====
const FII_CAT_MAP = {
  // Galpões Logísticos
  'HGLG11': 'Galpões', 'XPLG11': 'Galpões', 'VILG11': 'Galpões', 'BRCO11': 'Galpões',
  'GLOG11': 'Galpões', 'ALZR11': 'Galpões', 'LVBI11': 'Galpões', 'GGRC11': 'Galpões',
  'PATL11': 'Galpões', 'BTLG11': 'Galpões', 'VGIP11': 'Galpões', 'TRXF11': 'Galpões',
  // Shoppings
  'VISC11': 'Shoppings', 'XPML11': 'Shoppings', 'HSML11': 'Shoppings',
  'BPML11': 'Shoppings', 'ATSA11': 'Shoppings', 'FVPQ11': 'Shoppings',
  // Lajes Corporativas
  'HGRE11': 'Lajes', 'BRCR11': 'Lajes', 'RCRB11': 'Lajes', 'PATC11': 'Lajes',
  'PVBI11': 'Lajes', 'VINO11': 'Lajes', 'JSRE11': 'Lajes', 'TGAR11': 'Lajes',
  // Papel / CRI
  'MXRF11': 'Papel', 'IRDM11': 'Papel', 'KNCR11': 'Papel', 'KNHY11': 'Papel',
  'MCCI11': 'Papel', 'VRTA11': 'Papel', 'HABT11': 'Papel', 'RECR11': 'Papel',
  'VGIR11': 'Papel', 'CPTS11': 'Papel', 'KNIP11': 'Papel', 'RBRR11': 'Papel',
  'OUJP11': 'Papel', 'HCTR11': 'Papel',
  // Fundo de Fundos
  'BTHF11': 'Fundo de Fundos', 'HFOF11': 'Fundo de Fundos', 'TFOF11': 'Fundo de Fundos',
  // Residencial
  'BLMG11': 'Residencial', 'RBVA11': 'Residencial', 'RZAK11': 'Residencial',
  // Diversificado / Híbrido
  'KNRI11': 'Diversificado', 'HGPO11': 'Diversificado', 'BTRA11': 'Diversificado',
  'RBRP11': 'Diversificado', 'VVPR11': 'Diversificado',
};

const FII_CAT_COR = {
  'Galpões':         { dot: '#059669', bg: 'rgba(5,150,105,0.09)' },
  'Shoppings':       { dot: '#7c3aed', bg: 'rgba(124,58,237,0.09)' },
  'Lajes':           { dot: '#2563eb', bg: 'rgba(37,99,235,0.09)' },
  'Papel':           { dot: '#ea580c', bg: 'rgba(234,88,12,0.09)' },
  'Fundo de Fundos': { dot: '#71717a', bg: 'rgba(113,113,122,0.09)' },
  'Diversificado':   { dot: '#0891b2', bg: 'rgba(8,145,178,0.09)' },
  'Residencial':     { dot: '#db2777', bg: 'rgba(219,39,119,0.09)' },
};

let fiisData = [];
let fiisCategoria = 'todas';

function getFiiCat(ticker) {
  return FII_CAT_MAP[ticker] || 'Outros';
}

function buildFiiBar(data) {
  const contagem = {};
  data.forEach(s => {
    const cat = getFiiCat(s.stock);
    contagem[cat] = (contagem[cat] || 0) + 1;
  });

  const bar = document.getElementById('fiiBar');
  const countEl = document.getElementById('countFiiTodas');
  if (countEl) countEl.textContent = data.length;

  bar.querySelectorAll('[data-cat]:not([data-cat="todas"]):not([data-cat="favoritos"])').forEach(c => c.remove());

  Object.entries(contagem)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cat, qtd]) => {
      const cor = FII_CAT_COR[cat] || { dot: '#71717a', bg: 'rgba(0,0,0,0.05)' };
      const chip = document.createElement('button');
      chip.className = 'setor-chip' + (fiisCategoria === cat ? ' active' : '');
      chip.dataset.cat = cat;
      chip.onclick = () => filterFiis(cat);
      chip.innerHTML = `
        <span class="chip-dot" style="background:${cor.dot}"></span>
        ${esc(cat)}
        <span class="chip-count">${qtd}</span>`;
      bar.appendChild(chip);
    });
}

function filterFiis(cat) {
  fiisCategoria = cat;
  document.querySelectorAll('#fiiBar .setor-chip').forEach(c => {
    c.classList.toggle('active', c.dataset.cat === cat);
  });
  renderFiisTable();
}

function renderFiisTable() {
  let filtered = fiisCategoria === 'todas'
    ? fiisData
    : fiisCategoria === 'favoritos'
      ? fiisData.filter(s => isFav(s.stock))
      : fiisData.filter(s => getFiiCat(s.stock) === fiisCategoria);
  filtered = applySort('tbFiis', filtered);
  document.getElementById('tbFiis').innerHTML = filtered.length
    ? filtered.map(renderFiiRow).join('')
    : `<tr><td colspan="7" class="loading-text">${fiisCategoria === 'favoritos' ? 'Clique na ☆ de um FII para adicioná-lo aos favoritos' : 'Nenhum FII nesta categoria'}</td></tr>`;
}

function renderFiiRow(s) {
  const cat = getFiiCat(s.stock);
  const cor = FII_CAT_COR[cat] || { dot: '#71717a', bg: 'rgba(0,0,0,0.05)' };
  return `<tr onclick="openBrapiDetail('${esc(s.stock)}')">
    <td>${stockCellHtml(s, 'background:#e8f4ff;color:#2563eb;')}</td>
    <td><span class="stock-price">R$ ${fmtPreco(s.close)}</span></td>
    <td>${changeHtml(s.change)}</td>
    <td><span class="perf-value" style="font-weight:700;${s.dy != null ? 'color:var(--green)' : ''}">${s.dy != null ? s.dy.toFixed(2) + '%' : '—'}</span></td>
    <td><span class="perf-value">${s.pvp != null ? s.pvp.toFixed(2) : '—'}</span></td>
    <td>${sparkCell(s)}</td>
    <td>
      <span style="display:inline-flex;align-items:center;gap:5px;background:${cor.bg};color:${cor.dot};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">
        <span style="width:5px;height:5px;border-radius:50%;background:${cor.dot};flex-shrink:0;"></span>
        ${esc(cat)}
      </span>
    </td>
  </tr>`;
}

function loadFIIs() {
  const data = getAtivos(FII_TICKERS, 'fiis');
  data.forEach(s => { state.stockData[s.stock] = s; state.fiiData[s.stock] = s; });
  fiisData = data;
  buildFiiBar(data);
  renderFiisTable();
}
tableRefreshers.tbFiis = renderFiisTable;

// ===== PÁGINA: INTERNACIONAL =====
let usData = [];
function renderUsTable() {
  const data = applySort('tbGlobal', usData);
  document.getElementById('tbGlobal').innerHTML = data.length
    ? data.map(s => `<tr onclick="openBrapiDetail('${esc(s.stock)}')">
        <td>${stockCellHtml(s)}</td>
        <td><span class="stock-price">US$ ${fmtPreco(s.close)}</span></td>
        <td>${changeHtml(s.change)}</td>
        <td>${sparkCell(s)}</td>
        <td><span class="perf-value">${s.volume ? formatVol(s.volume) : '—'}</span></td>
        <td><span class="perf-value">${s.market_cap ? formatMktCap(s.market_cap, 'US$') : '—'}</span></td>
      </tr>`).join('')
    : LOADING_ROW(6);
}
function loadUSStocks() {
  usData = getAtivos(US_TICKERS, 'us_stocks');
  usData.forEach(s => state.stockData[s.stock] = s);
  renderUsTable();
}
tableRefreshers.tbGlobal = renderUsTable;

// ===== PÁGINA: CRIPTO =====
let cryptoData = [];
function renderCryptoTable() {
  const data = applySort('tbCripto', cryptoData);
  document.getElementById('tbCripto').innerHTML = data.length
    ? data.map(s => {
        const comNome = { ...s, name: CRYPTO_NAMES[s.stock] || s.name || '' };
        const up1m = (s.perf_1m || 0) >= 0;
        return `<tr onclick="openBrapiDetail('${esc(s.stock)}')">
          <td>${stockCellHtml(comNome, 'background:#fef3c7;color:#b45309;')}</td>
          <td><span class="stock-price">US$ ${fmtPreco(s.close)}</span></td>
          <td>${changeHtml(s.change)}</td>
          <td><span class="perf-value ${up1m ? 'up' : 'down'}">${s.perf_1m != null ? (up1m ? '+' : '') + s.perf_1m.toFixed(1) + '%' : '—'}</span></td>
          <td>${sparkCell(s)}</td>
          <td><span class="perf-value">${s.volume ? formatVol(s.volume) : '—'}</span></td>
        </tr>`;
      }).join('')
    : LOADING_ROW(6);
}
function loadCrypto() {
  cryptoData = getAtivos(CRYPTO_TICKERS, 'crypto');
  cryptoData.forEach(s => state.stockData[s.stock] = s);
  renderCryptoTable();
}
tableRefreshers.tbCripto = renderCryptoTable;

// ===== PÁGINA: ETFs =====
let etfsData = [];
function renderEtfsTable() {
  const data = applySort('tbEtfs', etfsData);
  document.getElementById('tbEtfs').innerHTML = data.length
    ? data.map(s => `<tr onclick="openBrapiDetail('${esc(s.stock)}')">
        <td>${stockCellHtml(s, 'background:#f0fdf4;color:#16a34a;')}</td>
        <td><span class="stock-price">R$ ${fmtPreco(s.close)}</span></td>
        <td>${changeHtml(s.change)}</td>
        <td>${sparkCell(s)}</td>
        <td><span class="perf-value">${s.volume ? formatVol(s.volume) : '—'}</span></td>
        <td><span class="perf-value">${s.market_cap ? formatMktCap(s.market_cap) : '—'}</span></td>
      </tr>`).join('')
    : LOADING_ROW(6);
}
function loadETFs() {
  etfsData = getAtivos(ETF_TICKERS, 'etfs');
  etfsData.forEach(s => state.stockData[s.stock] = s);
  renderEtfsTable();
}
tableRefreshers.tbEtfs = renderEtfsTable;

// ===== DI FUTURO (B3, tempo real) =====
let diFuturoCache = [];
const MES_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

function labelVencDI(venc) {
  const [ano, mes] = venc.split('-');
  return MES_PT[parseInt(mes, 10) - 1] + '/' + ano.slice(2);
}

async function fetchDIFuturo() {
  try {
    const resp = await fetch('https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1');
    const data = await resp.json();
    const contratos = (data.Scty || []).map(s => {
      const qtn = s.SctyQtn || {};
      const summ = s.asset?.AsstSummry || {};
      return {
        symb: s.symb || '',
        venc: summ.mtrtyCode || '',
        taxa: qtn.curPrc ?? qtn.prvsDayAdjstmntPric,
        ant: qtn.prvsDayAdjstmntPric ?? null,
        contratos: summ.opnCtrcts || 0,
      };
    }).filter(c => c.taxa && c.venc);
    // Curto prazo: os 2 vencimentos mais próximos com alta liquidez (melhor proxy do CDI)
    // Longo prazo: contratos de janeiro (DI1F), os benchmarks da curva
    contratos.sort((a, b) => a.venc.localeCompare(b.venc));
    const curtos = contratos.filter(c => !c.symb.startsWith('DI1F') && c.contratos >= 1000000).slice(0, 2);
    const jans = contratos.filter(c => c.symb.startsWith('DI1F')).slice(0, 6);
    const sel = [...curtos, ...jans];
    sel.sort((a, b) => a.venc.localeCompare(b.venc));
    diFuturoCache = sel.slice(0, 8);
    return diFuturoCache.length > 0;
  } catch (e) {
    console.warn('DI futuro B3:', e);
    return false;
  }
}

function renderDIFuturo() {
  const grid = document.getElementById('indGridDI');
  if (!grid) return;
  const src = diFuturoCache.length ? diFuturoCache : (dadosJson?.di_futuro || []);
  if (!src.length) {
    grid.innerHTML = '<div class="loading-text">Sem dados da B3 no momento</div>';
    return;
  }
  grid.innerHTML = src.map(c => {
    const varPp = c.ant != null ? c.taxa - c.ant : null;
    const up = (varPp || 0) >= 0;
    const sub = varPp != null
      ? `${up ? '▲' : '▼'} ${up ? '+' : ''}${varPp.toFixed(2).replace('.', ',')} p.p. hoje · taxa anualizada`
      : 'taxa anualizada do contrato';
    return indCard('DI ' + labelVencDI(c.venc), c.taxa.toFixed(2).replace('.', ',') + '% <span style="font-size:13px;font-weight:600;color:var(--text-secondary)">a.a.</span>', sub, up ? 'up' : 'down');
  }).join('');
}

async function loadDIFuturo() {
  await fetchDIFuturo();
  renderDIFuturo();
}

function diTickerItem() {
  const src = diFuturoCache.length ? diFuturoCache : (dadosJson?.di_futuro || []);
  const c = src[0];
  if (!c) return null;
  return { symbol: 'DI ' + labelVencDI(c.venc).toUpperCase(), price: c.taxa, change: c.ant != null ? c.taxa - c.ant : null };
}

// ===== PÁGINA: INDICADORES =====
let indicadoresCarregado = false;

async function fetchSgs(codigo, n = 1) {
  const resp = await fetch(`https://api.bcb.gov.br/dados/serie/bcdata.sgs.${codigo}/dados/ultimos/${n}?formato=json`);
  return resp.json();
}

function acumulado12m(serie) {
  // série mensal em % a.m. -> acumulado composto em %
  const fator = serie.reduce((acc, item) => acc * (1 + parseFloat(item.valor) / 100), 1);
  return (fator - 1) * 100;
}

function indCard(label, value, sub, subClass = '') {
  return `<div class="ind-card">
    <div class="ind-label">${label}</div>
    <div class="ind-value">${value}</div>
    ${sub ? `<div class="ind-sub ${subClass}">${sub}</div>` : ''}
  </div>`;
}

function indCardVar(label, value, change) {
  const up = (change || 0) >= 0;
  const sub = change != null ? `${up ? '▲' : '▼'} ${up ? '+' : ''}${change.toFixed(2)}% hoje` : '';
  return indCard(label, value, sub, up ? 'up' : 'down');
}

function renderIndicadoresMercados() {
  const grid = document.getElementById('indGridMercados');
  if (!grid || !dadosJson) return;
  const cards = [];
  const idx = dadosJson.indices || {};
  const fmt = v => v != null ? v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : '—';

  if (idx.IBOV) cards.push(indCardVar('🇧🇷 Ibovespa', fmt(idx.IBOV.close) + ' pts', idx.IBOV.change));
  if (idx.SP500) cards.push(indCardVar('🇺🇸 S&P 500', fmt(idx.SP500.close) + ' pts', idx.SP500.change));
  if (idx.NASDAQ) cards.push(indCardVar('🇺🇸 Nasdaq', fmt(idx.NASDAQ.close) + ' pts', idx.NASDAQ.change));
  if (idx.DOW) cards.push(indCardVar('🇺🇸 Dow Jones', fmt(idx.DOW.close) + ' pts', idx.DOW.change));
  if (dadosJson.dolar?.close) cards.push(indCardVar('💵 Dólar', 'R$ ' + dadosJson.dolar.close.toFixed(4), dadosJson.dolar.change));
  if (dadosJson.euro?.close) cards.push(indCardVar('💶 Euro', 'R$ ' + dadosJson.euro.close.toFixed(4), dadosJson.euro.change));
  const btc = dadosJson.crypto?.BTC;
  if (btc) cards.push(indCardVar('₿ Bitcoin', 'US$ ' + fmt(btc.close), btc.change));

  grid.innerHTML = cards.join('') || '<div class="loading-text">Sem dados no momento</div>';

  renderCommodities();
}

const COMMODITY_ICONE = {
  OURO: '🥇', PRATA: '🥈', BRENT: '🛢️', WTI: '🛢️', GAS: '🔥',
  COBRE: '🔶', MINERIO: '⛏️', SOJA: '🌱', MILHO: '🌽', CAFE: '☕', ACUCAR: '🍬',
};

function renderCommodities() {
  const grid = document.getElementById('indGridCommodities');
  if (!grid) return;
  const coms = dadosJson?.commodities || {};
  const cards = Object.entries(coms).map(([chave, c]) => {
    const up = (c.change || 0) >= 0;
    const valor = c.close >= 1000
      ? c.close.toLocaleString('pt-BR', { maximumFractionDigits: 2 })
      : c.close.toFixed(2).replace('.', ',');
    const sub = `${up ? '▲' : '▼'} ${up ? '+' : ''}${(c.change || 0).toFixed(2)}% hoje · ${c.unidade || ''}`;
    return indCard((COMMODITY_ICONE[chave] || '') + ' ' + esc(c.stock), valor, sub, up ? 'up' : 'down');
  });
  grid.innerHTML = cards.join('') || '<div class="loading-text">Sem dados no momento</div>';
}

async function loadIndicadores() {
  renderIndicadoresMercados();
  loadDIFuturo(); // tempo real, atualiza a cada visita e a cada 2 min
  if (indicadoresCarregado) return;

  const grid = document.getElementById('indGridJuros');
  if (!grid) return;
  grid.innerHTML = '<div class="loading-text">Consultando Banco Central...</div>';

  const cards = [];
  // Selic meta (432) e CDI anualizado (4389): % a.a. | IPCA (433) e IGP-M (189): % a.m.
  const consultas = [
    { cod: 432, n: 1, render: d => indCard('Taxa Selic', parseFloat(d[0].valor).toFixed(2).replace('.', ',') + '%', 'meta anual · ' + d[0].data) },
    { cod: 4389, n: 1, render: d => indCard('CDI', parseFloat(d[0].valor).toFixed(2).replace('.', ',') + '%', 'taxa anualizada') },
    { cod: 433, n: 12, render: d => indCard('IPCA (12 meses)', acumulado12m(d).toFixed(2).replace('.', ',') + '%', 'inflação oficial acumulada') },
    { cod: 189, n: 12, render: d => indCard('IGP-M (12 meses)', acumulado12m(d).toFixed(2).replace('.', ',') + '%', 'índice de contratos/aluguel') },
  ];

  const resultados = await Promise.allSettled(consultas.map(c => fetchSgs(c.cod, c.n)));
  resultados.forEach((r, i) => {
    if (r.status === 'fulfilled' && Array.isArray(r.value) && r.value.length) {
      try { cards.push(consultas[i].render(r.value)); } catch {}
    }
  });

  grid.innerHTML = cards.length
    ? cards.join('')
    : '<div class="loading-text">Não foi possível consultar o Banco Central agora. Tente novamente em instantes.</div>';
  indicadoresCarregado = cards.length > 0;
}

// ===== BUSCA GLOBAL =====
let searchSelected = 0;

function openSearch() {
  document.getElementById('searchOverlay').classList.add('open');
  const input = document.getElementById('searchInput');
  input.value = '';
  renderSearchResults('');
  setTimeout(() => input.focus(), 50);
}

function closeSearch() {
  document.getElementById('searchOverlay').classList.remove('open');
}

function searchAssets(q) {
  const todos = Object.values(state.stockData);
  const ql = q.toUpperCase();
  return todos
    .filter(s => s.stock?.toUpperCase().includes(ql) || (s.name || '').toUpperCase().includes(ql))
    .sort((a, b) => {
      const aPre = a.stock.toUpperCase().startsWith(ql) ? 0 : 1;
      const bPre = b.stock.toUpperCase().startsWith(ql) ? 0 : 1;
      return aPre - bPre || (b.market_cap || 0) - (a.market_cap || 0);
    })
    .slice(0, 8);
}

function renderSearchResults(q) {
  const box = document.getElementById('searchResults');
  searchSelected = 0;
  if (!q || q.length < 2) {
    box.innerHTML = '<div class="search-empty">Digite o ticker ou nome de um ativo — ex.: PETR4, Vale, HGLG11, Bitcoin</div>';
    return;
  }

  const ativos = searchAssets(q);
  const noticias = (NEWS_DATA.all || [])
    .filter(n => n.title.toUpperCase().includes(q.toUpperCase()))
    .slice(0, 4);

  let html = ativos.map((s, i) => {
    const tipoLabel = { stock: 'Ação BR', fii: 'FII', etf: 'ETF', us: 'Ação EUA', crypto: 'Cripto' }[s.type] || 'Ativo';
    const moeda = (s.type === 'us' || s.type === 'crypto') ? 'US$' : 'R$';
    return `<div class="search-result ${i === 0 ? 'selected' : ''}" data-action="asset" data-tk="${esc(s.stock)}">
      <div class="sr-icon">${esc((s.stock || '').slice(0, 4))}</div>
      <div class="sr-main">
        <div class="sr-title">${esc(s.stock)} <span style="font-weight:400;color:var(--text-secondary)">· ${esc(s.name || tipoLabel)}</span></div>
        <div class="sr-sub">${tipoLabel}</div>
      </div>
      <div class="sr-price">${moeda} ${fmtPreco(s.close)} ${changeHtml(s.change)}</div>
    </div>`;
  }).join('');

  html += noticias.map(n => {
    const nUrl = safeUrl(n.url);
    return `<div class="search-result" data-action="news" data-url="${nUrl}">
      <div class="sr-icon">📰</div>
      <div class="sr-main">
        <div class="sr-title">${esc(n.title)}</div>
        <div class="sr-sub">${esc(n.source)} · ${esc(tempoRelativo(n.time))}</div>
      </div>
    </div>`;
  }).join('');

  box.innerHTML = html || '<div class="search-empty">Nenhum resultado para sua busca</div>';

  box.querySelectorAll('.search-result').forEach(el => {
    el.addEventListener('click', () => activateSearchResult(el));
  });
}

function activateSearchResult(el) {
  if (el.dataset.action === 'asset') {
    closeSearch();
    openBrapiDetail(el.dataset.tk);
  } else if (el.dataset.action === 'news' && el.dataset.url) {
    window.open(el.dataset.url, '_blank', 'noopener');
  }
}

function setupSearch() {
  const input = document.getElementById('searchInput');
  input.addEventListener('input', () => renderSearchResults(input.value.trim()));
  input.addEventListener('keydown', e => {
    const results = [...document.querySelectorAll('#searchResults .search-result')];
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!results.length) return;
      searchSelected = (searchSelected + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length;
      results.forEach((r, i) => r.classList.toggle('selected', i === searchSelected));
      results[searchSelected].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      if (results[searchSelected]) activateSearchResult(results[searchSelected]);
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeSearch();
    if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
      e.preventDefault();
      openSearch();
    }
  });
}

// ===== MODAL DE DETALHE =====
function detailChartSvg(s, w = 456, h = 110) {
  const spark = s.spark;
  if (!spark || spark.length < 2) return '';
  const min = Math.min(...spark), max = Math.max(...spark);
  const range = max - min || 1;
  const pts = spark.map((v, i) => [
    (i / (spark.length - 1) * w),
    (h - 6 - ((v - min) / range) * (h - 12)),
  ]);
  const line = pts.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const area = `0,${h} ` + line + ` ${w},${h}`;
  const trendUp = spark[spark.length - 1] >= spark[0];
  const color = trendUp ? 'var(--green)' : 'var(--red)';
  const gid = 'g' + s.stock.replace(/[^A-Za-z0-9]/g, '');
  return `
    <div style="margin:20px 0 4px;">
      <div class="detail-perf-title">Últimos 12 meses</div>
      <svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="display:block">
        <defs>
          <linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <polygon points="${area}" fill="url(#${gid})"/>
        <polyline points="${line}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>
      </svg>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);font-family:'SF Mono','Consolas',monospace;">
        <span>min ${fmtPreco(min)}</span><span>max ${fmtPreco(max)}</span>
      </div>
    </div>`;
}

function relatedNewsHtml(ticker) {
  const noticias = (NEWS_DATA.all || []).filter(n => (n.tickers || []).includes(ticker)).slice(0, 3);
  if (!noticias.length) return '';
  return `<div class="detail-news">
    <div class="detail-news-title">Notícias sobre ${esc(ticker)}</div>
    ${noticias.map(n => {
      const nUrl = safeUrl(n.url);
      return `<a href="${nUrl || '#'}" target="_blank" rel="noopener">
        ${esc(n.title)}
        <div class="dn-meta">${esc(n.source)} · ${esc(tempoRelativo(n.time))}</div>
      </a>`;
    }).join('')}
  </div>`;
}

function openBrapiDetail(ticker) {
  const s = state.stockData[ticker] || state.fiiData[ticker];
  if (!s) return;
  const up = (s.change || 0) >= 0;
  const currency = (s.type === 'us' || s.type === 'crypto') ? 'US$' : 'R$';
  const priceStr = fmtPreco(s.close);

  const nomeCompleto = (s.name && s.name !== s.stock) ? s.name : (CRYPTO_NAMES[s.stock] || s.stock);
  const subtitulo = nomeCompleto !== s.stock ? s.stock : '';
  const setorPt = traduzirSetor(s.sector) || s.sector || '—';
  const tipoLabel = { stock: 'Ação BR', fii: 'FII', etf: 'ETF', us: 'Ação EUA', crypto: 'Cripto' }[s.type] || s.type || '—';
  const desc = gerarDescricao(s);

  const periodos = [
    { label: '1 dia', val: s.change },
    { label: '1 mês', val: s.perf_1m },
    { label: '3 meses', val: s.perf_3m },
    { label: '6 meses', val: s.perf_6m },
    { label: '12 meses', val: s.perf_12m },
  ];
  const maxAbs = Math.max(...periodos.map(p => Math.abs(p.val || 0)), 1);

  function perfRow(p) {
    if (p.val == null) return '';
    const isUp = p.val >= 0;
    const width = Math.min((Math.abs(p.val) / maxAbs) * 100, 100).toFixed(1);
    const color = isUp ? 'var(--green)' : 'var(--red)';
    return `
      <div class="detail-perf-row">
        <span class="detail-perf-label">${p.label}</span>
        <div class="detail-perf-bar-wrap">
          <div class="detail-perf-bar" style="width:${width}%;background:${color}"></div>
        </div>
        <span class="detail-perf-pct ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${p.val.toFixed(2)}%</span>
      </div>`;
  }

  // Estatísticas: FIIs ganham DY e P/VP em destaque
  const stats = [];
  if (s.type === 'fii') {
    stats.push(['DY (12m)', s.dy != null ? s.dy.toFixed(2) + '%' : '—']);
    stats.push(['P/VP', s.pvp != null ? s.pvp.toFixed(2) : '—']);
  }
  stats.push(['Volume', s.volume ? formatVol(s.volume) : '—']);
  stats.push(['Valor de Mercado', s.market_cap ? formatMktCap(s.market_cap, currency) : '—']);
  if (s.type !== 'fii') {
    stats.push(['Setor', esc(setorPt)]);
    stats.push(['Tipo', tipoLabel]);
  }

  const modal = document.getElementById('detailModal');
  modal.innerHTML = `
    <button class="detail-close" onclick="closeDetail()">✕</button>
    <button class="detail-fav ${isFav(s.stock) ? 'faved' : ''}" title="Favoritar"
      onclick="toggleFav('${esc(s.stock)}');this.classList.toggle('faved');this.textContent=this.classList.contains('faved')?'★':'☆'">${isFav(s.stock) ? '★' : '☆'}</button>

    <div class="detail-header">
      <div class="detail-icon">${esc((s.stock || '').slice(0, 4))}</div>
      <div class="detail-title-wrap">
        <h2>${esc(nomeCompleto)}</h2>
        ${subtitulo ? `<p>${esc(subtitulo)}</p>` : ''}
      </div>
    </div>

    <div class="detail-price-row">
      <span class="detail-price">${currency} ${priceStr}</span>
      <span class="detail-change" style="color:${up ? 'var(--green)' : 'var(--red)'}">
        ${up ? '+' : ''}${s.change?.toFixed(2)}%
      </span>
    </div>

    ${detailChartSvg(s)}

    <div class="detail-perf-section">
      <div class="detail-perf-title">Valorização</div>
      ${periodos.map(perfRow).join('')}
    </div>

    <div class="detail-grid">
      ${stats.map(([label, valor]) => `
        <div class="detail-stat">
          <div class="detail-stat-label">${label}</div>
          <div class="detail-stat-value" style="font-size:${String(valor).length > 8 ? '14' : '18'}px;">${valor}</div>
        </div>`).join('')}
    </div>

    <div class="detail-desc">${esc(desc)}</div>
    ${relatedNewsHtml(s.stock)}`;

  document.getElementById('detailOverlay').classList.add('open');
}

function gerarDescricao(s) {
  const setor = traduzirSetor(s.sector) || '';
  if (s.type === 'fii') {
    const cat = getFiiCat(s.stock);
    const descs = {
      'Galpões': 'Fundo imobiliário focado em galpões logísticos e industriais, com renda proveniente de contratos de locação de longo prazo.',
      'Shoppings': 'Fundo imobiliário com participação em shopping centers, com receita atrelada ao fluxo de vendas dos lojistas.',
      'Lajes': 'Fundo imobiliário de lajes corporativas, com imóveis comerciais de alto padrão locados para grandes empresas.',
      'Papel': 'Fundo imobiliário de recebíveis (CRI/LCI/LCA), com rendimentos indexados ao CDI ou IPCA.',
      'Fundo de Fundos': 'Fundo que investe em cotas de outros FIIs, oferecendo diversificação com gestão ativa da carteira.',
      'Residencial': 'Fundo imobiliário com foco em empreendimentos residenciais para renda.',
      'Diversificado': 'Fundo imobiliário com portfólio diversificado entre diferentes segmentos do mercado imobiliário.',
    };
    return descs[cat] || 'Fundo de Investimento Imobiliário listado na B3.';
  }
  if (s.type === 'crypto') {
    const cryptoDescs = {
      'BTC': 'Bitcoin é a primeira criptomoeda descentralizada, criada em 2009. Funciona como reserva de valor digital e meio de troca sem intermediários.',
      'ETH': 'Ethereum é uma plataforma blockchain com contratos inteligentes. Seu token nativo, o Ether, alimenta aplicações descentralizadas (DApps).',
      'SOL': 'Solana é uma blockchain de alta velocidade e baixo custo, voltada para DeFi, NFTs e aplicações Web3.',
      'XRP': 'XRP é o token da Ripple, usado para transferências internacionais rápidas e de baixo custo entre instituições financeiras.',
      'BNB': 'BNB é o token nativo da Binance, utilizado para pagar taxas na exchange e em serviços do ecossistema Binance.',
      'ADA': 'Cardano é uma blockchain com foco em segurança e sustentabilidade, desenvolvida com base em pesquisa acadêmica.',
      'DOGE': 'Dogecoin começou como meme mas se tornou uma das criptomoedas mais populares, com forte comunidade e baixo valor unitário.',
    };
    return cryptoDescs[s.stock] || 'Criptoativo negociado globalmente, sujeito a alta volatilidade.';
  }
  if (s.type === 'etf') {
    if (s.stock === 'BOVA11') return 'ETF que replica o Ibovespa, o principal índice da Bolsa brasileira, com as ações de maior liquidez e volume.';
    if (s.stock === 'SMAL11') return 'ETF de small caps brasileiras, empresas de menor capitalização com potencial de crescimento acelerado.';
    if (s.stock === 'IVVB11') return 'ETF que replica o S&P 500, índice com as 500 maiores empresas americanas, negociado em reais na B3.';
    if (s.stock === 'HASH11') return 'ETF de criptoativos, expondo o investidor ao desempenho de Bitcoin, Ethereum e outras criptomoedas.';
    if (s.stock === 'GOLD11') return 'ETF lastreado em ouro físico, permitindo exposição ao metal precioso sem precisar comprá-lo diretamente.';
    if (s.stock === 'NASD11') return 'ETF que replica o índice Nasdaq 100, com as maiores empresas de tecnologia dos Estados Unidos.';
    if (s.stock === 'IMAB11') return 'ETF de renda fixa atrelado ao IMA-B, índice de títulos públicos indexados ao IPCA (NTN-B).';
    return `ETF (fundo de índice) negociado na B3${setor ? ', com exposição a ' + setor.toLowerCase() : ''}.`;
  }
  if (s.type === 'us') {
    const usDescs = {
      'AAPL': 'Apple é a maior empresa do mundo por valor de mercado, conhecida por iPhone, Mac e serviços digitais como App Store e iCloud.',
      'MSFT': 'Microsoft domina o mercado de software corporativo, cloud (Azure) e produtividade (Office 365), além de ser dona do LinkedIn e GitHub.',
      'NVDA': 'NVIDIA lidera o mercado de GPUs, componente essencial para inteligência artificial, data centers e jogos digitais.',
      'GOOGL': 'Alphabet (Google) controla o maior mecanismo de busca do mundo, YouTube, Android e uma das principais plataformas de publicidade digital.',
      'AMZN': 'Amazon é líder global em e-commerce e computação em nuvem (AWS), além de atuar em streaming (Prime Video) e logística.',
      'META': 'Meta Platforms opera Facebook, Instagram e WhatsApp, as maiores redes sociais do mundo, com bilhões de usuários ativos.',
      'TSLA': 'Tesla é pioneira em veículos elétricos e energia limpa, com negócios em baterias, software automotivo e inteligência artificial.',
      'JPM': 'JPMorgan Chase é o maior banco americano por ativos, com atuação em banco de investimento, crédito e gestão de patrimônio.',
      'V': 'Visa opera a maior rede de pagamentos eletrônicos do mundo, processando trilhões de dólares em transações anualmente.',
      'MA': 'Mastercard é uma das maiores redes de pagamento global, conectando consumidores, bancos e comerciantes em mais de 200 países.',
      'BRK-B': 'Berkshire Hathaway é o conglomerado de Warren Buffett, com participações em seguros, ferrovias, energia e ações de grandes empresas.',
      'LLY': 'Eli Lilly é uma das maiores farmacêuticas do mundo, com destaque para medicamentos para diabetes e obesidade.',
      'UNH': 'UnitedHealth é o maior plano de saúde dos EUA, com operações em seguros, gestão de benefícios e serviços de saúde.',
      'XOM': 'ExxonMobil é uma das maiores petroleiras do mundo, com atuação em exploração, refino e distribuição de combustíveis.',
      'WMT': 'Walmart é o maior varejista do mundo, com mais de 10.000 lojas em 24 países e liderança crescente no e-commerce.',
    };
    return usDescs[s.stock] || `Empresa americana listada em bolsa${setor ? ', setor de ' + setor.toLowerCase() : ''}.`;
  }
  // Ação BR
  const setorDescs = {
    'Energia': 'empresa do setor de petróleo, gás e energia, com operações de exploração, produção e/ou distribuição de combustíveis',
    'Mineração': 'empresa do setor de mineração e siderurgia, com produção de minério de ferro, aço ou outros metais',
    'Bancos': 'instituição financeira do setor bancário, com serviços de crédito, investimento e soluções financeiras',
    'Financeiro': 'empresa do setor financeiro, atuando em seguros, pagamentos ou serviços de capital',
    'Telecom': 'empresa de telecomunicações, oferecendo serviços de telefonia, internet e dados',
    'Varejo': 'empresa do setor varejista, com lojas físicas e/ou e-commerce voltado ao consumidor final',
    'Saúde': 'empresa do setor de saúde, com atuação em hospitais, planos de saúde, diagnósticos ou farmácias',
    'Imóveis': 'empresa do setor imobiliário, com foco em incorporação, shoppings ou desenvolvimento de empreendimentos',
    'Tecnologia': 'empresa do setor de tecnologia, com soluções em software, plataformas digitais ou hardware',
    'Consumo': 'empresa de bens de consumo, com produção de alimentos, bebidas ou produtos essenciais',
    'Industrial': 'empresa do setor industrial, com produção de bens de capital, máquinas ou equipamentos',
  };
  const descSetor = setorDescs[setor] || 'empresa listada na B3';
  const nome = s.name && s.name !== s.stock ? s.name : s.stock;
  return `${nome} é uma ${descSetor}, negociada na Bolsa de Valores do Brasil (B3).`;
}

function closeDetail() {
  document.getElementById('detailOverlay').classList.remove('open');
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

// ===== ANÁLISES =====
function renderAnalysesData(list) {
  document.getElementById('analysisCards').innerHTML = list.map(a => {
    const recLabel = a.rec === 'buy' ? '🟢 Compra' : a.rec === 'sell' ? '🔴 Venda' : '🟡 Neutro';
    const aUrl = safeUrl(a.url);
    const inner = `
      <div class="analysis-header">
        <span class="analysis-source">${esc(a.source)}</span>
        <span class="analysis-date">${esc(a.date)}</span>
      </div>
      <div class="analysis-title">${esc(a.title)}</div>
      <div class="analysis-summary">${esc(a.summary)}</div>
      <div style="display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap;">
        <span class="rec-badge ${esc(a.rec)}">${recLabel}</span>
        ${(a.tickers || []).length ? `<div class="analysis-tickers">${tickerTagsHtml(a.tickers)}</div>` : ''}
      </div>`;
    return `<div class="analysis-card">${aUrl ? `<a href="${aUrl}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none;display:block;">${inner}</a>` : inner}</div>`;
  }).join('');
}

function renderAnalyses() {
  renderAnalysesData([
    { source: 'BTG Pactual', date: 'Junho 2026', title: 'Carteira Recomendada de Ações — Junho 2026', summary: 'Top picks: PETR4, ITUB4, WEGE3, VALE3, BBAS3. Setor financeiro deve se beneficiar com queda de juros.', tickers: ['PETR4', 'ITUB4', 'WEGE3', 'VALE3', 'BBAS3'], rec: 'buy', url: '' },
    { source: 'XP Investimentos', date: 'Junho 2026', title: 'Top 10 Ações para Junho — Ibovespa a caminho dos 145k', summary: 'Preferência por empresas com forte geração de caixa. Destaques: RENT3, LREN3 e AXIA3.', tickers: ['RENT3', 'LREN3', 'AXIA3'], rec: 'buy', url: '' },
    { source: 'BTG Pactual', date: 'Junho 2026', title: 'Carteira de FIIs — Melhores Fundos para o Mês', summary: 'Recomendação de FIIs de tijolo com desconto sobre VP. HGLG11, XPLG11 e VISC11 como apostas.', tickers: ['HGLG11', 'XPLG11', 'VISC11'], rec: 'buy', url: '' },
    { source: 'Goldman Sachs', date: 'Maio 2026', title: 'Dólar pode cair para R$ 4,70 até o fim do ano', summary: 'Fluxo estrangeiro e política monetária dovish nos EUA devem pressionar moeda americana.', tickers: [], rec: 'hold', url: '' },
    { source: 'Suno Research', date: 'Junho 2026', title: 'FIIs de Papel vs Tijolo: O que comprar agora?', summary: 'Com queda da Selic, FIIs de tijolo ganham atratividade. Migração gradual de CRIs para galpões e shoppings.', tickers: ['MXRF11', 'IRDM11', 'XPML11'], rec: 'buy', url: '' },
  ]);
}

// ===== LOGIN GATE (captação de leads) =====
// Para forçar re-login de todos os usuários, incremente este número
const LOGIN_VERSION = 1;
const SHEETS_URL = 'https://script.google.com/macros/s/AKfycbwrzREM1n8exDkGWLrnxAZJds3p7JccVyPS_nrO-UbMuWMYwh-d2sIt5bj4TtF6if8/exec';
// Nenhuma seção é bloqueada por cadastro — todo o conteúdo é aberto.
// O formulário do "loginGate" agora é apenas uma newsletter opcional.
const GATED_PAGES = [];

function isLoggedIn() {
  const saved = localStorage.getItem('convexanews_login');
  if (!saved) return false;
  try {
    const data = JSON.parse(saved);
    return data.version === LOGIN_VERSION;
  } catch { return false; }
}

function requireLogin() {
  if (isLoggedIn()) return;
  const gate = document.getElementById('loginGate');
  gate.style.display = 'flex';
  gate.classList.remove('closing');
  document.getElementById('loginName').focus();
}

function closeLoginGate() {
  const gate = document.getElementById('loginGate');
  gate.classList.add('closing');
  setTimeout(() => { gate.style.display = 'none'; gate.classList.remove('closing'); }, 400);
}

function setFieldError(inputId, hasError) {
  const field = document.getElementById(inputId).closest('.login-field');
  if (hasError) field.classList.add('has-error');
  else field.classList.remove('has-error');
}

async function handleLogin(e) {
  e.preventDefault();
  const name = document.getElementById('loginName').value.trim();
  const email = document.getElementById('loginEmail').value.trim();
  const phone = document.getElementById('loginPhone').value.trim();
  const consent = document.getElementById('loginConsent').checked;

  const nameErr = !name;
  const emailErr = !email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const phoneErr = !phone;
  setFieldError('loginName', nameErr);
  setFieldError('loginEmail', emailErr);
  setFieldError('loginPhone', phoneErr);
  document.getElementById('consentLabel').classList.toggle('has-error', !consent);
  if (nameErr || emailErr || phoneErr || !consent) return false;

  const btn = document.getElementById('loginBtn');
  btn.disabled = true;
  btn.textContent = 'Entrando...';

  try {
    await fetch(SHEETS_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome: name, email, telefone: phone, origem: 'ConvexaNews', consentimento: true, data: new Date().toISOString() })
    });
  } catch (err) {
    console.warn('Sheets error (non-blocking):', err);
  }

  localStorage.setItem('convexanews_login', JSON.stringify({ name, email, phone, version: LOGIN_VERSION, ts: Date.now() }));
  btn.textContent = '✓ Bem-vindo!';

  setTimeout(() => {
    closeLoginGate();
    btn.disabled = false;
    btn.textContent = 'Entrar';
    updateAccessBtn();
  }, 800);

  return false;
}

function updateAccessBtn() {
  const btn = document.querySelector('.access-btn');
  if (!btn) return;
  if (isLoggedIn()) {
    btn.textContent = '✓ Inscrito';
    btn.onclick = null;
    btn.style.cursor = 'default';
  }
}

function switchPageGated(page) {
  if (GATED_PAGES.includes(page) && !isLoggedIn()) {
    history.replaceState(null, '', '#/' + state.currentPage);
    requireLogin();
    return;
  }
  switchPage(page);
}

// ===== INIT =====
async function init() {
  // 1. Notícias e análises dinâmicas (JSONs gerados pelo coletor)
  loadNoticias();
  loadAnalises();

  // 2. Interações
  setupSorting();
  setupSearch();

  // 3. DI futuro (B3, tempo real) — alimenta ticker e pagina Indicadores
  await fetchDIFuturo();

  // 4. Dados das tabelas: dados.json (GitHub Actions) com fallback BrAPI
  const dadosOk = await loadDadosJson();
  if (dadosOk) {
    loadTickerDataFromJson();
  } else {
    const brapiOk = await loadBrapiList();
    if (brapiOk) loadTickerData();
  }

  loadBRStocks();
  loadFIIs();
  loadETFs();
  loadUSStocks();
  loadCrypto();

  // 5. Tempo real a cada 2 min: DI futuro (B3) + ticker bar (BrAPI)
  setInterval(async () => {
    await fetchDIFuturo();
    if (state.currentPage === 'indicadores') renderDIFuturo();
    const ok = await loadBrapiList();
    if (ok) loadTickerData();
    else loadTickerDataFromJson();
  }, 120000);

  // 5. Tabelas: recarrega dados.json a cada 15 min (sincronizado com o robô)
  setInterval(async () => {
    await loadDadosJson();
    loadBRStocks();
    loadFIIs();
    loadETFs();
    loadUSStocks();
    loadCrypto();
    if (state.currentPage === 'indicadores') renderIndicadoresMercados();
  }, 900000);

  // 6. Rota inicial via hash (ex.: site.com/#/fiis)
  const inicial = pageFromHash();
  if (inicial !== 'noticias') switchPageGated(inicial);
}

updateAccessBtn();
init();
