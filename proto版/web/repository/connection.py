#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库连接与健康检查。

复用 proto版根目录 db_helper.get_conn()（WAL 模式、row_factory=Row），
平台不新造连接逻辑。
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # web/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # proto版/

import db_helper  # noqa: E402

# 数据表清单（一致性比对相关；nowcast/alert 留底不计入一致率，但列入健康检查）
COMPARE_TABLES = ['current_weather', 'hourly_forecast', 'daily_forecast', 'aqi']
ALL_TABLES = ['city', 'pull_round', 'current_weather', 'hourly_forecast',
              'daily_forecast', 'aqi', 'nowcast', 'alert']


def get_conn() -> sqlite3.Connection:
    """获取 SQLite 连接（WAL，支持并发读）。每请求短连接，用后 close。"""
    return db_helper.get_conn()


def check_healthy() -> dict:
    """健康检查：DB 存在性 / 各表存在性 / 批次总量 / 最近批次。

    返回 dict，不抛异常（供 /health 与前端探活用）。
    """
    result = {
        'db_exists': os.path.exists(db_helper.DB_PATH),
        'tables': {},
        'pull_count': 0,
        'last_pull_at': None,
    }
    if not result['db_exists']:
        return result

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        for t in ALL_TABLES:
            try:
                result['tables'][t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                result['tables'][t] = None
        try:
            result['pull_count'] = cur.execute(
                "SELECT COUNT(DISTINCT pull_at) FROM current_weather").fetchone()[0]
            result['last_pull_at'] = cur.execute(
                "SELECT MAX(pull_at) FROM current_weather").fetchone()[0]
        except Exception:
            pass
    except Exception as e:
        result['error'] = str(e)
    finally:
        if conn is not None:
            conn.close()
    return result
