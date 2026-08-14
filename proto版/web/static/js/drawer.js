/* =========================================================
   城市详情 Drawer：从图表点击钻取
   ========================================================= */
window.Drawer = (function () {
  function open(city) {
    const mask = document.getElementById('drawer-mask');
    const drawer = document.getElementById('drawer');
    document.getElementById('drawer-city').textContent = city;
    drawer.classList.remove('hidden');
    mask.classList.remove('hidden');
    document.getElementById('drawer-body').innerHTML =
      '<div class="empty">加载中…</div>';
    load(city);
  }

  function close() {
    document.getElementById('drawer').classList.add('hidden');
    document.getElementById('drawer-mask').classList.add('hidden');
  }

  async function load(city) {
    const el = document.getElementById('drawer-body');
    try {
      const url = '/api/city/' + encodeURIComponent(city) + '?' + App.lastFilterQuery;
      const res = await fetch(url);
      const body = await res.json();
      if (body.error) throw new Error(body.error);
      const d = body.data;
      const [country, prov] = d.region || ['', ''];
      let html = `
        <div class="sub-card">
          <h4>概览</h4>
          <div class="kv"><span>地区</span><b>${App.escapeHtml(country)} / ${App.escapeHtml(prov)}</b></div>
          <div class="kv"><span>总体一致率</span><b class="${App.rateClass(d.overall_rate + '%')}">${d.overall_rate}%</b></div>
          <div class="kv"><span>有效样本</span><b>${d.n}</b></div>
          <div class="kv"><span>一致数</span><b>${d.ok}</b></div>
          <div class="kv"><span>最近批次</span><b>${App.escapeHtml(d.recent_batch || '-')}</b></div>
          <div class="kv"><span>状态</span><b class="${d.abnormal ? 'rate-lo' : 'rate-hi'}">${d.abnormal ? '⚠ 异常' : '正常'}</b></div>
          <div class="kv"><span>最差字段</span><b>${App.escapeHtml(d.worst_field || '-')}</b></div>
        </div>`;
      // 各模块一致率
      if (d.modules && d.modules.length) {
        html += `<div class="sub-card"><h4>各模块一致率</h4>
          <div class="tbl-wrap"><table><thead><tr><th>模块</th><th>时效</th><th>有效</th><th>一致率</th></tr></thead><tbody>`;
        for (const m of d.modules) {
          html += `<tr><td>${App.escapeHtml(m.module.replace('模块', ''))}</td>
            <td>${App.escapeHtml(m.period || '')}</td><td class="num">${m.valid}</td>
            ${rateTd(m.rate)}</tr>`;
        }
        html += `</tbody></table></div></div>`;
      }
      // 字段明细（前200条）
      if (d.detail && d.detail.length) {
        html += `<div class="sub-card"><h4>字段明细（${d.detail_count} 条，显示前 ${d.detail.length}）</h4>
          <div class="tbl-wrap"><table><thead><tr><th>字段</th><th>时效</th><th>国内</th><th>海外</th>
            <th>差异</th><th>阈值</th><th>状态</th><th>批次</th></tr></thead><tbody>`;
        for (const r of d.detail.slice(0, 200)) {
          html += `<tr><td>${App.escapeHtml(r.field)}</td>
            <td>${App.escapeHtml(r.period || '-')}</td>
            <td class="num">${App.escapeHtml(r.cn ?? '-')}</td>
            <td class="num">${App.escapeHtml(r.iv ?? '-')}</td>
            <td class="num">${App.escapeHtml(r.diff ?? '-')}</td>
            <td class="num">${App.escapeHtml(r.threshold ?? '-')}</td>
            <td>${okTag(r.ok)}</td>
            <td class="num hint">${App.escapeHtml(r.pull_at || '')}</td></tr>`;
        }
        html += `</tbody></table></div></div>`;
      } else {
        html += `<div class="sub-card"><h4>字段明细</h4><div class="empty">当前筛选下无该城市数据</div></div>`;
      }
      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = `<div class="empty">加载失败：${App.escapeHtml(e.message)}</div>`;
    }
  }

  function rateTd(rateStr) {
    const cls = App.rateClass(rateStr);
    return `<td class="num ${cls}">${App.escapeHtml(rateStr)}</td>`;
  }
  function okTag(ok) {
    if (ok === '一致') return '<span class="tag ok">一致</span>';
    if (ok === '不一致') return '<span class="tag bad">不一致</span>';
    if (ok === '清洗剔除') return '<span class="tag miss">清洗</span>';
    return '<span class="tag miss">缺数据</span>';
  }

  return { open, close };
})();
