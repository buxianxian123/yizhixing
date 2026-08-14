#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务分析聚合层：一致率 / 偏差 / TOP5 / 天气误判 / 趋势 / 城市 / 明细。

全部建立在 rt.aggregate_stats 之上（与 gen_xlsx / gen_md_report 同口径），
保证「平台一致率 = MD 一致率」。

CompareResult = (pull_at, city, module, field, ts, cn_v, iv_v, diff, ok, note, period)
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config  # noqa: E402
import reformat_threshold as rt  # noqa: E402


# ============ 基础：stat 聚合 ============

def _stat(results):
    """results(11元组) → aggregate_stats 的 stat（去掉 pull_at 后喂）。"""
    results10 = [r[1:] for r in results]
    return rt.aggregate_stats(results10)


def _stat_from_10(results10):
    """results(10元组) → aggregate_stats 的 stat（供 gen_md_report 复用）。"""
    return rt.aggregate_stats(results10)


def _field_unit(field):
    """字段单位（与 gen_xlsx 格式化一致）。"""
    if '温度' in field or '体感' in field:
        return '℃'
    if '湿度' in field:
        return '%'
    if '风速' in field:
        return 'm/s'
    if '气压' in field:
        return 'hPa'
    if '降水概率' in field:
        return '%'
    if '降水' in field:
        return 'mm'
    return ''


def _fmt_dev(v, field):
    """偏差格式化：天气现象显示 '-'，数值带单位（与 gen_xlsx:482-499 一致）。
    summary 用（保留 float 原样，如 170.0hPa）。"""
    if '天气现象' in field:
        return '-'
    if v is None or v == '':
        return ''
    if isinstance(v, float):
        v = round(v, 2)
    return f'{v}{_field_unit(field)}'


def _fmt_dev_top5(v, field):
    """TOP5 偏差格式化：与 gen_xlsx「前五偏差城市」sheet 一致。
    有单位字段带单位（如 18.7℃），无单位字段存数字（AQI 472 → '472'）。"""
    if '天气现象' in field:
        return '-'
    if v is None or v == '':
        return ''
    if isinstance(v, float):
        v = round(v, 2)
    u = _field_unit(field)
    if not u and isinstance(v, float) and v.is_integer():
        v = int(v)
    return f'{v}{u}'


# ============ 供 API 的行数据 ============

def _iter_stat_sorted(stat):
    """按 gen_xlsx 的遍历顺序输出 (field, module, period, s)。"""
    mods = list(rt.MODULES.keys())
    period_order = {p[0]: i for i, p in enumerate(rt.PERIODS_24H)}
    items = sorted(stat.items(), key=lambda x: (
        mods.index(x[0][1]) if x[0][1] in mods else 99,
        x[0][0],
        period_order.get(x[0][2], 99),
    ))
    return items


def _summary_from_stat(stat):
    """stat → summary 行（字段粒度，= gen_xlsx 总结 sheet 逐行）。"""
    rows = []
    for (field, m, period), s in _iter_stat_sorted(stat):
        rate = f"{s['ok'] / s['n'] * 100:.1f}%" if s['n'] else '0'
        if '天气现象' in field:
            avg_display = '-'
            max_display = '-'
        else:
            avg_display = round(s['sumdiff'] / s['n'], 2) if s['n'] else ''
            max_display = s['maxdiff']
        avg_display = _fmt_dev(avg_display, field)
        max_display = _fmt_dev(max_display, field)
        rows.append({
            'field': field, 'module': m, 'period': period or '',
            'total': s['total'], 'miss': s['miss'], 'clean': s['clean'],
            'valid': s['n'], 'ok': s['ok'], 'rate': rate,
            'avg_dev': avg_display, 'max_dev': max_display, 'max_city': s['maxcity'],
        })
    return rows


def summary_rows(results):
    """字段粒度行（11元组 results 版，平台 API 用）。"""
    return _summary_from_stat(_stat(results))


