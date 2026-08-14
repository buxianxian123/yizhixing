/* =========================================================
   ECharts 图表 v2：模块/饼图/字段(侧栏+排序)/24h小多图/
   城市(滑块+侧栏)/天气(柱状+桑基)/趋势/TOP5
   依照 gen_html_report.py 功能对齐
   ========================================================= */
window.Charts = (function () {
  const C = {};
  let moduleView = 'bar';
  let weatherView = 'bar';
  let _lastMods = null, _lastOv = null, _lastWm = null;
  let _lastFields = null, _lastCities = null;
let _lastTop5 = null;

  // 字段一致率：排序 + 模块筛选
  let fieldAsc = true;
  let fbModule = '全部';

  // 城市排行：显示条数
  let cityView = 20;

  // 24h 小多图实例
  const TREND24_CELLS = [];

  // ===== Design Token（与 app.css :root 同源）=====
  const C_TEXT = '#4b525e';        // --text-secondary
  const C_TERTIARY = '#848b96';    // --text-tertiary
  const C_BORDER = '#e7e8eb';      // --border-default
  const C_SPLIT = '#eef0f2';       // splitLine
  const C_PRIMARY = '#3478d8';     // --primary

  const BASE = { color: C_TEXT, fontSize: 12 };
  const INK3 = C_TERTIARY;
  const SPLIT_LINE = { color: C_SPLIT };
  const LABEL = C_TERTIARY;
  const TOOLTIP = {
    backgroundColor: '#fff', borderColor: C_BORDER, borderWidth: 1,
    textStyle: { color: '#222529', fontSize: 12 },
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,.08); border-radius: 6px;',
  };

  // 模块色族（同一视觉家族，不制造好坏暗示）
  const MODULE_COLORS = ['#63a8e8', '#76a2df', '#879dde', '#9898d8', '#a894d2', '#b18fcb'];

  function initAll() {
    const ids = ['moduleBar', 'pie', 'trend', 'top5', 'weather', 'fieldBar', 'cityRate'];
    for (const id of ids) {
      const el = document.getElementById('ch-' + id);
      if (el) C[id] = echarts.init(el);
    }
    initTop5Field();
    window.addEventListener('resize', () => {
      for (const id in C) if (C[id]) C[id].resize();
      TREND24_CELLS.forEach(c => c && c.resize());
    });
  }

  function empty(el, msg) {
    el.innerHTML = `<div class="empty">${msg || '当前筛选条件暂无数据'}</div>`;
  }

  // 状态色：绿/黄/红 表达业务状态（一致率高低）
  function colorOf(rate) {
    return rate >= 80 ? '#27a464' : rate >= 60 ? '#f29c38' : '#e55252';
  }

  // ---------- 模块一致率 ----------
  // 24小时 按时效分段命名（短/中/长），避免三个「24小时」分不清
  const SEG_SHORT = {
    '短时效(1-6h)': '短', '中时效(7-12h)': '中', '长时效(13-24h)': '长',
  };

  function moduleLabel(m) {
    let name = m.module.replace('模块', '');
    if (m.period) {
      const seg = SEG_SHORT[m.period] || m.period.replace(/[()]/g, '');
      name = `${name} ${seg}`;
    }
    return name;
  }

  function updateModule(mods, ov) {
    _lastMods = mods; _lastOv = ov;
    if (!C.moduleBar) return;
    if (!mods || !mods.length) { empty(document.getElementById('ch-moduleBar')); return; }
    const data = mods.map(m => ({ name: moduleLabel(m), value: parseFloat(String(m.rate).replace('%', '')) || 0 }));
    if (moduleView === 'radar') {
      C.moduleBar.setOption({
        tooltip: { ...TOOLTIP, trigger: 'item', formatter: p => `${p.name}：${p.value}%` },
        radar: {
          indicator: data.map(d => ({ name: d.name, max: 100 })),
          radius: '60%',
          axisName: { color: INK3, fontSize: 11 },
          splitLine: { lineStyle: { color: C_SPLIT } },
          splitArea: { areaStyle: { color: ['rgba(52,120,216,.03)', 'rgba(52,120,216,.06)'] } },
        },
        series: [{
          type: 'radar',
          data: [{ value: data.map(d => d.value), areaStyle: { color: 'rgba(52,120,216,.15)' },
                   lineStyle: { color: C_PRIMARY } }],
        }],
      }, true);
    } else {
      C.moduleBar.setOption({
        tooltip: { ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}：${p[0].value}%` },
        grid: { left: 50, right: 20, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: data.map(d => d.name),
          axisLabel: { color: BASE.color, interval: 0, hideOverlap: false, rotate: 0, fontSize: 11 },
          axisLine: { lineStyle: { color: C_BORDER } } },
        yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: INK3 }, splitLine: { lineStyle: SPLIT_LINE } },
        series: [{
          type: 'bar', barWidth: '50%',
          data: data.map((d, i) => ({ value: d.value, itemStyle: { color: MODULE_COLORS[i % MODULE_COLORS.length] } })),
          label: { show: true, position: 'top', formatter: '{c}%', color: LABEL, fontSize: 12 },
        }],
      }, true);
    }
  }
  function setModuleView(v, btn) {
    moduleView = v;
    document.querySelectorAll('#card-moduleBar .ctl-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (_lastMods) updateModule(_lastMods, _lastOv);
  }

  // ---------- 一致分布饼图 ----------
  function updatePie(ov) {
    if (!C.pie) return;
    const ok = ov.total_ok || 0;
    const bad = (ov.total_valid || 0) - ok;
    const miss = ov.miss_count || 0;
    const clean = ov.clean_count || 0;
    C.pie.setOption({
      tooltip: { ...TOOLTIP, trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, icon: 'circle', textStyle: { color: INK3, fontSize: 12 } },
      series: [{
        type: 'pie', radius: ['42%', '68%'], center: ['50%', '45%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%', color: BASE.color, fontSize: 12 },
        data: [
          { name: '一致', value: ok, itemStyle: { color: '#34a873' } },
          { name: '不一致', value: bad, itemStyle: { color: '#e35757' } },
          { name: '缺数据', value: miss, itemStyle: { color: '#a1a8b3' } },
          { name: '清洗剔除', value: clean, itemStyle: { color: '#d0d4db' } },
        ],
      }],
    }, true);
  }

  // ---------- 一致率趋势 ----------
  function updateTrend(trend) {
    if (!C.trend) return;
    if (!trend || !trend.x || !trend.x.length) { empty(document.getElementById('ch-trend')); return; }
    const series = trend.series.map(s => ({
      name: s.name, type: 'line', smooth: true,
      data: s.data, connectNulls: true,
      itemStyle: { color: C_PRIMARY }, lineStyle: { color: C_PRIMARY, width: 2 },
      areaStyle: { color: 'rgba(52,120,216,.08)' },
    }));
    document.getElementById('trend-desc').textContent = `${trend.x.length} 个批次 · 总体一致率`;
    C.trend.setOption({
      tooltip: { ...TOOLTIP, trigger: 'axis' },
      legend: { textStyle: { color: INK3 }, top: 0 },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: trend.x, axisLabel: { color: INK3, fontSize: 10, interval: 'auto' } },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: INK3 }, splitLine: { lineStyle: SPLIT_LINE } },
      series,
    }, true);
  }

  // ---------- TOP5 偏差城市（模块 + 字段 双筛选，天气现象按次数排名） ----------
  let top5Module = '实况';
  let top5Field = '温度';
  const MODULE_ORDER = ['实况', '24小时', '15天', 'AQI模块'];

  // 模块 → 字段下拉（按 gen_md_report.MOD_FIELDS，不同模块字段不同）
  const MOD_FIELDS = {
    '实况': ['温度', '体感温度', '湿度', '风速', '气压', '天气现象'],
    '24小时': ['温度', '体感温度', '湿度', '风速', '天气现象', '降水概率'],
    '15天': ['温度(最高)', '温度(最低)', '湿度', '风速(白天)', '风速(夜间)', '气压', '天气现象(白天)', '天气现象(夜间)', '降水概率'],
    'AQI模块': ['AQI'],
  };

  function renderTop5FieldSelect() {
    const fSel = document.getElementById('top5-field');
    if (!fSel) return;
    const fields = MOD_FIELDS[top5Module] || [];
    if (!fields.includes(top5Field)) top5Field = fields[0] || '';
    fSel.innerHTML = fields.map(f =>
      `<option value="${f}" ${f === top5Field ? 'selected' : ''}>${f.replace('温度(最高)', '温度最高').replace('温度(最低)', '温度最低').replace('风速(白天)', '风速白天').replace('风速(夜间)', '风速夜间').replace('天气现象(白天)', '天气现象白天').replace('天气现象(夜间)', '天气现象夜间')}</option>`).join('');
  }

  function initTop5Field() {
    const mSel = document.getElementById('top5-module');
    if (mSel) mSel.innerHTML = MODULE_ORDER.map(m =>
      `<option value="${m}" ${m === top5Module ? 'selected' : ''}>${m === 'AQI模块' ? 'AQI' : m}</option>`).join('');
    renderTop5FieldSelect();
  }

  function switchTop5Module(module) {
    top5Module = module;
    renderTop5FieldSelect();
    if (_lastTop5) updateTop5(_lastTop5);
  }

  function switchTop5Field(field) {
    top5Field = field;
    if (_lastTop5) updateTop5(_lastTop5);
  }

  function updateTop5(top5) {
    _lastTop5 = top5;
    if (!C.top5) return;
    const el = document.getElementById('ch-top5');

    if (!top5 || !top5.length) { empty(el); return; }

    // 模块 + 字段双过滤（精确字段名，下拉已是模块专属字段）
    let rows = top5.filter(r => r.module === top5Module);
    if (top5Field) rows = rows.filter(r => r.field === top5Field);
    if (!rows.length) { empty(el, `「${top5Module.replace('模块','')} · ${top5Field}」暂无数据`); return; }

    // 城市级合并：同一城市在多个时效下取最大偏差/次数；天气现象后端已按次数统计
    const isWx = top5Field.includes('天气现象');
    const byCity = {};
    for (const r of rows) {
      const d = Math.abs(parseFloat(r.dev) || 0);
      if (!byCity[r.city] || d > byCity[r.city].dev) {
        byCity[r.city] = { dev: d, field: r.field };
      }
    }
    let merged = Object.entries(byCity)
      .map(([city, o]) => ({ city, dev: o.dev, field: o.field }))
      .sort((a, b) => b.dev - a.dev)
      .slice(0, 5);
    if (!merged.length) { empty(el); return; }

    const cities = merged.map(r => r.city);
    const devs = merged.map(r => r.dev);
    C.top5.setOption({
      tooltip: { ...TOOLTIP, trigger: 'axis', formatter: p => {
        const v = p[0].value;
        return top5Field.includes('天气现象') ? `${p[0].name}<br/>${v} 次天气现象偏差` : `${p[0].name}<br/>${v} 偏差`;
      } },
      grid: { left: 90, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value', axisLabel: { color: INK3 }, splitLine: { lineStyle: SPLIT_LINE } },
      yAxis: { type: 'category', data: cities, axisLabel: { color: BASE.color } },
      series: [{
        type: 'bar', barWidth: '55%',
        data: devs.map((d, i) => ({
          value: d, name: cities[i],
          itemStyle: { color: ['#e55252', '#ec6b5e', '#ef7e60', '#f19068', '#f3a270'][i] },
        })),
        label: { show: true, position: 'right', formatter: '{c}', color: LABEL },
      }],
    }, true);
    C.top5.off('click');
    C.top5.on('click', p => { if (p.name) Drawer.open(p.name); });
  }

  // ---------- 字段一致率（侧栏+排序+解读） ----------
  function initFbModuleList() {
    const list = ['全部', '实况', '24小时', '15天', 'AQI模块'];
    const el = document.getElementById('fb-module-list');
    if (!el) return;
    el.innerHTML = '<div class="sl-title">模块筛选</div>' +
      list.map(m => `<div class="sl-item${m === fbModule ? ' active' : ''}" onclick="Charts.setFbModule('${m}',this)"><span>${m === 'AQI模块' ? 'AQI' : m}</span></div>`).join('');
  }

  function updateField(fields) {
    _lastFields = fields;
    if (!C.fieldBar) return;
    const el = document.getElementById('ch-fieldBar');
    if (!fields || !fields.length) { empty(el); document.getElementById('fieldBar-note').innerHTML = '当前筛选下无数据。'; return; }

    const filtered = fbModule === '全部' ? fields : fields.filter(f => f.module === fbModule || f.module === fbModule + '模块');
    const grp = {};
    for (const f of filtered) {
      const k = f.field + '@' + f.module;
      if (!grp[k]) grp[k] = { f: f.field, m: f.module, rate: parseFloat(String(f.rate).replace('%', '')) || 0 };
    }
    let arr = Object.values(grp);
    arr.sort((a, b) => fieldAsc ? a.rate - b.rate : b.rate - a.rate);

    C.fieldBar.setOption({
      tooltip: { ...TOOLTIP, trigger: 'axis', formatter: p => `${p[0].name}<br/>一致率 ${p[0].value}%` },
      grid: { left: 170, right: 50, top: 20, bottom: 20 },
      xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: INK3 }, splitLine: { lineStyle: SPLIT_LINE } },
      yAxis: { type: 'category', data: arr.map(d => d.f + ' (' + (d.m === 'AQI模块' ? 'AQI' : d.m.replace('模块', '')) + ')'), axisLabel: { color: BASE.color, fontSize: 11 } },
      series: [{
        type: 'bar', barWidth: '62%',
        data: arr.map(d => ({ value: d.rate, itemStyle: { color: colorOf(d.rate) } })),
        label: { show: true, position: 'right', formatter: '{c}%', color: LABEL, fontSize: 11 },
      }],
    }, true);

    const sortBtn = document.getElementById('fb-sort');
    if (sortBtn) {
      sortBtn.textContent = fieldAsc ? '当前升序 ⇅ 切换' : '当前降序 ⇅ 切换';
      sortBtn.classList.toggle('active', !fieldAsc);
    }

    const noteEl = document.getElementById('fieldBar-note');
    if (arr.length) {
      const weakest = arr.reduce((a, b) => a.rate < b.rate ? a : b);
      const strongest = arr.reduce((a, b) => a.rate > b.rate ? a : b);
      const lowCnt = arr.filter(d => d.rate < 60).length;
      noteEl.innerHTML = `共 ${arr.length} 个字段×模块组合；最高 <b>${strongest.f} ${strongest.rate}%</b>，最低 <b>${weakest.f} ${weakest.rate}%</b>${lowCnt ? `，其中 <b>${lowCnt}</b> 个一致率不足 60% 需重点排查` : ''}。`;
    } else {
      noteEl.innerHTML = '当前筛选下无数据。';
    }
  }

  function toggleFieldSort() {
    fieldAsc = !fieldAsc;
    if (_lastFields) updateField(_lastFields);
  }
  function setFbModule(v, btn) {
    fbModule = v;
    document.querySelectorAll('#fb-module-list .sl-item').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (_lastFields) updateField(_lastFields);
  }

  // ---------- 24小时时效小多图 ----------
  function updateTrend24(fields) {
    const grid = document.getElementById('trend24-grid');
    if (!grid) return;
    const hFields = fields ? fields.filter(f => f.module === '24小时') : [];
    if (!hFields.length) { grid.innerHTML = '<div class="empty" style="padding:40px">当前筛选下无 24 小时数据</div>'; return; }

    const fieldMap = {};
    for (const f of hFields) {
      if (!fieldMap[f.field]) fieldMap[f.field] = {};
      fieldMap[f.field][f.period] = parseFloat(String(f.rate).replace('%', '')) || 0;
    }
    const fieldNames = Object.keys(fieldMap);
    const periods = ['短时效(1-6h)', '中时效(7-12h)', '长时效(13-24h)'];
    const shortNames = ['短', '中', '长'];

    if (TREND24_CELLS.length !== fieldNames.length) {
      TREND24_CELLS.forEach(c => c && c.dispose());
      TREND24_CELLS.length = 0;
      grid.innerHTML = fieldNames.map((f, i) =>
        `<div class="trend24-cell"><div class="trend24-title">${f.replace('天气现象', '天气现象')}</div><div class="trend24-chart" id="trend24-cell-${i}"></div></div>`
      ).join('');
      fieldNames.forEach((f, i) => {
        const el = document.getElementById('trend24-cell-' + i);
        if (el) TREND24_CELLS.push(echarts.init(el));
      });
    } else {
      fieldNames.forEach((f, i) => {
        const t = document.querySelectorAll('.trend24-title')[i];
        if (t) t.textContent = f.replace('天气现象', '天气');
      });
    }

    fieldNames.forEach((f, i) => {
      if (!TREND24_CELLS[i]) return;
      const data = periods.map(p => fieldMap[f][p] || 0);
      TREND24_CELLS[i].setOption({
        grid: { left: 30, right: 10, top: 22, bottom: 22 },
        tooltip: { ...TOOLTIP, trigger: 'axis', formatter: p => `${shortNames[p[0].dataIndex]}时效：${p[0].value}%` },
        xAxis: { type: 'category', data: shortNames, axisLabel: { fontSize: 10, color: INK3 }, axisTick: { show: false }, axisLine: { lineStyle: { color: C_BORDER } } },
        yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', fontSize: 9, color: INK3 }, splitLine: { lineStyle: SPLIT_LINE }, axisLine: { show: false }, axisTick: { show: false } },
        series: [{
          type: 'bar', barWidth: '46%',
          data: data.map((v, j) => ({ value: v, itemStyle: { color: [MODULE_COLORS[0], MODULE_COLORS[1], MODULE_COLORS[2]][j] } })),
          label: { show: true, position: 'top', formatter: '{c}', fontSize: 10, color: LABEL, fontWeight: 600 },
        }],
      }, true);
    });
  }

  // ---------- 城市一致率排行（滑块+侧栏） ----------
  function updateCities(cities) {
    _lastCities = cities;
    if (!C.cityRate) return;
    const el = document.getElementById('ch-cityRate');
    if (!cities || !cities.length) { empty(el); document.getElementById('city-rank-list').innerHTML = '<div class="sl-empty">暂无数据</div>'; return; }

    const arr = cities.map(c => ({ name: c.city, value: parseFloat(String(c.rate).replace('%', '')) || 0, abnormal: c.abnormal }))
      .sort((a, b) => a.value - b.value);

    const worst = arr.slice(0, 5);
    const best = arr.slice(-5).reverse();
    document.getElementById('city-rank-list').innerHTML = `
      <div class="sl-title">最差 5 城</div>
      ${worst.map(d => `<div class="sl-item bad" onclick="Drawer.open('${d.name}')"><span>${d.name}</span><b>${d.value}%</b></div>`).join('')}
      <div class="sl-title">最好 5 城</div>
      ${best.map(d => `<div class="sl-item ok" onclick="Drawer.open('${d.name}')"><span>${d.name}</span><b>${d.value}%</b></div>`).join('')}
    `;

    const startPercent = cityView === 0 ? 0 : Math.max(0, Math.floor((arr.length - cityView) / arr.length * 100));

    C.cityRate.setOption({
      grid: { left: 100, right: 70, top: 20, bottom: 20 },
      dataZoom: [{
        type: 'slider', yAxisIndex: 0, right: 10, width: 10,
        start: startPercent, end: 100,
        backgroundColor: 'transparent',
        dataBackground: { lineStyle: { color: 'transparent' }, areaStyle: { color: 'transparent' } },
        selectedDataBackground: { lineStyle: { color: C_PRIMARY }, areaStyle: { color: 'rgba(52,120,216,.18)' } },
        fillerColor: 'rgba(52,120,216,.12)', borderColor: 'transparent',
        handleSize: '100%', handleStyle: { color: C_PRIMARY, borderColor: '#2868c5', borderWidth: 0 },
        showDataShadow: false, showDetail: false,
      }],
      tooltip: { ...TOOLTIP, trigger: 'axis', formatter: p => `${p[0].name}：${p[0].value}%` },
      xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: INK3 }, splitLine: { lineStyle: SPLIT_LINE } },
      yAxis: { type: 'category', data: arr.map(d => d.name), axisLabel: { color: BASE.color, fontSize: 11 } },
      series: [{
        type: 'bar', barWidth: '60%',
        data: arr.map(d => ({ value: d.value, itemStyle: { color: d.abnormal ? '#e55252' : colorOf(d.value) } })),
        label: { show: true, position: 'right', formatter: '{c}%', color: LABEL, fontSize: 10 },
      }],
    }, true);
    C.cityRate.off('click');
    C.cityRate.on('click', p => { if (p.name) Drawer.open(p.name); });
  }

  function setCityView(n, btn) {
    cityView = n;
    document.querySelectorAll('#city-view-ctrl .ctl-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (_lastCities) updateCities(_lastCities);
  }

  // ---------- 天气现象误判（仅不一致配对，图表与表格同源） ----------
  function updateWeather(wm) {
    _lastWm = wm;
    if (!C.weather) return;
    const el = document.getElementById('ch-weather');

    if (!wm || !wm.mismatch_pairs || !wm.mismatch_pairs.length) {
      C.weather.clear();
      empty(el);
      document.getElementById('weather-note').innerHTML = '当前筛选下无不一致项，国内外天气现象判断完全一致。';
      document.getElementById('weather-table').innerHTML = '';
      return;
    }

    // 聚合 mismatch_pairs（不同模块/字段可能有相同配对，需合并）
    const aggMap = {};
    for (const p of wm.mismatch_pairs) {
      const k = p.cn + '||' + p.iv;
      if (!aggMap[k]) aggMap[k] = { cn: p.cn, iv: p.iv, cnt: 0 };
      aggMap[k].cnt += p.cnt;
    }
    const mismatch = Object.values(aggMap).sort((a, b) => b.cnt - a.cnt);

    // 解读条
    const totalCnt = mismatch.reduce((s, p) => s + p.cnt, 0);
    const top = mismatch[0];
    document.getElementById('weather-note').innerHTML =
      `共 <b>${mismatch.length}</b> 种不一致配对，合计 <b>${totalCnt}</b> 次。最常见误判：<b>国内${top.cn} › 海外${top.iv}</b>（${top.cnt}次）。`;

    // TOP10 表格（双列）-- 与图表同源
    const tblEl = document.getElementById('weather-table');
    const top10 = mismatch.slice(0, 10);
    const left = top10.slice(0, 5), right = top10.slice(5);
    const mk = (arr, start) => arr.length ?
      `<table><thead><tr><th class="rank">#</th><th>国内天气</th><th>海外天气</th><th>次数</th></tr></thead><tbody>` +
      arr.map((x, i) => `<tr><td class="rank">${start + i}</td><td>${x.cn}</td><td>${x.iv}</td><td><b>${x.cnt}</b></td></tr>`).join('') +
      `</tbody></table>` : '';
    tblEl.innerHTML = `<div class="sankey-twin"><div class="sankey-col"><div class="sl-title">前 5</div>${mk(left, 1)}</div><div class="sankey-col"><div class="sl-title">6 - 10</div>${mk(right, 6)}</div></div>`;

    // 图表：柱状图 TOP15 不一致配对（横向，按次数降序）
    C.weather.clear();
    const topPairs = mismatch.slice(0, 15);
    const labels = topPairs.map(p => `${p.cn} -> ${p.iv}`);
    const values = topPairs.map(p => p.cnt);
    C.weather.setOption({
      tooltip: { ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: p => `${p[0].name}<br/>${p[0].value} 次` },
      grid: { left: 160, right: 60, top: 20, bottom: 20 },
      xAxis: { type: 'value', max: Math.ceil(Math.max(...values, 1) * 1.15),
        axisLabel: { color: INK3 }, splitLine: { lineStyle: SPLIT_LINE } },
      yAxis: { type: 'category', data: labels, inverse: true,
        axisLabel: { color: BASE.color, fontSize: 11 },
        axisLine: { lineStyle: { color: C_BORDER } } },
      series: [{
        type: 'bar', barWidth: '58%',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: ['#e55252', '#ec6b5e', '#f29c38', '#f5c842', '#a3c46d',
            '#3478d8', '#5b8fd6', '#6366f1', '#7c6cc0', '#9370b8',
            '#db2777', '#e11d48', '#f0a0a0', '#d97706', '#27a464'][i % 15] },
        })),
        label: { show: true, position: 'right', formatter: '{c}', color: LABEL, fontSize: 11 },
      }],
    }, true);
  }

  return {
    initAll, updateModule, updatePie, updateTrend, updateTop5,
    updateField, updateTrend24, updateCities, updateWeather,
    setModuleView, toggleFieldSort, setFbModule, setCityView,
    initFbModuleList, initTop5Field, switchTop5Field,
  };
})();
