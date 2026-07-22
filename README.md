# TBNZ Data Dashboard — Tiger Brokers 新西兰数据分析看板

Tiger Brokers (老虎证券) 新西兰分部的内部数据分析工具，帮助增长团队直观地了解客户、交易、资产和活动数据。

## 这个项目是做什么的？

简单来说，它是一个**数据看板网站**，团队成员打开浏览器就能看到：

- **地图热力图** — 新西兰各地区的用户活跃度分布
- **客户分析** — 哪些客户有异常信号（大额出金、沉睡、交易激增等），需要重点跟进
- **交易分析** — 本月交易额走势、品类分布、核心贡献用户排名
- **资产分析 (AUC)** — 托管资产规模、增长趋势、资产配置情况
- **排名追踪** — Top 200 客户排名变化（谁新进了、谁掉出了、谁大幅跃升了）
- **活动分析** — 线下活动的获客效果、转化漏斗、客户归因追踪

## 技术栈

| 部分      | 技术              | 用途                             |
| --------- | ----------------- | -------------------------------- |
| 前端      | React + Vite      | 页面展示和交互                   |
| UI 组件库 | Ant Design 6      | 按钮、表格、卡片等 UI 组件       |
| 图表      | ECharts           | 折线图、饼图、柱状图等数据可视化 |
| 后端      | Python + FastAPI  | 提供数据接口 (API)               |
| 数据库    | MongoDB           | 存储客户、交易、活动等数据       |
| 数据导入  | pandas + openpyxl | 从 Excel 文件导入数据            |

## 项目结构

```
TBNZ-Data-Dashboard/
├── frontend/                    # 前端代码（浏览器里看到的部分）
│   ├── src/
│   │   ├── layouts/             # 页面框架（侧边栏、导航）
│   │   │   ├── AppLayout        #   主框架：侧边栏 + 内容区
│   │   │   └── AnalysisLayout   #   综合分析的子导航框架
│   │   ├── pages/               # 各个页面
│   │   │   ├── Map/             #   地图页 — 热力图 + 筛选 + ROI
│   │   │   ├── Analysis/        #   综合分析
│   │   │   │   ├── ClientsPage  #     客户信号与异常
│   │   │   │   ├── TradingPage  #     交易趋势分析
│   │   │   │   ├── AUCPage      #     资产托管分析
│   │   │   │   └── RankingsPage #     Top 200 排名追踪
│   │   │   └── Activities/      #   活动分析 — 时间线 + 详情 + 获客追踪
│   │   ├── components/          # 可复用的小组件
│   │   │   ├── StatCard         #   指标卡片（显示数字 + 涨跌幅）
│   │   │   ├── PageHeader       #   页面顶部标题栏
│   │   │   ├── ClientTag        #   客户标签（HNW/S-Class/Inactive 等）
│   │   │   └── SignalCard       #   客户信号卡片
│   │   ├── services/api.js      # 统一的后端 API 调用封装
│   │   └── styles/              # 全局样式和设计变量
│   └── vite.config.js           # 构建配置（含 API 代理）
│
├── backend/                     # 后端代码（提供数据的部分）
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（启动文件）
│   │   ├── config.py            # 配置（数据库连接等）
│   │   ├── models/              # 数据模型定义
│   │   ├── schemas/             # 请求/响应模型
│   │   ├── services/            # 业务服务（含 Excel 导入）
│   │   └── routers/             # API 路由（按功能分文件）
│   │       ├── clients.py       #   客户相关接口
│   │       ├── trading.py       #   交易相关接口
│   │       ├── auc.py           #   资产托管相关接口
│   │       ├── rankings.py      #   排名相关接口
│   │       ├── activities.py    #   活动相关接口
│   │       ├── map.py           #   地图相关接口
│   │       └── import_data.py   #   Excel 导入接口
│   ├── requirements.txt         # Python 依赖列表
│   ├── .env.example             # 环境变量模板
│   └── scripts/
│       ├── generate_sample_excel.py # 生成联调样例 Excel
│       ├── generate_multi_month_data.py # 生成多月份动态样例（含资产配置比例）
│       ├── inspect_excel.py         # 查看样例文件的 sheet 和行数
│       ├── check_mongo_counts.py    # 查看导入后各集合落库数量
│       └── smoke_test_import.ps1     # 一键健康检查+导入联调
│
├── data/                        # Excel 样例数据 / 数据字典
├── development-plan.md          # 完整的开发计划文档
└── docker-compose.yml           # MongoDB 容器部署配置
```

