
#!/usr/bin/env python3
import hashlib

# ============== 配置区域 ==============
# 在这里修改你需要的参数
PASSWORD = '49ff9a4e5e8bd5e8ce9e057c5adc5d2d'  # 固定的 password
TIMESTAMP = '0'                                 # 固定的 timestamp
LAT = '39.91488908'                            # 纬度 —— 👈 修改这里
LON = '116.40387397'                           # 经度 —— 👈 修改这里
TOKEN = 'cc920d85f8fbb762b6c705375add6c32'      # token (可选)
# =====================================


def generate_key(password, timestamp, lat, lon):
    """
    根据 getkey.py 的 get_lonlat_key 规则生成 key
    公式: MD5(password + timestamp + lat + lon)
    """
    string = password + timestamp + lat + lon
    a = hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    return a.hexdigest()


def generate_url(lat, lon, key, token=TOKEN):
    """生成完整的请求 URL"""
    base_url = 'http://coapi.moji.com/whapi/v2/weather'
    url = f'{base_url}?timestamp={TIMESTAMP}&token={token}&lat={lat}&lon={lon}&key={key}'
    return url


if __name__ == '__main__':
    print("=" * 70)
    print("天气接口 Key 生成工具")
    print("=" * 70)
    print()

    # 生成 key
    key = generate_key(PASSWORD, TIMESTAMP, LAT, LON)

    # 显示详细信息
    print("📝 输入参数:")
    print(f"  password:  {PASSWORD}")
    print(f"  timestamp: {TIMESTAMP}")
    print(f"  lat:       {LAT}")
    print(f"  lon:       {LON}")
    print()

    print("🔐 加密过程:")
    concat_string = PASSWORD + TIMESTAMP + LAT + LON
    print(f"  拼接字符串: password + timestamp + lat + lon")
    print(f"             = '{PASSWORD}' + '{TIMESTAMP}' + '{LAT}' + '{LON}'")
    print(f"             = '{concat_string}'")
    print(f"  MD5 结果:   {key}")
    print()

    print("🌐 生成的 URL:")
    url = generate_url(LAT, LON, key)
    print(f"  {url}")
    print()

    print("=" * 70)
    print("💡 提示: 修改脚本顶部的 LAT 和 LON 即可生成新的 key")
    print("=" * 70)

