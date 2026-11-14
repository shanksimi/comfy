from nodes import PreviewImage


class ShankImageComparer(PreviewImage):
    CATEGORY = "image"
    FUNCTION = "compare_images"
    DESCRIPTION = "So sánh ảnh A và B bằng thanh trượt hoặc bấm để đổi ảnh."
    RETURN_TYPES = ("IMAGE",)
    OUTPUT_TOOLTIPS = ("Ảnh A được truyền tiếp. Nếu chỉ có ảnh B, trả ảnh B.",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "image_a": ("IMAGE", {"tooltip": "Ảnh hoặc batch A dùng làm mốc so sánh."}),
                "image_b": ("IMAGE", {"tooltip": "Ảnh hoặc batch B để đối chiếu với A."}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    def compare_images(self, image_a=None, image_b=None, prompt=None, extra_pnginfo=None):
        previews = {}
        first_image = None
        for key, batch in (("a_images", image_a), ("b_images", image_b)):
            previews[key] = []
            if batch is not None and len(batch):
                if first_image is None:
                    first_image = batch
                previews[key] = self.save_images(
                    batch, "shank.compare", prompt, extra_pnginfo
                )["ui"]["images"]
        return {"ui": previews, "result": (first_image,)}
