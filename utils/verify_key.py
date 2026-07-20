
import hashlib

# URL 中的参数
timestamp = '0'
lat = '39.91488908'
lon = '116.40387397'
expected_key = 'cecaa19db0a0151a841c68f55ee0ed47'
suspected_password = '49ff9a4e5e8bd5e8ce9e057c5adc5d2d'
token = 'cc920d85f8fbb762b6c705375add6c32'

print("=" * 60)
print("验证 URL key 生成")
print("=" * 60)
print(f"URL: http://coapi.moji.com/whapi/v2/weather?timestamp=0&token=cc920d85f8fbb762b6c705375add6c32&lat=39.91488908&lon=116.40387397&key=cecaa19db0a0151a841c68f55ee0ed47")
print(f"预期 key: {expected_key}")
print(f"疑似 password: {suspected_password}")
print()

# 按照 getkey.py 里的 get_lonlat_key 方式
print("--- 测试 1: get_lonlat_key 方式 (password + timestamp + lat + lon) ---")
string = suspected_password + timestamp + lat + lon
a = hashlib.md5()
a.update(string.encode(encoding='utf-8'))
key1 = a.hexdigest()
print(f"拼接字符串: '{string}'")
print(f"生成的 key: {key1}")
print(f"匹配结果: {'✅ 匹配！' if key1 == expected_key else '❌ 不匹配'}")
print()

# 试试 lat 和 lon 顺序反过来
print("--- 测试 2: password + timestamp + lon + lat ---")
string = suspected_password + timestamp + lon + lat
a = hashlib.md5()
a.update(string.encode(encoding='utf-8'))
key2 = a.hexdigest()
print(f"拼接字符串: '{string}'")
print(f"生成的 key: {key2}")
print(f"匹配结果: {'✅ 匹配！' if key2 == expected_key else '❌ 不匹配'}")
print()

# 试试包含 token
print("--- 测试 3: password + timestamp + token + lat + lon ---")
string = suspected_password + timestamp + token + lat + lon
a = hashlib.md5()
a.update(string.encode(encoding='utf-8'))
key3 = a.hexdigest()
print(f"拼接字符串: '{string}'")
print(f"生成的 key: {key3}")
print(f"匹配结果: {'✅ 匹配！' if key3 == expected_key else '❌ 不匹配'}")
print()

