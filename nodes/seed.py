"""
Seed Node - Custom Node cho ComfyUI (Tiếng Anh hiển thị, chú thích tiếng Việt)

Node cung cấp giá trị seed cho KSampler.
Hỗ trợ: seed cố định, random seed, tăng/giảm seed, và nút copy/paste seed.
"""

import random


MAX_SEED = 0xFFFFFFFFFFFFFFFF


class ShankSeed:
    """
    Seed Node.
    Cung cấp giá trị seed cho KSampler và các node khác cần seed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": MAX_SEED}),
                "mode": (["fixed", "random", "increment", "decrement"], {"default": "fixed"}),
            },
            "optional": {
                "prev_seed": ("INT", {"default": 0, "min": 0, "max": MAX_SEED}),
            },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("seed", "next_seed")
    FUNCTION = "get_seed"
    CATEGORY = "utils/seed"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(cls, mode, **kwargs):
        return float("nan") if mode == "random" else mode

    def get_seed(self, seed=0, mode="fixed", prev_seed=None):
        """
        Trả về seed hiện tại và seed kế tiếp (dùng để nối chuỗi node Seed).
        """
        base_seed = seed if not prev_seed else prev_seed
        if mode == "random":
            current_seed = random.randint(0, MAX_SEED)
        elif mode == "increment":
            current_seed = (base_seed + 1) & MAX_SEED
        elif mode == "decrement":
            current_seed = max(0, base_seed - 1)
        else:  # fixed
            current_seed = seed

        next_seed = (current_seed + 1) & MAX_SEED

        return (current_seed, next_seed)


# Đăng ký node
NODE_CLASS_MAPPINGS = {
    "ShankSeed": ShankSeed,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ShankSeed": "Shank Seed (shanksimi)",
}