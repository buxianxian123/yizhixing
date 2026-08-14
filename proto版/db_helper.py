#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库操作公共模块。

提供连接管理、值转换、表/列映射、通用插入。
被 pull_latest_round.py / gen_report_from_csv.py / migrate_csv_to_db.py 复用。
"""
import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, '..', 'data')
DB_PATH = os.path.join(BASE, 'weather_data.db')

# ===== 模块 -> 表/列映射 =====
# ts_col: 多值模块的时间戳列名(单值模块为 None)
# fields: {字段名: (国内列名, 海外列名)}
MODULE_TABLE_MAP = {
    '实况': {
        'table': 'current_weather',
        'ts_col': None,
        'fields': {
            '温度':         ('temp_cn',       'temp_intl'),
            '体感温度':     ('real_feel_cn',  'real_feel_intl'),
            '湿度':         ('humidity_cn',   'humidity_intl'),
            '风速':         ('wspd_cn',       'wspd_intl'),
            '气压':         ('mslp_cn',       'mslp_intl'),
            '天气现象':     ('weather_cn',    'weather_intl'),
            '紫外线':       ('uvi_cn',        'uvi_intl'),
            '能见度':       ('vis_cn',        'vis_intl'),
            '风向':         ('wind_dir_cn',   'wind_dir_intl'),
        },
    },
    '24小时': {
        'table': 'hourly_forecast',
        'ts_col': 'ts_utc',
        'fields': {
            '温度':         ('temp_cn',       'temp_intl'),
            '体感温度':     ('real_feel_cn',  'real_feel_intl'),
            '湿度':         ('humidity_cn',   'humidity_intl'),
            '风速':         ('wspd_cn',       'wspd_intl'),
            '天气现象':     ('weather_cn',    'weather_intl'),
            '风向':         ('wind_dir_cn',   'wind_dir_intl'),
            '降水概率':     ('pop_cn',        'pop_intl'),
        },
    },
    '15天': {
        'table': 'daily_forecast',
        'ts_col': 'local_date',
        'fields': {
            '温度(最高)':       ('temp_high_cn',      'temp_high_intl'),
            '温度(最低)':       ('temp_low_cn',       'temp_low_intl'),
            '湿度':             ('humidity_cn',       'humidity_intl'),
            '风速(白天)':       ('wspd_day_cn',       'wspd_day_intl'),
            '风速(夜间)':       ('wspd_night_cn',     'wspd_night_intl'),
            '气压':             ('mslp_cn',           'mslp_intl'),
            '天气现象(白天)':   ('weather_day_cn',    'weather_day_intl'),
            '天气现象(夜间)':   ('weather_night_cn',  'weather_night_intl'),
            '紫外线':           ('uvi_cn',            'uvi_intl'),
            '降水概率':         ('pop_cn',            'pop_intl'),
        },
    },
    'AQI模块': {
        'table': 'aqi',
        'ts_col': None,
        'fields': {
            'AQI': ('aqi_cn', 'aqi_intl'),
        },
    },
}

# ===== 短时/预警 表名 (无 MODULES 配置, 独立处理) =====
AUX_TABLE_MAP = {
    '短时': 'nowcast',
    '预警': 'alert',
}


def get_conn():
    """返回 SQLite 连接 (WAL 模式, 支持并发读)"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def to_val(v):
    """值 -> 数据库存储值。
    None/空串/'缺数据' -> None (NULL)
    数字/数字字符串 -> float
    其他文字 -> str (天气现象/风向/紫外线文字等)"""
    if v is None or v == '' or v == '缺数据':
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (ValueError, TypeError):
        return str(v)


def insert_row(conn, table, row_dict):
    """通用插入: INSERT OR IGNORE (靠 UNIQUE 约束去重)。
    row_dict: {列名: 值, ...}"""
    columns = list(row_dict.keys())
    placeholders = ', '.join(['?'] * len(columns))
    col_str = ', '.join(columns)
    conn.execute(
        f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})",
        list(row_dict.values())
    )


def build_field_cols(row, fields, table_map, cn_data, intl_data):
    """从归一化数据提取字段值, 填入 row dict。
    fields: MODULES[module]['fields'] 配置
    table_map: MODULE_TABLE_MAP[module]
    cn_data/intl_data: 归一化后的国内/海外数据 dict (单值模块是 dict, 多值模块是数组元素)"""
    for fname, spec in fields.items():
        cn_col, intl_col = table_map['fields'][fname]
        row[cn_col] = to_val(cn_data.get(spec['cn']) if cn_data else None)
        row[intl_col] = to_val(intl_data.get(spec['intl']) if intl_data else None)


def get_all_dates(conn):
    """查询数据库中所有有数据的日期 (YYYYMMDD 格式列表)"""
    cur = conn.execute(
        "SELECT DISTINCT substr(pull_at, 1, 10) AS d FROM current_weather "
        "UNION SELECT DISTINCT substr(pull_at, 1, 10) FROM pull_round "
        "ORDER BY d"
    )
    return [r[0].replace('-', '') for r in cur.fetchall() if r[0]]
