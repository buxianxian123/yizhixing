#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析国内/国际接口 JSON 结构，映射要测的8个字段"""
import json

with open('/tmp/cn_beijing.json', 'r', encoding='utf-8') as f:
    cn = json.load(f)
with open('/tmp/in_beijing.json', 'r', encoding='utf-8') as f:
    intl = json.load(f)

print("=" * 70)
print("国内接口 顶层结构 (data 下的模块)")
print("=" * 70)
cn_data = cn.get('data', {})
for k, v in cn_data.items():
    if isinstance(v, list):
        print(f"  {k}: 数组[{len(v)}条]" + (f" (每条字段: {list(v[0].keys()) if v else '空'})" if v else ""))
    elif isinstance(v, dict):
        print(f"  {k}: 对象 (字段: {list(v.keys())})")
    else:
        print(f"  {k}: {type(v).__name__} = {v}")

print()
print("=" * 70)
print("国际接口 顶层结构 (data 下的模块)")
print("=" * 70)
intl_data = intl.get('data', {})
for k, v in intl_data.items():
    if isinstance(v, list):
        print(f"  {k}: 数组[{len(v)}条]" + (f" (每条字段: {list(v[0].keys()) if v else '空'})" if v else ""))
    elif isinstance(v, dict):
        print(f"  {k}: 对象 (字段: {list(v.keys())})")
    else:
        print(f"  {k}: {type(v).__name__} = {v}")

# 详细看各模块字段
print()
print("=" * 70)
print("【实况模块】字段对比 (国内 current vs 国际 current)")
print("=" * 70)
cn_cur = cn_data.get('current', {})
intl_cur = intl_data.get('current', {})
print(f"国内 current 字段({len(cn_cur)}个): {sorted(cn_cur.keys())}")
print()
print(f"国际 current 字段({len(intl_cur)}个): {sorted(intl_cur.keys())}")

print()
print("=" * 70)
print("【小时预报模块】字段对比")
print("=" * 70)
cn_hourly = cn_data.get('hourly', cn_data.get('forecast_hourly', []))
intl_hourly = intl_data.get('hourly', [])
if cn_hourly: print(f"国内 hourly 第一条字段({len(cn_hourly[0])}个): {sorted(cn_hourly[0].keys())}")
else: print("国内: 未找到hourly, 顶层key=", list(cn_data.keys()))
if intl_hourly: print(f"国际 hourly 第一条字段({len(intl_hourly[0])}个): {sorted(intl_hourly[0].keys())}")

print()
print("=" * 70)
print("【15天预报模块】字段对比")
print("=" * 70)
# 国内 daily 可能在 forecast 里
cn_daily = cn_data.get('daily', cn_data.get('forecast', {}).get('daily', []) if isinstance(cn_data.get('forecast'), dict) else [])
intl_daily = intl_data.get('daily', [])
print("国内顶层daily:", 'daily' in cn_data, "| forecast存在:", 'forecast' in cn_data)
if isinstance(cn_data.get('forecast'), dict):
    print("  forecast下key:", list(cn_data['forecast'].keys()))
if cn_daily: print(f"国内 daily 第一条字段({len(cn_daily[0])}个): {sorted(cn_daily[0].keys())}")
else:
    # 尝试其他位置
    for path in [['forecast','daily'],['daily'],['forecast_15d']]:
        d = cn_data
        ok = True
        for p in path:
            if isinstance(d, dict) and p in d: d = d[p]
            else: ok=False; break
        if ok and isinstance(d, list) and d:
            print(f"  国内 {path} 第一条字段: {sorted(d[0].keys())}")
            cn_daily = d; break
if intl_daily: print(f"国际 daily 第一条字段({len(intl_daily[0])}个): {sorted(intl_daily[0].keys())}")

print()
print("=" * 70)
print("【AQI模块】字段对比")
print("=" * 70)
cn_aqi = cn_data.get('aqi', {})
intl_aqi = intl_data.get('aqi', {})
print(f"国内 aqi 字段({len(cn_aqi)}个): {sorted(cn_aqi.keys())}")
print(f"国际 aqi 字段({len(intl_aqi)}个): {sorted(intl_aqi.keys())}")

# 打印一些样例值帮助识别
print()
print("=" * 70)
print("【字段值样例】(帮助识别字段含义)")
print("=" * 70)
print("国内 current 样例:")
for k in ['temp','real_feel','humidity','weather','weather_id','wind_degrees','mslp','vis','uvi','wind_speed','wind']:
    if k in cn_cur: print(f"  {k} = {cn_cur[k]}")
print("国内 current 所有含wind的字段:", {k:v for k,v in cn_cur.items() if 'wind' in k.lower()})
print()
print("国际 current 样例:")
for k in ['temp','feels_like','real_feel','humidity','weather','weather_id','wind_degrees','wind_speed','pressure','mslp','vis','uvi']:
    if k in intl_cur: print(f"  {k} = {intl_cur[k]}")
print("国际 current 所有含wind的字段:", {k:v for k,v in intl_cur.items() if 'wind' in k.lower()})
print("国际 current 所有含press/feel/temp的字段:", {k:v for k,v in intl_cur.items() if any(x in k.lower() for x in ['press','feel','temp','humid','weather','vis'])})
