# Adapted from rgthree-comfy (MIT). See LICENSE-image-resize.
from comfy.utils import common_upscale
from nodes import ImageScale, MAX_RESOLUTION


class ShankImageResize:
    CATEGORY = "image/upscaling"
    FUNCTION = "main"
    DESCRIPTION = "Đổi kích thước ảnh theo pixel hoặc phần trăm, giữ tỷ lệ ảnh gốc."
    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("IMAGE", "WIDTH", "HEIGHT")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "measurement": (["pixels", "percentage"],),
            "width": ("INT", {"default": 0, "min": 0, "max": MAX_RESOLUTION, "step": 1,
                              "tooltip": "Chiều rộng đích. Để 0 để tính theo chiều cao."}),
            "height": ("INT", {"default": 0, "min": 0, "max": MAX_RESOLUTION, "step": 1,
                               "tooltip": "Chiều cao đích. Để 0 để tính theo chiều rộng."}),
            "fit": (["crop", "pad", "contain"], {
                "tooltip": "crop cắt giữa, pad thêm viền đen, contain trả ảnh vừa trong khung đích. "
                           "Nếu một chiều bằng 0, node tự tính chiều còn lại và dùng contain.",
            }),
            "method": (ImageScale.upscale_methods,),
        }}

    def main(self, image, measurement, width, height, method, fit):
        _, original_height, original_width, _ = image.shape
        if measurement == "percentage":
            width = max(1, round(width * original_width / 100)) if width else 0
            height = max(1, round(height * original_height / 100)) if height else 0

        if (width, height) in ((0, 0), (original_width, original_height)):
            return image, original_width, original_height

        if width == 0 or height == 0:
            width = width or max(1, round(height * original_width / original_height))
            height = height or max(1, round(width * original_height / original_width))
            fit = "contain"

        scale_x = width / original_width
        scale_y = height / original_height
        scale = max(scale_x, scale_y) if fit == "crop" else min(scale_x, scale_y)
        resized_width = max(1, round(original_width * scale))
        resized_height = max(1, round(original_height * scale))
        resized = common_upscale(
            image.movedim(-1, 1), resized_width, resized_height, method, crop="disabled",
        )
        # ComfyUI's Lanczos implementation squeezes grayscale channels.
        if resized.ndim == 3:
            resized = resized.unsqueeze(1)
        resized = resized.movedim(1, -1)

        if fit == "crop":
            left = (resized_width - width) // 2
            top = (resized_height - height) // 2
            resized = resized[:, top:top + height, left:left + width, :]
        elif fit == "pad" and (resized_width, resized_height) != (width, height):
            batch, _, _, channels = resized.shape
            padded = resized.new_zeros((batch, height, width, channels))
            left = (width - resized_width) // 2
            top = (height - resized_height) // 2
            padded[:, top:top + resized_height, left:left + resized_width, :] = resized
            resized = padded

        return resized, resized.shape[2], resized.shape[1]