def summary_rows_from_10(results10):
    """字段粒度行（10元组版，供 gen_md_report.build_md 复用）。

    输出与 gen_md_report.read_summary 同 schema：avgDev/maxDev/maxCity。
    """
    rows = _summary_from_stat(_stat_from_10(results10))
    out = []
    for r in rows:
        out.append({
            'field': r['field'], 'module': r['module'], 'period': r['period'],
            'total': r['total'], 'miss': r['miss'], 'clean': r['clean'],
            'valid': r['valid'], 'ok': r['ok'], 'rate': r['rate'],
            'avgDev': r['avg_dev'], 'maxDev': r['max_dev'], 'maxCity': r['max_city'],
        })
    return out


def module_rows(results):
    """模块+时效粒度（= MD 结论汇总表的行）。按模块聚合（跨字段）。"""
    rows = summary_rows(results)
    out = []
    for m in rt.MODULES.keys():
        m_rows = [r for r in rows if r['module'] == m]
        # 按 period 分组（24h 分时效，其他单 period）
        periods = sorted({r['period'] for r in m_rows}, key=lambda x: config.PERIOD_DISPLAY.index(x) if x in config.PERIOD_DISPLAY else 99) or ['']
        for period in periods:
            sub = [r for r in m_rows if r['period'] == period]
            ok = sum(r['ok'] for r in sub)
            n = sum(r['valid'] for r in sub)
            miss = sum(r['miss'] for r in sub)
            clean = sum(r['clean'] for r in sub)
            total = sum(r['total'] for r in sub)
            rate = f"{ok / n * 100:.1f}%" if n else '0'
            out.append({
                'module': m, 'period': period or '',
                'total': total, 'miss': miss, 'clean': clean,
                'valid': n, 'ok': ok, 'rate': rate,
            })
    return out


def overview(results, fs):
    """首页 KPI 卡片。"""
    rows = summary_rows(results)
    total_ok = sum(r['ok'] for r in rows)
    total_valid = sum(r['valid'] for r in rows)
    total_miss = sum(r['miss'] for r in rows)
    total_clean = sum(r['clean'] for r in rows)
    overall_rate = round(total_ok / total_valid * 100, 1) if total_valid else 0.0

    # 城市维度
    city_agg = _city_agg(results)
    city_count = len(city_agg)

    # 异常城市（平台新增口径，不入 MD）
    abnormal = [c for c, a in city_agg.items() if a['abnormal']]

    # 最差模块 / 最差字段（有效样本>=10 才参与，与 gen_html 一致）
    mod_rows = module_rows(results)
    weakest_mod = min([r for r in mod_rows if r['valid'] >= 10], key=lambda r: _rate_num(r['rate']), default=None)
    weakest_field = min([r for r in rows if r['valid'] >= 10], key=lambda r: _rate_num(r['rate']), default=None)

    # TOP 偏差城市（实况，非天气现象，|偏差|/阈值 最大）
    top_dev = _top_dev_city(results)

    # 天气误判数量
    wm = weather_mismatch(results)
    weather_mismatch_count = sum(p['cnt'] for p in wm['mismatch_pairs'])

    return {
        'overall_rate': overall_rate,
        'overall_rate_str': f'{overall_rate:.1f}%',
        'total_ok': total_ok, 'total_valid': total_valid,
        'valid_field_count': len(rows),
        'city_count': city_count,
        'abnormal_city_count': len(abnormal),
        'clean_count': total_clean,
        'miss_count': total_miss,
        'weakest_module': {'name': weakest_mod['module'], 'rate': weakest_mod['rate']} if weakest_mod else None,
        'weakest_field': {'name': weakest_field['field'], 'rate': weakest_field['rate']} if weakest_field else None,
        'top_dev_city': top_dev,
        'weather_mismatch_count': weather_mismatch_count,
        'per_module': mod_rows,
    }


