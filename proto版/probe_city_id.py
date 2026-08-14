#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针 v2：用一个 city id 去问国内 proto detail 接口，反查它对应哪座城市。

v1 教训: 请求体带经纬度时接口按经纬度返回, id 被无视(返回的还是北京东城区)。
v2 做法: 去掉 lon/lat, 只传 id, 并试 coordinate=2/1/0, 看接口认不认 id。

运行:  cd proto版
      python3 probe_city_id.py 131511          # 查 Fcity=131511
      python3 probe_city_id.py 471400          # 查 Finternal=471400

注意: 拉真实接口, 自己跑, 别后台触发。
"""
import sys, os, json, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import weather_pb2
from google.protobuf.json_format import MessageToDict

URL_PRD = "https://weather.api.moji.com/data/detail"


def build_body(city_id, coordinate=2, with_xy=True, lon=116.407112, lat=39.904138):
    city = {"avatarId": 8, "coordinate": coordinate, "cr": 1, "id": int(city_id),
            "type": 1, "voice": {"lang": "CN", "tu": "c", "wu": "beau"}}
    if with_xy:
        city["lon"] = lon
        city["lat"] = lat
    return {
        "common": {"app_version": "1009086401", "device": "MI 5", "height": 1920,
                   "identifier": "mo8c02c306a1cf5721b84eb0984d8d49", "language": "CN",
                   "os_version": "26", "package_name": "com.moji.mjweather", "pid": 5599,
                   "platform": "Android", "uid": "209808450010611712", "width": 1080},
        "params": {"city": [city]},
    }


def post(body):
    try:
        resp = requests.post(URL_PRD, data=json.dumps(body), timeout=25)
    except Exception as e:
        return {'_err': f"请求失败 {e}"}
    if resp.status_code != 200:
        return {'_err': f"HTTP {resp.status_code}: {resp.text[:200]}"}
    try:
        msg = weather_pb2.Weather()
        msg.ParseFromString(resp.content)
        d = MessageToDict(msg, preserving_proto_field_name=True)
        if int(d.get('code', -1)) != 0:
            return {'code': d.get('code')}
        det = (d.get('detail') or [{}])[0]
        return {
            'code': d.get('code'),
            'cityId': det.get('cityId'), 'pCityId': det.get('pCityId'),
            'cityName': det.get('cityName'), 'pCityName': det.get('pCityName'),
        }
    except Exception as e:
        return {'_err': f"pb解析失败 {e}"}


def probe(city_id):
    print(f"=== 反查 id={city_id} ===")
    # 基准: 带北京经纬度(coordinate=2) → 应返回东城区/北京, 证明经纬度优先
    r0 = post(build_body(city_id, coordinate=2, with_xy=True))
    print(f"[A] 带经纬度 coor=2      -> {r0}")
    # 不带经纬度, 只传 id, 试三种 coordinate
    for coord in (2, 1, 0):
        r = post(build_body(city_id, coordinate=coord, with_xy=False))
        print(f"[B] 只传id  coor={coord}      -> {r}")
    # 汇总判断: 若某组返回的 cityId/pCityId/cityName 与北京东城区(5009/33)不同, 则接口认了 id
    beijing = {'5009', '33'}
    print("\n判断:")
    found = False
    for coord in (2, 1, 0):
        r = post(build_body(city_id, coordinate=coord, with_xy=False))
        if '_err' in r or 'code' not in r:
            continue
        if str(r.get('cityId')) not in beijing and r.get('cityName'):
            print(f"  ✅ coordinate={coord} 时接口认了 id={city_id} → 城市是【{r.get('pCityName') or r.get('cityName')}】")
            found = True
    if not found:
        print(f"  ❌ 三种 coordinate 都不认 id={city_id}(返回东城区/北京或报错) → 131511 不是这个 detail 接口的 city id")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 probe_city_id.py <city_id>  例: 131511")
        sys.exit(1)
    probe(sys.argv[1])
