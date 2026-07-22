# 数据分析应用 — 开发计划

> **技术栈**：前端 JavaScript | 后端 Python (FastAPI) | 数据库 MongoDB | 数据源 Excel  
> **运行环境**：本地电脑，浏览器访问  
> **UI 基准**：Figma 设计稿 (以 Figma 为最终标准)  
> **导航结构**：地图 (Map) | 整体分析 (Whole Analysis) | 活动分析 (Activities)

---

## 阶段〇：项目初始化与基础架构搭建

### 0.1 项目目录结构规划

```
project-root/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 配置（DB连接等）
│   │   ├── models/             # MongoDB 数据模型 (ODM)
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── routers/            # API 路由
│   │   ├── services/           # 业务逻辑
│   │   └── utils/              # 工具函数
│   ├── requirements.txt
│   └── .env
├── frontend/                   # JavaScript 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   │   ├── Map/            # 地图页
│   │   │   ├── Analysis/       # 整体分析（客户/交易/AUC/排名）
│   │   │   └── Activities/     # 活动分析
│   │   ├── components/         # 可复用组件
│   │   ├── services/           # API 调用封装
│   │   ├── stores/             # 状态管理
│   │   ├── utils/              # 工具函数
│   │   └── assets/             # 静态资源
│   ├── public/
│   └── package.json
├── data/                       # Excel 样例数据 / 数据字典
├── docs/                       # 文档
└── docker-compose.yml          # MongoDB 等服务编排 (可选)
```

### 0.2 技术选型确认

| 层级       | 技术                     | 说明                           |
| ---------- | ------------------------ | ------------------------------ |
| 前端框架   | React (Vite 构建)        | 组件化开发，生态丰富           |
| UI 组件库  | Ant Design / Material UI | 根据 Figma 设计风格选择        |
| 图表库     | ECharts / Recharts       | 折线图、饼图、柱状图等         |
| 地图库     | Leaflet + heatmap.js     | 热力图可视化                   |
| 后端框架   | FastAPI                  | 高性能异步 Python Web 框架     |
| ODM        | Motor (异步) + Beanie    | MongoDB 异步操作               |
| Excel 解析 | openpyxl / pandas        | Excel 导入解析                 |
| 数据库     | MongoDB (本地)           | 文档型数据库，适配灵活数据结构 |

### 0.3 开发环境搭建

- [x] 安装 MongoDB（本地实例或 Docker），创建数据库 `growth_analytics`
- [x] 初始化 Python 虚拟环境，安装后端依赖
- [x] 初始化前端项目 (Vite + React)
- [ ] 配置 ESLint、Prettier（前端）、Black、Ruff（后端）
- [x] 搭建前后端联调代理（Vite proxy → FastAPI）
- [x] 创建 `.env` 配置文件（MongoDB URI 等）

---

## 阶段一：数据基础建设

> **对应需求**：Excel 数据导入至 MongoDB，为所有页面提供数据支撑

### 1.1 数据模型设计（MongoDB Collections）

**集合清单**：

```
customers            # 客户基础信息（含标签、分级）
transactions         # 交易记录（按月）
activities           # 活动信息
activity_tracking    # 活动获客追踪数据（归因记录）
customer_assets      # 客户资产快照（按月）
rankings             # 排名历史记录
```

- [x] 设计每个集合的 Schema（字段、类型、索引）
- [x] 编写 Beanie Document 模型类

### 1.2 客户数据模型

- [x] `customers` 集合字段：
  ```
  {
    client_id,
    name,
    uid,
    age, gender,
    location,                  # 地理位置（奥克兰/惠灵顿/基督城/其他）
    nationality,
    client_type,               # HNW / S-Class / Frequent Trader / Inactive / New
    tags: [],                  # 标签数组：[HNW], [S-Class], [Inactive], [Frequent Trader], [New]
    monthly_net_assets_usd,    # 月末净资产（美金）
    monthly_trade_count,       # 每月交易次数
    trade_category,            # 交易分类：stock / option / futures / fund
    asset_allocation: {        # 资产配置
      stocks_pct, options_pct, futures_pct, funds_pct
    },
    monthly_snapshots: [{      # 按月快照
      month, net_assets, trade_count,
      deposit_amount, withdrawal_amount,
      trading_volume, last_login_date
    }],
    signal: {                  # 当前信号/异常
      type,                    # 信号类型
      description,             # 信号描述
      recommended_action       # 推荐操作
    }
  }
  ```

### 1.3 活动与追踪数据模型

