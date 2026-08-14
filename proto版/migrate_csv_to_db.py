#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性迁移: 将 data/原始数据csv/ 下所有 CSV 导入 SQLite 数据库。

导入内容:
  1. 城市列表 CSV -> city 表
  2. 各模块 CSV (实况/24小时/15天/AQI/短时/预警) -> 对应表

处理:
  - '缺数据' 标记行 -> is_missing=1, 数据列全部 NULL
  - 空串 -> NULL
  - 数字字符串 -> float
  - 文字 -> str
  - _bak_* 备份文件跳过
  - INSERT OR IGNORE 去重 (与 CSV 的去重逻辑一致)

运行: python3 migrate_csv_to_db.py
"""
import os
import csv
import glob
import sqlite3
import reformat_threshold as rt
import db_helper

CSV_BASE = os.path.join(rt.BASE, '原始数据csv')
CITY_CSV = rt.CITY_CSV


def _is_missing_row(row_values):
    """检测是否为'缺数据'标记行: 第3列(索引2, 写入时间/城市之后的第一列)为'缺数据'"""
    return len(row_values) > 2 and row_values[2] == '缺数据'


def migrate_cities(conn):
    """导入城市列表 CSV -> city 表"""
    count = 0
    with open(CITY_CSV, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            db_helper.insert_row(conn, 'city', {
                'fcity':        int(r['Fcity']) if r['Fcity'] else None,
                'flon':         float(r['Flon']) if r['Flon'] else None,
                'flat':         float(r['Flat']) if r['Flat'] else None,
                'finternal':    int(r['Finternal']) if r.get('Finternal') else None,
                'fcityname_cn': r['Fcityname_cn'].strip(),
                'fbj_code':     r.get('Fbj_code', '').strip() or None,
                'category':     r.get('分类', '').strip() or None,
                'reason':       r.get('选取原因', '').strip() or None,
            })
            count += 1
    conn.commit()
    return count


def _build_csv_to_db_mapping(module, mspec, table_map):
    """构建 CSV 列名 -> DB 列名 的映射 dict"""
    mapping = {
        '写入时间': 'pull_at',
        '城市': 'city_name',
    }
    if table_map['ts_col']:
        if mspec['source'] == 'hourly':
            mapping['时次(UTC)'] = 'ts_utc'
            mapping['predictTime(国内UTC)'] = 'predict_time_cn'
            mapping['predictTime(海外UTC)'] = 'predict_time_intl'
            mapping['localTime(国内)'] = 'local_time_cn'
            mapping['localTime(海外)'] = 'local_time_intl'
            mapping['updatetime(国内UTC)'] = 'updatetime_cn'
        elif mspec['source'] == 'daily':
            mapping['日期(当地)'] = 'local_date'
            mapping['predictDate(国内UTC)'] = 'predict_date_cn'
            mapping['predictDate(海外UTC)'] = 'predict_date_intl'
            mapping['localDate(国内)'] = 'local_date_cn'
            mapping['localDate(海外)'] = 'local_date_intl'
    for fname, (cn_col, intl_col) in table_map['fields'].items():
        mapping[f'{fname}(国内)'] = cn_col
        mapping[f'{fname}(海外)'] = intl_col
    return mapping


def migrate_module_csv(conn, module, mspec, table_map):
    """导入一个模块的所有日期 CSV -> 对应表"""
    table = table_map['table']
    mapping = _build_csv_to_db_mapping(module, mspec, table_map)
    total = 0

    pattern = os.path.join(CSV_BASE, '*', f'{module}_*.csv')
    for csv_path in sorted(glob.glob(pattern)):
        bn = os.path.basename(csv_path)
        if '_bak_' in bn or '备份' in bn:
            continue

        with open(csv_path, encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                continue

            # 构建 CSV列索引 -> DB列名 的映射 (跳过不在映射中的列)
            col_map = {}
            for i, col_name in enumerate(header):
                if col_name in mapping:
                    col_map[i] = mapping[col_name]

            for raw in reader:
                if len(raw) != len(header):
                    continue  # 跳过列数不匹配的错位行

                is_missing = _is_missing_row(raw)
                row = {}
                for i, db_col in col_map.items():
                    val = raw[i].strip() if i < len(raw) else ''
                    if is_missing:
                        row[db_col] = None
                    else:
                        row[db_col] = db_helper.to_val(val)
                if 'is_missing' not in row:
                    row['is_missing'] = 1 if is_missing else 0

                db_helper.insert_row(conn, table, row)
                total += 1

    conn.commit()
    return total


# ===== 短时/预警 CSV 列映射 =====
NOWCAST_CSV_MAP = {
    '写入时间': 'pull_at', '城市': 'city_name',
    '国内是否降水(rain)': 'cn_rain', '国内类型(type)': 'cn_type',
    '国内描述(content)': 'cn_content', '国内时间戳(timestamp)': 'cn_timestamp',
    '国内降水概率(percent_json)': 'cn_percent_json',
    '国际是否降水(rain)': 'intl_rain', '国际降水等级(level)': 'intl_level',
    '国际降水强度(rain_intensity)': 'intl_rain_intensity',
    '国际降水持续(rain_last_time)': 'intl_rain_last_time',
    '国际描述(long_desc)': 'intl_long_desc', '国际短描述(short_desc)': 'intl_short_desc',
    '国际时间戳(timestamp)': 'intl_timestamp',
    '国际降水概率(percent_json)': 'intl_percent_json',
}

ALERT_CSV_MAP = {
    '写入时间': 'pull_at', '城市': 'city_name',
    '国内预警数': 'cn_alert_count', '国内预警JSON': 'cn_alert_json',
    '国际预警数': 'intl_alert_count', '国际预警JSON': 'intl_alert_json',
}


def migrate_aux_csv(conn, aux_name, csv_map):
    """导入短时/预警 CSV -> 对应表"""
    table = db_helper.AUX_TABLE_MAP[aux_name]
    total = 0

    pattern = os.path.join(CSV_BASE, '*', f'{aux_name}_*.csv')
    for csv_path in sorted(glob.glob(pattern)):
        bn = os.path.basename(csv_path)
        if '_bak_' in bn or '备份' in bn:
            continue

        with open(csv_path, encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                continue

            col_map = {}
            for i, col_name in enumerate(header):
                if col_name in csv_map:
                    col_map[i] = csv_map[col_name]

            for raw in reader:
                if len(raw) != len(header):
                    continue
                row = {}
                for i, db_col in col_map.items():
                    val = raw[i].strip() if i < len(raw) else ''
                    if db_col in ('cn_alert_count', 'intl_alert_count'):
                        row[db_col] = int(val) if val and val.isdigit() else 0
                    else:
                        row[db_col] = db_helper.to_val(val)
                db_helper.insert_row(conn, table, row)
                total += 1

    conn.commit()
    return total


def main():
    if not os.path.exists(CSV_BASE):
        print(f"❌ CSV 目录不存在: {CSV_BASE}")
        return

    conn = db_helper.get_conn()

    # 1. 城市列表
    n = migrate_cities(conn)
    print(f"✅ city: {n} 行")

    # 2. 四个比对模块
    for module, mspec in rt.MODULES.items():
        table_map = db_helper.MODULE_TABLE_MAP[module]
        n = migrate_module_csv(conn, module, mspec, table_map)
        print(f"✅ {module} -> {table_map['table']}: {n} 行")

    # 3. 短时/预警
    n = migrate_aux_csv(conn, '短时', NOWCAST_CSV_MAP)
    print(f"✅ 短时 -> nowcast: {n} 行")

    n = migrate_aux_csv(conn, '预警', ALERT_CSV_MAP)
    print(f"✅ 预警 -> alert: {n} 行")

    # 4. 统计
    print("\n=== 数据库统计 ===")
    for table in ['city', 'pull_round', 'current_weather', 'hourly_forecast',
                   'daily_forecast', 'aqi', 'nowcast', 'alert', 'raw_pull_data']:
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:20s}: {cur.fetchone()[0]} 行")

    # 日期范围
    cur = conn.execute("SELECT MIN(substr(pull_at,1,10)), MAX(substr(pull_at,1,10)) FROM current_weather")
    r = cur.fetchone()
    if r and r[0]:
        print(f"\n  日期范围: {r[0]} ~ {r[1]}")
        cur = conn.execute("SELECT DISTINCT substr(pull_at,1,10) AS d FROM current_weather ORDER BY d")
        dates = [row[0] for row in cur.fetchall()]
        print(f"  日期数: {len(dates)} ({', '.join(dates)})")

    conn.close()
    print(f"\n数据库: {db_helper.DB_PATH}")


if __name__ == '__main__':
    main()
