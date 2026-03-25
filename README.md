# DFM Auto Generator MVP

一个基于 FastAPI、`python-pptx` 和 mock 资产生成的 DFM 自动生成系统 MVP。

当前目标不是做真实 CAD 解析，而是把整条链路跑通到“本机可直接演示”，并开始支持更接近真实项目的 BOM 输入适配：

- 输入 STEP 文件
- 输入 BOM JSON / CSV
- 输出 15 页 DFM PPT
- 输出标准化中间产物 `report_data.json`
- 支持多 BOM profile 配置与自动识别
- 自动补 mock 图片，不留空白图片区
- 支持 API、CLI、pytest 最小化测试

## Python 版本要求

- 最低要求：Python 3.9+
- 推荐版本：Python 3.10 或 3.11
- 如果你的机器上 `python` 不可用，请直接使用 `python3`

## 当前目录结构

```text
app/
  api/
  cad_parser/
    base.py
    factory.py
    mock_parser.py
    parser.py
    real_parser.py
  core/
  mock_assets/
  models/
  planner/
  ppt_builder/
  tagging/
  main.py
data/
  mock_bom.json
  realistic_bom.json
  realistic_bom.csv
  mock_model.step
configs/
  bom_mapping.json
  bom_profiles/
    generic_json.json
    generic_csv.json
    erp_style_a.json
    plm_style_b.json
outputs/
tests/
run.py
requirements.txt
```

## 快速开始

### 1. 创建虚拟环境

```bash
cd /Users/zhangyiming/Desktop/Aether
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 直接生成 sample PPT

```bash
python run.py sample
```

成功后会在终端输出生成的 `.pptx` 绝对路径。

如果想手动指定 BOM profile：

```bash
python run.py sample --bom-profile generic_json
```

如果希望指定输出目录：

```bash
python run.py sample --output-dir outputs
```

如果想从本地真实文件生成：

```bash
python run.py generate \
  --step-file data/mock_model.step \
  --bom-file data/realistic_bom.csv \
  --bom-profile erp_style_a
```

### 4. 启动 FastAPI 服务

```bash
uvicorn app.main:app --reload
```

启动后可访问：

- `GET /`
- `GET /health`
- `POST /generate/sample`
- `POST /generate`

### 5. 通过 API 生成 sample

```bash
curl -X POST "http://127.0.0.1:8000/generate/sample"
```

也可以手动传 profile：

```bash
curl -X POST "http://127.0.0.1:8000/generate/sample?bom_profile=generic_json"
```

### 6. 上传 STEP + BOM 生成 PPT

```bash
curl -X POST "http://127.0.0.1:8000/generate" \
  -F "step_file=@data/mock_model.step" \
  -F "bom_file=@data/mock_bom.json" \
  -F "bom_profile=generic_json"
```

也支持 CSV：

```bash
curl -X POST "http://127.0.0.1:8000/generate" \
  -F "step_file=@data/mock_model.step" \
  -F "bom_file=@data/realistic_bom.csv"
