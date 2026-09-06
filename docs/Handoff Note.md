---
type: project-handoff
project: 碳化硅外延层厚度确定研究
updated: 2026-05-04
---

# 项目交接说明

## 当前目标

接手用户已有的数学建模 B 题论文，判断结果是否可信，并提出可深挖的建模、实验、论文和可解释性方向。

> 2026-08-15 更新：已新增可独立编译的中英文论文交付件 `deliverables/SiC_FTIR_Thickness_Paper_2026-08-15/`。中文阅读稿明确补充了核心公式的短推导和符号说明；详见 `reports/2026-08-15_SiC论文交付报告.md`。随后生成综合版 `deliverables/SiC_FTIR_Thickness_Paper_Integrated_2026-08-15/`，保留新版的模型叙述并补入既有终稿的数据背景、预处理稳健性与滑窗 FFT；详见 `reports/2026-08-15_SiC论文综合版交付报告.md`。论文主张仍限定为 $7.4\text{--}7.6\ \mu m$ 的模型支持区间，而非外部认证真值。

## 已完成

- 已创建项目骨架。
- 已复制题目、已有论文和附件数据到 `Sources/`。
- 已阅读题目和已有论文的主要内容。
- 已形成初步诊断：论文有复折射率、多光束干涉、神经网络和 LM 等元素，但可信度链条仍弱。
- 已记录用户要求：后续代码全部使用 Python。
- 已运行 Python 初步数据诊断脚本：SiC 粗估约 6.5-6.9 $\mu m$，Si 粗估约 3.5 $\mu m$；Si 与论文 5.13 $\mu m$ 差异需要优先复核。
- 已完成第一轮资料扫描，文献按标准测厚、SiC FTIR 测厚、光学常数、TMM、多光束与可靠性分析分类。
- 已精读 Li2010，并据此建立新版论文总架构：标准峰距法 -> FOD 拟合 -> 色散修正 -> Airy/TMM 全谱拟合 -> 稳健性分析。
- 已建立 `Code/spectral_pipeline.py`，当前环境无需 matplotlib 即可生成 CSV 和 SVG。
- 代码已集中到 `Code/`，统一入口为 `Code/run_pipeline.py`。
- 已运行 pipeline，输出在 `Experiments/outputs/` 和 `Experiments/figures/`。
- 已发现并修正 FOD 级次口径问题：同类极值相邻为一级次，混合峰谷才是半级次。
- 用户要求进入“数学建模项目深挖模式”：不扩展到整个 vault，不浮躁推进，一段一段打磨，项目内容要能学习、消化、复用。
- 已写入项目级规则：`Notes/项目深挖工作规则.md`。
- 已完成第一组深挖笔记：`Notes/题目分析.md`、`Notes/问题拆解.md`、`Notes/模型路线对比.md`。
- 已完成第二组深挖笔记：`Notes/变量与假设.md`、`Notes/算法实现计划.md`。
- 已新增并运行 `Code/sensitivity_analysis.py`，输出 `Experiments/outputs/fod_sensitivity_summary.md`。
- 敏感性结果显示常数折射率 FOD 对平滑窗口、最小峰距和波段较敏感，暂不能作为最终结果。
- 已新增并运行 `Code/dispersion_analysis.py`，解析本地 Larruquert SiC `n,k` 数据，建立 $n(\nu), k(\nu)$ 线性插值，并将 SiC FOD 从常数折射率升级为色散修正 FOD。
- 色散 FOD 输出见 `Experiments/outputs/dispersion_fod_summary.md`、`dispersion_fod_results.csv`、`sic_larruquert_nk_sample.csv`。
- Si 厚度复核输出见 `Experiments/outputs/si_thickness_review.csv`：在当前 FOD 极值和 `n=3.42` 口径下，Si 厚度仍集中在约 3.4-3.6 $\mu m$；若强行达到旧论文 5.13 $\mu m$，需要约 2.27-2.43 的等效常数折射率，暂不被当前数据链条支撑。
- 已补充中文研究过程笔记 `Experiments/本轮研究过程记录-2026-05-03-色散FOD与Si复核.md`，用于学习模型、公式和数据流。
- 已补充 `Experiments/outputs/输出文件说明.md`，解释 outputs 下各文件含义；自动生成的 Markdown 摘要已改为中文。
- 已补充数学公式推导 `Methods/数学模型推导-色散FOD与Si复核.md`，明确常数折射率 FOD、色散 FOD、Larruquert 插值、最小二乘估计和 Si 等效折射率反推模型。
- 数学模型笔记已改为 Obsidian 可渲染的 LaTeX 符号格式，避免用代码变量替代数学符号。
- 已建立项目级多 agent 协作方案：`Notes/多Agent协作分工方案.md`。
- 已新增 `AgentWork/README.md` 和 `AgentWork/任务包模板.md`，用于保存子 agent 的可审查证据包。
- 已完成第一批多 agent 子任务，输出见 `AgentWork/审查任务-色散FOD输出复核-2026-05-03.md`、`AgentWork/数据任务-附件3和4硅厚度差异二审-2026-05-03.md`、`AgentWork/文献任务-Li2010之外核心文献核验-2026-05-03.md`。
- 主 agent 已写入接收报告：`AgentWork/主Agent接收报告-第一批-2026-05-03.md`。当前决策是：FOD/色散 FOD 只作为中间模型与可信度审查，下一步应进入 Dong2012 精读和 Airy/TMM 全谱拟合。
- 已新增 `AgentWork/外部Agent接入说明-2026-05-03.md`，用于把其他对话框中的 agent 通过文件证据包纳入主 agent 管理。
- 用户要求后续所有建模过程、调试过程和数学公式都必须写清楚，公式统一使用 LaTeX；该规则已写入 `Notes/项目深挖工作规则.md`。
- 已新增 `Notes/建模与调试过程记录.md`，用于记录模型思想、公式、代码检查、调试结果和不确定性。
- 已新增 `Methods/Airy_TMM全谱拟合建模与调试.md` 和 `Code/tmm_air_debug.py`；脚本已用 Codex bundled Python 运行成功，输出见 `Experiments/outputs/tmm_air_debug_summary.md`。
- TMM 当前只是最小调试模型：同质界面厚度敏感性为 0，人工折射率差下搜索约在 6.2-6.3 $\mu m$ 出现误差低谷，但该结果不能作为最终厚度。
- 用户进一步强调：研究过程是最重要的，需要像总总结一样详细记录全文思想，尤其不能省略数据处理、建模和调试；该要求已写入 `Notes/项目深挖工作规则.md` 的“总研究叙事规则”。
- 已新增 `Notes/研究过程总览.md`，串联从数据处理到 Dong/TMM 的当前完整研究链。
- 已下载真正的 Dong2012 PDF：`Sources/Literature/Dong2012_4H_SiC_FTIR.pdf`；第一次误下载的 HTML 已保存为 `Dong2012_4H_SiC_FTIR_pdf_access-page.html`。
- 已新增 `Literature/Dong2012精读与模型转化.md`，把 Dong2012 的介电函数、Airy 反射公式、可调参数和 EQS 思想转成 LaTeX 笔记。
- 已新增并运行 `Code/dong2012_dielectric_debug.py`，输出见 `Experiments/outputs/dong2012_dielectric_debug_summary.md`。用 Dong2012 表 2 参数调试本题 SiC 数据时，10 度/15 度误差低谷约在 7.4 $\mu m$ 附近；但该参数来自 Dong 样品，不能作为最终厚度。
- 已新增并运行 `Code/dong2012_tmm_sensitivity.py`，输出见 `Experiments/outputs/dong2012_tmm_sensitivity_summary.md`。缩放 Dong2012 等离子体频率时，联合低谷主要集中在 7.4-7.6 $\mu m$，说明当前 Dong/TMM 框架下厚度信号有一定稳定性，但仍需扩展敏感性和最终联合拟合。
- 已新增并运行 `Code/dong2012_tmm_gamma_sensitivity.py`，输出见 `Experiments/outputs/dong2012_tmm_gamma_sensitivity_summary.md`。缩放 Drude 阻尼 $\gamma$ 时，联合低谷稳定在 7.44-7.46 $\mu m$。
- 已新增 `Code/model_route_comparison.py`，输出 `Experiments/outputs/model_route_comparison_summary.md`，并新增方法笔记 `Methods/模型路线结果对比与可信度.md`。
- 当前最强候选表述：Dong/TMM 框架下，多角度联合低谷在 $\nu_p$ 敏感性中约为 7.44-7.58 $\mu m$，在 $\gamma$ 敏感性中约为 7.44-7.46 $\mu m$。仍不能写成最终厚度。
- 已新增 `Notes/数学符号与公式总表.md`，并把项目 Markdown 中主要数学符号统一为可渲染 LaTeX 口径。
- 已新增并运行 `Code/dong2012_tmm_phonon_sensitivity.py`，输出见 `Experiments/outputs/dong2012_tmm_phonon_sensitivity_summary.md`。两类 $\Gamma_L,\Gamma_T$ 敏感性设计下联合低谷约为 7.40-7.48 $\mu m$。
- 已新增并运行 `Code/dong2012_tmm_band_sensitivity.py`，输出见 `Experiments/outputs/dong2012_tmm_band_sensitivity_summary.md`。全部测试波段联合低谷约为 7.38-7.44 $\mu m$，不含 Reststrahlen 区的高波数波段约为 7.42-7.44 $\mu m$。
- 已新增并运行 `Code/dong2012_tmm_coordinate_search.py`，输出见 `Experiments/outputs/dong2012_tmm_coordinate_search_summary.md`。分阶段坐标搜索最终低谷为 7.46 $\mu m$，联合 RMSE 相比 baseline 改善约 2.4%；该结果是探索性优化，不是全局最优证明。
- 已新增并运行 `Code/dong2012_tmm_uncertainty.py`，输出见 `Experiments/outputs/dong2012_tmm_uncertainty_summary.md`。固定坐标搜索参数下，profile 最小值为 7.455 $\mu m$，残差块 bootstrap 分布集中在 7.445-7.465 $\mu m$ 左右。
- 已新增 `Writing/模型建立与结果分析草稿.md`，把当前模型路线和结果转成论文可写结构。
- 已新增 `Writing/论文初稿-2026-05-04.md`，作为当前阶段的完整论文基准稿。该稿不把 $7.455\ \mu m$ 写成最终厚度，而是把 $d\approx7.4\text{--}7.6\ \mu m$ 写成当前最强候选区间，并明确列出 Dong2012 参数迁移、连续联合优化、材料参数不确定性传播、各向异性/偏振和 Si 部分尚未闭合等问题。
- 已新增 `Code/paper_assets.py`，输出论文图表、参数表和图表计划；见 `Writing/论文图表与参数表计划-2026-05-04.md`、`Writing/论文参数表与结果表-2026-05-04.md`。
- 已新增 `Code/dong2012_tmm_bestfit_export.py`，输出 $d=7.455\ \mu m$ 固定参数代表值下的拟合谱线和残差；见 `Experiments/outputs/dong2012_tmm_bestfit_summary.md`。
- 已新增 `Code/dong2012_tmm_local_refinement.py`。在无 `scipy` 环境下做两轮局部坐标细化，最终 $d^\ast=7.465\ \mu m$、联合 RMSE 为 $0.00171152$，相对固定参数代表值改善约 $1.508\%$；但部分参数触及局部边界，不能写成全局最优。
- 已扩展 `Code/paper_assets.py`，新增参数敏感性 RMSE 热力图：`paper_fig10_rmse_heatmap_nu_p_sensitivity.svg`、`paper_fig11_rmse_heatmap_gamma_sensitivity.svg`、`paper_fig12_rmse_heatmap_phonon_sensitivity.svg`。当前判断是 $\nu_p$ 最敏感，下一步应优先为 $\nu_p$ 或载流子浓度建立物理合理边界。
- 已在 `Notes/项目深挖工作规则.md` 新增“研究方向自检规则”。后续每完成一组模型、实验、图表或论文内容，都要检查它是否服务于厚度反演模型的精度、稳定性、可解释性或论文表达；若不能说明价值，应停止扩展并回到建模主线。
- 已新增并运行 `Code/dong2012_plasma_boundary.py`，把 Dong2012 Eq. (2) 中 $\nu_p$ 与载流子浓度 $N$ 的关系转成可复现换算。输出见 `Experiments/outputs/dong2012_plasma_boundary_table.csv` 和 `Experiments/outputs/dong2012_plasma_boundary_summary.md`。
- 当前建议的 $\nu_p$ 受约束优化候选边界为 $s_{\nu_p,\mathrm{epi}}\in[0.75,1.75]$、$s_{\nu_p,\mathrm{sub}}\in[0.75,1.25]$。对应 $N_{\mathrm{epi}}\approx9.20\times10^{16}\text{--}5.01\times10^{17}\ \mathrm{cm}^{-3}$、$N_{\mathrm{sub}}\approx2.45\times10^{18}\text{--}6.81\times10^{18}\ \mathrm{cm}^{-3}$。这只是优化边界，不是本题样品真实掺杂结论。
- 已新增并运行 `Code/dong2012_tmm_constrained_refinement.py`，输出见 `Experiments/outputs/dong2012_tmm_constrained_refinement_summary.md`、`dong2012_tmm_constrained_refinement_chosen.csv` 和 `dong2012_tmm_constrained_refinement_final_angle_metrics.csv`。结果为 $d^\ast=7.465\ \mu m$、joint RMSE `0.00171152`；$10^\circ$ 单独最佳为 $7.490\ \mu m$，RMSE `0.00112873`；$15^\circ$ 单独最佳为 $7.430\ \mu m$，RMSE `0.00188375`。
- 有边界优化没有推翻 $7.4\text{--}7.6\ \mu m$ 候选区间，但外延层 $s_{\nu_p}=1.75$ 触及上界，因此不能写成内部最优材料参数，只能写成候选边界内的边界最优状态。
- 用户提醒“不能只用十年前方法，必须参考最近论文和获奖/优秀论文”。已分派并接收三类子 agent 报告，并写入主 agent 接收报告：`AgentWork/主Agent接收报告-近年资料与方法路线-2026-05-04.md`。
- 新增 `Literature/近年资料与官方优秀论文矩阵-2026-05-04.md`。当前官方资料包括 B060、B157、2025 B 题讲评，以及已补充核验的 2026-04-01 清华 B 题分享。清华分享是中国大学生在线站内“数模团队”视频页，来源/单位清华大学，作者张新晨、徐威南、周诗贺；它是学习线索，不等同于组委会官方讲评。官方资料只能在逐页 OCR、视频转写或人工核验后引用具体公式、图表或数值。
- 新增 `Methods/近年方法路线与Python实验优先级-2026-05-04.md`。下一步不应继续盲目扩大参数搜索，而应按“残差诊断 -> 频域初值 -> 折射率/介电函数统一 -> TMM 联合拟合 -> 全局优化”的顺序推进。
- 已新增并运行 `Code/residual_diagnostics.py`。输出见 `Experiments/outputs/residual_diagnostics_summary.md`、`residual_diagnostics_angle_metrics.csv`、`residual_diagnostics_band_metrics.csv`、`Experiments/figures/residual_diagnostics_angle_residuals.svg` 和 `residual_diagnostics_band_rmse.svg`。诊断显示 $15^\circ$ 残差显著强于 $10^\circ$，且两角残差一阶自相关都很高，说明当前模型仍有结构性误差。
- 已新增并运行 `Code/fft_frequency_seed.py`。FFT 主周期稳定为 $\Delta\nu\approx250\ \mathrm{cm}^{-1}$，但厚度换算依赖 $n_{\mathrm{eff}}$：Larruquert 口径约 $6.5\ \mu m$，常数 $n=2.60$ 口径约 $7.7\ \mu m$，Dong 受约束口径约 $8.0\ \mu m$。这说明频域检查支持“条纹周期稳定”，但不能直接证明 $7.4\text{--}7.6\ \mu m$。
- 用户新增要求“每个方法算法要成为单独文档并添加 Obsidian 双链”。已建立 `Methods/方法节点/方法节点索引.md` 和第一批方法节点，后续新方法也应按该格式新增独立笔记。
- 用户进一步指出需要“根本方法论”，不只是具体物理模型名。已新增 `Methods/方法论总览.md`，并补充数据处理、信号提取、物理正演、反问题求解、真实性验证、机器学习辅助六类根方法节点。特别说明：牛顿迭代尚未真正用于主结果；机器学习若使用，应具体落为仿真谱 MLP、1D-CNN、随机森林/XGBoost 特征回归、PCA/Autoencoder 异常检测或贝叶斯优化 surrogate。
- 用户追问“数据处理在哪里”。已新增并运行 `Code/data_processing_diagnostics.py` 与 `Code/sliding_fft_diagnostics.py`。结论是：全波段多种预处理均给出 $\Delta\nu=250\ \mathrm{cm}^{-1}$；滑窗 FFT 给出 $\Delta\nu\in[244.537,256.000]\ \mathrm{cm}^{-1}$。这说明数据中存在稳定条纹尺度，但频域厚度初值仍依赖 $n_{\mathrm{eff}}$，不能替代 Dong/TMM 最终解释。
- 已新增方法节点 [[预处理稳健性诊断]]，并把本轮记录写入 `Notes/研究过程总览.md` 与 `Notes/建模与调试过程记录.md`。下一步最值得做的是把滑窗 FFT 窗口结果与 `residual_diagnostics_band_metrics.csv` 对齐，判断残差高发波段来自数据处理问题还是物理模型缺项。
- 已按用户要求将具体预处理拆成独立方法节点：[[去均值中心化]]、[[移动平均去趋势]]、[[多项式去趋势]]、[[滚动中位数基线]]、[[滚动分位数基线]]、[[一阶差分预处理]]。
- 已新增并运行 `Code/residual_fft_alignment.py`。结果显示高残差且周期稳定波段数为 `1`，高残差且频域证据偏弱或周期不稳波段数为 `3`。这说明下一步不能只堆物理模型，也要考虑数据质量、吸收区、预处理和波段权重。
- 已新增并运行 `Code/band_weighted_tmm_profile.py`。固定当前受约束 Dong/TMM 参数、只改变波段权重时，$d^\ast\in[7.465,7.485]\ \mu m$，最大厚度位移为 $0.020\ \mu m$。这是一条稳健性旁证，不能写成最终置信区间。
- 用户指出论文初稿没有图。已新增并运行 `Code/manuscript_visual_assets.py`，生成双角度原始谱线合并图和研究证据链总览图；已新增 `Writing/论文图表嵌入清单-2026-05-04.md` 和 `Writing/论文图文版-2026-05-04.md`。下一位 agent 应优先以图文版论文为主入口继续打磨，不要回到无图纯文字稿。
- 用户进一步指出公式需要尽量有推导，方法和公式若来自论文必须标明来源并建立双链。已新增 `Writing/公式推导与来源索引-2026-05-04.md` 和 `Writing/引用与来源追踪表-2026-05-04.md`，并在 `Writing/论文图文版-2026-05-04.md` 增加“公式、方法与来源导航”及关键章节来源链接。下一位 agent 继续写论文时，必须保持“公式推导 + 来源双链 + 代码/输出追踪”三件套；未全文精读的近年论文只能写成学习线索。
- 用户追问图文版论文是否为最终论文，并指出部分图表/正文英文影响阅读。已明确：`Writing/论文图文版-2026-05-04.md` 是当前最完整论文基准稿，不是最终论文。已将主要 SVG 图表标题、坐标轴、图例、波段权重口径和正文表格中文化；保留 FFT、FOD、TMM、RMSE、Python、SVG、文件名等必要缩写。下一位 agent 不要再把代码口径直接写进正文表格，应使用中文解释名。
- 用户进一步要求“假设我一无所知，把研究过程当教科书来写”，并要求每个公式说明来源或推导、每一步说明意义、每张图说明如何阅读。已新增 `Notes/研究过程教科书版-2026-05-04.md`，作为后续用户学习主入口。下一位 agent 若继续写，应优先扩展这个文件，而不是直接继续堆论文正文。
- 用户反馈教科书版仍不够图文并茂，且学习材料不应像引用墙。已在 `Notes/研究过程教科书版-2026-05-04.md` 新增 0.5 图文导读，嵌入 9 张已有 SVG，并按“这张图回答什么、怎么看、支持什么、不能证明什么”讲解；已把“来源与追踪”改为“学习链接（想回查时再看）”。项目规则 `Notes/项目深挖工作规则.md` 已新增“教程式图文讲解规则”。下一位 agent 继续写教程时，应先讲明白，再附链接，不要用引用替代解释。
- 用户进一步纠正：不是要以图为中心，图只是辅助；核心应是模型的完善过程。已在 `Notes/项目深挖工作规则.md` 新增“模型完善过程主轴规则”。后续研究过程文档应按“为什么需要这个模型 -> 模型从哪里来 -> 假设 -> 数学形式 -> 相比前一模型解释了什么 -> Python 实现和调试 -> 用哪些图验证效果 -> 结论边界 -> 为什么进入下一步模型”来写。图表必须服务于模型验证，不要把教程写成看图集。
- 已按上述规则新增 `Notes/研究过程教科书版-模型主线重构-2026-05-04.md`。该文档是当前最推荐学习入口，按模型演进主线重写研究过程：峰距法 -> FOD -> 色散 FOD -> FFT 独立检查 -> Airy/TMM -> Dong2012 介电函数 -> 受约束 Dong/TMM -> 残差诊断 -> 残差-FFT 对齐 -> 波段权重。旧版 `Notes/研究过程教科书版-2026-05-04.md` 保留为图文补充和历史稿，后续优先扩展新重构版。
- 2026-05-05 用户已安装 Zotero，并要求后续文献原文、PDF、网页快照优先进入 Zotero，vault 只保留笔记。已在 `Notes/项目深挖工作规则.md` 新增 Zotero 文献管理规则，并新增 `Literature/Zotero文献归档清单-2026-05-05.md`。后续不要直接把新查到的 PDF 长期下载到项目 `Sources/Literature/`；若 Codex 不能安全直接导入 Zotero，应生成 DOI/RIS/BibTeX 待导入清单和精读笔记。禁止直接编辑 `C:\Users\A2826\Zotero\zotero.sqlite`。
- 用户要求直接在 Zotero 中建立集合并放入文献。已通过 Zotero 本地 connector 导入 26 条项目相关文献/网页条目。Zotero 集合名为 `SiC Epilayer Thickness Study`，collection key 为 `89BU9R2E`。由于 connector 对中文集合名/中文标签处理不稳定，集合名采用英文，中文解释保留在 vault 笔记中。本次尚未批量绑定 PDF 附件。为修正集合名，已在关闭 Zotero 后备份并最小修改 Zotero 数据库集合名字段；备份为 `C:\Users\A2826\Zotero\zotero.sqlite.backup-before-sic-rename-20260505`。
- 注意：操作过程中曾误把 Zotero API 中乱码显示的 `新疆电量预测与产业因果推断研究` 集合识别为可清理集合；已从备份恢复。当前 Zotero 集合状态：`SiC Epilayer Thickness Study` key `89BU9R2E`，26 条；`新疆电量预测与产业因果推断研究` key `RIKW96JZ`，30 条。后续不要改动 `RIKW96JZ`。
- 用户反馈 Zotero 里看不到条目后，已再次核查并把 Zotero 界面定位到本项目集合：`zotero://select/library/collections/89BU9R2E`。项目 `Literature/Zotero文献归档清单-2026-05-05.md` 已改为 `imported-to-zotero` 状态，并补充“如果看不到，先选中 `SiC Epilayer Thickness Study` 集合”的说明。
- 用户进一步发现集合里有大量问号和作者不清楚。已用 DOI 官方 CSL 元数据生成清洁 RDF，并通过 Zotero connector 重导入清洁条目。由于 Zotero 本地 `/api/users/0` 写接口返回 `501 Method not implemented`，无法用 `PATCH` 修旧条目；因此已关闭 Zotero、备份数据库，并最小整理 collection membership，让 `SiC Epilayer Thickness Study` 只显示清洁导入的 26 条。修复后 API 核查：集合 26 条，`bad_question_items=0`，`empty_creator_items=0`。备份：`C:\Users\A2826\Zotero\zotero.sqlite.backup-before-sic-metadata-cleanup-20260505`。另已补 `tmm` 代码仓库条目的 programmer 为 Steven J. Byrnes，补充前备份：`C:\Users\A2826\Zotero\zotero.sqlite.backup-before-sic-tmm-creator-fix-20260505`。旧坏条目未删除，只是不再挂在项目集合中。
- 2026-05-11 用户准备报名夏令营，要求生成正式提交论文版本。已新增 `Deliverables/夏令营提交版论文-2026-05-11.qmd`、`.html` 和 `.pdf`。PDF 为 A4、15 页，已关闭浏览器页眉页脚。正式版去掉学习稿语气和 Obsidian 双链，保留核心结论边界：$d\approx7.4\text{--}7.6\ \mu\mathrm{m}$ 是当前最强候选区间，$d^\ast=7.465\ \mu\mathrm{m}$ 是受约束 Dong/TMM 代表点。已用 `pdfinfo`、`pdftotext` 和第一页渲染图做基础检查。报告见 `System/Reports/2026-05-11 碳化硅项目夏令营提交版论文生成报告.md`。
- 2026-05-11 用户进一步反馈上一版不符合正式提交期待，明确要求 LaTeX 编译，并要求内容安排参照国家级数学建模论文、篇幅适中。已新增 `Deliverables/latex_submit/main.tex` 和 `Deliverables/latex_submit/夏令营提交版论文-LaTeX-2026-05-11.pdf`。LaTeX 版为 A4、14 页，已用 `xelatex` 编译通过；`main.log` 未发现真正的 Overfull、Undefined、LaTeX Warning 或 Error；已用 `pdftotext` 和第一页渲染做基础检查。作者字段当前为 `A2826`，正式提交前需由用户替换为真实姓名、学校和专业信息。报告见 `System/Reports/2026-05-11 碳化硅项目LaTeX夏令营提交版论文重写报告.md`。
- 2026-07-07 用户希望项目收尾，并要求继续做必要实验后写最终研究论文。已新增 `Code/final_evidence_audit.py`，只读取已有实验输出，生成 `Experiments/outputs/final_evidence_audit.csv`、`Experiments/outputs/final_evidence_audit_summary.md` 和 `Experiments/figures/final_evidence_audit.png`。审计显示纳入最终判断的强证据覆盖约为 $7.400\text{--}7.580\ \mu\mathrm{m}$，因此最终论文采用 $d\approx7.4\text{--}7.6\ \mu\mathrm{m}$，代表点仍为 $d^\ast=7.465\ \mu\mathrm{m}$。已新增最终论文目录 `Deliverables/final_research_paper_2026-07-07/`，最终 PDF 为 `碳化硅外延层厚度反演研究-最终论文-2026-07-07.pdf`，A4、15 页，已用 `xelatex` 编译两遍并渲染检查第 1 页和第 12 页。报告见 `System/Reports/2026-07-07 碳化硅项目最终收尾论文与证据审计报告.md`。

