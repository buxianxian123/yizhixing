#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成所有测试城市的 国内 + 国际 接口 URL

加密规则（已验证）:
  国内: key = MD5(password + timestamp + lat + lon)            # lat 在前
  国际: key = HMAC-SHA256(password, timestamp + lat + lon)     # lat 在前

⚠️ 经纬度直接用 CSV 原始字符串，不做 float 转换，避免精度丢失。
"""
import hashlib
import hmac
import csv
from urllib.parse import urlencode

# ============== 配置区域 ==============
# 国内版接口 (生产环境)
PASSWORD_CN = '49ff9a4e5e8bd5e8ce9e057c5adc5d2d'
TIMESTAMP_CN = '0'
TOKEN_CN = 'cc920d85f8fbb762b6c705375add6c32'
BASE_URL_CN = 'http://coapi.moji.com/whapi/v2/weather'

# 国际版接口 (生产环境)
PASSWORD_IN = '923ffbda8b65bf0f8e126824d050887a'
TS_IN = '0'
TOKEN_IN = 'b88b7a5375e293671270016fe556a4b5'
BASE_URL_IN = 'https://datasw1.api.moweather.com/whapi/in/weather'

# 国际版接口字段参数 —— 覆盖全部 6 个模块:
#   实况(current) 短时降水(nowcast) 小时预报(hourly)
#   15天预报(daily) AQI(aqi+aqiForecastHourly) 预警(alert)
FIELD_DICT_IN = {
    "lang": "zh-CN",
    "city": "1",
    "current": "1",            # 实况天气模块
    "nowcast": "2",            # 短时降水模块
    "hourly": "360",           # 小时预报模块 (覆盖 24/48/72h)
    "hHis": "0",
    "daily": "15",             # 15天预报模块
    "aqi": "1",                # AQI 实况
    "aqiForecastHourly": "72", # AQI 预报
    "alert": "1",              # 预警模块
    "metric": "true",
}

CSV_PATH = '/Users/yingxu.han/IdeaProjects/untitled/项目目录/墨迹国际化与国内版本天气数据一致性测试/天气一致性测试城市_热门城市筛选.csv'
OUTPUT_HTML = '/Users/yingxu.han/IdeaProjects/untitled/项目目录/墨迹国际化与国内版本天气数据一致性测试/城市URL列表.html'
# =====================================


def get_cn_key(lat, lon, timestamp='0'):
    """国内版: MD5(password + timestamp + lat + lon)"""
    string = PASSWORD_CN + timestamp + lat + lon
    a = hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    return a.hexdigest()


def get_in_key(lat, lon, timestamp='0'):
    """国际版: HMAC-SHA256(password, timestamp + lat + lon)"""
    data = timestamp + lat + lon
    hmac_sha256 = hmac.new(PASSWORD_IN.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
    return hmac_sha256.hex()


def gen_cn_url(lat, lon):
    key = get_cn_key(lat, lon, TIMESTAMP_CN)
    return f'{BASE_URL_CN}?timestamp={TIMESTAMP_CN}&token={TOKEN_CN}&lat={lat}&lon={lon}&key={key}'


def gen_in_url(lat, lon):
    key = get_in_key(lat, lon, TS_IN)
    encoded_params = urlencode(FIELD_DICT_IN)
    return f'{BASE_URL_IN}?token={TOKEN_IN}&lon={lon}&lat={lat}&{encoded_params}&ts={TS_IN}&key={key}'


def self_check():
    """自检：用之前人工验证过的数据，确认加密逻辑无误"""
    print("=" * 70)
    print("🔍 自检：验证加密逻辑")
    print("=" * 70)

    # 国内版已知正确例子 (北京附近, 之前验证过)
    cn_lat, cn_lon = '39.91488908', '116.40387397'
    cn_expected = 'cecaa19db0a0151a841c68f55ee0ed47'
    cn_key = get_cn_key(cn_lat, cn_lon)
    print(f"国内版 MD5: lat={cn_lat}, lon={cn_lon}")
    print(f"  生成 key: {cn_key}")
    print(f"  预期 key: {cn_expected}")
    print(f"  {'✅ 通过' if cn_key == cn_expected else '❌ 失败'}")
    print()

    # 国际版已知正确例子 (新加坡, 之前验证过)
    in_lat, in_lon = '1.3521', '103.8198'
    in_expected = '0134ace27e5c2c717c955aaa0a8b7d1cb5f5da26febf045e620041cb41350e92'
    in_key = get_in_key(in_lat, in_lon)
    print(f"国际版 HMAC-SHA256: lat={in_lat}, lon={in_lon}")
    print(f"  生成 key: {in_key}")
    print(f"  预期 key: {in_expected}")
    print(f"  {'✅ 通过' if in_key == in_expected else '❌ 失败'}")
    print()

    if cn_key != cn_expected or in_key != in_expected:
        print("⚠️ 自检失败！加密逻辑有误，停止生成。")
        return False
    print("✅ 自检通过，加密逻辑正确，开始生成所有城市 URL\n")
    return True


def read_cities():
    """读取 CSV，返回城市列表。经纬度保留原始字符串。"""
    cities = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:  # utf-8-sig 去掉 BOM
        reader = csv.DictReader(f)
        for row in reader:
            # 经纬度用原始字符串，仅 strip 首尾空白(不改变数值精度)
            lon = row['Flon'].strip()
            lat = row['Flat'].strip()
            cities.append({
                'fcity': row['Fcity'].strip(),
                'lon': lon,
                'lat': lat,
                'internal': row['Finternal'].strip(),
                'name': row['Fcityname_cn'].strip(),
                'bj_code': row['Fbj_code'].strip(),
                'category': row['分类'].strip(),
                'reason': row['选取原因'].strip(),
            })
    return cities


def generate_html(cities):
    """生成 HTML 表格，方便核对经纬度和复制 URL"""
    rows_html = []
    for i, c in enumerate(cities, 1):
        cn_url = gen_cn_url(c['lat'], c['lon'])
        in_url = gen_in_url(c['lat'], c['lon'])

        # 重复城市标注 (台北市在 CSV 出现两次)
        dup_note = ''
        if c['name'] == '台北市' and c['fcity'] == '3179':
            dup_note = ' (CSV重复行)'

        rows_html.append(f"""
        <tr>
            <td class="idx">{i}</td>
            <td class="name">{c['name']}<span class="dup">{dup_note}</span></td>
            <td class="cat">{c['category']}</td>
            <td class="reason">{c['reason']}</td>
            <td class="lonlat" title="CSV原始值">{c['lon']}</td>
            <td class="lonlat" title="CSV原始值">{c['lat']}</td>
            <td class="url-cell">
                <a href="{cn_url}" target="_blank" class="url-link cn">国内URL ↗</a>
                <button class="copy-btn" data-url="{cn_url}">复制</button>
            </td>
            <td class="url-cell">
                <a href="{in_url}" target="_blank" class="url-link intl">国际URL ↗</a>
                <button class="copy-btn" data-url="{in_url}">复制</button>
            </td>
        </tr>""")

    # 统计分类
    from collections import Counter
    cat_counter = Counter(c['category'] for c in cities)
    cat_summary = ' | '.join(f"{k}: {v}" for k, v in cat_counter.most_common())

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>国内/国际接口 URL 列表（{len(cities)}个城市）</title>
<style>
    body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 20px; background: #f5f6f8; color: #333; }}
    h1 {{ font-size: 20px; }}
    .summary {{ background: #fff; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; line-height: 1.8; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
    .summary b {{ color: #d4380d; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.06); font-size: 13px; }}
    th, td {{ border: 1px solid #e8e8e8; padding: 8px 10px; text-align: left; vertical-align: middle; }}
    th {{ background: #fafafa; font-weight: 600; position: sticky; top: 0; }}
    tr:hover {{ background: #fafcff; }}
    .idx {{ color: #999; text-align: center; width: 40px; }}
    .name {{ font-weight: 600; white-space: nowrap; }}
    .dup {{ color: #d4380d; font-size: 11px; margin-left: 4px; }}
    .cat {{ color: #1890ff; white-space: nowrap; }}
    .reason {{ color: #666; white-space: nowrap; }}
    .lonlat {{ font-family: "SF Mono", Consolas, monospace; color: #d4380d; font-weight: 600; }}
    .url-cell {{ white-space: nowrap; }}
    .url-link {{ display: inline-block; padding: 3px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; margin-right: 4px; }}
    .url-link.cn {{ background: #e6f7ff; color: #1890ff; border: 1px solid #91d5ff; }}
    .url-link.intl {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
    .url-link:hover {{ opacity: 0.85; }}
    .copy-btn {{ padding: 3px 8px; font-size: 11px; cursor: pointer; border: 1px solid #d9d9d9; background: #fff; border-radius: 4px; }}
    .copy-btn:hover {{ background: #f0f0f0; }}
    .copy-btn.copied {{ background: #52c41a; color: #fff; border-color: #52c41a; }}
    .tip {{ color: #999; font-size: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<h1>国内 / 国际接口 URL 列表</h1>
<div class="summary">
    📊 共 <b>{len(cities)}</b> 个城市 (CSV {len(cities)}行，含台北市重复行) &nbsp;|&nbsp;
    分类: {cat_summary}<br>
    🔐 加密: 国内 <b>MD5</b>(pwd+ts+lat+lon) &nbsp;|&nbsp; 国际 <b>HMAC-SHA256</b>(pwd, ts+lat+lon)<br>
    ⚠️ 经纬度为 <b>CSV原始字符串</b>，红色标注，请逐个与 CSV 核对。
</div>
<table>
<thead>
<tr>
    <th>序号</th><th>城市</th><th>分类</th><th>选取原因</th>
    <th>经度(lon)</th><th>纬度(lat)</th>
    <th>国内接口</th><th>国际接口</th>
</tr>
</thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>
<p class="tip">💡 点击「国内URL / 国际URL」在新标签打开接口，点「复制」复制完整 URL。</p>
<script>
document.querySelectorAll('.copy-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        const url = btn.dataset.url;
        navigator.clipboard.writeText(url).then(() => {{
            const old = btn.textContent;
            btn.textContent = '已复制';
            btn.classList.add('copied');
            setTimeout(() => {{ btn.textContent = old; btn.classList.remove('copied'); }}, 1200);
        }});
    }});
}});
</script>
</body>
</html>"""
    return html


