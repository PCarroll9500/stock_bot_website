// ---------- CONFIG ----------
const DATA_PATH = './data/stockinfo.json';
const CACHE_BUST = () => `?v=${Date.now()}`;

// ---------- ELEMENTS ----------
const el = {
  year: document.getElementById('year'),
  ticker: document.getElementById('ticker'),
  lastUpdate: document.getElementById('lastUpdate'),
  status: document.getElementById('status'),
  tbody: document.getElementById('tbody'),
  raw: document.getElementById('raw'),
  showRawBtn: document.getElementById('showRawBtn'),
  retryBtn: document.getElementById('retryBtn'),
  chart: document.getElementById('chart'),
  chartWrap: document.getElementById('chartWrap'),
  errorBox: document.getElementById('errorBox'),
  errorMsg: document.getElementById('errorMsg'),
  localNotice: document.getElementById('localNotice'),
  pickBtn: document.getElementById('pickBtn'),
  fileInput: document.getElementById('fileInput')
};
el.year.textContent = new Date().getFullYear();

// ---------- HELPERS ----------
function setStatus(text, cls='') {
  el.status.className = `status ${cls}`;
  el.status.textContent = text;
}
function showError(err) {
  console.error(err);
  el.errorMsg.textContent = (err && err.message) ? err.message : String(err);
  el.errorBox.classList.remove('hidden');
  setStatus('Error loading data', 'err');
}
function hideError() {
  el.errorBox.classList.add('hidden');
  el.errorMsg.textContent = '';
}
function fmtNumber(n) {
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtDate(iso) {
  const d = (iso && iso.length <= 10) ? new Date(iso + 'T00:00:00') : new Date(iso);
  return isNaN(d) ? String(iso) : d.toLocaleDateString();
}
function drawChart(series) {
  const svg = el.chart;
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  if (!Array.isArray(series) || series.length < 2) { el.chartWrap.style.display = 'none'; return; }
  el.chartWrap.style.display = '';
  const W = 800, H = 220, PAD = 18;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const ys = series.map(p => Number(p.close)).filter(v => !Number.isNaN(v));
  const xMax = series.length - 1;
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const xScale = i => PAD + i * (W - 2*PAD) / (xMax || 1);
  const yScale = v => H - PAD - (v - yMin) * (H - 2*PAD) / ((yMax - yMin) || 1);
  // gridline last
  const last = ys[ys.length - 1];
  const grid = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  grid.setAttribute('x1', PAD); grid.setAttribute('x2', W - PAD);
  grid.setAttribute('y1', yScale(last)); grid.setAttribute('y2', yScale(last));
  grid.setAttribute('stroke', '#2a355f'); grid.setAttribute('stroke-dasharray', '4 4');
  svg.appendChild(grid);
  // path
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  let d = '';
  series.forEach((p, i) => { const x = xScale(i), y = yScale(Number(p.close)); d += (i ? ` L ${x} ${y}` : `M ${x} ${y}`); });
  path.setAttribute('d', d); path.setAttribute('fill','none'); path.setAttribute('stroke','#6ae2a0'); path.setAttribute('stroke-width','2.5');
  svg.appendChild(path);
  // last dot
  const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  dot.setAttribute('cx', xScale(xMax)); dot.setAttribute('cy', yScale(last)); dot.setAttribute('r', 4.5); dot.setAttribute('fill','#6ae2a0');
  svg.appendChild(dot);
  // min/max labels
  const lbls = [{x:PAD,y:H-4,t:fmtNumber(yMin)},{x:W-PAD,y:H-4,t:fmtNumber(yMax)}];
  lbls.forEach(l => { const t = document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x',l.x); t.setAttribute('y',l.y); t.setAttribute('fill','#9aa3b2'); t.setAttribute('font-size','11');
    t.setAttribute('text-anchor', l.x < W/2 ? 'start':'end'); t.textContent=l.t; svg.appendChild(t);
  });
}
function renderTable(series) {
  const tb = el.tbody; tb.innerHTML = '';
  if (!Array.isArray(series) || series.length === 0) { tb.innerHTML = '<tr><td colspan="2">No data points.</td></tr>'; return; }
  series.slice(-30).forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${fmtDate(p.date)}</td><td>${fmtNumber(p.close)}</td>`;
    tb.appendChild(tr);
  });
}
function validatePayload(data) {
  if (!data || typeof data !== 'object') throw new Error('Invalid JSON payload.');
  if (!('ticker' in data)) throw new Error('Missing "ticker" field.');
  if (!('series' in data)) throw new Error('Missing "series" field.');
  if (!Array.isArray(data.series)) throw new Error('"series" must be an array.');
  return data;
}
function renderAll(payload) {
  el.ticker.textContent = payload.ticker || '—';
  el.lastUpdate.textContent = payload.updated_at ? new Date(payload.updated_at).toLocaleString() : '—';
  renderTable(payload.series);
  drawChart(payload.series);
  el.raw.textContent = JSON.stringify(payload, null, 2);
  const n = payload.series?.length || 0;
  setStatus(n ? `Loaded ${n} data point${n===1?'':'s'}` : 'Loaded (no data points)', n ? 'ok' : 'warn');
}

// ---------- LOAD (server mode) ----------
async function loadFromServer() {
  hideError();
  setStatus('Loading…');
  el.tbody.innerHTML = '<tr><td colspan="2">Loading…</td></tr>';
  try {
    const resp = await fetch(DATA_PATH + CACHE_BUST(), { cache: 'no-store' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status} while fetching ${DATA_PATH}`);
    const data = await resp.json();
    renderAll(validatePayload(data));
  } catch (e) {
    showError(e);
  }
}

// ---------- LOAD (local file picker) ----------
function enableLocalFileMode() {
  el.localNotice.classList.remove('hidden');
  el.pickBtn.addEventListener('click', () => el.fileInput.click());
  el.fileInput.addEventListener('change', async () => {
    const f = el.fileInput.files?.[0];
    if (!f) return;
    try {
      const text = await f.text();
      const json = JSON.parse(text);
      renderAll(validatePayload(json));
      hideError();
      setStatus('Loaded from local file', 'ok');
    } catch (e) {
      showError(e);
    }
  });
}

// ---------- EVENTS ----------
el.retryBtn.addEventListener('click', () => {
  if (location.protocol === 'file:') {
    // In file mode, retry just re-prompts for file
    el.fileInput.value = '';
    el.fileInput.click();
  } else {
    loadFromServer();
  }
});
el.showRawBtn.addEventListener('click', () => {
  el.raw.classList.toggle('hidden');
  el.showRawBtn.textContent = el.raw.classList.contains('hidden') ? 'Show raw JSON' : 'Hide raw JSON';
});

// ---------- BOOT ----------
(function init() {
  if (location.protocol === 'file:') {
    // Local file mode: show helper and allow manual load
    setStatus('Waiting for local JSON…', 'warn');
    enableLocalFileMode();
  } else {
    // Server/Pages mode: just fetch it
    loadFromServer();
  }
})();