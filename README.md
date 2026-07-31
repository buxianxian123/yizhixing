# 墨迹天气 国内/国际 数据一致性分析工具

国内版与国际版天气数据一致性比对，一次运行同时输出**严格相等**和**阈值口径**两份报告。

重构后按版本分文件夹：`proto版/`（当前线上）+ `json版/`（coapi 旧接口留存）。

## 目录结构

```
├── proto版/                     ← 当前线上版（国内 proto detail 接口）
│   ├── raw_pull.py              ✅ 定时拉取原始数据(proto+国际) -> data/原始拉取/ (只拉不比)
│   ├── reformat_threshold.py    ✅ 单次比对(拉一次出报告)
│   ├── scheduled_compare.py     ✅ 定时均值(读留底攒N轮出均值报告, 不拉接口)
│   ├── gen_report_from_raw.py   ✅ 手动取最近N份出均值报告(如 .py 45)
│   ├── fetch_cn_pb.py           国内 proto detail 拉取+normalize
│   ├── weather_pb2.py / weather.proto
│   ├── gen_html_report.py / gen_md_report.py / echarts.min.js   报告生成
│   ├── gen_all_urls.py          国际URL构造
│   └── compare_config.yaml / compare_config_strict.yaml
├── json版/                      ← coapi 旧接口留存版（国内 coapi.moji.com）
│   ├── raw_pull_cnjson.py       ✅ 定时拉取(coapi+国际) -> data/原始拉取_json/
│   ├── reformat_threshold_cnjson.py   ✅ 单次比对
│   ├── scheduled_compare_cnjson.py   ✅ 定时均值(读留底攒N轮)
│   ├── gen_report_from_raw_cnjson.py ✅ 手动取最近N份出均值报告
│   ├── gen_html_report.py / gen_md_report.py / echarts.min.js / gen_all_urls.py
│   └── compare_config_cnjson.yaml   (7级降水 + 天气≥4分, 对齐老报告口径)
├── _废弃/                       ← 旧coapi辅助脚本 + 旧留底(57轮), 留存不删
├── docs/                        ← pdf/md/接口文档
├── data/
│   ├── 天气一致性测试城市_热门城市筛选.csv   测试城市列表
│   ├── 原始拉取/                proto 留底(raw_pull拉, scheduled/gen_report读)
│   ├── 原始拉取_json/           coapi 留底(raw_pull_cnjson拉)
│   └── 比对结果/                报告输出
└── requirements.txt
```

## proto版 运行（当前线上）

```bash
pip3 install openpyxl pyyaml protobuf requests

# 1. 定时拉取原始数据（常驻, 和比对解耦, 只拉不比）
nohup python3 proto版/raw_pull.py > raw_pull.log 2>&1 &

# 2. 单次比对（拉一次接口出报告）
python3 proto版/reformat_threshold.py

# 3. 定时均值比对（常驻, 读 raw_pull 留底攒N轮出均值, 不拉接口）
nohup python3 proto版/scheduled_compare.py > scheduled.log 2>&1 &

# 4. 手动取最近N份出均值报告（不用等定时任务攒满, 用raw_pull已拉数据）
python3 proto版/gen_report_from_raw.py 45      # 取最近45份
python3 proto版/gen_report_from_raw.py          # 全部已有
```

> 流程：raw_pull 持续拉数据到 `data/原始拉取/`（唯一拉取源）→ scheduled_compare 读留底攒满48轮(2天)自动出均值报告；或手动 `gen_report_from_raw.py N` 取最近N份立即出报告。

## json版 运行（coapi 留存）

```bash
python3 json版/reformat_threshold_cnjson.py          # 单次比对
python3 json版/gen_report_from_raw_cnjson.py 45       # 手动取最近N份
nohup python3 json版/raw_pull_cnjson.py > raw_pull_json.log 2>&1 &    # 定时拉取
```

⚠️ coapi 接口可能已下线，拉得到才能跑全套；拉不到则 json版仅作留存参考。

## 两版区别

| | proto版（线上） | json版（留存） |
|---|---|---|
| 国内接口 | weather.api.moji.com/data/detail (POST/protobuf) | coapi.moji.com/whapi/v2/weather (GET/MD5) |
| 国际接口 | datasw1 moweather (GET/json, 含nowcast) | datasw1 moweather (GET/json) |
| 降水等级 | 7级 | 7级 |
| 天气现象判定 | score≥5 | score≥4（对齐老报告） |
| **能比** | 逐时/逐日降水概率(pop) | 实况降水量 + 逐日体感早晚(coapi有字段) |
| **比不了** | 逐日体感早晚 + 实况降水量（detail无字段） | 降水概率 |

> 同一套 config 字段映射 + weather_mapping 44+29种语义映射 + 阈值口径，仅国内数据源不同。proto版因 detail 新接口缺 `precip_1h` 和 `realFeel Day/Night`，比不了实况降水量和逐日体感早晚；json版 coapi 旧接口有这俩字段能比，但没降水概率。

## 修改阈值规则

- proto版：编辑 `proto版/compare_config.yaml`
- json版：编辑 `json版/compare_config_cnjson.yaml`

改完重跑对应脚本即可。配置含：阈值(温度2/体感2/湿度10/风速2/气压10/AQI20)、降水等级、天气现象语义映射(44+29种)、定时调度(avg_count/interval_seconds)。

## 报告内容

每份 xlsx 含：数据明细（逐条比对, 绿=一致/红=不一致/灰=缺数据）+ 总结（按字段模块汇总一致率/偏差）+ 说明。
另生成 HTML（ECharts交互图+TOP5表）和 MD 报告。24h按时效分短(1-6h)/中(7-12h)/长(13-24h)三段统计。

## 数据源与覆盖

- 模块：实况 / 24小时逐时 / 15天预报 / AQI
- 城市：84城（CSV配置，国内为主）
- 风速：国际 km/h ÷3.6 换算 m/s 后比对
