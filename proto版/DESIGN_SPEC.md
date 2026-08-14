# 国际国内数据一致性平台 UI 完整视觉方案

## 一、整体设计定位

**定位：现代数据分析型 B 端后台**

核心关键词：

> **干净、克制、轻暖、专业、数据优先、长时间阅读舒适**

视觉原则：

1. 页面背景暖，内容区域白。
2. 不使用大面积高饱和颜色。
3. 不使用纯黑文字。
4. 不依赖明显边框制造层次，以**背景 + 白卡 + 阴影**为主。
5. 蓝色负责交互，不承担业务异常含义。
6. 绿/红只表达业务状态。
7. 图表颜色区分"模块"，不要让颜色暗示"好坏"。
8. 所有组件统一 8px 圆角。
9. 整体视觉偏现代 SaaS，而不是传统 ERP。

---

# 二、全局 Design Token

> **单一来源：`web/static/css/app.css` 的 `:root`**
> 图表常量：`web/static/js/charts.js` 顶部 `C_TEXT / C_TERTIARY / C_BORDER / C_SPLIT / C_PRIMARY`

## 1. 页面基础色

| Token           | 色值        | 用途    |
| --------------- | --------- | ----- |
| `--bg-page`     | `#f9f8f5` | 页面背景  |
| `--bg-card`     | `#ffffff` | 卡片、面板 |
| `--bg-subtle`   | `#f5f6f7` | 次级区域  |
| `--bg-hover`    | `#f4f7fb` | Hover |
| `--bg-selected` | `#edf4fd` | 选中状态  |

核心原则：

```text
页面 = #f9f8f5
卡片 = #ffffff
```

**不要反过来。**

---

# 三、边框与阴影

## 1. 边框

```text
--border-default: #e7e8eb
--border-hover:   #3478d8
--border-focus:   #3478d8
```

## 2. 卡片阴影

```css
--shadow-card: 0 1px 5px rgba(0, 0, 0, 0.05);
--shadow-hover: 0 3px 12px rgba(0, 0, 0, 0.07);
--shadow-modal: 0 8px 30px rgba(0, 0, 0, 0.10);
```

不要到处加重阴影。靠暖背景 + 白卡片 + 极淡阴影产生层次。

---

# 四、圆角规范

```text
--radius-sm: 6px   (Tooltip)
--radius-md: 8px   (输入框/下拉/按钮/Tab/普通卡片)
--radius-lg: 12px  (大型分析卡片/弹窗)
```

---

# 五、文字系统

```text
--text-primary:   #222529  (标题、核心指标)
--text-secondary: #4b525e  (正文、表格)
--text-tertiary:  #848b96  (说明、备注)
--text-disabled:  #b0b6bf  (禁用/Placeholder)
```

---

# 六、字体规范

```css
font-family: Inter, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
```

---

# 七、字号规范

| 场景   |      字号 |      字重 |
| ---- | ------: | ------: |
| 页面标题 |    24px |     600 |
| 模块标题 |    18px |     600 |
| 卡片标题 |    16px |     600 |
| 正文   |    14px |     400 |
| 表格   |    13px |     400 |
| 辅助说明 |    12px |     400 |
| 核心指标 | 28~32px | 600/700 |
| 小指标  | 20~24px |     600 |

---

# 八、系统主色

```text
--primary:         #3478d8
--primary-hover:   #2868c5
--primary-light:   #edf4fd
--primary-disabled: #b4c4dd
```

用于：查询/确认/主要按钮/Tab 激活/链接/交互/图表主趋势线

---

# 九、按钮规范

## 主按钮：背景 `--primary`，文字 `#fff`，Hover `--primary-hover`

## 次按钮：背景 `--neutral-light`，文字 `--text-secondary`

## 文字按钮：文字 `--primary`，背景 `transparent`

## 危险按钮：背景 `--danger`，文字 `#fff`

---

# 十、业务状态颜色

```text
--success:      #27a464   --success-light:  #edf8f2
--danger:       #e55252   --danger-light:   #fdf0f0
--warning:      #f29c38   --warning-light:  #fff6e9
--neutral:      #848b96   --neutral-light:  #f1f2f4
```

---

# 十一、图表颜色规范

## ① 模块色族（柱状图，不制造好坏暗示）

```text
--chart-1: #63a8e8  (实况)
--chart-2: #76a2df  (24小时短)
--chart-3: #879dde  (24小时中)
--chart-4: #9898d8  (24小时长)
--chart-5: #a894d2  (15天)
--chart-6: #b18fcb  (AQI)
```

## ② 环形图状态色（严格业务语义）

```text
--chart-success:  #34a873  (一致)
--chart-danger:   #e35757  (不一致)
--chart-missing:  #a1a8b3  (缺失数据)
--chart-cleaned:  #d0d4db  (清洗剔除)
```

## ③ ECharts 全局

```text
textStyle:  #4b525e
轴线:       #e7e8eb
SplitLine:  #eef0f2
AxisLabel:  #848b96
Tooltip:    白底 #fff，阴影 0 4px 12px rgba(0,0,0,.08)
```

---

# 十二、表格规范

- 表头：`--bg-subtle` + `--text-secondary` + `font-weight: 600`
- 正文：`--bg-card` + `--text-secondary`
- 分割线：`--border-default`
- Hover：`--bg-hover`
- 状态用 Tag 突出，不涂整格

---

# 十三、状态 Tag

| 状态 | 文字色 | 背景 | 圆角 |
|------|--------|------|------|
| 一致 | `--success` | `--success-light` | 6px |
| 不一致 | `--danger` | `--danger-light` | 6px |
| 警告 | `--warning` | `--warning-light` | 6px |

---

# 十四、页面布局

```text
Sidebar：220~240px
Main padding：24px
Card gap：16px
```

---

# 十五、最终颜色 Token（可直接复制）

```css
:root {
  /* Background */
  --bg-page: #f9f8f5;
  --bg-card: #ffffff;
  --bg-subtle: #f5f6f7;
  --bg-hover: #f4f7fb;
  --bg-selected: #edf4fd;

  /* Border */
  --border-default: #e7e8eb;
  --border-hover: #3478d8;
  --border-focus: #3478d8;

  /* Text */
  --text-primary: #222529;
  --text-secondary: #4b525e;
  --text-tertiary: #848b96;
  --text-disabled: #b0b6bf;

  /* Primary */
  --primary: #3478d8;
  --primary-hover: #2868c5;
  --primary-light: #edf4fd;
  --primary-disabled: #b4c4dd;

  /* Status */
  --success: #27a464;
  --success-light: #edf8f2;
  --danger: #e55252;
  --danger-light: #fdf0f0;
  --warning: #f29c38;
  --warning-light: #fff6e9;
  --neutral: #848b96;
  --neutral-light: #f1f2f4;

  /* Chart */
  --chart-1: #63a8e8;
  --chart-2: #76a2df;
  --chart-3: #879dde;
  --chart-4: #9898d8;
  --chart-5: #a894d2;
  --chart-6: #b18fcb;
  --chart-success: #34a873;
  --chart-danger: #e35757;
  --chart-missing: #a1a8b3;
  --chart-cleaned: #d0d4db;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* Shadow */
  --shadow-card: 0 1px 5px rgba(0,0,0,.05);
  --shadow-hover: 0 3px 12px rgba(0,0,0,.07);
  --shadow-modal: 0 8px 30px rgba(0,0,0,.10);
}
```

## 最重要的视觉规则

> **"暖背景、白卡片、冷边界、蓝交互、绿红表达业务状态，图表低饱和。"**
