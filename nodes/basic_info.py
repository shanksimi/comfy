from comfy.samplers import KSampler
from nodes import MAX_RESOLUTION


# Starting sizes, rounded to multiples of 16 for latent compatibility.
ASPECT_PRESETS = {}
for family, dimensions in (
    ("Anima / Illu / Pony", ((1024, 1024), (768, 1344), (832, 1216), (896, 1152), (1024, 1280))),
    ("FLUX / Krea / MOSS / Qwen", ((1024, 1024), (720, 1280), (864, 1296), (896, 1200), (928, 1168))),
):
    for ratio, (width, height) in zip(("1:1", "9:16", "2:3", "3:4", "4:5"), dimensions):
        ASPECT_PRESETS[f"{ratio} · {family} ({width}x{height})"] = (width, height)
        if width != height:
            left, right = ratio.split(":")
            ASPECT_PRESETS[f"{right}:{left} · {family} ({height}x{width})"] = (height, width)


class ShankBasicInfo:
    CATEGORY = "utils"
    FUNCTION = "get_values"
    DESCRIPTION = "Gom các thông số kích thước, lấy mẫu và upscale để nhiều node dùng chung."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "width": ("INT", {"default": 0, "min": 0, "max": MAX_RESOLUTION, "step": 8,
                              "tooltip": "Chiều rộng ảnh theo pixel. Giá trị 0 được truyền nguyên."}),
            "height": ("INT", {"default": 0, "min": 0, "max": MAX_RESOLUTION, "step": 8,
                               "tooltip": "Chiều cao ảnh theo pixel. Giá trị 0 được truyền nguyên."}),
            "cfg": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 100.0, "step": 0.1,
                              "tooltip": "Mức độ bám conditioning khi lấy mẫu."}),
            "steps": ("INT", {"default": 30, "min": 1, "max": 10000,
                              "tooltip": "Số bước lấy mẫu."}),
            "upscale_factor": ("FLOAT", {"default": 1.5, "min": 0.01, "max": 16.0, "step": 0.05,
                                         "tooltip": "Hệ số phóng ảnh. 1.5 tương ứng với 150% kích thước ban đầu."}),
            "sampler_name": (KSampler.SAMPLERS, {"default": "euler_ancestral",
                                                 "tooltip": "Thuật toán lấy mẫu của KSampler."}),
            "scheduler": (KSampler.SCHEDULERS, {"default": "simple",
                                               "tooltip": "Lịch mức nhiễu trong quá trình lấy mẫu."}),
        }, "optional": {
            "aspect_ratio": (["Custom", *ASPECT_PRESETS], {
                "default": "Custom",
                "tooltip": "Preset kích thước gợi ý theo tỷ lệ gần đúng và nhóm model. Custom dùng width và height nhập tay.",
            }),
        }}

    RETURN_TYPES = ("INT", "INT", "FLOAT", "INT", "FLOAT", KSampler.SAMPLERS, "STRING", KSampler.SCHEDULERS, "STRING")
    RETURN_NAMES = ("width", "height", "CFG", "steps", "upscale factor", "sampler", "sampler_name", "scheduler", "scheduler_name")
    OUTPUT_TOOLTIPS = (
        "Chiều rộng ảnh theo pixel.",
        "Chiều cao ảnh theo pixel.",
        "Giá trị CFG để nối vào sampler.",
        "Số bước lấy mẫu.",
        "Hệ số phóng ảnh để nối vào node upscale.",
        "Lựa chọn sampler để nối vào sampler_name của KSampler.",
        "Tên sampler dạng văn bản để ghi metadata.",
        "Lựa chọn scheduler để nối vào KSampler.",
        "Tên scheduler dạng văn bản để ghi metadata.",
    )

    def get_values(self, width, height, cfg, steps, upscale_factor, sampler_name, scheduler, aspect_ratio="Custom"):
        width, height = ASPECT_PRESETS.get(aspect_ratio, (width, height))
        return width, height, cfg, steps, upscale_factor, sampler_name, sampler_name, scheduler, scheduler
