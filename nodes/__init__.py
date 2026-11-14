from .load_image_metadata import NODE_CLASS_MAPPINGS as _META_NODE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _META_DISPLAY_MAPPINGS
from .wildcard_encode import NODE_CLASS_MAPPINGS as _WILDCARD_NODE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _WILDCARD_DISPLAY_MAPPINGS
from .seed import NODE_CLASS_MAPPINGS as _SEED_NODE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _SEED_DISPLAY_MAPPINGS
from .anima_lllite import NODE_CLASS_MAPPINGS as _LLLITE_NODE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _LLLITE_DISPLAY_MAPPINGS
from .unet_loader import ShankUNETLoader
from .aio_aux_preprocessor import ShankAIOAuxPreprocessor
from .reroute_primitive import ShankReroutePrimitive
from .ultimate_sd_upscale import ShankUltimateSDUpscale
from .batch_to_image import ShankBatchToImage
from .face_detailer import ShankFaceDetailer, ShankHanDetailer
from .ultralytics_detector import ShankUltralyticsDetectorProvider

NODE_CLASS_MAPPINGS = {**_META_NODE_MAPPINGS, **_WILDCARD_NODE_MAPPINGS, **_SEED_NODE_MAPPINGS, **_LLLITE_NODE_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**_META_DISPLAY_MAPPINGS, **_WILDCARD_DISPLAY_MAPPINGS, **_SEED_DISPLAY_MAPPINGS, **_LLLITE_DISPLAY_MAPPINGS}

NODE_CLASS_MAPPINGS["ShankUNETLoader"] = ShankUNETLoader
NODE_DISPLAY_NAME_MAPPINGS["ShankUNETLoader"] = "U-Net Loader with Filename (shanksimi)"

NODE_CLASS_MAPPINGS["ShankAIOAuxPreprocessor"] = ShankAIOAuxPreprocessor
NODE_DISPLAY_NAME_MAPPINGS["ShankAIOAuxPreprocessor"] = "AIO Aux Preprocessor (shanksimi)"

NODE_CLASS_MAPPINGS["ShankReroutePrimitive"] = ShankReroutePrimitive
NODE_DISPLAY_NAME_MAPPINGS["ShankReroutePrimitive"] = "Reroute Primitive (shanksimi)"

NODE_CLASS_MAPPINGS["ShankUltimateSDUpscale"] = ShankUltimateSDUpscale
NODE_DISPLAY_NAME_MAPPINGS["ShankUltimateSDUpscale"] = "Ultimate SD Upscale (shanksimi)"

NODE_CLASS_MAPPINGS["ShankBatchToImage"] = ShankBatchToImage
NODE_DISPLAY_NAME_MAPPINGS["ShankBatchToImage"] = "Batch to Image (shanksimi)"

NODE_CLASS_MAPPINGS["ShankFaceDetailer"] = ShankFaceDetailer
NODE_DISPLAY_NAME_MAPPINGS["ShankFaceDetailer"] = "FaceDetailer (shanksimi)"

NODE_CLASS_MAPPINGS["ShankHanDetailer"] = ShankHanDetailer
NODE_DISPLAY_NAME_MAPPINGS["ShankHanDetailer"] = "HandDetailer (shanksimi)"

NODE_CLASS_MAPPINGS["ShankUltralyticsDetectorProvider"] = ShankUltralyticsDetectorProvider
NODE_DISPLAY_NAME_MAPPINGS["ShankUltralyticsDetectorProvider"] = "Ultralytics Detector Provider (shanksimi)"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
