# 数学模型推导：色散 FOD 与 Si 厚度复核

## 这份笔记解决什么问题

这份笔记只写本轮已经实现的数学模型，不写还没实现的 TMM / Airy 全谱模型。

本轮模型目标：

- 用附件反射率曲线中的峰/谷位置估计外延层厚度。
- 将 SiC 的常数折射率模型升级为色散折射率模型。
- 用同一 FOD 框架复核 Si 厚度是否能支持旧论文中的 $5.13\,\mu m$。

## 1. 符号定义

| 符号 | 含义 | 单位 |
| --- | --- | --- |
| $\nu$ | 红外光波数 | $cm^{-1}$ |
| $\lambda$ | 波长 | $\mu m$ |
| $R(\nu)$ | 反射率 | $\%$ |
| $d$ | 外延层厚度 | $\mu m$ |
| $\theta_0$ | 空气中入射角 | 度或弧度 |
| $\theta_1$ | 外延层内折射角 | 度或弧度 |
| $n$ | 实部折射率 | 无量纲 |
| $k$ | 消光系数 | 无量纲 |
| $\tilde n=n+ik$ | 复折射率 | 无量纲 |
| $m$ | 干涉级次 | 无量纲 |

波长和波数的换算为：

$$
\lambda_{\mu m}=\frac{10000}{\nu_{cm^{-1}}}
$$

## 2. 折射角模型

假设入射介质为空气，折射率近似为 1。由 Snell 定律：

$$
\sin\theta_1=\frac{\sin\theta_0}{n}
$$

所以：

$$
\cos\theta_1=\sqrt{1-\left(\frac{\sin\theta_0}{n}\right)^2}
$$

如果使用色散折射率 $n(\nu)$，则折射角也随波数变化：

$$
\cos\theta_1(\nu)=\sqrt{1-\left(\frac{\sin\theta_0}{n(\nu)}\right)^2}
$$

## 3. 干涉相位与厚度

薄膜上下表面反射光的光程差近似为：

$$
\Delta L = 2dn\cos\theta_1
$$

换成以波数表示的干涉级次，可写成：

$$
p(\nu)=\frac{2dn\cos\theta_1\,\nu}{10000}+\phi
$$

其中 $\phi$ 是由反射相位、峰/谷类型等带来的常数项。本项目当前使用 FOD 方法，核心好处是通过“级次差”消去 $\phi$。

## 4. 相邻同类极值的峰距厚度公式

对于相邻两个同类极值，例如峰-峰或谷-谷，级次差为 1：

$$
\Delta p = 1
$$

若折射率近似为常数，则有：

$$
1=\frac{2dn\cos\theta_1\,\Delta\nu}{10000}
$$

因此厚度估计为：

$$
d=\frac{10000}{2n\cos\theta_1\,\Delta\nu}
$$

这就是 `baseline_thickness_intervals.csv` 中相邻同类极值厚度粗估的来源。

注意：如果混合使用峰-谷相邻极值，级次差通常是 $\frac{1}{2}$。当前代码为了避免混淆，峰和谷分开处理。

## 5. 常数折射率 FOD 模型

选择同一类极值序列：

$$
\nu_0,\nu_1,\ldots,\nu_q
$$

以最高波数极值作为参考点：

$$
\nu_{\mathrm{ref}}=\nu_q
$$

对于第 $i$ 个极值，定义相对级次差：

$$
\Delta m_i=q-i
$$

常数折射率模型下：

$$
\Delta m_i \approx \frac{2dn\cos\theta_1(\nu_{\mathrm{ref}}-\nu_i)}{10000}
$$

令：

$$
X_i=n(\nu_{\mathrm{ref}}-\nu_i)
$$

则：

$$
\Delta m_i \approx aX_i
$$

其中：

$$
a=\frac{2d\cos\theta_1}{10000}
$$

用最小二乘拟合 $a$：

$$
\hat a=\frac{\sum_i X_i\Delta m_i}{\sum_i X_i^2}
$$

再反推出厚度：

$$
\hat d=\frac{10000\hat a}{2\cos\theta_1}
$$

这就是 `fod_fit_results.csv` 的数学模型。

## 6. 色散修正 FOD 模型

常数折射率模型的问题是把 $n$ 当成不随波数变化。但 SiC 在红外波段存在色散，因此本轮引入：

$$
n=n(\nu), \qquad k=k(\nu)
$$

先定义色散相位因子：

$$
g(\nu)=n(\nu)\cos\theta_1(\nu)\nu
$$

其中：

