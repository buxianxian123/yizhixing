
import hashlib
import hmac

# 国际版接口参数
url = 'https://datasw1.api.moweather.com/whapi/in/weather?token=b88b7a5375e293671270016fe556a4b5&lon=103.8198&lat=1.3521&lang=zh-CN&city=1&current=1&hourly=360&hHis=0&aqiForecastHourly=72&metric=true&ts=0&key=0134ace27e5c2c717c955aaa0a8b7d1cb5f5da26febf045e620041cb41350e92'
token = 'b88b7a5375e293671270016fe556a4b5'
lon = '103.8198'
lat = '1.3521'
ts = '0'
expected_key = '0134ace27e5c2c717c955aaa0a8b7d1cb5f5da26febf045e620041cb41350e92'

# 国内版的 password (试试这个行不行)
password_cn = '49ff9a4e5e8bd5e8ce9e057c5adc5d2d'

print("=" * 70)
print("验证国际版接口 Key")
print("=" * 70)
print(f"URL: {url}")
print()
print("参数:")
print(f"  token: {token}")
print(f"  lon:   {lon}")
print(f"  lat:   {lat}")
print(f"  ts:    {ts}")
print(f"  key:   {expected_key}")
print()

# GetKey.py 中的实现
def hmac_sha256(key, data):
    hmac_sha256 = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
    return hmac_sha256.hex()

def get_lonlat_key_hmacsha256(password, lon, lat, timestamp='0'):
    data = str(timestamp) + str(lat) + str(lon)
    key = password
    usedkey = hmac_sha256(key, data)
    return usedkey

print("--- 测试 1: 用国内版 password 试试 ---")
key1 = get_lonlat_key_hmacsha256(password_cn, lon, lat, ts)
print(f"data = ts + lat + lon = '{ts}' + '{lat}' + '{lon}' = '{ts + lat + lon}'")
print(f"生成的 key: {key1}")
print(f"匹配吗？   {key1 == expected_key}")
print()

print("--- 测试 2: 用 token 作为 password 试试 ---")
key2 = get_lonlat_key_hmacsha256(token, lon, lat, ts)
print(f"data = ts + lat + lon = '{ts}' + '{lat}' + '{lon}' = '{ts + lat + lon}'")
print(f"生成的 key: {key2}")
print(f"匹配吗？   {key2 == expected_key}")
print()

print("--- 测试 3: 试试不同的拼接顺序 ---")
test_cases = [
    ("ts + lat + lon", ts + lat + lon),
    ("ts + lon + lat", ts + lon + lat),
    ("lat + lon + ts", lat + lon + ts),
    ("lon + lat + ts", lon + lat + ts),
    ("ts + lat + lon + token", ts + lat + lon + token),
    ("token + ts + lat + lon", token + ts + lat + lon),
]

# 试试用 token 做 password
for desc, data in test_cases:
    key = hmac_sha256(token, data)
    if key == expected_key:
        print(f"✅ 找到匹配！拼接方式: {desc}")
        print(f"   data: '{data}'")
        print(f"   key:  {key}")

print()

# 也试试用国内版 password
print("--- 测试 4: 用国内版 password 试试不同拼接 ---")
for desc, data in test_cases:
    key = hmac_sha256(password_cn, data)
    if key == expected_key:
        print(f"✅ 找到匹配！拼接方式: {desc}")
        print(f"   data: '{data}'")
        print(f"   key:  {key}")

print()
print("=" * 70)
print()
print("📝 总结:")
print("  国内版接口: get_lonlat_key (MD5)")
print("             公式: MD5(password + timestamp + lat + lon)")
print()
print("  国际版接口: get_lonlat_key_hmacsha256 (HMAC-SHA256)")
print("             公式: HMAC-SHA256(password, timestamp + lat + lon)")
print()