- [x] `activities` 集合字段：

  ```
  {
    activity_id,
    name,                      # 活动名称
    description,               # 活动描述
    date_start, date_end,      # 日期范围
    location,                  # 活动地点
    status,                    # 状态（进行中/已完成/计划中）
    metrics: {
      total_visitors,          # 总访客数
      new_signups,             # 新注册人数
      conversion_rate          # 转化率
    },
    daily_trend: [{            # 每日执行趋势
      date, cumulative_visitors, new_signups
    }]
  }
  ```

- [x] `activity_tracking` 集合字段：
  ```
  {
    tracking_id,
    activity_id,
    sequence,                  # 序号
    channel_source,            # 渠道来源
    invite_code,               # 邀请码
    channel,                   # 渠道
    client_type,               # 客户类型
    client_name,               # 客户姓名
    client_uid,                # 客户 UID
    registration_date,         # 注册时间
    registration_amount,       # 注册金额
    deposit_status,            # 入金状态
    attribution_result         # 归因结果
  }
  ```

### 1.4 Excel 数据导入（后端）

- [x] `POST /api/import/upload` — 上传 Excel 文件
- [x] 后端解析逻辑：
  - 使用 pandas 读取 Excel
  - 自动识别数据类型（客户数据 / 交易数据 / 活动数据 / 资产数据）
  - 数据校验（必填字段、格式验证、去重检查）
  - 批量写入 MongoDB（使用 `bulk_write + upsert`，支持增量更新）
- [x] 导入日志记录（导入时间、文件名、记录数、错误数）

---

## 阶段二：地图页面 (Map)

> **Figma 页面**：活动热力图 — 新西兰

### 2.1 地图与热力图

- [x] 新西兰地图底图基础（Leaflet + OSM 底图 + 点位渲染）
- [ ] GeoJSON 行政边界叠加
- [ ] 热力图图层（heatmap.js）
- [ ] 热力程度图例：
  - 高热 (90+) — 深色
  - 较热 (70-90) — 中色
  - 中等 (40-70) — 浅色

### 2.2 筛选条件面板

- [x] 筛选条件基础版本（当前为地图上方 Filter Bar）：
  - 地区（奥克兰、惠灵顿、基督城、汉密尔顿等主要城市 & 其他）
  - 性别（男/女）
  - 年龄段（18-24 / 25-34 / 35-44 / 45+，支持范围选择）
- [x] 筛选条件联动：选中后地图点位实时更新（基于本地 JSON）
- [ ] 当前筛选条件标签展示（如 "奥克兰 / 女 / 18-30"）

### 2.3 活动 ROI 分析面板

- [ ] 右侧数据面板：
  - 活动总数指标卡（如 128.4k）
  - 转化率指标卡（如 12.4%）
  - 活动 ROI 排名 — 按地区排行榜
  - 平均投入 vs 回报柱状图（按地域）

### 2.4 年龄分布图

- [ ] 饼图 / 环形图展示年龄分布：
  - 18-24 岁（24%）
  - 25-34 岁（42%）
  - 35-44 岁（18%）
  - 45 岁以上（16%）
- [ ] 支持地区/全部切换

### 2.5 API

- [x] `GET /api/map/heatmap-data` — 热力图数据（支持筛选参数：地区、性别、年龄段，当前为 mock 返回）
- [x] `GET /api/map/roi-ranking` — 活动 ROI 地区排名（当前为 mock 返回）
- [x] `GET /api/map/age-distribution` — 年龄分布数据（支持地区筛选，当前为 mock 返回）

---

## 阶段三：整体分析 — 客户 (Whole Analysis > Clients)

> **Figma 页面**：NZ 客户 — 客户优先级 & 信号

### 3.1 客户概览指标卡

- [x] 顶部三大指标卡：
  - 交易量 (Trading Volume)：如 NZ$12.5M，显示环比变化（+15.2%）
  - 资产规模 (AUC)：如 NZ$380M，显示环比变化（+0.5%）
  - NZ Top 100 排名：如 Top 12，显示排名变化（+8）

### 3.2 客户类型筛选

- [x] 筛选条件栏：
  - 全部客户
  - 高净值客户 (HNW)
  - S 级客户 (S-Class)
  - 需回访
  - 客户异常
- [x] 市场筛选（全部市场）

### 3.3 客户信号与异常卡片 (Signals & Anomalies)

- [x] 信号卡片列表，每张卡片包含：
  - 客户姓名 + UID
  - 标签（如 [HNW]、[S-Class]、[Inactive]、[Frequent Trader]、[New]）
  - 信号描述（如 "持续入金增长，月均入金 NZ$75k+"）
  - 推荐操作
  - 操作按钮：「推送给 Sales」/「查看详情」

