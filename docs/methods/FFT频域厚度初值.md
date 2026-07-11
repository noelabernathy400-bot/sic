---
type: method-node
method: FFT频域厚度初值
project: 碳化硅外延层厚度确定研究
---

# FFT频域厚度初值

## 它解决什么问题

FFT 频域厚度初值把反射率谱中的条纹看作波数域里的周期信号，用主频估计厚度。它是 [[TMM转移矩阵法]] 之外的一条独立真实性检查。

相关节点：[[VMD-LSP频域分解]]、[[滑窗FFT与波段筛选]]、[[峰谷级次差法FOD]]

## 核心公式

如果主频为 $f$，单位是 cycles per $\mathrm{cm}^{-1}$，则波数周期为：

$$
\Delta\nu=\frac{1}{f}.
$$

用有效折射率 $n_{\mathrm{eff}}$ 换算厚度：

$$
d_{\mathrm{FFT}}
\approx
\frac{10000 f}
{2\sqrt{n_{\mathrm{eff}}^2-\sin^2\theta}}.
$$

## 本项目怎么用

新增脚本：

```text
Code/fft_frequency_seed.py
```

它做了：

- 等间隔波数重采样；
- 去趋势；
- Hanning 窗；
- FFT 主频查找；
- 用不同 $n_{\mathrm{eff}}$ 口径换算厚度。

## 当前发现

FFT 主周期非常稳定：

$$
\Delta\nu\approx250\ \mathrm{cm}^{-1}.
$$

但厚度换算强烈依赖 $n_{\mathrm{eff}}$：

- Larruquert $n_{\mathrm{eff}}\approx3.07$ 时，厚度约 $6.5\ \mu m$。
- 常数 $n=2.60$ 时，厚度约 $7.7\ \mu m$。
- 当前 Dong 受约束模型的 $n_{\mathrm{eff}}\approx2.48$ 时，厚度约 $8.0\ \mu m$。

这说明：

$$
\text{条纹主周期稳定}
\neq
\text{厚度已经唯一确定}.
$$

## 对当前模型的影响

它没有直接支持 $7.465\ \mu m$，反而暴露出更深的问题：TMM 的厚度低谷不是简单主周期公式能解释的，可能还受到全谱线型、材料吸收、仿射校准、多光束和相位模型影响。

这不是坏消息，是重要真实性检查。
