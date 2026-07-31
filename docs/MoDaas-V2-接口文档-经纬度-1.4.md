
# MoDaas-V2-接口文档-经纬度-1.4

[TOC]



## 1、请求概述

### 1.1 、请求方式:

- HTTP协议 GET 请求方式
- HTTP协议 POST FORM表单 请求方式

### 1.2 、请求参数:

#### 1.2.1、经纬度请求参数：

- 请求示例:

  - http://coapi.moji.com/whapi/v2/weather?timestamp=0&token=5a41ea068106efae760b7b5cf87341b8&key=7f75196cbc814f559928f2d2e9b5a97d&lat=39.91488908&lon=116.40387397&language=zh-CN

- ##### 参数列表：

  | 参数      | 类型   | 必填 | 说明                                                       |
  | --------- | ------ | ---- | ---------------------------------------------------------- |
  | timestamp | long   | 是   | 当前时间戳 单位毫秒                                        |
  | token     | String | 是   | 注：请求标识 token 由墨迹天气提供                          |
  | lat       | Double | 是   | 纬度                                                       |
  | lon       | Double | 是   | 经度                                                       |
  | key       | String | 是   | MD5签名                                                    |
  | language  | String | 否   | 语言标示，例如en-US, 不传此参数默认为英文                  |
  | month     | String | 否   | 月份，例如:202001,不传此参数默认为当前月                   |
  | date      | String | 否   | 历史一天数据参数：日期，例如:20200101,不传此参数默认为今天 |

- ##### 签名算法

  - key = MD5(password+timestamp+lat+lon)
    - 注：password 由墨迹天气提供

## 2、返回结果

### 2.1 响应报文结构及提示信息

- 响应报文结构示例：

  - ~~~json
    {
        "code": 0,
        "data": {
            "current": {
           			...
          	},
        		....
        },
        "msg": "success",
        "rc": {
            "c": 0,
            "p": "success"
        }
    }
    ~~~

  - 返回值code码详解

    - | code | msg                                                          | 含义                   |
      | ---- | ------------------------------------------------------------ | ---------------------- |
      | 0    | success                                                      | 请求成功且返回天气数据 |
      | 10   | Weather Service Exception                                    | 服务器异常             |
      | 103  | Lat is illegal \| Lat in [-90, 90]或者Lon is illegal \| Lon in [-180, 180] | 参数经纬度错误         |
      | 108  | city time zone offer fail                                    | 时区请求失败           |
      | 201  | Out of time range                                            | 超出时间范围           |
      | 203  | Month is illegal                                             | 参数month格式非法      |
      | 204  | Date is illegal                                              | 参数date格式非法       |
      | 205  | History data is empty                                        | 历史数据为空           |
      | 1002 | Location Timeout                                             | 定位超时               |

## 3、响应报文数据

### 3.1、全球城市

#### 3.1.1、城市信息

##### 3.1.1.1、城市信息示例：

- ~~~json
  "city": {
        "country_code": "AD",
        "country_enname": "Andorra",
        "country_name": "Andorra",
        "enname": "",
        "id": 1000002,
        "latitude": 42.5299,
        "longtitude": 1.6401,
        "name": "",
        "parent_ennames": "Encamp",
        "parent_names": "Encamp",
        "region_enname": "Europe",
        "region_name": "Europe",
        "time_zone": 2,
        "time_zone_name": "Europe/Andorra"
  }
  ~~~

##### 3.1.1.2、城市信息要素说明：

- | 要素名称       | 要素类型 | 要素单位 | 要素说明           | 备注 |
  | -------------- | -------- | -------- | ------------------ | ---- |
  | country_code   | String   |          | 国家code           |      |
  | country_enname | String   |          | 国家英文名称       |      |
  | country_name   | String   |          | 多语言国家名称     |      |
  | enname         | String   |          | 城市英文名称       |      |
  | id             | int      |          | 城市id             |      |
  | latitude       | double   |          | 纬度               |      |
  | longtitude     | double   |          | 经度               |      |
  | name           | String   |          | 多语言城市名称     |      |
  | parent_ennames | String   |          | 上级城市英文名称   |      |
  | parent_names   | String   |          | 上级城市多语言名称 |      |
  | region_enname  | String   |          | 英文区域名称       |      |
  | region_name    | String   |          | 多语言区域名称     |      |
  | time_zone      | int      |          | 时区               |      |
  | time_zone_name | String   |          | 时区名称           |      |

#### 3.1.2、实况数据

##### 3.1.2.1、实况数据示例：

- ~~~json
  "current": {
          "day": 1,
          "dewpoint": 1,
          "get_time": "2020-11-06 10:25:17",
          "humidity": 92,
          "icon": 2,
          "mslp": 766,
          "obs_time": "2020-11-06 10:00:00",
          "precip_1h": 0,
          "real_feel": -1,
          "sky": 100,
          "temp": 2,
          "uvi": 1,
          "vis": 5000,
    			"weather": "晴",
          "weather_id": 13,
          "wind_degrees": 180,
          "wind_dir": "南",
          "wind_dir_id": 9,
          "wind_level": 2,
          "wspd": 3
      },
  ~~~

##### 3.1.2.2、实况数据要素说明：

