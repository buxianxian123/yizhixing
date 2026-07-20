
#!/usr/bin/env python3
import hashlib
import hmac
from urllib.parse import urlencode

# ============== 配置区域 ==============
# 国内版接口
PASSWORD_CN = '49ff9a4e5e8bd5e8ce9e057c5adc5d2d'  # 国内版 password
TIMESTAMP_CN = '0'
TOKEN_CN = 'cc920d85f8fbb762b6c705375add6c32'

# 国际版接口
PASSWORD_IN = '923ffbda8b65bf0f8e126824d050887a'  # 国际版生产环境 password
TS_IN = '0'
TOKEN_IN = 'b88b7a5375e293671270016fe556a4b5'

# 要测试的经纬度 (两个接口共用)
LAT = '1.3521'
LON = '103.8198'
# =====================================


def get_lonlat_key(password, lon, lat, timestamp='0'):
    """国内版: MD5(password + timestamp + lat + lon)"""
    string = password + timestamp + lat + lon
    a = hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    return a.hexdigest()


def hmac_sha256(key, data):
    """HMAC-SHA256 加密"""
    hmac_sha256 = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
    return hmac_sha256.hex()


def get_lonlat_key_hmacsha256(password, lon, lat, timestamp='0'):
    """国际版: HMAC-SHA256(password, timestamp + lat + lon)"""
    data = str(timestamp) + str(lat) + str(lon)
    return hmac_sha256(password, data)


def generate_cn_url(lat, lon, key, token=TOKEN_CN, timestamp=TIMESTAMP_CN):
    """生成国内版 URL"""
    base_url = 'http://coapi.moji.com/whapi/v2/weather'
    url = f'{base_url}?timestamp={timestamp}&token={token}&lat={lat}&lon={lon}&key={key}'
    return url


def generate_in_url(lat, lon, key, token=TOKEN_IN, ts=TS_IN, fielddict=None):
    """生成国际版 URL"""
    if fielddict is None:
        fielddict = {
            "lang": "zh-CN",
            "city": "1",
            "current": "1",
            "hourly": "360",
            "hHis": "0",
            "aqiForecastHourly": "72",
            "metric": "true"
        }
    base_url = 'https://datasw1.api.moweather.com/whapi/in/weather'
    encoded_params = urlencode(fielddict)
    url = f'{base_url}?token={token}&lon={lon}&lat={lat}&{encoded_params}&ts={ts}&key={key}'
    return url


if __name__ == '__main__':
    print("=" * 70)
    print("天气接口 Key 生成工具 (国内版 + 国际版)")
    print("=" * 70)
    print()

    print("📍 测试位置:")
    print(f"  lat: {LAT}")
    print(f"  lon: {LON}")
    print()

    # ========== 国内版 ==========
    print("🇨🇳 国内版接口:")
    print("-" * 70)
    key_cn = get_lonlat_key(PASSWORD_CN, LON, LAT, TIMESTAMP_CN)
    url_cn = generate_cn_url(LAT, LON, key_cn)

    print("🔐 加密方式: MD5")
    print(f"   拼接字符串: password + timestamp + lat + lon")
    print(f"                = '{PASSWORD_CN}' + '{TIMESTAMP_CN}' + '{LAT}' + '{LON}'")
    print(f"                = '{PASSWORD_CN + TIMESTAMP_CN + LAT + LON}'")
    print(f"   生成 key:   {key_cn}")
    print()
    print("🌐 URL:")
    print(f"   {url_cn}")
    print()

    # ========== 国际版 ==========
    print("🌍 国际版接口:")
    print("-" * 70)

    key_in = get_lonlat_key_hmacsha256(PASSWORD_IN, LON, LAT, TS_IN)
    url_in = generate_in_url(LAT, LON, key_in)

    print("🔐 加密方式: HMAC-SHA256")
    print(f"   data = ts + lat + lon")
    print(f"        = '{TS_IN}' + '{LAT}' + '{LON}'")
    print(f"        = '{TS_IN + LAT + LON}'")
    print(f"   生成 key:   {key_in}")
    print()
    print("🌐 URL:")
    print(f"   {url_in}")

    # 验证一下和用户提供的 URL 是否匹配
    expected_key = '0134ace27e5c2c717c955aaa0a8b7d1cb5f5da26febf045e620041cb41350e92'
    if LAT == '1.3521' and LON == '103.8198':
        print()
        print("✅ 验证结果:")
        if key_in == expected_key:
            print(f"   生成的 key 与预期一致！")
        else:
            print(f"   生成的 key 与预期不一致")
            print(f"   预期: {expected_key}")

    print()
    print("=" * 70)
    print("💡 提示: 修改脚本顶部的 LAT 和 LON 即可生成新的 key")
    print("=" * 70)