## 页面导航说明

网站左侧有一个固定的侧边栏，包含三个主要入口：

```
🌐 地图 (Map)           → /map             一个页面，带筛选面板
📊 综合分析 (Whole)      → /analysis/...    四个子页面，按路由切换
  ├─ 客户               → /analysis (默认页)
   ├─ 交易               → /analysis/trading
   ├─ AUC 资产            → /analysis/auc
   └─ 排名               → /analysis/rankings
⚡ 活动分析 (Activities)  → /activities       一个页面，左列时间线 + 右侧详情
```

## 如何在本地运行

### 前置条件

- **Node.js** v18+（前端需要）
- **Python** 3.10+（后端需要）
- **MongoDB**：可选本地安装或 Docker 方式运行

### 第一步：启动数据库

方式 A：本地安装 MongoDB（Windows）

```bash
winget install --id MongoDB.Server -e --accept-package-agreements --accept-source-agreements
```

方式 B：用 Docker 启动 MongoDB（推荐）

```bash
docker compose up -d mongodb
```

两种方式都要求数据库监听 `localhost:27017`。

### 第二步：启动后端

```bash
cd backend

# 配置环境变量（首次）
copy .env.example .env

# 创建 Python 虚拟环境（首次）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖（首次）
pip install -r requirements.txt

# 启动后端服务
uvicorn app.main:app --reload --port 8000
```

启动后访问 http://localhost:8000/docs 可以看到 API 文档。

### MongoDB + Excel 联调（后端）

业务填表说明书（标准 Excel 导入格式）：

- [docs/excel-import-spec-business.md](docs/excel-import-spec-business.md)
- [docs/excel-import-template-3-sheets.xlsx](docs/excel-import-template-3-sheets.xlsx)

```bash
cd backend

# 生成联调用样例 Excel（输出到 data/sample_import.xlsx）
venv\Scripts\python.exe scripts/generate_sample_excel.py

# 校验样例文件（显示 sheet 与行数）
venv\Scripts\python.exe scripts/inspect_excel.py ../data/sample_import.xlsx
```

PowerShell 上传样例（兼容 Windows PowerShell 5.1）：

```powershell
curl.exe -s -X POST -F "file=@../data/sample_import.xlsx" http://localhost:8000/api/import/upload
```

返回结果里会包含每个 sheet 的导入统计（总行数、成功数、重复数、错误数）。

也可以直接执行一键联调脚本：

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts/smoke_test_import.ps1
```

如果需要快速验证各模块（小样本，30 行总数据），可使用小规模联调脚本：

```powershell
# 在仓库根目录执行
run-small-data-smoke.bat
```

该脚本会自动完成：

- 生成 `data/sample_import_small.xlsx`
- 上传导入到 `/api/import/upload`
- 调用已完成模块关键接口（Clients/Trading/AUC/Rankings/Activities）
- 输出 MongoDB 各集合落库计数

最近一次联调验收（后端）结果：

- Health Check：`/api/health` 返回 `ok`
- Excel 上传导入：`status=success`，`total_rows=54`，`imported_rows=54`，`duplicate_rows=0`，`error_rows=0`
- MongoDB 落库计数：
  - `customers=2`
  - `transactions=2`
  - `activities=1`
  - `activity_tracking=1`
  - `customer_assets=24`
  - `rankings`：可选（未上传时由后端自动计算排名）

导入后验证 MongoDB 落库数量：

```bash
cd backend
venv\Scripts\python.exe scripts/check_mongo_counts.py
```

### 第三步：启动前端

```bash
cd frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

启动后打开浏览器访问 http://localhost:5173 即可看到界面。

> 前端开发服务器会自动把 `/api` 开头的请求转发到后端 `localhost:8000`，无需额外配置。

### 第四步：运行测试与质量校验

后端（pytest）：

```bash
cd backend
python -m pytest -q
```

