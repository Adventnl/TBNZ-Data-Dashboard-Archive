# MongoDB + Excel 导入联调指南

本文档用于在本地完成后端 MongoDB 接入和 Excel 导入接口联调。

## 1. 准备数据库

可任选一种方式：

### 方式 A：本地安装 MongoDB（Windows）

```powershell
winget install --id MongoDB.Server -e --accept-package-agreements --accept-source-agreements
```

安装后可检查：

```powershell
Get-Command mongod
Get-Service MongoDB
```

### 方式 B：Docker 运行 MongoDB

```powershell
docker compose up -d mongodb
```

检查容器状态：

```powershell
docker ps
```

## 2. 启动后端

```powershell
cd backend
copy .env.example .env
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

预期返回：

```json
{ "status": "ok", "service": "growth-analytics-api" }
```

## 3. 生成导入样例

```powershell
cd backend
.\venv\Scripts\python.exe scripts/generate_sample_excel.py
```

输出文件位于：`data/sample_import.xlsx`

如需生成小规模联调样例（总计 30 行，便于快速回归）：

```powershell
cd backend
.\venv\Scripts\python.exe scripts/generate_small_test_dataset.py
```

输出文件位于：`data/sample_import_small.xlsx`

## 4. 执行 Excel 上传导入

```powershell
curl.exe -s -X POST -F "file=@../data/sample_import.xlsx" http://localhost:8000/api/import/upload
```

如需联调 AUC 12 个月趋势与动态资产分布，建议使用多月份样例：

```powershell
cd backend
.\venv\Scripts\python.exe scripts/generate_multi_month_data.py
curl.exe -s -X POST -F "file=@../data/sample_import_multi_month.xlsx" http://localhost:8000/api/import/upload
```

导入成功时，返回结构包含：

- `status`：`success` 或 `partial_success`
- `summary`：每个 sheet 的导入统计
- `imported_rows` / `duplicate_rows` / `error_rows`

也可以直接执行仓库内的联调脚本（Windows PowerShell）：

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File scripts/smoke_test_import.ps1
```

小规模一键联调（推荐快速验证各模块）:

```powershell
# 在仓库根目录执行
run-small-data-smoke.bat
```

## 5. 验证 MongoDB 落库

```powershell
cd backend
.\venv\Scripts\python.exe scripts/check_mongo_counts.py
```

可额外验证 AUC 分布接口是否按月份动态变化：

```powershell
curl.exe -s "http://localhost:8000/api/auc/asset-allocation?month=2026-02"
curl.exe -s "http://localhost:8000/api/auc/asset-allocation?month=2026-03"
```

若两个月的 `percentage` 不同，说明分布图数据已按快照动态计算（而非固定示例比例）。

可额外验证 Activities 后端接口（阶段七）：

```powershell
curl.exe -s "http://localhost:8000/api/activities?page=1&page_size=10"
curl.exe -s "http://localhost:8000/api/activities/A001"
curl.exe -s "http://localhost:8000/api/activities/A001/trend"
curl.exe -s "http://localhost:8000/api/activities/A001/tracking?page=1&page_size=20&sort_by=registration_date&sort_order=descend"
```

说明：

- `/api/activities`：按 `date_start` 倒序分页返回活动列表
- `/api/activities/{id}`：返回活动详情、指标与趋势数据
- `/api/activities/{id}/trend`：返回按天趋势（含 `day/date/label/cumulative_visitors/new_signups`）
- `/api/activities/{id}/tracking`：支持关键词、渠道、客户类型、入金状态、归因结果、日期范围筛选以及分页排序

可额外验证 Map 后端接口（阶段二，当前为 mock 数据返回）：

```powershell
curl.exe -s "http://localhost:8000/api/map/heatmap-data?region=all&gender=all&age_group=all"
curl.exe -s "http://localhost:8000/api/map/roi-ranking?region=auckland"
curl.exe -s "http://localhost:8000/api/map/age-distribution?region=wellington"
```

说明：

- `/api/map/heatmap-data`：返回热力点位与筛选参数回显
- `/api/map/roi-ranking`：返回区域 ROI 统计与季度数据
- `/api/map/age-distribution`：返回区域年龄分布
- 以上接口当前用于前端联调占位，后续会替换为基于 MongoDB 聚合的真实口径

## 6. 常见问题

- 端口被占用：确认 27017 未被其他程序占用。
- 上传报 400：检查文件扩展名是否为 `.xlsx` 或 `.xlsm`。
- 上传报字段缺失：检查 sheet 列名是否满足必填字段（`uid`、`name`、`trade_amount` 等）。
- Docker 未安装：改用本地 MongoDB 安装方式。
- `Invoke-RestMethod -Form` 不可用：Windows PowerShell 5.1 不支持该参数，使用本文档中的 `curl.exe -F` 命令。
- `pandas/numpy` 兼容报错：优先使用 `backend/venv` 解释器执行脚本，不要混用系统 Python 环境。

## 7. 最近联调记录（后端）

最近一次 smoke test 结果：

- Health Check：`/api/health` 返回 `ok`
- 导入接口：`status=success`，`total_rows=54`，`imported_rows=54`，`duplicate_rows=0`，`error_rows=0`
- 落库计数：`customers=2`、`transactions=2`、`activities=1`、`activity_tracking=1`、`customer_assets=24`（`rankings` 可选，不上传时由后端自动计算）

说明：`import_logs` 的数量会随着每次导入递增，属于预期行为。
