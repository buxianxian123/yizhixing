#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""筛选参数解析 / 校验 / 归一化 → FilterSpec。

FilterSpec 是平台所有分析的统一筛选模型，也是缓存 key 的来源。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config  # noqa: E402
import reformat_threshold as rt  # noqa: E402

from repository.connection import get_conn  # noqa: E402


# 全局有效城市集（rt.load_cities 设置 CITY_RANK 后可用）
_VALID_CITIES = None


def _valid_cities():
    global _VALID_CITIES
    if _VALID_CITIES is None:
        try:
            _VALID_CITIES = set(c[0] for c in rt.load_cities())
        except Exception:
            _VALID_CITIES = set()
    return _VALID_CITIES


class FilterSpec:
    """统一筛选模型。字段：
      date_start / date_end: YYYYMMDD（日期范围，pulls 为空时生效）
      pulls: list[str] 精确批次（优先于日期）
      cities: list[str] 城市名（已与 valid 求交集）
      modules: list[str]
      periods: list[str]
      group_a / group_b: list[str]（仅 compare 用）
    """

    def __init__(self, date_start=None, date_end=None, pulls=None, cities=None,
                 modules=None, periods=None, group_a=None, group_b=None, extras=None):
        self.date_start = date_start
        self.date_end = date_end
        self.pulls = pulls or []
        self.cities = cities or []
        self.modules = modules or []
        self.periods = periods or []
        self.group_a = group_a or []
        self.group_b = group_b or []
        self.extras = extras or {}  # dim/field/page/q 等非筛选但按请求附加的参数

    @property
    def date_range(self):
        """(start_YYYYMMDD, end_YYYYMMDD) or None。仅当 pulls 为空且日期有值。"""
        if self.pulls:
            return None
        if self.date_start and self.date_end:
            return (self.date_start, self.date_end)
        if self.date_start:
            return (self.date_start, self.date_start)
        return None

    def snapshot(self):
        return {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'pulls': self.pulls,
            'cities': self.cities,
            'modules': self.modules,
            'periods': self.periods,
        }

    def cache_key(self):
        snap = dict(self.snapshot())
        snap['extras'] = self.extras
        return json.dumps(snap, ensure_ascii=False, sort_keys=True)

    def get(self, key, default=None):
        """兼容 dict 式访问：先查 extras（request.args 附加参数），再查自身属性。"""
        if key in self.extras:
            return self.extras[key]
        return getattr(self, key, default)


def _norm_date(s):
    """归一化日期：YYYY-MM-DD 或 YYYYMMDD → YYYYMMDD。非法抛 ValueError。"""
    if not s:
        return None
    s = str(s).strip().replace('-', '')
    if len(s) == 8 and s.isdigit():
        return s
    raise ValueError(f'非法日期参数: {s}（期望 YYYY-MM-DD 或 YYYYMMDD）')


def _split(v):
    """list 或 逗号分隔字符串 → list。"""
    if not v:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v).split(',') if x.strip()]


def _validate_modules(modules):
    valid = set(rt.MODULES.keys())
    out = [m for m in modules if m in valid]
    return out


def _validate_periods(periods):
    valid = set(config.PERIOD_DISPLAY)
    return [p for p in periods if p in valid]


def _resolve_cities(country, prov, city3, cities):
    """地区三级 + 直接城市 → 城市名列表（与 valid 求交集）。

    country/prov/city3 从 city_region.json 解析；cities 为直接城市名。
    """
    result = set(cities)

    # 读地区映射
    region = {}
    try:
        with open(config.REGION_JSON, encoding='utf-8') as f:
            region = json.load(f)
    except Exception:
        pass

    if country:
        for city, (c, p) in region.items():
            if c == country:
                if prov:
                    if p == prov:
                        if city3:
                            if city == city3:
                                result.add(city)
                        else:
                            result.add(city)
                else:
                    result.add(city)
    elif city3:
        # 只有市没有国/省：按城市名反查
        for city, (c, p) in region.items():
            if city == city3:
                result.add(city)

    valid = _valid_cities()
    # 保持顺序稳定
    ordered = [c for c in result if c in valid]
    return ordered


def _parse_common(params, for_report=False):
    """从类 dict 解析共享筛选（用于 URL query args 和 JSON payload）。"""
    date_start = _norm_date(params.get('date_start') or params.get('dateStart'))
    date_end = _norm_date(params.get('date_end') or params.get('dateEnd'))
    pulls = _split(params.get('pulls') or params.get('pull_at'))
    cities = _split(params.get('cities') or params.get('city'))
    modules = _validate_modules(_split(params.get('modules') or params.get('module')))
    periods = _validate_periods(_split(params.get('periods') or params.get('period')))
    country = (params.get('country') or '').strip() or None
    prov = (params.get('prov') or '').strip() or None
    city3 = (params.get('city3') or '').strip() or None

    # 若直接给了城市名/地区，city 列表用 resolve 合并
    cities = _resolve_cities(country, prov, city3, cities)

    return FilterSpec(date_start=date_start, date_end=date_end, pulls=pulls,
                      cities=cities, modules=modules, periods=periods)


# 附加参数（非筛选，按端点注入 fs.extras）
_EXTRA_KEYS = ('dim', 'field', 'page', 'per_page', 'q', 'sort', 'order')


def parse_args(args):
    """解析 Flask request.args（URL 查询参数）。"""
    fs = _parse_common(args)
    # ab = "A组pulls|B组pulls"（仅 compare 用）
    ab = args.get('ab')
    if ab:
        parts = str(ab).split('|')
        fs.group_a = _split(parts[0]) if len(parts) > 0 else []
        fs.group_b = _split(parts[1]) if len(parts) > 1 else []
        # compare 用 ab 作为筛选批次
        fs.pulls = fs.group_a + fs.group_b
    extras = {k: args.get(k) for k in _EXTRA_KEYS if args.get(k)}
    fs.extras = extras

    # 无任何筛选条件时：回退到最近 DEFAULT_LAST_PULLS 个批次（避免裸请求读全表超上限）
    _apply_default_pulls(fs)
    return fs


def parse_payload(payload):
    """解析 POST JSON body。"""
    fs = _parse_common(payload)
    fs.group_a = _split(payload.get('groupA') or payload.get('group_a'))
    fs.group_b = _split(payload.get('groupB') or payload.get('group_b'))
    extras = {k: payload.get(k) for k in _EXTRA_KEYS if payload.get(k)}
    fs.extras = extras
    # 与 URL 参数一致：无筛选时回退到最近批次，避免读全表超上限
    _apply_default_pulls(fs)
    return fs


def _apply_default_pulls(fs):
    """无批次且无日期时，回退到最近 DEFAULT_LAST_PULLS 个批次。"""
    if fs.pulls or fs.date_start or fs.date_end:
        return
    from repository.meta import get_pulls
    _all = get_pulls()
    if _all:
        fs.pulls = _all[-config.DEFAULT_LAST_PULLS:]