当前阶段三/四/七测试结果：`15 passed`

前端（ESLint）：

```bash
cd frontend
npm run lint
```

当前结果（2026-03-23 本地检查）：未通过（8 errors, 2 warnings）

主要问题：

- `ClientsPage.jsx` 中 `navigate` 未定义
- `MapPage.jsx` 存在未使用变量
- `RankingsPage.jsx` 存在 Hook 依赖告警

## 当前开发进度

- [x] 项目初始化（前端 Vite + React，后端 FastAPI）
- [x] UI 框架搭建（侧边栏导航、路由系统、页面布局）
- [x] 设计系统建立（颜色、字体、间距等设计变量）
- [x] 全部 6 个页面的 UI 框架（含 Mock 数据展示）
- [x] 地图页面基础实现（Leaflet 地图 + 多条件筛选，当前基于本地 JSON）
- [x] 活动分析页面基础实现（时间线、详情卡、趋势图、追踪表，当前为静态数据）
- [x] 可复用组件（指标卡片、客户标签、信号卡片等）
- [x] 后端 API 路由骨架（6 个模块的接口定义）
- [x] 前端 API 调用封装
- [x] MongoDB 数据模型实现（Beanie Document + 索引）
- [x] Excel 数据导入功能（`/api/import/upload` + 校验 + 批量 upsert + 导入日志）
- [x] MongoDB + Excel 后端部署联调（健康检查 + 导入上传 + 落库校验）
- [x] 阶段三（Clients）前后端联调：概览、信号筛选分页、客户详情、推送 Sales
- [x] 阶段四（Trading）前后端联调：概览、趋势、分类占比、贡献者分页排序
- [x] 阶段五（AUC）核心联调：概览、趋势、分级分布、Top 客户、分布分析 Tab
- [x] 阶段六（Rankings）前后端联调：概览统计、变动追踪、Top200 双维度排名
- [x] 阶段二（Map）后端 API：`/api/map/heatmap-data`、`/api/map/roi-ranking`、`/api/map/age-distribution`（当前为 mock 数据）
- [x] 阶段七（Activities）后端接口：活动列表、活动详情、执行趋势、获客追踪（分页/筛选/排序）
- [x] AUC 资产配置动态口径：基于客户快照资产配置字段按月计算（非固定示例比例）
- [x] AUC 分布分析多币种切换：USD/CNY/EUR/NZD/HKD/AUD
- [x] 阶段三/四/七后端单元测试（pytest）
- [ ] 前端代码规范校验（ESLint 待修复，当前存在 8 errors / 2 warnings）
- [ ] 活动分析前端联调（Activities 页面需对接 `/api/activities*`）
- [ ] 阶段二（Map）前后端联调（前端需对接 `/api/map/*`）
- [ ] 地图热力图集成（Leaflet + heatmap.js）
- [ ] 完整的筛选和交互功能
- [ ] 测试与性能优化

## AUC 模块已实现要点（同步）

- AUC 页面支持两个视图 Tab：`AUC 分析` 与 `AUC 分布分析`
- 趋势图支持三种模式切换：`全部显示` / `仅资产` / `仅流入`
- 线条节点颜色已调整为“比线更深”的配色方案
- 资产配置图支持多币种筛选（USD/CNY/EUR/NZD/HKD/AUD）
- `GET /api/auc/asset-allocation` 已按月动态返回数据，随快照与时间变化

### AUC 动态样例数据（推荐联调）

```bash
cd backend
venv\Scripts\python.exe scripts/generate_multi_month_data.py
curl.exe -s -X POST -F "file=@../data/sample_import_multi_month.xlsx" http://localhost:8000/api/import/upload
```

- 该样例覆盖最近 12 个月（包含当前月）
- `customer_assets` 中包含 `stocks_pct/options_pct/futures_pct/funds_pct`，用于驱动 AUC 分布图动态变化

## 设计参考

UI 设计基于 Figma 设计稿，主要设计特征：

- **品牌色**：Tiger 黄 (#FFCC00) 作为主色调
- **风格**：简洁白底卡片式布局，圆角设计
- **左侧边栏**：固定 200px 宽，包含 Logo + 导航 + 用户信息
