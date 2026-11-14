class ShankUltralyticsDetectorProvider:
    CATEGORY = "loaders"
    FUNCTION = "load_detector"
    RETURN_TYPES = ("BBOX_DETECTOR", "SEGM_DETECTOR")
    OUTPUT_TOOLTIPS = (
        "Detector tìm khung bao. Nối vào bbox_detector của FaceDetailer hoặc HandDetailer.",
        "Detector phân vùng theo pixel khi chọn model segm. Model bbox không tạo mask phân vùng.",
    )
    DESCRIPTION = "Nạp model Ultralytics để phát hiện khuôn mặt, bàn tay hoặc đối tượng khác."

    @staticmethod
    def upstream():
        from nodes import NODE_CLASS_MAPPINGS

        return NODE_CLASS_MAPPINGS.get("UltralyticsDetectorProvider")

    @classmethod
    def INPUT_TYPES(cls):
        upstream = cls.upstream()
        if upstream is None:
            return {"required": {}}
        schema = upstream.INPUT_TYPES()
        required = schema["required"]
        choices, *options = required["model_name"]
        return {**schema, "required": {**required, "model_name": (
            choices,
            {**(options[0] if options else {}),
             "tooltip": "Chọn model bbox để tìm khung bao hoặc model segm để lấy thêm mask."},
        )}}

    def load_detector(self, model_name=None):
        upstream = self.upstream()
        if upstream is None:
            raise RuntimeError("Cần cài ComfyUI-Impact-Subpack để nạp detector Ultralytics.")
        return getattr(upstream(), upstream.FUNCTION)(model_name=model_name)
