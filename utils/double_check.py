
import hashlib
import hmac

# 国际版接口参数
PASSWORD_IN = '923ffbda8b65bf0f8e126824d050887a'
lon = '103.8198'
lat = '1.3521'
ts = '0'
expected_key = '0134ace27e5c2c717c955aaa0a8b7d1cb5f5da26febf045e620041cb41350e92'

print("=" * 70)
print("双重验证国际版接口 Key")
print("=" * 70)
print()

# ========== HMAC-SHA256 方式 ==========
print("1️⃣  HMAC-SHA256 方式:")
print("-" * 70)

def hmac_sha256(key, data):
    hmac_sha256 = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
    return hmac_sha256.hex()

data_hmac = ts + lat + lon
key_hmac = hmac_sha256(PASSWORD_IN, data_hmac)
print(f"   data = '{data_hmac}'")
print(f"   key  = {key_hmac}")
print(f"   匹配? {key_hmac == expected_key}")
print()

# ========== 各种 MD5 方式 ==========
print("2️⃣  各种 MD5 方式:")
print("-" * 70)

test_cases = [
    ("password + ts + lat + lon", PASSWORD_IN + ts + lat + lon),
    ("ts + lat + lon + password", ts + lat + lon + PASSWORD_IN),
    ("password + lat + lon + ts", PASSWORD_IN + lat + lon + ts),
    ("password + ts + lon + lat", PASSWORD_IN + ts + lon + lat),
    ("ts + lon + lat + password", ts + lon + lat + PASSWORD_IN),
    ("password + (ts + lat + lon)", PASSWORD_IN + (ts + lat + lon)),
    ("password + ts + lat + lon + token", PASSWORD_IN + ts + lat + lon + 'b88b7a5375e293671270016fe556a4b5'),
]

for desc, string in test_cases:
    a = hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    key = a.hexdigest()
    if key == expected_key:
        print(f"✅ {desc}")
        print(f"   string = '{string}'")
        print(f"   key    = {key}")
    else:
        print(f"❌ {desc}")

print()
print("=" * 70)
print()
print("让我们看看 key 的长度:")
print(f"  预期 key 长度: {len(expected_key)}")
print(f"  MD5 长度: 32")
print(f"  HMAC-SHA256 长度: 64")
print()
print(f"预期 key 长度是 64，所以应该是 HMAC-SHA256，不是 MD5")
print()
print("让我再看看 RequestAll.py 第 40 行:")
print("  key = GetKey.get_lonlat_key_hmacsha256(password, lon, lat, timestamp=ts)")
print("确实调用的是 hmacsha256 版本!")

