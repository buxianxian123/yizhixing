# 墨迹天气 国内/国际 数据一致性分析工具

国内版（coapi.moji.com）与国际版（datasw1.api.moweather.com）天气数据一致性比对工具，支持**严格相等**和**阈值容忍**两种口径。

## 目录结构

```
├── utils/          ← 核心比对脚本
│   ├── compare_all.py           # 严格相等批量比对
│   ├── reformat_threshold.py    # ✅ 阈值口径比对（配置驱动，推荐使用）
│   ├── compare_config.yaml      # 阈值规则配置
│   ├── verify_align.py          # 单城市时次对齐验证
│   ├── analyze_fields.py        # 字段映射分析
│   ├── check_unit.py            # 单位验证（风速/PM2.5）
│   ├── gen_key.py / gen_key_both.py / GetKey.py
│   ├── gen_all_urls.py          # 批量生成测试 URL
│   └── ...
├── data/           ← 测试数据与参考文档
│   └── 墨迹国际化与国内版本天气数据一致性测试/
│       ├── 墨迹国际化与国内版本天气数据一致性测试.xlsx
│       ├── 天气一致性测试城市_热门城市筛选.csv
│       ├── 数据一致性测试方案.pdf
│       └── 城市URL列表.html
├── requirements.txt
└── README.md
```

## 快速开始

```bash
# 1. 装依赖
pip3 install openpyxl pyyaml

# 2. 跑阈值口径比对（推荐）
cd 国际国内数据一致性校验
python3 utils/reformat_threshold.py

# 3. 查看结果
open data/墨迹国际化与国内版本天气数据一致性测试/比对结果/一致性比对报告_阈值口径.xlsx
```

## 修改阈值规则

编辑 `utils/compare_config.yaml`，改完直接跑 `reformat_threshold.py` 即可。

## 数据源

- **国内接口**: coapi.moji.com/whapi/v2/weather
- **国际接口**: datasw1.api.moweather.com/whapi/in/weather
- **覆盖模块**: 实况(current) / 24小时逐时(hourly) / 15天(daily) / AQI
