---
type: method-node
method: 色散修正FOD
project: 碳化硅外延层厚度确定研究
---

# 色散修正FOD

## 它解决什么问题

[[峰谷级次差法FOD]] 假设折射率是常数，但 SiC 在红外区的折射率和消光系数会随波数变化。色散修正 FOD 把 $n$ 改成 $n(\nu)$，让相位差模型更贴近材料事实。

相关节点：[[Cauchy与Sellmeier色散模型]]、[[Lorentz-Drude介电函数模型]]、[[FFT频域厚度初值]]

## 核心公式

定义相位因子：

$$
g(\nu)=n(\nu)\sqrt{1-\left(\frac{\sin\theta}{n(\nu)}\right)^2}\nu.
$$

同类极值之间的级次差可以用

$$
\Delta p
\approx
\frac{2d}{10000}\left[g(\nu_{\mathrm{ref}})-g(\nu)\right]
$$

来做最小二乘拟合。

## 本项目怎么用

项目使用 Larruquert SiC 光学常数表插值得到 $n(\nu),k(\nu)$，再做色散修正 FOD。结果显示 SiC 厚度估计明显低于常数 $n=2.60$ 的 FOD。

这说明一个关键事实：

$$
\text{厚度估计对折射率模型非常敏感。}
$$

## 风险

Larruquert 数据不一定就是本题 4H-SiC 外延层的真实光学常数。它只能作为可复现的外部 $n,k$ 输入，不能当成样品真实参数。

## 当前作用

它的作用是提醒我们：最终模型必须显式处理材料折射率，而不是固定一个常数。
