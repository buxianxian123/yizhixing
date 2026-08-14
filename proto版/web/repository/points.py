#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 DB 读取比对点（Pt）。

与 gen_report_from_csv._read_module_from_db 逐字对齐（口径一致），但支持：
  - 批次精确(pulls) / 日期范围(date_range) / 城市(cities) / 模块(modules) / 时效(periods) 过滤
  - 返回 11 元组 Pt = (pull_at, city, module, field, ts, cn_v, iv_v, period)

⚠️ 关键口径：
  - 24h 时效分段在读取层计算（base_ts=组内第一行 updatetime_cn，period=rt.get_period_label）
  - is_missing=1 → cn_v=iv_v=None
  - 不做任何单位换算（风速换算全交给 rt.cmp_point，避免双 ÷3.6）
  - 绝不做 SELECT *，只投影需要的列
"""
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config  # noqa: E402
import db_helper  # noqa: E402
import reformat_threshold as rt  # noqa: E402


class TooManyPoints(Exception):
    """读取点数超过 MAX_POINTS 守卫。"""


def read_points(conn, fs):
    """按筛选条件读取比对点。

    fs: services.filters.FilterSpec
    返回 (Pt 列表, pulls 集合)。Pt = (pull_at, city, module, field, ts, cn_v, iv_v, period)
    """
    modules = fs.modules or list(rt.MODULES.keys())
    pulls = fs.pulls            # list[str] or None
    date_range = fs.date_range  # (start_YYYYMMDD, end_YYYYMMDD) or None
    cities = fs.cities          # list[str] or None (已与 valid 求交集)
    periods = fs.periods        # list[str] or None，仅作用于 24h

    all_pts = []
    all_pulls = set()

    for module in modules:
        mspec = rt.MODULES.get(module)
        if mspec is None:
            continue
        pts, pulls_set = _read_module(conn, module, mspec, pulls, date_range, cities, periods)
        all_pts.extend(pts)
        all_pulls.update(pulls_set)

        if len(all_pts) > config.MAX_POINTS:
            raise TooManyPoints(
                f"结果量 {len(all_pts)} 超过上限 {config.MAX_POINTS}，请缩小批次/城市范围")

    return all_pts, all_pulls


def _read_module(conn, module, mspec, pulls, date_range, cities, periods):
    """读取单个模块的比对点（对齐 gen_report_from_csv._read_module_from_db）。"""
    table_map = db_helper.MODULE_TABLE_MAP[module]
    table = table_map['table']
    ts_col = table_map['ts_col']
    fields = mspec['fields']
    source = mspec['source']

    # 可比对字段（跳过 compare: false 和无列映射的）
    comp_fields = {}
    for fname, spec in fields.items():
        if spec.get('compare') is False:
            continue
        col_map = table_map['fields'].get(fname)
        if not col_map:
            continue
        cn_col, intl_col = col_map
        comp_fields[fname] = (cn_col, intl_col, spec)
    if not comp_fields:
        return [], set()

    # ---- WHERE 条件 ----
    conds = []
    params = []
    if pulls:
        conds.append(f"pull_at IN ({','.join('?' * len(pulls))})")
        params.extend(pulls)
    elif date_range:
        # YYYYMMDD -> YYYY-MM-DD (与 substr(pull_at,1,10) 格式对齐)
        def _d(s):
            return f'{s[:4]}-{s[4:6]}-{s[6:8]}' if s and len(s) == 8 else s
        conds.append("substr(pull_at,1,10) BETWEEN ? AND ?")
        params.extend([_d(date_range[0]), _d(date_range[1])])
    if cities:
        conds.append(f"city_name IN ({','.join('?' * len(cities))})")
        params.extend(cities)
    where = ' AND '.join(conds) if conds else '1=1'

    # ---- 列投影（绝不全表） ----
    select_cols = ['pull_at', 'city_name', 'is_missing']
    if ts_col:
        select_cols.append(ts_col)
    if source == 'hourly':
        select_cols.extend(['predict_time_cn', 'updatetime_cn'])
    for fname, (cn_col, intl_col) in table_map['fields'].items():
        if fname in comp_fields:
            select_cols.append(cn_col)
            select_cols.append(intl_col)

    sql = f"SELECT {', '.join(select_cols)} FROM {table} WHERE {where}"
    if source == 'hourly':
        sql += " ORDER BY pull_at, city_name, ts_utc IS NULL, ts_utc"
    elif source == 'daily':
        sql += " ORDER BY pull_at, city_name, local_date IS NULL, local_date"
    else:
        sql += " ORDER BY pull_at, city_name"

    rows = conn.execute(sql, params).fetchall()

    pts = []
    pulls_set = set()

    if source == 'hourly':
        groups = defaultdict(list)
        for row in rows:
            groups[(row['pull_at'], row['city_name'])].append(row)
            pulls_set.add(row['pull_at'])

        for (wt, city), grp in groups.items():
            # base_ts 取组内第一行 updatetime_cn（与 gen_report_from_csv 一致）
            base_ts = None
            ut_str = grp[0]['updatetime_cn'] if grp else None
            if ut_str:
                try:
                    base_ts = datetime.strptime(ut_str, '%Y-%m-%d %H:%M:%S').replace(
                        tzinfo=timezone.utc).timestamp()
                except Exception:
                    pass

            for idx, row in enumerate(grp):
                predict_ts = None
                pred_str = row['predict_time_cn']
                if pred_str:
                    try:
                        predict_ts = datetime.strptime(pred_str, '%Y-%m-%d %H:%M:%S').replace(
                            tzinfo=timezone.utc).timestamp()
                    except Exception:
                        pass
                period = rt.get_period_label(source, idx, base_ts, predict_ts)
                if not period:
                    continue
                # 时效过滤（仅作用于 24h）
                if periods and period not in periods:
                    continue

                ts = row[ts_col] or ''
                for fname, (cn_col, intl_col, spec) in comp_fields.items():
                    cn_v = row[cn_col] if not row['is_missing'] else None
                    iv_v = row[intl_col] if not row['is_missing'] else None
                    pts.append((wt, city, module, fname, ts, cn_v, iv_v, period))
    else:
        for row in rows:
            wt = row['pull_at']
            city = row['city_name']
            pulls_set.add(wt)

            if ts_col:
                ts = row[ts_col] or ''
            else:
                ts = wt or mspec.get('ts_label', '')

            for fname, (cn_col, intl_col, spec) in comp_fields.items():
                cn_v = row[cn_col] if not row['is_missing'] else None
                iv_v = row[intl_col] if not row['is_missing'] else None
                pts.append((wt, city, module, fname, ts, cn_v, iv_v, ''))

    return pts, pulls_set