def main():
    if not self_check():
        return

    cities = read_cities()
    print(f"📂 读取到 {len(cities)} 个城市\n")

    # 控制台输出前5个 + 新加坡，供快速核对
    print("=" * 70)
    print("📋 前 5 个城市预览（完整列表见 HTML 文件）")
    print("=" * 70)
    for c in cities[:5]:
        print(f"\n[{c['fcity']}] {c['name']} ({c['category']})")
        print(f"  经度 lon = {c['lon']}")
        print(f"  纬度 lat = {c['lat']}")
        print(f"  国内URL: {gen_cn_url(c['lat'], c['lon'])}")
        print(f"  国际URL: {gen_in_url(c['lat'], c['lon'])}")

    # 单独打印新加坡，和之前验证的做参照
    sg = next((c for c in cities if c['name'] == '新加坡'), None)
    if sg:
        print(f"\n[新加坡参照] CSV里 lon={sg['lon']}, lat={sg['lat']}")
        print(f"  (注意: 之前验证用的 lon=103.8198/lat=1.3521 精度不同，CSV用的是更精确的值)")
        print(f"  国际URL: {gen_in_url(sg['lat'], sg['lon'])}")

    # 生成 HTML
    html = generate_html(cities)
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n{'=' * 70}")
    print(f"✅ 完成！共生成 {len(cities)} 个城市的 URL")
    print(f"📄 HTML 文件: {OUTPUT_HTML}")
    print(f"   双击用浏览器打开即可核对经纬度和复制 URL")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
