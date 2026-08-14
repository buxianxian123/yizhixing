#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化本地 SQLite 数据库。

根据现有 CSV 结构建表，替代 data/原始数据csv/ 的文件存储方式。
数据库文件: data/weather_data.db

表结构对应 6 个模块 CSV + 城市配置表 + 拉取轮次元数据表 + 原始数据留底表:
  city              <- 天气一致性测试城市_热门城市筛选.csv
  pull_round        <- _manifest.json (每轮拉取元数据)
  current_weather   <- 实况_<date>.csv
  hourly_forecast   <- 24小时_<date>.csv
  daily_forecast    <- 15天_<date>.csv
  aqi               <- AQI模块_<date>.csv
  nowcast           <- 短时_<date>.csv
  alert             <- 预警_<date>.csv
  raw_pull_data     <- 原始拉取/原始_<ts>/<city>/ (国内.pb + 国内.json + 国际.json)

运行: python3 init_db.py
"""
import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, '..', 'data')
DB_PATH = os.path.join(BASE, 'weather_data.db')

SCHEMA = """
-- ========== 城市配置表 ==========
-- 来源: data/天气一致性测试城市_热门城市筛选.csv
CREATE TABLE IF NOT EXISTS city (
    fcity          INTEGER PRIMARY KEY,
    flon           REAL    NOT NULL,
    flat           REAL    NOT NULL,
    finternal      INTEGER,
    fcityname_cn   TEXT    NOT NULL,
    fbj_code       TEXT,
    category       TEXT,
    reason         TEXT
);

