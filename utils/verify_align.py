#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单城市验证：北京，检查时次对齐 + 字段对应 + 风速换算"""
import hashlib, hmac, subprocess, json
from datetime import datetime, timezone, timedelta

PASSWORD_CN='49ff9a4e5e8bd5e8ce9e057c5adc5d2d'
PASSWORD_IN='923ffbda8b65bf0f8e126824d050887a'
TOKEN_CN='cc920d85f8fbb762b6c705375add6c32'
TOKEN_IN='b88b7a5375e293671270016fe556a4b5'
lon,lat='116.407112','39.904138'

def cn_key(la,lo): return hashlib.md5((PASSWORD_CN+'0'+la+lo).encode()).hexdigest()
def in_key(la,lo): return hmac.new(PASSWORD_IN.encode(),('0'+la+lo).encode(),hashlib.sha256).hexdigest()

def fetch(url):
    r=subprocess.run(['curl','-sk','--max-time','20',url],capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except: return {}

# 国内完整
cn=fetch(f'http://coapi.moji.com/whapi/v2/weather?timestamp=0&token={TOKEN_CN}&lat={lat}&lon={lon}&key={cn_key(lat,lon)}')['data']
# 国际完整(全模块)
in_url=f'https://datasw1.api.moweather.com/whapi/in/weather?token={TOKEN_IN}&lon={lon}&lat={lat}&lang=zh-CN&current=1&hourly=24&daily=15&aqi=1&ts=0&metric=true&key={in_key(lat,lon)}'
ind=fetch(in_url)['data']

print("="*70); print("【hourly 时次对齐】 国内前3条 vs 国际前3条"); print("="*70)
print(f"{'idx':<4}{'国内predict_time':<24}{'国际pt(UTC)':<22}{'国际pt转北京':<22}")
for i in range(3):
    ct=cn['hourly'][i].get('predict_time','-')
    pt=ind['hourly'][i].get('pt')
    pt_utc=datetime.fromtimestamp(pt,tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if pt else '-'
    pt_bj=datetime.fromtimestamp(pt,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M') if pt else '-'
    print(f"{i:<4}{ct:<24}{pt_utc:<22}{pt_bj:<22}")

print(); print("="*70); print("【daily 日期对齐】 前3条"); print("="*70)
print(f"{'idx':<4}{'国内predict_date':<16}{'国际pt转日期(北京)':<22}")
for i in range(3):
    cd=cn['daily'][i].get('predict_date','-')
    pt=ind['daily'][i].get('pt')
    pd=datetime.fromtimestamp(pt,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d') if pt else '-'
    print(f"{i:<4}{cd:<16}{pd:<22}")

print(); print("="*70); print("【字段对应 + 风速换算验证】 实况"); print("="*70)
c=cn['current']; i=ind['current']
print(f"温度:      国内temp={c.get('temp')}      国际temp={i.get('temp')}")
print(f"体感:      国内real_feel={c.get('real_feel')}   国际rf={i.get('rf')}")
print(f"湿度:      国内humidity={c.get('humidity')}    国际rh={i.get('rh')}")
print(f"气压:      国内mslp={c.get('mslp')}      国际sp={i.get('sp')}")
print(f"风速:      国内wspd={c.get('wspd')}(m/s)  国际wspd={i.get('wspd')}  换算={round(i.get('wspd',0)/3.6,2) if i.get('wspd') else '-'}(m/s)")
print(f"天气id:    国内weather_id={c.get('weather_id')}  国际wtrid={i.get('wtrid')}")
print(f"天气文字:  国内weather={c.get('weather')}  国际wtr={i.get('wtr')}")

print(); print("="*70); print("【字段对应】 hourly第1条"); print("="*70)
ch=cn['hourly'][0]; ih=ind['hourly'][0]
print(f"温度: temp={ch.get('temp')} / {ih.get('temp')}")
print(f"体感: real_feel={ch.get('real_feel')} / rf={ih.get('rf')}")
print(f"湿度: humidity={ch.get('humidity')} / rh={ih.get('rh')}")
print(f"气压: mslp={ch.get('mslp')} / sp={ih.get('sp')}")
print(f"风速: wspd={ch.get('wspd')} / {ih.get('wspd')}(换算{round(ih.get('wspd',0)/3.6,2) if ih.get('wspd') else '-'})")
print(f"天气id: weather_id={ch.get('weather_id')} / wtrid={ih.get('wtrid')}")

print(); print("="*70); print("【字段对应】 daily第1条 (注意白天/夜间双值)"); print("="*70)
cd_=cn['daily'][0]; id_=ind['daily'][0]
print(f"温度(高): temp_high={cd_.get('temp_high')} / temph={id_.get('temph')}")
print(f"温度(低): temp_low={cd_.get('temp_low')} / templ={id_.get('templ')}")
print(f"体感(白天): realfeel_d={cd_.get('realfeel_d')} / rfd={id_.get('rfd')}")
print(f"体感(夜间): realfeel_n={cd_.get('realfeel_n')} / rfn={id_.get('rfn')}")
print(f"湿度: humidity={cd_.get('humidity')} / rh={id_.get('rh')}")
print(f"气压: mslp={cd_.get('mslp')} / spd={id_.get('spd')}(白天) spn={id_.get('spn')}(夜间)")
print(f"风速(白天): wspd_day={cd_.get('wspd_day')} / wspdd={id_.get('wspdd')}(换算{round(id_.get('wspdd',0)/3.6,2) if id_.get('wspdd') else '-'})")
print(f"风速(夜间): wspd_night={cd_.get('wspd_night')} / wspdn={id_.get('wspdn')}(换算{round(id_.get('wspdn',0)/3.6,2) if id_.get('wspdn',0) else '-'})")
print(f"天气id(白天): weather_id_day={cd_.get('weather_id_day')} / wtridd={id_.get('wtridd')}")
print(f"天气id(夜间): weather_id_night={cd_.get('weather_id_night')} / wtridn={id_.get('wtridn')}")

print(); print("="*70); print("【AQI模块】"); print("="*70)
print(f"AQI: 国内aqi={cn['aqi'].get('aqi')} / 国际AQI={ind['aqi'].get('AQI')}")
print(f"PM2.5: 国内pm25={cn['aqi'].get('pm25')} / 国际PM2P5={ind['aqi'].get('PM2P5')}")
