import datetime
import re
import urllib.parse
from urllib.parse import urlencode

from utils.GetKey import GetKey


class RequestAll:

    @staticmethod
    def QX_getHonorSearchUrl_SHA256(url: str, password: str, keywords: str = '大兴区',
                                    language: str = 'zh-CN', size: str = '20') -> str:
        """荣耀搜索接口 URL 拼接"""
        try:
            timestamp = re.search(r"timestamp=(.*?)&", url).group(1)
        except (AttributeError, IndexError):
            timestamp = 0
        url1 = url.split("?")[0]
        url2 = url.split("?")[1]
        key = GetKey.get_accuSearch_key_hmacsha256(password, keywords, language, size, timestamp=timestamp)
        useurl = f"{url1}?keywords={urllib.parse.quote(keywords)}&size={str(size)}&language={language}&key={key}&{url2}"
        return useurl

    @staticmethod
    def QX_getInteinationalJuhe_SHA256(url: str, password: str, fielddict: dict = None,
                                       lon: str = '116.40387397', lat: str = '39.91488908',
                                       ts: int = None) -> str:
        """墨迹国际化接口（仅支持经纬度）URL 拼接"""
        if ts is None:
            ts = int(datetime.datetime.now().timestamp() * 1000)

        if not fielddict:
            fielddict = {"lang": "zh-CN", "current": "1", "daily": "15", "hourly": "24",
                         "hHis": "8", "dHis": "8", "city": "1",
                         "alert": "1", "nowcast": "2", "tiles": "14", "ocean": "1",
                         "sunBlueGlow": "1"}

        encoded_params = urlencode(fielddict)
        key = GetKey.get_lonlat_key_hmacsha256(password, lon, lat, timestamp=ts)
        usedurl = f"{url}&lon={lon}&lat={lat}&{encoded_params}&ts={str(ts)}&key={key}"
        return usedurl
