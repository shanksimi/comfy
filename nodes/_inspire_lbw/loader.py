# Adapted from ComfyUI-Inspire-Pack at d23db9a. See LICENSE.
import os
import re

import comfy.lora
import comfy.utils
import folder_paths
import numpy as np
import nodes


def is_numeric_string(input_str):
    return re.match(r'^-?\d+(\.\d+)?$', input_str) is not None


def load_lbw_preset(filename):
    path = os.path.join(os.path.dirname(__file__), "resources", filename)
    path = os.path.abspath(path)
    preset_list = []

    if os.path.exists(path):
        with open(path, 'r') as file:
            for line in file:
                preset_list.append(line.strip())

        return preset_list
    else:
        return []


def parse_unet_num(s):
    if s[1] == '.':
        return int(s[0])
    else:
        return int(s)


class LoraLoaderBlockWeight:
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(s):
        preset = ["Preset"]  # 20
        preset += load_lbw_preset("lbw-preset.txt")
        preset += load_lbw_preset("lbw-preset.custom.txt")
        preset = [name for name in preset if not name.startswith('@')]

        lora_names = folder_paths.get_filename_list("loras")
        lora_dirs = [os.path.dirname(name) for name in lora_names]
        lora_dirs = ["All"] + list(set(lora_dirs))

        return {"required": {"model": ("MODEL",),
                             "clip": ("CLIP", ),
                             "category_filter": (lora_dirs,),
                             "lora_name": (lora_names, ),
                             "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                             "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                             "inverse": ("BOOLEAN", {"default": False, "label_on": "True", "label_off": "False", "tooltip": "Apply the following weights for each block:\nTrue: 1 - weight\nFalse: weight"}),
                             "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": ""}),
                             "A": ("FLOAT", {"default": 4.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                             "B": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                             "preset": (preset,),
                             "block_vector": ("STRING", {"multiline": True, "placeholder": "block weight vectors", "default": "1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1", "pysssss.autocomplete": False}),
                             "bypass": ("BOOLEAN", {"default": False, "label_on": "True", "label_off": "False"}),
                             }
                }

    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    RETURN_NAMES = ("model", "clip", "populated_vector")
    FUNCTION = "doit"

    CATEGORY = "InspirePack/LoraBlockWeight"

    @staticmethod
    def validate(vectors):
        if len(vectors) < 12:
            return False

        for x in vectors:
            if x in ['R', 'r', 'U', 'u', 'A', 'a', 'B', 'b'] or is_numeric_string(x):
                continue
            else:
                subvectors = x.strip().split(' ')
                for y in subvectors:
                    y = y.strip()
                    if y not in ['R', 'r', 'U', 'u', 'A', 'a', 'B', 'b'] and not is_numeric_string(y):
                        return False

        return True

    @staticmethod
    def convert_vector_value(A, B, vector_value):
        def simple_vector(x):
            if x in ['U', 'u']:
                ratio = np.random.uniform(-1.5, 1.5)
                ratio = round(ratio, 2)
            elif x in ['R', 'r']:
                ratio = np.random.uniform(0, 3.0)
                ratio = round(ratio, 2)
            elif x == 'A':
                ratio = A
            elif x == 'a':
                ratio = A/2
            elif x == 'B':
                ratio = B
            elif x == 'b':
                ratio = B/2
            elif is_numeric_string(x):
                ratio = float(x)
            else:
                ratio = None

            return ratio

        v = simple_vector(vector_value)
        if v is not None:
            ratios = [v]
        else:
            ratios = [simple_vector(x) for x in vector_value.split(" ")]

        return ratios

    @staticmethod
    def norm_value(value):  # make to int if 1.0 or 0.0
        if value == 1:
            return 1
        elif value == 0:
            return 0
        else:
            return value

    @staticmethod
    def block_spec_parser(loaded, spec):
        if not spec.startswith("%"):
            return spec
        else:
            items = [x.strip() for x in spec[1:].split(',')]

            input_blocks_set = set()
            middle_blocks_set= set()
            output_blocks_set = set()
            double_blocks_set = set()
            single_blocks_set = set()

            for key, v in loaded.items():
                if isinstance(key, tuple):
                    k = key[0]
                else:
                    k = key

                k_unet = k[len("diffusion_model."):]

                if k_unet.startswith("input_blocks."):
                    k_unet_num = k_unet[len("input_blocks."):len("input_blocks.")+2]
                    k_unet_int = parse_unet_num(k_unet_num)
                    input_blocks_set.add(k_unet_int)
                elif k_unet.startswith("middle_block."):
                    k_unet_num = k_unet[len("middle_block."):len("middle_block.")+2]
                    k_unet_int = parse_unet_num(k_unet_num)
                    middle_blocks_set.add(k_unet_int)
                elif k_unet.startswith("output_blocks."):
                    k_unet_num = k_unet[len("output_blocks."):len("output_blocks.")+2]
                    k_unet_int = parse_unet_num(k_unet_num)
                    output_blocks_set.add(k_unet_int)
                elif k_unet.startswith("double_blocks."):
                    k_unet_num = k_unet[len("double_blocks."):len("double_blocks.") + 2]
                    k_unet_int = parse_unet_num(k_unet_num)
                    double_blocks_set.add(k_unet_int)
                elif k_unet.startswith("single_blocks."):
                    k_unet_num = k_unet[len("single_blocks."):len("single_blocks.") + 2]
                    k_unet_int = parse_unet_num(k_unet_num)
                    single_blocks_set.add(k_unet_int)

            pat1 = re.compile(r"(default|base)=([0-9.]+)")
            pat2 = re.compile(r"(in|out|mid|double|single)([0-9]+)-([0-9]+)=([0-9.]+)")
            pat3 = re.compile(r"(in|out|mid|double|single)([0-9]+)=([0-9.]+)")
            pat4 = re.compile(r"(in|out|mid|double|single)=([0-9.]+)")

            base_spec = None
            default_spec = 1.0

            for item in items:
                match = pat1.match(item)
                if match:
                    if match[1] == 'base':
                        base_spec = match[2]
                        continue

                    if match[1] == 'default':
                        default_spec = match[2]
                        continue

            if base_spec is None:
                base_spec = default_spec

            input_blocks = [default_spec] * len(input_blocks_set)
            middle_blocks = [default_spec] * len(middle_blocks_set)
            output_blocks = [default_spec] * len(output_blocks_set)
            double_blocks = [default_spec] * len(double_blocks_set)
            single_blocks = [default_spec] * len(single_blocks_set)

            for item in items:
                match = pat2.match(item)
                if match:
                    for x in range(int(match[2])-1, int(match[3])):
                        value = float(match[4])

                        if x < 0:
                            continue

                        if match[1] == 'in' and len(input_blocks) > x:
                            input_blocks[x] = value
                        elif match[1] == 'out' and len(output_blocks) > x:
                            output_blocks[x] = value
                        elif match[1] == 'mid' and len(middle_blocks) > x:
                            middle_blocks[x] = value
                        elif match[1] == 'double' and len(double_blocks) > x:
                            double_blocks[x] = value
                        elif match[1] == 'single' and len(single_blocks) > x:
                            single_blocks[x] = value

                    continue

                match = pat3.match(item)
                if match:
                    value = float(match[3])
                    x = int(match[2]) - 1

                    if x < 0:
                        continue

                    if match[1] == 'in' and len(input_blocks) > x:
                        input_blocks[x] = value
                    elif match[1] == 'out' and len(output_blocks) > x:
                        output_blocks[x] = value
                    elif match[1] == 'mid' and len(middle_blocks) > x:
                        middle_blocks[x] = value
                    elif match[1] == 'double' and len(double_blocks) > x:
                        double_blocks[x] = value
                    elif match[1] == 'single' and len(single_blocks) > x:
                        single_blocks[x] = value

                    continue

                match = pat4.match(item)
                if match:
                    value = float(match[2])

                    if match[1] == 'in':
                        input_blocks = [value] * len(input_blocks)
                    elif match[1] == 'out':
                        output_blocks = [value] * len(output_blocks)
                    elif match[1] == 'mid':
                        middle_blocks = [value] * len(middle_blocks)
                    elif match[1] == 'double':
                        double_blocks = [value] * len(double_blocks)
                    elif match[1] == 'single':
                        single_blocks = [value] * len(single_blocks)

                    continue

            # concat specs
            res = [str(base_spec)]
            for x in (input_blocks + middle_blocks + output_blocks + double_blocks + single_blocks):
                res.append(str(x))

            return ",".join(res)

    @staticmethod
    def load_lbw(model, clip, lora, inverse, seed, A, B, block_vector):
        key_map = comfy.lora.model_lora_keys_unet(model.model)
        key_map = comfy.lora.model_lora_keys_clip(clip.cond_stage_model, key_map)
        loaded = comfy.lora.load_lora(lora, key_map)

        block_vector = LoraLoaderBlockWeight.block_spec_parser(loaded, block_vector)

        block_vector = block_vector.split(":")
        if len(block_vector) > 1:
            block_vector = block_vector[1]
        else:
            block_vector = block_vector[0]

        vector = block_vector.split(",")

        if not LoraLoaderBlockWeight.validate(vector):
            preset_dict = load_preset_dict()
            if len(vector) > 0 and vector[0].strip() in preset_dict:
                vector = preset_dict[vector[0].strip()].split(",")
            else:
                raise ValueError(f"[LoraLoaderBlockWeight] invalid block_vector '{block_vector}'")

        # sort: input, middle, output, others
        input_blocks = []
        middle_blocks = []
        output_blocks = []
        double_blocks = []
        single_blocks = []
        others = []
        for key, v in loaded.items():
            if isinstance(key, tuple):
                k = key[0]
            else:
                k = key

            k_unet = k[len("diffusion_model."):]

            if k_unet.startswith("input_blocks."):
                k_unet_num = k_unet[len("input_blocks."):len("input_blocks.")+2]
                input_blocks.append((k, v, parse_unet_num(k_unet_num), k_unet))
            elif k_unet.startswith("middle_block."):
                k_unet_num = k_unet[len("middle_block."):len("middle_block.")+2]
                middle_blocks.append((k, v, parse_unet_num(k_unet_num), k_unet))
            elif k_unet.startswith("output_blocks."):
                k_unet_num = k_unet[len("output_blocks."):len("output_blocks.")+2]
                output_blocks.append((k, v, parse_unet_num(k_unet_num), k_unet))
            elif k_unet.startswith("double_blocks."):
                k_unet_num = k_unet[len("double_blocks."):len("double_blocks.")+2]
                double_blocks.append((key, v, parse_unet_num(k_unet_num), k_unet))
            elif k_unet.startswith("single_blocks."):
                k_unet_num = k_unet[len("single_blocks."):len("single_blocks.")+2]
                single_blocks.append((key, v, parse_unet_num(k_unet_num), k_unet))
            else:
                others.append((k, v, k_unet))

        input_blocks = sorted(input_blocks, key=lambda x: x[2])
        middle_blocks = sorted(middle_blocks, key=lambda x: x[2])
        output_blocks = sorted(output_blocks, key=lambda x: x[2])
        double_blocks = sorted(double_blocks, key=lambda x: x[2])
        single_blocks = sorted(single_blocks, key=lambda x: x[2])

        # prepare patch
        np.random.seed(seed % (2**31))
        populated_vector_list = []
        ratios = []
        ratio = 1.0
        vector_i = 1

        last_k_unet_num = None

        block_weights = {}
        muted_weights = []

        for k, v, k_unet_num, k_unet in (input_blocks + middle_blocks + output_blocks + double_blocks + single_blocks):
            if last_k_unet_num != k_unet_num and len(vector) > vector_i:
                ratios = LoraLoaderBlockWeight.convert_vector_value(A, B, vector[vector_i].strip())
                ratio = ratios.pop(0)

                if inverse:
                    populated_ratio = 1 - ratio
                else:
                    populated_ratio = ratio

                populated_vector_list.append(LoraLoaderBlockWeight.norm_value(populated_ratio))

                vector_i += 1
            else:
                if len(ratios) > 0:
                    ratio = ratios.pop(0)
                else:
                    pass # use last used ratio if no more user specified ratio is given

                if inverse:
                    populated_ratio = 1 - ratio
                else:
                    populated_ratio = ratio

            last_k_unet_num = k_unet_num

            if populated_ratio != 0:
                block_weights[k] = v, populated_ratio
            else:
                muted_weights.append(k)

        # prepare base patch
        ratios = LoraLoaderBlockWeight.convert_vector_value(A, B, vector[0].strip())
        ratio = ratios.pop(0)

        if inverse:
            populated_ratio = 1 - ratio
        else:
            populated_ratio = ratio

        populated_vector_list.insert(0, LoraLoaderBlockWeight.norm_value(populated_ratio))

        for k, v, k_unet in others:
            if populated_ratio != 0:
                block_weights[k] = v, populated_ratio
            else:
                muted_weights.append(k)

        populated_vector = ','.join(map(str, populated_vector_list))
        return block_weights, muted_weights, populated_vector

    @staticmethod
    def load_lora_for_models(model, clip, lora, strength_model, strength_clip, inverse, seed, A, B, block_vector):
        block_weights, muted_weights, populated_vector = LoraLoaderBlockWeight.load_lbw(model, clip, lora, inverse, seed, A, B, block_vector)

        new_modelpatcher = model.clone()
        new_clip = clip.clone()

        muted_weights = set(muted_weights)

        for k, v in block_weights.items():
            weights, ratio = v

            if k in muted_weights:
                pass
            elif 'text' in k or 'encoder' in k:
                new_clip.add_patches({k: weights}, strength_clip * ratio)
            else:
                new_modelpatcher.add_patches({k: weights}, strength_model * ratio)

        return new_modelpatcher, new_clip, populated_vector

    def doit(self, model, clip, lora_name, strength_model, strength_clip, inverse, seed, A, B, preset, block_vector, bypass=False, category_filter=None):
        if strength_model == 0 and strength_clip == 0 or bypass:
            return model, clip, ""

        lora_path = folder_paths.get_full_path("loras", lora_name)
        lora = None
        if self.loaded_lora is not None:
            if self.loaded_lora[0] == lora_path:
                lora = self.loaded_lora[1]
            else:
                temp = self.loaded_lora
                self.loaded_lora = None
                del temp

        if lora is None:
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            self.loaded_lora = (lora_path, lora)

        model_lora, clip_lora, populated_vector = LoraLoaderBlockWeight.load_lora_for_models(model, clip, lora, strength_model, strength_clip, inverse, seed, A, B, block_vector)
        return model_lora, clip_lora, populated_vector


def load_preset_dict():
    preset = ["Preset"]  # 20
    preset += load_lbw_preset("lbw-preset.txt")
    preset += load_lbw_preset("lbw-preset.custom.txt")

    dict = {}
    for x in preset:
        if not x.startswith('@'):
            item = x.split(':')
            if len(item) > 1:
                dict[item[0]] = item[1]

    return dict
