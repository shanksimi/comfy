import json
import math


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
                "loras": ("STRING", {"default": "[]", "tooltip": "Danh sách LoRA theo thứ tự áp dụng."}),
            },
            "optional": {"clip": ("CLIP", {"tooltip": "CLIP cần áp dụng LoRA. Có thể để trống."})},
        }

    def load_loras(self, model, loras, clip=None):
        import folder_paths
        from nodes import LoraLoader

        rows = json.loads(loras)
        if not isinstance(rows, list):
            raise ValueError("Cấu hình LoRA phải là danh sách.")
        available = set(folder_paths.get_filename_list("loras"))
        loader = LoraLoader()
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
