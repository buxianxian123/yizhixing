#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元数据查询：批次 / 日期 / 城市 / 模块 / 字段 / 地区树。

全部走索引的小查询，毫秒级。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config  # noqa: E402
import reformat_threshold as rt  # noqa: E402
from repository.connection import get_conn  # noqa: E402


def get_pulls(conn=None):
    """批次列表：SELECT DISTINCT pull_at FROM current_weather（唯一权威来源）。

    注意：不能用 pull_round（只有 8/11 后 24 条，早期 CSV 迁移数据无记录）。
    """
    own = conn is None
    if own:
        conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT pull_at FROM current_weather ORDER BY pull_at").fetchall()
        return [r[0] for r in rows]
    finally:
        if own:
            conn.close()


def get_dates(conn=None):
    """日期列表：按天去重（YYYY-MM-DD）。"""
    pulls = get_pulls(conn)
    return sorted({p[:10] for p in pulls})


def get_cities(conn=None):
    """城市列表：name + 经纬度 + 分类，从 city 表读。"""
    own = conn is None
    if own:
        conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT fcityname_cn, flon, flat, category FROM city ORDER BY fcity").fetchall()
        return [{'name': r[0], 'lon': r[1], 'lat': r[2], 'category': r[3]} for r in rows]
    finally:
        if own:
            conn.close()


def get_modules():
    """模块列表（带展示名与 compare 字段）。"""
    out = []
    for m, mspec in rt.MODULES.items():
        fields = [f for f, s in mspec['fields'].items() if s.get('compare') is not False]
        out.append({'name': m, 'display': config.MODULE_DISPLAY.get(m, m), 'fields': fields})
    return out


def get_fields():
    """所有比对字段（去重，按 FIELD_ORDER 排序）。"""
    seen = []
    for m in rt.MODULES.values():
        for f, s in m['fields'].items():
            if s.get('compare') is not False and f not in seen:
                seen.append(f)
    return sorted(seen, key=lambda x: config.FIELD_ORDER.index(x) if x in config.FIELD_ORDER else 99)


def get_periods():
    return config.PERIOD_DISPLAY


def get_region_tree():
    """地区三级联动树：国 › 省 › 城市（读 city_region.json）。"""
    try:
        with open(config.REGION_JSON, encoding='utf-8') as f:
            region = json.load(f)
    except Exception:
        region = {}
    tree = {}
    for city, (country, prov) in region.items():
        tree.setdefault(country, {}).setdefault(prov, []).append(city)
    countries = [{'name': c, 'provs': [{'name': p, 'cities': sorted(cs)}
                                       for p, cs in sorted(tree[c].items())]}
                 for c in sorted(tree.keys())]
    return {'countries': countries}


def get_meta():
    conn = get_conn()
    try:
        pulls = get_pulls(conn)
        dates = get_dates(conn)
        cities = get_cities(conn)
    finally:
        conn.close()
    modules = get_modules()
    last_pull_at = pulls[-1] if pulls else None
    return {
        'dates': dates,
        'pulls': [{'pull_at': p, 'date': p[:10], 'hour': p[11:16]} for p in pulls],
        'cities': cities,
        'modules': modules,
        'fields': get_fields(),
        'periods': get_periods(),
        'last_pull_at': last_pull_at,
        'total_pulls': len(pulls),
        'total_cities': len(cities),
    }
