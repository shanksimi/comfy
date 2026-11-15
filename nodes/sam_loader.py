class ShankSAMLoader:
    CATEGORY = "loaders"
    FUNCTION = "load_model"
    RETURN_TYPES = ("SAM_MODEL",)
    OUTPUT_TOOLTIPS = ("Model SAM để nối vào sam_model_opt của Detailer hoặc SAMDetector.",)
    DESCRIPTION = "Nạp model Segment Anything (SAM) để tạo mask phân vùng đối tượng."

    @staticmethod
    def upstream():
        from nodes import NODE_CLASS_MAPPINGS
        return NODE_CLASS_MAPPINGS.get("SAMLoader")

    @classmethod
    def INPUT_TYPES(cls):
        upstream = cls.upstream()
        if upstream is None:
            return {"required": {}}
        schema = upstream.INPUT_TYPES()
        required = dict(schema["required"])
        tooltips = {
            "model_name": "Chọn weights SAM. ESAM cần cài ComfyUI-YoloWorld-EfficientSAM.",
            "device_mode": (
                "AUTO đưa model lên GPU khi cần nếu có GPU. Prefer GPU ưu tiên giữ model "
                "trên GPU khi đủ VRAM. CPU luôn chạy trên CPU."
            ),
        }
        for name, tooltip in tooltips.items():
            choices, *options = required[name]
            required[name] = (choices, {**(options[0] if options else {}), "tooltip": tooltip})
        return {**schema, "required": required}

    def load_model(self, **inputs):
        upstream = self.upstream()
        if upstream is None:
            raise RuntimeError("Cần cài ComfyUI-Impact-Pack để nạp model SAM.")
        return getattr(upstream(), upstream.FUNCTION)(**inputs)
