---
type: method-node
method: Cauchy与Sellmeier色散模型
project: 碳化硅外延层厚度确定研究
---

# Cauchy与Sellmeier色散模型

## 它解决什么问题

Cauchy 和 Sellmeier 模型用较少参数描述透明区折射率随波长变化。官方 B157 可见 Cauchy 色散模型关键词，因此它是优秀论文中常见的经验色散路线。

相关节点：[[色散修正FOD]]、[[Lorentz-Drude介电函数模型]]、[[TMM转移矩阵法]]

## Cauchy 形式

常见形式为：

$$
n(\lambda)=A+\frac{B}{\lambda^2}+\frac{C}{\lambda^4}.
$$

## Sellmeier 形式

典型形式为：

$$
n^2(\lambda)=1+\sum_j\frac{B_j\lambda^2}{\lambda^2-C_j}.
$$

## 本项目怎么用

当前尚未正式实现 Cauchy/Sellmeier 拟合。它们可以作为：

- 透明区的经验对照模型；
- [[FFT频域厚度初值]] 的 $n_{\mathrm{eff}}$ 来源之一；
- [[TMM转移矩阵法]] 的简化材料模型。

## 风险

SiC 红外区包含强声子响应和自由载流子效应，Cauchy/Sellmeier 不一定适合强吸收或 Reststrahlen 区。最终主模型仍应优先使用 [[Lorentz-Drude介电函数模型]]。
