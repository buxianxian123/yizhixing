#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从已拉取的原始JSON复现均值报告（验证数据加工逻辑，不用等定时任务跑满48次）
选最近N份原始json -> build_points -> merge_pull -> average_all -> gen_xlsx + csv + html + md

加工链路与 scheduled_compare.py 完全一致，只是数据源从"实时拉接口"换成"读已存的原始json"。
定时任务每跑一次都会留底 原始json_<时间戳>/<城市>_<时间戳>/国内.json + 国际.json，
本脚本读这些留底复现，可在定时任务跑满前就验证 build_points/merge/average/gen_xlsx 整条链路是否正确。

运行:
  python3 gen_report_from_raw.py          # 用全部已有原始json做均值
  python3 gen_report_from_raw.py 6        # 取最近6份做均值
"""
import os, sys, glob, json, subprocess
import reformat_threshold as rt
import scheduled_compare as sc

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = rt.OUT_DIR


def load_raw_pulls(cities):
    """扫描所有 原始json_<时间戳> 目录，每份用 build_points 重建points，返回 [(时间戳, pts), ...]"""
    raw_dirs = sorted(glob.glob(os.path.join(OUT_DIR, '原始json_*')))
    pulls = []
    for rd in raw_dirs:
        ts = os.path.basename(rd).replace('原始json_', '')
        pts = []
        for name, lon, lat in cities:
            city_dirs = glob.glob(os.path.join(rd, f'{name}_*'))
            if not city_dirs:
                continue
            cd = city_dirs[0]
            try:
                cn = json.load(open(os.path.join(cd, '国内.json'), encoding='utf-8'))
                intl = json.load(open(os.path.join(cd, '国际.json'), encoding='utf-8'))
                pts += rt.build_points(name, cn, intl, strict=False)
            except Exception as e:
                print(f'  跳过 {name}: {e}')
        if pts:
            pulls.append((ts, pts))
    return pulls


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0=全部已有
    cities = rt.load_cities()
    print(f"扫描已拉取的原始JSON留底...")
    pulls = load_raw_pulls(cities)
    print(f"找到 {len(pulls)} 份拉取: {', '.join(p[0] for p in pulls)}")
    if not pulls:
        print("❌ 未找到原始JSON，请确认 data/比对结果/原始json_* 目录存在（定时任务需开启 keep_raw）")
        return
    if n and n < len(pulls):
        pulls = pulls[-n:]
        print(f"取最近 {n} 份做均值")
    avg_count = len(pulls)
    window_start, window_end = pulls[0][0], pulls[-1][0]
    print(f"\n累积 {avg_count} 份，区间 {window_start} ~ {window_end}")

    # merge（与 scheduled_compare 同链路）
    acc = {}
    for ts, pts in pulls:
        sc.merge_pull(acc, pts)

    # average（与 scheduled_compare 同链路）
    strict_pts, threshold_pts = sc.average_all(acc, avg_count)
    if not strict_pts:
        print("❌ 无有效数据")
        return

    tag = f'{avg_count}次均值_{window_start}-{window_end}_fromraw'
    xlsx_path = os.path.join(OUT_DIR, f'一致性比对报告_均值_阈值口径_{tag}.xlsx')
    csv_path = os.path.join(OUT_DIR, f'数据明细_均值_{tag}.csv')

    extra = [
        f'本报告从已拉取的原始JSON留底复现（验证加工逻辑）: 取 {avg_count} 份原始JSON做均值',
        f'采样窗口: {window_start} ~ {window_end}',
        '加工链路与 scheduled_compare.py 完全一致（build_points -> merge_pull -> average_all -> gen_xlsx）',
        '区别: scheduled_compare 实时拉接口，本脚本读已存原始JSON',
    ]
    n2 = rt.gen_xlsx(threshold_pts, f'阈值口径({avg_count}次均值)', xlsx_path, extra_notes=extra)
    print(f"\n✅ xlsx: {os.path.basename(xlsx_path)} ({n2} 数据点)")

    import csv
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['城市', '模块', '字段', '时次', '国内值', '海外值', '差异', '是否一致', '备注', '时效分段'])
        for p in threshold_pts:
            w.writerow(p)
    print(f"✅ csv: {os.path.basename(csv_path)}")

    # html + md（复用现有脚本，传xlsx路径，保证同源同算法）
    for script in ['gen_html_report.py', 'gen_md_report.py']:
        r = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, script), xlsx_path])
        if r.returncode != 0:
            print(f"⚠️ {script} 生成失败")
    print(f"\n✅ html + md 已生成（与定时任务同算法、同源xlsx）")
    print(f"\n用途: 验证数据加工逻辑正确性，无需等定时任务跑满")


if __name__ == '__main__':
    main()
