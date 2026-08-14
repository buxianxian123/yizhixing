#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收核心：平台一致率 == 现有 gen_xlsx→read_summary 口径（逐格相等）。

对多个筛选条件，断言平台 summary_rows 与 gen_xlsx 生成的 xlsx「总结」sheet
逐行相等（rate/ok/valid/miss/clean/avg/max/maxCity）。

运行:
  /usr/local/bin/python3.13 web/tests/test_parity.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # web/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # proto版/

import openpyxl  # noqa: E402
import reformat_threshold as rt  # noqa: E402
import db_helper  # noqa: E402

from repository import points as repo_points  # noqa: E402
from services import filters as svc_filters  # noqa: E402
from services import compare as svc_compare  # noqa: E402
from services import aggregation as svc_agg  # noqa: E402


def _platform_summary(fs):
    """平台 summary_rows（逐格）。"""
    conn = db_helper.get_conn()
    try:
        pts, pulls = repo_points.read_points(conn, fs)
    finally:
        conn.close()
    results = svc_compare.compare_points(pts)
    return svc_agg.summary_rows(results), pulls


def _xlsx_summary(fs):
    """gen_xlsx 生成的 xlsx 总结 sheet 逐行。"""
    conn = db_helper.get_conn()
    try:
        pts, pulls = repo_points.read_points(conn, fs)
    finally:
        conn.close()
    results = svc_compare.compare_points(pts)
    results10 = [r[1:] for r in results]
    pull_count = len(pulls) or 1
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        xlsx = tmp.name
    try:
        rt.gen_xlsx(results10, f'阈值口径({pull_count}次拉取逐条)', xlsx)
        wb = openpyxl.load_workbook(xlsx, read_only=True)
        ws = wb['总结']
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
    finally:
        os.remove(xlsx)
    # 表头: 字段 模块 时效 总数据 缺数据 清洗剔除 有效样本 一致数 一致率 平均偏差 最大偏差 最大偏差城市
    out = []
    for r in rows[1:]:
        if r is None or r[0] is None:
            continue
        out.append({
            'field': r[0], 'module': r[1], 'period': r[2] or '',
            'total': r[3], 'miss': r[4], 'clean': r[5], 'valid': r[6],
            'ok': r[7], 'rate': r[8], 'avg': r[9], 'max': r[10], 'max_city': r[11],
        })
    return out, pulls


def _norm(v):
    """归一化比较：数字字符串统一。"""
    return str(v)


def check(fs, label):
    plat, pulls_p = _platform_summary(fs)
    xlsx, pulls_x = _xlsx_summary(fs)
    assert len(pulls_p) == len(pulls_x), f'{label}: pulls 数量不一致 {len(pulls_p)} vs {len(pulls_x)}'

    def key(r):
        return (r['field'], r['module'], r['period'])

    plat_map = {key(r): r for r in plat}
    xlsx_map = {key(r): r for r in xlsx}
    assert set(plat_map) == set(xlsx_map), f'{label}: 键集合不一致\n  平台多: {set(plat_map) - set(xlsx_map)}\n  xlsx多: {set(xlsx_map) - set(plat_map)}'

    # 平台行 key: avg_dev/max_dev/max_city；xlsx 行 key: avg/max/max_city
    col_map = {'total': 'total', 'miss': 'miss', 'clean': 'clean',
               'valid': 'valid', 'ok': 'ok', 'rate': 'rate',
               'avg': 'avg_dev', 'max': 'max_dev', 'max_city': 'max_city'}
    diffs = []
    for k in plat_map:
        a, b = plat_map[k], xlsx_map[k]
        for col in ('total', 'miss', 'clean', 'valid', 'ok', 'rate', 'avg', 'max', 'max_city'):
            if _norm(a.get(col_map[col])) != _norm(b.get(col)):
                diffs.append((k, col, a.get(col_map[col]), b.get(col)))
    assert not diffs, f'{label}: 逐格不一致 {len(diffs)} 处，前5: {diffs[:5]}'
    print(f'  ✅ {label}: {len(plat)} 行逐格一致 (pulls={len(pulls_p)})')


def main():
    rt.load_cities()
    cases = [
        (svc_filters.FilterSpec(date_start='20260812', date_end='20260812'), '整日 2026-08-12'),
        (svc_filters.FilterSpec(pulls=['2026-08-12 08:46:00']), '单批次 2026-08-12 08:46:00'),
        (svc_filters.FilterSpec(date_start='20260811', date_end='20260812', cities=['北京市', '上海市']), '日期+城市子集'),
        (svc_filters.FilterSpec(date_start='20260812', date_end='20260812', modules=['实况', 'AQI模块']), '模块子集 实况+AQI'),
    ]
    print('=== 平台一致率 vs gen_xlsx 逐格一致性校验 ===')
    for fs, label in cases:
        check(fs, label)
    print('\n🎉 全部通过：平台聚合口径与现有 xlsx/MD 完全一致')


if __name__ == '__main__':
    main()