- [x] 信号类型：
  - **HNW 持续入金**：高净值客户资产持续增长，交易量上升
  - **沉睡客户**：近 2+ 个月无登录，曾有活跃交易记录
  - **交易量激增**：交易量为平均值的 3x/5x 以上（Volume Spike）
  - **新客户大额入金**：新注册客户短期内多次大额入金
  - **资产持续下滑**：客户资产持续下降，建议联系了解情况

### 3.4 API

- [x] `GET /api/clients/overview` — 客户概览指标（交易量、AUC、排名）
- [x] `GET /api/clients/signals` — 客户信号列表（支持按类型筛选、分页）
- [x] `POST /api/clients/{uid}/push-to-sales` — 推送客户给 Sales
- [x] `GET /api/clients/{uid}/detail` — 获取客户详细信息

---

## 阶段四：整体分析 — 交易 (Whole Analysis > Trading)

> **Figma 页面**：交易量趋势分析

### 4.1 交易指标概览

- [x] 指标卡片：
  - 总交易量（含本币与 USD 等值，如 ¥8.42M ≈ $1.16M USD）
  - 环比变化（如 +12.5% vs 上期）
  - 上期交易量（如 ¥7.48M，环比 +4.2%）
  - 上上期交易量（如 ¥8.08M）
  - 平均客户交易额 AOV（如 ¥12,450，环比 -1.8%）

### 4.2 筛选条件

- [x] 市场筛选：全部市场 (All Markets)
- [x] 按交易类型筛选
- [x] 时间范围切换：7D / 30D / 1Y

### 4.3 交易趋势图 (Trading Trends)

- [x] 双折线对比图：
  - 当前周期 (Current) — 实线
  - 上一周期 (Previous) — 虚线
- [x] X 轴为日期，Y 轴为交易量
- [x] 鼠标悬停显示具体数值（如 05-21 May: ¥421,890）

### 4.4 交易类型分布 (Category)

- [x] 交易类型占比图（柱状图或饼图）
- [x] 按市场 / 按交易类型分类展示

### 4.5 头部贡献者表格 (Top Contributors)

- [x] 表格列：排名、市场、姓名、客户 UID、交易量 (VOLUME)、占比 (%)、环比变动 (%)
- [x] 支持排序
- [x] 分页展示

### 4.6 API

- [x] `GET /api/trading/overview` — 交易指标概览（支持时间范围、市场筛选）
- [x] `GET /api/trading/trends` — 交易趋势数据（当前 vs 上期，按日聚合）
- [x] `GET /api/trading/categories` — 交易类型分布
- [x] `GET /api/trading/top-contributors` — 头部贡献者列表（支持分页、排序）

---

## 阶段五：整体分析 — AUC (Whole Analysis > AUC)

> **Figma 页面**：资产规模 (AUC) 分析 & 分布分析

### 5.1 AUC 指标概览

- [x] 指标卡片：
  - 总资产规模 (Total AUC)：如 $245.8M，YoY +12%
  - 平均每客户资产：如 $42,350，Health: Good
  - 资产留存率：如 98.2%，+0.5%
  - 净流入：如 +$12.4M，+18%

### 5.2 AUC 趋势图

- [x] 12 个月趋势图（双数据系列）：
  - Total Assets（面积图/折线图）
  - Net Inflow（柱状图/折线图）
- [x] X 轴为月份（Jan - Dec），Y 轴为金额
- [x] 视图切换：全部显示 / 仅资产 / 仅流入

### 5.3 资产分级分布 (Asset Tier Distribution)

- [x] 分级展示（柱状图或分段条形图）：
  - <$10k (Mass)：如 12,450 clients
  - $10k-$100k (Core)：如 5,230 clients
  - $100k-$1M (Affluent)：如 890 clients
  - > $1M (HNW)：如 124 clients
- [x] 按客户类型排行列表

### 5.4 资产配置图 (Asset Allocation)

- [x] 饼图展示资产配置比例（动态）：
  - 基于客户快照资产配置字段按月计算（非固定示例比例）
  - 类别：股票 (Stocks) / 期权 (Options) / 期货 (Futures) / 基金 (Funds)
- [x] 多币种支持显示：USD, CNY, EUR, NZD, HKD, AUD
- [x] 注：Base currency normalized to USD equivalent

### 5.5 切换视图

- [x] 两个 Tab 页：「AUC 分析」与「AUC 分布分析」

### 5.6 API