## 重要背景

- 题目要求围绕红外干涉法确定碳化硅和硅外延层厚度。
- 附件 1、2 是同一块碳化硅晶圆片在 10 度、15 度入射角下的反射率数据。
- 附件 3、4 是同一块硅晶圆片在 10 度、15 度入射角下的反射率数据。
- 用户认为现有论文“没有什么亮点”，希望找到真正可深挖方向。

## 未解决问题

- 尚未完整复现已有论文的厚度计算。
- Python 图表、基础实验链条、FOD 参数敏感性和第一版 SiC 色散折射率修正已建立。
- 尚未判断现有 6.145 $\mu m$ 是否能被附件数据严格支撑；Si 的 5.13 $\mu m$ 暂不被当前 FOD 复核支持，但仍需在 TMM/Airy 模型中复查。
- 文献矩阵已完成第一版，但 Dong2012、Oishi2006、Troparevsky2010 等仍需合法全文和精读。
- 多 agent 协作可以降低主上下文压力，但不能代替主 agent 的科学审查；子 agent 输出必须先进入 `AgentWork/`，不得直接作为论文结论。
- `git safe.directory` 已按用户授权配置，当前可以运行 `git status --short`。
- 多 agent 第一批输出已通过主 agent 接收，但尚未整合进正式 `Literature/文献矩阵.md`、`Methods/` 或 `Writing/`；下一步应谨慎提升已核验内容。
- 默认系统 `python` 缺少 `numpy/pandas`，运行项目脚本应使用 `C:\Users\A2826\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`，后续需写入 `Code/README.md`。
- 下一步应细化论文图表和参数表，并决定是否继续做连续优化/参数置信区间；继续保留 $d\approx7.4\text{--}7.6\ \mu m$ 为候选区间而非最终厚度。
- 公式显示规则已写入 `Notes/项目深挖工作规则.md`；后续公式应直接用 `$...$` 或 `$$...$$`，不要写成 LaTeX 代码块。
- 论文初稿已经建立，但它是研究基点，不是终稿；下一位 agent 应优先围绕初稿做图表补强、连续优化设计、文献引用核验和结果表达收敛，不要重新初始化项目。
- 当前 `scipy` 未安装；若要做真正连续优化，需要安装依赖或继续使用手写网格/坐标搜索，并明确其局限。
- RMSE 热力图已经补齐；后续不应再只问“厚度是否稳定”，还要问“拟合质量是否也稳定”。当前最该深挖的是 $\nu_p$ 的物理边界。
- 当前项目主线不是泛泛整理资料，而是构建更精确、更可解释的 SiC 外延层厚度反演模型，并用数据实验、残差、敏感性、稳健性和可视化不断审查它。
- $\nu_p$ 物理边界已经建立并接入局部细化。下一步不要继续盲目扩大参数搜索；应检查最终状态下的分角度残差结构，并为 $\gamma$ 和声子阻尼补充更合理物理/经验边界。
- 当前文献路线判断：Dong2012 继续作为 SiC 红外介电函数和 TMM 的物理地基；Sun et al. 2023 用于频域独立验证；Dutta et al. 2022 用于全局优化和非唯一反问题；Chahal et al. 2024 用于近年 n-doped 4H-SiC 材料边界；机器学习论文只作未来方向，不进入当前主模型。
- 残差诊断和 FFT 后的模型判断：$d\approx7.4\text{--}7.6\ \mu m$ 仍是 Dong/TMM 强候选区间，但它尚未被简单频域厚度公式独立证明。下一步应解释为什么 FFT 稳定主周期在不同 $n_{\mathrm{eff}}$ 口径下给出 $6.5\text{--}8.0\ \mu m$，并精读 Sun2023 或做滑窗 FFT/VMD-LSP。
- 数据处理诊断后的补充判断：数据处理的作用不是替代物理模型，而是稳定提取条纹周期、峰谷结构、局部波段漂移和残差线索。当前证据支持“数据确实含有稳定厚度尺度”，但最终厚度仍必须由材料光学常数和 TMM 解释。
- 已在 `Notes/项目深挖工作规则.md` 新增“算力与 token 成本提醒规则”。后续如果准备做大规模全局优化、机器学习仿真谱训练、MCMC/bootstrap、高分辨率参数扫描、批量 OCR/视频转写或长上下文文献精读，应先做小规模 sanity check；一旦成本明显升高，必须提醒用户考虑是否接入学校服务器或更合适的计算环境。未经用户明确授权，不假设服务器权限，不把密码、私钥、长期 token 等敏感信息写入 vault。