$$
\cos\theta_1(\nu)=\sqrt{1-\left(\frac{\sin\theta_0}{n(\nu)}\right)^2}
$$

级次差模型变成：

$$
\Delta m_i \approx \frac{2d}{10000}\left[g(\nu_{\mathrm{ref}})-g(\nu_i)\right]
$$

令：

$$
X_i^{\mathrm{disp}}=g(\nu_{\mathrm{ref}})-g(\nu_i)
$$

则：

$$
\Delta m_i \approx bX_i^{\mathrm{disp}}
$$

其中：

$$
b=\frac{2d}{10000}
$$

最小二乘估计：

$$
\hat b=\frac{\sum_i X_i^{\mathrm{disp}}\Delta m_i}{\sum_i\left(X_i^{\mathrm{disp}}\right)^2}
$$

厚度估计为：

$$
\hat d=\frac{10000\hat b}{2}
$$

这就是本轮 `dispersion_fod_results.csv` 的数学模型。

## 7. Larruquert 光学常数插值模型

Larruquert 数据以波长 $\lambda$ 给出：

$$
(\lambda_j,n_j,k_j)
$$

先转换到波数：

$$
\nu_j=\frac{10000}{\lambda_j}
$$

再对任意极值位置 $\nu$ 进行线性插值：

$$
n(\nu)=\operatorname{InterpLinear}\{(\nu_j,n_j)\}
$$

$$
k(\nu)=\operatorname{InterpLinear}\{(\nu_j,k_j)\}
$$

本轮 FOD 相位拟合只使用 $n(\nu)$，而 $k(\nu)$ 暂时作为吸收诊断：

$$
\tilde n(\nu)=n(\nu)+ik(\nu)
$$

为什么不直接把 $k$ 塞进 FOD？因为 FOD 只利用峰/谷位置，主要对应相位条件；$k$ 更直接影响反射率幅值、峰谷清晰度和可用波段。后续 TMM / Airy 模型才会更自然地使用复折射率 $\tilde n(\nu)$。

## 8. 拟合优度

当前代码输出残差平方和：

$$
RSS=\sum_i\left(\Delta m_i-\widehat{\Delta m_i}\right)^2
$$

以及：

$$
R^2=1-\frac{\sum_i\left(\Delta m_i-\widehat{\Delta m_i}\right)^2}{\sum_i\left(\Delta m_i-\overline{\Delta m}\right)^2}
$$

这里的 $R^2$ 只说明“级次差线性拟合得好不好”，不能单独证明厚度就是最终真值。

## 9. Si 厚度复核模型

Si 当前仍使用常数折射率：

$$
n_{\mathrm{Si}}=3.42
$$

因此其 FOD 厚度仍按第 5 节计算。

为了检查旧论文的 $5.13\,\mu m$ 是否能由同一极值链条推出，本轮还做了一个反推问题：如果厚度固定为：

$$
d^\ast=5.13\,\mu m
$$

那么需要什么常数折射率 $n^\ast$ 才能满足 FOD 拟合？

也就是求解：

$$
d_{\mathrm{FOD}}(n^\ast)=5.13
$$

数值求解后得到：

$$
n^\ast\approx 2.27\sim 2.43
$$

这个值明显低于当前 Si 红外折射率基线 $3.42$，所以当前结论是：

$$
\text{旧论文的 }5.13\,\mu m\text{ 暂不被当前 FOD 链条支持。}
$$

这不是最终否定，而是说明：如果旧论文结果要成立，需要找到不同的峰谷识别、不同单位口径、不同折射率来源，或者更复杂的光学模型解释。

## 10. 本轮模型结论

本轮数学模型给出三点结论：

1. 常数折射率 FOD 是一个可解释的基线，但对参数和波段敏感。
2. 引入 Larruquert $n(\nu)$ 后，SiC 厚度从常数模型的约 $6.5\sim 7.3\,\mu m$ 降到约 $5.3\sim 5.9\,\mu m$。
3. Si 在当前 FOD 模型下稳定落在约 $3.4\sim 3.6\,\mu m$，旧论文 $5.13\,\mu m$ 暂时无法由同一链条推出。

## 11. 下一步要补的数学模型

下一步不是继续堆 FOD，而是建立可以直接拟合完整反射率曲线的模型：

$$
R_{\mathrm{model}}\left(\nu;d,n(\nu),k(\nu),\theta_0\right)
$$

也就是 Airy 或 TMM 模型。那时复折射率：

$$
\tilde n(\nu)=n(\nu)+ik(\nu)
$$

会进入 Fresnel 系数和薄膜传播相位，模型会比当前 FOD 更完整。
