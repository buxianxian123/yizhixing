#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时均值比对（常驻脚本）
每 interval_seconds 秒全量拉一次 -> 累积；攒满 avg_count 次后取平均 -> 出一份均值报告。
数值字段取均值、天气现象取众数，再跑一次比对，报告格式与一次性脚本一致，只是数据更稳。
运行: python3 scheduled_compare.py   (Ctrl-C 优雅停止，状态落盘可续跑)
配置: compare_config.yaml -> schedule 段
"""
import os, sys, csv, json, time, datetime
from collections import Counter

import reformat_threshold as rt   # 复用 fetch_city/load_cities/build_points/gen_xlsx/calc_weather_deviation/get_threshold

# ====== 路径配置 ======
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = rt.OUT_DIR                       # data/比对结果
STATE_PATH = os.path.join(OUT_DIR, '.均值累积状态.json')
RAW_DIR = os.path.join(OUT_DIR, '原始JSON_均值')

# ====== 读调度配置（支持环境变量覆盖，便于小窗口测试，不设则用配置值）======
SCHED = rt.config['schedule']
INTERVAL = int(os.environ.get('SC_INTERVAL', SCHED['interval_seconds']))
AVG_COUNT = int(os.environ.get('SC_AVG_COUNT', SCHED['avg_count']))
KEEP_RAW = SCHED.get('keep_raw', True)
MAX_WINDOWS = int(os.environ.get('SC_MAX_WINDOWS', '0'))   # 0=无限循环; >0=跑满N个窗口后退出


def now_str():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M')


# =========================================================
# 第一部分：单次拉取 + 累积
# =========================================================

def pull_once(cities, out_dir, pull_n):
    """全量拉一次。返回 (points列表, 成功城数, 跳过城数)。
    原始JSON完整保存(不加工)：原始json_{时间戳}/{城市}_{时间戳}/国内.json + 国际.json。
    points 未合并进累积器，由调用方在整次拉取成功后合并（中断可丢弃，不污染累积器）"""
    pts_all = []
    ok = 0; skip = 0
    ts = now_str()
    raw_top = os.path.join(out_dir, f'原始json_{ts}')
    for idx, (name, lon, lat) in enumerate(cities, 1):
        cn_data, in_data = rt.fetch_city(name, lon, lat)
        if cn_data is None:
            skip += 1
            print(f"  [{idx}/{len(cities)}] ⏭️ {name} 国内接口失败, 跳过")
            continue
        if in_data is None:
            skip += 1
            print(f"  [{idx}/{len(cities)}] ⏭️ {name} 国际接口失败, 跳过")
            continue
        if KEEP_RAW:
            city_dir = os.path.join(raw_top, f'{name}_{ts}')
            os.makedirs(city_dir, exist_ok=True)
            with open(os.path.join(city_dir, '国内.json'), 'w', encoding='utf-8') as f:
                json.dump(cn_data, f, ensure_ascii=False)
            with open(os.path.join(city_dir, '国际.json'), 'w', encoding='utf-8') as f:
                json.dump(in_data, f, ensure_ascii=False)
        # build_points 一次即可：strict 只影响 ok/diff，cn/iv 原值两种口径相同
        pts_all += rt.build_points(name, cn_data, in_data, strict=False)
        ok += 1
        if idx % 10 == 0 or idx == len(cities):
            print(f"  [{idx}/{len(cities)}] {name} ✅")
    return pts_all, ok, skip


def merge_pull(acc, pts):
    """把一次拉取的 points 合并进累积器。
    acc: {(城市,模块,字段,时次): {'cn':[], 'iv':[], 'period':str}}"""
    for p in pts:
        city, module, field, ts, cnv, iv, _diff, _ok, _note, period = p
        key = (city, module, field, ts)
        e = acc.get(key)
        if e is None:
            e = {'cn': [], 'iv': [], 'period': period}
            acc[key] = e
        e['cn'].append(cnv)
        e['iv'].append(iv)


# =========================================================
# 第二部分：取平均 -> 重算 diff/ok
# =========================================================

def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None

def _mode(vals):
    vals = [v for v in vals if v is not None]
    return Counter(vals).most_common(1)[0][0] if vals else None

def average_all(acc, avg_count):
    """累积器 -> (严格相等点列表, 阈值口径点列表)，每个点是 10-元组。
    数值/风速: 取均值后重算 diff；天气现象: 取众数后跑语义偏差"""
    strict_pts = []
    threshold_pts = []
    for (city, module, field, ts), e in acc.items():
        period = e['period']
        spec = rt.MODULES[module]['fields'][field]
        typ = spec.get('type', 'numeric')

        # 配对有效样本（同一次拉取 cn/iv 都在才算）
        pairs = [(c, i) for c, i in zip(e['cn'], e['iv']) if c is not None and i is not None]
        count = len(pairs)

        if count == 0:
            miss_pt = (city, module, field, ts, None, None, '', '缺数据', '缺数据', period)
            strict_pts.append(miss_pt); threshold_pts.append(miss_pt)
            continue

        if typ == 'weather':
            cn_v = _mode([c for c, _ in pairs])
            iv_v = _mode([i for _, i in pairs])
            diff, ok = rt.calc_weather_deviation(cn_v, iv_v)
            note = f'按语义映射比对(众数,{count}次)'
            pt = (city, module, field, ts, cn_v, iv_v, diff, ok, note, period)
            strict_pts.append(pt); threshold_pts.append(pt)   # 天气两种口径一致
        else:
            # numeric / wind（wind 的 iv 已是 ÷3.6 后的 m/s，均值后直接相减）
            cn_vals = [rt.num(c) for c, _ in pairs]
            iv_vals = [rt.num(i) for _, i in pairs]
            avg_cn = _mean(cn_vals)
            avg_iv = _mean(iv_vals)
            avg_diff = round(avg_cn - avg_iv, 2)
            th = rt.get_threshold(field)
            ok_strict = '一致' if avg_diff == 0 else '不一致'
            ok_th = '一致' if (th is not None and abs(avg_diff) <= th) else '不一致'
            if typ == 'wind':
                note = f"海外均值已÷{rt.WIND_CFG['divisor']}换算({count}次均值)"
            else:
                note = spec.get('note', '') or f'{count}次均值'
            strict_pts.append((city, module, field, ts, avg_cn, avg_iv, avg_diff, ok_strict, note, period))
            threshold_pts.append((city, module, field, ts, avg_cn, avg_iv, avg_diff, ok_th, note, period))

    return strict_pts, threshold_pts


# =========================================================
# 第三部分：出报告
# =========================================================

def emit_reports(acc, avg_count, window_start, window_end):
    strict_pts, threshold_pts = average_all(acc, avg_count)
    if not strict_pts:
        print("❌ 无有效数据, 不生成报告")
        return

    tag = f'{avg_count}次均值_{window_start}-{window_end}'
    date = window_end[:8]
    strict_dir = os.path.join(OUT_DIR, '严格相等报告', date); os.makedirs(strict_dir, exist_ok=True)
    th_dir = os.path.join(OUT_DIR, '阈值口径报告', date); os.makedirs(th_dir, exist_ok=True)
    csv_dir = os.path.join(OUT_DIR, '数据明细CSV', date); os.makedirs(csv_dir, exist_ok=True)
    xlsx_strict = os.path.join(strict_dir, f'一致性比对报告_均值_严格相等_{tag}.xlsx')
    xlsx_threshold = os.path.join(th_dir, f'一致性比对报告_均值_阈值口径_{tag}.xlsx')
    csv_path = os.path.join(csv_dir, f'数据明细_均值_{tag}.csv')

    extra = [
        f'本报告为定时均值比对: 每 {INTERVAL}s 拉一次, 攒满 {avg_count} 次取平均后比对',
        f'采样窗口: {window_start} ~ {window_end}',
        '数值字段: 多次国内值/海外值分别取均值后比对',
        '天气现象: 取众数(最常出现)后按语义映射比对',
        '风速: 海外值已是 ÷3.6 换算后的 m/s, 均值后直接相减',
        '原始JSON留底: data/比对结果/原始json_<拉取时间戳>/<城市>_<时间戳>/国内.json + 国际.json（完整不加工）',
    ]

    n1 = rt.gen_xlsx(strict_pts, f'严格相等({avg_count}次均值)', xlsx_strict, extra_notes=extra)
    print(f"\n✅ 严格相等均值报告: {xlsx_strict}")
    print(f"   数据点: {n1}")

    n2 = rt.gen_xlsx(threshold_pts, f'阈值口径({avg_count}次均值)', xlsx_threshold, extra_notes=extra)
    print(f"✅ 阈值口径均值报告: {xlsx_threshold}")
    print(f"   数据点: {n2}")

    # 数据明细CSV（阈值口径，替代原始JSON作为证据）
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['城市', '模块', '字段', '时次', '国内值', '海外值', '差异', '是否一致', '备注', '时效分段'])
        for p in threshold_pts:
            w.writerow(p)
    print(f"✅ 数据明细CSV: {csv_path}")

    # 速览一致率
    print(f"\n{'='*60}")
    print(f"阈值口径均值 - 各字段一致率速览")
    print(f"{'='*60}")
    wb = openpyxl_load(xlsx_threshold)
    if wb:
        ws = wb['总结']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] and not row[2]:
                print(f"  {str(row[0]):14s} {str(row[1]):8s}  一致率: {str(row[7]):>7s}  平均偏差: {str(row[8]):>8s}")


def openpyxl_load(path):
    try:
        import openpyxl
        return openpyxl.load_workbook(path)
    except Exception:
        return None


# =========================================================
# 第四部分：状态落盘 / 续跑
# =========================================================

def save_state(acc, pulls_done, window_start):
    """累积器落盘，防崩溃丢窗口"""
    data = {
        'window_start': window_start,
        'pulls_done': pulls_done,
        'acc': [
            {'key': list(k), 'cn': v['cn'], 'iv': v['iv'], 'period': v['period']}
            for k, v in acc.items()
        ],
    }
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def load_state():
    """启动时尝试加载未完成窗口的状态。窗口未满即续跑（支持跨天长窗口，如2天48次）"""
    if not os.path.exists(STATE_PATH):
        return {}, 0, None
    try:
        with open(STATE_PATH, encoding='utf-8') as f:
            d = json.load(f)
        ws = d.get('window_start', '')
        pd = d.get('pulls_done', 0)
        # 窗口未满即续跑（支持跨天长窗口，如2天48次均值）
        if pd >= AVG_COUNT:
            print(f"  状态文件窗口已满({pd}/{AVG_COUNT}), 丢弃, 全新开始")
            os.remove(STATE_PATH)
            return {}, 0, None
        acc = {}
        for e in d['acc']:
            acc[tuple(e['key'])] = {'cn': e['cn'], 'iv': e['iv'], 'period': e['period']}
        print(f"  ✅ 续跑: 已累积 {pd}/{AVG_COUNT} 次 (窗口 {ws})")
        return acc, pd, ws
    except Exception as ex:
        print(f"  状态文件读取失败({ex}), 全新开始")
        return {}, 0, None


# =========================================================
# 主循环
# =========================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cities = rt.load_cities()
    rt.CITY_RANK  # 偏远优先序号已由 load_cities 设置

    acc, pulls_done, window_start = load_state()
    windows_done = 0

    print(f"\n{'='*60}")
    print(f"定时均值比对启动")
    print(f"  城市: {len(cities)} 城")
    print(f"  节奏: 每 {INTERVAL}s 拉一次, 攒满 {AVG_COUNT} 次出一份均值报告")
    print(f"  原始JSON留底: {'开' if KEEP_RAW else '关'}")
    if MAX_WINDOWS:
        print(f"  测试模式: 跑满 {MAX_WINDOWS} 个窗口后退出")
    print(f"{'='*60}")

    try:
        while True:
            if window_start is None:
                window_start = now_str()
            pull_n = pulls_done + 1
            print(f"\n[{datetime.datetime.now():%H:%M:%S}] 第 {pull_n}/{AVG_COUNT} 次拉取开始 (窗口 {window_start})")

            pts_all, ok, skip = pull_once(cities, OUT_DIR, pull_n)

            # 整次拉取成功后，才合并进累积器（中断可丢弃本次，不污染已有数据）
            merge_pull(acc, pts_all)
            pulls_done += 1
            save_state(acc, pulls_done, window_start)
            print(f"  本次成功 {ok} 城, 跳过 {skip} 城; 累积 {pulls_done}/{AVG_COUNT}")

            if pulls_done >= AVG_COUNT:
                window_end = now_str()
                print(f"\n攒满 {AVG_COUNT} 次, 生成均值报告 ({window_start} ~ {window_end})...")
                emit_reports(acc, AVG_COUNT, window_start, window_end)
                # 清空，开始下一窗口
                acc = {}; pulls_done = 0; window_start = None
                windows_done += 1
                if os.path.exists(STATE_PATH):
                    os.remove(STATE_PATH)
                if MAX_WINDOWS and windows_done >= MAX_WINDOWS:
                    print(f"\n✅ 已跑满 {MAX_WINDOWS} 个窗口, 测试完成, 退出")
                    break
                print(f"\n✅ 本窗口报告已生成, 进入下一窗口")
            else:
                print(f"  休眠 {INTERVAL}s 后下次拉取... (Ctrl-C 可停止, 状态已存)")

            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n收到 Ctrl-C, 优雅停止")
        if pulls_done and window_start:
            print(f"  已累积 {pulls_done}/{AVG_COUNT} 次 (窗口 {window_start}), 状态已存, 下次启动续跑")
        else:
            print("  当前无未完成窗口")


if __name__ == '__main__':
    main()
