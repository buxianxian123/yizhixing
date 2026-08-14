#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 raw_pull JSON 留底重算某天的 CSV(按当前最新配置) —— 修复历史配置变更导致的列错位。

用法:
  python3 rebuild_day_csv.py 20260803     # 重算指定日期(旧文件备份)
  python3 rebuild_day_csv.py 20260803 --dry-run   # 先看会做什么, 不改文件

数据源: data/原始拉取/原始_<ts>/<城市>/国内.json + 国际.json (raw_pull.py 留底)
输出:   data/原始数据csv/<日期>/<模块>_<日期>.csv (当前配置表头, 全量干净)
旧文件: 备份为 <模块>_<日期>_pre_rebuild_<时间戳>.csv

与 convert_raw_to_csv.py 同逻辑(normalize + _match_utc + UTC对齐), 只是按日期过滤、
只写一天的文件, 并带备份。纯读JSON留底, 不拉接口。
"""
import os, sys, json, glob, csv, datetime, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reformat_threshold as rt
from fetch_cn_pb import normalize_cn, normalize_in
from convert_raw_to_csv import _match_utc, fmt_val, MATCH_TOLERANCE, build_header
from convert_raw_to_csv import RAW_DIR, BASE_OUT

DRY_RUN = '--dry-run' in sys.argv


def iter_rounds_for_date(date_str):
    """遍历原始拉取目录, 找出属于指定日期(当地日期, 按轮次目录名的年月日)的轮次。
    返回 [(轮次目录, pull_at_str), ...] 按时间排序。"""
    ymd = date_str
    rounds = []
    for rd in sorted(glob.glob(os.path.join(RAW_DIR, '原始_*'))):
        base = os.path.basename(rd).replace('原始_', '')
        # 目录名形如 20260803_104831
        if len(base) >= 8 and base[:8] == ymd:
            rounds.append(rd)
    return rounds


def pull_at_from_dir(rd):
    manifest = os.path.join(rd, '_manifest.json')
    if os.path.exists(manifest):
        try:
            d = json.load(open(manifest, encoding='utf-8'))
            if d.get('pull_at'):
                return d['pull_at']
        except Exception:
            pass
    base = os.path.basename(rd).replace('原始_', '')
    if len(base) >= 13:
        return f'{base[:4]}-{base[4:6]}-{base[6:8]} {base[9:11]}:{base[11:13]}:00'
    return base


def build_module_rows(module, mspec, cities, rounds):
    """对一个模块, 遍历所有轮次所有城市, 输出行列表和已见key集合。"""
    source = mspec['source']
    fields = mspec['fields']
    multi = mspec.get('multi')
    limit = mspec.get('limit', 99)
    ts_local_key = 'predict_time' if source == 'hourly' else 'predict_date'

    rows = []
    seen = set()

    for rd in rounds:
        pull_at = pull_at_from_dir(rd)
        ok_city = 0
        for name, lon, lat in cities:
            cn_path = os.path.join(rd, name, '国内.json')
            intl_path = os.path.join(rd, name, '国际.json')
            if not (os.path.exists(cn_path) and os.path.exists(intl_path)):
                continue
            try:
                cn_raw = json.load(open(cn_path, encoding='utf-8'))
                intl_raw = json.load(open(intl_path, encoding='utf-8'))
            except Exception:
                continue
            if isinstance(intl_raw, dict) and 'data' in intl_raw and 'current' not in intl_raw:
                intl_raw = intl_raw['data']
            try:
                cn = normalize_cn(cn_raw)
                tz_hours = cn.get('_meta', {}).get('timezone')
                intl = normalize_in(intl_raw, tz_hours=tz_hours)
            except Exception:
                continue
            ok_city += 1

            if multi:
                cn_arr = cn.get(source, [])
                intl_arr = intl.get(source, [])[:limit]
                if source == 'daily':
                    intl_map = {b.get(ts_local_key): b for b in intl_arr if b.get(ts_local_key)}
                    for a in cn_arr:
                        local_ts = a.get(ts_local_key)
                        if not local_ts or local_ts not in intl_map:
                            continue
                        b = intl_map[local_ts]
                        dedup_key = (pull_at, name, local_ts)
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)
                        row = [pull_at, name, local_ts, a.get('_utc'), b.get('_utc'),
                               a.get(ts_local_key), b.get(ts_local_key)]
                        for fname, spec in fields.items():
                            row.append(fmt_val(a.get(spec['cn'])))
                            row.append(fmt_val(b.get(spec['intl'])))
                        rows.append(row)
                else:  # hourly
                    for a in cn_arr:
                        b, diff_sec = _match_utc(a.get('_utc'), intl_arr)
                        if b is None:
                            continue
                        utc_ts = a.get('_utc')
                        dedup_key = (pull_at, name, utc_ts)
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)
                        row = [pull_at, name, utc_ts, a.get('_utc'), b.get('_utc'),
                               a.get(ts_local_key), b.get(ts_local_key)]
                        for fname, spec in fields.items():
                            row.append(fmt_val(a.get(spec['cn'])))
                            row.append(fmt_val(b.get(spec['intl'])))
                        rows.append(row)
            else:  # 单值模块
                cn_mod = cn.get(source, {}) or {}
                intl_mod = intl.get(source, {}) or {}
                dedup_key = (pull_at, name)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                row = [pull_at, name]
                for fname, spec in fields.items():
                    row.append(fmt_val(cn_mod.get(spec['cn'])))
                    row.append(fmt_val(intl_mod.get(spec['intl'])))
                rows.append(row)
    return rows


def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit() or len(sys.argv[1]) != 8:
        print('用法: python3 rebuild_day_csv.py <YYYYMMDD> [--dry-run]')
        return
    date_str = sys.argv[1]

    cities = rt.load_cities()
    rounds = iter_rounds_for_date(date_str)
    print(f'日期: {date_str}')
    print(f'找到 {len(rounds)} 轮原始拉取:')
    for r in rounds[:5]:
        print(f'  {os.path.basename(r)}')
    if len(rounds) > 5:
        print(f'  ... 共 {len(rounds)} 轮')
    if not rounds:
        print('❌ 当天无原始拉取, 无法重算')
        return

    out_dir = os.path.join(BASE_OUT, date_str)
    if DRY_RUN:
        print('\n[--dry-run] 不写文件, 只打印各模块行数预览')
    else:
        os.makedirs(out_dir, exist_ok=True)

    now_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    for module, mspec in rt.MODULES.items():
        rows = build_module_rows(module, mspec, cities, rounds)
        header = build_header(module, mspec)
        out_path = os.path.join(out_dir, f'{module}_{date_str}.csv')
        print(f'\n{module}: {len(rows)} 行, 表头 {len(header)} 列')

        if not rows:
            print(f'  ⚠️ 无数据, 跳过')
            continue

        if DRY_RUN:
            print(f'  预览: {out_path}')
            continue

        # 旧文件备份
        if os.path.exists(out_path):
            bak = out_path.replace('.csv', f'_pre_rebuild_{now_ts}.csv')
            shutil.move(out_path, bak)
            print(f'  旧文件备份: {os.path.basename(bak)}')

        with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f'  ✅ 写入: {os.path.basename(out_path)} ({len(rows)} 行)')

    print(f'\n{"[dry-run] 完成" if DRY_RUN else "重算完成"}: {BASE_OUT}/{date_str}/')


if __name__ == '__main__':
    main()