- [x] `GET /api/auc/overview` — AUC 指标概览
- [x] `GET /api/auc/trends` — AUC 趋势数据（按月聚合，12 个月）
- [x] `GET /api/auc/tier-distribution` — 资产分级分布
- [x] `GET /api/auc/asset-allocation` — 资产配置比例（动态、多币种）
- [x] `GET /api/auc/top-clients` — 按客户类型资产排行

---

## 阶段六：整体分析 — 排名 (Whole Analysis > Rankings)

> **Figma 页面**：Top 200 排名追踪

### 6.1 排名统计概览

- [x] 月份选择器（选择查看的月份）
- [x] 汇总指标卡片：
  - 本月变动数量
  - New Entry 数量（新进入 Top 200 的客户数）
  - Dropped Out 数量（跌出 Top 200 的客户数）
  - 大幅跃升 (>20 位) 数量

### 6.2 排名变动追踪卡片

- [x] **New Entry** 卡片区：
  - 客户姓名、UID、新排名、原排名（如 No. 182 from No. 245）
- [x] **Dropped Out** 卡片区：
  - 客户姓名、UID、新排名、原排名
- [x] **大幅跃升 (>20 位)** 卡片区：
  - 客户姓名、UID、新排名、原排名（如 No. 12 from No. 36）

### 6.3 排名详情表格

- [x] 两个排名维度切换：
  - Top 500 Leaderboard
  - 核心贡献用户排名
- [x] 表格列：排名、UID、邀请码/渠道、S级/M级、客户类型、排名变动、AUC 占比、交易量
- [x] 分页展示（如 "Showing 1 to 10 of 500 entries"）
- [x] 支持排序与筛选

### 6.4 API

- [x] `GET /api/rankings/overview` — 排名概览统计（New Entry、Dropped Out、大幅跃升数量）
- [x] `GET /api/rankings/movements` — 排名变动卡片数据（新进/跌出/大幅跃升列表）
- [x] `GET /api/rankings/top500-trading` — Top 500 交易排名表（支持分页、排序、月份筛选、国籍筛选）
- [x] `GET /api/trading/top-contributors` — 核心贡献用户排名表（支持分页、排序）

---

## 阶段七：活动分析 (Activities)

> **Figma 页面**：活动分析 — 活动列表 + 活动详情 + 获客追踪

### 7.1 活动列表侧边栏

- [x] 左侧活动时间线列表（静态样例）：
  - 按时间倒序排列
  - 每个条目显示：活动名称、日期、地点、状态标签
  - 示例：「奥克兰博览会 2024」2024-01-10 奥克兰-中心城区
  - 示例：「国际留学展」2023-12-15 全国线上
  - 示例：「奥克兰大学合作推广」2023-11-22 Auckland University
- [x] 点击活动条目切换右侧详情（静态联动）

### 7.2 活动详情面板

- [x] 活动信息头（静态样例）：
  - 活动名称
  - 活动描述
  - 日期范围（如 2024-01-10 至 01-12）
  - 地点（如 奥克兰 Aotea Square）
- [x] 指标卡片（静态样例）：
  - 活动总访客数（如 12,480，+8.4%）
  - 新注册人数（如 856，+12.1%）
  - 转化率（如 6.86%，+1.5%）

### 7.3 活动执行趋势图 (Execution Trend)

- [x] 双 Y 轴折线图（静态样例）：
  - 左 Y 轴：累计访客量 (L)
  - 右 Y 轴：新注册人数 (R)
  - X 轴：活动天数（Day 1, Day 2 ... Day N）
- [x] 鼠标悬停联动显示

### 7.4 活动获客追踪表

- [ ] 完整字段版表格列（当前已实现简化版静态列）：
  - 序号
  - 渠道来源
  - 邀请码
  - 渠道
  - 客户类型
  - 姓名 / UID
  - 注册时间
  - 注册金额
  - 入金状态
  - 归因结果
- [ ] 支持分页、筛选、排序（当前为静态表格展示）
- [ ] 数据导出 Excel（按钮已预留，导出逻辑待接入）

### 7.5 API

- [x] `GET /api/activities` — 活动列表（支持分页，按时间倒序）
- [x] `GET /api/activities/{id}` — 活动详情（含指标和趋势数据）
- [x] `GET /api/activities/{id}/trend` — 活动执行趋势数据（按天）
- [x] `GET /api/activities/{id}/tracking` — 活动获客追踪表（支持分页、筛选、排序）

---

## 阶段八：前端整合与 UI 还原

> **以 Figma 设计稿为最终标准**

### 8.1 设计稿分析与组件拆分

- [ ] 从 Figma 导出设计稿截图 / 标注
- [ ] 拆分页面组件层级
- [ ] 提取设计 Token（颜色、字体、间距、圆角等）
- [ ] 建立前端 Design System（CSS 变量 / Theme）

