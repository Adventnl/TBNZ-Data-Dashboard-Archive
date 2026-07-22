# Excel 数据接入填表说明书（业务版）

本文档用于按统一格式填报 Excel，并通过后端接口导入系统。

- 适用接口：`POST /api/import/upload`
- 支持文件：`.xlsx`、`.xlsm`
- 上传方式：单文件上传（1 个 Excel 内含多个 sheet）
- 模板下载（3 张表，仅表头）：[excel-import-template-3-sheets.xlsx](excel-import-template-3-sheets.xlsx)

## 1. 总体填报规范

### 1.1 工作簿结构

当前版本建议一个文件包含以下 3 个标准 sheet（名称建议完全一致）：

| sheet 名 | 用途 | 最低必填字段 |
| --- | --- | --- |
| `customers` | 客户主档 | `uid`, `name` |
| `transactions` | 交易流水 | `uid`, `trade_amount` |
| `customer_assets` | 客户月度资产快照 | `uid`, `month` |

说明：

- 可只上传其中部分 sheet（不强制必须 3 张都提供）。
- 只要某张 sheet 的必填字段齐全，系统就会导入该 sheet。
- 无法识别或字段缺失的 sheet 会被跳过，并在导入结果 `summary` 里报错。
- 排名（Top 200/Top 500）会在后端基于 `customer_assets` 自动计算，无需单独提交 `rankings` sheet。
- `activities`、`activity_tracking` 目前先不纳入业务填报范围。

### 1.2 通用格式要求

- 第一行必须是字段名（表头）。
- 不要合并单元格。
- 不要留全空行、全空列（系统会自动清理，但建议业务侧避免）。
- 日期建议统一填 `YYYY-MM-DD`。
- 月份建议统一填 `YYYY-MM`。
- 数值列不要填中文或说明文字（例如“约 10 万”）。

### 1.3 重复行处理（重要）

系统按业务主键做 **upsert（有则更新，无则新增）**：

| sheet 名 | 去重/更新键 |
| --- | --- |
| `customers` | `uid` |
| `transactions` | 优先 `transaction_id`；若缺失则退化到交易组合键 |
| `customer_assets` | `uid + month` |

## 2. 标准字段定义（业务填报列）

以下为建议业务按“标准列名”直接填报。

---

## 2.1 customers（客户主档）

### 必填

| 字段名 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `uid` | 文本 | 客户唯一标识 | `10001` |
| `name` | 文本 | 客户姓名 | `Alice Wang` |

### 推荐可选

| 字段名 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `client_id` | 文本 | 客户编号 | `C001` |
| `age` | 整数 | 年龄 | `32` |
| `gender` | 文本 | 性别（建议 `M/F`） | `F` |
| `location` | 文本 | 城市/地区 | `Auckland` |
| `nationality` | 文本 | 国籍 | `NZ` |
| `monthly_net_assets_usd` | 数值 | 月度净资产（USD） | `125000` |
| `monthly_trade_count` | 整数 | 月交易次数 | `12` |
| `trade_category` | 文本 | 主交易品类 | `stock` |
| `stocks_pct` | 数值 | 股票配置比例 | `45` |
| `options_pct` | 数值 | 期权配置比例 | `25` |
| `futures_pct` | 数值 | 期货配置比例 | `15` |
| `funds_pct` | 数值 | 基金配置比例 | `15` |

默认行为：

- `monthly_net_assets_usd`、`monthly_trade_count` 缺失时按 `0` 处理。
- `client_type`、`tags`、`signal_description`、`recommended_action` 不再由业务侧填报，后端会基于算法自动生成。

---

## 2.2 transactions（交易流水）

### 必填

| 字段名 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `uid` | 文本 | 客户唯一标识 | `10001` |
| `trade_amount` | 数值 | 交易金额 | `12000` |

### 推荐可选

