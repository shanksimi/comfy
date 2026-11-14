"""
Shank Wildcard Encode - Node xử lý wildcard trong prompt (Tiếng Việt)

Chức năng tương tự ImpactWildcardEncode của Impact Pack:
Thay thế các mẫu {a|b|c} trong prompt bằng một giá trị ngẫu nhiên.
Hỗ trợ đọc danh sách từ file trong thư mục wildcards/ nếu có.

Giao diện:
  - Ô trên (text): Nhập prompt chứa wildcard.
  - Ô dưới (display_text): Ô HIỂN THỊ KẾT QUẢ sau khi xử lý.
    * Bạn KHÔNG CẦN nhập vào ô này.
    * Kết quả thực sự được trả về qua socket output (text).
"""

from fnmatch import fnmatchcase
from pathlib import Path
import re
import random
import math


class ShankWildcardEncode:
    DESCRIPTION = (
        "Mở rộng wildcard trong prompt, áp dụng LoRA được chỉ định và mã hóa "
        "prompt thành conditioning. Dùng BREAK để mã hóa từng đoạn riêng "
        "rồi nối conditioning."
    )

    @classmethod
    def INPUT_TYPES(cls):
        multiline = {"multiline": True, "dynamicPrompts": False}
        return {"required": {
            "model": ("MODEL", {"tooltip": "Model đầu vào để áp dụng LoRA từ prompt."}),
            "clip": ("CLIP", {"tooltip": "CLIP đầu vào để áp dụng LoRA và mã hóa prompt."}),
            "wildcard_text": ("STRING", {
                **multiline,
                "tooltip": "Prompt mẫu dùng trong Populate. Ví dụ: {đỏ|xanh}, __outfits/dress__ hoặc <lora:tên:0.8>.",
            }),
            "populated_text": ("STRING", {
                **multiline,
                "tooltip": "Hiển thị prompt đã mở rộng trong Populate. Trong Fixed và Reproduce, bạn có thể chỉnh prompt dùng để chạy tại đây.",
            }),
            "mode": (["populate", "fixed", "reproduce"], {
                "tooltip": "Populate: mở rộng wildcard từ prompt mẫu. Fixed: dùng ô prompt kết quả. Reproduce: dùng ô kết quả một lần, rồi giao diện trở về Populate.",
            }),
            "seed": ("INT", {
                "default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF,
                "tooltip": "Seed điều khiển việc chọn wildcard. Cùng seed, prompt và danh sách wildcard cho cùng kết quả.",
            }),
        }}

    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "STRING")
    RETURN_NAMES = ("model", "clip", "conditioning", "populated_text")
    OUTPUT_TOOLTIPS = (
        "Model sau khi áp dụng LoRA từ prompt, nếu có.",
        "CLIP sau khi áp dụng LoRA từ prompt, nếu có.",
        "Conditioning đã mã hóa để nối vào sampler.",
        "Prompt đã mở rộng wildcard, gồm cả các thẻ LoRA đã chọn.",
    )
    FUNCTION = "encode"
    CATEGORY = "text/impact"

    @classmethod
    def IS_CHANGED(cls, mode, **kwargs):
        return float("nan") if mode in ("populate", "reproduce") else mode

    def encode(self, model, clip, wildcard_text, populated_text, mode, seed):
        import folder_paths
        import nodes

        populated = self.populate(wildcard_text if mode == "populate" else populated_text, seed)
        available = folder_paths.get_filename_list("loras")
        loader = nodes.LoraLoader()
        applied = set()

        def apply_lora(match):
            nonlocal model, clip
            name, *options = match[1].split(":")
            name = name.strip().replace(chr(92), "/")
            weights = []
            block = loader_name = None
            block_a = block_b = 1.0
            for option in options:
                if option.startswith("LBW="):
                    for item in option[4:].split(";"):
                        item = item.strip()
                        if item.startswith("A="):
                            block_a = float(item[2:])
                        elif item.startswith("B="):
                            block_b = float(item[2:])
                        elif item:
                            block = item
                elif option.startswith("LOADER="):
                    loader_name = option[7:].lower()
                else:
                    weights.append(float(option))
            if len(weights) > 2 or (block and loader_name):
                raise ValueError(f"Unsupported LoRA tag: {match[0]}")
            model_weight = weights[0] if weights else 1.0
            clip_weight = weights[1] if len(weights) == 2 else model_weight
            if not all(map(math.isfinite, (model_weight, clip_weight, block_a, block_b))):
                raise ValueError(f"Invalid LoRA weights: {match[0]}")
            candidates = [file for file in available if file.replace(chr(92), "/") in
                          (name, name + ".safetensors")]
            if not candidates:
                candidates = [file for file in available if Path(file.replace(chr(92), "/")).name in
                              (name, name + ".safetensors")]
            if len(candidates) != 1:
                raise ValueError(f"LoRA missing or ambiguous: {name}")
            file = candidates[0]
            if file not in applied:
                if loader_name:
                    custom = nodes.NODE_CLASS_MAPPINGS.get("NunchakuFluxLoraLoader")
                    if loader_name != "nunchaku" or custom is None:
                        raise ValueError(f"LoRA loader unavailable: {loader_name}")
                    model = custom().load_lora(model, file, model_weight)[0]
                elif block:
                    custom = nodes.NODE_CLASS_MAPPINGS.get("LoraLoaderBlockWeight //Inspire")
                    if custom is None:
                        raise ValueError("LBW requires ComfyUI-Inspire-Pack")
                    model, clip, _ = custom().doit(
                        model, clip, file, model_weight, clip_weight, False, 0,
                        block_a, block_b, "", block,
                    )
                else:
                    model, clip = loader.load_lora(model, clip, file, model_weight, clip_weight)
                applied.add(file)
            return ""

        prompt = re.sub(r"<lora:([^<>]+)>", apply_lora, populated)
        parts = [part.strip() for part in re.split(r"\bBREAK\b", prompt) if part.strip()]
        encoder = nodes.CLIPTextEncode()
        conditioning = []
        for part in parts or [""]:
            current = encoder.encode(clip, part)[0]
            conditioning = nodes.ConditioningConcat().concat(conditioning, current)[0] if conditioning else current
        return {"ui": {"text": [populated], "mode": [mode]},
                "result": (model, clip, conditioning, populated)}

    @staticmethod
    def wildcard_entries():
        roots = (Path(__file__).resolve().parent / "wildcards",
                 Path(__file__).resolve().parent.parent / "wildcards")
        entries = {}

        def add_yaml(mapping, prefix):
            if isinstance(mapping, dict):
                for key, value in mapping.items():
                    add_yaml(value, (*prefix, str(key)))
            elif isinstance(mapping, list):
                entries["/".join(prefix).lower()] = [
                    str(value).strip() for value in mapping if isinstance(value, (str, int, float))
                ]

        for root in roots:
            for path in sorted(root.rglob("*")):
                suffix = path.suffix.lower()
                if suffix not in (".txt", ".yaml", ".yml"):
                    continue
                if not path.is_file() or root.resolve() not in path.resolve().parents:
                    continue
                try:
                    content = path.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeError):
                    continue
                if suffix == ".txt":
                    key = path.relative_to(root).with_suffix("").as_posix().lower()
                    entries[key] = [line.strip() for line in content.splitlines()
                                    if line.strip() and not line.lstrip().startswith("#")]
                else:
                    import yaml
                    add_yaml(yaml.safe_load(content), ())

        return entries

    def populate(self, text, seed):
        rng = random.Random(seed)

        entries = self.wildcard_entries()

        def wildcard_options(pattern):
            pattern = pattern.lower().replace(chr(92), "/")
            return [value for key, values in entries.items() if fnmatchcase(key, pattern)
                    for value in values]

        def replace_group(match):
            content = match[1]
            count = re.fullmatch(r"(\d+)(?:-(\d+))?\$\$(?:(.*?)\$\$)?(.*)", content)
            low = high = 1
            separator = " "
            if count:
                low, high = sorted((int(count[1]), int(count[2] or count[1])))
                separator = count[3] if count[3] is not None else " "
                content = count[4]
            reference = re.fullmatch(r"__([\w.\-+/*\\]+?)__", content.strip())
            if count and reference:
                options = wildcard_options(reference[1])
            elif content.endswith(".txt") and "|" not in content:
                options = wildcard_options(content[:-4])
                return rng.choice(options) if options else content
            else:
                options = content.split("|")
            values, weights = [], []
            for option in options:
                weight = re.fullmatch(r"(\d+(?:\.\d+)?)::(.*)", option.strip())
                if weight:
                    probability = float(weight[1])
                    if probability > 0 and math.isfinite(probability):
                        values.append(weight[2].strip())
                        weights.append(probability)
                else:
                    values.append(option.strip())
                    weights.append(1.0)
            if not values:
                return match[0]
            if not count and all(weight == 1.0 for weight in weights):
                return rng.choice(values)
            amount = rng.randint(min(low, len(values)), min(high, len(values))) if count else 1
            chosen = []
            for _ in range(amount):
                scale = max(weights)
                index = rng.choices(range(len(values)), weights=[w / scale for w in weights])[0]
                chosen.append(values.pop(index))
                weights.pop(index)
            return separator.join(chosen)

        def replace_reference(match):
            options = wildcard_options(match[1])
            return rng.choice(options) if options else match[0]

        result = "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("#"))
        for _ in range(10):
            updated = re.sub(r"\{([^{}]+)\}", replace_group, result)
            updated = re.sub(r"__([\w.\-+/*\\]+?)__", replace_reference, updated)
            if updated == result:
                break
            result = updated

        return result


