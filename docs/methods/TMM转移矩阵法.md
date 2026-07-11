---
type: method-node
method: TMM转移矩阵法
project: 碳化硅外延层厚度确定研究
---

# TMM转移矩阵法

## 它解决什么问题

TMM 用矩阵描述多层薄膜中电磁波的传播、反射和透射。它比简单 Airy 模型更适合扩展到多层、吸收、复折射率和偏振。

相关节点：[[Airy多光束干涉模型]]、[[Lorentz-Drude介电函数模型]]、[[多角度联合拟合与仿射校准]]

## 核心对象

每层材料用复折射率表示：

$$
\tilde n(\nu)=n(\nu)+ik(\nu).
$$

每层都有相位厚度：

$$
\delta_j=\frac{2\pi}{\lambda}\tilde n_j d_j\cos\theta_j.
$$

多层结构通过矩阵相乘得到整体反射系数。

## 本项目怎么用

当前项目使用的是 Airy/TMM 思路的单层外延层模型：

$$
\text{air}
\rightarrow
\text{SiC epilayer}
\rightarrow
\text{SiC substrate}.
$$

光学常数由 [[Lorentz-Drude介电函数模型]] 提供。

## 当前结论

Dong/TMM 路线给出当前最强候选区间：

$$
d\approx7.4\text{--}7.6\ \mu m.
$$

但 [[残差诊断]] 显示模型仍有结构性误差，因此 TMM 不是已经闭合的最终答案。
