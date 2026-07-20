#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阈值口径一致性比对 - 配置驱动
规则全部在 compare_config.yaml, 改配置不改代码
输出: 一致性比对报告_阈值口径.xlsx (不覆盖严格相等版)
"""
import json, glob, os, datetime
import yaml
import openpyxl
from openpyxl.styles import Font, PatternFill

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, '..', 'data')
JSON_DIR = os.path.join(BASE, '比对结果', '原始JSON')
TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d_%H%M')
XLSX = os.path.join(BASE, '比对结果', f'一致性比对报告_阈值口径_{TIMESTAMP}.xlsx')
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'compare_config.yaml')

# 读配置
config=yaml.safe_load(open(CONFIG_PATH,encoding='utf-8'))
THRESHOLDS=config['thresholds']
WIND_CFG=config['wind_convert']
MODULES=config['modules']

# 24小时时效分段
PERIODS_24H = [
    ('短时效(1-6h)', 0, 6),
    ('中时效(7-12h)', 6, 12),
    ('长时效(13-24h)', 12, 24),
]

def num(v):
    if v is None: return None
    try: return float(v)
    except: return None

def wind_convert(v):
    if v is None or not WIND_CFG.get('enabled'): return v
    return round(v/WIND_CFG['divisor'],2)

def text_diff(cv,iv):
    if cv is None or iv is None: return ''
    return '一致' if cv==iv else '不一致'

def get_threshold(field):
    """按字段名匹配阈值(支持'温度(最高)'等带括号字段)"""
    for k,v in THRESHOLDS.items():
        if k in field: return v
    return None

def get_period_label(source, idx):
    """根据模块和数据索引返回时效分段标签"""
    if source != 'hourly':
        return ''
    for label, start, end in PERIODS_24H:
        if start <= idx < end:
            return label
    return ''

def cmp_point(city,module,field,ts,cnv,iv,spec,period=''):
    """单个数据点比对, 返回10元组行(含period)"""
    typ=spec.get('type','numeric'); note=spec.get('note','')
    if typ=='wind':
        cv=num(cnv); iv_conv=wind_convert(num(iv))
        if WIND_CFG.get('enabled') and iv is not None:
            note=f"海外原{iv} ÷{WIND_CFG['divisor']}"
    elif typ=='weather':
        cv=cnv; iv_conv=iv
    else:
        cv=num(cnv); iv_conv=num(iv)
    # 天气: 文字比对, 差异列空
    if typ=='weather':
        ok=text_diff(cv,iv_conv)
        return (city,module,field,ts,cnv,iv,'',ok,note or '按中文文字比对',period)
    # 数值: 缺数据 or 阈值判定
    if cv is None or iv_conv is None:
        return (city,module,field,ts,cnv,iv,'','缺数据',note,period)
    diff=round(cv-iv_conv,2)
    th=get_threshold(field)
    ok='一致' if (th is not None and abs(diff)<=th) else '不一致'
    return (city,module,field,ts,cv,iv_conv,diff,ok,note,period)

def points(city,cn,ind):
    P=[]
    for module,mspec in MODULES.items():
        source=mspec['source']; fields=mspec['fields']
        if mspec.get('multi'):
            cn_arr=cn.get(source,[])[:mspec.get('limit',99)]
            ind_arr=ind.get(source,[])[:mspec.get('limit',99)]
            ts_key=mspec.get('ts_key'); lim=mspec.get('limit',99)
            for k in range(min(len(cn_arr),len(ind_arr),lim)):
                a=cn_arr[k]; b=ind_arr[k]
                ts=a.get(ts_key,f'第{k+1}') if ts_key else f'第{k+1}'
                period=get_period_label(source,k)
                for field,spec in fields.items():
                    P.append(cmp_point(city,module,field,ts,a.get(spec['cn']),b.get(spec['intl']),spec,period))
        else:
            cn_mod=cn.get(source,{}); ind_mod=ind.get(source,{})
            ts=mspec.get('ts_label','')
            for field,spec in fields.items():
                P.append(cmp_point(city,module,field,ts,cn_mod.get(spec['cn']),ind_mod.get(spec['intl']),spec))
    return P

def main():
    cn_files=sorted(glob.glob(f'{JSON_DIR}/*_国内.json'))
    allP=[]
    for cf in cn_files:
        city=os.path.basename(cf).replace('_国内.json','')
        inf=cf.replace('_国内.json','_国际.json')
        if not os.path.exists(inf): continue
        cn=json.load(open(cf,encoding='utf-8')); ind=json.load(open(inf,encoding='utf-8'))
        allP+=points(city,cn,ind)

    city_count=len(cn_files)
    print(f"城市数:{city_count} 数据点:{len(allP)} (配置: {CONFIG_PATH})")

    wb=openpyxl.Workbook()

    # ============ Sheet1 数据明细 ============
    ws=wb.active; ws.title='数据明细'
    H=['城市','模块','字段','时次','国内值','海外值','差异','是否一致','备注','时效分段']
    ws.append(H)
    for c in range(1,len(H)+1): ws.cell(row=1,column=c).font=Font(bold=True)
    green=PatternFill('solid',fgColor='E6F7E6'); red=PatternFill('solid',fgColor='FFE6E6'); gray=PatternFill('solid',fgColor='F0F0F0')
    for p in allP: ws.append(list(p))
    for i,p in enumerate(allP,2):
        cell=ws.cell(row=i,column=8)
        if p[7]=='一致': cell.fill=green
        elif p[7]=='不一致': cell.fill=red
        else: cell.fill=gray
    for col,w in zip('ABCDEFGHIJ',[12,10,14,18,14,14,10,10,22,14]): ws.column_dimensions[col].width=w
    ws.freeze_panes='A2'

    # ============ Sheet2 总结 ============
    ws2=wb.create_sheet('总结')
    from collections import defaultdict
    # stat key: (field, module, period)
    stat=defaultdict(lambda:{'total':0,'miss':0,'n':0,'ok':0,'sumdiff':0,'maxdiff':0,'maxcity':''})
    for p in allP:
        city,module,field,ts,cnv,iv,diff,ok,note,period=p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9]
        s=stat[(field,module,period)]; s['total']+=1
        if ok in('缺数据',''):
            s['miss']+=1; continue
        s['n']+=1
        if ok=='一致': s['ok']+=1
        if isinstance(diff,(int,float)):
            s['sumdiff']+=abs(diff)
            if abs(diff)>abs(s['maxdiff']): s['maxdiff']=diff; s['maxcity']=city
    H2=['字段','模块','时效','总数据','缺数据(已排除)','有效样本','一致数','一致率','平均偏差','最大偏差','最大偏差城市']
    ws2.append(H2)
    for c in range(1,len(H2)+1): ws2.cell(row=1,column=c).font=Font(bold=True)
    PERIOD_ORDER = {p[0]: i for i, p in enumerate(PERIODS_24H)}
    for module in MODULES.keys():
        for (field,m,period),s in sorted(stat.items(), key=lambda x: (x[0][1], list(MODULES.keys()).index(x[0][1]) if x[0][1] in MODULES else 99, x[0][0], PERIOD_ORDER.get(x[0][2], 99))):
            if m!=module: continue
            rate=f"{s['ok']/s['n']*100:.1f}%" if s['n'] else '0'
            avgdiff=round(s['sumdiff']/s['n'],2) if s['n'] else ''
            ws2.append([field,m,period,s['total'],s['miss'],s['n'],s['ok'],rate,avgdiff,s['maxdiff'],s['maxcity']])
    for col,w in zip('ABCDEFGHIJK',[16,10,14,8,14,10,8,10,10,10,14]): ws2.column_dimensions[col].width=w
    ws2.freeze_panes='A2'

    # ============ Sheet3 说明 ============
    ws3=wb.create_sheet('说明')
    notes=['一致性比对说明 - 阈值口径(配置驱动)', '', '配置文件: compare_config.yaml', '']
    notes.append(f'报告生成: {city_count}个城市, {len(allP)}个数据点')
    notes.append('')
    notes.append('一、一致判定阈值(来自配置):')
    for k,v in THRESHOLDS.items():
        notes.append(f'  {k} |差|≤{v}')
    notes.append('  天气现象 中文文字完全一致')
    notes.append('  缺数据 标"缺数据",不计入一致率分母')
    notes.append('')
    notes.append('二、风速换算(来自配置):')
    notes.append(f"  enabled={WIND_CFG.get('enabled')}, divisor={WIND_CFG.get('divisor')} (海外÷{WIND_CFG.get('divisor')}换算m/s)")
    notes.append('')
    notes.append('三、24小时时效分段统计:')
    notes.append('  短时效(1-6h): 第1~6小时')
    notes.append('  中时效(7-12h): 第7~12小时')
    notes.append('  长时效(13-24h): 第13~24小时')
    notes.append('')
    notes.append('四、字段映射(来自配置):')
    for module,mspec in MODULES.items():
        notes.append(f'  [{module}] source={mspec["source"]} multi={mspec.get("multi")} limit={mspec.get("limit","-")}')
        for field,spec in mspec['fields'].items():
            notes.append(f'    {field}: 国内={spec["cn"]} 海外={spec["intl"]} type={spec["type"]}'+(f' note={spec["note"]}' if spec.get('note') else ''))
    notes.append('')
    notes.append('五、其他:')
    notes.append('  1. 天气现象按中文文字比对(国内language=zh-CN + 国际lang=zh-CN)')
    notes.append('  2. 时次对齐: 24h按predict_time, 15天按predict_date, 转北京时区')
    notes.append('  3. 国内不覆盖城市(伦敦/纽约等海外)未纳入')
    notes.append('  4. 差异列: 数值=国内-海外(正值国内大); 天气现象差异列空, 看「是否一致」列')
    notes.append('')
    notes.append('注: 本报告阈值口径(允许合理偏差); 严格相等版见「一致性比对报告.xlsx」')
    notes.append('    修改 compare_config.yaml 后重跑即可更新口径')
    for n in notes: ws3.append([n])
    ws3['A1'].font=Font(bold=True,size=13)

    wb.save(XLSX)
    print(f"✅ 已生成: {XLSX}")

if __name__=='__main__':
    main()