# 试试 password 先用 hmacsha256 加密一次（华为项目那种）
print("--- 测试 4: 先用 HMAC-SHA256 加密 password ---")
import hmac
data = "H&M"
hmac_sha256 = hmac.new(suspected_password.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
usedpwd256 = hmac_sha256.hex()
print(f"HMAC-SHA256(password, 'H&M') = {usedpwd256}")
string = usedpwd256 + timestamp + lat + lon
a = hashlib.md5()
a.update(string.encode(encoding='utf-8'))
key4 = a.hexdigest()
print(f"拼接字符串: '{string}'")
print(f"生成的 key: {key4}")
print(f"匹配结果: {'✅ 匹配！' if key4 == expected_key else '❌ 不匹配'}")
print()

# 我们有预期的 key，反过来看看能不能找到正确的拼接方式
print("--- 测试 5: 已知预期 key，我们来分析它 ---")
print(f"预期 key 的长度: {len(expected_key)} (MD5 是 32 字符，匹配)")
print()

# 试试把 suspected_password 当成是已经加密后的 key，反过来找 password？
print("--- 测试 6: 反向思维 - 假设 expected_key 是 MD5 结果，我们已知拼接字符串的一部分 ---")
print(f"我们需要: MD5(password + '{timestamp}{lat}{lon}') = '{expected_key}'")
print()

# 等等，让我们看看 URL 里的 token 也是 32 位的，是不是也是 MD5？
print("--- 测试 7: 检查 URL 里的 token ---")
print(f"token: {token} (长度 {len(token)})")
print(f"key:   {expected_key} (长度 {len(expected_key)})")
print()

# 让我们试试暴力一点，看看常见的拼接方式
print("--- 测试 8: 测试常见的几种拼接方式 ---")
test_cases = [
    # (描述, 拼接函数)
    ("password + lat + lon", lambda p: p + lat + lon),
    ("password + lon + lat", lambda p: p + lon + lat),
    ("password + timestamp + lat + lon", lambda p: p + timestamp + lat + lon),
    ("password + timestamp + lon + lat", lambda p: p + timestamp + lon + lat),
    ("lat + lon + password", lambda p: lat + lon + p),
    ("timestamp + lat + lon + password", lambda p: timestamp + lat + lon + p),
    ("password + lat + lon + timestamp", lambda p: p + lat + lon + timestamp),
    ("password + '0' + lat + lon", lambda p: p + '0' + lat + lon),
    ("password + token + lat + lon", lambda p: p + token + lat + lon),
    ("token + password + lat + lon", lambda p: token + p + lat + lon),
    ("password + timestamp + token + lat + lon", lambda p: p + timestamp + token + lat + lon),
    ("password + timestamp + lat + lon + token", lambda p: p + timestamp + lat + lon + token),
]

for desc, func in test_cases:
    string = func(suspected_password)
    a = hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    key = a.hexdigest()
    if key == expected_key:
        print(f"✅ 找到匹配！方式: {desc}")
        print(f"   拼接字符串: '{string}'")
        print(f"   生成的 key: {key}")
    else:
        print(f"❌ 不匹配: {desc}")

print()

# 等等，也许 49ff9a4e5e8bd5e8ce9e057c5adc5d2d 不是 password，而是别的？
print("--- 测试 9: 假设 '49ff9a4e5e8bd5e8ce9e057c5adc5d2d' 是中间结果 ---")
print(f"让我们看看它是不是某个东西的 MD5？长度是 32，是的")
print()

# 让我们想想，URL 里有 key=cecaa19db0a0151a841c68f55ee0ed47，这可能是用另一个 password 生成的
print("--- 测试 10: 让我们用预期 key 反过来看看 ---")
print("既然我们知道了预期的 key，我们可以看看能不能找到规律...")
print()
print("让我们重新看 getkey.py 里的方法:")
print("- get_lonlat_key: MD5(password + timestamp + lat + lon)")
print("- get_passwordAndparam1_key: MD5(password + timestamp + param)")
print("- get_city_key: MD5(password + timestamp + cityId)")
print()
print("可能这个接口用的是 get_passwordAndparam1_key？param 是什么呢？")
print()

# 试试 param 是经纬度拼接，或者别的组合
print("--- 测试 11: 试试 get_passwordAndparam1_key 方式 ---")
# param 可能是 lat,lon 或者 lon,lat 或者其他组合
params_to_try = [
    f"{lat},{lon}",
    f"{lon},{lat}",
    f"{lat}{lon}",
    f"{lon}{lat}",
    lat,
    lon,
    token,
    f"{token}{lat}{lon}",
]

for param in params_to_try:
    string = suspected_password + timestamp + param
    a = hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    key = a.hexdigest()
    if key == expected_key:
        print(f"✅ 找到匹配！param='{param}'")
        print(f"   拼接字符串: '{string}'")
        print(f"   生成的 key: {key}")

print()
print("=" * 60)
print()

# 等等，也许应该用 expected_key 和 suspected_password 来看看关系
print("--- 最后的思路 ---")
print(f"你给的字符串: {suspected_password}")
print(f"URL 里的 key: {expected_key}")
print(f"URL 里的 token: {token}")
print()
print("让我们检查一下这些是不是有什么关系...")

# 看看 suspected_password 是不是 token 的某种变换？
print(f"suspected_password == token? {suspected_password == token}")
print(f"suspected_password == key? {suspected_password == expected_key}")

