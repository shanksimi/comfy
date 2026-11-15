# Adapted from Fannovel16/comfyui_controlnet_aux at b9abafa. See LICENSE.txt.
import importlib
import os
import sys
import traceback

os.environ.setdefault("NPU_DEVICE_COUNT", "0")
os.environ.setdefault("MMCV_WITH_OPS", "0")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from .utils import here, define_preprocessor_inputs, INPUT
from .log import log

# The bundled annotators use absolute imports, including in model configs.
for source in (here / "src", here / "src/custom_controlnet_aux", here / "src/custom_mmpkg"):
    if str(source) not in sys.path:
        sys.path.append(str(source))


def load_nodes():
    shorted_errors = []
    full_error_messages = []
    node_class_mappings = {}
    node_display_name_mappings = {}

    for filename in sorted((here / "node_wrappers").glob("*.py")):
        module_name = filename.stem
        if module_name.startswith('.'): continue #Skip hidden files created by the OS (e.g. [.DS_Store](https://en.wikipedia.org/wiki/.DS_Store))
        try:
            module = importlib.import_module(
                f".node_wrappers.{module_name}", package=__package__
            )
            node_class_mappings.update(getattr(module, "NODE_CLASS_MAPPINGS"))
            if hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS"):
                node_display_name_mappings.update(getattr(module, "NODE_DISPLAY_NAME_MAPPINGS"))

            log.debug(f"Imported {module_name} nodes")

        except AttributeError:
            pass  # wip nodes
        except Exception:
            error_message = traceback.format_exc()
            full_error_messages.append(error_message)
            error_message = error_message.splitlines()[-1]
            shorted_errors.append(
                f"Failed to import module {module_name} because {error_message}"
            )

    if len(shorted_errors) > 0:
        full_err_log = '\n\n'.join(full_error_messages)
        print(f"\n\nFull error log from comfyui_controlnet_aux: \n{full_err_log}\n\n")
        log.info(
            f"Some nodes failed to load:\n\t"
            + "\n\t".join(shorted_errors)
            + "\n\n"
            + "Check that you properly installed the dependencies.\n"
            + "If you think this is a bug, please report it on the github page (https://github.com/Fannovel16/comfyui_controlnet_aux/issues)"
        )
    return node_class_mappings, node_display_name_mappings

AUX_NODE_MAPPINGS, AUX_DISPLAY_NAME_MAPPINGS = load_nodes()

#For nodes not mapping image to image or has special requirements
AIO_NOT_SUPPORTED = ["InpaintPreprocessor", "MeshGraphormer+ImpactDetector-DepthMapPreprocessor", "DiffusionEdge_Preprocessor"]
AIO_NOT_SUPPORTED += ["SavePoseKpsAsJsonFile", "FacialPartColoringFromPoseKps", "UpperBodyTrackingFromPoseKps", "RenderPeopleKps", "RenderAnimalKps"]
AIO_NOT_SUPPORTED += ["Unimatch_OptFlowPreprocessor", "MaskOptFlow"]

def preprocessor_options():
    auxs = list(AUX_NODE_MAPPINGS.keys())
    auxs.insert(0, "none")
    for name in AIO_NOT_SUPPORTED:
        if name in auxs:
            auxs.remove(name)
    return auxs


PREPROCESSOR_OPTIONS = preprocessor_options()

class AIO_Preprocessor:
    @classmethod
    def INPUT_TYPES(s):
        return define_preprocessor_inputs(
            preprocessor=INPUT.COMBO(PREPROCESSOR_OPTIONS, default="none"),
            resolution=INPUT.RESOLUTION()
        )

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"

    CATEGORY = "ControlNet Preprocessors"

    def execute(self, preprocessor, image, resolution=512):
        if preprocessor == "none":
            return (image, )
        else:
            aux_class = AUX_NODE_MAPPINGS[preprocessor]
            input_types = aux_class.INPUT_TYPES()
            input_types = {
                **input_types["required"],
                **(input_types["optional"] if "optional" in input_types else {})
            }
            params = {}
            for name, input_type in input_types.items():
                if name == "image":
                    params[name] = image
                    continue

                if name == "resolution":
                    params[name] = resolution
                    continue

                if len(input_type) == 2 and ("default" in input_type[1]):
                    params[name] = input_type[1]["default"]
                    continue

                default_values = { "INT": 0, "FLOAT": 0.0 }
                if type(input_type[0]) is list:
                    for input_type_value in input_type[0]:
                        if input_type_value in default_values:
                            params[name] = default_values[input_type_value]
                            break
                else:
                    if input_type[0] in default_values:
                        params[name] = default_values[input_type[0]]

            return getattr(aux_class(), aux_class.FUNCTION)(**params)
