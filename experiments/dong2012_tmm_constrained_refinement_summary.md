# Dong/TMM 有 $\nu_p$ 物理边界的局部细化

## 研究方向自检

本脚本不是新增模型路线，而是给上一轮局部细化补上物理边界。它验证的问题是：当 $\nu_p$ 被限制在载流子浓度合理范围内时，厚度低谷是否仍然稳定。

$$
\text{物理边界} \rightarrow \text{局部优化} \rightarrow \text{厚度稳定性检查}
$$

## 边界设置

本轮只给 $\nu_p$ 设置物理边界，其他缩放因子沿用上一轮局部细化的数值边界。

$$
s_{\nu_p,\mathrm{epi}}\in[0.75,1.75],
\qquad
s_{\nu_p,\mathrm{sub}}\in[0.75,1.25].
$$

对应的载流子浓度范围约为：

$$
N_{\mathrm{epi}}\in[9.20\times10^{16},5.01\times10^{17}]\ \mathrm{cm}^{-3},
$$

$$
N_{\mathrm{sub}}\in[2.45\times10^{18},6.81\times10^{18}]\ \mathrm{cm}^{-3}.
$$

## 与无边界局部细化的比较

| 口径 | $d^\ast$ | joint RMSE | max angle RMSE | 说明 |
| --- | --- | --- | --- | --- |
| 初始坐标搜索状态 | $7.455\ \mu m$ | `0.00173772` | `0.00191729` | 受约束细化起点 |
| 有 $\nu_p$ 边界局部细化 | $7.465\ \mu m$ | `0.00171152` | `0.00188375` | 本轮结果 |
| 无 $\nu_p$ 专门边界局部细化 | $7.465\ \mu m$ | `0.00171152` | `0.00188375` | 上一轮结果 |

相对初始状态，本轮绝对 RMSE 改善为：

$$
\Delta\mathrm{RMSE}=0.00002620,
\qquad
\frac{\Delta\mathrm{RMSE}}{\mathrm{RMSE}_0}=1.508\%.
$$

## 最终参数边界状态

| 参数 | 数值 | 边界状态 |
| --- | --- | --- |
| `epi_nu_p_scale` | `1.750000` | `upper` |
| `sub_nu_p_scale` | `1.000000` | `interior` |
| `epi_gamma_scale` | `2.500000` | `upper` |
| `sub_gamma_scale` | `0.100000` | `lower` |
| `epi_gamma_l_scale` | `2.125000` | `interior` |
| `epi_gamma_t_scale` | `2.125000` | `interior` |
| `sub_gamma_l_scale` | `1.875000` | `interior` |
| `sub_gamma_t_scale` | `1.875000` | `interior` |

## 分角度结果

| 数据 | $d^\ast$ | RMSE | affine scale | affine offset |
| --- | --- | --- | --- | --- |
| SiC_10deg | $7.490\ \mu m$ | `0.00112873` | `1.005375` | `-0.005385` |
| SiC_15deg | $7.430\ \mu m$ | `0.00188375` | `1.068155` | `-0.008718` |

## 解释

本轮最关键的信息不是 RMSE 又降低了一点，而是有边界条件下厚度低谷仍然没有离开当前候选区间。

$$
d^\ast\approx7.465\ \mu m.
$$

但外延层 $s_{\nu_p,\mathrm{epi}}$ 触及上界 $1.75$。这说明当前数据仍倾向于更强的外延层 Drude 项；为了保持科学谨慎，论文中不能把该点写成内部最优参数，只能写成“在候选物理边界内的边界最优状态”。

因此，当前厚度结论可以继续保留为：

$$
d\approx7.4\text{--}7.6\ \mu m,
$$

而不是直接收缩成一个无条件最终厚度。
