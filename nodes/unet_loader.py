from nodes import UNETLoader


class ShankUNETLoader(UNETLoader):
    """Load a diffusion model and expose its selected filename."""

    RETURN_TYPES = ("MODEL", "STRING")
    RETURN_NAMES = ("model", "filename")
    OUTPUT_TOOLTIPS = ("Loaded diffusion model", "Selected model filename, including any subfolder")
    CATEGORY = "loaders"
    DESCRIPTION = "Loads a U-Net or diffusion model and returns its filename."

    def load_unet(self, unet_name, weight_dtype):
        (model,) = super().load_unet(unet_name, weight_dtype)
        return model, unet_name
