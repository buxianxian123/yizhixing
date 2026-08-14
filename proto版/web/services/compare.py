#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把比对点 Pt 逐条喂给 rt.cmp_point → CompareResult。

CompareResult = (pull_at, *cmp_point 10元组)
  = (pull_at, city, module, field, ts, cn_v, iv_v, diff, ok, note, period)

对齐 gen_report_from_csv.main 的口径：
  - spec 缺失的字段跳过
  - 只保留 valid 城市（city in rt.CITY_RANK）
  - 风速换算/天气映射/清洗全部由 rt.cmp_point 完成，这里不做任何处理
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import reformat_threshold as rt  # noqa: E402


def compare_points(pts):
    """Pt 列表 → CompareResult 列表（含 valid 城市过滤）。"""
    # valid 城市 = CITY_RANK 的键（rt.load_cities 已设置；独立脚本防御性加载）
    if not rt.CITY_RANK:
        try:
            rt.load_cities()
        except Exception:
            pass
    valid = set(rt.CITY_RANK.keys())
    results = []
    for pt in pts:
        pull_at, city, module, field, ts, cn_v, iv_v, period = pt
        spec = rt.MODULES.get(module, {}).get('fields', {}).get(field)
        if spec is None:
            continue
        res = rt.cmp_point(city, module, field, ts, cn_v, iv_v, spec, period)
        # res = (city, module, field, ts, cnv, iv, diff, ok, note, period)
        if city in valid:
            results.append((pull_at,) + res)
    return results
