# AI_CONTEXT — SiC 外延层厚度反演研究

> For Claude Code, ChatGPT, Codex.

## Project

数学建模竞赛项目：用 FTIR 反射光谱反演 4H-SiC 外延层厚度。已完成完整论文。

- Python 3.12 | numpy | scipy | matplotlib

## Code Map

```
src/run_pipeline.py                      ← 主流程入口
src/spectral_pipeline.py                 ← 频谱分析流程
src/dong2012_tmm_coordinate_search.py    ← TMM 坐标搜索
src/dong2012_tmm_constrained_refinement.py ← 物理约束优化
src/dong2012_tmm_bestfit_export.py       ← 最佳拟合导出
src/data_processing_diagnostics.py       ← 数据预处理诊断
src/band_weighted_tmm_profile.py         ← 波段权重拟合
src/final_evidence_audit.py              ← 最终证据审计
...
```

## Key Docs

| File | Content |
|------|---------|
| `docs/Overview.md` | 项目总览 |
| `docs/literature/Dong2012精读与模型转化.md` | 核心论文精读 |
| `docs/methods/方法论总览.md` | 方法论体系 |
| `docs/notes/数学符号与公式总表.md` | 符号约定 |

## 最终论文

`deliverables/final_research_paper_2026-07-07/main.pdf`
