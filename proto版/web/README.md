# 墨迹天气 国内/国际 数据一致性比对平台

将原 `gen_html_report.py` 重构升级为直接连 `weather_data.db` 的**交互式数据一致性分析平台**。

---


## 功能模块全景


###  全局筛选器（所有分析的入口）

| 维度 | 控件 | 说明 |
|---|---|---|
| 日期范围 | 起/止日期输入 | 输入后自动勾选该日期范围内全部批次 |
| 快捷范围 | 最近1天 / 3天 / 7天 芯片 | 一键切换，选中态高亮 |
| 批次 | 多选下拉 | 331 个批次精确选择；选批次时清空日期；Ctrl/⌘+点击多选 |
| 地区三级 | 国 › 省 › 市 逐级联动 | 84 城地区映射（含海外国家） |
| 模块 | 多选 | 实况 / 24小时 / 15天 / AQI |
| 时效 | 多选 | 短时效(1-6h) / 中时效(7-12h) / 长时效(13-24h)，仅作用于24h |
| 查询 / 重置 | 按钮 | 触发刷新 / 清空恢复默认（最近24批） |

联动机制：筛选变化 → debounce 300ms → 前端请求一次 `/api/dashboard` 拿到全部聚合数据 → 重绘所有组件，保证图表与表格永远一致。

###  KPI 指标卡片（第一屏，10 张）

总体一致率（最大最醒目，<40% 标红）/ 有效字段数 / 参与城市数 / 清洗数据量 / 缺失数据量 / 最差模块 / 最差字段 / TOP偏差城市 / 天气误判数。

###  图表区（8 组，全部 ECharts + 点击钻取）

| 图 | 类型 | 要点 |
|---|---|---|
| 模块一致率 | 柱状 ↔ 雷达切换 | 4 模块一致率，≥80%绿/≥60%黄/<60%红 |
| 一致分布 | 饼图 | 一致/不一致/缺数据/清洗剔除 四段占比 |
| 一致率趋势 | 折线 | 按批次(pull_at)的总体一致率走势，反映时间稳定性 |
| TOP5 偏差城市 | 横条 | 点击柱子 → 城市详情抽屉 |
| 字段一致率 | 分组条形 | 右侧模块筛选栏 + 升降序切换 + 底部分析文案 |
| 24小时时效小多图 | 小图网格 | 每字段一图，画短/中/长三时效一致率 |
| 城市一致率 | 横条 + 滑块 | 5/10/15/20/25/全部 条数切换；右侧最差5城/最好5城速览；点击 → 抽屉 |
| 天气现象误判 | 柱状 ↔ 桑基切换 | 国内 vs 海外不一致配对：柱状看频次、桑基看流向 |

###  表格区（6 个 Tab，真 HTML table）

| Tab | 内容 |
|---|---|
| 结论汇总 | 模块×8字段(温度/湿度/风速/气压/天气现象/体感/降水概率/AQI) 一致率矩阵 |
| 模块详情 | 按模块+时效分组的字段明细：有效样本/已清洗/一致率/平均偏差/最大偏差/最大偏差城市 |
| TOP5 偏差城市 | 每字段 TOP1-5 偏差城市（天气现象显示 CN→INTL 配对） |
| 天气TOP对 | 天气现象大类不一致配对频次 |
| 规则与口径 | 评测规则/评测字段/数值阈值/天气8大类/脏数据清洗/统计口径/局限性/风险（即 MD 全部规则表） |
| 数据明细 | 逐条比对：城市/模块/字段/时次/国内值/海外值/差异/状态/时效/批次，搜索 + 分页 |

表格通用能力：排序 / 搜索 / 分页 / 固定表头 / 横向滚动 / 数字右对齐 / 一致率红黄绿着色 / 状态标签(一致/不一致/清洗/缺数据)。

###  城市详情抽屉

点击任何图表中的城市 → 右侧滑出抽屉：概览（地区/总体一致率/有效样本/最近批次/异常状态/最差字段）+ 各模块一致率 + 字段明细（国内值/海外值/差值/阈值/状态/批次）。形成完整钻取链路：**总体 → 模块 → 字段 → 城市 → 具体时次的国内/海外值**。

###  批次灵活比对（区别于旧报告的核心能力）

