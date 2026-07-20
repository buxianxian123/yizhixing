#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新请求国内70城市(加language=zh-CN返回中文)，覆盖JSON"""
import hashlib,subprocess,json,csv,glob,os,time
PASSWORD_CN='49ff9a4e5e8bd5e8ce9e057c5adc5d2d'
TOKEN_CN='cc920d85f8fbb762b6c705375add6c32'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, '..', 'data', '天气一致性测试城市_热门城市筛选.csv')
JSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', '比对结果', '原始JSON')
def cn_key(lat,lon): return hashlib.md5((PASSWORD_CN+'0'+lat+lon).encode()).hexdigest()
def fetch(url,retry=2):
    for _ in range(retry+1):
        r=subprocess.run(['curl','-sk','--max-time','25',url],capture_output=True,text=True)
        try:
            d=json.loads(r.stdout)
            if d.get('code')==0: return d.get('data',{})
        except: pass
        time.sleep(0.5)
    return None
existing=[os.path.basename(f).replace('_国内.json','') for f in glob.glob(f'{JSON_DIR}/*_国内.json')]
city_ll={}
with open(CSV_PATH,'r',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        city_ll[r['Fcityname_cn'].strip()]=(r['Flon'].strip(),r['Flat'].strip())
n=0
for idx,name in enumerate(existing,1):
    if name not in city_ll: continue
    lon,lat=city_ll[name]
    url=f'http://coapi.moji.com/whapi/v2/weather?timestamp=0&token={TOKEN_CN}&lat={lat}&lon={lon}&key={cn_key(lat,lon)}&language=zh-CN'
    cn=fetch(url)
    if cn:
        json.dump(cn,open(f'{JSON_DIR}/{name}_国内.json','w',encoding='utf-8'),ensure_ascii=False)
        n+=1
    if idx%10==0: print(f'[{idx}/{len(existing)}]')
print(f'✅ 重新请求国内(中文) {n} 个城市')