| 字段名 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `transaction_id` | 文本 | 交易唯一编号（强烈建议填） | `T001` |
| `month` | 文本 | 月份（`YYYY-MM`） | `2026-03` |
| `trade_date` | 日期 | 交易日期 | `2026-03-01` |
| `trade_type` | 文本 | 交易类型 | `stock` |
| `trade_category` | 文本 | 交易分类 | `equity` |
| `market` | 文本 | 市场 | `NZ` |
| `trading_volume` | 数值 | 交易量 | `15000` |
| `currency` | 文本 | 币种 | `USD` |

默认行为：

- `currency` 缺失时默认 `USD`。
- `month` 缺失且 `trade_date` 有值时，系统自动由日期推导月份。

---

## 2.3 customer_assets（客户资产快照）

### 必填

| 字段名 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `uid` | 文本 | 客户唯一标识 | `10001` |
| `month` | 文本 | 月份（`YYYY-MM`） | `2026-03` |

### 推荐可选

| 字段名 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `net_assets` | 数值 | 净资产 | `125000` |
| `deposit_amount` | 数值 | 入金金额 | `10000` |
| `withdrawal_amount` | 数值 | 出金金额 | `2000` |
| `trading_volume` | 数值 | 交易量 | `15000` |
| `currency` | 文本 | 币种 | `USD` |
| `snapshot_date` | 日期 | 快照日期 | `2026-03-31` |
| `stocks_pct` | 数值 | 股票配置比例（AUC 分布推荐） | `45` |
| `options_pct` | 数值 | 期权配置比例（AUC 分布推荐） | `25` |
| `futures_pct` | 数值 | 期货配置比例（AUC 分布推荐） | `15` |
| `funds_pct` | 数值 | 基金配置比例（AUC 分布推荐） | `15` |

默认行为：

- `currency` 缺失时默认 `USD`。

---

## 2.4 排名说明（无需填报）

- 当前版本无需业务单独提交 `rankings` sheet。
- 系统会根据 `customer_assets` 的 `net_assets`（AUC 维度）和 `trading_volume`（交易维度）自动计算排名。
- 若历史流程仍上传 `rankings`，系统兼容导入，但不作为业务侧必填。

## 3. 列名兼容（历史模板别名）

系统支持部分历史字段自动映射为标准字段。建议业务长期使用标准列名，但旧模板可按下表兼容：

| 旧列名/别名 | 自动映射为 |
| --- | --- |
| `customer_id` | `client_id` |
| `client_uid`, `customer_uid`, `user_id`, `user_uid` | `uid` |
| `client_name`, `customer_name` | `name` |
| `trade_id`, `order_id` | `transaction_id` |
| `amount`, `trade_value` | `trade_amount` |
| `trade_volume`, `volume` | `trading_volume` |
| `portfolio_value`, `account_balance`, `net_asset` | `net_assets` |
| `asset_value` | `auc_value` |
| `rank_change` | `previous_rank` |

## 4. 提交前质检清单（发业务）

提交 Excel 前，请逐项确认：

1. 文件扩展名为 `.xlsx` 或 `.xlsm`。
2. 每个 sheet 第一行是标准字段名，无合并单元格。
3. 关键必填列完整，且必填列单元格无空值。
4. 日期列统一 `YYYY-MM-DD`，月份列统一 `YYYY-MM`。
5. 数值列均为纯数字（不要带中文单位）。
6. 同一业务主键无冲突（例如同一个 `uid+month` 仅保留一行资产快照）。

## 5. 常见报错与处理

| 报错信息（示例） | 可能原因 | 处理建议 |
| --- | --- | --- |
| `Only .xlsx or .xlsm files are supported` | 文件类型不支持 | 另存为 `.xlsx` |
| `Uploaded file is empty` | 上传了空文件 | 检查文件内容后重传 |
| `Missing required columns: ...` | 缺少必填列 | 按本文档补齐列名 |
| `Row X: missing required values in ...` | 必填列有空值 | 补齐该行字段 |
| `field must be numeric` | 数值列含非数字 | 清洗为纯数字 |
| `field must be a valid date` | 日期格式不可解析 | 改为标准日期格式 |
| `Unable to infer dataset type...` | sheet 名和字段均无法识别 | 使用标准 sheet 名并补齐关键列 |

---

如需业务侧模板文件（仅表头），建议基于本说明书生成并统一下发，避免多版本模板并行。