def _rate_num(rate_str):
    if not rate_str or rate_str == '0':
        return 0.0
    try:
        return float(str(rate_str).replace('%', ''))
    except (ValueError, TypeError):
        return 0.0


# ============ 城市维度 ============

def _city_agg(results):
    """按城市聚合。abnormal: 任一字段 rate<60 或 总体 rate<85。"""
    stat = _stat(results)
    city_map = {}
    # 每城：字段级统计
    per_city_field = defaultdict(lambda: defaultdict(lambda: {'ok': 0, 'n': 0, 'sumdiff': 0, 'maxdiff': 0, 'maxcity': ''}))
    for r in results:
        pull_at, city, module, field, ts, cnv, iv, diff, ok, note, period = r
        if ok in ('清洗剔除', '缺数据', ''):
            continue
        c = per_city_field[city][field]
        c['n'] += 1
        if ok == '一致':
            c['ok'] += 1
        if isinstance(diff, (int, float)):
            c['sumdiff'] += abs(diff)
            if abs(diff) > abs(c['maxdiff']):
                c['maxdiff'] = diff
    for city, fields in per_city_field.items():
        ok = sum(f['ok'] for f in fields.values())
        n = sum(f['n'] for f in fields.values())
        rate = round(ok / n * 100, 1) if n else 0.0
        field_rates = {f: round(fd['ok'] / fd['n'] * 100, 1) if fd['n'] else 0.0 for f, fd in fields.items()}
        abnormal = rate < config.ABNORMAL_CITY_RATE or any(
            fr < config.ABNORMAL_FIELD_RATE for fr in field_rates.values())
        worst = min(field_rates, key=field_rates.get) if field_rates else None
        city_map[city] = {
            'ok': ok, 'n': n, 'rate': rate,
            'abnormal': abnormal, 'worst_field': worst,
            'field_rates': field_rates,
        }
    return city_map


def city_rows(results, fs):
    """城市表/散点。"""
    city_agg = _city_agg(results)
    # 地区映射
    region = _load_region()
    out = []
    for city, a in city_agg.items():
        rg = region.get(city, ['', ''])
        out.append({
            'city': city, 'country': rg[0], 'prov': rg[1],
            'n': a['n'], 'ok': a['ok'], 'rate': a['rate'],
            'abnormal': a['abnormal'], 'worst_field': a['worst_field'],
        })
    return out


def city_detail(results, fs, name):
    """城市详情抽屉。"""
    stat = _stat(results)
    region = _load_region()
    city_agg = _city_agg(results)

    # 该城市的字段明细
    detail = []
    for r in results:
        pull_at, city, module, field, ts, cnv, iv, diff, ok, note, period = r
        if city != name:
            continue
        spec = rt.MODULES.get(module, {}).get('fields', {}).get(field, {})
        th = rt.get_threshold(field)
        detail.append({
            'pull_at': pull_at, 'module': module, 'field': field, 'period': period or '',
            'ts': ts, 'cn': cnv, 'iv': iv, 'diff': diff, 'ok': ok, 'note': note,
            'threshold': th,
        })
    detail.sort(key=lambda x: x['pull_at'])

    agg = city_agg.get(name, {})
    # 最近批次
    pulls = sorted({r[0] for r in results if r[1] == name})
    recent = pulls[-1] if pulls else None
    return {
        'city': name, 'lon': None, 'lat': None,
        'region': region.get(name, ['', '']),
        'recent_batch': recent,
        'overall_rate': agg.get('rate', 0.0),
        'ok': agg.get('ok', 0), 'n': agg.get('n', 0),
        'abnormal': agg.get('abnormal', False),
        'worst_field': agg.get('worst_field'),
        'field_rates': agg.get('field_rates', {}),
        'modules': module_rows(results),
        'detail_count': len(detail),
        'detail': detail[:2000],  # 抽屉展示上限
    }


