# 墨迹天气 国内/国际 数据一致性分析工具

国内版（coapi.moji.com）与国际版（datasw1.api.moweather.com）天气数据一致性比对工具，一次运行同时输出**严格相等**和**阈值容忍**两份报告。

## 目录结构

```
├── utils/                       ← 核心脚本
│   ├── reformat_threshold.py    ✅ 一站式主脚本（拉数据 + 两份比对）
│   ├── compare_config.yaml      ✅ 阈值规则配置（改阈值改这个文件）
│   ├── compare_all.py           # 旧版：仅拉数据+严格比对（可删）
│   ├── verify_align.py          # 辅助：单城市时次对齐验证
│   ├── analyze_fields.py        # 字段映射分析
│   ├── check_unit.py            # 单位验证
│   ├── gen_all_urls.py          # 批量生成测试 URL
│   └── ...（GetKey.py 等工具）
├── data/
│   ├── 天气一致性测试城市_热门城市筛选.csv  ← 测试城市列表
│   ├── 墨迹国际化与国内版本天气数据一致性测试.xlsx
│   ├── 数据一致性测试方案.pdf
│   └── 比对结果/                         ← 每次运行生成的报告和JSON
│       ├── 一致性比对报告_严格相等_20260720_1421.xlsx
│       ├── 一致性比对报告_阈值口径_20260720_1421.xlsx
│       └── 原始JSON/
├── requirements.txt
├── SETUP.md                     ← 新机上手教程
└── README.md
```

## 快速开始

```bash
# 装依赖
pip3 install openpyxl pyyaml

# 一键运行（拉实时数据 → 生成两份报告）
python3 utils/reformat_threshold.py
```

运行结束后在 `data/比对结果/` 下会生成两个带时间戳的文件：
- `一致性比对报告_严格相等_20260720_1421.xlsx`
- `一致性比对报告_阈值口径_20260720_1421.xlsx`

## 修改阈值规则

编辑 `utils/compare_config.yaml`，改完跑 `python3 utils/reformat_threshold.py` 即可。

## 报告内容

每份 xlsx 包含 3 个 Sheet：

| Sheet | 内容 |
|-------|------|
| 数据明细 | 每城市×每模块×每字段的逐条比对结果（标颜色：绿=一致 / 红=不一致 / 灰=缺数据） |
| 总结 | 按字段+模块汇总：一致率、平均偏差、最大偏差 |
| 说明 | 本次报告的阈值规则和参数说明 |

### 24小时时效分段

24h 模块按时间拆成 3 段独立统计：

| 分段 | 小时范围 |
|------|---------|
| 短时效(1-6h) | 第 1~6 小时 |
| 中时效(7-12h) | 第 7~12 小时 |
| 长时效(13-24h) | 第 13~24 小时 |

## 数据源

- **国内接口**: coapi.moji.com/whapi/v2/weather
- **国际接口**: datasw1.api.moweather.com/whapi/in/weather
- **覆盖模块**: 实况(current) / 24小时逐时(hourly) / 15天(daily) / AQI
- **覆盖城市**: 70个国内城市（海外城市国内接口不覆盖，自动跳过）
