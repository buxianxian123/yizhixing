#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从数据库生成一致性报告 (xlsx + md)。

数据源: data/weather_data.db (替代 CSV 留底)
链路:   读DB -> cmp_point逐条比对 -> gen_xlsx -> gen_md_report
       逐次比对: 每次拉取的每条数据独立比对, 统计按有效样本加和, 不做先均值后比对。

运行:
  python3 gen_report_from_csv.py             # 全部日期
  python3 gen_report_from_csv.py 20260803    # 指定日期
  python3 gen_report_from_csv.py 3           # 最近3天
"""
import os, sys
from collections import defaultdict
from datetime import datetime, timezone
import reformat_threshold as rt
import db_helper


def _read_module_from_db(conn, module, mspec, date_dirs):
    """从数据库读取一个模块的数据 -> (比对点列表, 写入时间集合)。
    比对点为 10 元组(city, module, field, ts, cn_raw, iv_raw, '', '', '', period)。

    24h: 按(pull_at,城市)分组、按 ts_utc 排序, 用 updatetime_cn 算时效分段。
    单值模块(实况/AQI): 用 pull_at 作时次区分, 保留每次拉取样本。
    """
    table_map = db_helper.MODULE_TABLE_MAP[module]
    table = table_map['table']
    ts_col = table_map['ts_col']
    fields = mspec['fields']
    source = mspec['source']

    # 构建可比对字段列表 (跳过 compare: false)
    comp_fields = {}
    for fname, spec in fields.items():
        if spec.get('compare') is False:
            continue
        cn_col, intl_col = table_map['fields'][fname]
        comp_fields[fname] = (cn_col, intl_col, spec)
    if not comp_fields:
        return [], set()

    # 日期过滤
    conditions = ' OR '.join(['substr(pull_at,1,10) = ?' for _ in date_dirs])
    params = [f'{d[:4]}-{d[4:6]}-{d[6:8]}' for d in date_dirs]

    # 查询列: 基础列 + 时间列 + 字段列
    select_cols = ['pull_at', 'city_name', 'is_missing']
    if ts_col:
        select_cols.append(ts_col)
    if source == 'hourly':
        select_cols.extend(['predict_time_cn', 'updatetime_cn'])
    for fname, (cn_col, intl_col) in table_map['fields'].items():
        if fname in comp_fields:
            select_cols.append(cn_col)
            select_cols.append(intl_col)

    sql = f"SELECT {', '.join(select_cols)} FROM {table} WHERE {conditions}"
    if source == 'hourly':
        # NULL 排在最后 (与 CSV '缺数据' 排序行为一致)
        sql += " ORDER BY pull_at, city_name, ts_utc IS NULL, ts_utc"
    elif source == 'daily':
        sql += " ORDER BY pull_at, city_name, local_date IS NULL, local_date"
    else:
        sql += " ORDER BY pull_at, city_name"

    cur = conn.execute(sql, params)
    rows = cur.fetchall()

    pts = []
    pulls = set()

    if source == 'hourly':
        groups = defaultdict(list)
        for row in rows:
            wt = row['pull_at']
            city = row['city_name']
            groups[(wt, city)].append(row)
            pulls.add(wt)

        for (wt, city), grp in groups.items():
            # 从第一行取 updatetime_cn 算 base_ts
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

                ts = row['ts_utc'] or ''
                for fname, (cn_col, intl_col, spec) in comp_fields.items():
                    cn_v = row[cn_col] if not row['is_missing'] else None
                    iv_v = row[intl_col] if not row['is_missing'] else None
                    pts.append((city, module, fname, ts, cn_v, iv_v, '', '', '', period))
    else:
        for row in rows:
            wt = row['pull_at']
            city = row['city_name']
            pulls.add(wt)

            if ts_col:
                ts = row[ts_col] or ''
            else:
                ts = wt or mspec.get('ts_label', '')

            for fname, (cn_col, intl_col, spec) in comp_fields.items():
                cn_v = row[cn_col] if not row['is_missing'] else None
                iv_v = row[intl_col] if not row['is_missing'] else None
                pts.append((city, module, fname, ts, cn_v, iv_v, '', '', '', ''))

    return pts, pulls


def read_db_points(conn, date_dirs):
    """读多个日期的数据库数据 -> (比对点列表, 拉取份数集合)"""
    pts = []
    pulls = set()
    for module, mspec in rt.MODULES.items():
        fp, fw = _read_module_from_db(conn, module, mspec, date_dirs)
        pts.extend(fp)
        pulls.update(fw)
    return pts, pulls


def main():
    conn = db_helper.get_conn()

    # 获取所有有数据的日期
    all_dates = db_helper.get_all_dates(conn)
    if not all_dates:
        # 回退: 从 current_weather 查日期
        cur = conn.execute(
            "SELECT DISTINCT substr(pull_at,1,10) AS d FROM current_weather ORDER BY d")
        all_dates = [r[0].replace('-', '') for r in cur.fetchall() if r[0]]

    if not all_dates:
        print('❌ 数据库无数据')
        conn.close()
        return

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        date_dirs = all_dates
    elif arg.isdigit() and len(arg) == 8:
        date_dirs = [arg] if arg in all_dates else []
    elif arg.isdigit():
        n = int(arg)
        date_dirs = all_dates[-n:] if 0 < n < len(all_dates) else all_dates
    else:
        date_dirs = all_dates

    if not date_dirs:
        print(f'❌ 选中的日期无数据: {arg}')
        conn.close()
        return

    print(f'数据源: {db_helper.DB_PATH}')
    print(f'日期: {date_dirs}')

    cities = rt.load_cities()
    valid = set(c[0] for c in cities)

    pts, pulls = read_db_points(conn, date_dirs)
    conn.close()
    print(f'读出 {len(pts)} 个比对点, {len(pulls)} 次拉取')
    if not pts:
        print('❌ 无有效数据')
        return

    # 逐次比对
    all_pts = []
    for pt in pts:
        city, module, field, ts, cn_v, iv_v, _, _, _, period = pt
        spec = rt.MODULES.get(module, {}).get('fields', {}).get(field, {})
        if not spec:
            continue
        result = rt.cmp_point(city, module, field, ts, cn_v, iv_v, spec, period)
        all_pts.append(result)

    threshold_pts = [p for p in all_pts if p[0] in valid]
    pull_count = len(pulls) or 1
    print(f'逐次比对 {pull_count} 次拉取, {len(threshold_pts)} 个数据点')

    window_start, window_end = date_dirs[0], date_dirs[-1]
    tag = f'{pull_count}次拉取_{window_start}-{window_end}_db'
    xlsx_path = os.path.join(rt.OUT_DIR, f'一致性比对报告_逐次比对_阈值口径_{tag}.xlsx')
    extra = [
        f'本报告从数据库生成: {pull_count} 次拉取逐条比对 (与参考版口径一致)',
        f'日期范围: {window_start} ~ {window_end}',
        f'数据源: data/weather_data.db (pull_latest_round.py 写入)',
        '统计方法: 每次拉取的每条数据独立比对后汇总, 不做先均值后比对',
        '风速: 海外值 ÷3.6 换算为 m/s 后比对',
        '天气现象: 按语义映射大类比对, 未识别天气按缺数据处理',
    ]
    n = rt.gen_xlsx(threshold_pts, f'阈值口径({pull_count}次拉取逐条)', xlsx_path, extra_notes=extra)
    print(f'\n✅ xlsx: {os.path.basename(xlsx_path)} ({n} 数据点)')

    # md
    import subprocess
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, 'gen_md_report.py'), xlsx_path])
    if r.returncode != 0:
        print('⚠️ gen_md_report 生成失败')

    # 一致率速览
    print(f"\n{'='*60}\n阈值口径(DB逐次比对) - 各字段一致率速览\n{'='*60}")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_path)
        ws = wb['总结']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] and not row[2]:
                print(f"  {str(row[0]):14s} {str(row[1]):8s}  一致率: {str(row[8]):>7s}  平均偏差: {str(row[9]):>8s}")
    except Exception:
        pass


if __name__ == '__main__':
    main()
