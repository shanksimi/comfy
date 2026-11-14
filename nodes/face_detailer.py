class ShankFaceDetailer:
    CATEGORY = "image"
    WILDCARD_DEFAULT = "[CONCAT] detailed face, detailed eyes, perfect face, beautiful face, beauty eyes, detailed expressive eyes"
    DESCRIPTION = (
        "Phát hiện khuôn mặt hoặc đối tượng bằng detector, cắt và phóng vùng phát hiện "
        "để tái tạo chi tiết, rồi ghép vùng đã xử lý trở lại ảnh."
    )
    FUNCTION = "detail"
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "MASK", "DETAILER_PIPE", "IMAGE")
    RETURN_NAMES = ("image", "cropped_refined", "cropped_enhanced_alpha", "mask", "detailer_pipe", "cnet_images")
    OUTPUT_IS_LIST = (False, True, True, False, False, True)
    OUTPUT_TOOLTIPS = (
        "Ảnh hoàn chỉnh sau khi ghép các vùng đã xử lý.",
        "Danh sách vùng cắt đã được cải thiện chi tiết.",
        "Danh sách vùng đã cải thiện kèm kênh alpha.",
        "Mask tổng hợp của các vùng xử lý.",
        "Bộ cấu hình để nối vào các node Detailer tương thích.",
        "Danh sách ảnh điều kiện ControlNet nếu có.",
    )

    @staticmethod
    def upstream():
        from nodes import NODE_CLASS_MAPPINGS

        return NODE_CLASS_MAPPINGS.get("FaceDetailer")

    @classmethod
    def INPUT_TYPES(cls):
        upstream = cls.upstream()
        if upstream is None:
            return {"required": {"image": ("IMAGE", {
                "tooltip": "Cài ComfyUI-Impact-Pack để hiện các đầu vào của FaceDetailer.",
            })}}
        schema = upstream.INPUT_TYPES()
        required = schema["required"]
        wildcard_type, options = required["wildcard"]
        return {**schema, "required": {
            **required, "wildcard": (wildcard_type, {**options, "default": cls.WILDCARD_DEFAULT}),
        }}

    def detail(self, **inputs):
        upstream = self.upstream()
        if upstream is None:
            raise RuntimeError("Cần cài ComfyUI-Impact-Pack để chạy FaceDetailer.")
        return getattr(upstream(), upstream.FUNCTION)(**inputs)


class ShankHanDetailer(ShankFaceDetailer):
    WILDCARD_DEFAULT = "[CONCAT] detailed hands, slender hands"
    DESCRIPTION = (
        "Phát hiện bàn tay, tái tạo chi tiết trong vùng cắt rồi ghép lại vào ảnh. "
        "Nối detector bàn tay vào bbox_detector."
    )

    @classmethod
    def INPUT_TYPES(cls):
        schema = super().INPUT_TYPES()
        required = schema["required"]
        if "bbox_detector" not in required:
            return schema
        detector_type, *options = required["bbox_detector"]
        detector_options = dict(options[0]) if options else {}
        detector_options["tooltip"] = "Nối detector nhận diện bàn tay để xác định vùng cần chỉnh."
        return {**schema, "required": {
            **required, "bbox_detector": (detector_type, detector_options),
        }}
