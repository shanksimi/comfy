# Adapted from ComfyUI-nunchaku at b600f87. See LICENCE.txt.
from comfy.model_patcher import ModelPatcher
from folder_paths import get_full_path_or_raise


def load_lora(model, lora_name, lora_strength):
    from nunchaku.lora.flux import to_diffusers

    wrapper = model.model.diffusion_model
    if not hasattr(wrapper, "ctx_for_copy") or not hasattr(wrapper, "loras"):
        raise ValueError("LOADER=nunchaku cần model FLUX đã được nạp dưới dạng Nunchaku.")

    path = get_full_path_or_raise("loras", lora_name)
    ctx = wrapper.ctx_for_copy
    copied = type(wrapper)(
        wrapper.model, config=ctx["comfy_config"]["model_config"], ctx_for_copy=dict(ctx),
    )
    base = ctx["model_config"].get_model({})
    base.diffusion_model = copied
    result = ModelPatcher(base, ctx["device"], ctx["device_id"])
    copied.loras = [*wrapper.loras, (path, lora_strength)]
    state = to_diffusers(path)
    key = "transformer.x_embedder.lora_A.weight"
    if key in state:
        channels = state[key].shape[1]
        if channels % 4:
            raise ValueError("Số kênh đầu vào của LoRA FLUX không hợp lệ.")
        config = result.model.model_config.unet_config
        config["in_channels"] = max(config["in_channels"], channels // 4)
    return result