## 下一步

- [x] 运行 `Experiments/scripts/initial_data_diagnostic.py`
- [x] 生成数据探索图和峰谷提取结果
- [ ] 继续精读 Oishi et al. 2006；Dong Lin et al. 2012 已完成第一版模型转化
- [x] 将 Li2010 FOD 模型翻译为 Python 实验
- [x] 扩展 FOD 参数敏感性分析
- [x] 整理变量与假设体系
- [ ] 基于 $k(\nu)$ 和极值稳定性收窄物理合理波段
- [x] 复核 Si 厚度
- [x] 解析 Larruquert n,k 数据并接入 SiC 色散模型
- [ ] 建立常数折射率、色散修正、TMM 全谱拟合三类对比模型
- [ ] 做敏感性分析和稳健性分析
- [x] 将结论迁移到新版论文结构
- [ ] 基于 `Writing/论文初稿-2026-05-04.md` 继续补图表、参数表、参考文献核验和最终论文表达
- [x] 基于 `Writing/论文初稿-2026-05-04.md` 生成第一批论文图表、参数表和最佳拟合曲线
- [ ] 继续补 RMSE 参数敏感性热力图和带物理边界的连续/局部优化方案
- [x] 补充参数敏感性 RMSE 热力图
- [ ] 查证 Dong2012 或相关资料中 $\nu_p$ 与载流子浓度的关系，建立合理参数边界
- [x] 查证 Dong2012 或相关资料中 $\nu_p$ 与载流子浓度的关系，建立合理参数边界
- [x] 将 $\nu_p$ 物理边界接入 Dong/TMM 局部细化脚本，做有边界优化对比
- [x] 检查有边界最终状态下的 $10^\circ$ 与 $15^\circ$ 残差结构
- [x] 按 `Notes/多Agent协作分工方案.md` 拆分第一批子任务：色散 FOD 输出复核、附件 3/4 硅厚度差异二审、Li2010 之外核心文献核验
- [x] 实现 `Code/residual_diagnostics.py`，优先输出分角度、分波段残差和残差自相关
- [x] 实现 `Code/fft_frequency_seed.py`，用频域主周期独立检查 $7.4\text{--}7.6\ \mu m$ 候选区间
- [x] 实现 `Code/data_processing_diagnostics.py`，检查多种预处理下主周期和频域厚度初值是否稳定
- [x] 实现 `Code/sliding_fft_diagnostics.py`，检查主周期是否随波数窗口漂移
- [x] 对齐滑窗 FFT 主周期与 TMM 分波段残差，判断残差高发波段来自数据处理问题还是物理模型缺项
- [x] 设计波段权重 TMM 厚度剖面稳健性实验
- [x] 生成论文图文版，嵌入核心可视化图表
- [ ] 决定是否把波段权重扩展到材料参数联合优化；若要大规模运行，先提示服务器算力选项
- [x] 接收 `AgentWork/官方2026清华B题分享补充核验-2026-05-04.md`
- [ ] 精读 Sun2023、Dutta2022、Chahal2024 后再把具体方法写进论文正文
- [ ] 按 `Methods/方法节点/方法节点索引.md` 继续补充后续新方法节点，并把论文草稿中的方法名改成双链
- [ ] 按 `Methods/方法论总览.md` 设计下一批数据处理实验：Savitzky-Golay、robust baseline、滑窗 FFT 和异常值检查
- [x] 建立论文公式推导与来源追踪索引，并把图文版论文关键公式挂回文献、方法节点、代码和输出
- [x] 中文化图文版论文和主要论文图表的可读英文显示
- [x] 新增面向零基础的研究过程教科书版主入口
