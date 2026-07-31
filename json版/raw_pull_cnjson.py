#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时全量拉取原始文件 - json版(coapi)（和比对解耦：只拉不比）

国内: coapi json 接口(GET, MD5 鉴权)
      - 存 国内.json = coapi 返回的 data(current/hourly/daily/aqi 旧 moweather 兼容结构)
国际: moweather json 接口(GET)
      - 存 国际.json = 接口返回的 data

每轮全量拉一遍所有城市, 按时间戳存盘到 data/原始拉取_json/, 不做任何比对/均值/报告。
scheduled_compare_cnjson.py / gen_report_from_raw_cnjson.py 读这里存好的原始文件跑比对。

⚠️ coapi 接口可用性未知, 若拉不到(code!=0), 留底会缺城市。
运行:  python3 json版/raw_pull_cnjson.py          (Ctrl-C 优雅停止)
测试:  SC_INTERVAL=600 SC_MAX_ROUNDS=2 python3 json版/raw_pull_cnjson.py
间隔:  compare_config_cnjson.yaml -> schedule.interval_seconds (默认 3600)
"""
import os, sys, json, time, datetime
import reformat_threshold_cnjson as rt

HERE = os.path.dirname(os.path.abspath(__file__))

# ====== 路径 ======
BASE = os.path.join(HERE, '..', 'data')
RAW_DIR = os.path.join(BASE, '原始拉取_json')            # 和 proto 的 原始拉取 分开, coapi 留底

# ====== 调度配置 ======
SCHED = rt.config['schedule']
INTERVAL = int(os.environ.get('SC_INTERVAL', SCHED['interval_seconds']))
MAX_ROUNDS = int(os.environ.get('SC_MAX_ROUNDS', '0'))   # 0=无限循环; >0=跑满N轮退出


def now_str():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


# 国内: coapi GET, 返回 data dict (失败 None)
def fetch_cn_raw(lat, lon):
    return rt.fetch(rt.cn_url(lat, lon))


# 国际: moweather GET, 返回 data dict (失败 None)
def fetch_in_raw(lat, lon):
    return rt.fetch(rt.in_url_full(lat, lon))


def pull_round(cities):
    ts = now_str()
    top = os.path.join(RAW_DIR, f'原始_{ts}')
    os.makedirs(top, exist_ok=True)

    ok = 0
    failed = []
    seen_name = {}

    for idx, (name, lon, lat) in enumerate(cities, 1):
        dirname = name
        if dirname in seen_name:
            dirname = f'{name}_{lon}_{lat}'
        else:
            seen_name[dirname] = True
        city_dir = os.path.join(top, dirname)
        os.makedirs(city_dir, exist_ok=True)

        cn_data = fetch_cn_raw(lat, lon)
        if cn_data is not None:
            with open(os.path.join(city_dir, '国内.json'), 'w', encoding='utf-8') as f:
                json.dump(cn_data, f, ensure_ascii=False)

        in_data = fetch_in_raw(lat, lon)
        if in_data is not None:
            with open(os.path.join(city_dir, '国际.json'), 'w', encoding='utf-8') as f:
                json.dump(in_data, f, ensure_ascii=False)

        miss = []
        if cn_data is None: miss.append('国内')
        if in_data is None: miss.append('国际')
        if miss:
            failed.append({'city': name, 'miss': '/'.join(miss)})
            print(f"  [{idx}/{len(cities)}] ⚠️ {name} {'/'.join(miss)} 失败")
        else:
            ok += 1
        if idx % 10 == 0 or idx == len(cities):
            print(f"  [{idx}/{len(cities)}] {name} ✅")

    manifest = {
        'timestamp': ts,
        'pull_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cities_total': len(cities),
        'ok': ok,
        'fail': len(failed),
        'failed': failed,
        'interval_seconds': INTERVAL,
        'note': '国内.json=coapi data(current/hourly/daily/aqi); 国际.json=moweather data',
    }
    with open(os.path.join(top, '_manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(RAW_DIR, '_latest.txt'), 'w', encoding='utf-8') as f:
        f.write(top)
    return {'ts': ts, 'ok': ok, 'fail': len(failed), 'out_dir': top}


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    cities = rt.load_cities()

    print(f"\n{'='*60}")
    print(f"定时全量拉取原始文件启动 - json版(coapi) (和比对解耦, 只拉不比)")
    print(f"  城市: {len(cities)} 城")
    print(f"  间隔: 每 {INTERVAL}s 拉一轮" +
          (f" (跑满 {MAX_ROUNDS} 轮退出)" if MAX_ROUNDS else " (无限循环)"))
    print(f"  国内: coapi json (GET/MD5) -> 国内.json")
    print(f"  国际: moweather json (GET) -> 国际.json")
    print(f"  存盘: {RAW_DIR}/原始_<时间戳>/<城市>/")
    print(f"{'='*60}")

    rounds_done = 0
    try:
        while True:
            print(f"\n[{datetime.datetime.now():%H:%M:%S}] 第 {rounds_done+1}" +
                  (f"/{MAX_ROUNDS}" if MAX_ROUNDS else "") + f" 轮全量拉取开始")
            r = pull_round(cities)
            rounds_done += 1
            print(f"✅ 第 {rounds_done} 轮完成: 成功 {r['ok']}/{len(cities)}, 失败 {r['fail']}")
            print(f"   存盘: {r['out_dir']}")
            if MAX_ROUNDS and rounds_done >= MAX_ROUNDS:
                print(f"\n已跑满 {MAX_ROUNDS} 轮, 退出")
                break
            print(f"   休眠 {INTERVAL}s 后下一轮... (Ctrl-C 可停止)")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n收到 Ctrl-C, 优雅停止 (已完成 {rounds_done} 轮)")


if __name__ == '__main__':
    main()