def _load_region():
    import json
    try:
        with open(config.REGION_JSON, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


# ============ TOP5 偏差城市 ============

def _top5_from_stat(stat, wx_city_cnt=None):
    """stat → TOP5 偏差城市行（= 前五偏差城市 sheet 逐行）。

    wx_city_cnt: 天气现象每城市偏差次数 {(module, field, period): {city: n}}，
    用于天气现象字段按「偏差次数」排名（而非评分制偏差值）。
    """
    rows = []
    mods = list(rt.MODULES.keys())
    period_order = {p[0]: i for i, p in enumerate(rt.PERIODS_24H)}
    items = sorted(stat.items(), key=lambda x: (
        mods.index(x[0][1]) if x[0][1] in mods else 99,
        x[0][0],
        period_order.get(x[0][2], 99),
    ))
    for (field, m, period), s in items:
        top_items = list(s['top'].items())
        if '天气现象' in field and wx_city_cnt:
            # 天气现象：按该城市偏差次数排名，偏差次数为城市计数值
            cnt = wx_city_cnt.get((m, field, period or ''), {})
            top_sorted = sorted(top_items, key=lambda x: (
                -cnt.get(x[0], 0),
                -rt.CITY_RANK.get(x[0], 9999),
            ))[:5]
        else:
            top_sorted = sorted(top_items, key=lambda x: (
                -abs(x[1][0]),
                -rt._weather_level_diff(x[1][1], x[1][2]),
                -rt.CITY_RANK.get(x[0], 9999),
            ))[:5]
        for rank, (city, val) in enumerate(top_sorted, 1):
            d, cn_val, intl_val = val
            if cn_val and intl_val and '天气现象' in field:
                pair_str = f'国内{cn_val}→国外{intl_val}'
            else:
                pair_str = ''
            if '天气现象' in field and wx_city_cnt:
                n = cnt.get(city, 0)
                rows.append({
                    'module': m, 'field': field, 'period': period or '',
                    'rank': rank, 'city': city, 'pair': pair_str,
                    'dev': n, 'dev_str': f'{n}次',
                })
            else:
                rows.append({
                    'module': m, 'field': field, 'period': period or '',
                    'rank': rank, 'city': city, 'pair': pair_str,
                    'dev': round(d, 2), 'dev_str': _fmt_dev_top5(d, field),
                })
    return rows


def _weather_city_cnt(results):
    """天气现象每城市偏差次数 {(module, field, period): {city: n}}。
    仅统计天气现象且判定为不一致的点。"""
    from collections import defaultdict
    cnt = defaultdict(lambda: defaultdict(int))
    for r in results:
        pull_at, city, module, field, ts, cnv, iv, diff, ok, note, period = r
        if '天气现象' not in field or ok != '不一致':
            continue
        cnt[(module, field, period or '')][city] += 1
    return {k: dict(v) for k, v in cnt.items()}


def top5_rows(results):
    """TOP5 偏差城市（11元组 results 版）。"""
    return _top5_from_stat(_stat(results), wx_city_cnt=_weather_city_cnt(results))


def top5_rows_from_10(results10):
    """TOP5 偏差城市（10元组版，供 gen_md_report.build_md 复用）。

    输出与 gen_md_report.read_top5 同 schema：module/field/period/rank/city/pair/dev
    （dev 为带单位字符串，天气现象 dev 用 pair）。
    """
    rows = _top5_from_stat(_stat_from_10(results10))
    out = []
    for r in rows:
        out.append({
            'module': r['module'], 'field': r['field'], 'period': r['period'],
            'rank': r['rank'], 'city': r['city'], 'pair': r['pair'],
            # 与 gen_md_report.read_top5 一致：dev 为 xlsx 中「偏差」列的字符串（带单位）
            'dev': r['dev_str'],
        })
    return out


# ============ 天气误判 ============

def _weather_pairs_from_stat(stat):
    """stat → 天气TOP对（大类不一致，按次数降序前5，与 gen_xlsx 天气TOP对 sheet 同口径）。
    返回 [{module, field, period, cn, iv, cnt}]"""
    out = []
    for (field, m, period), s in stat.items():
        if '天气现象' not in field or not s.get('pair_counts'):
            continue
        sorted_pairs = sorted(s['pair_counts'].items(), key=lambda x: -x[1])
        mismatch = []
        for (cn_val, intl_val), cnt in sorted_pairs:
            a = rt.WTH_TEXTS.get(cn_val)
            b = rt.WTH_TEXTS.get(intl_val)
            if a is not None and b is not None and a['cat'] != b['cat']:
                mismatch.append(((cn_val, intl_val), cnt))
        for (cn_val, intl_val), cnt in mismatch[:5]:
            out.append({'module': m, 'field': field, 'period': period or '',
                        'cn': cn_val, 'iv': intl_val, 'cnt': cnt})
    return out


def weather_pairs_from_10(results10):
    """天气TOP对（10元组版，供 gen_md_report 复用）。"""
    return _weather_pairs_from_stat(_stat_from_10(results10))


def weather_mismatch(results):
    """天气误判：全部配对 + 大类不一致配对 + 8大类映射。"""
    stat = _stat(results)
    all_pairs = defaultdict(int)
    mismatch_pairs = []
    for (field, m, period), s in stat.items():
        if '天气现象' not in field:
            continue
        sorted_pairs = sorted(s['pair_counts'].items(), key=lambda x: -x[1])
        for (cn_val, intl_val), cnt in sorted_pairs:
            all_pairs[(cn_val, intl_val)] += cnt
            a = rt.WTH_TEXTS.get(cn_val)
            b = rt.WTH_TEXTS.get(intl_val)
            if a is not None and b is not None and a['cat'] != b['cat']:
                mismatch_pairs.append({
                    'cn': cn_val, 'iv': intl_val, 'cnt': cnt,
                    'cn_cat': a['cat'], 'iv_cat': b['cat'],
                })
    # 大类映射（8类）
    cat_map = {k: v for k, v in rt.WTH_TEXTS.items()}
    return {
        'all_pairs': [{'cn': c, 'iv': i, 'cnt': n} for (c, i), n in sorted(all_pairs.items(), key=lambda x: -x[1])],
        'mismatch_pairs': sorted(mismatch_pairs, key=lambda x: -x['cnt'])[:50],
        'cat_map': cat_map,
    }


# ============ 趋势 / 批次比较 ============

def trend_rows(results, fs):
    """按 pull_at 的一致率趋势（dim=overall/module/field）。"""
    dim = fs.get('dim', 'overall') if hasattr(fs, 'get') else 'overall'
    dim = dim or 'overall'
    # 按 pull_at 分组
    by_batch = defaultdict(list)
    for r in results:
        by_batch[r[0]].append(r)
    pulls_sorted = sorted(by_batch.keys())

    def _rate_of(sub):
        ok = sum(1 for r in sub if r[8] == '一致')
        n = sum(1 for r in sub if r[8] not in ('清洗剔除', '缺数据', ''))
        return round(ok / n * 100, 1) if n else None

    if dim == 'module':
        mod_names = list(rt.MODULES.keys())
        out = []
        for m in mod_names:
            out.append({'name': config.MODULE_DISPLAY.get(m, m),
                        'data': [_rate_of([r for r in by_batch[p] if r[2] == m]) for p in pulls_sorted]})
        return {'x': pulls_sorted, 'series': out}
    elif dim == 'field':
        fields_sorted = sorted({r[3] for r in results})
        out = []
        for f in fields_sorted:
            out.append({'name': f,
                        'data': [_rate_of([r for r in by_batch[p] if r[3] == f]) for p in pulls_sorted]})
        return {'x': pulls_sorted, 'series': out}
    else:
        # overall
        data = [_rate_of(by_batch[p]) for p in pulls_sorted]
        return {'x': pulls_sorted, 'series': [{'name': '总体一致率', 'data': data}]}


def compare_rows(results, fs):
    """A/B 两组比较。"""
    a_pulls = set(fs.group_a)
    b_pulls = set(fs.group_b)
    a_res = [r for r in results if r[0] in a_pulls]
    b_res = [r for r in results if r[0] in b_pulls]

    def _summ(res):
        rows = summary_rows(res)
        ok = sum(r['ok'] for r in rows)
        n = sum(r['valid'] for r in rows)
        return {'overall_rate': round(ok / n * 100, 1) if n else 0.0,
                'ok': ok, 'valid': n, 'rows': rows}

    a = _summ(a_res)
    b = _summ(b_res)
    diff = round((a['overall_rate'] or 0) - (b['overall_rate'] or 0), 1)
    return {
        'a': {'overall_rate': a['overall_rate'], 'ok': a['ok'], 'valid': a['valid'],
              'pulls': sorted(a_pulls)},
        'b': {'overall_rate': b['overall_rate'], 'ok': b['ok'], 'valid': b['valid'],
              'pulls': sorted(b_pulls)},
        'diff': {'overall_rate': diff},
    }


def detail_rows(results, fs):
    """明细分页（前端再分页；后端提供全量行，SQL 级分页见 repository）。"""
    page = int(fs.get('page', 1) if hasattr(fs, 'get') else 1)
    per_page = int(fs.get('per_page', config.DETAIL_PAGE_SIZE) if hasattr(fs, 'get') else config.DETAIL_PAGE_SIZE)
    q = (fs.get('q') if hasattr(fs, 'get') else '') or ''
    sort = (fs.get('sort') if hasattr(fs, 'get') else '') or ''
    order = (fs.get('order') if hasattr(fs, 'get') else '') or 'asc'

    rows = []
    for r in results:
        pull_at, city, module, field, ts, cnv, iv, diff, ok, note, period = r
        rows.append({
            'pull_at': pull_at, 'city': city, 'module': module, 'field': field,
            'ts': ts, 'cn': cnv, 'iv': iv, 'diff': diff, 'ok': ok, 'note': note,
            'period': period or '',
        })
    if q:
        rows = [r for r in rows if q in r['city'] or q in r['field'] or q in r['module']]
    if sort in ('city', 'field', 'module', 'pull_at', 'ok'):
        rows.sort(key=lambda r: (r.get(sort) is None, str(r.get(sort))), reverse=(order == 'desc'))
    elif sort in ('cn', 'iv', 'diff'):
        def _nk(r):
            v = r.get(sort)
            try:
                return float(v)
            except (TypeError, ValueError):
                return float('-inf')
        rows.sort(key=lambda r: (r.get(sort) is None, _nk(r)), reverse=(order == 'desc'))

    total = len(rows)
    start = (page - 1) * per_page
    return {'total': total, 'page': page, 'per_page': per_page, 'rows': rows[start:start + per_page]}


# ============ 工具 ============

def _top_dev_city(results):
    """实况模块 |偏差|/阈值 最大的城市（非天气现象）。"""
    TH = rt.THRESHOLDS
    best_ratio = -1
    best = None
    for r in results:
        pull_at, city, module, field, ts, cnv, iv, diff, ok, note, period = r
        if module != '实况' or '天气现象' in field:
            continue
        if not isinstance(diff, (int, float)):
            continue
        th = rt.get_threshold(field)
        if not th:
            continue
        ratio = abs(diff) / th
        if ratio > best_ratio or (ratio == best_ratio and rt.CITY_RANK.get(city, 9999) > rt.CITY_RANK.get(best['city'], 9999) if best else True):
            best_ratio = ratio
            best = {'city': city, 'field': field, 'dev': round(diff, 2), 'ratio': round(ratio, 1)}
    return best
