# Dong/TMM $\Gamma_L,\Gamma_T$ 参数敏感性摘要

本输出用于检查 Dong2012 介电函数中的声子阻尼参数改变时，Airy/TMM 厚度低谷是否稳定，不是最终厚度结果。

## 敏感性设计

- 固定 Dong2012 的 $\nu_{p,\perp}$ 与 Drude 阻尼 $\gamma$。
- 改变声子阻尼 $\Gamma_L$ 与 $\Gamma_T$。
- 缩放系数：[0.5, 1.0, 1.5, 2.0]。
- `layer_shared_scale`：外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。
- `lt_shared_scale`：全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。
- 厚度搜索区间：$3.0\text{--}8.0\ \mu m$。
- 波段：$1500\text{--}4000\ cm^{-1}$。
- 每个角度允许独立线性标定 $R_{\mathrm{obs}}\approx aR_{\mathrm{model}}+b$。
- 联合误差取 $10^\circ$ 和 $15^\circ$ RMSE 的均值，并用最大 RMSE 检查最差角度。

## 各设计模式下的低谷范围

| mode | min | max | mean | std |
| --- | --- | --- | --- | --- |
| layer_shared_scale | 7.42 | 7.48 | 7.45 | 0.023094 |
| lt_shared_scale | 7.4 | 7.48 | 7.44875 | 0.0252653 |

## 联合误差最小的参数组合

| mode | design_note | epi_gamma_l_scale | epi_gamma_t_scale | sub_gamma_l_scale | sub_gamma_t_scale | joint_best_thickness_um | joint_mean_rmse | joint_max_rmse | joint_std_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 2 | 2 | 1 | 1 | 7.44 | 0.00174747 | 0.0021727 | 0.000601365 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 1.5 | 1.5 | 0.5 | 0.5 | 7.42 | 0.00174966 | 0.00217994 | 0.000608509 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 1 | 1 | 0.5 | 0.5 | 7.42 | 0.00175223 | 0.00216008 | 0.000576779 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 2 | 2 | 0.5 | 0.5 | 7.42 | 0.00175463 | 0.00220545 | 0.00063756 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 1.5 | 1.5 | 1 | 1 | 7.44 | 0.00175975 | 0.00216467 | 0.000572631 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 0.5 | 0.5 | 0.5 | 0.5 | 7.42 | 0.00176264 | 0.00214644 | 0.000542771 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 0.5 | 0.5 | 0.5 | 0.5 | 7.42 | 0.00176264 | 0.00214644 | 0.000542771 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 0.5 | 1 | 0.5 | 1 | 7.42 | 0.00176315 | 0.00220765 | 0.000628613 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 0.5 | 2 | 0.5 | 2 | 7.4 | 0.00177148 | 0.0021097 | 0.000478307 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 0.5 | 1.5 | 0.5 | 1.5 | 7.42 | 0.0017722 | 0.00227708 | 0.000714004 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 1 | 1.5 | 1 | 1.5 | 7.44 | 0.00177733 | 0.00221435 | 0.000618041 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 1 | 1 | 1 | 1 | 7.44 | 0.00178038 | 0.00216366 | 0.000542031 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 1 | 1 | 1 | 1 | 7.44 | 0.00178038 | 0.00216366 | 0.000542031 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 1 | 2 | 1 | 2 | 7.44 | 0.00178143 | 0.00227235 | 0.000694264 |
| layer_shared_scale | 外延层与衬底分别缩放，且每层内 $\Gamma_L$ 与 $\Gamma_T$ 同比例缩放。 | 2 | 2 | 1.5 | 1.5 | 7.46 | 0.00178663 | 0.00222585 | 0.000621143 |
| lt_shared_scale | 全局缩放 $\Gamma_L$ 与 $\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。 | 1 | 0.5 | 1 | 0.5 | 7.44 | 0.0017898 | 0.00212024 | 0.000467314 |

## 厚度低谷出现频次

| mode | joint_best_thickness_um | count |
| --- | --- | --- |
| layer_shared_scale | 7.42 | 4 |
| layer_shared_scale | 7.44 | 4 |
| layer_shared_scale | 7.46 | 4 |
| layer_shared_scale | 7.48 | 4 |
| lt_shared_scale | 7.44 | 4 |
| lt_shared_scale | 7.46 | 4 |
| lt_shared_scale | 7.48 | 4 |
| lt_shared_scale | 7.42 | 3 |
| lt_shared_scale | 7.4 | 1 |

## 解释

- $\Gamma_L$ 与 $\Gamma_T$ 控制晶格振动项的线宽，主要影响吸收带附近的谱线形状。
- 如果声子阻尼缩放后厚度低谷仍集中，说明厚度识别主要来自条纹相位，而不是某个声子阻尼参数偶然造成。
- 如果低谷明显漂移，说明当前 Dong/TMM 模型对 Reststrahlen 区或阻尼参数仍较敏感，论文中必须降低结论强度。
- 该结果仍不能替代最终联合拟合，因为真实样品的 $\Gamma_L,\Gamma_T$ 未知，且波段选择尚未系统比较。