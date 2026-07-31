#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时全量拉取原始文件（和比对解耦：只拉不比，不存比对结果）

国内: proto detail 接口(POST, pb 二进制)
      - 存 国内.pb   = 接口返回的原始 protobuf 二进制(最原始, 未来 proto 加字段也不丢)
      - 存 国内.json = pb ParseFromString -> MessageToDict(含顶层 radar.rain / condition / forecast / aqi
                      全量, 未做 normalize, 留给后面定比对规则时直接取)
国际: moweather json 接口(GET, 完整字段集: current/nowcast/hourly/daily/aqi/aqiForecastHourly/alert)
      - nowcast 短时降水模块带着国际版 rain, 正好和国内 radar.rain 对得上
      - 存 国际.json = 接口返回的原始响应文本(含 code/message/data 全量)

每轮全量拉一遍所有城市, 按时间戳存盘, 不做任何比对/均值/报告。
比对规则定了之后, 单独写脚本读这里存好的原始文件跑比对即可。

运行:  python3 utils/raw_pull.py          (Ctrl-C 优雅停止)
测试:  SC_INTERVAL=600 SC_MAX_ROUNDS=2 python3 utils/raw_pull.py   (10分钟一轮, 跑2轮退出)
间隔:  compare_config.yaml -> schedule.interval_seconds (默认 3600=每1小时)
"""
import os, sys, json, time, datetime, subprocess
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reformat_threshold as rt        # load_cities / config
import gen_all_urls as gu               # gen_in_url (完整字段集, 含 nowcast)
import weather_pb2
from google.protobuf.json_format import MessageToDict
from fetch_cn_pb import _BODY, URL_PRD, URL_TEST

# ====== 路径 ======
BASE = os.path.join(HERE, '..', 'data')
RAW_DIR = os.path.join(BASE, '原始拉取')            # 和 data/比对结果 分开, 纯原始留底

# ====== 调度配置(支持环境变量覆盖, 便于小窗口测试) ======
SCHED = rt.config['schedule']
INTERVAL = int(os.environ.get('SC_INTERVAL', SCHED['interval_seconds']))
MAX_ROUNDS = int(os.environ.get('SC_MAX_ROUNDS', '0'))   # 0=无限循环; >0=跑满N轮退出
CN_ENV = os.environ.get('CN_ENV', 'prd')                  # prd / test(张俊本地)


def now_str():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


# =========================================================
# 国内: POST proto detail, 返回 (raw_pb_bytes, pb_dict)
# =========================================================
def fetch_cn_raw(lon, lat, env=CN_ENV):
    """拉国内 proto detail, 一次请求同时拿到 原始二进制 + pb dict。
    失败返回 (None, None)。和 fetch_cn_pb 同口径, 只是多留一份 raw bytes"""
    url = URL_PRD if env == 'prd' else URL_TEST
    body = json.loads(json.dumps(_BODY))   # 深拷贝模板, 避免污染
    body['params']['city'][0]['lon'] = float(lon)
    body['params']['city'][0]['lat'] = float(lat)
    try:
        resp = requests.post(url, data=json.dumps(body), timeout=25)
        if resp.status_code != 200:
            return None, None
        raw = resp.content
        msg = weather_pb2.Weather()
        msg.ParseFromString(raw)
        d = MessageToDict(msg, preserving_proto_field_name=True)
        if d.get('code') != 0:
            return None, None
        return raw, d
    except Exception:
        return None, None


# =========================================================
# 国际: GET moweather json (完整字段集), 返回 (raw_text, full_dict)
# =========================================================
def fetch_in_raw(lat, lon, retry=2):
    """拉国际版完整字段接口(含 nowcast 短时降水 / alert / aqiForecastHourly)。
    返回 (原始响应文本, 完整解析 dict)。失败返回 (None, None)。
    用 curl -sk, 和 reformat_threshold.fetch 同口径(auth/TLS 已验证)"""
    url = gu.gen_in_url(lat, lon)
    for _ in range(retry + 1):
        r = subprocess.run(['curl', '-sk', '--max-time', '25', url],
                           capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            if d.get('code') == 0:
                return r.stdout, d
        except Exception:
            pass
        time.sleep(0.5)
    return None, None


# =========================================================
# 单轮全量拉取
# =========================================================
def pull_round(cities):
    """全量拉一轮。存盘: 原始拉取/原始_<时间戳>/<城市>/{国内.pb, 国内.json, 国际.json}
    返回 dict: {ts, ok, fail, out_dir}"""
    ts = now_str()
    top = os.path.join(RAW_DIR, f'原始_{ts}')
    os.makedirs(top, exist_ok=True)

    ok = 0
    failed = []
    seen_name = {}   # 城市名去重(防台北等同名不同经纬度撞目录)

    for idx, (name, lon, lat) in enumerate(cities, 1):
        # 目录名去重: 同名不同经纬度时追加经纬度
        dirname = name
        if dirname in seen_name:
            dirname = f'{name}_{lon}_{lat}'
        else:
            seen_name[dirname] = True
        city_dir = os.path.join(top, dirname)
        os.makedirs(city_dir, exist_ok=True)

        # 国内: 原始 pb 二进制 + pb dict(未 normalize, 含 radar)
        cn_raw, cn_dict = fetch_cn_raw(lon, lat)
        if cn_raw is not None:
            with open(os.path.join(city_dir, '国内.pb'), 'wb') as f:
                f.write(cn_raw)
        if cn_dict is not None:
            with open(os.path.join(city_dir, '国内.json'), 'w', encoding='utf-8') as f:
                json.dump(cn_dict, f, ensure_ascii=False)

        # 国际: 原始响应文本(含 nowcast 短时降水里的 rain)
        in_text, in_dict = fetch_in_raw(lat, lon)
        if in_text is not None:
            with open(os.path.join(city_dir, '国际.json'), 'w', encoding='utf-8') as f:
                f.write(in_text)

        miss = []
        if cn_dict is None: miss.append('国内')
        if in_dict is None: miss.append('国际')
        if miss:
            failed.append({'city': name, 'miss': '/'.join(miss)})
            print(f"  [{idx}/{len(cities)}] ⚠️ {name} {'/'.join(miss)} 失败")
        else:
            ok += 1
        if idx % 10 == 0 or idx == len(cities):
            print(f"  [{idx}/{len(cities)}] {name} ✅")

    # 轮次清单
    manifest = {
        'timestamp': ts,
        'pull_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cities_total': len(cities),
        'ok': ok,
        'fail': len(failed),
        'failed': failed,
        'interval_seconds': INTERVAL,
        'cn_env': CN_ENV,
        'note': '国内.pb=原始protobuf二进制; 国内.json=pb dict(含radar/condition/forecast/aqi全量); '
                '国际.json=完整响应文本(含nowcast短时降水rain/alert/aqiForecastHourly)',
    }
    with open(os.path.join(top, '_manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    # latest 指针, 方便找最新一轮
    with open(os.path.join(RAW_DIR, '_latest.txt'), 'w', encoding='utf-8') as f:
        f.write(top)
    return {'ts': ts, 'ok': ok, 'fail': len(failed), 'out_dir': top}


# =========================================================
# 主循环
# =========================================================
def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    cities = rt.load_cities()

    print(f"\n{'='*60}")
    print(f"定时全量拉取原始文件启动 (和比对解耦, 只拉不比)")
    print(f"  城市: {len(cities)} 城")
    print(f"  间隔: 每 {INTERVAL}s 拉一轮" +
          (f" (跑满 {MAX_ROUNDS} 轮退出)" if MAX_ROUNDS else " (无限循环)"))
    print(f"  国内: proto detail (env={CN_ENV}) -> 国内.pb + 国内.json")
    print(f"  国际: moweather 完整字段(含 nowcast 短时降水) -> 国际.json")
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
