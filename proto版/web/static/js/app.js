/* =========================================================
   全局应用状态 + 筛选联动 + 数据加载 + 错误处理
   ========================================================= */
window.App = (function () {
  const state = {
    dateStart: '', dateEnd: '',
    pulls: [],            // 批次多选（精确 pull_at）
    cities: [],           // 城市多选
    country: '', prov: '', city3: '',
    modules: [],          // 模块多选
    periods: [],          // 时效多选
    lastPulls: 1,         // 快捷范围天数（默认最近1天/24小时）
  };

  let meta = null;            // /api/meta 缓存
  let lastFilterQuery = '';   // 上次成功请求的 query

  const C = { // 图表实例
    moduleBar: null, trend: null, top5: null, weather: null,
    fieldBar: null, cityRate: null,
  };

  // ---------- 基础 ----------
  async function fetchJSON(url) {
    const res = await fetch(url);
    const body = await res.json();
    if (!res.ok || body.error) {
      const err = body.error || `HTTP ${res.status}`;
      throw new Error(err);
    }
    return body.data;
  }

  function safeNum(v, digits) {
    const n = parseFloat(v);
    if (v === null || v === undefined || v === '' || isNaN(n)) return null;
    return digits !== undefined ? +n.toFixed(digits) : n;
  }

  // 编码筛选条件 → query string
  function encodeFilter(extra) {
    const p = new URLSearchParams();
    if (state.dateStart) p.set('date_start', state.dateStart);
    if (state.dateEnd) p.set('date_end', state.dateEnd);
    if (state.pulls.length) p.set('pulls', state.pulls.join(','));
    if (state.cities.length) p.set('cities', state.cities.join(','));
    if (state.country) p.set('country', state.country);
    if (state.prov) p.set('prov', state.prov);
    if (state.city3) p.set('city3', state.city3);
    if (state.modules.length) p.set('modules', state.modules.join(','));
    if (state.periods.length) p.set('periods', state.periods.join(','));
    if (extra) for (const k in extra) if (extra[k]) p.set(k, extra[k]);
    return p.toString();
  }

  // ---------- 数据加载 ----------
  async function refreshAll() {
    const q = encodeFilter();
    lastFilterQuery = q;
    showLoading();
    try {
      const dash = await fetchJSON('/api/dashboard?' + q);
      const { overview: ov, modules: mods, fields, top5, weather_mismatch: wm, cities, trend } = dash;
      renderCoreKPI(ov);
      renderQualityOverview(ov);
      Charts.updateModule(mods, ov);
      Charts.updatePie(ov);
      Charts.updateField(fields);
      Charts.updateTrend24(fields);
      Charts.updateTop5(top5);
      Charts.updateWeather(wm);
      Charts.updateCities(cities);
      Charts.updateTrend(trend);
      Tables.renderAll({ mods, fields, top5, wm, cities });
      updateDbStatus(null);
    } catch (e) {
      console.error('refreshAll:', e);
      showGlobalError(e.message);
    }
  }

  function showLoading() {
    const el = document.getElementById('core-kpis');
    el.innerHTML = `<div class="kpi" style="grid-column:1/-1"><div class="label">加载中…</div>
      <div class="value" style="font-size:16px;color:var(--text-tertiary)">正在查询数据，请稍候</div></div>`;
    document.getElementById('quality-overview').innerHTML = '';
  }

  function showGlobalError(msg) {
    const el = document.getElementById('core-kpis');
    el.innerHTML = `<div class="kpi" style="grid-column:1/-1"><div class="label">提示</div>
      <div class="value" style="font-size:16px">${escapeHtml(msg || '当前筛选条件暂无数据')}</div></div>`;
    document.getElementById('quality-overview').innerHTML = '';
  }

  function escapeHtml(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function rateClass(rateStr) {
    const v = safeNum(rateStr);
    if (v === null) return '';
    return v >= 80 ? 'rate-hi' : v >= 60 ? 'rate-mi' : 'rate-lo';
  }

  function renderCoreKPI(ov) {
    const el = document.getElementById('core-kpis');
    const items = [
      { label: '总体一致率', value: ov.overall_rate_str, cls: 'big', warn: ov.overall_rate < 40,
        extra: `一致 ${ov.total_ok} / 有效 ${ov.total_valid}` },
      { label: '有效字段数', value: ov.valid_field_count, extra: '参与比对的字段×模块组合' },
      { label: '参与城市数', value: ov.city_count, extra: '当前筛选城市' },
    ];
    el.innerHTML = items.map(k => `
      <div class="kpi ${k.cls || ''} ${k.warn ? 'warn' : ''}">
        <div class="label">${k.label}</div>
        <div class="value ${k.warn ? 'warn-c' : ''}">${k.value}</div>
        <div class="extra">${k.extra || ''}</div>
      </div>`).join('');
  }

  function renderQualityOverview(ov) {
    const el = document.getElementById('quality-overview');
    const items = [
      { label: '清洗数据', value: ov.clean_count, sub: '超物理范围剔除' },
      { label: '缺失数据', value: ov.miss_count, sub: '不进分母', danger: ov.miss_count > 0 },
      { label: '最差模块', value: ov.weakest_module ? ov.weakest_module.name : '-',
        sub: ov.weakest_module ? ov.weakest_module.rate : '' },
      { label: '最差字段', value: ov.weakest_field ? ov.weakest_field.name : '-',
        sub: ov.weakest_field ? ov.weakest_field.rate : '' },
      { label: 'TOP偏差城市', value: ov.top_dev_city ? ov.top_dev_city.city : '-',
        sub: ov.top_dev_city ? `${ov.top_dev_city.field} 偏差${ov.top_dev_city.dev}` : '' },
      { label: '天气误判', value: ov.weather_mismatch_count, sub: '大类不一致配对', danger: ov.weather_mismatch_count > 0 },
    ];
    el.innerHTML = `<div class="qo-header">质量异常概览</div>
      <div class="qo-grid">${items.map(k => `
        <div class="qo-item">
          <div class="qo-label">${k.label}</div>
          <div class="qo-value ${k.danger ? 'danger' : ''}">${k.value}</div>
          <div class="qo-sub">${k.sub || ''}</div>
        </div>`).join('')}</div>`;
  }

  // ---------- 报告 ----------
  async function generateReport() {
    const btn = event && event.target;
    if (btn) { btn.disabled = true; btn.textContent = '生成中…'; }
    try {
      const res = await fetch('/api/report/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      });
      const body = await res.json();
      if (!res.ok || body.error) throw new Error(body.error || '生成失败');
      const d = body.data;
      const zone = document.getElementById('report-zone');
      document.getElementById('report-meta').textContent =
        `生成于 ${d.generated_at} · 筛选: 日期 ${state.dateStart || '-'}~${state.dateEnd || '-'} · 批次 ${(d.filter_snapshot.pulls || []).length} 个 · 城市 ${d.filter_snapshot.cities.length} 个`;
      document.getElementById('report-dl-md').href = d.md_url;
      document.getElementById('report-dl-xlsx').href = d.xlsx_url;
      document.getElementById('report-preview').innerHTML = renderMdPreview(d.md);
      zone.classList.remove('hidden');
      zone.scrollIntoView({ behavior: 'smooth' });
    } catch (e) {
      alert('报告生成失败：' + e.message);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '生成 Markdown 报告'; }
    }
  }

  function buildPayload() {
    return {
      date_start: state.dateStart, date_end: state.dateEnd,
      pulls: state.pulls, cities: state.cities,
      country: state.country, prov: state.prov, city3: state.city3,
      modules: state.modules, periods: state.periods,
    };
  }

  function renderMdPreview(md) {
    const lines = md.split('\n');
    let html = '';
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (line.startsWith('# ')) { html += `<h3>${escapeHtml(line.slice(2))}</h3>`; i++; }
      else if (line.startsWith('## ')) { html += `<h4>${escapeHtml(line.slice(3))}</h4>`; i++; }
      else if (line.startsWith('### ')) { html += `<h5>${escapeHtml(line.slice(4))}</h5>`; i++; }
      else if (line.startsWith('|')) {
        const block = [];
        while (i < lines.length && lines[i].startsWith('|')) { block.push(lines[i]); i++; }
        html += _renderMdTable(block);
      }
      else { html += `<p>${escapeHtml(line) || '&nbsp;'}</p>`; i++; }
    }
    return html;
  }

  function _renderMdTable(block) {
    const rows = block.filter(l => !l.match(/^\|[\s:|-]+\|?$/)).map(l => {
      const s = l.trim().replace(/^\|/, '').replace(/\|$/, '');
      return s.split('|').map(c => c.trim());
    });
    if (!rows.length) return '';
    const thead = '<tr>' + rows[0].map(c => `<th>${escapeHtml(c)}</th>`).join('') + '</tr>';
    const tbody = rows.slice(1).map(r => '<tr>' + r.map(c => `<td>${escapeHtml(c)}</td>`).join('') + '</tr>').join('');
    return `<div class="tbl-wrap"><table><thead>${thead}</thead><tbody>${tbody}</tbody></table></div>`;
  }

  function closeReport() { document.getElementById('report-zone').classList.add('hidden'); }

  // ---------- 状态 & 联动 ----------
  function apply() {
    Filters.syncStateFromDom();
    refreshAll();
  }
  function reset() {
    Filters.resetDom();
    state.pulls = []; state.cities = []; state.modules = []; state.periods = [];
    state.country = ''; state.prov = ''; state.city3 = '';
    state.dateStart = ''; state.dateEnd = '';
    state.lastPulls = 1;
    Filters.initDefaultRange();
    Filters.syncChipActive();
    apply();
  }
  function setLastPulls(days) {
    state.lastPulls = days;
    // 取最近 days 天内的批次
    state.pulls = pullsInDays(days);
    Filters.renderPullSelect();
    apply();
  }

  // 最近 days 天内的批次时间（按最新批次往前推）
  function pullsInDays(days) {
    if (!meta || !meta.pulls.length) return [];
    const all = meta.pulls.map(p => p.pull_at).sort();
    const cutoff = new Date(new Date(all[all.length - 1]).getTime() - days * 86400000);
    return all.filter(ts => new Date(ts) >= cutoff);
  }

  function updateDbStatus(err) {
    const el = document.getElementById('db-status');
    if (err) { el.className = 'db-status err'; el.textContent = '数据源异常'; return; }
    el.className = 'db-status ok';
    el.textContent = meta
      ? `数据源 · ${meta.total_pulls} 批次 · ${meta.total_cities} 城市 · 最近 ${meta.last_pull_at}`
      : '数据源连接中…';
  }

  async function init() {
    try {
      meta = await fetchJSON('/health');
      meta = await fetchJSON('/api/meta');
      Filters.init(meta);
      initDefaultRange();
      updateDbStatus(null);
      Charts.initAll();
      Charts.initFbModuleList();
      await refreshAll();
    } catch (e) {
      console.error('init:', e);
      updateDbStatus(e.message);
      showGlobalError('无法连接数据源：' + e.message);
    }
  }

  function initDefaultRange() {
    if (meta && meta.pulls.length) {
      // 默认最近 24 小时（state.lastPulls 天）
      state.pulls = pullsInDays(state.lastPulls);
      state.dateStart = ''; state.dateEnd = '';
      Filters.renderPullSelect();
      Filters.syncDomFromState();
    }
  }

  // 暴露给全局
  return {
    state,
    get meta() { return meta; },
    get lastFilterQuery() { return lastFilterQuery; },
    set lastFilterQuery(v) { lastFilterQuery = v; },
    encodeFilter, refreshAll, apply, reset, setLastPulls,
    generateReport, closeReport,
    init, escapeHtml, safeNum, rateClass,
  };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
