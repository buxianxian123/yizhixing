/* =========================================================
   表格渲染：结论汇总 / 模块详情 / TOP5 / 天气TOP对 / 规则 / 明细
   真 HTML table，支持排序/搜索/分页/固定表头/横向滚动/数字右对齐
   ========================================================= */
window.Tables = (function () {
  const state = {
    mods: [], fields: [], top5: [], wm: null, cities: [], reportMd: null,
    tab: 'summary',
    detailPage: 1, detailPerPage: 30, detailQ: '', detailSort: '', detailOrder: 'asc',
  };
  let detailAll = [];   // 明细全量（来自 /api/detail）

  function escape(s) { return App.escapeHtml(s); }

  function rateCell(rateStr) {
    const cls = App.rateClass(rateStr);
    return `<td class="num ${cls}">${escape(rateStr)}</td>`;
  }

  function switchTab(tab) {
    state.tab = tab;
    document.querySelectorAll('.tabs .tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.tab-body').forEach(el => {
      el.classList.toggle('hidden', el.id !== 'tab-' + tab);
    });
    renderActive();
  }

  function renderActive() {
    const map = {
      summary: renderSummary, detail: renderModuleDetail, top5: renderTop5,
      weather: renderWeatherPairs, rules: renderRules, rows: renderRows,
    };
    (map[state.tab] || renderSummary)();
  }

  function renderAll(data) {
    state.mods = data.mods; state.fields = data.fields; state.top5 = data.top5;
    state.wm = data.wm; state.cities = data.cities;
    state.reportMd = null;
    renderActive();
  }

  // ---------- 结论汇总（模块×字段，来自 /api/modules + /api/fields） ----------
  // 字段映射：不同模块字段名不同（如 15天 = 温度(最高)/(最低)、风速(白天)/(夜间)）
  // 与 gen_md_report.SUM_FIELDS / D15_DAY / D15_NIGHT 保持一致
  const SUM_COLS = ['温度', '湿度', '风速', '气压', '天气现象', '体感温度', '降水概率', 'AQI'];
  const SUM_MAP = {
    '温度': '温度', '湿度': '湿度', '风速': '风速', '气压': '气压',
    '天气现象': '天气现象', '体感温度': '体感温度', '降水概率': '降水概率', 'AQI': 'AQI',
  };
  const D15_DAY = {
    '温度': '温度(最高)', '湿度': '湿度', '风速': '风速(白天)', '气压': '气压',
    '天气现象': '天气现象(白天)', '体感温度': null, '降水概率': '降水概率', 'AQI': null,
  };
  const D15_NIGHT = {
    '温度': '温度(最低)', '湿度': '湿度', '风速': '风速(夜间)', '气压': '气压',
    '天气现象': '天气现象(夜间)', '体感温度': null, '降水概率': '降水概率', 'AQI': null,
  };

  function renderSummary() {
    const el = document.getElementById('tab-summary');
    const mods = state.mods;
    if (!mods || !mods.length) { el.innerHTML = '<div class="empty">当前筛选条件暂无数据</div>'; return; }
    const fields = state.fields;
    // 构建 模块行 → 各列 rate；d15Map 用于 15天 白天/夜间的字段映射
    const rateOf = (module, period, field, d15Map) => {
      const real = d15Map ? d15Map[field] : (SUM_MAP[field] || null);
      if (!real) return '-';
      const f = fields.find(x => x.module === module && x.period === period && x.field === real);
      return f ? f.rate : '-';
    };
    const thead = `<tr><th>模块</th><th>样本说明</th>` + SUM_COLS.map(c => `<th>${c}</th>`).join('') + `</tr>`;
    let tbody = '';
    for (const m of mods) {
      const disp = m.module.replace('模块', '');
      const periodLabel = m.period ? ` (${m.period})` : '';
      // 15天 拆成白天/夜间两行（与 gen_md_report 结论表一致）
      const pairs = m.module === '15天'
        ? [[D15_DAY, '白天'], [D15_NIGHT, '夜间']]
        : [[null, '']];
      for (const [d15Map, half] of pairs) {
        const cells = SUM_COLS.map(c => {
          const r = rateOf(m.module, m.period, c, d15Map);
          return r === '-' ? '<td class="num">-</td>' : rateCell(r);
        }).join('');
        const label = half ? `${disp}-${half}` : disp;
        tbody += `<tr><td>${escape(label)}${escape(periodLabel)}</td>
          <td>${m.valid} 有效 / 一致 ${m.ok}</td>${cells}</tr>`;
      }
    }
    el.innerHTML = `<div class="tbl-wrap"><table class="summary-tbl">
      <thead>${thead}</thead><tbody>${tbody}</tbody></table></div>`;
  }

  // ---------- 模块详情（字段粒度，来自 /api/fields） ----------
  function renderModuleDetail() {
    const el = document.getElementById('tab-detail');
    const fields = state.fields;
    if (!fields || !fields.length) { el.innerHTML = '<div class="empty">暂无数据</div>'; return; }
    // 按模块+时效分组
    const groups = {};
    for (const f of fields) {
      const key = f.module + '|' + f.period;
      (groups[key] = groups[key] || []).push(f);
    }
    let html = '';
    for (const key in groups) {
      const [module, period] = key.split('|');
      const title = `${module.replace('模块', '')}${period ? ' · ' + period : ''}`;
      const rows = groups[key].map(f => `<tr>
        <td>${escape(f.field)}</td>
        <td class="num">${f.valid}</td>
        <td class="num">${f.clean}</td>
        ${rateCell(f.rate)}
        <td class="num">${escape(f.avg_dev)}</td>
        <td class="num">${escape(f.max_dev)}</td>
        <td>${escape(f.max_city || '-')}</td>
      </tr>`).join('');
      html += `<div class="sub-card"><h4>${escape(title)}</h4>
        <div class="tbl-wrap"><table>
        <thead><tr><th>字段</th><th>有效样本</th><th>已清洗脏数据</th><th>一致率</th>
          <th>平均偏差</th><th>最大偏差</th><th>最大偏差城市</th></tr></thead>
        <tbody>${rows}</tbody></table></div></div>`;
    }
    el.innerHTML = html;
  }

  // ---------- TOP5 偏差城市（来自 /api/top5） ----------
  function renderTop5() {
    const el = document.getElementById('tab-top5');
    const top5 = state.top5;
    if (!top5 || !top5.length) { el.innerHTML = '<div class="empty">暂无数据</div>'; return; }
    // 按 模块+时效 分组
    const groups = {};
    for (const t of top5) {
      const key = t.module + '|' + t.period;
      (groups[key] = groups[key] || []).push(t);
    }
    let html = '';
    for (const key in groups) {
      const [module, period] = key.split('|');
      const rows = groups[key];
      // 按字段分组，每个字段一行 TOP1-5
      const byField = {};
      for (const r of rows) (byField[r.field] = byField[r.field] || []).push(r);
      let tbody = '';
      for (const field in byField) {
        const items = byField[field].slice(0, 5);
        const cells = items.map((r, idx) => {
          const label = r.pair ? `${r.city}(${r.pair})` : `${r.city}(${r.dev_str})`;
          const topClass = 'top' + (idx + 1);
          return `<td class="city ${topClass}" title="${escape(label)}">${escape(r.city)}<br>
            <small class="hint">${escape(r.pair || r.dev_str)}</small></td>`;
        }).join('');
        const padding = '<td class="city">-</td>'.repeat(Math.max(0, 5 - items.length));
        tbody += `<tr><td class="fname">${escape(field)}</td>${cells}${padding}</tr>`;
      }
      const title = `${module.replace('模块', '')}${period ? ' · ' + period : ''}`;
      html += `<div class="sub-card"><h4>${escape(title)} · TOP5 偏差城市</h4>
        <div class="tbl-wrap"><table>
        <thead><tr><th>字段</th><th>TOP1</th><th>TOP2</th><th>TOP3</th><th>TOP4</th><th>TOP5</th></tr></thead>
        <tbody>${tbody}</tbody></table></div></div>`;
    }
    el.innerHTML = html;
  }

  // ---------- 天气TOP对（来自 /api/weather-mismatch） ----------
  function renderWeatherPairs() {
    const el = document.getElementById('tab-weather');
    const wm = state.wm;
    if (!wm || !wm.mismatch_pairs || !wm.mismatch_pairs.length) {
      el.innerHTML = '<div class="empty">无不一致天气现象配对</div>'; return;
    }
    // 与图表同源：按 cn+iv 合并求和后排序
    const aggMap = {};
    for (const p of wm.mismatch_pairs) {
      const k = p.cn + '||' + p.iv;
      if (!aggMap[k]) aggMap[k] = { cn: p.cn, iv: p.iv, cnt: 0 };
      aggMap[k].cnt += p.cnt;
    }
    const mismatch = Object.values(aggMap).sort((a, b) => b.cnt - a.cnt).slice(0, 50);
    const rows = mismatch.map(p => `<tr>
      <td>${escape(p.cn)}</td><td>${escape(p.iv)}</td><td class="num">${p.cnt}</td>
    </tr>`).join('');
    el.innerHTML = `<div class="tbl-wrap"><table>
      <thead><tr><th>国内天气</th><th>海外天气</th><th>次数</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  }

  // ---------- 规则与口径（来自 /api/report/md 的 tables） ----------
  function renderRules() {
    const el = document.getElementById('tab-rules');
    if (state.reportMd) { _renderRulesContent(el, state.reportMd); return; }
    el.innerHTML = '<div class="empty">加载规则表中…</div>';
    fetch('/api/report/md?' + App.lastFilterQuery)
      .then(res => res.json())
      .then(body => {
        if (body.error) throw new Error(body.error);
        state.reportMd = body.data;
        _renderRulesContent(el, state.reportMd);
      })
      .catch(e => { el.innerHTML = `<div class="empty">加载失败：${escape(e.message)}</div>`; });
  }

  function _cleanTitle(title) {
    return escape(title.replace(/^[\d一二三四五六七八九十]+[、.\s]+/, '').replace(/^\d+\.\d+\s+/, ''));
  }

  function _extractMdList(md, heading) {
    const lines = md.split('\n');
    let start = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes(heading)) { start = i + 1; break; }
    }
    if (start < 0) return [];
    const items = [];
    for (let i = start; i < lines.length; i++) {
      if (lines[i].startsWith('## ')) break;
      const m = lines[i].match(/^\d+\.\s*(.+)/);
      if (m) items.push(m[1]);
    }
    return items;
  }

  function _renderRulesContent(el, reportMd) {
    if (!reportMd || !reportMd.tables || !reportMd.tables.length) {
      el.innerHTML = '<div class="empty">暂无规则表</div>'; return;
    }
    // 只保留规则类表格（排除 3.x 4.x 详情/TOP5 表 和 一、测试结论）
    const ruleKeywords = ['评测规则', '评测字段', '数值字段阈值', '天气现象比对', '脏数据清洗', '统计口径'];
    const matched = reportMd.tables.filter(t =>
      ruleKeywords.some(k => t.title.includes(k)));

    let html = '';
    for (const t of matched) {
      html += `<div class="sub-card"><h3 class="rule-h3">${_cleanTitle(t.title)}</h3>
        <div class="tbl-wrap">${t.html}</div></div>`;
    }

    // 局限性 & 风险点（从 MD 原文解析）
    if (reportMd.md) {
      const limits = _extractMdList(reportMd.md, '评测局限性');
      if (limits.length) {
        html += `<div class="sub-card"><h3 class="rule-h3">评测局限性</h3>
          <ol class="rule-list">${limits.map(x => `<li>${escape(x)}</li>`).join('')}</ol></div>`;
      }
      const risks = _extractMdList(reportMd.md, '风险与遗留');
      if (risks.length) {
        html += `<div class="sub-card"><h3 class="rule-h3">风险与遗留项</h3>
          <ol class="rule-list risk-list">${risks.map(x => `<li>${escape(x)}</li>`).join('')}</ol></div>`;
      }
    }

    el.innerHTML = html || '<div class="empty">暂无规则表</div>';
  }

  // ---------- 数据明细（来自 /api/detail） ----------
  async function renderRows() {
    const el = document.getElementById('tab-rows');
    const q = state.detailQ;
    try {
      const url = '/api/detail?' + App.lastFilterQuery +
        `&page=${state.detailPage}&per_page=${state.detailPerPage}` +
        (q ? `&q=${encodeURIComponent(q)}` : '');
      const res = await fetch(url);
      const body = await res.json();
      if (body.error) throw new Error(body.error);
      const d = body.data;
      detailAll = d.rows || [];
      const total = d.total || 0;
      const pages = Math.max(1, Math.ceil(total / state.detailPerPage));
      const rows = d.rows.map(r => `<tr>
        <td class="city">${escape(r.city)}</td>
        <td>${escape(r.module)}</td><td>${escape(r.field)}</td>
        <td class="num">${escape(r.ts || '')}</td>
        <td class="num">${escape(r.cn ?? '-')}</td><td class="num">${escape(r.iv ?? '-')}</td>
        <td class="num">${escape(r.diff ?? '-')}</td>
        <td>${okTag(r.ok)}</td><td class="num hint">${escape(r.period || '')}</td>
        <td class="num hint">${escape(r.pull_at || '')}</td>
      </tr>`).join('');
      const tools = `<div class="tbl-tools">
        <input placeholder="🔍 搜索城市/字段/模块…" value="${escape(q)}"
          oninput="Tables.setDetailQ(this.value)">
        <span>共 ${total} 条</span>
        <div class="pager">
          <button onclick="Tables.pageDetail(-1)" ${state.detailPage <= 1 ? 'disabled' : ''}>上一页</button>
          <span>${state.detailPage} / ${pages}</span>
          <button onclick="Tables.pageDetail(1)" ${state.detailPage >= pages ? 'disabled' : ''}>下一页</button>
        </div>
      </div>`;
      el.innerHTML = tools + `<div class="tbl-wrap"><table>
        <thead><tr><th>城市</th><th>模块</th><th>字段</th><th>时次</th><th>国内值</th>
          <th>海外值</th><th>差异</th><th>状态</th><th>时效</th><th>批次</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="10" class="empty">暂无数据</td></tr>'}</tbody></table></div>`;
    } catch (e) {
      el.innerHTML = `<div class="empty">明细加载失败：${escape(e.message)}</div>`;
    }
  }

  function okTag(ok) {
    if (ok === '一致') return '<span class="tag ok">一致</span>';
    if (ok === '不一致') return '<span class="tag bad">不一致</span>';
    if (ok === '清洗剔除') return '<span class="tag miss">清洗</span>';
    return '<span class="tag miss">缺数据</span>';
  }

  function setDetailQ(v) {
    clearTimeout(state._qTimer);
    state._qTimer = setTimeout(() => {
      state.detailQ = v;
      state.detailPage = 1;
      renderRows();
    }, 400);
  }
  function pageDetail(d) {
    state.detailPage += d;
    renderRows();
  }

  return {
    renderAll, switchTab, setDetailQ, pageDetail,
  };
})();
