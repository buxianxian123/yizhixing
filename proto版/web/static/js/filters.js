/* =========================================================
   筛选区：日期 / 快捷范围 / 批次多选 / 地区三级 / 模块 / 时效
   ========================================================= */
window.Filters = (function () {
  let meta = null;

  function init(m) {
    meta = m;
    renderPullSelect();
    renderModuleSelect();
    renderPeriodSelect();
    renderRegionSelect();
    bindQuickRange();
    bindDateRange();
    syncChipActive();
  }

  // ---------- 批次多选 ----------
  function renderPullSelect() {
    const sel = document.getElementById('f-pull');
    if (!meta || !meta.pulls) return;
    const selected = new Set(App.state.pulls);
    sel.innerHTML = meta.pulls.map(p =>
      `<option value="${p.pull_at}" ${selected.has(p.pull_at) ? 'selected' : ''}>${p.pull_at}</option>`
    ).join('');
    sel.onchange = () => {
      const vals = Array.from(sel.selectedOptions).map(o => o.value);
      App.state.pulls = vals;
      document.getElementById('f-pull-count').textContent = `已选 ${vals.length} 批`;
      // 选了批次就清空日期
      if (vals.length) {
        App.state.dateStart = ''; App.state.dateEnd = '';
        document.getElementById('f-date-start').value = '';
        document.getElementById('f-date-end').value = '';
      }
      App.apply();
    };
  }

  // ---------- 模块多选 ----------
  function renderModuleSelect() {
    const sel = document.getElementById('f-module');
    if (!meta || !meta.modules) return;
    const selected = new Set(App.state.modules);
    sel.innerHTML = meta.modules.map(m =>
      `<option value="${m.name}" ${selected.has(m.name) ? 'selected' : ''}>${m.display}</option>`
    ).join('');
    sel.onchange = () => {
      App.state.modules = Array.from(sel.selectedOptions).map(o => o.value);
      App.apply();
    };
  }

  // ---------- 时效多选 ----------
  function renderPeriodSelect() {
    const sel = document.getElementById('f-period');
    if (!meta || !meta.periods) return;
    const selected = new Set(App.state.periods);
    sel.innerHTML = meta.periods.map(p =>
      `<option value="${p}" ${selected.has(p) ? 'selected' : ''}>${p}</option>`
    ).join('');
    sel.onchange = () => {
      App.state.periods = Array.from(sel.selectedOptions).map(o => o.value);
      App.apply();
    };
  }

  // ---------- 地区三级联动 ----------
  async function renderRegionSelect() {
    const countrySel = document.getElementById('f-country');
    const provSel = document.getElementById('f-prov');
    const city3Sel = document.getElementById('f-city3');
    let tree;
    try {
      const res = await fetch('/api/regions');
      const body = await res.json();
      tree = body.data || {};
    } catch (e) {
      countrySel.innerHTML = '<option value="">全部</option>';
      return;
    }
    const countries = tree.countries || [];
    countrySel.innerHTML = '<option value="">全部地区</option>' +
      countries.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    provSel.innerHTML = '<option value="">全部</option>';
    city3Sel.innerHTML = '<option value="">全部</option>';

    countrySel.onchange = () => {
      App.state.country = countrySel.value;
      App.state.prov = ''; App.state.city3 = '';
      App.state.cities = [];
      const c = countries.find(x => x.name === App.state.country);
      provSel.innerHTML = '<option value="">全部</option>' + (c ? c.provs.map(p =>
        `<option value="${p.name}">${p.name}</option>`).join('') : '');
      city3Sel.innerHTML = '<option value="">全部</option>';
      document.getElementById('f-city3').value = '';
      App.apply();
    };
    provSel.onchange = () => {
      App.state.prov = provSel.value;
      App.state.city3 = '';
      App.state.cities = [];
      const c = countries.find(x => x.name === App.state.country);
      const p = c && c.provs.find(x => x.name === App.state.prov);
      city3Sel.innerHTML = '<option value="">全部</option>' + (p ? p.cities.map(city =>
        `<option value="${city}">${city}</option>`).join('') : '');
      App.apply();
    };
    city3Sel.onchange = () => {
      App.state.city3 = city3Sel.value;
      App.state.cities = [];
      if (App.state.city3) {
        // 城市由后端解析，前端仅标记（后端从 country/prov/city3 解析）
      }
      App.apply();
    };
  }

  // 日期输入：变更即自动勾选该范围内全部批次，并清除快捷范围高亮
  function bindDateRange() {
    ['f-date-start', 'f-date-end'].forEach(id => {
      document.getElementById(id).addEventListener('change', () => {
        App.state.lastPulls = 0;
        syncStateFromDom();
        syncChipActive();
        App.apply();
      });
    });
  }

  // ---------- 快捷范围（最近1/3/7天） ----------
  function syncChipActive() {
    const days = App.state.lastPulls;
    document.querySelectorAll('.chip[data-range]').forEach(c =>
      c.classList.toggle('active', `${days}d` === c.dataset.range));
  }

  function bindQuickRange() {
    const chips = document.querySelectorAll('.chip[data-range]');
    chips.forEach(chip => {
      chip.onclick = () => {
        const d = parseInt(chip.dataset.range.replace('d', ''), 10);
        App.state.dateStart = ''; App.state.dateEnd = '';
        document.getElementById('f-date-start').value = '';
        document.getElementById('f-date-end').value = '';
        App.setLastPulls(d);
        chips.forEach(c => c.classList.toggle('active', c === chip));
      };
    });
  }

  // ---------- 状态同步 ----------
  // 日期范围 → 自动勾选范围内全部批次（与后端 date_range 语义一致）
  function pullsInRange(ds, de) {
    if (!meta || !meta.pulls.length) return [];
    return meta.pulls
      .filter(p => {
        const d = p.pull_at.slice(0, 10);
        return (!ds || d >= ds) && (!de || d <= de);
      })
      .map(p => p.pull_at);
  }

  function syncStateFromDom() {
    const ds = document.getElementById('f-date-start').value;
    const de = document.getElementById('f-date-end').value;
    App.state.dateStart = ds;
    App.state.dateEnd = de;
    if (ds || de) {
      // 有日期则自动勾选该日期范围内全部批次
      App.state.pulls = pullsInRange(ds, de);
      renderPullSelect();
      document.getElementById('f-pull-count').textContent = `已选 ${App.state.pulls.length} 批`;
    }
  }

  function syncDomFromState() {
    document.getElementById('f-date-start').value = App.state.dateStart;
    document.getElementById('f-date-end').value = App.state.dateEnd;
    const sel = document.getElementById('f-pull');
    if (sel) sel.value = App.state.pulls;
    document.getElementById('f-pull-count').textContent = `已选 ${App.state.pulls.length} 批`;
  }

  function resetDom() {
    document.getElementById('f-date-start').value = '';
    document.getElementById('f-date-end').value = '';
    document.getElementById('f-country').value = '';
    document.getElementById('f-prov').innerHTML = '<option value="">全部</option>';
    document.getElementById('f-city3').innerHTML = '<option value="">全部</option>';
  }

  return { init, renderPullSelect, syncStateFromDom, syncDomFromState, resetDom, syncChipActive };
})();
