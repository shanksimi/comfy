import folder_paths


# The native loader resolves patch filenames through the model_patches category.
for controlnet_path in folder_paths.get_folder_paths("controlnet"):
    folder_paths.add_model_folder_path("model_patches", controlnet_path)


class ShankModelPatchLoader:
    RETURN_TYPES = ("MODEL_PATCH",)
    FUNCTION = "load_model_patch"
    CATEGORY = "model/loaders"
    DESCRIPTION = "Loads a ComfyUI model patch from model_patches or controlnet."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"name": (folder_paths.get_filename_list("model_patches"),)}}

    def load_model_patch(self, name):
        from comfy_extras.nodes_model_patch import ModelPatchLoader

        try:
            return ModelPatchLoader().load_model_patch(name)
        except UnboundLocalError as error:
            if "'model'" not in str(error):
                raise
            raise ValueError(
                f"ComfyUI did not recognize '{name}' as a model patch. "
                "For Anima LLLite, choose weights supported by Load Model Patch. "
                "Use Load ControlNet for standard ControlNet weights."
            ) from error
