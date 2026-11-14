_TOOLTIPS = {
    "images": "Ảnh hoặc batch ảnh cần lưu.",
    "filename": (
        "Mẫu tên file. Biến hỗ trợ: %date, %time, %time_format<format>, %model, "
        "%width, %height, %seed, %counter, %counter<padding>, %sampler_name, %steps, "
        "%cfg, %scheduler_name, %basemodelname, %denoise, %clip_skip, %custom, %label."
    ),
    "path": "Thư mục con trong thư mục output của ComfyUI.",
    "extension": "Định dạng file ảnh cần lưu.",
    "lossless_webp": "Lưu WebP ở chế độ không mất dữ liệu.",
    "quality_jpeg_or_webp": "Chất lượng nén JPEG, WebP hoặc AVIF.",
    "optimize_png": "Tối ưu dung lượng PNG. Có thể làm chậm quá trình lưu.",
    "embed_workflow": (
        "Nhúng workflow vào file ảnh. PNG hỗ trợ ổn định. WebP và JPEG đang thử nghiệm. "
        "JPEG yêu cầu metadata nhỏ hơn 65.535 byte."
    ),
    "save_workflow_as_json": "Lưu thêm workflow thành file JSON riêng.",
    "metadata": "Metadata tạo ảnh cần nhúng. Nối từ node chuẩn bị metadata của Image Saver.",
    "counter": "Giá trị bộ đếm dùng cho biến %counter.",
    "time_format": "Định dạng thời gian dùng trong mẫu tên file.",
    "label": "Nhãn tùy chọn cho biến %label trong tên file hoặc đường dẫn.",
    "show_preview": "Hiển thị bản xem trước của ảnh đã lưu trong node.",
}


class ShankImageSaverSimple:
    CATEGORY = "image"
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("hashes", "a1111_params")
    OUTPUT_TOOLTIPS = (
        "Danh sách hash phân cách bằng dấu phẩy, có thể nối vào additional_hashes.",
        "Chuỗi tham số tạo ảnh theo định dạng A1111 được ghi vào metadata.",
    )
    DESCRIPTION = "Lưu ảnh kèm metadata tạo ảnh tương thích Civitai và tùy chọn nhúng workflow."

    @staticmethod
    def upstream():
        from nodes import NODE_CLASS_MAPPINGS

        return NODE_CLASS_MAPPINGS.get("Image Saver Simple")

    @classmethod
    def INPUT_TYPES(cls):
        upstream = cls.upstream()
        if upstream is None:
            return {"required": {"images": ("IMAGE", {
                "tooltip": "Cần cài ComfyUI-Image-Saver để hiện các tùy chọn lưu ảnh.",
            })}}
        return {
            group: {
                name: (spec[0], {**(spec[1] if len(spec) > 1 else {}), "tooltip": _TOOLTIPS[name]})
                if name in _TOOLTIPS else spec
                for name, spec in inputs.items()
            }
            for group, inputs in upstream.INPUT_TYPES().items()
        }

    def save_images(self, **inputs):
        upstream = self.upstream()
        if upstream is None:
            raise RuntimeError("Cần cài ComfyUI-Image-Saver của alexopus để lưu ảnh.")
        return getattr(upstream(), upstream.FUNCTION)(**inputs)
