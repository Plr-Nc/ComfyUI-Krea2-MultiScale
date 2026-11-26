"""Krea2 多尺度渐进采样器

在低显存卡上加速 DiT 采样的一个笨办法：
  扩散的前几步只决定构图（低频），后几步才补细节（高频）。
  所以前 split_step 步在缩小后的 latent 上跑，中间放大，后面在全尺寸跑。

实测（RTX 5060 Laptop 8GB / Krea2 Turbo nvfp4 / 1920x3328 / 8 步 / 2 LoRA）：
  基线 236.9s → 多尺度 142.6s（-39.8%）

关键坑（血泪）：
  KSamplerAdvanced 的噪声交接只有一种组合是对的
    第一段 return_with_leftover_noise = disable
    第二段 add_noise                  = enable
  其余两种组合都直接出纯噪声，因为 bicubic 插值会把残留噪声抹平，
  尺度对不上模型预期的 sigma。
"""

import comfy.utils
import comfy.samplers
import nodes


class Krea2MultiScaleSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff,
                                 "control_after_generate": True}),
                "steps": ("INT", {"default": 8, "min": 1, "max": 10000}),
                "cfg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent_image": ("LATENT",),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "split_step": ("INT", {"default": 4, "min": 0, "max": 100, "step": 1,
                                       "tooltip": "前 N 步在低分辨率跑。0 或 >=steps 表示关闭多尺度，等价于普通 KSampler。"}),
                "low_scale": ("FLOAT", {"default": 0.5, "min": 0.1, "max": 1.0, "step": 0.05,
                                        "tooltip": "低分辨率阶段的缩放比例。0.5 = 面积只剩 1/4。"}),
                "upscale_method": (["bicubic", "bilinear", "area", "nearest-exact", "bislerp"],),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "sampling/krea2"

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               positive, negative, latent_image, denoise,
               split_step, low_scale, upscale_method):

        # 关闭多尺度 = 直通普通采样
        if split_step <= 0 or split_step >= steps or low_scale >= 1.0:
            return nodes.common_ksampler(model, seed, steps, cfg, sampler_name, scheduler,
                                         positive, negative, latent_image,
                                         denoise=denoise, disable_noise=False,
                                         start_step=0, last_step=10000,
                                         force_full_denoise=True)

        samples = latent_image["samples"]
        h, w = samples.shape[-2], samples.shape[-1]
        lo_w = max(8, int(round(w * low_scale)))
        lo_h = max(8, int(round(h * low_scale)))

        # 第一阶段：缩小 → 只跑前 split_step 步
        low = comfy.utils.common_upscale(samples, lo_w, lo_h, "bilinear", "disabled")
        low_latent = latent_image.copy()
        low_latent["samples"] = low

        (stage1,) = nodes.common_ksampler(
            model, seed, steps, cfg, sampler_name, scheduler,
            positive, negative, low_latent,
            denoise=denoise, disable_noise=False,
            start_step=0, last_step=split_step,
            force_full_denoise=True)          # ← 对应 return_with_leftover_noise = disable

        # 第二阶段：放大 → 重新加噪（disable_noise=False）→ 跑剩下的步
        up = comfy.utils.common_upscale(stage1["samples"], w, h, upscale_method, "disabled")
        up_latent = stage1.copy()
        up_latent["samples"] = up

        (stage2,) = nodes.common_ksampler(
            model, seed, steps, cfg, sampler_name, scheduler,
            positive, negative, up_latent,
            denoise=denoise, disable_noise=False,   # ← 对应 add_noise = enable
            start_step=split_step, last_step=10000,
            force_full_denoise=True)

        return (stage2,)


NODE_CLASS_MAPPINGS = {"Krea2MultiScaleSampler": Krea2MultiScaleSampler}
NODE_DISPLAY_NAME_MAPPINGS = {"Krea2MultiScaleSampler": "Krea2 多尺度采样器"}