- | 要素名称     | 要素类型 | 要素单位  | 值范围                                      | 要素说明         | 备注                   |
  | ------------ | -------- | --------- | ------------------------------------------- | ---------------- | ---------------------- |
  | day          | int      |           | 0:晚上 1:白天                               | 白天晚上表示     |                        |
  | dewpoint     | float    | 摄氏度(℃) | --                                          | 露点温度         | 暂不支持精度到小数点后 |
  | get_time     | datetime | --        | --                                          | 数据下载时间戳   | LOCAL时间              |
  | humidity     | int      | %         | 0~100                                       | 相对湿度         |                        |
  | icon         | int      | --        | --                                          | 天气图标id       |                        |
  | mslp         | int      | 百帕(hPa) | --                                          | 平均海平面气压   |                        |
  | obs_time     | datetime | --        | --                                          | 观察时间         | LOCAL时间              |
  | precip_1h    | float    | mm/h      | --                                          | 过去一小时降水量 | 保留到小数点后2位      |
  | real_feel    | float    | 摄氏度(℃) | --                                          | 体感温度         | 暂不支持精度到小数点后 |
  | sky          | int      | %         | 0~100                                       | 云覆盖率         |                        |
  | temp         | float    | 摄氏度(℃) | --                                          | 温度             | 2位小数                |
  | uvi          | int      | --        | --                                          | 紫外线指数       |                        |
  | vis          | int      | m         | --                                          | 能见度           |                        |
  | weather      | string   | --        | --                                          | 天气现象         | 默认中文简写           |
  | weather_id   | int      | --        | [天气现象表](https://quip.com/GXRLAfkirHza) | 天气现象id       |                        |
  | wind_degrees | int      | 度        | 0~360                                       | 风向角度         |                        |
  | wind_dir     | string   | --        | --                                          | 风向             | 默认中文简写           |
  | wind_dir_id  | int      | --        | [风向描述表](https://quip.com/AbxNAUG9XXXi) | 风向id           |                        |
  | wind_level   | int      | --        | [风级描述表](https://quip.com/lcMwAN6t1ZMf) | 风力等级         |                        |
  | wspd         | float    | m/s       | --                                          | 风速             | 保留到小数点后2位      |

#### 3.1.3、  预报15天数据

##### 3.1.3.1、预报15天数据示例：

- ~~~json
  "daily": [
          {
              "get_time": "2020-11-06 11:50:22",
              "humidity": 89,
              "icon_day": 13,
              "icon_night": 31,
              "moon_down": "2020-11-06 12:52:00",
              "moon_phase": "WaningGibbous",
              "moon_rise": "2020-11-06 22:00:00",
              "mslp": 767,
              "pop": 36,
              "predict_date": "2020-11-06",
              "qpf": 1.4,
              "snow": 0.6,
              "sun_down": "2020-11-06 17:40:00",
              "sun_rise": "2020-11-06 07:34:00",
              "temp_high": 5,
              "temp_low": 0,
              "update_time": "2020-11-06 08:45:00",
              "uvi": 1,
              "weather_day": "大部分多云，有时有小雪",
              "weather_id_day": 24,
              "weather_id_night": 12,
              "weather_night": "部分多云",
              "wind_degrees_day": 180,
              "wind_degrees_night": 180,
              "wind_dir_day": "南",
              "wind_dir_id_day": 9,
              "wind_dir_id_night": 9,
              "wind_dir_night": "南",
              "wind_level_day": "3",
              "wind_level_night": "3",
              "wspd_day": 4,
              "wspd_night": 4.4
          },
         ...
    		 ...
      ],
  ~~~

##### 3.1.3.1、预报15天数据要素说明：

- | 要素名称           | 要素类型 | 要素单位  | 值范围         | 要素说明           | 备注              |
  | ------------------ | -------- | --------- | -------------- | ------------------ | ----------------- |
  | get_time           | datetime | --        | --             | 下载数据源时间     | LOCAL时间         |
  | humidity           | int      | %         | 0~100          | 相对湿度           |                   |
  | icon_day           | int      | --        | --             | 白天天气图标id     |                   |
  | icon_night         | int      | --        | --             | 晚上天气图标id     |                   |
  | moon_rise          | datetime | --        | --             | 月升               | LOCAL时间         |
  | moon_down          | datetime | --        | --             | 月落               | LOCAL时间         |
  | moon_phase         | string   | --        | --             | 月相               | 英文              |
  | mslp               | int      | 帕(hPa)   | --             | 气压               |                   |
  | pop                | int      | %         | 0~100          | 降水概率           |                   |
  | predict_date       | datetime | --        | --             | 预报时间           | LOCAL时间         |
  | qpf                | float    | mm        |                | 未来一天预测降水量 | 保留到小数点后2位 |
  | snow               | float    | cm        |                | 未来一天预测降雪量 | 保留到小数点后2位 |
  | sun_down           | datetime | --        | --             | 日落               | LOCAL时间         |
  | sun_rise           | datetime | --        | --             | 日出               | LOCAL时间         |
  | temp_high          | int      | 摄氏度(℃) | --             | 高温               |                   |
  | temp_low           | int      | 摄氏度(℃) | --             | 低温               |                   |
  | update_time        | datetime | --        | --             | 更新时间           | 系统运行地时间    |
  | uvi                | int      | --        | --             | 紫外线指数         | 目前缺            |
  | weather_day        | string   | --        | --             | 白天天气现象       | 默认中文简写      |
  | weather_id_day     | int      | --        | 参见天气现象表 | 白天天气现象id     |                   |
  | weather_id_night   | int      | --        | 参见天气现象表 | 晚上天气现象id     |                   |
  | weather_night      | string   | --        | --             | 晚上天气现象       | 默认中文简写      |
  | wind_degrees_day   | int      | 度        | 0~360          | 风向角度           |                   |
  | wind_degrees_night | int      | 度        | 0~360          | 风向角度           |                   |
  | wind_dir_day       | string   | --        | --             | 白天风向           | 默认中文简写      |
  | wind_dir_id_day    | int      | --        | 详见风向描述表 | 白天风向id         |                   |
  | wind_dir_id_night  | int      | --        | 详见风向描述表 | 晚上风向id         |                   |
  | wind_dir_night     | string   | --        | --             | 晚上风向           | 默认中文简写      |
  | wind_level_day     | string   | --        | 参见风力描述表 | 白天风力等级       |                   |
  | wind_level_night   | string   | --        | 参见风力描述表 | 晚上风力等级       |                   |
  | wspd_day           | float    | m/s       | --             | 白天风速           | 保留到小数点后2位 |
  | wspd_night         | float    | m/s       | --             | 晚上风速           | 保留到小数点后2位 |

#### 3.1.4、 预报24小时数据

##### 3.1.4.1、预报24小时数据示例：

- ~~~json
  "hourly": [
          {
              "day": 1,
              "dewpoint": 2,
              "get_time": "2020-11-06 11:30:22",
              "humidity": 90,
              "icon": 2,
              "mslp": 767,
              "pop": 40,
              "predict_date": "2020-11-06",
              "predict_hour": 11,
              "predict_time": "2020-11-06 11:00:00",
              "qpf": 0,
              "real_feel": 0,
              "sky": 100,
              "snow": 0,
              "temp": 3,
              "update_time": "2020-11-06 14:27:00",
              "uvi": 1,
              "vis": 6000,
              "weather": "晴",
              "weather_id": 13,
              "wind_degrees": 180,
              "wind_dir": "南",
              "wind_dir_id": 9,
              "wind_level": 2,
              "wspd": 3.2,
              "sol_ir": 211
          },
          ...
    			...
      ],
  ~~~

##### 3.1.4.2、预报24小时要素说明：

- | 要素名称     | 要素类型 | 要素单位  | 值范围         | 要素说明             | 备注                     |
  | ------------ | -------- | --------- | -------------- | -------------------- | ------------------------ |
  | day          | int      | --        | 0:晚上 1:白天  | 白天晚上表示         |                          |
  | dewpoint     | float    | 摄氏度(℃) | --             | 露点温度             | 暂不支持精度到小数点后   |
  | get_time     | datetime |           |                | 下载数据源时间       | LOCAL时间                |
  | humidity     | int      | %         | 0~100          | 相对湿度             |                          |
  | icon         | int      | --        | --             | 天气图标id           |                          |
  | mslp         | int      | 帕(hPa)百 | --             | 平均海平面气压       |                          |
  | pop          | int      | %         | 0~100          | 降水概率             |                          |
  | predict_date | date     | --        | --             | 预报天               |                          |
  | predict_hour | int      | --        | 0~23           | 预报小时             | 用于统计某个时间段的情况 |
  | predict_time | datetime | --        | --             | 预报时间             | LOCAL时间                |
  | qpf          | float    | mm/h      |                | 未来一小时预测降水量 | 保留到小数点后2位        |
  | real_feel    | float    | 摄氏度(℃) | --             | 体感温度             | 暂不支持精度到小数点后   |
  | sky          | int      | %         | 0~100          | 云覆盖率             |                          |
  | snow         | float    | cm/h      |                | 未来一小时预测降雪量 | 保留到小数点后2位        |
  | temp         | float    | 摄氏度(℃) | --             | 温度                 | 暂不支持精度到小数点后   |
  | upate_time   | datetime | --        | --             | 更新时间             | LOCAL时间                |
  | uvi          | int      | --        | --             | 紫外线指数           |                          |
  | vis          | int      | m         | --             | 能见度               |                          |
  | weather      | string   | --        | --             | 天气现象             | 默认中文简写             |
  | weather_id   | int      | --        | 参见天气现象表 | 天气现象id           |                          |
  | wind_degrees | int      | 度        | 0~360          | 风向角度             |                          |
  | wind_dir     | string   | --        | --             | 风向                 | 默认中文简写             |
  | wind_dir_id  | int      | --        | 详见风向描述表 | 风向id               |                          |
  | wind_level   | int      | --        | 参见风力描述表 | 风力等级             |                          |
  | wspd         | float    | m/s       | --             | 风速                 | 保留到小数点后2位        |
  | sol_ir       | float    | W/m²      |                | 太阳辐射             |                          |

### 3.2、国内+国外热门城市

#### 3.2.1、城市信息

##### 3.2.1.1、城市信息示例：

- ~~~json
  "city": {
        "country_code": "CN",
        "country_enname": "China",
        "country_name": "中国",
        "enname": "Beijing",
        "id": 2,
        "latitude": 39.904138,
        "longtitude": 116.407112,
        "name": "北京市",
        "parent_ennames": "Beijing",
        "parent_names": "北京市",
        "region_enname": "Asia",
        "region_name": "亚洲",
        "time_zone": 8,
        "time_zone_name": "Asia/Shanghai"
  }
  ~~~

##### 3.2.1.2、城市信息要素说明：

- | 要素名称       | 要素类型 | 要素单位 | 要素说明           | 备注 |
  | -------------- | -------- | -------- | ------------------ | ---- |
  | country_code   | String   |          | 国家code           |      |
  | country_enname | String   |          | 国家英文名称       |      |
  | country_name   | String   |          | 多语言国家名称     |      |
  | enname         | String   |          | 城市英文名称       |      |
  | id             | int      |          | 城市id             |      |
  | latitude       | double   |          | 纬度               |      |
  | longtitude     | double   |          | 经度               |      |
  | name           | String   |          | 多语言城市名称     |      |
  | parent_ennames | String   |          | 上级城市英文名称   |      |
  | parent_names   | String   |          | 上级城市多语言名称 |      |
  | region_enname  | String   |          | 英文区域名称       |      |
  | region_name    | String   |          | 多语言区域名称     |      |
  | time_zone      | int      |          | 时区               |      |
  | time_zone_name | String   |          | 时区名称           |      |

#### 3.2.1、实况数据

##### 3.2.1.1、实况数据示例：

- ~~~json
   "current": {
          "cloud_cover": 81,
          "comfort": 72,
          "dewpoint": 5,
          "get_time": "2023-06-12 17:20:03",
          "humidity": 25,
          "icon": 1,
          "mslp": 998,
          "obs_time": "2023-06-12 17:35:08",
          "precip_1h": 0,
          "pressure_desc": "低于标准大气压",
          "pressure_tendency": "稳定",
          "real_feel": 26,
          "sun_down": "2023-06-12 19:43:00",
          "sun_rise": "2023-06-12 04:45:00",
          "temp": 29,
          "tips": "略微偏热，注意衣物变化。",
          "uvi": 5,
          "vis": 30000,
          "weather": "多云",
          "weather_id": 8,
          "wind_degrees": 0,
          "wind_dir": "北风",
          "wind_dir_id": 1,
          "wind_gust_level": 5,
          "wind_level": 4,
          "wspd": 5.89,
          "rain_snow_type":"1",
          "rainfall_intensity":"0.0",
          "rainfall_intensity_1h":"0.0"
   
      },
   ~~~

##### 3.2.1.2、实况数据要素说明：

- | 要素名称              | 要素类型 | 要素单位  | 值范围                                      | 要素说明         | 备注                                                         |
  | --------------------- | -------- | --------- | ------------------------------------------- | ---------------- | ------------------------------------------------------------ |
  | comfort               | int      | --        | --                                          | 舒适度           |                                                              |
  | dewpoint              | int      | 摄氏度(℃) | --                                          | 露点温度         | 暂不支持精度到小数点后                                       |
  | get_time              | datetime | --        | --                                          | 数据下载时间     | LOCAL时间                                                    |
  | humidity              | int      | %         | 0~100                                       | 相对湿度         |                                                              |
  | icon                  | int      | --        | --                                          | 天气图标id       |                                                              |
  | mslp                  | int      | 百帕(hPa) | --                                          | 平均海平面气压   |                                                              |
  | obs_time              | datetime | --        | --                                          | 观察时间         | LOCAL时间                                                    |
  | precip_1h             | float    | mm/h      | --                                          | 过去一小时降水量 | 保留到小数点后2位                                            |
  | real_feel             | int      | 摄氏度(℃) | --                                          | 体感温度         | 暂不支持精度到小数点后                                       |
  | sun_rise              | datetime | --        | --                                          | 日出             | LOCAL时间                                                    |
  | sun_down              | datetime | --        | --                                          | 日落             | LOCAL时间                                                    |
  | temp                  | float    | 摄氏度(℃) | --                                          | 温度             | 2位小数                                                      |
  | tips                  | string   | --        | --                                          | 生活提示         |                                                              |
  | uvi                   | int      | --        | --                                          | 紫外线指数       |                                                              |
  | vis                   | int      | m         | --                                          | 能见度           |                                                              |
  | weather               | string   | --        | --                                          | 天气现象         | 默认en-US                                                    |
  | weather_id            | int      | --        | [天气现象表](https://quip.com/GXRLAfkirHza) | 天气现象id       |                                                              |
  | wind_degrees          | int      | 度        | 0~360                                       | 风向角度         |                                                              |
  | wind_dir              | string   | --        | --                                          | 风向             | 默认en-US                                                    |
  | wind_dir_id           | int      | --        | [风向描述表](https://quip.com/AbxNAUG9XXXi) | 风向id           |                                                              |
  | wind_level            | int      | --        | [风级描述表](https://quip.com/lcMwAN6t1ZMf) | 风力等级         |                                                              |
  | wspd                  | float    | m/s       | --                                          | 风速             | 保留到小数点后2位                                            |
  | pressure_desc         | string   | --        |                                             | 气压描述         |                                                              |
  | pressure_tendency     | string   | --        |                                             | 气压变化         |                                                              |
  | wind_gust_level       | int      | --        |                                             | 阵风风力等级     |                                                              |
  | cloud_cover           | int      | %         | 0~100                                       | 云量             |                                                              |
  | rainfall_intensity    | string   |           | 0-1                                         | 实况雨强         |                                                              |
  | rain_snow_type        | string   |           |                                             | 降水量类型       | 1代表雨，2代表雪                                             |
  | rainfall_intensity_1h | string   | mm/h      |                                             | 小时级雨强*      | rainfall_intensity_1h小时级雨强是指以实况雨强映射到小时级雨强，表示以当前实况雨强对应一小时降水量大小 |

#### 3.2.3、  预报7天数据

##### 3.2.3.1、预报7天数据示例：

- ~~~json
   "daily": [
          {
              "cloud_cover_day": 7,
              "cloud_cover_night": 81,
              "get_time": "2023-06-08 23:01:03",
              "humidity": 10,
              "icon_day": 1,
              "icon_night": 31,
              "moon_down": "2023-06-08 08:39:00",
              "moon_phase": "WaningGibbous",
              "moon_rise": "2023-06-08 23:52:00",
              "mslp": 1001,
              "pop": 20,
              "predict_date": "2023-06-08",
              "qpf": 0,
              "sun_down": "2023-06-08 19:41:00",
              "sun_rise": "2023-06-08 04:46:00",
              "temp_high": 34,
              "temp_low": 19,
              "update_time": "2023-06-08 23:08:00",
              "uvi": 11,
              "weather_day": "多云",
              "weather_id_day": 8,
              "weather_id_night": 8,
              "weather_night": "多云",
              "wind_degrees_day": 0,
              "wind_degrees_night": 315,
              "wind_dir_day": "北风",
              "wind_dir_id_day": 1,
              "wind_dir_id_night": 14,
              "wind_dir_night": "西北风",
              "wind_gust_level_day": "5",
              "wind_gust_level_night": "1",
              "wind_level_day": "3-4",
              "wind_level_night": "1",
              "wspd_day": 5.6,
              "wspd_night": 0.9,
              "sol_ir_day": 251,
              "sol_ir_night": 7949,
              "tips":"今天比昨天低7度,未来2天以晴为主"
          },
         ...
    		 ...
      ],
   ~~~

##### 3.2.3.1、预报7天数据要素说明：

- | 要素名称              | 要素类型 | 要素单位  | 值范围         | 要素说明           | 备注              | 7天、15天、40天的前15天 | 40天的后25天 |
  | --------------------- | -------- | --------- | -------------- | ------------------ | ----------------- | ----------------------- | ------------ |
  | get_time              | datetime | --        | --             | 下载数据源时间戳   | LOCAL时间         | 支持                    | 不支持       |
  | humidity              | int      | %         | 0~100          | 相对湿度           |                   | 支持                    | 支持         |
  | icon_day              | int      | --        | --             | 白天天气图标id     |                   | 支持                    | 支持         |
  | icon_night            | int      | --        | --             | 晚上天气图标id     |                   | 支持                    | 支持         |
  | moon_down             | datetime | --        | --             | 月落               |                   | 支持                    | 不支持       |
  | moon_phase            | string   | --        | --             | 月相               | LOCAL时间         | 支持                    | 不支持       |
  | moon_rise             | datetime | --        | --             | 月升               |                   | 支持                    | 不支持       |
  | mslp                  | int      | 帕(hPa)   | --             | 气压               | LOCAL时间         | 支持                    | 支持         |
  | pop                   | int      | %         | 0~100          | 降水概率           |                   | 支持                    | 不支持       |
  | predict_date          | datetime | --        | --             | 预报时间           | LOCAL时间         | 支持                    | 支持         |
  | qpf                   | float    | mm        |                | 未来一天预测降水量 |                   | 支持                    | 不支持       |
  | sun_down              | datetime | --        | --             | 日落               | 保留到小数点后2位 | 支持                    | 支持         |
  | sun_rise              | datetime | --        | --             | 日出               | LOCAL时间         | 支持                    | 支持         |
  | temp_high             | int      | 摄氏度(℃) | --             | 高温               | LOCAL时间         | 支持                    | 支持         |
  | temp_low              | int      | 摄氏度(℃) | --             | 低温               |                   | 支持                    | 支持         |
  | update_time           | datetime | --        | --             | 更新时间           | LOCAL时间         | 支持                    | 支持         |
  | uvi                   | int      | --        | --             | 紫外线指数         | 系统运行地时间    | 支持                    | 不支持       |
  | weather_day           | string   | --        | --             | 白天天气现象       |                   | 支持                    | 支持         |
  | weather_id_day        | int      | --        | 参见天气现象表 | 白天天气现象id     | 默认en_US         | 支持                    | 不支持       |
  | weather_id_night      | int      | --        | 参见天气现象表 | 晚上天气现象id     |                   | 支持                    | 不支持       |
  | weather_night         | string   | --        | --             | 晚上天气现象       |                   | 支持                    | 支持         |
  | wind_degrees_day      | int      | 度        | 0~360          | 风向角度           |                   | 支持                    | 支持         |
  | wind_degrees_night    | int      | 度        | 0~360          | 风向角度           |                   | 支持                    | 支持         |
  | wind_dir_day          | string   | --        | --             | 白天风向           |                   | 支持                    | 支持         |
  | wind_dir_id_day       | int      | --        | 详见风向描述表 | 白天风向id         | 默认en_US         | 支持                    | 支持         |
  | wind_dir_id_night     | int      | --        | 详见风向描述表 | 晚上风向id         |                   | 支持                    | 支持         |
  | wind_dir_night        | string   | --        | --             | 晚上风向           |                   | 支持                    | 支持         |
  | wind_level_day        | string   | --        | 参见风力描述表 | 白天风力等级       | 默认en_US         | 支持                    | 支持         |
  | wind_level_night      | string   | --        | 参见风力描述表 | 晚上风力等级       |                   | 支持                    | 支持         |
  | wspd_day              | float    | m/s       | --             | 白天风速           | 保留到小数点后2位 | 支持                    | 支持         |
  | wspd_night            | float    | m/s       | --             | 晚上风速           | 保留到小数点后2位 | 支持                    | 支持         |
  | wind_gust_level_day   | string   | --        | 参见风力描述表 | 白天阵风风力等级   |                   | 支持                    | 支持         |
  | cloud_cover_day       | int      | --        | --             | 白天云量           |                   | 支持                    | 支持         |
  | wind_gust_level_night | string   | --        | 参见风力描述表 | 晚上阵风风力等级   |                   | 支持                    | 支持         |
  | cloud_cover_night     | int      | --        | --             | 晚上云量           |                   | 支持                    | 支持         |
  | sol_ir_day            | float    | W/m²      | --             | 白天太阳辐射       |                   | 支持                    | 不支持       |
  | sol_ir_night          | float    | W/m²      | --             | 晚上太阳辐射       |                   | 支持                    | 不支持       |
  | tips                  | string   | --        | --             | 天气说明提示语     |                   | 支持                    | 支持         |

#### 3.2.4、 预报15天数据

==参考：3.2.3、  预报7天数据==

#### 3.2.5、 预报40天数据

==参考：3.2.3、  预报7天数据==

#### 3.2.6、 预报24小时数据

##### 3.2.6.1、预报24小时数据示例：

- ~~~json
  "hourly": [
          {
              "day": "1",
              "dewpoint": "-11",
              "humidity": "15",
              "icon": "0",
              "mslp": "1020",
              "pop": "0",
              "predict_date": "2020-10-28",
              "predict_hour": "13",
              "predict_time": "2020-10-28 13:00:00",
              "qpf": "0.0",
              "real_feel": "18",
              "sky": "0",
              "snow": "0",
              "temp": "18",
              "update_time": "2020-10-28 13:32:09",
              "uvi": "4",
              "weather": "晴",
              "weather_id": "5",
              "wind_degrees": "315",
              "wind_dir": "西北偏西",
              "wind_dir_id": "14",
              "wind_level": "1",
              "wspd": "5.40",
              "sol_ir": 211,
              "vis": 6000
          },
          ...
    			...
      ],
  ~~~

##### 3.2.6.2、预报24小时要素说明：

- | 要素名称     | 要素类型 | 要素单位  | 值范围         | 要素说明             | 备注                     |
  | ------------ | -------- | --------- | -------------- | -------------------- | ------------------------ |
  | day          | int      | --        | 0:晚上 1:白天  | 白天晚上表示         |                          |
  | dewpoint     | int      | 摄氏度(℃) | --             | 露点温度             | 暂不支持精度到小数点后   |
  | humidity     | int      | %         | 0~100          | 相对湿度             |                          |
  | icon         | int      | --        | --             | 天气图标id           |                          |
  | mslp         | int      | 帕(hPa)百 | --             | 平均海平面气压       |                          |
  | pop          | int      | %         | 0~100          | 降水概率             |                          |
  | predict_date | date     | --        | --             | 预报天               |                          |
  | predict_hour | int      | --        | 0~23           | 预报小时             | 用于统计某个时间段的情况 |
  | predict_time | datetime | --        | --             | 预报时间             | LOCAL时间                |
  | qpf          | float    | mm/h      |                | 未来一小时预测降水量 | 保留到小数点后2位        |
  | real_feel    | int      | 摄氏度(℃) | --             | 体感温度             | 暂不支持精度到小数点后   |
  | sky          | int      | %         | 0~100          | 云覆盖率             |                          |
  | snow         | float    | cm/h      |                | 未来一小时预测降雪量 | 保留到小数点后2位        |
  | temp         | int      | 摄氏度(℃) | --             | 温度                 | 暂不支持精度到小数点后   |
  | upate_time   | datetime | --        | --             | 更新时间             | LOCAL时间                |
  | uvi          | int      | --        | --             | 紫外线指数           |                          |
  | weather      | string   | --        | --             | 天气现象             | 默认中文简写             |
  | weather_id   | int      | --        | 参见天气现象表 | 天气现象id           |                          |
  | wind_degrees | int      | 度        | 0~360          | 风向角度             |                          |
  | wind_dir     | string   | --        | --             | 风向                 | 默认中文简写             |
  | wind_dir_id  | int      | --        | 详见风向描述表 | 风向id               |                          |
  | wind_level   | int      | --        | 参见风力描述表 | 风力等级             |                          |
  | wspd         | float    | m/s       | --             | 风速                 | 保留到小数点后2位        |
  | sol_ir       | float    | W/m²      |                | 太阳辐射             |                          |
  | vis          | int      | m         | --             | 能见度               |                          |

#### 3.2.7、 预报36小时数据

==参考：3.2.6、  预报24小时数据==

#### 3.2.8、 预警数据

##### 3.2.8.1、预警数据示例：

- ~~~json
  "alerts": [
        {
          "alert_level": "蓝色",
  				"alert_name": "大风",
          "content": "受冷空气影响，预计5月1日08时至20时，本市大部分地区有4、5级偏北风，阵风7、8级，请注意防范。",
          "deal_time": "2021-04-30 17:59:58",
          "info_id": 89,
          "land_defense_id": "10,9,22",
          "port_defense_id": "9,23,28",
          "pub_time": "2021-04-30 16:00:00",
          "title": "北京市气象台发布大风蓝色预警"
        },
        ...
  ],
  ~~~

##### 3.2.8.2、预警数据要素说明：

- | 要素名称        | 要素类型 | 要素单位 | 值范围 | 要素说明           | 备注      |
  | --------------- | -------- | -------- | ------ | ------------------ | --------- |
  | alert_level     | string   | --       | --     | 预警等级           |           |
  | alert_name      | string   | --       | --     | 预警类型           |           |
  | content         | string   | --       | --     | 预警内容           |           |
  | deal_time       | datetime | --       | --     | 预警处理时间       | LOCAL时间 |
  | info_id         | int      | --       | --     | 预警类型等级id     |           |
  | land_defense_id | string   | --       | --     | 陆地防御指南id列表 |           |
  | port_defense_id | string   | --       | --     | 港口防御指南id列表 |           |
  | pub_time        | datetime | --       | --     | 发布时间           | LOCAL时间 |
  | title           | string   | --       | --     | 预警标题           |           |

#### 3.2.9、 生活指数数据

##### 3.2.9.1、生活指数示例：

- ~~~json
  "index": [
        {
            "index_desc": "风力较大，洗车后会蒙上灰尘。",
            "index_level": "7",
            "index_level_desc": "较不适宜",
            "index_type": "洗车指数",
            "index_type_id": "17",
            "predict_date": "2020-10-28",
            "update_time": "2020-10-28 19:35:04"
        },
        ...
  ],
  ~~~

##### 3.2.9.2、生活指数要素说明：

- | 要素名称         | 要素类型 | 要素单位 | 值范围 | 要素说明     | 备注      |
  | ---------------- | -------- | -------- | ------ | ------------ | --------- |
  | index_desc       | string   | --       | --     | 文案描述     |           |
  | index_level      | int      | --       | --     | 指数等级     |           |
  | index_level_desc | string   | --       | --     | 指数等级描述 |           |
  | index_type       | string   | --       | --     | 指数类型     |           |
  | index_type_id    | int      | --       | --     | 指数类型id   |           |
  | predict_date     | date     | --       | --     | 预报时间     |           |
  | update_time      | datetime | --       | --     | 指数更新时间 | LOCAL时间 |

#### 3.2.10、 AQI实况数据

##### 3.2.10.1、AQI实况数据示例：

- ~~~json
  "aqi": {
        "aqi": "51",
        "co": "0.2",
        "co_aqi": "2",
        "no2": "13.0",
        "no2_aqi": "7",
        "o3": "54.0",
        "o3_aqi": "17",
        "pm10": "51.0",
        "pm10_aqi": "51",
        "pm25": "6.0",
        "pm25_aqi": "9",
        "primary_pollutant": "PM10",
        "pub_time": "2020-10-27 03:00:00",
        "so2": "2.0",
        "so2_aqi": "1",
    		"rank":"1/125"
  },
  ~~~

##### 3.2.10.2、AQI实况数据要素说明：

- | 要素名称          | 要素类型 | 要素单位 | 值范围 | 要素说明                 | 备注             |
  | ----------------- | -------- | -------- | ------ | ------------------------ | ---------------- |
  | aqi               | int      | --       | --     | 空气质量指数值           |                  |
  | co                | float    | mg/m3    | -      | 一氧化碳浓度             | 保留小数点后一位 |
  | co_aqi            | float    | --       | --     | 一氧化碳空气质量分指数值 | 保留小数点后一位 |
  | no2               | float    | μg/m3    | --     | 二氧化氮浓度             | 保留小数点后一位 |
  | no2_aqi           | float    | --       | --     | 二氧化氮空气质量分指数值 | 保留小数点后一位 |
  | o3                | float    | μg/m3    | --     | 臭氧浓度                 | 保留小数点后一位 |
  | o3_aqi            | float    | --       | --     | 臭氧空气质量分指数值     | 保留小数点后一位 |
  | pm10              | float    | μg/m3    | --     | PM10浓度                 | 保留小数点后一位 |
  | pm10_aqi          | float    | --       | --     | PM10空气质量分指数值     | 保留小数点后一位 |
  | pm25              | float    | μg/m3    | --     | PM25浓度                 | 保留小数点后一位 |
  | pm25_aqi          | float    | --       | --     | PM25空气质量分指数值     | 保留小数点后一位 |
  | primary_pollutant | string   | --       | --     | 主污染物                 |                  |
  | pub_time          | datetime | --       | --     | 发布时间戳               | LOCAL时间        |
  | so2               | float    | μg/m3    | --     | 二氧化硫浓度             | 保留小数点后一位 |
  | so2_aqi           | float    | --       | --     | 二氧化硫空气质量分指数值 | 保留小数点后一位 |
  | rank              | string   |          | --     | 排名                     |                  |

#### 3.2.11、 AQI预报3天数据

##### 3.2.11.1、AQI预报3天数据示例：

- ~~~json
  "aqi_forecast": [
              {
                  "aqi": "46",
                  "predict_time": "2020-10-27",
                  "pub_time": "2020-10-27 00:00:00"
              },
              ...
          ],
  ~~~

##### 3.2.11.2、AQI预报3天数据要素说明：

- | 要素名称     | 要素类型 | 要素单位 | 值范围 | 要素说明       | 备注      |
  | ------------ | -------- | -------- | ------ | -------------- | --------- |
  | aqi          | int      | --       | --     | 空气质量指数值 |           |
  | predict_time | date     | --       | --     | 预报时间       | LOCAL时间 |
  | pub_time     | datetime | --       | --     | 发布时间       | LOCAL时间 |

#### 3.2.12、 AQI预报7天数据

==参考：3.2.11、  AQI预报3天数据==

#### 3.2.13、 AQI预报48小时数据

##### 3.2.13.1、AQI预报48小时示例：

- ~~~json
  "aqi_forecast_hourly": [
              {
                  "aqi": "58",
                  "predict_time": "2020-10-31 13:00:00",
                  "pub_time": "2020-10-31 13:00:00"
              },
           ...
          ],
  ~~~

##### 3.2.13.2、AQI预报48小时要素说明：

- | 要素名称     | 要素类型 | 要素单位 | 值范围 | 要素说明       | 备注      |
  | ------------ | -------- | -------- | ------ | -------------- | --------- |
  | aqi          | int      | --       | --     | 空气质量指数值 |           |
  | predict_time | datetime | --       | --     | 预报时间       | LOCAL时间 |
  | pub_time     | datetime | --       | --     | 发布时间       | LOCAL时间 |

#### 3.2.14、 AQI历史24小时数据

##### 3.2.14.1、AQI史24小时示例：

- ~~~json
  "aqi_history": [
              {
                  "aqi": "64",
                  "pub_time": "2020-10-28 18:00:00"
              },
           ...
          ],
  ~~~

##### 3.2.14.2、AQI历史24小时要素说明：

- | 要素名称 | 要素类型 | 要素单位 | 值范围 | 要素说明       | 备注      |
  | -------- | -------- | -------- | ------ | -------------- | --------- |
  | aqi      | int      | --       | --     | 空气质量指数值 |           |
  | pub_time | datetime | --       | --     | 发布时间       | LOCAL时间 |

#### 3.2.15、 AQI排名数据

##### 3.2.15.1、AQI排名示例：

- ~~~json
  "aqi_rank": [
            {
              "aqi": "15",
              "city_id": "2887",
              "city_name": "普洱市",
              "province_name": "云南省",
              "pub_time": "2020-10-28 19:53:38",
              "rank": "1"
            },
           ...
          ],
  ~~~

##### 3.2.15.2、AQI排名数据要素说明：

- | 要素名称      | 要素类型 | 要素单位 | 值范围 | 要素说明       | 备注      |
  | ------------- | -------- | -------- | ------ | -------------- | --------- |
  | aqi           | int      | --       | --     | 空气质量指数值 |           |
  | city_id       | int      |          |        | 城市id         |           |
  | city_name     | string   |          |        | 城市名称       |           |
  | province_name | string   |          |        | 省份名称       |           |
  | pub_time      | datetime | --       | --     | 发布时间       | LOCAL时间 |
  | rank          | int      |          |        | 排名           |           |

#### 3.2.16、 AQI监测站

##### 3.2.16.1、AQI监测站示例：

- ~~~json
  "aqi_point": [
  {
      "aqi": 25,
      "co": 0.3,
      "co_aqi": 3,
      "lat": 40.177134,
      "lon": 116.66438,
      "no2": 10,
      "no2_aqi": 5,
      "o3": 78,
      "o3_aqi": 25,
      "pm10": 17,
      "pm10_aqi": 17,
      "pm25": 11,
      "pm25_aqi": 16,
      "point_name": "顺义新城",
      "primary_pollutant": "--",
      "pub_time": "2021-03-01 15:00:00",
      "so2": 2,
      "so2_aqi": 1
  },
  ~~~

##### 3.2.16.2、AQI监测站要素说明：

- | 要素名称          | 要素类型 | 要素单位 | 值范围 | 要素说明                 | 备注             |
  | ----------------- | -------- | -------- | ------ | ------------------------ | ---------------- |
  | aqi               | int      | --       | --     | 空气质量指数值           |                  |
  | co                | float    | μg/cm3   | -      | 一氧化碳浓度             | 保留小数点后一位 |
  | co_aqi            | float    | --       | --     | 一氧化碳空气质量分指数值 | 保留小数点后一位 |
  | no2               | float    | μg/cm3   | --     | 二氧化氮浓度             | 保留小数点后一位 |
  | no2_aqi           | float    | --       | --     | 二氧化氮空气质量分指数值 | 保留小数点后一位 |
  | o3                | float    | μg/cm3   | --     | 臭氧浓度                 | 保留小数点后一位 |
  | o3_aqi            | float    | --       | --     | 臭氧空气质量分指数值     | 保留小数点后一位 |
  | pm10              | float    | μg/cm3   | --     | PM10浓度                 | 保留小数点后一位 |
  | pm10_aqi          | float    | --       | --     | PM10空气质量分指数值     | 保留小数点后一位 |
  | pm25              | float    | μg/cm3   | --     | PM25浓度                 | 保留小数点后一位 |
  | pm25_aqi          | float    | --       | --     | PM25空气质量分指数值     | 保留小数点后一位 |
  | primary_pollutant | string   | --       | --     | 主污染物                 |                  |
  | pub_time          | datetime | --       | --     | 发布时间戳               | LOCAL时间        |
  | so2               | float    | μg/cm3   | --     | 二氧化硫浓度             | 保留小数点后一位 |
  | so2_aqi           | float    | --       | --     | 二氧化硫空气质量分指数值 | 保留小数点后一位 |
  | lat               | double   | --       | --     | 纬度                     |                  |
  | lon               | double   | --       | --     | 经度                     |                  |
  | point_name        | string   | --       | --     | 站点名称                 |                  |

#### 3.2.17、 限行数据

##### 3.2.17.1、限行示例：

- ~~~json
  "limit": [
        {
            "date": "2020-03-17",
            "prompt": "W"
        },
        ...
  ],
  ~~~

##### 3.2.17.2、限行要素说明：

- | 要素名称 | 要素类型 | 要素单位 | 值范围 | 要素说明 | 备注      |
  | -------- | -------- | -------- | ------ | -------- | --------- |
  | date     | date     |          |        | 限行日期 | LOCAL时间 |
  | prompt   | string   | --       | --     | 限行提示 |           |

#### 3.2.18、 天气提醒数据

##### 3.2.18.1、天气提醒示例：

- ~~~json
  "push_info": "疫情期间，注意防护：北京市，今夜到明天，小雨，7~11℃，东南风转西北风3级，空气 优。"
  ~~~

##### 3.2.18.2、天气提醒要素说明：

- | 要素名称  | 要素类型 | 要素单位 | 值范围 | 要素说明     | 备注 |
  | --------- | -------- | -------- | ------ | ------------ | ---- |
  | push_info | string   |          |        | 天气提醒内容 |      |

#### 3.2.19、 短时实况数据

==注：短时数据只支持经纬度请求方式；near_rain_dir、near_rain_distance和near_rain_type当附近没有降雨时将不显示==

##### 3.2.19.1、短时实况示例：

- ~~~json
  "nowcast": {
          "long_desc": "未来一小时不会下雨，您可以放心出门~",
          "near_rain_dir": 0,
          "near_rain_distance": 0,
          "near_rain_type": 0,
          "rain": 0,
          "rain_intensity": 0.0,
          "rain_last_time": 0,
          "short_desc": "未来一小时不会下雨",
          "timestamp": 1604054893000,
          "weather_id": 0
  }
  ~~~

##### 3.2.19.2、短时实况要素说明：

- | 要素名称           | 要素类型 | 要素单位 | 值范围                                                 | 要素说明       | 备注                  | 实况 | 1小时、2小时 |
  | ------------------ | -------- | -------- | ------------------------------------------------------ | -------------- | --------------------- | ---- | ------------ |
  | long_desc          | string   | --       | --                                                     | 详细文档描述   |                       | 支持 | 支持         |
  | near_rain_dir      | int      | --       | 1～8 1:东2:东南3:南4:西南 5:西  6:西北7:北8:东北       | 最近降水带方向 |                       | 支持 | 支持         |
  | near_rain_distance | int      | km       | --                                                     | 最近降水带距离 | 精度保留到小数点后2位 | 支持 | 支持         |
  | near_rain_type     | int      | --       | 6:雨夹雪 7:小雨 8:中雨 9:大雨 14:小雪  15:中雪 16:大雪 | 最近降水带类型 |                       | 支持 | 支持         |
  | rain               | int      | --       | 0:没有 1:有                                            | 是否降水       |                       | 支持 | 支持         |
  | rain_intensity     | float    | --       | --                                                     | 短时雨强       |                       | 支持 | 支持         |
  | rain_last_time     | int      | min      |                                                        | 降水持续时间   |                       | 支持 | 支持         |
  | short_desc         | string   | --       | --                                                     | 简短预报文案   |                       | 支持 | 支持         |
  | timestamp          | long int | --       |                                                        | 更新时间       |                       | 支持 | 支持         |
  | weather_id         | int      | --       | --                                                     | 天气天气现象ID |                       | 支持 | 支持         |

#### 3.2.20、 短时一小时数据

==注：短时数据只支持经纬度请求方式；near_rain_dir、near_rain_distance和near_rain_type当附近没有降雨时将不显示==

##### 3.2.20.1、短时一小时示例：

- ~~~json
  "nowcast": {
          "long_desc": "未来一小时不会下雨，您可以放心出门~",
          "percent": [
                    {
                    "dbz": 0,
                    "icon": -1,
                    "rain_intensity": 0.0
                    },
  									...
          ],
          "near_rain_dir": 0,
          "near_rain_distance": 0,
          "near_rain_type": 0,
          "rain": 0,
          "rain_intensity": 0.0,
          "rain_last_time": 0,
          "short_desc": "未来一小时不会下雨",
          "timestamp": 1604054893000,
          "weather_id": 0
  }
  ~~~

##### 3.2.20.2、短时实况要素说明：

- | 要素名称               | 要素类型 | 要素单位 | 值范围                                                 | 要素说明         | 备注                  | 实况   | 1小时、2小时 |
  | ---------------------- | -------- | -------- | ------------------------------------------------------ | ---------------- | --------------------- | ------ | ------------ |
  | long_desc              | string   | --       | --                                                     | 详细文档描述     |                       | 支持   | 支持         |
  | near_rain_dir          | int      | --       | 1～8 1:东2:东南3:南4:西南 5:西  6:西北7:北8:东北       | 最近降水带方向   |                       | 支持   | 支持         |
  | near_rain_distance     | int      | km       | --                                                     | 最近降水带距离   | 精度保留到小数点后2位 | 支持   | 支持         |
  | near_rain_type         | int      | --       | 6:雨夹雪 7:小雨 8:中雨 9:大雨 14:小雪  15:中雪 16:大雪 | 最近降水带类型   |                       | 支持   | 支持         |
  | percent.dbz            | int      | --       | --                                                     | 雷达反射强度     |                       | 不支持 | 支持         |
  | percent.icon           | int      | --       | --                                                     | 天气图标id       |                       | 不支持 | 支持         |
  | percent.rain_intensity | float    | --       | --                                                     | 短时雨强         |                       | 不支持 | 支持         |
  | rain                   | int      | --       | 0:没有 1:有                                            | 是否降水         |                       | 支持   | 支持         |
  | rain_intensity         | float    | --       | --                                                     | 短时雨强第一分钟 |                       | 支持   | 支持         |
  | rain_last_time         | int      | min      |                                                        | 降水持续时间     |                       | 支持   | 支持         |
  | short_desc             | string   | --       | --                                                     | 简短预报文案     |                       | 支持   | 支持         |
  | timestamp              | long int | --       |                                                        | 更新时间         |                       | 支持   | 支持         |
  | weather_id             | int      | --       | --                                                     | 天气天气现象ID   |                       | 支持   | 支持         |

#### 3.2.21、 短时两小时数据

==参考：3.2.19、  短时一小时数据==

#### 3.2.22、 潮汐数据

##### 3.2.22.1、潮汐示例：

- ~~~json
  "ports": [
              {
                  "lat": "36.22",
                  "lon": "120.52",
                  "port_id": "45",
                  "port_name": "女岛港",
                  "sea_level": "2.2",
                  "tides": {
                      "2020-10-19": [
                          {
                              "level": "409.0",
                              "predict_date": "2020-10-19 04:50:00"
                          },
  				…
                      ],
  				…
                  }
              },
  			…
          ]
  ~~~

##### 3.2.22.2、潮汐要素说明：

- | 要素名称           | 要素类型            | 要素单位 | 值范围 | 要素说明 | 备注 |
  | ------------------ | ------------------- | -------- | ------ | -------- | ---- |
  | port_id            | string              |          |        | 港口Id   |      |
  | port_name          | string              |          |        | 港口名称 |      |
  | lat                | string              |          |        | 纬度     |      |
  | lon                | string              |          |        | 经度     |      |
  | sea_level          | string              | m        |        | 海平面   |      |
  | tides              | array               |          |        | 潮汐数据 |      |
  | tides.level        | string              | m        |        | 潮高     |      |
  | tides.predict_date | yyyy-MM-dd HH:mm:ss |          |        | 预报时间 |      |

