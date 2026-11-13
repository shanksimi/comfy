"""
Ví dụ custom node đơn giản cho ComfyUI.
Node này nhận ảnh đầu vào và lưu lại với tên file tuỳ chỉnh.
"""

import os
import numpy as np
from PIL import Image

import folder_paths


class SaveImagePlus:
    """
    Lưu ảnh đầu ra với tên file có thể tùy chỉnh.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
            },
            "optional": {
                "output_dir": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_image"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def save_image(self, images, filename_prefix="ComfyUI", output_dir=""):
        # Xác định thư mục lưu
        if output_dir and os.path.isdir(output_dir):
            save_dir = output_dir
        else:
            save_dir = folder_paths.get_output_directory()

        os.makedirs(save_dir, exist_ok=True)

        results = []
        for i, image in enumerate(images):
            # Chuyển tensor sang numpy array (0-255)
            if hasattr(image, "cpu"):
                image = image.cpu().numpy()
            image = np.clip(image * 255.0, 0, 255).astype(np.uint8)
            img = Image.fromarray(image)

            # Tạo tên file
            filename = f"{filename_prefix}_{i:05d}.png"
            filepath = os.path.join(save_dir, filename)
            img.save(filepath)

            results.append({
                "filename": filename,
                "subfolder": "",
                "type": "output",
            })

        return {"ui": {"images": results}, "result": ()}


# Đăng ký node
NODE_CLASS_MAPPINGS = {
    "SaveImagePlus": SaveImagePlus,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImagePlus": "Save Image Plus (Custom)",
}