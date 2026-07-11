---
type: method-node
method: Lorentz-Drude介电函数模型
project: 碳化硅外延层厚度确定研究
---

# Lorentz-Drude介电函数模型

## 它解决什么问题

SiC 在红外区受到声子振动和自由载流子影响，折射率不能随便取常数。Lorentz-Drude 模型用物理参数描述介电函数，再转成 $n(\nu),k(\nu)$。

相关节点：[[TMM转移矩阵法]]、[[坐标搜索局部细化与物理约束优化]]、[[Cauchy与Sellmeier色散模型]]

## 核心公式

Dong2012 风格的垂直分量介电函数可写成：

$$
\varepsilon_\perp(\nu)
=
\varepsilon_{\infty,\perp}
\left[
\frac{\nu_{L,\perp}^2-\nu^2-i\Gamma_L\nu}
{\nu_{T,\perp}^2-\nu^2-i\Gamma_T\nu}
-
\frac{\nu_{p,\perp}^2}
{\nu(\nu+i\gamma)}
\right].
$$

再由

$$
\tilde n(\nu)=\sqrt{\varepsilon(\nu)}
$$

得到复折射率。

## 本项目怎么用

项目把 Dong2012 表 2 参数转成 Python，随后对：

$$
\nu_p,\quad \gamma,\quad \Gamma_L,\quad \Gamma_T
$$

做敏感性分析、坐标搜索和受约束优化。

## 当前关键发现

当前受约束优化中，外延层

$$
s_{\nu_p,\mathrm{epi}}=1.75
$$

触及候选上界。这意味着模型倾向于把 Drude 项推强，但不能把该边界值解释为真实材料参数。

## 风险

Dong2012 参数来自文献样品，不是本题样品。后续必须结合 Chahal2024 等近年 4H-SiC 红外介电性质资料补充物理边界。
