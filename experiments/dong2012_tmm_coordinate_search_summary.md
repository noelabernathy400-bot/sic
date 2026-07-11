# Dong/TMM 分阶段坐标搜索摘要

本输出用于探索 Dong/TMM 材料参数联合变化时厚度低谷是否仍稳定。它不是最终全局优化结果，而是可解释的分阶段坐标搜索。

## 搜索设计

- 波段固定为 $1500\text{--}4000\ cm^{-1}$，这是前面波段敏感性中误差较低且稳定的高波数区。
- 厚度搜索区间为 $7.0\text{--}7.8\ \mu m$，步长约 $0.01\ \mu m$。
- 第一阶段固定全部参数，得到 baseline。
- 第二阶段只搜索外延层/衬底的 $\nu_p$ 缩放。
- 第三阶段在第二阶段最优基础上搜索外延层/衬底的 $\gamma$ 缩放。
- 第四阶段在第三阶段最优基础上搜索外延层/衬底的 $\Gamma_L,\Gamma_T$ 同比例缩放。
- 每个角度允许独立线性标定 $R_{\mathrm{obs}}\approx aR_{\mathrm{model}}+b$。
- 该方法是顺序坐标搜索，结果依赖阶段顺序，不能当作全局最优。

## 每阶段被选中的参数

| stage | candidate_id | epi_nu_p_scale | sub_nu_p_scale | epi_gamma_scale | sub_gamma_scale | epi_gamma_l_scale | epi_gamma_t_scale | sub_gamma_l_scale | sub_gamma_t_scale | joint_best_thickness_um | joint_mean_rmse | joint_max_rmse | joint_std_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7.44 | 0.00178228 | 0.00216602 | 0.000542685 |
| plasma | 9 | 1.5 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7.45 | 0.00177225 | 0.00214372 | 0.000525337 |
| drude_gamma | 12 | 1.5 | 1 | 2 | 0.5 | 1 | 1 | 1 | 1 | 7.44 | 0.00174974 | 0.00217989 | 0.000608326 |
| phonon_layer | 14 | 1.5 | 1 | 2 | 0.5 | 2 | 2 | 1.5 | 1.5 | 7.46 | 0.00173941 | 0.00220597 | 0.000659822 |

## 误差改善

| baseline_joint_mean_rmse | final_joint_mean_rmse | absolute_improvement | relative_improvement_pct |
| --- | --- | --- | --- |
| 0.00178228 | 0.00173941 | 4.28688e-05 | 2.40528 |

## 最终阶段单角度低谷

| stage | candidate_id | epi_nu_p_scale | sub_nu_p_scale | epi_gamma_scale | sub_gamma_scale | epi_gamma_l_scale | epi_gamma_t_scale | sub_gamma_l_scale | sub_gamma_t_scale | dataset | angle_deg | best_thickness_um | best_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phonon_layer | 14 | 1.5 | 1 | 2 | 0.5 | 2 | 2 | 1.5 | 1.5 | SiC_10deg | 10 | 7.48 | 0.00115423 |
| phonon_layer | 14 | 1.5 | 1 | 2 | 0.5 | 2 | 2 | 1.5 | 1.5 | SiC_15deg | 15 | 7.42 | 0.00191729 |

## 解释

- 如果分阶段搜索后 $d$ 仍停留在 $7.4\text{--}7.6\ \mu m$ 附近，说明联合参数调整没有轻易推翻当前候选区间。
- 如果误差改善很小，说明当前 baseline 已经较难通过这些粗网格缩放显著改进。
- 如果某一阶段改变参数后 $d$ 明显漂移，论文中必须把该参数列为主要不确定性来源。
- 本轮只使用粗缩放网格，下一步若要收敛到可报告参数，需要更细网格或连续优化。