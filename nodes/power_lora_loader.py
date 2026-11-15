import json
import logging
import math
import os


class _LoraInputs(dict):
    def __contains__(self, key):
        return key.lower().startswith("lora_") or super().__contains__(key)

    def __getitem__(self, key):
        if key.lower().startswith("lora_"):
            return ("*",)
        return super().__getitem__(key)


def _resolve_rgthree_name(name, available):
    # Match in the same order as rgthree's get_lora_by_filename.
    full_stem = lambda value: os.path.splitext(value)[0]
    basename = os.path.basename
    basename_stem = lambda value: full_stem(basename(value))
    for transform in (str, full_stem, basename, basename_stem):
        normalized = transform(name)
        match = next((path for path in available if transform(path) == normalized), None)
        if match is not None:
            return match
    return next((path for path in available if name in path), None)


class ShankPowerLoraLoader:
    CATEGORY = "loaders"
    DESCRIPTION = "Áp dụng nhiều LoRA theo thứ tự. Có thể bật/tắt và chỉnh độ mạnh MODEL, CLIP cho từng LoRA."
    FUNCTION = "load_loras"
    RETURN_TYPES = ("MODEL", "CLIP")
    OUTPUT_TOOLTIPS = ("MODEL sau khi áp dụng LoRA.", "CLIP sau khi áp dụng LoRA, nếu có đầu vào CLIP.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "Model cần áp dụng LoRA."}),
            },
            "optional": _LoraInputs({
                "loras": ("STRING", {"default": "[]", "tooltip": "Danh sách LoRA theo thứ tự áp dụng."}),
                "clip": ("CLIP", {"tooltip": "CLIP cần áp dụng LoRA. Có thể để trống."}),
            }),
        }

    def load_loras(self, model=None, loras=None, clip=None, **inputs):
        import folder_paths
        from nodes import LoraLoader

        available = folder_paths.get_filename_list("loras")
        loader = LoraLoader()
        if loras is None:
            for key, row in inputs.items():
                if not key.lower().startswith("lora_") or not isinstance(row, dict):
                    continue
                if not row.get("on") or not row.get("lora") or "strength" not in row:
                    continue
                name = _resolve_rgthree_name(row["lora"], available)
                if name is None:
                    logging.warning("[ShankPowerLoraLoader] Không tìm thấy LoRA: %s", row["lora"])
                    continue
                model_strength = row["strength"]
                clip_strength = row.get("strengthTwo")
                if clip is None:
                    clip_strength = 0
                elif clip_strength is None:
                    clip_strength = model_strength
                if model is not None and (model_strength or clip_strength):
                    model, clip = loader.load_lora(model, clip, name, model_strength, clip_strength)
            return model, clip

        rows = json.loads(loras)
        if not isinstance(rows, list):
            raise ValueError("Cấu hình LoRA phải là danh sách.")
        available = set(available)
        for row in rows:
            if not row.get("enabled") or not row.get("name"):
                continue
            name = row["name"]
            model_strength = float(row["model"])
            clip_strength = float(row["clip"]) if clip is not None else 0.0
            if not all(map(math.isfinite, (model_strength, clip_strength))):
                raise ValueError(f"Độ mạnh LoRA không hợp lệ: {name}")
            if model_strength == clip_strength == 0:
                continue
            if name not in available:
                raise ValueError(f"Không tìm thấy LoRA: {name}")
            model, clip = loader.load_lora(model, clip, name, model_strength, clip_strength)
        return model, clip
