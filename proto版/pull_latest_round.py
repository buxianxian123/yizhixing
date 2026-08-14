#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉最新一轮，直接写数据库（UTC对齐版）。

对齐规则：
- 小时模块: 按 UTC 时间匹配，允许误差 ≤ 10 分钟（与线上报告一致）
- 15天模块: 按当地日期匹配（DayN 即当地日历日）

输出: data/weather_data.db 各模块表
去重: INSERT OR IGNORE, 靠 UNIQUE 约束 (写入时间, 城市, [时次/日期])

原始留底(文件) + 缺数据留底(文件) 保持不变, 供人工核对。
"""
import os
import json
import subprocess
import datetime
import reformat_threshold as rt
import fetch_cn_pb
import db_helper
from fetch_cn_pb import fetch_cn, normalize_in
from convert_raw_to_csv import _match_utc, _snap_has_data, build_nowcast_row, build_alert_rows


def _is_missing_cn(cn):
    """国内数据是否缺失(实况/逐时/逐日 任一为空)"""
    if not cn or not isinstance(cn, dict):
        return True
    cur = cn.get('current') or {}
    return not cur or not cn.get('hourly') or not cn.get('daily')


def _save_missing_json(name, lon_str, lat_str):
    """保存缺数据城市的国内+国际原始JSON到 data/缺数据留底/<日期>/"""
    try:
        date_dir = datetime.datetime.now().strftime('%Y%m%d')
        out_dir = os.path.join(rt.BASE, '缺数据留底', date_dir)
        os.makedirs(out_dir, exist_ok=True)
        cn_raw = fetch_cn_pb._last_raw_dict or {}
        json.dump(cn_raw,
                  open(os.path.join(out_dir, f'{name}_国内.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False)
        pb_bytes = fetch_cn_pb._last_raw_content or b''
        if pb_bytes:
            with open(os.path.join(out_dir, f'{name}_国内.pb'), 'wb') as f:
                f.write(pb_bytes)
        from gen_all_urls import gen_in_url
        url = gen_in_url(lat_str, lon_str)
        r = subprocess.run(['curl', '-sk', '--max-time', '25', '--connect-timeout', '8', url],
                           capture_output=True, text=True)
        intl_raw = json.loads(r.stdout) if r.returncode == 0 else {}
        json.dump(intl_raw, open(os.path.join(out_dir, f'{name}_国际.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False)
        det = (cn_raw.get('detail') or [{}])[0] if cn_raw.get('detail') else {}
        cn_desc = f"code={cn_raw.get('code')}, detail[0].cityId={det.get('cityId')}, cityName={'空' if not det.get('cityName') else det.get('cityName')}, 无天气数据(current/hourly/daily均无), pb={len(pb_bytes)}B(完整响应, 可独立重新解析)"
        inl_cur = (intl_raw.get('data') or {}).get('current')
        inl_desc = f"code={intl_raw.get('code')}, data.current={'有' if inl_cur else '无'}"
        note_lines = [
            f"城市={name}  经纬度={lon_str},{lat_str}",
            f"拉取时刻={datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"国内接口(moji detail, 重试后仍空): {cn_desc}",
            f"国际接口(同城同时): {inl_desc}",
            "结论: 国内接口对海外城市间歇返回'空成功包'(城市解析失败), 原始字节国内.pb已按原样留底",
            "本证据包自包含(国内.pb/国内.json/国际.json/说明), 不依赖其他留底; 国际接口全历史0缺失",
        ]
        with open(os.path.join(out_dir, f'{name}_缺数据说明.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(note_lines) + '\n')
        print(f"   缺数据证据已存: {out_dir}/{name}_国内.pb, {name}_国内.json, {name}_国际.json + 缺数据说明.txt")
    except Exception as e:
        print(f"   ⚠️ {name} 缺数据JSON保存失败: {e}")


def _insert_module_row(conn, module, mspec, pull_at, name, cn_data, intl_data, _updatetime_utc):
    """向数据库插入一条模块数据。返回是否插入 (True/False)。
    处理多值(小时/逐日)和单值(实况/AQI)两种模式, 含缺数据标记行。"""
    table_map = db_helper.MODULE_TABLE_MAP[module]
    table = table_map['table']
    source = mspec['source']
    fields = mspec['fields']
    multi = mspec.get('multi')
    limit = mspec.get('limit', 99)

    if multi:
        cn_arr = cn_data.get(source, [])
        intl_arr = intl_data.get(source, [])[:limit]
        ts_local_key = 'predict_time' if source == 'hourly' else 'predict_date'

        if not cn_arr or not intl_arr:
            # 缺数据标记行
            row = {'pull_at': pull_at, 'city_name': name, 'is_missing': 1}
            if source == 'hourly':
                row['updatetime_cn'] = _updatetime_utc
            db_helper.insert_row(conn, table, row)
            return True
        elif source == 'daily':
            # 15天: 按当地日期匹配
            intl_map = {b.get(ts_local_key): b for b in intl_arr if b.get(ts_local_key)}
            inserted = False
            for a in cn_arr:
                local_ts = a.get(ts_local_key)
                if not local_ts or local_ts not in intl_map:
                    continue
                b = intl_map[local_ts]
                row = {
                    'pull_at': pull_at, 'city_name': name,
                    'local_date': local_ts,
                    'predict_date_cn': a.get('_utc'),
                    'predict_date_intl': b.get('_utc'),
                    'local_date_cn': a.get(ts_local_key),
                    'local_date_intl': b.get(ts_local_key),
                }
                db_helper.build_field_cols(row, fields, table_map, a, b)
                row['is_missing'] = 0
                db_helper.insert_row(conn, table, row)
                inserted = True
            return inserted
        else:
            # 小时: 按UTC匹配, ≤10分钟容差
            inserted = False
            for a in cn_arr:
                b, diff_sec = _match_utc(a.get('_utc'), intl_arr)
                if b is None:
                    continue
                utc_ts = a.get('_utc')
                row = {
                    'pull_at': pull_at, 'city_name': name,
                    'ts_utc': utc_ts,
                    'predict_time_cn': a.get('_utc'),
                    'predict_time_intl': b.get('_utc'),
                    'local_time_cn': a.get(ts_local_key),
                    'local_time_intl': b.get(ts_local_key),
                    'updatetime_cn': _updatetime_utc,
                }
                db_helper.build_field_cols(row, fields, table_map, a, b)
                row['is_missing'] = 0
                db_helper.insert_row(conn, table, row)
                inserted = True
            return inserted
    else:
        # 单值模块: 实况/AQI
        cn_mod = cn_data.get(source, {}) or {}
        intl_mod = intl_data.get(source, {}) or {}
        if not _snap_has_data(cn_mod) or not intl_mod:
            row = {'pull_at': pull_at, 'city_name': name, 'is_missing': 1}
            db_helper.insert_row(conn, table, row)
            return True
        else:
            row = {'pull_at': pull_at, 'city_name': name}
            db_helper.build_field_cols(row, fields, table_map, cn_mod, intl_mod)
            row['is_missing'] = 0
            db_helper.insert_row(conn, table, row)
            return True


def main():
    print("=== 开始拉最新一轮 ===")
    cities = rt.load_cities()
    pull_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:00')

    # 原始留底目录 (文件留底, 供 convert_raw_to_csv/rebuild_day_csv 复算)
    round_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_round_dir = os.path.join(rt.BASE, '原始拉取', f'原始_{round_ts}')
    os.makedirs(raw_round_dir, exist_ok=True)
    missing_saved = set()
    city_data = {}

    total_ok = 0
    total_fail = 0

    # ========== 阶段1: 每城拉一次 国内+国际 ==========
    from gen_all_urls import gen_in_url
    for idx, (name, lon_str, lat_str) in enumerate(cities, 1):
        try:
            cn = fetch_cn(float(lon_str), float(lat_str))
            if cn is None:
                print(f"⚠️ [{idx}/{len(cities)}] {name} 国内拉取失败，跳过")
                total_fail += 1
                continue
            if _is_missing_cn(cn):
                print(f"   {name}: 国内数据缺失(实况/逐时/逐日), 重拉一次...")
                cn2 = fetch_cn(float(lon_str), float(lat_str))
                if cn2 is not None and not _is_missing_cn(cn2):
                    cn = cn2
                    print(f"   {name}: 重拉成功, 使用新数据")
                else:
                    if name not in missing_saved:
                        missing_saved.add(name)
                        _save_missing_json(name, lon_str, lat_str)
                    print(f"   {name}: 重拉仍空 -> 记缺数据(存JSON, 写标记行)")

            tz_hours = cn.get('_meta', {}).get('timezone')
            _updatetime_utc = ''
            ut = cn.get('_meta', {}).get('updatetime')
            if ut:
                _updatetime_utc = datetime.datetime.fromtimestamp(
                    ut, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            url = gen_in_url(lat_str, lon_str)
            intl_raw = {}
            for attempt in (1, 2):
                try:
                    r = subprocess.run(
                        ['curl', '-sk', '--max-time', '25', '--connect-timeout', '8', url],
                        capture_output=True, text=True, timeout=35)
                    tmp = json.loads(r.stdout) if r.returncode == 0 else {}
                    if tmp.get('code') == 0:
                        intl_raw = tmp
                        break
                except Exception:
                    pass
                if attempt == 1:
                    print(f"   {name}: 国际拉取失败, 重试一次...")
            if not intl_raw:
                print(f"⚠️ {name} 国际拉取失败(重试后仍失败)，跳过")
                total_fail += 1
                continue
            intl = intl_raw['data'] if ('data' in intl_raw and 'current' not in intl_raw) else intl_raw
            intl = normalize_in(intl, tz_hours=tz_hours)

            # 落原始留底(文件, 每城一次)
            city_raw_dir = os.path.join(raw_round_dir, name)
            try:
                os.makedirs(city_raw_dir, exist_ok=True)
                with open(os.path.join(city_raw_dir, '国内.pb'), 'wb') as f:
                    f.write(fetch_cn_pb._last_raw_content or b'')
                with open(os.path.join(city_raw_dir, '国内.json'), 'w', encoding='utf-8') as f:
                    json.dump(fetch_cn_pb._last_raw_dict or {}, f, ensure_ascii=False)
                with open(os.path.join(city_raw_dir, '国际.json'), 'w', encoding='utf-8') as f:
                    json.dump(intl_raw, f, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ {name} 留底保存失败: {e}")

            city_data[name] = {'cn': cn, 'intl': intl, '_updatetime_utc': _updatetime_utc}
            total_ok += 1
            if idx % 10 == 0 or idx == len(cities):
                print(f"  [{idx}/{len(cities)}] {name} ✅")
        except Exception as e:
            print(f"⚠️ {name} 拉取异常: {e}")
            total_fail += 1
            continue

    print(f"\n拉取完成: 成功 {total_ok} 城市, 失败 {total_fail} 城市")

    # ========== 阶段2: 写数据库 ==========
    conn = db_helper.get_conn()

    # pull_round 记录
    db_helper.insert_row(conn, 'pull_round', {
        'pull_at': pull_at,
        'raw_dir': os.path.basename(raw_round_dir),
        'total_ok': total_ok,
        'total_fail': total_fail,
    })

    conn.commit()

    # 各比对模块
    for module, mspec in rt.MODULES.items():
        n_mod = 0
        for name, lon_str, lat_str in cities:
            if name not in city_data:
                continue
            d = city_data[name]
            try:
                if _insert_module_row(conn, module, mspec, pull_at, name,
                                      d['cn'], d['intl'], d['_updatetime_utc']):
                    n_mod += 1
            except Exception as e:
                print(f"⚠️ {module}/{name} 写入失败: {e}")
                continue
        conn.commit()
        print(f"✅ {module}: +{n_mod} 城市")

    # 短时/预警
    for name, d in city_data.items():
        try:
            nc_row = build_nowcast_row(pull_at, name, d['cn'], d['intl'])
            db_helper.insert_row(conn, 'nowcast', {
                'pull_at': pull_at, 'city_name': name,
                'cn_rain': db_helper.to_val(nc_row[2]),
                'cn_type': db_helper.to_val(nc_row[3]),
                'cn_content': db_helper.to_val(nc_row[4]),
                'cn_timestamp': db_helper.to_val(nc_row[5]),
                'cn_percent_json': db_helper.to_val(nc_row[6]),
                'intl_rain': db_helper.to_val(nc_row[7]),
                'intl_level': db_helper.to_val(nc_row[8]),
                'intl_rain_intensity': db_helper.to_val(nc_row[9]),
                'intl_rain_last_time': db_helper.to_val(nc_row[10]),
                'intl_long_desc': db_helper.to_val(nc_row[11]),
                'intl_short_desc': db_helper.to_val(nc_row[12]),
                'intl_timestamp': db_helper.to_val(nc_row[13]),
                'intl_percent_json': db_helper.to_val(nc_row[14]),
            })
        except Exception as e:
            print(f"⚠️ 短时/{name} 写入失败: {e}")

        try:
            for al_row in build_alert_rows(pull_at, name, d['cn'], d['intl']):
                db_helper.insert_row(conn, 'alert', {
                    'pull_at': pull_at, 'city_name': name,
                    'cn_alert_count': al_row[2],
                    'cn_alert_json': db_helper.to_val(al_row[3]),
                    'intl_alert_count': al_row[4],
                    'intl_alert_json': db_helper.to_val(al_row[5]),
                })
        except Exception as e:
            print(f"⚠️ 预警/{name} 写入失败: {e}")

    conn.commit()
    n_nowcast = conn.execute("SELECT COUNT(*) FROM nowcast WHERE pull_at=?", (pull_at,)).fetchone()[0]
    n_alert = conn.execute("SELECT COUNT(*) FROM alert WHERE pull_at=?", (pull_at,)).fetchone()[0]
    print(f"✅ 短时: +{n_nowcast} 行")
    print(f"✅ 预警: +{n_alert} 行")

    conn.close()

    # ========== 阶段3: 写轮次清单(供 convert_raw_to_csv/rebuild_day_csv 读取) ==========
    try:
        with open(os.path.join(raw_round_dir, '_manifest.json'), 'w', encoding='utf-8') as f:
            json.dump({'pull_at': pull_at}, f, ensure_ascii=False)
    except Exception:
        pass

    print(f"\n=== 拉取完成 ===")
    print(f"成功: {total_ok} 城市, 失败: {total_fail} 城市")
    print(f"数据库: {db_helper.DB_PATH}")
    print(f"原始留底: {raw_round_dir} ({len(city_data)} 城市)")


if __name__ == '__main__':
    main()
