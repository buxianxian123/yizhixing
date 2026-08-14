#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""平台配置：路径常量 + compare_config.yaml 规则 + 平台自身参数。

复用 proto版根目录的 compare_config.yaml（阈值/风速/天气映射/清洗/时效分段，
规则唯一来源，经 reformat_threshold.py 加载），平台自身参数在此维护。
"""
import os
import yaml

# ===== 路径常量 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))        # web/
PROTO_DIR = os.path.dirname(SCRIPT_DIR)                         # proto版/
BASE = os.path.join(PROTO_DIR, '..', 'data')                    # ../data/
DB_PATH = os.path.join(BASE, 'weather_data.db')
CITY_CSV = os.path.join(BASE, '天气一致性测试城市_热门城市筛选.csv')
CONFIG_PATH = os.environ.get('CONFIG_PATH') or os.path.join(PROTO_DIR, 'compare_config.yaml')
REGION_JSON = os.path.join(SCRIPT_DIR, 'static', 'assets', 'city_region.json')
ECHARTS_PATH = os.path.join(PROTO_DIR, 'echarts.min.js')
REPORT_DIR = os.path.join(SCRIPT_DIR, 'report')                 # 运行时生成 xlsx/md
OUT_DIR = os.path.join(BASE, '比对结果')                        # 与现有一致，用于定位旧产物

# ===== 平台自身参数（不影响比对口径） =====
MAX_POINTS = 20_000_000       # read_points 内存上限守卫（覆盖月级查询）
DEFAULT_LAST_PULLS = 24       # 首屏默认「最近 N 个批次」
CACHE_TTL = 30                # 聚合缓存 TTL（秒）——缩短以保证 DB 更新后及时可见
CACHE_MAXSIZE = 128           # LRU 缓存条目上限
ABNORMAL_FIELD_RATE = 60.0    # 异常城市判定：任一字段一致率 < 60%
ABNORMAL_CITY_RATE = 85.0     # 异常城市判定：城市总体一致率 < 85%
DETAIL_PAGE_SIZE = 50         # 明细分页默认每页条数
DETAIL_MAX_PAGE_SIZE = 200    # 明细分页每页上限

# ===== compare_config.yaml 规则加载（复用 reformat_threshold 已加载的常量）=====
def _load_config():
    try:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


# ===== 模块展示名 / 字段展示顺序（与 gen_md_report / gen_html_report 对齐） =====
MODULE_DISPLAY = {'实况': '实况', '24小时': '24小时', '15天': '15天', 'AQI模块': 'AQI'}
PERIOD_DISPLAY = ['短时效(1-6h)', '中时效(7-12h)', '长时效(13-24h)']
FIELD_ORDER = ['温度', '体感温度', '湿度', '风速', '气压', '天气现象', '降水量',
               '温度(最高)', '温度(最低)', '体感温度(白天)', '体感温度(夜间)',
               '风速(白天)', '风速(夜间)', '天气现象(白天)', '天气现象(夜间)', 'AQI']