-- ========== 拉取轮次元数据表 ==========
-- 来源: data/原始拉取/原始_<ts>/_manifest.json
CREATE TABLE IF NOT EXISTS pull_round (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at        TEXT    NOT NULL UNIQUE,
    raw_dir        TEXT,
    total_ok       INTEGER DEFAULT 0,
    total_fail     INTEGER DEFAULT 0,
    created_at     TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- ========== 实况模块表 ==========
-- 来源: 实况_<date>.csv
-- 表头: 写入时间,城市,温度(国内),温度(海外),体感温度(国内),体感温度(海外),
--       湿度(国内),湿度(海外),风速(国内),风速(海外),气压(国内),气压(海外),
--       天气现象(国内),天气现象(海外),紫外线(国内),紫外线(海外),
--       能见度(国内),能见度(海外),风向(国内),风向(海外)
-- 去重: (写入时间, 城市)
CREATE TABLE IF NOT EXISTS current_weather (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at         TEXT    NOT NULL,
    city_name       TEXT    NOT NULL,
    temp_cn         REAL,
    temp_intl       REAL,
    real_feel_cn    REAL,
    real_feel_intl  REAL,
    humidity_cn     REAL,
    humidity_intl   REAL,
    wspd_cn         REAL,
    wspd_intl       REAL,
    mslp_cn         REAL,
    mslp_intl       REAL,
    weather_cn      TEXT,
    weather_intl    TEXT,
    uvi_cn          TEXT,
    uvi_intl        REAL,
    vis_cn          REAL,
    vis_intl        REAL,
    wind_dir_cn     TEXT,
    wind_dir_intl   TEXT,
    is_missing      INTEGER DEFAULT 0,
    UNIQUE(pull_at, city_name)
);

-- ========== 24小时逐时预报表 ==========
-- 来源: 24小时_<date>.csv
-- 表头: 写入时间,城市,时次(UTC),predictTime(国内UTC),predictTime(海外UTC),
--       localTime(国内),localTime(海外),updatetime(国内UTC),
--       温度(国内),温度(海外),体感温度(国内),体感温度(海外),
--       湿度(国内),湿度(海外),风速(国内),风速(海外),
--       天气现象(国内),天气现象(海外),风向(国内),风向(海外),
--       降水概率(国内),降水概率(海外)
-- 去重: (写入时间, 城市, 时次(UTC))
CREATE TABLE IF NOT EXISTS hourly_forecast (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at           TEXT    NOT NULL,
    city_name         TEXT    NOT NULL,
    ts_utc            TEXT,
    predict_time_cn   TEXT,
    predict_time_intl TEXT,
    local_time_cn     TEXT,
    local_time_intl   TEXT,
    updatetime_cn     TEXT,
    temp_cn           REAL,
    temp_intl         REAL,
    real_feel_cn      REAL,
    real_feel_intl    REAL,
    humidity_cn       REAL,
    humidity_intl     REAL,
    wspd_cn           REAL,
    wspd_intl         REAL,
    weather_cn        TEXT,
    weather_intl      TEXT,
    wind_dir_cn       TEXT,
    wind_dir_intl     TEXT,
    pop_cn            REAL,
    pop_intl          REAL,
    is_missing        INTEGER DEFAULT 0,
    UNIQUE(pull_at, city_name, ts_utc)
);

-- ========== 15天逐日预报表 ==========
-- 来源: 15天_<date>.csv
-- 表头: 写入时间,城市,日期(当地),predictDate(国内UTC),predictDate(海外UTC),
--       localDate(国内),localDate(海外),
--       温度(最高)(国内),温度(最高)(海外),温度(最低)(国内),温度(最低)(海外),
--       湿度(国内),湿度(海外),风速(白天)(国内),风速(白天)(海外),
--       风速(夜间)(国内),风速(夜间)(海外),气压(国内),气压(海外),
--       天气现象(白天)(国内),天气现象(白天)(海外),
--       天气现象(夜间)(国内),天气现象(夜间)(海外),
--       紫外线(国内),紫外线(海外),降水概率(国内),降水概率(海外)
-- 去重: (写入时间, 城市, 日期(当地))
CREATE TABLE IF NOT EXISTS daily_forecast (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at             TEXT    NOT NULL,
    city_name           TEXT    NOT NULL,
    local_date          TEXT,
    predict_date_cn     TEXT,
    predict_date_intl   TEXT,
    local_date_cn       TEXT,
    local_date_intl     TEXT,
    temp_high_cn        REAL,
    temp_high_intl      REAL,
    temp_low_cn         REAL,
    temp_low_intl       REAL,
    humidity_cn         REAL,
    humidity_intl       REAL,
    wspd_day_cn         REAL,
    wspd_day_intl       REAL,
    wspd_night_cn       REAL,
    wspd_night_intl     REAL,
    mslp_cn             REAL,
    mslp_intl           REAL,
    weather_day_cn      TEXT,
    weather_day_intl    TEXT,
    weather_night_cn    TEXT,
    weather_night_intl  TEXT,
    uvi_cn              TEXT,
    uvi_intl            REAL,
    pop_cn              REAL,
    pop_intl            REAL,
    is_missing          INTEGER DEFAULT 0,
    UNIQUE(pull_at, city_name, local_date)
);

-- ========== AQI模块表 ==========
-- 来源: AQI模块_<date>.csv
-- 表头: 写入时间,城市,AQI(国内),AQI(海外)
-- 去重: (写入时间, 城市)
CREATE TABLE IF NOT EXISTS aqi (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at     TEXT    NOT NULL,
    city_name   TEXT    NOT NULL,
    aqi_cn      REAL,
    aqi_intl    REAL,
    is_missing  INTEGER DEFAULT 0,
    UNIQUE(pull_at, city_name)
);

-- ========== 短时降水表 ==========
-- 来源: 短时_<date>.csv
-- 表头: 写入时间,城市,
--       国内是否降水(rain),国内类型(type),国内描述(content),国内时间戳(timestamp),国内降水概率(percent_json),
--       国际是否降水(rain),国际降水等级(level),国际降水强度(rain_intensity),国际降水持续(rain_last_time),
--       国际描述(long_desc),国际短描述(short_desc),国际时间戳(timestamp),国际降水概率(percent_json)
-- 去重: (写入时间, 城市)
CREATE TABLE IF NOT EXISTS nowcast (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at               TEXT    NOT NULL,
    city_name             TEXT    NOT NULL,
    cn_rain               TEXT,
    cn_type               TEXT,
    cn_content            TEXT,
    cn_timestamp          TEXT,
    cn_percent_json       TEXT,
    intl_rain             TEXT,
    intl_level            TEXT,
    intl_rain_intensity   TEXT,
    intl_rain_last_time   TEXT,
    intl_long_desc        TEXT,
    intl_short_desc       TEXT,
    intl_timestamp        TEXT,
    intl_percent_json     TEXT,
    UNIQUE(pull_at, city_name)
);

-- ========== 预警表 ==========
-- 来源: 预警_<date>.csv
-- 表头: 写入时间,城市,国内预警数,国内预警JSON,国际预警数,国际预警JSON
-- 去重: (写入时间, 城市)
CREATE TABLE IF NOT EXISTS alert (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    pull_at           TEXT    NOT NULL,
    city_name         TEXT    NOT NULL,
    cn_alert_count    INTEGER DEFAULT 0,
    cn_alert_json     TEXT,
    intl_alert_count  INTEGER DEFAULT 0,
    intl_alert_json   TEXT,
    UNIQUE(pull_at, city_name)
);

-- ========== 索引 ==========
CREATE INDEX IF NOT EXISTS idx_current_pull    ON current_weather(pull_at);
CREATE INDEX IF NOT EXISTS idx_current_city    ON current_weather(city_name);
CREATE INDEX IF NOT EXISTS idx_hourly_pull     ON hourly_forecast(pull_at);
CREATE INDEX IF NOT EXISTS idx_hourly_city     ON hourly_forecast(city_name);
CREATE INDEX IF NOT EXISTS idx_daily_pull      ON daily_forecast(pull_at);
CREATE INDEX IF NOT EXISTS idx_daily_city      ON daily_forecast(city_name);
CREATE INDEX IF NOT EXISTS idx_aqi_pull        ON aqi(pull_at);
CREATE INDEX IF NOT EXISTS idx_aqi_city        ON aqi(city_name);
CREATE INDEX IF NOT EXISTS idx_nowcast_pull    ON nowcast(pull_at);
CREATE INDEX IF NOT EXISTS idx_nowcast_city    ON nowcast(city_name);
CREATE INDEX IF NOT EXISTS idx_alert_pull      ON alert(pull_at);
CREATE INDEX IF NOT EXISTS idx_alert_city      ON alert(city_name);
"""


def init_db():
    os.makedirs(BASE, exist_ok=True)
    if os.path.exists(DB_PATH):
        print(f"数据库已存在: {DB_PATH}")
        print("如需重建请先删除该文件。")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name")
    indexes = [r[0] for r in cur.fetchall()]

    conn.close()

    print(f"数据库创建成功: {DB_PATH}")
    print(f"  表 ({len(tables)}): {', '.join(tables)}")
    print(f"  索引 ({len(indexes)}): {', '.join(indexes)}")


if __name__ == '__main__':
    init_db()
