#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国内 proto detail 接口拉取 + 转 json (旧 moweather 兼容结构)
替代 reformat_threshold.py 里国内接口 (coapi.moji.com whapi/v2/weather)。

输出结构与旧 moweather 一致, build_points / MODULES 无需改:
  current: {temp, real_feel, humidity, wspd, mslp, weather}
  hourly:  [{temp, real_feel, humidity, wspd, mslp, weather, predict_time}]
  daily:   [{temp_high, temp_low, humidity, wspd_day, wspd_night, mslp,
             weather_day, weather_night, predict_date}]
  aqi:     {aqi}

风速单位已统一到 m/s (与海外 km/h÷3.6 同口径, wind_convert 不动):
  实况 condition.windSpeed             = m/s  (直接用)
  逐时 forecastHour.windSpeed          = km/h (÷3.6)
  逐日 forecastDay.windSpeedDays/Nights = m/s  (double, 最可靠; windSpeedDay/Night 偶返回0不用)

时间戳: predictTime / predictDate 是 13 位毫秒, 按城市时区 detail[0].timezone 转本地字符串
15天预报来源: detail[0].forecast.forecastDay (不是 forecastDayList, 那个是空的)
降水: 新接口无 precip mm 字段, 降水量对比砍掉 (build_points 取 precip_11h 自然为 None->缺数据)
"""
import os, sys, json, requests
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import weather_pb2
from google.protobuf.json_format import MessageToDict

URL_PRD = "https://weather.api.moji.com/data/detail"           # 生产
URL_TEST = "http://192.168.20.200:6695/weather/data/detail"     # 张俊本地

# 经纬度方式请求 body 模板 (沿用 getHomeText 的 body_lonlat)
_BODY = {
    "common": {"app_version": "1009086401", "device": "MI 5", "height": 1920,
               "identifier": "mo8c02c306a1cf5721b84eb0984d8d49", "language": "CN",
               "os_version": "26", "package_name": "com.moji.mjweather", "pid": "5599",
               "platform": "Android", "uid": "209808450010611712", "width": 1080},
    "params": {"city": [{"avatarId": 8, "coordinate": 2, "cr": 1, "id": 1028595, "type": 1,
                         "lon": 116.407112, "lat": 39.904138,
                         "voice": {"lang": "CN", "tu": "c", "wu": "beau"}}]}
}


def fetch_cn_pb(lon, lat, env='prd'):
    """拉国内 proto detail 接口, 返回 pb dict (MessageToDict). 失败返回 None"""
    url = URL_PRD if env == 'prd' else URL_TEST
    body = json.loads(json.dumps(_BODY))  # 深拷贝模板, 避免污染
    body['params']['city'][0]['lon'] = float(lon)
    body['params']['city'][0]['lat'] = float(lat)
    try:
        resp = requests.post(url, data=json.dumps(body), timeout=25)
        if resp.status_code != 200:
            return None
        msg = weather_pb2.Weather()
        msg.ParseFromString(resp.content)
        d = MessageToDict(msg, preserving_proto_field_name=True)
        if d.get('code') != 0:
            return None
        return d
    except Exception:
        return None


def _ts_to_str(ms, tz_hours, fmt):
    """13位毫秒时间戳 -> 城市本地时区字符串. tz_hours=None 时用本机时区"""
    if ms is None:
        return None
    tz = timezone(timedelta(hours=tz_hours)) if tz_hours is not None else None
    return datetime.fromtimestamp(int(ms) / 1000, tz=tz).strftime(fmt)


def normalize_cn(pb):
    """pb dict -> 旧 moweather 兼容结构 {current, hourly, daily, aqi}"""
    det = (pb.get('detail') or [{}])[0]
    cond = det.get('condition') or {}
    tz_h = det.get('timezone')  # 时区(小时), 北京=8

    current = {
        'temp': cond.get('temperature'),
        'real_feel': cond.get('realFeel'),
        'humidity': cond.get('humidity'),
        'wspd': cond.get('windSpeed'),           # m/s
        'mslp': cond.get('pressure'),
        'weather': cond.get('condition'),
        # precip_1h 不设: 新接口无此字段, build_points 取不到 -> 缺数据
    }

    hourly = []
    for h in (det.get('forecastHourList') or {}).get('forecastHour') or []:
        ws = h.get('windSpeed')
        wspd = round(ws / 3.6, 2) if ws is not None else None   # km/h -> m/s
        hourly.append({
            'temp': h.get('temperature'),
            'real_feel': h.get('realFeel'),
            'humidity': h.get('humidity'),
            'wspd': wspd,
            'mslp': h.get('pressure') or None,   # 逐时气压接口偶返回0, 当缺数据
            'weather': h.get('condition'),
            'pop': h.get('pop'),                  # 降水概率(0-100)
            'predict_time': _ts_to_str(h.get('predictTime'), tz_h, '%Y-%m-%d %H:00:00'),
        })

    daily = []
    for fd in ((det.get('forecast') or {}).get('forecastDay') or []):
        daily.append({
            'temp_high': fd.get('temperatureHigh'),
            'temp_low': fd.get('temperatureLow'),
            'humidity': fd.get('humidity'),
            'wspd_day': fd.get('windSpeedDays'),      # m/s (double, 最可靠)
            'wspd_night': fd.get('windSpeedNights'),   # m/s
            'mslp': fd.get('pressure'),
            'weather_day': fd.get('conditionDay'),
            'weather_night': fd.get('conditionNight'),
            'pop': fd.get('pop'),                  # 降水概率(0-100)
            'predict_date': _ts_to_str(fd.get('predictDate'), tz_h, '%Y-%m-%d'),
            # realfeel_d / realfeel_n 不设: 新接口无此字段
        })

    aqi = det.get('aqi') or {}
    return {
        'current': current,
        'hourly': hourly,
        'daily': daily,
        'aqi': {'aqi': aqi.get('value')},
    }


def normalize_in(ind):
    """给海外 moweather 数据补 predict_time/predict_date 字符串, 供 build_points 按时次对齐.
    海外 hourly/daily 的时次字段是 pt(10位秒时间戳), 转成和国内同格式字符串(本机时区).
    国内城市都在东八区, 本机+8 与国内 det.timezone=8 一致, 能对齐匹配"""
    if not ind:
        return ind
    for h in ind.get('hourly') or []:
        pt = h.get('pt')
        if pt is not None and not h.get('predict_time'):
            h['predict_time'] = datetime.fromtimestamp(int(pt)).strftime('%Y-%m-%d %H:00:00')
    for d in ind.get('daily') or []:
        pt = d.get('pt')
        if pt is not None and not d.get('predict_date'):
            d['predict_date'] = datetime.fromtimestamp(int(pt)).strftime('%Y-%m-%d')
    return ind


def fetch_cn(lon, lat, env='prd'):
    """对外统一接口: 拉国内 + 转旧结构. 失败返回 None.
    替代 reformat_threshold.fetch_city 里的国内分支 (cn_data = fetch(cn_url))."""
    pb = fetch_cn_pb(lon, lat, env)
    if pb is None:
        return None
    return normalize_cn(pb)


if __name__ == '__main__':
    # 自测: 拉北京, 看转出的标准结构
    d = fetch_cn(116.407112, 39.904138)
    if d is None:
        print("❌ 拉取失败"); sys.exit(1)
    print("=== 实况 current ===")
    print(d['current'])
    print(f"\n=== 逐时 hourly ({len(d['hourly'])} 条), 前3条 ===")
    for h in d['hourly'][:3]:
        print(" ", h)
    print(f"\n=== 逐日 daily ({len(d['daily'])} 条), 前3条 ===")
    for fd in d['daily'][:3]:
        print(" ", fd)
    print("\n=== AQI ===")
    print(d['aqi'])
