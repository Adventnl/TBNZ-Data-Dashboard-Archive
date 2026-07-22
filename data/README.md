# 数据目录

存放 Excel 样例数据和数据字典。

## 数据文件规范

| 数据类型 | 文件命名                 | 说明         |
| -------- | ------------------------ | ------------ |
| 客户数据 | customers_YYYYMM.xlsx    | 客户基础信息 |
| 交易数据 | transactions_YYYYMM.xlsx | 月度交易记录 |
| 资产数据 | assets_YYYYMM.xlsx       | 客户资产快照 |
| 活动数据 | activities.xlsx          | 活动信息     |

## 联调样例文件

- `sample_import.xlsx`：MongoDB + Excel 导入联调用样例文件（多 sheet）
- 生成命令：在 `backend` 目录执行 `venv\Scripts\python.exe scripts/generate_sample_excel.py`
- 校验命令：在 `backend` 目录执行 `venv\Scripts\python.exe scripts/inspect_excel.py ../data/sample_import.xlsx`
- 生成位置：`data/sample_import.xlsx`
- 版本控制：该文件为联调临时产物，已加入 `.gitignore`，按需重新生成即可。

- `sample_import_multi_month.xlsx`：AUC 动态联调用多月份样例（最近 12 个月，含当前月）
- 生成命令：在 `backend` 目录执行 `venv\Scripts\python.exe scripts/generate_multi_month_data.py`
- 校验命令：在 `backend` 目录执行 `venv\Scripts\python.exe scripts/inspect_excel.py ../data/sample_import_multi_month.xlsx`
- 导入命令（PowerShell）：`curl.exe -s -X POST -F "file=@../data/sample_import_multi_month.xlsx" http://localhost:8000/api/import/upload`
- 说明：该样例在 `customer_assets` 中包含 `stocks_pct/options_pct/futures_pct/funds_pct`，用于驱动 AUC 分布图按月份动态变化。
- 当前默认规模：`260` 客户、`12` 个月、`rankings` 约 `6240` 条记录（AUC + Trading 双维度），用于完整联调 Top 200 排名追踪场景。

- `sample_import_small.xlsx`：小规模联调样例（总计 `30` 行，覆盖客户/交易/AUC/排名/活动）
- 生成命令：在 `backend` 目录执行 `venv\Scripts\python.exe scripts/generate_small_test_dataset.py`
- 校验命令：在 `backend` 目录执行 `venv\Scripts\python.exe scripts/inspect_excel.py ../data/sample_import_small.xlsx`
- 一键联调脚本（仓库根目录）：`run-small-data-smoke.bat`
- 脚本作用：自动生成小样例、上传导入、调用关键 API、输出 MongoDB 落库计数
