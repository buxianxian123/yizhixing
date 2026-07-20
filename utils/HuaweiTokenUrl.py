import datetime
from urllib.parse import urlencode

from utils.GetKey import GetKey


class HuaweiTokenUrl:

    @staticmethod
    def Honor_getPolymerize(url: str, password: str, fielddict: dict = None,
                            test: str = "citycode", citycode: str = "2332635",
                            lon: str = '116.416357', lat: str = '39.928353',
                            timestamp: int = None, ip: str = '16') -> str:
        """荣耀聚合接口 URL 拼接"""
        if timestamp is None:
            timestamp = int(datetime.datetime.now().timestamp() * 1000)

        if not fielddict:
            fielddict = {"metric": "true", "language": "zh-CN", "current": "1", "daily": "15", "hourly": "24",
                         "live": "-1", "aqi": "1", "alert": "1", "aqiForecast": "15", "nowcast": "2",
                         "aqiForecastHourly": "72", "city": "1", "sunBlueGlow": "1"}

        encoded_params = urlencode(fielddict)

        if test == "citycode":
            key = GetKey.get_city_key_hmacsha256(password, citycode, timestamp=timestamp)
            usedurl = f"{url}&adcode={citycode}&{encoded_params}&timestamp={str(timestamp)}&key={key}"
        else:
            key = GetKey.get_lonlat_key_hmacsha256(password, lon, lat, timestamp=timestamp)
            usedurl = f"{url}&lon={lon}&lat={lat}&{encoded_params}&timestamp={str(timestamp)}&key={key}"

        return usedurl

    @staticmethod
    def Honor_global_typhoon(typhoonCode: str = 'all', timestamp: str = '0',
                             model: str = "当前全部生效台风", type: str = '2704') -> str:
        """荣耀全球台风接口（测试环境）"""
        if model == "当前全部生效台风":
            typhoon_honor_url = ("https://datash-api-moweather.mojitest.com/whapi/honor/typhoon"
                                 "?token=a03cdef2437423530a30623c40aaf4a0&timestamp=0"
                                 f"&type={type}&language=zh-CN&returnCurrTyphoonList=true")
            typhoon_honor_pwd = "32a02ece5c0b183fd95f7aed95f26a4f2975b30e6483451c6440edfe29a1e141"
            key = GetKey.get_honor_typhoon_key_hmacsha256(typhoon_honor_pwd, type='2704', timestamp=timestamp)
            typhoon_honor_prd_usedurl = typhoon_honor_url + "&key=" + key
        return typhoon_honor_prd_usedurl