- **单批次**：选一个 pull_at，看该批次国内 vs 国际
- **多批次趋势**：多个批次一致率随时间走势（= 一致率趋势图）
- **A/B 组比较**：两组批次横向对比（如 A=0-3点 vs B=6-8点），输出两组总体一致率 + 差异

全部动态从 DB 查询，不写死任何具体批次。

###  生成 Markdown 报告

「生成 Markdown 报告」按钮 → 复用现有 `gen_md_report.py` → 结果卡片：生成时间 + 筛选快照 + 页面内预览 md + 下载 .md/.xlsx + 「查看原始 Markdown」入口。报告口径与旧 CLI 完全一致。

---

## 目录结构

```
web/
├── app.py              # Flask 入口：注册路由、错误处理、统一响应、启动时 load_cities
├── config.py           # 路径常量 + compare_config.yaml 规则 + 平台参数(MAX_POINTS/缓存TTL/异常阈值)
├── requirements.txt
├── repository/         # 数据查询层（只读 DB）
│   ├── connection.py   # get_conn(复用 db_helper) + check_healthy()
│   ├── meta.py         # 批次(331)/日期/城市/模块/字段/地区树
│   └── points.py       # 按筛选读比对点 Pt（与 gen_report_from_csv 逐字对齐，含 24h 时效分段）
├── services/           # 业务分析层
│   ├── filters.py      # FilterSpec 统一筛选模型 + cache_key
│   ├── compare.py      # 逐条 rt.cmp_point → valid 城市过滤
│   ├── aggregation.py  # 一致率聚合（复用 rt.aggregate_stats，口径唯一真源）
│   ├── report.py       # 生成临时xlsx → import gen_md_report.build_md → md + HTML表格解析
│   └── cache.py        # 进程内 LRU+TTL 缓存
├── templates/index.html
├── static/
│   ├── assets/echarts.min.js   # 本地离线
│   ├── assets/city_region.json # 84城地区映射（原 gen_html_report CITY_REGION + 补16城）
│   ├── css/app.css
│   └── js/{app,filters,charts,tables,drawer}.js
├── report/             # 运行时生成的 md/xlsx
└── tests/
    ├── test_parity.py  # 验收核心：平台一致率 == gen_xlsx 逐格
    └── test_smoke.py   # API 冒烟
```

依赖的现有模块（**只 import 不改**）：
- `reformat_threshold.py`（比对核心；`aggregate_stats` 是从 `gen_xlsx` 纯提取的共享函数）
- `db_helper.py`（连接/模块→表/列映射）
- `gen_md_report.py`（报告生成，未改动）

---

## API 一览

所有分析端点接受共享筛选参数：`date_start/date_end`、`pulls`(逗号分隔，优先于日期)、`cities`、`country/prov/city3`、`modules`、`periods`。

| 端点 | 说明 |
|---|---|
| `GET /health` | 探活：DB/表/批次数/最近批次 |
| `GET /api/meta` | 批次/日期/城市/模块/字段/地区元数据 |
| `GET /api/regions` | 地区三级联动树 |
| `GET /api/dashboard` | **组合端点**：一次读库+比对返回 overview/modules/fields/top5/weather_mismatch/cities/trend（前端主用） |
| `GET /api/overview` | KPI 总览 |
| `GET /api/modules` | 模块+时效一致率（=MD 总结行） |
| `GET /api/fields` | 字段粒度（=MD 总结 sheet 逐行） |
| `GET /api/trend?dim=overall\|module\|field` | 按批次趋势折线 |
| `GET /api/cities` | 城市表 |
| `GET /api/city/<name>` | 城市详情抽屉 |
| `GET /api/top5` | TOP5 偏差城市 |
| `GET /api/weather-mismatch` | 天气误判配对 |
| `GET /api/detail` | 明细分页 |
| `GET /api/compare?ab=A组\|B组` | A/B 两组比较 |
| `GET /api/report/md` | 交互式完整表格视图（不落盘） |
| `POST /api/report/generate` | 生成报告落盘 |
| `GET /report/<file>` | 下载 md/xlsx |

统一响应：`{data, meta:{filter_snapshot, pulls, points, elapsed_ms, cached}}`；错误 `{error}` + 4xx/5xx。

---



## 测试

```bash


# 口径一致性（核心验收）
/usr/local/bin/python3.13 web/tests/test_parity.py

# API 冒烟
/usr/local/bin/python3.13 web/tests/test_smoke.py
```