### 8.2 页面开发清单（基于 Figma 设计稿）

| 页面            | 路由                 | 说明                                                  |
| --------------- | -------------------- | ----------------------------------------------------- |
| 地图            | `/map`               | 活动热力图（新西兰） + 筛选面板 + ROI 分析 + 年龄分布 |
| 整体分析 > 客户 | `/analysis`          | 客户指标概览 + 信号与异常卡片 + 客户筛选              |
| 整体分析 > 交易 | `/analysis/trading`  | 交易量指标 + 趋势图 + 类型分布 + 头部贡献者           |
| 整体分析 > AUC  | `/analysis/auc`      | 资产规模指标 + 趋势图 + 分级分布 + 资产配置           |
| 整体分析 > 排名 | `/analysis/rankings` | 排名概览 + 变动追踪卡片 + Top 200 详情表              |
| 活动分析        | `/activities`        | 活动时间线侧边栏 + 详情面板 + 趋势图 + 获客追踪表     |

### 8.3 导航结构

- [ ] 顶部导航栏：Tiger Brokers Logo + 三个主 Tab
  - **地图 (Map)** → `/map`
  - **整体分析 (Whole Analysis)** → `/analysis`（默认子页）
    - 左侧边栏子导航：客户 / 交易 / AUC / 排名
  - **活动分析 (Activities)** → `/activities`
- [ ] 右上角：当前用户（admin）

---

## 阶段九：测试与优化

### 9.1 后端测试

- [x] API 单元测试（pytest，阶段三/四/七已覆盖）
- [x] 信号生成逻辑验证
- [ ] 排名变动计算验证
- [x] 数据聚合准确性测试

### 9.2 前端测试

- [ ] 核心组件单元测试
- [ ] 页面交互流程测试
- [ ] 图表渲染验证（折线图、饼图、热力图等）

### 9.3 集成与性能

- [x] 后端联调测试（MongoDB + Excel 导入链路：health / upload / 落库计数）
- [ ] 前后端联调测试（Clients/Trading/AUC/Rankings 已联调；Map/Activities 前端联调待完成）
- [ ] MongoDB 索引优化（针对高频查询）
- [ ] 大数据量下的分页/虚拟滚动
- [ ] 图表渲染性能优化

---

## 阶段十：部署与交付

### 10.1 本地部署

- [ ] 编写启动脚本（一键启动 MongoDB + 后端 + 前端）
- [x] 编写环境配置文档
- [ ] 打包前端静态资源，由 FastAPI 静态托管

### 10.2 文档

- [ ] 用户操作手册
- [ ] 数据字典（Excel 模板 + 字段说明）
- [x] 部署/运维手册（MongoDB + Excel 导入联调指南）

---

## 开发顺序总览

```
阶段〇 项目初始化          ████░░░░░░░░░░░░░░░░  基础架构
阶段一 数据基础建设        ██████░░░░░░░░░░░░░░  数据基础
阶段二 地图页面            ████████░░░░░░░░░░░░  热力图 + 筛选 + ROI
阶段三 整体分析-客户       ██████████░░░░░░░░░░  信号 & 异常
阶段四 整体分析-交易       ████████████░░░░░░░░  交易趋势分析
阶段五 整体分析-AUC        ██████████████░░░░░░  资产规模分析
阶段六 整体分析-排名       ██████████████░░░░░░  Top 200 追踪
阶段七 活动分析            ████████████████░░░░  活动详情 + 获客追踪
阶段八 UI 还原整合         ██████████████████░░  前端精装
阶段九 测试优化            ████████████████████  质量保障
阶段十 部署交付            ████████████████████  上线
```

> **注意**：阶段八（Figma UI 还原）实际上会贯穿阶段二到阶段七，每完成一个功能模块即参照 Figma 进行 UI 适配。此处单独列出是为了预留整体 UI 校准和组件复用优化的时间。

---

## 关键依赖与风险

| 风险项               | 影响           | 缓解措施                           |
| -------------------- | -------------- | ---------------------------------- |
| Excel 数据格式不统一 | 导入失败       | 提供标准模板 + 健壮的校验逻辑      |
| 地理位置分类         | 地图不准确     | 与业务确认城市分类映射规则         |
| Figma 设计变更       | 返工           | 设计冻结后开发，变更走 CR 流程     |
| 大数据量性能         | 页面卡顿       | MongoDB 索引 + 分页 + 前端虚拟列表 |
| 多币种换算           | AUC 数据不一致 | 统一以 USD 为基准，标注换算规则    |
