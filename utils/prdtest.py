from utils.GetKey import GetKey


class prdtest:

    @staticmethod
    def Honor_global_typhoon(typhoonCode: str = 'all', timestamp: str = '0',
                             model: str = "当前全部生效台风", type: str = '2704') -> str:
        """荣耀全球台风接口（生产环境）"""
        if model == "当前全部生效台风":
            typhoon_honor_url = ("https://datash.api.moweather.com/whapi/honor/typhoon"
                                 "?token=86b9a8b8c91828af80c894bc287be8d1&timestamp=0"
                                 f"&type={type}&language=zh-CN&returnCurrTyphoonList=true")
            typhoon_honor_pwd = "0c72cbee13c9e3949f35a0f0edf9e9eed5d4e648ac49a1491927e3756aa96a68"
            key = GetKey.get_honor_typhoon_key_hmacsha256(typhoon_honor_pwd, type='2704', timestamp=timestamp)
            typhoon_honor_prd_usedurl = typhoon_honor_url + "&key=" + key
        return typhoon_honor_prd_usedurl
