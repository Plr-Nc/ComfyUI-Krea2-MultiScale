# Krea2 多尺度采样

给 8GB 显存的显卡用的小工具：**把 Krea 2 的出图时间砍掉约 37%，画质基本不变。**

实测（RTX 5060 Laptop 8GB，1920×3328，8 步，挂 2 个 LoRA）：

| | 耗时 |
|---|---|
| 原版 KSampler | 281 秒 |
| 装了这个节点 | **177 秒** |

## 怎么用

1. 把整个文件夹丢进 `ComfyUI/custom_nodes/`
2. 重启 ComfyUI
3. 在节点面板搜索 `sampling/krea2`，找到「**Krea2 多尺度采样器**」

它长得和 KSampler 一样，**直接替换掉原来的 KSampler 就行**，model / positive / negative / latent 四根线一一对应，别的不动。

## 三个参数

| 参数 | 默认 | 干嘛的 |
|---|---|---|
| `split_step` | 4 | 前几步走低分辨率。**填 0 就等于普通 KSampler**，可以随时对照 |
| `low_scale` | 0.5 | 低分辨率阶段缩到多少，0.5 = 面积剩四分之一 |
| `upscale_method` | bicubic | 中间那次放大用什么插值 |

`steps` / `cfg` / `sampler_name` / `scheduler` / `denoise` 全部保持你原来的值，不要改 —— 前后两段共用同一套 sigma，靠 step 切片接起来的。

## 原理（一句话）

扩散的前几步只决定构图，后几步才加细节。所以前几步在小画布上跑，中间放大，后面在全尺寸跑。

8 步拆成 4 + 4：低分辨率那 4 步的 token 数只剩 1/4，attention 更是只剩 1/16 —— 时间就从这儿省出来的。

## 需要注意

- **构图可能变**。换了采样路径，同一个 seed 出来的图可能和原来不完全一样
- 只测了 **8 步的 Turbo 蒸馏模型**，Raw（52 步）没验证
- `split_step` 不要超过总步数的一半，否则后段步数太少接不住
- 低显存卡建议 `low_scale` 保持 0.5，再低容易出现构图崩坏
- 节点本身零依赖，只用 ComfyUI 自带的东西。但如果你原来的工作流用了 Comfyroll Studio 之类的第三方节点，那些还是要装的

## 和 SelfLift 的关系

思路来自于 **SelfLift**（[arXiv:2609.02036](https://arxiv.org/abs/2609.02036)）：早期步骤降分辨率、中途提升、剩余步骤全分辨率。

SelfLift 的官方 ComfyUI 实现在 **ComfyUI 0.45** 上跑不了 Krea 2 —— 它要求模型的 `model_sampling` 是 `CONST` 类型，而 Krea 2 走的是 `ModelSamplingFlux`，第一行检查就会被拦下，并且它的像素锚点校正（`rho`）依赖 `CONST` 的语义。

这个节点是个**不依赖那些检查的简化版**：没有锚点校正，画质会比 SelfLift 略软，但在 Krea 2 上能跑。

## License

MIT
