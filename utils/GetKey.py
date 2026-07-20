import hashlib
import hmac
import base64
from urllib.parse import quote_plus
class GetKey:
    '''针对华为项目之前短password进行hmacsha256加密，并返回长的password
    password：之前短的pwd'''
    def get_Huawei_password_hmacsha256(password):
        data="H&M"  #"H&M"为开发写死的一个添加的字符串，不排除后续会改，如果改了会影响加密结果，需要同步修改
        hmac_sha256 = hmac.new(password.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
        usedpwd256=hmac_sha256.hex()
        return usedpwd256

    #根据password+1个入参编码获得key
    def get_passwordAndparam1_key(password, param,timestamp='0'):
        string = password + timestamp+'{param}'.format(param=param)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    #预警接口加密规则
    def get_alert_key(password, param,timestamp='0'):
        string = password + timestamp+'{param}'.format(param=param)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5
    # 根据经纬度获得key值
    def get_lonlat_key(password, lon, lat,timestamp='0'):
        string = password + timestamp+'{lat}{lon}'.format(lat=lat, lon=lon)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    # 获得AI生活指数的key值
    # 生成算法 key = MD5(password + timestamp+ type);
    def get_AiIndex_key(password, type, timestamp='0'):
        string = password + str(timestamp) + str(type)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    # 根据城市获得key值
    def get_city_key(password,cityId,timestamp='0'):
        string = password + str(timestamp) + str(cityId)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5



    def hmac_sha256(key, data):
        hmac_sha256 = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
        return hmac_sha256.hex()

    # 根据城市id获得key值
    def get_city_key_hmacsha256(password, citycode, timestamp='0'):
        data=str(timestamp) + str(citycode)
        key=password
        usedkey=GetKey.hmac_sha256(key,data)
        return usedkey

    # 根据经纬度获得key值
    def get_lonlat_key_hmacsha256(password, lon,lat, timestamp='0'):
        data = str(timestamp) + str(lat) +str(lon)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    #获得荣耀朝晚霞接口key
    def get_glow_lonlat_key_hmacsha256(password, lon,lat, timestamp='0',type='1'):
        data = str(timestamp) + str(lon) +str(lat)+str(type)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    # 获得华为天气地图hmacsha256加密的key值
    def get_weather_map_key_hmacsha256(password, cityCode, type,timestamp='0'):
        data = str(timestamp) + str(cityCode) + str(type)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    # 获得华为天气地图hmacsha256加密的key值（文件接口版本file）
    def get_weather_map_file_key_hmacsha256(password, type, timestamp='0'):
        data = str(timestamp) + str(type)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    # 根据地址获得hmacsha256加密的key值
    def get_address_key_hmacsha256(password, address, timestamp='0'):
        data = str(timestamp) + str(address)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    # 根据地址获得key值
    def get_address_key(password, address, timestamp='0'):
        string = password + str(timestamp) + str(address)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    # 获得accu华为搜索接口_hmacsha256加密的key值
    def get_accuSearch_key_hmacsha256(password, keywords, language, size, timestamp='0'):
        data = str(timestamp) + keywords + language + str(size)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    # 获得accu华为搜索接口key值
    def get_accuSearch_key(password, keywords, language,size,timestamp='0'):
        string = password + str(timestamp) + keywords + language + str(size)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    #荣耀全球台风 type固定为2704
    def get_honor_typhoon_key_hmacsha256(password,type='2704', timestamp='0'):
        data = str(timestamp) + str(type)
        key = password
        usedkey = GetKey.hmac_sha256(key, data)
        return usedkey

    # def get_glow_lonlat_key_hmacsha256(password, lon,lat, timestamp='0',type='1'):
    #     data = str(timestamp) + str(lon) +str(lat)+str(type)
    #     key = password
    #     usedkey = GetKey.hmac_sha256(key, data)
    #     return usedkey

    # 根据台风编码获得key值
    def get_typhoon_key(password, typhoon, timestamp='0'):
        string = password + timestamp + str(typhoon)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    #单站雷达接口key
    def get_radar_key(password,lon,lat,level,timestamp='0'):
        string = password + timestamp + lat + lon + str(level)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    #获得poi搜索以及城市搜索的key。该key根据DigestUtils.md5Hex(pwd + timestamp + keywords + language + size)
    def get_Search_md5Hex_key(pwd,keywords,timestamp='0',size='20',language='en'):
        string = pwd + str(timestamp) + keywords+language+str(size)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    # 根据json获得sign值 安卓
    def get_RegistSign_key_android(jsonstr):
        string = jsonstr + "KAndroid"
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        return md5

    # 全球风云加密算法获取key
    def gloableWater(pwd, timestamp, element, version):
        string = pwd + timestamp + element + version
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        key = a.hexdigest()
        return key
    #文件接口v2
    def fileInterfaceKey(pwd, timestamp, elementIds, spaceIds,version='0.0.2'):
        string = pwd + str(timestamp)  + str(version) + str(elementIds) + str(spaceIds)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        key = a.hexdigest()
        return key

    #EC切片v1接口
    def EC_v1_Key(pwd,timestamp,element,version='0.0.2'):
        string = pwd + str(timestamp) + str(element)+ str(version)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        key = a.hexdigest()
        return key

    #文件接口v1
    def fileInterfaceKeyV1(pwd, timestamp, elementIds, version):
        string = pwd + str(timestamp)  + str(elementIds)+ str(version)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        key = a.hexdigest()
        return key

    #获得观测站key值
    def ObservationStation(id,password,timestamp='0'):
        string = password +str(timestamp)+str(id)
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        key = a.hexdigest()
        return key

    # app端二级页面 根据 data(body体) + pwd获得key值
    def get_app_level2_key(bodydata, pwd):
        string = bodydata + pwd
        a = hashlib.md5()
        a.update(string.encode(encoding='utf-8'))
        md5 = a.hexdigest()
        MD5=md5.upper()  #app上key需要转为大写字母
        return MD5

    # 使用私钥对参数字符串进行加密(获取宝马key)
    def get_BM_key(private_key, params):
        data=params
        hmac_sha256 = hmac.new(private_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha1).digest() #宝马用的hashlib.sha1，华为用的hashlib.sha256
        # 将二进制摘要转换为 Base64 编码
        base64_hmac = base64.b64encode(hmac_sha256)
        #做一个 URLEncode，得到签名
        url_encoded_hmac = quote_plus(base64_hmac.decode())
        return url_encoded_hmac