# Đăng ký node
NODE_CLASS_MAPPINGS = {
    "ShankWildcardEncode": ShankWildcardEncode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ShankWildcardEncode": "Shank Wildcard Encode (shanksimi)",
}

def populate_queued_prompt(payload):
    graph = payload.get("prompt", {})
    extra = payload.get("extra_data", {}).get("extra_pnginfo", {})
    workflow = extra.get("workflow", {})
    saved_nodes = {str(node["id"]): node for node in workflow.get("nodes", [])}
    resolver = ShankWildcardEncode()
    for node_id, entry in graph.items():
        if entry.get("class_type") != "ShankWildcardEncode":
            continue
        inputs = entry["inputs"]
        if inputs.get("mode") != "populate":
            continue
        text, seed = inputs.get("wildcard_text"), inputs.get("seed")
        if isinstance(seed, list) and len(seed) == 2 and seed[1] == 0:
            source = graph.get(str(seed[0]), {})
            if source.get("class_type") == "ShankSeed":
                seed = source.get("inputs", {}).get("seed")
                if seed in (-1, -2, -3):
                    continue
        if not isinstance(text, str) or type(seed) is not int:
            continue
        try:
            populated = resolver.populate(text, seed)
        except (ValueError, OSError):
            continue  # Let execution report the error on the node.
        inputs.update(populated_text=populated, mode="reproduce")
        saved = saved_nodes.get(str(node_id), {})
        values = saved.get("widgets_values")
        if isinstance(values, list) and len(values) >= 3:
            values[1:3] = [populated, "reproduce"]
        named = saved.get("widgets_values_named")
        if isinstance(named, dict):
            named.update(populated_text=populated, mode="reproduce")
    return payload


def register_server():
    from aiohttp import web
    from server import PromptServer
    import folder_paths

    server = PromptServer.instance
    server.add_on_prompt_handler(populate_queued_prompt)

    @server.routes.get("/shanksimi/wildcard-options")
    async def options(request):
        import asyncio

        entries = await asyncio.to_thread(ShankWildcardEncode.wildcard_entries)
        return web.json_response({
            "wildcards": sorted(entries),
            "loras": folder_paths.get_filename_list("loras"),
        })


register_server()
