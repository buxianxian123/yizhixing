#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告生成：复用现有 gen_md_report.py，口径与旧 CLI 完全一致。

链路：筛选 → read_points → compare_points → rt.gen_xlsx(临时xlsx) → import gen_md_report
       read_summary/read_top5/read_thresholds/read_meta/parse_avg_count/parse_sample + build_md → md

重要：
  - 临时 xlsx 文件名必须固定格式 `一致性比对报告_逐次比对_阈值口径_{N}次拉取_{start}-{end}_db.xlsx`
    （gen_md_report 从文件名解析批次/日期）
  - 城市子集时 gen_xlsx 说明 sheet 写实际城市数 → read_meta 自动正确
  - 不 subprocess（gen_md_report.main 会写根目录）；import 后 build_md 直接返回字符串
"""
import os
import re
import sys
import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config  # noqa: E402
import reformat_threshold as rt  # noqa: E402
import gen_md_report as gmd  # noqa: E402

from repository.connection import get_conn  # noqa: E402
from repository import points as repo_points  # noqa: E402
from services import compare as svc_compare  # noqa: E402
from services import aggregation as svc_agg  # noqa: E402


def _build_report_data(fs):
    """按筛选读数据 → 比对 → 返回 results(11元组) 和 pulls。"""
    conn = get_conn()
    try:
        pts, pulls = repo_points.read_points(conn, fs)
    finally:
        conn.close()
    results = svc_compare.compare_points(pts)
    results10 = [r[1:] for r in results]
    return results10, results, pulls


def _xlsx_name(fs, pulls):
    """生成匹配 gen_md_report 解析的 xlsx 文件名。"""
    pull_count = len(pulls) or 1
    dates = sorted({p[:10].replace('-', '') for p in pulls})
    if dates:
        start, end = dates[0], dates[-1]
    else:
        start = end = (fs.date_start or fs.date_end or '')
    return f'一致性比对报告_逐次比对_阈值口径_{pull_count}次拉取_{start}-{end}_db.xlsx'


def build_report_view(fs):
    """交互式「完整表格视图」（不落盘）：返回 (md, tables[], meta)。

    tables: [{id, title, html}]，由服务端把 md 的 | 表格转真 HTML <table>。
    """
    results10, results, pulls = _build_report_data(fs)
    if not results10:
        # 空数据：返回空视图，避免 gen_md_report.build_md 对空 summary 崩溃
        return '', [], {
            'cities': 0, 'pulls': len(pulls), 'sample': _sample_str(fs, pulls),
            'koujing': '阈值口径',
            'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'filter_snapshot': fs.snapshot(), 'empty': True,
        }
    md = _render_md(fs, results10, pulls)
    tables = _md_to_tables(md)
    meta = {
        'cities': len({r[1] for r in results}) if results else 0,
        'pulls': len(pulls),
        'sample': _sample_str(fs, pulls),
        'koujing': '阈值口径',
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'filter_snapshot': fs.snapshot(),
    }
    return md, tables, meta


def generate_report(fs):
    """生成报告落盘 web/report/，返回 {id, md, md_url, xlsx_url, generated_at, filter_snapshot}。"""
    results10, results, pulls = _build_report_data(fs)
    if not results10:
        raise ValueError('当前筛选条件下无数据，无法生成报告，请调整筛选条件')
    rid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]
    os.makedirs(config.REPORT_DIR, exist_ok=True)

    xlsx_name = _xlsx_name(fs, pulls)
    xlsx_path = os.path.join(config.REPORT_DIR, xlsx_name)
    # 标题含批次/日期（gen_xlsx 用 title 解析拉取次数）
    pull_count = len(pulls) or 1
    title = f'阈值口径({pull_count}次拉取逐条)'
    extra_notes = [
        f'本报告由平台生成',
        f'筛选条件: 日期 {fs.date_start or "-"} ~ {fs.date_end or "-"}；批次 {len(pulls)} 个；城市 {len(set(r[1] for r in results))} 个；'
        f'模块 {fs.modules or "全部"}；时效 {fs.periods or "全部"}',
        f'城市子集: {", ".join(sorted(set(r[1] for r in results))[:20]) if results else "-"}{" 等" if results and len(set(r[1] for r in results)) > 20 else ""}',
    ]
    rt.gen_xlsx(results10, title, xlsx_path, extra_notes=extra_notes)

    md = _render_md(fs, results10, pulls)
    md_name = f'一致性比对报告_{rid}.md'
    md_path = os.path.join(config.REPORT_DIR, md_name)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)

    return {
        'id': rid,
        'md': md,
        'md_url': f'/report/{md_name}',
        'xlsx_url': f'/report/{xlsx_name}',
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'filter_snapshot': fs.snapshot(),
    }


# ============ 内部：渲染 md ============

def _render_md(fs, results10, pulls):
    """复用 gen_md_report.build_md：先跑 aggregate_stats 构造 summary/top5/weather_pairs。"""
    # 构造与 gen_md_report.read_summary 同 schema 的 summary 行
    summary = svc_agg.summary_rows_from_10(results10)
    top5 = svc_agg.top5_rows_from_10(results10)
    thresholds, rain_th, clean_ranges = gmd.read_thresholds()

    # 天气TOP对（大类不一致前5，与 gen_xlsx 天气TOP对 sheet 同口径）
    weather_pairs = svc_agg.weather_pairs_from_10(results10)

    # meta：cities 用实际城市数，avg_count 用 len(pulls)
    cities = len({r[0] for r in results10}) or 0
    meta = {
        'time': _sample_str(fs, pulls),
        'source': '平台生成',
        'koujing': '阈值口径',
        'cities': cities,
        'sample': _sample_str(fs, pulls),
        'avg_count': len(pulls) or 1,
    }
    md = gmd.build_md(summary, top5, thresholds, rain_th, meta, weather_pairs, clean_ranges)
    return md


def _sample_str(fs, pulls):
    """采样区间文本（与 gen_md_report.parse_sample 输出风格一致）。"""
    dates = sorted({p[:10] for p in pulls})
    if dates:
        return f'{dates[0]} ~ {dates[-1]}，{len(pulls)} 次拉取逐条比对'
    return f'{fs.date_start or "-"} ~ {fs.date_end or "-"}，{len(pulls)} 次拉取逐条比对'


# ============ md → HTML 表格 ============

def _md_to_tables(md):
    """把 markdown 的管道表格转成真 HTML <table>。

    返回 [{id, title, html}]。title 取表格前最近的标题行。
    不重新计算任何数据，只保留表头/列序/单元格文本。
    """
    tables = []
    current_title = ''
    lines = md.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith('#'):
            current_title = line.lstrip('#').strip()
            i += 1
            continue
        if line.startswith('|'):
            # 收集连续表格行
            block = []
            while i < n and lines[i].startswith('|'):
                block.append(lines[i])
                i += 1
            html = _table_block_to_html(block)
            if html:
                tables.append({'id': f'tab{len(tables) + 1}',
                               'title': current_title, 'html': html})
            continue
        i += 1
    return tables


def _table_block_to_html(block):
    """管道表格块 → <table>（首行为表头，跳过分隔行 |---|）。"""
    lines = [b.strip() for b in block if b.strip()]
    if not lines:
        return None
    header = _split_pipe(lines[0])
    rows = []
    for ln in lines[1:]:
        cells = _split_pipe(ln)
        # 分隔行 |---|---| 跳过
        if all(re.fullmatch(r':?-{1,}:?', c.strip()) for c in cells if c.strip()):
            continue
        rows.append(cells)
    if not header:
        return None
    thead = '<tr>' + ''.join(f'<th>{_esc(h)}</th>' for h in header) + '</tr>'
    tbody = ''.join('<tr>' + ''.join(f'<td>{_esc(c)}</td>' for c in r) + '</tr>' for r in rows)
    return f'<table class="md-table"><thead>{thead}</thead><tbody>{tbody}</tbody></table>'


def _split_pipe(line):
    """按 | 拆分 markdown 行（去掉首尾空）。"""
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))
