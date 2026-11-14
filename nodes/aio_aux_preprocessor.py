class ShankAIOAuxPreprocessor:
    """Expose the installed ControlNet Aux AIO preprocessor under a Shank ID."""

    CATEGORY = "ControlNet Preprocessors"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"
    DESCRIPTION = "Runs a preprocessor from the installed comfyui_controlnet_aux extension."

    @staticmethod
    def upstream():
        from nodes import NODE_CLASS_MAPPINGS

        return NODE_CLASS_MAPPINGS.get("AIO_Preprocessor")

    @classmethod
    def INPUT_TYPES(cls):
        upstream = cls.upstream()
        if upstream is not None:
            return upstream.INPUT_TYPES()
        return {"required": {
            "preprocessor": (["none"],),
            "image": ("IMAGE",),
            "resolution": ("INT", {"default": 512, "min": 64, "max": 16384, "step": 64}),
        }}

    def execute(self, preprocessor, image, resolution=512):
        upstream = self.upstream()
        if upstream is None:
            if preprocessor == "none":
                return (image,)
            raise RuntimeError("Install comfyui_controlnet_aux to use AIO preprocessors.")
        return getattr(upstream(), upstream.FUNCTION)(
            preprocessor=preprocessor, image=image, resolution=resolution,
        )
