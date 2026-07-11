# 数据处理诊断摘要

## 问题

本轮实验回答的问题是：在碳化硅附件 1、附件 2 中，厚度信息是不是只由物理模型决定，数据处理是否几乎无关？

答案不是二选一。物理模型决定“如何把条纹相位解释为厚度”，数据处理决定“我们是否稳定地看见了同一组条纹信息”。本轮只做小规模 sanity check，不把任何预处理结果写成最终厚度。

## 方法

对 $1500\text{--}4000\ \mathrm{cm^{-1}}$ 波段做统一重采样，然后比较以下预处理：

- 去均值：`center_only`
- 移动平均去趋势：`ma_detrend_201cm`、`ma_detrend_401cm`、`ma_detrend_801cm`
- 多项式去趋势：`poly2_detrend`、`poly3_detrend`
- 滚动中位数/分位数基线：`rolling_median_401cm`、`rolling_q20_401cm`
- 一阶差分：`first_difference`

评价指标包括主频周期、常数 $n=2.60$ 口径下的 FFT 厚度初值、峰值显著性 `peak_to_median`、峰谷数量和双角度一致性。

## 主要发现

本轮测试的所有预处理都给出相同的双角度主周期 $\Delta\nu=250\ \mathrm{cm^{-1}}$，因此不能说某一种预处理在主周期上明显胜出。差异主要体现在峰值显著性、峰谷数量和局部曲线形态上。常数 $n=2.60$ 口径下，$10^\circ$ 与 $15^\circ$ 的 FFT 厚度初值差约为 $0.0212\ \mu m$。

所有预处理的平均主周期统计如下：

| 指标 | 数值 |
| --- | --- |
| count | 9 |
| mean | 250 |
| std | 0 |
| min | 250 |
| max | 250 |

双角度对比表：

| preprocessing | thickness_10deg_um | thickness_15deg_um | thickness_gap_um | period_10deg_cm | period_15deg_cm | period_gap_cm | min_peak_to_median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| center_only | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 11.8847 |
| first_difference | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 13.4117 |
| ma_detrend_201cm | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 13.1276 |
| ma_detrend_401cm | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 14.9123 |
| ma_detrend_801cm | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 5.8497 |
| poly2_detrend | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 11.6798 |
| poly3_detrend | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 11.6595 |
| rolling_median_401cm | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 12.4211 |
| rolling_q20_401cm | 7.70952 | 7.73071 | 0.0211848 | 250 | 250 | 0 | 12.9445 |

## 当前解释

数据中并不是“信息很少”，而是主要信息比较集中：条纹周期给出厚度尺度，条纹相位和振幅包络约束材料参数，双角度差异暴露模型是否一致，残差结构暴露模型遗漏项。数据处理的作用是把这些信息拆开看清楚。

如果不同预处理都给出接近的主周期，说明条纹周期是数据中的稳定信息；如果不同预处理导致厚度初值或峰谷数量大幅变化，说明简单峰谷法和频域法不能单独作为最终结论，必须回到 TMM 物理模型和残差诊断。

## 与主模型关系

本轮实验不替代 Dong/TMM 模型。它只提供三类证据：

1. 检查条纹周期是否稳定；
2. 判断哪些预处理会破坏物理条纹；
3. 为后续滑窗 FFT、VMD-LSP 或 TMM 联合拟合提供更可靠的数据处理口径。

## 输出文件

- `Experiments/outputs/data_processing_diagnostics_summary.csv`
- `Experiments/outputs/data_processing_diagnostics_curves.csv`
- `Experiments/outputs/data_processing_diagnostics_summary.md`
- `Experiments/figures/data_processing_preprocessed_curves.svg`
- `Experiments/figures/data_processing_fft_thickness_seed.svg`

## 下一步

下一步不应盲目加复杂预处理。更合理的是：

1. 把最稳的 2-3 种预处理接入滑窗 FFT；
2. 检查主周期是否随波数区间漂移；
3. 把漂移结果和 Dong/TMM 残差高发波段对齐；
4. 判断差异来自数据噪声、基线处理、吸收区，还是来自物理模型缺项。
