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


_ANIMA_BREAK = "shanksimi.anima_break"


def _prepare_anima_break(model, encoded):
    import torch
    from comfy.patcher_extension import WrappersMP

    conditioning = []
    for group in zip(*encoded, strict=True):
        embeddings = [embedding for embedding, _ in group]
        options = group[0][1].copy()
        options.pop("t5xxl_ids")
        options.pop("t5xxl_weights", None)
        options.pop("attention_mask", None)
        options[_ANIMA_BREAK] = tuple(
            (embedding.shape[1], metadata["t5xxl_ids"], metadata.get("t5xxl_weights"))
            for embedding, metadata in group
        )
        conditioning.append([torch.cat(embeddings, dim=1), options])

    # The adapter belongs to the diffusion model and needs its loaded weights.
    wrapper_type = WrappersMP.PREPARE_SAMPLING
    if not model.get_wrappers(wrapper_type, _ANIMA_BREAK):
        model = model.clone()
        model.add_wrapper_with_key(wrapper_type, _ANIMA_BREAK, _adapt_anima_break)
    return model, conditioning


def _adapt_anima_break(executor, model, noise_shape, conds, *args, **kwargs):
    import torch
    from comfy import model_management

    inner_model, loaded_conds, loaded_models = executor(model, noise_shape, conds, *args, **kwargs)
    types = {}
    device = model.load_device
    with torch.inference_mode(), model_management.cuda_device_context(device):
        for kind, entries in loaded_conds.items():
            types[kind] = [
                _adapt_anima_entry(entry, inner_model, device) if _ANIMA_BREAK in entry else entry
                for entry in entries
            ]
    return inner_model, types, loaded_models


def _adapt_anima_entry(entry, model, device):
    import torch

    updated = entry.copy()
    sections = updated.pop(_ANIMA_BREAK)
    dtype = model.get_dtype_inference()
    lengths = [length for length, _, _ in sections]
    embeddings = updated["cross_attn"].to(device=device, dtype=dtype).split(lengths, dim=1)
    adapted = []
    for embedding, (_, ids, weights) in zip(embeddings, sections, strict=True):
        ids = ids.to(device=device).unsqueeze(0)
        if weights is not None:
            weights = weights.to(embedding).reshape(1, -1, 1)
        context = model.diffusion_model.preprocess_text_embeds(embedding, ids, t5xxl_weights=weights)
        # ComfyUI pads each adapter output to 512. Pad only once after joining.
        adapted.append(context[:, :ids.shape[1]])
    context = torch.cat(adapted, dim=1)
    updated["cross_attn"] = torch.nn.functional.pad(context, (0, 0, 0, max(0, 512 - context.shape[1])))
    return updated


class ShankWildcardEncode:
    DESCRIPTION = (
        "Mở rộng wildcard trong prompt, áp dụng LoRA được chỉ định và mã hóa "
        "prompt thành conditioning. BREAK tách các đoạn để mã hóa riêng. "
        "Với Anima, nối đầu ra sau khi xử lý Qwen và T5 của từng đoạn."
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
        "Model sau khi áp dụng LoRA. Nối đầu ra này vào sampler khi dùng BREAK với Anima.",
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
                    if loader_name != "nunchaku":
                        raise ValueError(f"LoRA loader unavailable: {loader_name}")
                    from ._nunchaku_lora.loader import load_lora

                    model = load_lora(model, file, model_weight)
                elif block:
                    from ._inspire_lbw.loader import LoraLoaderBlockWeight

                    model, clip, _ = LoraLoaderBlockWeight().doit(
                        model, clip, file, model_weight, clip_weight, False, 0,
                        block_a, block_b, "", block,
                    )
                else:
                    model, clip = loader.load_lora(model, clip, file, model_weight, clip_weight)
                applied.add(file)
            return ""

        prompt = re.sub(r"<lora:([^<>]+)>", apply_lora, populated)
        parts = [part.strip() for part in re.split(r"\bBREAK\b", prompt) if part.strip()]
        model, conditioning = self._encode_parts(model, clip, parts, nodes)
        return {"ui": {"text": [populated], "mode": [mode]},
                "result": (model, clip, conditioning, populated)}

    @staticmethod
    def _encode_parts(model, clip, parts, nodes):
        encoder = nodes.CLIPTextEncode()
        conditioning = encoder.encode(clip, parts[0] if parts else "")[0]
        if len(parts) < 2:
            return model, conditioning

        if conditioning and "t5xxl_ids" in conditioning[0][1]:
            encoded = [conditioning, *(encoder.encode(clip, part)[0] for part in parts[1:])]
            return _prepare_anima_break(model, encoded)

        for part in parts[1:]:
            current = encoder.encode(clip, part)[0]
            conditioning = nodes.ConditioningConcat().concat(conditioning, current)[0]
        return model, conditioning

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
