---
type: method-node
method: VMD-LSP频域分解
project: 碳化硅外延层厚度确定研究
---

# VMD-LSP频域分解

## 它解决什么问题

Sun et al. 2023 提到用 VMD-LSP 处理 epi-wafer 红外干涉谱。它的目标是从复杂谱线中分离出与不同层厚度相关的频率成分。

相关节点：[[FFT频域厚度初值]]、[[滑窗FFT与波段筛选]]

## 方法拆解

VMD 是 Variational Mode Decomposition，用于把信号分解成若干窄带模态。LSP 是 Lomb-Scargle periodogram，适合非均匀采样或不规则信号的周期估计。

可以理解为：

$$
\text{复杂反射谱}
\rightarrow
\text{若干频率模态}
\rightarrow
\text{每个模态估计周期}
\rightarrow
\text{换算厚度}.
$$

## 本项目当前怎么用

尚未实现 VMD-LSP。当前只实现了简化版 [[FFT频域厚度初值]]，用于先做真实性检查。

## 后续怎么实现

如果 FFT 发现主频混叠或多峰明显，可以再考虑 VMD-LSP。实现前必须精读 Sun2023，不能凭名称编造参数。

## 风险

VMD 的模态数、惩罚参数和停止条件会影响结果；若没有清楚记录，容易变成不可复现调参。
