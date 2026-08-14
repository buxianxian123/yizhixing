#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 raw_pull 留底的所有 json 转成原始数据 csv（UTC 对齐版）：
1. 对齐规则：按 UTC 时间严格对齐，允许误差 ≤ 10 分钟（与线上报告一致）
   - 国内 predictTime → 从接口取时区偏移 → 转 UTC
   - 国际 pt → UTC
   - 两者 UTC 时间差 ≤ 10 分钟 算同一时刻
2. CSV 格式：
   写入时间,城市,[时次/日期(UTC)],predictTime/predictDate(国内UTC),predictTime/predictDate(海外UTC),
   localTime/localDate(国内),localTime/localDate(海外), 要素1(国内),要素1(海外),...
3. 存储：data/原始数据csv/<YYYYMMDD>/ 每天一个文件夹，每个文件夹4个模块csv
   一天对应一份，第二天另存，便于归档；模块csv文件名带日期(实况_20260731.csv)
4. 去重：按 (写入时间, 城市, UTC时次/日期) 唯一，重复轮次同一时次只保留首次出现

运行: python3 convert_raw_to_csv.py"""
import os, json, glob, csv
from datetime import datetime, timedelta, timezone
import reformat_threshold as rt
from fetch_cn_pb import normalize_cn, normalize_in

# 数据源目录支持环境变量覆盖: RAW_SRC=xxx python3 convert_raw_to_csv.py
# (用于从参考版原始留底等其他数据源重建 CSV)
RAW_DIR = os.environ.get('RAW_SRC') or os.path.join(rt.BASE, '原始拉取')
BASE_OUT = os.path.join(rt.BASE, '原始数据csv')

# 匹配容差: 10分钟
MATCH_TOLERANCE = timedelta(minutes=10)


def fmt_val(v):
    """值写入 csv 前格式化：整数 float(如 3.0) 统一不带 .0，None/空返回空串。"""
    if v is None:
        return ''
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return str(v)
    return str(v)


def _snap_has_data(mod):
    """单值模块快照(cn 归一化后的 current/aqi dict)是否有任一字段值。
    上游空包(code:0 但 detail[0].cityName 空)会被 normalize_cn 归一化成"全 None 的 dict"而非空 dict,
    不能只查真值(not mod 恒为 False), 必须检查是否有任一非 None 值"""
    return isinstance(mod, dict) and any(v is not None for v in mod.values())


def build_header(module, mspec):
    """构建表头。multi 模块在 时次/日期 列后加 UTC + 当地时间列。"""
    source = mspec['source']
    fields = mspec['fields']
    multi = mspec.get('multi')
    header = ['写入时间', '城市']
    if multi:
        ts_label = '时次(UTC)' if source == 'hourly' else '日期(当地)'
        ts_name = 'predictTime' if source == 'hourly' else 'predictDate'
        local_name = 'localTime' if source == 'hourly' else 'localDate'
        header.append(ts_label)
        header.append(f'{ts_name}(国内UTC)')
        header.append(f'{ts_name}(海外UTC)')
        header.append(f'{local_name}(国内)')
        header.append(f'{local_name}(海外)')
        if source == 'hourly':
            header.append('updatetime(国内UTC)')
    for fname, _ in fields.items():
        header.append(f'{fname}(国内)')
        header.append(f'{fname}(海外)')
    return header


# ===== 短时降水 + 预警 模块（只拉取存储, 暂不比对）=====
# 短时降水: 国内顶层 Weather.radar(rain/type/content/percent) vs 国际 data.nowcast(level/long_desc/percent)
# 预警:     国内 detail.alertList.alert vs 国际 data.alert(稀疏)
AUX_HEADERS = {
    '短时': ['写入时间', '城市',
             '国内是否降水(rain)', '国内类型(type)', '国内描述(content)', '国内时间戳(timestamp)', '国内降水概率(percent_json)',
             '国际是否降水(rain)', '国际降水等级(level)', '国际降水强度(rain_intensity)', '国际降水持续(rain_last_time)',
             '国际描述(long_desc)', '国际短描述(short_desc)', '国际时间戳(timestamp)', '国际降水概率(percent_json)'],
    '预警': ['写入时间', '城市', '国内预警数', '国内预警JSON', '国际预警数', '国际预警JSON'],
}


def build_nowcast_row(pull_at, name, cn, intl):
    """短时降水: 国内 radar(顶层) vs 国际 nowcast, 每(轮,城市)一行, 多存字段。
    国内: rain(是否降水)/type/content/banner/timestamp/percent(强度序列)
    国际: rain(是否降水)/level/rain_intensity(强度)/rain_last_time(持续)/long_desc/short_desc/timestamp/percent"""
    nc = (cn or {}).get('nowcast') or {}
    nw = (intl or {}).get('nowcast') or {}
    return [
        pull_at, name,
        nc.get('rain'), nc.get('type'), nc.get('content'), nc.get('timestamp'),
        json.dumps(nc.get('percent'), ensure_ascii=False) if nc.get('percent') else '',
        nw.get('rain'), nw.get('level'), nw.get('rain_intensity'), nw.get('rain_last_time'),
        nw.get('long_desc'), nw.get('short_desc'), nw.get('timestamp'),
        json.dumps(nw.get('percent'), ensure_ascii=False) if nw.get('percent') else '',
    ]


def build_alert_rows(pull_at, name, cn, intl):
    """预警: 国内 alertList vs 国际 alert, 每(轮,城市)一行, 预警列表JSON序列化保存。"""
    al_cn = (cn or {}).get('alerts') or []
    al_in = (intl or {}).get('alert') or []
    return [[
        pull_at, name,
        len(al_cn), json.dumps(al_cn, ensure_ascii=False),
        len(al_in), json.dumps(al_in, ensure_ascii=False),
    ]]


def _parse_utc(s):
    """UTC时间字符串 → datetime(UTC)。支持 %Y-%m-%d %H:%M:%S 和 %Y-%m-%d"""
    if not s:
        return None
    try:
        if ' ' in s:
            return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        else:
            return datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _match_utc(cn_utc_str, intl_utc_list, tolerance=MATCH_TOLERANCE):
    """在国际 UTC 列表中找与 cn_utc 最接近且 ≤ tolerance 的条目。
    返回 (匹配的海外条目, 实际时间差秒数)，匹配失败返回 (None, None)"""
    cn_dt = _parse_utc(cn_utc_str)
    if cn_dt is None:
        return None, None
    best = None
    best_diff = None
    for b in intl_utc_list:
        b_utc = b.get('_utc')
        b_dt = _parse_utc(b_utc)
        if b_dt is None:
            continue
        diff = abs((cn_dt - b_dt).total_seconds())
        if diff <= tolerance.total_seconds():
            if best is None or diff < best_diff:
                best = b
                best_diff = diff
    return best, best_diff


def _match_ts(cn_ts, intl_items, tolerance_seconds=600):
    """按 _predict_ts 数值 timestamp(秒) 找最近匹配, 允许 tolerance_seconds 误差。
    返回 (匹配的海外条目, 实际时间差秒数)，匹配失败返回 (None, None)"""
    if cn_ts is None:
        return None, None
    best = None
    best_diff = None
    for b in intl_items:
        b_ts = b.get('_predict_ts')
        if b_ts is None:
            continue
        diff = abs(cn_ts - b_ts)
        if diff <= tolerance_seconds:
            if best is None or diff < best_diff:
                best = b
                best_diff = diff
    return best, best_diff


def main():
    cities = rt.load_cities()
    rounds = sorted(glob.glob(os.path.join(RAW_DIR, '原始_*')))
    print(f"扫描到 {len(rounds)} 轮留底, {len(cities)} 城市")
    print(f"输出根目录: {BASE_OUT}")
    print(f"UTC匹配容差: {MATCH_TOLERANCE.total_seconds()/60:.0f} 分钟")
    os.makedirs(BASE_OUT, exist_ok=True)

    # 按 (日期, 模块) 收集行
    data = {}
    seen = {}
    headers = {}

    for module, mspec in rt.MODULES.items():
        headers[module] = build_header(module, mspec)
    for _m, _h in AUX_HEADERS.items():
        headers[_m] = _h

    first_module = next(iter(rt.MODULES))
    aux_seen = set()   # 短时/预警每(轮,城市)只收集一次

    for rd_idx, rd in enumerate(rounds, 1):
        # 读取轮次时间
        manifest_path = os.path.join(rd, '_manifest.json')
        pull_at = ''
        if os.path.exists(manifest_path):
            try:
                pull_at = json.load(open(manifest_path, encoding='utf-8')).get('pull_at', '')
            except Exception:
                pass
        if not pull_at:
            ts = os.path.basename(rd).replace('原始_', '')
            if len(ts) >= 15:
                ymd = ts[:8]
                hh = ts[9:11]
                mm = ts[11:13]
                pull_at = f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]} {hh}:{mm}:00'
        if not pull_at:
            date_dir = 'unknown'
        else:
            date_dir = pull_at[:10].replace('-', '')

        if rd_idx % 10 == 0 or rd_idx == len(rounds):
            print(f"  处理第 {rd_idx}/{len(rounds)} 轮: {os.path.basename(rd)} → {date_dir}")

        for module, mspec in rt.MODULES.items():
            source = mspec['source']
            fields = mspec['fields']
            multi = mspec.get('multi')
            limit = mspec.get('limit', 99)

            key = (date_dir, module)
            if key not in data:
                data[key] = []
                seen[key] = set()
            rows = data[key]
            seen_set = seen[key]

            for name, lon, lat in cities:
                cn_path = os.path.join(rd, name, '国内.json')
                intl_path = os.path.join(rd, name, '国际.json')
                if not (os.path.exists(cn_path) and os.path.exists(intl_path)):
                    continue
                try:
                    cn_raw = json.load(open(cn_path, encoding='utf-8'))
                    intl_raw = json.load(open(intl_path, encoding='utf-8'))
                    if isinstance(intl_raw, dict) and 'data' in intl_raw and 'current' not in intl_raw:
                        intl_raw = intl_raw['data']

                    cn = normalize_cn(cn_raw)
                    tz_hours = cn.get('_meta', {}).get('timezone')
                    _updatetime_utc = ''
                    if source == 'hourly':
                        ut = cn.get('_meta', {}).get('updatetime')
                        if ut:
                            _updatetime_utc = datetime.fromtimestamp(
                                ut, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    intl = normalize_in(intl_raw, tz_hours=tz_hours)

                    # 短时降水 + 预警: 每(轮,城市)收集一次(只拉存储, 暂不比对)
                    if module == first_module and (rd_idx, name) not in aux_seen:
                        aux_seen.add((rd_idx, name))
                        data.setdefault((date_dir, '短时'), []).append(build_nowcast_row(pull_at, name, cn, intl))
                        for _r in build_alert_rows(pull_at, name, cn, intl):
                            data.setdefault((date_dir, '预警'), []).append(_r)

                    if multi:
                        cn_arr = cn.get(source, [])
                        intl_arr = intl.get(source, [])[:limit]
                        ts_local_key = 'predict_time' if source == 'hourly' else 'predict_date'

                        if not cn_arr or not intl_arr:
                            # 一侧无数据(国内/国际该模块数组为空): 写"缺数据"标记行, 让缺失可见
                            # (一致率侧会把空值当缺数据剔除出分母, 不污染一致率)
                            marker = ['缺数据', '', '', '', '', '', '']
                            if source == 'hourly':
                                marker[6] = _updatetime_utc   # updatetime(国内UTC)列
                            empty_row = [pull_at, name] + marker
                            empty_row += [''] * (len(headers[module]) - len(empty_row))
                            dedup_key = (pull_at, name, '缺数据')
                            if dedup_key not in seen_set:
                                seen_set.add(dedup_key)
                                rows.append(empty_row)
                        elif source == 'daily':
                            # 15天: 按当地日期匹配(与 rebuild_day_csv 一致, 实测全部城市15/15)。
                            # 国内 predictDate 是当地午夜, 海外 pt 是更新时刻锚点, 语义不同,
                            # 不能用 UTC 时间戳匹配(实测北京/东京/悉尼等全部 0/15 匹配不上)。
                            intl_map = {b.get(ts_local_key): b for b in intl_arr if b.get(ts_local_key)}
                            for a in cn_arr:
                                local_ts = a.get(ts_local_key)
                                if not local_ts or local_ts not in intl_map:
                                    continue
                                b = intl_map[local_ts]
                                dedup_key = (pull_at, name, local_ts)
                                if dedup_key in seen_set:
                                    continue
                                seen_set.add(dedup_key)
                                row = [
                                    pull_at, name,
                                    local_ts,              # 日期(当地)
                                    a.get('_utc'),         # predictDate(国内UTC)
                                    b.get('_utc'),         # predictDate(海外UTC)
                                    a.get(ts_local_key),   # localDate(国内)
                                    b.get(ts_local_key),   # localDate(海外)
                                ]
                                for fname, spec in fields.items():
                                    row.append(fmt_val(a.get(spec['cn'])))
                                    row.append(fmt_val(b.get(spec['intl'])))
                                rows.append(row)
                        else:
                            # 小时模块: 按UTC时间匹配, 允许10分钟误差
                            for a in cn_arr:
                                b, diff_sec = _match_utc(a.get('_utc'), intl_arr)
                                if b is None:
                                    continue
                                utc_ts = a.get('_utc')
                                dedup_key = (pull_at, name, utc_ts)
                                if dedup_key in seen_set:
                                    continue
                                seen_set.add(dedup_key)
                                row = [
                                    pull_at, name,
                                    utc_ts,           # 时次(UTC)
                                    a.get('_utc'),    # predictTime(国内UTC)
                                    b.get('_utc'),    # predictTime(海外UTC)
                                    a.get(ts_local_key),  # localTime(国内)
                                    b.get(ts_local_key),  # localTime(海外)
                                    _updatetime_utc,       # updatetime(国内UTC)
                                ]
                                for fname, spec in fields.items():
                                    row.append(fmt_val(a.get(spec['cn'])))
                                    row.append(fmt_val(b.get(spec['intl'])))
                                rows.append(row)
                    else:
                        # 单值模块: 实况/AQI. 任一侧缺数据时写"缺数据"标记行(与多值模块对齐),
                        # 报告端 _raw_val 把"缺数据"当 None -> cmp_point 记缺数据 -> 不进一致率分母
                        cn_mod = cn.get(source, {}) or {}
                        intl_mod = intl.get(source, {}) or {}
                        dedup_key = (pull_at, name)
                        if dedup_key in seen_set:
                            continue
                        seen_set.add(dedup_key)
                        if not _snap_has_data(cn_mod) or not intl_mod:
                            marker = [pull_at, name, '缺数据'] + [''] * (len(headers[module]) - 3)
                            rows.append(marker)
                        else:
                            row = [pull_at, name]
                            for fname, spec in fields.items():
                                row.append(fmt_val(cn_mod.get(spec['cn'])))
                                row.append(fmt_val(intl_mod.get(spec['intl'])))
                            rows.append(row)
                except Exception as e:
                    pass

    # 统一写文件
    total_lines = 0
    for (date_dir, module), rows in sorted(data.items()):
        out_dir = os.path.join(BASE_OUT, date_dir)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f'{module}_{date_dir}.csv')
        header = headers[module]
        with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        total_lines += len(rows)
        print(f"  写入 {out_path}: {len(rows)} 行")

    print(f"\n全部完成: 总数据行 {total_lines}")
    print(f"输出: {BASE_OUT}/<YYYYMMDD>/<模块>_<YYYYMMDD>.csv")
    print(f"  每个日期文件夹6个文件: 实况 24小时 15天 AQI模块 短时 预警 _<日期>.csv")


if __name__ == '__main__':
    main()
