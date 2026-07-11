# $\nu_p$ 物理边界与载流子浓度换算

## 研究方向自检

本轮工作只解决一个模型问题：当前 Dong/TMM 模型对 $\nu_p$ 最敏感，而 $\nu_p$ 又不能作为任意数值参数自由扩张。因此需要把 $\nu_p$ 换算为载流子浓度 $N$，给下一轮受约束优化提供物理边界。

它服务于当前主线：

$$
\text{题目数据}\rightarrow \text{物理参数约束}\rightarrow \text{受约束 TMM 优化}\rightarrow \text{厚度可信度}
$$

## 资料来源

- Dong et al. 2012，题名为 *Characterization of 4H-SiC substrates and epilayers by Fourier transform infrared reflectance spectroscopy*，DOI 为 $10.1088/1674\text{-}1056/21/4/047802$。本项目已保存 Crossref 元数据和本地 PDF/抽取文本。
- 本轮只使用 Dong2012 中已经在本地精读笔记记录的 Eq. (2) 和 Table 2 数值，不新增未经核验的外部文献结论。
- PDF 抽取文本存在符号乱码风险；正式论文引用前仍应对照 PDF 页面截图复核公式排版。

## 模型关系

Dong2012 给出的关系可以整理为：

$$
\nu_{p,\perp}
=
\frac{1}{2\pi c}
\sqrt{
\frac{Nq^2}
{m_{\perp}^{*}\varepsilon_0\varepsilon_{\infty,\perp}}
}
$$

反解得到：

$$
N
=
\frac{(2\pi c\nu_{p,\perp})^2
m_{\perp}^{*}\varepsilon_0\varepsilon_{\infty,\perp}}
{q^2}
$$

因此如果把等离子体频率写成缩放形式

$$
\nu_{p,\perp}=s_{\nu_p}\nu_{p,0},
$$

则载流子浓度随缩放因子平方变化：

$$
N(s_{\nu_p})=s_{\nu_p}^{2}N_0.
$$

这一步非常重要，因为它说明 $s_{\nu_p}=2$ 不是“参数翻倍”那么轻，而是把载流子浓度放大到 $4$ 倍。

## 换算基准

当前脚本使用：

$$
\varepsilon_{\infty,\perp}=6.56,
\qquad
m_{\perp}^{*}=0.42m_0.
$$

由 Dong2012 表 2 中的 $\nu_{p,\perp}$ 换算得到：

$$
N_{\mathrm{epi},0}\approx 1.636e+17\ \mathrm{cm}^{-3},
\qquad
N_{\mathrm{sub},0}\approx 4.356e+18\ \mathrm{cm}^{-3}.
$$

这与 Dong2012 Table 2 中外延层约 $1.6\times10^{17}\ \mathrm{cm}^{-3}$、衬底约 $4.4\times10^{18}\ \mathrm{cm}^{-3}$ 的红外拟合结果一致，说明本项目代码中的单位换算是自洽的。

## 当前参数场景换算表

| layer | scenario | nu_p_scale | nu_p_perp_cm_inv | carrier_concentration_cm3 | relative_to_baseline_n |
| --- | --- | --- | --- | --- | --- |
| 外延层 | Dong2012 other method (Hg-probe C-V) | 0.7334 | 53.525 | 8.800e+16 | 0.538 |
| 衬底 | Dong2012 other method (Hall measurement) | 1.0713 | 403.459 | 5.000e+18 | 1.148 |
| 外延层 | Dong2012 Table 2 baseline | 1.0000 | 72.980 | 1.636e+17 | 1.000 |
| 外延层 | nu_p sensitivity RMSE-best | 1.5000 | 109.470 | 3.681e+17 | 2.250 |
| 外延层 | local refinement final | 1.7500 | 127.715 | 5.010e+17 | 3.062 |
| 外延层 | provisional constrained lower | 0.7500 | 54.735 | 9.202e+16 | 0.562 |
| 外延层 | provisional constrained upper | 1.7500 | 127.715 | 5.010e+17 | 3.062 |
| 衬底 | Dong2012 Table 2 baseline | 1.0000 | 376.600 | 4.356e+18 | 1.000 |
| 衬底 | nu_p sensitivity RMSE-best | 1.0000 | 376.600 | 4.356e+18 | 1.000 |
| 衬底 | local refinement final | 1.0000 | 376.600 | 4.356e+18 | 1.000 |
| 衬底 | provisional constrained lower | 0.7500 | 282.450 | 2.450e+18 | 0.562 |
| 衬底 | provisional constrained upper | 1.2500 | 470.750 | 6.807e+18 | 1.562 |

## 对当前模型的约束建议

下一轮受约束优化可以先采用候选边界：

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

这组边界的含义不是“本题样品真实浓度已经确定”，而是：

1. 它覆盖 Dong2012 红外结果和其他方法对照值的同量级范围；
2. 它包含当前本题数据的 $\nu_p$ 敏感性 RMSE 最小点；
3. 它包含局部细化得到的外延层 $s_{\nu_p}=1.75$；
4. 它不允许继续无依据地把 $\nu_p$ 放大到非常高的载流子浓度，从而避免数值优化只追 RMSE。

## 不能下的结论

本轮不能写：

> 本题样品外延层载流子浓度就是 $5.01\times10^{17}\ \mathrm{cm}^{-3}$。

更准确的写法是：

> 根据 Dong2012 的 $\nu_p$-$N$ 关系，当前局部细化中的外延层 $s_{\nu_p}=1.75$ 等价于把 Dong2012 外延层基准载流子浓度放大到约 $5.01\times10^{17}\ \mathrm{cm}^{-3}$。由于本题未提供独立电学测量，该数值只能作为受约束优化中的候选参数状态，而不是样品真实掺杂结论。

## 下一步

最有价值的下一步是把上面的 $s_{\nu_p}$ 边界接入 Dong/TMM 局部优化脚本，重新比较：

$$
\text{无物理边界局部细化}
\quad\text{vs.}\quad
\text{有 }\nu_p\text{ 物理边界的局部细化}
$$

评价指标不只看联合 RMSE，还要看：

$$
d^\ast,\quad
\mathrm{RMSE}_{10^\circ},\quad
\mathrm{RMSE}_{15^\circ},\quad
\text{是否触及边界},\quad
\text{残差是否集中在特定波段}.
$$
