#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉几个城市的国际/国内原始数据，对比风速和PM2.5，判断单位"""
import hashlib, hmac, subprocess, json

PASSWORD_CN = '49ff9a4e5e8bd5e8ce9e057c5adc5d2d'
PASSWORD_IN = '923ffbda8b65bf0f8e126824d050887a'
TOKEN_CN = 'cc920d85f8fbb762b6c705375add6c32'
TOKEN_IN = 'b88b7a5375e293671270016fe556a4b5'

cities = [
    ('北京',   '116.407112',  '39.904138'),
    ('新加坡', '103.819836',  '1.353444839'),
    ('纽约',   '-74.0059731', '40.7143528'),
    ('漠河',   '122.538592',  '52.97801545'),
]

def cn_key(lat, lon):
    return hashlib.md5((PASSWORD_CN+'0'+lat+lon).encode()).hexdigest()

def in_key(lat, lon):
    return hmac.new(PASSWORD_IN.encode(), ('0'+lat+lon).encode(), hashlib.sha256).hexdigest()

def fetch(url):
    r = subprocess.run(['curl','-sk','--max-time','15',url], capture_output=True, text=True)
    try: return json.loads(r.stdout).get('data',{})
    except: return {}

print("="*90)
print("【风速对比】 国内 wspd(m/s?) + wind_level  vs  国际 wspd + wl")
print("="*90)
print(f"{'城市':<6}{'国内wspd':>10}{'国内风级':>8}{'国际wspd':>10}{'国际wl':>7}{'国际wspd/3.6':>13}{'→换算m/s对应风级':>18}")
print("-"*90)
# 蒲福风级 m/s 范围
beaufort = [(0,0.3),(1,1.5),(2,3.3),(3,5.4),(4,7.9),(5,10.7),(6,13.8),(7,17.1),(8,20.7)]
def level_of(ms):
    for i,(lo,hi) in enumerate(beaufort):
        if ms<=hi: return i
    return 9
for name,lon,lat in cities:
    cn_url = f'http://coapi.moji.com/whapi/v2/weather?timestamp=0&token={TOKEN_CN}&lat={lat}&lon={lon}&key={cn_key(lat,lon)}'
    in_url = f'https://datasw1.api.moweather.com/whapi/in/weather?token={TOKEN_IN}&lon={lon}&lat={lat}&lang=zh-CN&current=1&ts=0&key={in_key(lat,lon)}'
    cn = fetch(cn_url).get('current',{})
    inc = fetch(in_url).get('current',{})
    cw = cn.get('wspd'); cl = cn.get('wind_level')
    iw = inc.get('wspd'); iwl = inc.get('wl')
    conv = f"{iw/3.6:.2f}" if isinstance(iw,(int,float)) else '-'
    lv = level_of(iw/3.6) if isinstance(iw,(int,float)) else '-'
    print(f"{name:<6}{str(cw):>10}{str(cl):>8}{str(iw):>10}{str(iwl):>7}{conv:>13}{str(lv):>18}")

print()
print("="*90)
print("【PM2.5 / 污染物对比】 国内(μg/m3) vs 国际")
print("="*90)
print(f"{'城市':<6}{'国内aqi':>8}{'国内pm25':>9}{'国内pm10':>9}{'国际AQI':>8}{'国际PM2P5':>10}{'国际PM10':>9}{'PM2.5<PM10?':>12}")
print("-"*90)
for name,lon,lat in cities:
    cn_url = f'http://coapi.moji.com/whapi/v2/weather?timestamp=0&token={TOKEN_CN}&lat={lat}&lon={lon}&key={cn_key(lat,lon)}'
    in_url = f'https://datasw1.api.moweather.com/whapi/in/weather?token={TOKEN_IN}&lon={lon}&lat={lat}&lang=zh-CN&aqi=1&ts=0&key={in_key(lat,lon)}'
    cna = fetch(cn_url).get('aqi',{})
    ina = fetch(in_url).get('aqi',{})
    ca=cna.get('aqi'); cp25=cna.get('pm25'); cp10=cna.get('pm10')
    ia=ina.get('AQI'); ip25=ina.get('PM2P5'); ip10=ina.get('PM10')
    ok = (ip25 < ip10) if isinstance(ip25,(int,float)) and isinstance(ip10,(int,float)) else '?'
    print(f"{name:<6}{str(ca):>8}{str(cp25):>9}{str(cp10):>9}{str(ia):>8}{str(ip25):>10}{str(ip10):>9}{str(ok):>12}")

print()
print("="*90)
print("【北京国际 AQI 模块完整原始值】(给你看 PM2P5 上下文)")
print("="*90)
in_url = f'https://datasw1.api.moweather.com/whapi/in/weather?token={TOKEN_IN}&lon=116.407112&lat=39.904138&lang=zh-CN&aqi=1&ts=0&key={in_key("39.904138","116.407112")}'
ina = fetch(in_url).get('aqi',{})
for k,v in ina.items(): print(f"  {k} = {v}")
