"""ComfyUI-SeedVR2_VideoUpscaler, bundled at upstream commit 4490bd1 (Apache-2.0)."""

from .src.optimization.compatibility import ensure_triton_compat  # noqa: F401
from .src.interfaces import (
    SeedVR2LoadDiTModel,
    SeedVR2LoadVAEModel,
    SeedVR2TorchCompileSettings,
    SeedVR2VideoUpscaler,
)

_NODE_TYPES = (
    SeedVR2LoadDiTModel,
    SeedVR2LoadVAEModel,
    SeedVR2TorchCompileSettings,
    SeedVR2VideoUpscaler,
)

# ComfyUI's legacy pack loader accepts V3 node classes in the same mapping.
_SCHEMAS = [(node_type.GET_SCHEMA(), node_type) for node_type in _NODE_TYPES]
NODE_CLASS_MAPPINGS = {schema.node_id: node_type for schema, node_type in _SCHEMAS}
NODE_DISPLAY_NAME_MAPPINGS = {schema.node_id: schema.display_name for schema, _ in _SCHEMAS}
