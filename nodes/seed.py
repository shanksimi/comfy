"""
Seed Node - Custom Node cho ComfyUI (Tiếng Anh hiển thị, chú thích tiếng Việt)

Node cung cấp giá trị seed cho KSampler.
Hỗ trợ: seed cố định, random seed, tăng/giảm seed, và nút copy/paste seed.
"""

import random


class ShankSeed:
    """
    Seed Node.
    Cung cấp giá trị seed cho KSampler và các node khác cần seed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "mode": (["fixed", "random", "increment", "decrement"], {"default": "fixed"}),
            },
            "optional": {
                "prev_seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("seed", "next_seed")
    FUNCTION = "get_seed"
    CATEGORY = "utils/seed"
    OUTPUT_NODE = False

    def get_seed(self, seed=0, mode="fixed", prev_seed=0):
        """
        Trả về seed hiện tại và seed kế tiếp (dùng để nối chuỗi node Seed).
        """
        if mode == "random":
            current_seed = random.randint(0, 0xFFFFFFFFFFFFFFFF)
        elif mode == "increment":
            current_seed = prev_seed + 1 if prev_seed > 0 else seed + 1
        elif mode == "decrement":
            current_seed = prev_seed - 1 if prev_seed > 0 else seed - 1
            if current_seed < 0:
                current_seed = 0
        else:  # fixed
            current_seed = seed

        next_seed = current_seed + 1

        return (current_seed, next_seed)


# Đăng ký node
NODE_CLASS_MAPPINGS = {
    "ShankSeed": ShankSeed,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ShankSeed": "Shank Seed (shanksimi)",
}