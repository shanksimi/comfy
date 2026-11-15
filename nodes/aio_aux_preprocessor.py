class ShankAIOAuxPreprocessor:
    """Expose the bundled ControlNet Aux AIO preprocessor under a Shank ID."""

    CATEGORY = "ControlNet Preprocessors"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"
    DESCRIPTION = "Runs a preprocessor from the bundled ControlNet Aux annotators."

    @staticmethod
    def upstream():
        from ._controlnet_aux import AIO_Preprocessor

        return AIO_Preprocessor

    @classmethod
    def INPUT_TYPES(cls):
        return cls.upstream().INPUT_TYPES()

    def execute(self, preprocessor, image, resolution=512):
        upstream = self.upstream()
        return getattr(upstream(), upstream.FUNCTION)(
            preprocessor=preprocessor, image=image, resolution=resolution,
        )
