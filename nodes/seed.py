import random


class ShankSeed:
    """Seed control with a single output and queue-time selection in the UI."""

    LIMIT = 2**50
    MODES = (-1, -2, -3)
    CATEGORY = "utils/seed"
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("SEED",)
    FUNCTION = "get_seed"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": -1, "min": -cls.LIMIT, "max": cls.LIMIT}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO", "unique_id": "UNIQUE_ID"},
        }

    @classmethod
    def IS_CHANGED(cls, seed):
        return float("nan") if seed in cls.MODES else seed

    def get_seed(self, seed, prompt=None, extra_pnginfo=None, unique_id=None):
        if seed not in self.MODES:
            return (seed,)
        actual = random.randint(0, self.LIMIT)
        inputs = (prompt or {}).get(str(unique_id), {}).get("inputs", {})
        if inputs.get("seed") == seed:
            inputs["seed"] = actual
        workflow = (extra_pnginfo or {}).get("workflow") or {}
        for node in workflow.get("nodes", []):
            widgets = node.get("widgets_values") or []
            if str(node.get("id")) == str(unique_id) and widgets and widgets[0] == seed:
                widgets[0] = actual
                break
        return (actual,)


NODE_CLASS_MAPPINGS = {"ShankSeed": ShankSeed}
NODE_DISPLAY_NAME_MAPPINGS = {"ShankSeed": "Seed (shanksimi)"}
