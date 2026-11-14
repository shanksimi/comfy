_TOOLTIPS = {
    "image": "Ảnh đầu vào cần phóng lớn.",
    "model": "Model diffusion dùng để vẽ lại từng ô ảnh.",
    "positive": "Conditioning mô tả nội dung mong muốn cho từng ô.",
    "negative": "Conditioning mô tả nội dung cần tránh trong từng ô.",
    "vae": "VAE dùng để mã hóa và giải mã từng ô ảnh.",
    "upscale_by": "Hệ số phóng lớn ảnh.",
    "seed": "Seed dùng khi vẽ lại ảnh.",
    "steps": "Số bước lấy mẫu cho mỗi ô.",
    "cfg": "Mức độ bám conditioning khi vẽ lại mỗi ô.",
    "sampler_name": "Thuật toán lấy mẫu cho từng ô.",
    "scheduler": "Lịch mức nhiễu khi lấy mẫu.",
    "denoise": "Mức vẽ lại từng ô. Giá trị thấp giữ chi tiết ảnh gốc nhiều hơn.",
    "upscale_model": "Model phóng lớn ảnh trước khi vẽ lại từng ô.",
    "mode_type": "Thứ tự xử lý các ô trong lượt vẽ lại chính.",
    "tile_width": "Chiều rộng mỗi ô, tính bằng pixel.",
    "tile_height": "Chiều cao mỗi ô, tính bằng pixel.",
    "mask_blur": "Bán kính làm mềm biên mask của ô.",
    "tile_padding": "Số pixel ngữ cảnh mở rộng quanh mỗi ô.",
    "seam_fix_mode": "Cách xử lý đường nối giữa các ô.",
    "seam_fix_denoise": "Mức vẽ lại vùng đường nối.",
    "seam_fix_width": "Chiều rộng dải xử lý đường nối trong chế độ Band Pass.",
    "seam_fix_mask_blur": "Bán kính làm mềm mask vùng đường nối.",
    "seam_fix_padding": "Số pixel ngữ cảnh mở rộng khi sửa đường nối.",
    "force_uniform_tiles": "Giữ kích thước các ô đồng đều, kể cả ở mép ảnh.",
    "tiled_decode": "Giải mã VAE theo ô để giảm bộ nhớ cần dùng.",
    "batch_size": "Số ô xử lý mỗi lượt vẽ lại. Tăng giá trị có thể nhanh hơn, dùng thêm VRAM và cho kết quả khác. Không áp dụng khi sửa đường nối.",
}


class ShankUltimateSDUpscale:
    CATEGORY = "image/upscaling"
    RETURN_TYPES = ("IMAGE",)
    OUTPUT_TOOLTIPS = ("Ảnh sau khi phóng lớn, vẽ lại từng ô và xử lý đường nối đã chọn.",)
    DESCRIPTION = "Phóng lớn ảnh rồi dùng diffusion vẽ lại từng ô để bổ sung chi tiết. Có thể xử lý đường nối giữa các ô."
    FUNCTION = "upscale"

    @staticmethod
    def upstream():
        from nodes import NODE_CLASS_MAPPINGS

        return NODE_CLASS_MAPPINGS.get("UltimateSDUpscale")

    @classmethod
    def INPUT_TYPES(cls):
        upstream = cls.upstream()
        if upstream is None:
            return {"required": {"image": ("IMAGE",)}}

        schema = upstream.INPUT_TYPES()
        return {
            group: {
                name: (spec[0], {**(spec[1] if len(spec) > 1 else {}), "tooltip": _TOOLTIPS[name]})
                if name in _TOOLTIPS else spec
                for name, spec in inputs.items()
            }
            for group, inputs in schema.items()
        }

    def upscale(self, **inputs):
        upstream = self.upstream()
        if upstream is None:
            raise RuntimeError("Cần cài ComfyUI_UltimateSDUpscale để chạy node này.")
        return getattr(upstream(), upstream.FUNCTION)(**inputs)
