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
from .image_saver_simple import ShankMetadata, ShankImageSaverSimple
from .image_comparer import ShankImageComparer
from .power_lora_loader import ShankPowerLoraLoader
from .basic_info import ShankBasicInfo
from .simple_math import ShankSimpleMath

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

NODE_CLASS_MAPPINGS["ShankImageSaverSimple"] = ShankImageSaverSimple
NODE_DISPLAY_NAME_MAPPINGS["ShankImageSaverSimple"] = "Image Saver Simple (shanksimi)"

NODE_CLASS_MAPPINGS["ShankImageComparer"] = ShankImageComparer
NODE_DISPLAY_NAME_MAPPINGS["ShankImageComparer"] = "Image Comparer (shanksimi)"

NODE_CLASS_MAPPINGS["ShankPowerLoraLoader"] = ShankPowerLoraLoader
NODE_DISPLAY_NAME_MAPPINGS["ShankPowerLoraLoader"] = "Power Lora Loader (shanksimi)"

NODE_CLASS_MAPPINGS["ShankBasicInfo"] = ShankBasicInfo
NODE_DISPLAY_NAME_MAPPINGS["ShankBasicInfo"] = "Basic Info (shanksimi)"

NODE_CLASS_MAPPINGS["ShankSimpleMath"] = ShankSimpleMath
NODE_DISPLAY_NAME_MAPPINGS["ShankSimpleMath"] = "Simple Math (shanksimi)"

NODE_CLASS_MAPPINGS["ShankMetadata"] = ShankMetadata
NODE_DISPLAY_NAME_MAPPINGS["ShankMetadata"] = "Metadata"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
