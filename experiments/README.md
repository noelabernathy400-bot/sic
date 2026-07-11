# 实验目录说明

## 目标

本目录用于保存所有 Python 可复现实验。实验应从 `Sources/` 中读取原始数据，将派生结果写入 `Experiments/outputs/` 和 `Experiments/figures/`，不要覆盖原始资料。

## 当前脚本

| 脚本 | 作用 |
| --- | --- |
| `../Code/initial_data_diagnostic.py` | 初步数据诊断，输出命令行摘要 |
| `../Code/spectral_pipeline.py` | 生成谱线图、峰谷表、基线峰距厚度和 FOD 拟合结果 |
| `../Code/run_pipeline.py` | 一键运行当前 pipeline |

## 运行方式

```powershell
& 'C:\Users\A2826\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'Projects/MathematicalModeling/碳化硅外延层厚度确定研究/Code/run_pipeline.py'
```

## 输出

- `outputs/spectral_summary.csv`
- `outputs/extrema_points.csv`
- `outputs/baseline_thickness_intervals.csv`
- `outputs/fod_fit_results.csv`
- `outputs/spectral_pipeline_summary.md`
- `figures/*.svg`

## 已知口径

- 当前 FOD 脚本分别拟合峰序列和谷序列；相邻同类极值按一级次差处理。
- 如果后续使用峰谷混合序列，才应按半级次差处理。

## 规则

- 后续代码全部使用 Python。
- 所有脚本必须能从项目目录结构自动定位数据。
- 任何数值结果都要说明模型、参数和单位。
- 没有外部真值时，不要用“准确”替代“自洽/稳定/与模型一致”。
