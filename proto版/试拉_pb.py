#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
试拉国内 proto detail 接口, 看 pb 解析后的真实 json 结构。
拉真实接口, 自己跑:  cd 项目根 && python3 utils/试拉_pb.py
跑完把打印的【结构概览】或 data/比对结果/_北京_pb样本.json 发我, 用来核准字段映射。
"""
import os, sys, json, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import weather_pb2
from google.protobuf.json_format import MessageToDict

URL = "https://weather.api.moji.com/data/detail"  # prd 生产

# 经纬度方式拉北京 (CSV: 116.407112, 39.904138)
body = {
    "common": {"app_version": "1009086401", "device": "MI 5", "height": 1920,
               "identifier": "mo8c02c306a1cf5721b84eb0984d8d49", "language": "CN",
               "os_version": "26", "package_name": "com.moji.mjweather", "pid": "5599",
               "platform": "Android", "uid": "209808450010611712", "width": 1080},
    "params": {"city": [{"avatarId": 8, "coordinate": 2, "cr": 1, "id": 1028595, "type": 1,
                         "lon": 116.407112, "lat": 39.904138,
                         "voice": {"lang": "CN", "tu": "c", "wu": "beau"}}]}
}

print("POST", URL, "(北京 116.407112, 39.904138)")
resp = requests.post(URL, data=json.dumps(body), timeout=25)
print("HTTP", resp.status_code, "内容", len(resp.content), "字节")
if resp.status_code != 200:
    print("❌ HTTP非200, 响应前300字:", resp.text[:300]); sys.exit(1)

msg = weather_pb2.Weather()
try:
    msg.ParseFromString(resp.content)
except Exception as e:
    print("❌ pb解析失败:", e)
    print("响应前300字(可能不是pb):", resp.content[:300]); sys.exit(1)

d = MessageToDict(msg, preserving_proto_field_name=True)
det = (d.get("detail") or [{}])[0]

print("\n" + "=" * 50)
print("结构概览")
print("=" * 50)
print("code:", d.get("code"), " message:", d.get("message"))
print("detail[0].cityName:", det.get("cityName"), " cityId:", det.get("cityId"))
print("\n--- condition(实况) 字段 ---")
print(list(det.get("condition", {}).keys()))
print("condition 示例:", det.get("condition"))

fhl = det.get("forecastHourList", {})
fhs = fhl.get("forecastHour", [])
print("\n--- forecastHour(逐时) ---")
print("条数:", len(fhs))
if fhs:
    print("forecastHour[0] 字段:", list(fhs[0].keys()))
    print("forecastHour[0] 示例:", fhs[0])

fdl = det.get("forecastDayList", {})
fds = fdl.get("forecastDay", [])
print("\n--- forecastDay(逐日) ---")
print("条数:", len(fds))
if fds:
    print("forecastDay[0] 字段:", list(fds[0].keys()))
    print("forecastDay[0] 示例:", fds[0])

print("\n--- aqi(实况) ---")
print(det.get("aqi"))

out = os.path.join(HERE, "..", "data", "比对结果", "_北京_pb样本.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print("\n✅ 完整结构已存:", out)
print("把上面【结构概览】截图/复制发我, 或直接发 _北京_pb样本.json, 我核准字段映射")