```

### 7. 运行测试

```bash
pytest
```

## 当前会生成哪些页面

固定输出 15 页：

1. DFM Auto-Generated Report
2. Input Snapshot
3. DFM Workflow Overview
4. Product Structure Diagram
5. Assembly Hierarchy
6. Module Decomposition Overview
7. Motion/Top Module Detail
8. Process/Top Module Detail
9. Control/Top Module Detail
10. BOM Summary
11. Spare Parts And Consumables
12. Long Lead Time Items
13. DFM Observations
14. Software Architecture
15. Next Steps

实际第 7-9 页会根据当前 tag 结果选取前三个模块名。

## 标准化 report_data.json

每次 `sample` 或 `generate` 都会在 `outputs/` 下额外产出一份 `report_data.json`，用于调试中间结果。

它的内容包括：

- 输入源信息：STEP 文件名、BOM 来源、BOM 格式、mapping 配置路径
- profile 信息：`selected_bom_profile`、`detected_bom_profile`、检测置信度
- 标准化后的 `parts`
- BOM warning 列表
- BOM blocking error 列表
- `cad_model`
- `tagging`
- `plan_summary`

这样即使后面要替换真实 parser 或继续调 planner，也可以先看标准化数据是否正确。

## 标准化后的 Parts Schema

外部 BOM 无论来自 JSON 还是 CSV，都会先被适配到统一 schema：

```json
{
  "item_no": "0010",
  "part_name": "Servo Motor 1.5kW",
  "quantity": 2,
  "uom": "PCS",
  "material": "N/A",
  "process": "Purchased part",
  "category": "motion",
  "supplier": "Yaskawa Distributor",
  "lead_time_days": 35,
  "module_hint": "motion",
  "is_spare": false,
  "is_consumable": false,
  "revision": "A",
  "drawing_no": "ELE-MOT-015",
  "notes": "",
  "source_row": 3,
  "source_fields": {
    "Line No": "0030",
    "Item Description": "Servo Motor 1.5kW",
    "Qty": 2
  }
}
```

当前内部 planner / tagging / ppt_builder 使用的是其中的业务字段，`source_row` 和 `source_fields` 主要用于追踪外部数据来源和排错。

## BOM 外部输入适配

新增了 [app/bom_adapter/adapter.py](/Users/zhangyiming/Desktop/Aether/app/bom_adapter/adapter.py)、[app/bom_adapter/profiles.py](/Users/zhangyiming/Desktop/Aether/app/bom_adapter/profiles.py) 和 [configs/bom_profiles/](/Users/zhangyiming/Desktop/Aether/configs/bom_profiles)。

目前支持：

- JSON 数组格式
- JSON 包装格式：`items` / `rows` / `data` / `bom` / `records`
- CSV 表头映射

当前支持的 BOM profile：

- `generic_json`
- `generic_csv`
- `erp_style_a`
- `plm_style_b`

profile 可以手动指定，也可以自动识别。

当前已内置常见字段别名映射：

- `part_name / name / item_name / item description`
- `qty / quantity`
- `vendor / supplier`
- `lead_time / lt / leadtime`
- `category / type`

另外还支持：

- `material`
- `process`
- `module_hint / module`
- `revision / rev`
- `drawing_no / dwg_no`
- `is_spare / spare_flag`
- `is_consumable / consumable_flag`

如果外部 BOM 缺字段：

- 不会直接报错退出
- 非关键字段会使用默认值补齐
- warning 会写入接口响应和 `report_data.json`
- 关键字段缺失会记录为 blocking error，并阻止 PPT 生成

## BOM Profile 自动识别

如果没有显式传 `bom_profile`，系统会自动做一次轻量识别。

自动识别主要依据：

- 文件扩展名：`.json` / `.csv`
- 表头字段名
- 关键列组合
- profile 的特征关键词

例如：

- `Line No + Item Description + Vendor + LT` 更像 `erp_style_a`
- `Find No + Item Name + Subsystem + Approved Mfr` 更像 `plm_style_b`

如果识别不到足够高的置信度：

- JSON 会回退到 `generic_json`
- CSV 会回退到 `generic_csv`

`report_data.json` 中会记录：

- `selected_bom_profile`
- `detected_bom_profile`
- `detected_bom_profile_confidence`

## 真实输入示例

保留了最小示例：

- [mock_bom.json](/Users/zhangyiming/Desktop/Aether/data/mock_bom.json)

新增了更接近工业现场风格的样例：

- [realistic_bom.json](/Users/zhangyiming/Desktop/Aether/data/realistic_bom.json)
- [realistic_bom.csv](/Users/zhangyiming/Desktop/Aether/data/realistic_bom.csv)

这些样例包含了更像现场导出的字段命名，例如：

- `Line No`
- `Item Description`
- `Qty`
- `Vendor`
- `LT`
- `Commodity_Group`
- `DWG No`
- `Rev`

## Warning 与 Blocking Error 的区别

当前 BOM 输入校验分两级：

Warning：

- 缺少非关键字段
- 例如 `supplier`、`lead_time_days`、`category`
- 系统会补默认值，流程继续

Blocking Error：

- 缺少关键字段
- 当前关键字段默认是 `part_name` 和 `quantity`
- 系统会写出 `report_data.json`，但不会继续生成 PPT

这样做的目的，是把“还能演示但数据不完整”和“已经不适合继续生成报告”明确分开。

## 当前 mock 的部分

- STEP 解析：当前默认走 `MockCADParser`
- CAD 结构：由 mock parser 返回稳定装配树
- 图片资产：由 `app/mock_assets/generator.py` 动态生成 PNG 占位图
- DFM 判断：当前是基于关键词和 BOM 字段的轻量规则

## CAD Parser 未来替换方式

当前 `cad_parser` 已经抽象为稳定接口：

- [app/cad_parser/base.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/base.py)：定义 `CADParser`
- [app/cad_parser/mock_parser.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/mock_parser.py)：当前演示用 mock 实现
- [app/cad_parser/real_parser.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/real_parser.py)：未来真实解析器占位
- [app/cad_parser/factory.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/factory.py)：根据 `parser_type` 选择实现
- [app/cad_parser/parser.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/parser.py)：当前工作流入口 facade

未来接入真实 STEP 解析时，只需要：

1. 在 `FutureRealCADParser.parse()` 中实现真实解析逻辑
2. 保持输出仍然是 `CADModel`
3. 通过 `parser_type="real"` 或环境变量 `DFM_CAD_PARSER=real` 切换

这样 `tagging / planner / ppt_builder / API / CLI` 都不用改。

## 真实 STEP Parser 接入规范

真实 parser 暂时还没实现，但边界已经固定：

- 抽象定义在 [app/cad_parser/base.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/base.py)
- mock 实现在 [app/cad_parser/mock_parser.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/mock_parser.py)
- future real parser 占位在 [app/cad_parser/real_parser.py](/Users/zhangyiming/Desktop/Aether/app/cad_parser/real_parser.py)

真实 parser 必须遵守下面的 contract：

输入：

- `step_filename: str`
- `step_bytes: Optional[bytes]`

输出：

- 必须返回 `CADModel`

`CADModel` 必须包含：

- `source_file`
- `product_name`
- `assembly_name`
- `parts`

其中 `parts` 中的每个 `CADPart` 至少应包含：

- `part_no`
- `part_name`
- `level`
- `parent_part_no`
- `module_hint`
- `notes`

建议真实 parser 额外保证：

- 顶层总装是 `level=0`
- 下级件层级清晰
- `parent_part_no` 可以串出装配树
- `module_hint` 尽量给出 motion / process / control / safety 这类可供下游使用的语义标签

只要保持这个 contract，下游模块都不需要重写。

## 输出说明

- 生成的 PPT 默认放在 `outputs/`
- 标准化后的 report data 默认放在 `outputs/*_report_data.json`
- 自动生成的图片放在 `outputs/assets/<ppt 文件名>/`
- 如果后续在 slide payload 里提供真实 `image_path`，`ppt_builder` 会优先使用真实图片；没有时才回退到 mock 图片

## 常见报错排查

### 1. `python: command not found`

直接改用：

```bash
python3 -m venv .venv
```

或者在虚拟环境激活后使用：

```bash
python run.py sample
```

### 2. `No module named ...`

通常是虚拟环境没激活或依赖没装全：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. BOM 结构不标准但系统没有立即失败

这是当前设计的预期行为。BOM adapter 会先尝试 profile 识别和标准化。

可以直接查看：

- 接口响应里的 `warnings`
- 输出目录里的 `*_report_data.json`

标准 JSON 仍建议尽量接近：

```json
[
  {
    "item_no": "10",
    "part_name": "Base Frame",
    "quantity": 1
  }
]
```

### 4. `Real STEP parsing is not implemented yet`

说明你显式切到了 `real` parser，但当前项目还没有真实解析实现。演示阶段请使用：

```bash
python run.py sample --parser mock
```

### 5. PPT 生成成功，但图片看起来是占位图

这是当前版本的正常行为。没有真实 CAD 截图或架构图时，系统会自动生成 mock PNG 并插入 PPT。

### 6. `Failed to generate PPT`

建议按下面顺序排查：

1. 确认 STEP 文件能被读取
2. 确认 BOM 是合法 JSON 或 CSV
3. 查看 `report_data.json` 里的 `selected_bom_profile`、`detected_bom_profile` 和 `blocking_errors`
4. 检查 `configs/bom_profiles/` 中是否已经有匹配的模板
5. 确认依赖已安装完成
6. 先用 `python run.py sample` 验证本地基础链路

### 7. 生成被 blocking error 阻止

这种情况下通常说明 BOM 缺了关键字段，例如：

- `part_name`
- `quantity`

系统仍然会输出 `report_data.json`，你可以先检查：

- 识别到了哪个 profile
- 关键字段为什么没有被映射到
- 是否需要新增一个专用 BOM profile
