---
type: method-note
project: 碳化硅外延层厚度确定研究
created: 2026-05-03
status: draft
---

# Airy/TMM 全谱拟合建模与调试

## 1. 本节要解决什么

前面的标准峰距法、FOD 拟合法和色散 FOD 都只利用极值位置。它们能给厚度初值，也能暴露折射率、波段、峰谷识别的敏感性，但它们没有利用整条反射率曲线的形状。

下一步需要建立全谱模型，让模型同时解释：

- 干涉条纹位置；
- 反射率振幅；
- 多角度数据；
- 色散折射率 $n(\nu)$；
- 吸收虚部 $k(\nu)$；
- 薄膜与衬底之间的光学差异。

当前目标不是马上给最终厚度，而是建立一个可调试的 Airy/TMM 最小模型。

## 2. 建模思想

把样品简化为空气 / 外延层 / 衬底三层结构：

```text
air -> epilayer -> substrate
```

记：

| 符号 | 含义 |
| --- | --- |
| $\nu$ | 波数，单位 $\mathrm{cm}^{-1}$ |
| $\lambda_0$ | 真空波长，单位 $\mu\mathrm{m}$ |
| $d$ | 外延层厚度，单位 $\mu\mathrm{m}$ |
| $\theta_0$ | 空气中的入射角 |
| $\theta_1$ | 外延层内折射角 |
| $\tilde n_1(\nu)$ | 外延层复折射率，$\tilde n_1=n_1+i k_1$ |
| $\tilde n_2(\nu)$ | 衬底复折射率，$\tilde n_2=n_2+i k_2$ |
| $R(\nu;d)$ | 模型预测反射率 |

波数和真空波长的关系为：

$$
\lambda_0=\frac{10000}{\nu}
$$

因为 $\nu$ 的单位是 $\mathrm{cm}^{-1}$，而 $\lambda_0$ 使用 $\mu\mathrm{m}$，所以有 `10000` 的换算因子。

## 3. 相位厚度

外延层中一次往返对应的相位由下式控制：

$$
\delta(\nu,d)=\frac{2\pi}{\lambda_0}\tilde n_1(\nu)d\cos\theta_1(\nu)
=\frac{2\pi}{10000}\tilde n_1(\nu)d\cos\theta_1(\nu)\nu
$$

这里 $\delta$ 是单程相位厚度。干涉条纹的位置主要由 $\delta$ 随 $\nu$ 的变化速度决定。

FOD 模型只用了近似关系：

$$
\Delta m \approx \frac{2d}{10000}\left[g(\nu_a)-g(\nu_b)\right],
\quad
g(\nu)=n(\nu)\nu\cos\theta_1(\nu)
$$

TMM/Airy 模型则直接计算整个反射率 $R(\nu;d)$。

## 4. Fresnel 系数

对每个界面，需要计算 s 偏振和 p 偏振的反射系数。若第 $i$ 层到第 $j$ 层，则：

$$
r_{ij}^{(s)}
=
\frac{\tilde n_i\cos\theta_i-\tilde n_j\cos\theta_j}
{\tilde n_i\cos\theta_i+\tilde n_j\cos\theta_j}
$$

$$
r_{ij}^{(p)}
=
\frac{\tilde n_j\cos\theta_i-\tilde n_i\cos\theta_j}
{\tilde n_j\cos\theta_i+\tilde n_i\cos\theta_j}
$$

折射角由 Snell 定律给出：

$$
\tilde n_i\sin\theta_i=\tilde n_j\sin\theta_j
$$

在代码中通常不直接求 $\theta_j$，而是求：

$$
\cos\theta_j
=
\sqrt{1-\left(\frac{\tilde n_0\sin\theta_0}{\tilde n_j}\right)^2}
$$

## 5. 单层 Airy 反射率

空气 / 外延层 / 衬底的单层反射振幅可写成：

$$
r(\nu;d)
=
\frac{r_{01}+r_{12}\exp(2i\delta)}
{1+r_{01}r_{12}\exp(2i\delta)}
$$

反射率为：

$$
R(\nu;d)=|r(\nu;d)|^2
$$

若题目光源未区分偏振，可以先使用非偏振平均：

$$
R_{\mathrm{unpol}}(\nu;d)
=
\frac{1}{2}\left(R_s(\nu;d)+R_p(\nu;d)\right)
$$

## 6. 为什么需要调试

这个模型比 FOD 更接近物理，但也更容易出错。至少要调试以下问题：

| 检查项 | 为什么重要 |
| --- | --- |
| 单位换算 | $\nu$ 是 $\mathrm{cm}^{-1}$，$d$ 是 $\mu\mathrm{m}$，相位里必须除以 `10000` |
| 角度修正 | 10 度、15 度数据必须通过 Snell 定律进入模型 |
| 复折射率 | $\tilde n=n+ik$ 中 $k$ 会影响振幅和条纹可见度 |
| 层间光学差异 | 若 $\tilde n_1=\tilde n_2$，薄膜和衬底没有光学界面，厚度不应可识别 |
| 振幅标定 | 附件反射率可能有仪器尺度偏移，全谱拟合不能只看绝对振幅 |
| 多角度一致性 | 同一块样品的 10 度和 15 度应反推出同一厚度 |

## 7. 最小调试策略

第一版 Python 调试模型只做三件事：

1. **同质界面检查**：令 $\tilde n_1=\tilde n_2$，预测曲线应几乎不随 $d$ 变化。
2. **人工折射率差检查**：令 $\tilde n_2=\tilde n_1+\Delta n$，检查厚度变化是否会移动干涉条纹。
3. **网格搜索检查**：在候选厚度区间内搜索 $d$，只用于检查代码链条，不作为最终厚度。

拟合时先允许一个线性标定：

$$
R_{\mathrm{obs}}(\nu)\approx a R_{\mathrm{model}}(\nu;d)+b
$$

其中 $a$ 和 $b$ 用最小二乘求得。这样做不是最终物理模型，而是为了先检查条纹相位是否对得上，避免仪器反射率标定误差直接压倒厚度信息。

## 8. 当前不能下的结论

在没有精读 Dong2012、没有合适的 4H-SiC 介电函数、没有处理外延层和衬底载流子浓度差异之前，TMM 调试结果不能写成最终厚度。

当前 TMM/Airy 只回答：

- 代码中的相位和单位是否正确；
- 厚度搜索流程是否能工作；
- 哪些假设会让厚度不可识别；
- 后续真正全谱拟合需要哪些参数。

