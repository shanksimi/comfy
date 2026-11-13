"""
Impact Wildcard Encode - Node xử lý wildcard trong prompt (Tiếng Việt)

Chức năng tương tự ImpactWildcardEncode của Impact Pack:
Thay thế các mẫu {a|b|c} trong prompt bằng một giá trị ngẫu nhiên.
Hỗ trợ đọc danh sách từ file trong thư mục wildcards/ nếu có.
"""

import os
import re
import random

import folder_paths


class ImpactWildcardEncode:
    """
    Mã hóa Wildcard (Impact).
    Thay thế các mẫu {a|b|c} trong prompt bằng một giá trị ngẫu nhiên.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "encode"
    CATEGORY = "text/impact"
    OUTPUT_NODE = False

    def encode(self, text, seed=0):
        if not text:
            return ("",)

        rng = random.Random(seed)

        # Thư mục chứa file wildcard (nếu có)
        wildcard_dir = os.path.join(os.path.dirname(__file__), "wildcards")

        def replace_wildcard(match):
            content = match.group(1)

            # Trường hợp tham chiếu file: {ten_file.txt}
            if content.endswith(".txt") and "|" not in content:
                file_path = os.path.join(wildcard_dir, content)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = [line.strip() for line in f if line.strip()]
                        if lines:
                            return rng.choice(lines)
                    except Exception:
                        pass
                # Nếu không đọc được file, trả về nguyên nội dung
                return content

            # Trường hợp lựa chọn: {a|b|c}
            parts = [p.strip() for p in content.split("|")]
            if len(parts) > 1:
                return rng.choice(parts)
            return content

        # Lặp thay thế cho đến khi không còn wildcard (hỗ trợ lồng nhau đơn giản)
        result = text
        max_iterations = 10
        for _ in range(max_iterations):
            new_result = re.sub(r"\{([^{}]+)\}", replace_wildcard, result)
            if new_result == result:
                break
            result = new_result

        return (result,)


# Đăng ký node
NODE_CLASS_MAPPINGS = {
    "ImpactWildcardEncode": ImpactWildcardEncode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImpactWildcardEncode": "Mã hóa Wildcard (Impact)",
}