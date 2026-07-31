#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从已拉取的原始JSON复现均值报告（验证数据加工逻辑，不用等定时任务跑满48次）
选最近N份原始拉取 -> build_points -> merge_pull -> average_all -> gen_xlsx + csv + html + md

数据源: data/原始拉取/原始_<时间戳>/<城市>/国内.json + 国际.json（raw_pull.py 拉取留底）
加工链路与 scheduled_compare.py 完全一致，只是手动取最近N份一次性出报告（不用等定时任务攒满）。
raw_pull 每跑一轮都留底 原始拉取/原始_<时间戳>/<城市>/，本脚本读这些留底复现均值报告。

运行:
  python3 gen_report_from_raw.py          # 用全部已有原始拉取做均值
  python3 gen_report_from_raw.py 6        # 取最近6份做均值
  python3 gen_report_from_raw.py 45       # 取最近45份做均值
"""
import os, sys, glob, json, subprocess
import reformat_threshold as rt
import scheduled_compare as sc

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = rt.OUT_DIR                       # data/比对结果
RAW_PULL_DIR = os.path.join(os.path.dirname(OUT_DIR), '原始拉取')   # data/原始拉取 (raw_pull留底)


def load_raw_pulls(cities):
    """扫描 data/原始拉取/原始_<时间戳>/<城市>/ 目录，每份用 build_points 重建points，返回 [(时间戳, pts), ...]"""
    raw_dirs = sorted(glob.glob(os.path.join(RAW_PULL_DIR, '原始_*')))
    pulls = []
    for rd in raw_dirs:
        ts = os.path.basename(rd).replace('原始_', '')
        pts = []
        for name, lon, lat in cities:
            cn_path = os.path.join(rd, name, '国内.json')
            intl_path = os.path.join(rd, name, '国际.json')
            if not (os.path.exists(cn_path) and os.path.exists(intl_path)):
                continue
            try:
                cn = json.load(open(cn_path, encoding='utf-8'))
                intl = json.load(open(intl_path, encoding='utf-8'))
                if isinstance(intl, dict) and 'data' in intl and 'current' not in intl:
                    intl = intl['data']   # raw_pull存完整响应{code,data,msg}, 提取data给build_points
                pts += rt.build_points(name, cn, intl, strict=False)
            except Exception as e:
                print(f'  跳过 {name}: {e}')
        if pts:
            pulls.append((ts, pts))
    return pulls


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0=全部已有
    cities = rt.load_cities()
    print(f"扫描 raw_pull 留底: {RAW_PULL_DIR}")
    pulls = load_raw_pulls(cities)
    print(f"找到 {len(pulls)} 份拉取: {', '.join(p[0] for p in pulls)}")
    if not pulls:
        print(f"❌ 未找到原始拉取，请确认 {RAW_PULL_DIR}/原始_* 目录存在（需先跑 raw_pull.py 拉取）")
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
        f'本报告从 raw_pull 留底复现（验证加工逻辑）: 取 {avg_count} 份原始拉取做均值',
        f'采样窗口: {window_start} ~ {window_end}',
        '数据源: data/原始拉取/原始_<ts>/<城市>/国内.json + 国际.json (raw_pull.py 拉取)',
        '加工链路与 scheduled_compare.py 完全一致（build_points -> merge_pull -> average_all -> gen_xlsx）',
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
