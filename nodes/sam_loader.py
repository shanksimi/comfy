from pathlib import Path
from threading import RLock

import folder_paths


_SAM2_SIZES = {"tiny": "t", "small": "s", "base_plus": "b+", "large": "l"}
_SAM2_CONFIGS = {
    f"{version}_hiera_{size}": f"configs/{version}/{version}_hiera_{code}.yaml"
    for version in ("sam2", "sam2.1")
    for size, code in _SAM2_SIZES.items()
}


class ShankSAMPredictor:
    def __init__(self, model, predictor, device_mode):
        self.model = model
        self.predictor = predictor
        self.device_mode = device_mode
        self.lock = RLock()

    def prepare_device(self):
        self.lock.acquire()
        try:
            if self.device_mode == "AUTO":
                from comfy.model_management import get_torch_device

                self.model.to(get_torch_device())
        except BaseException:
            self.lock.release()
            raise

    def release_device(self):
        try:
            if self.device_mode == "AUTO":
                self.model.to("cpu")
        finally:
            self.lock.release()

    def predict(self, image, points, plabs, bbox, threshold):
        import numpy as np

        self.predictor.set_image(image)
        masks, scores, _ = self.predictor.predict(
            point_coords=np.asarray(points) if points is not None and len(points) else None,
            point_labels=np.asarray(plabs) if plabs is not None and len(plabs) else None,
            box=np.asarray(bbox) if bbox is not None else None,
        )
        matching = [mask for mask, score in zip(masks, scores) if score >= threshold]
        return matching or ([masks[int(np.argmax(scores))]] if len(scores) else [])


class ShankSAMLoader:
    CATEGORY = "loaders"
    FUNCTION = "load_model"
    RETURN_TYPES = ("SAM_MODEL",)
    OUTPUT_TOOLTIPS = ("Model SAM để nối vào sam_model_opt của Detailer.",)
    DESCRIPTION = "Nạp model Segment Anything để tạo mask phân vùng đối tượng."

    @classmethod
    def INPUT_TYPES(cls):
        if "sams" not in folder_paths.folder_names_and_paths:
            folder_paths.folder_names_and_paths["sams"] = (
                [str(Path(folder_paths.models_dir) / "sams")], {".pt", ".pth", ".safetensors"},
            )
        models = [
            name for name in folder_paths.get_filename_list("sams")
            if "hq" not in name.lower() and Path(name).suffix.lower() in {".pt", ".pth", ".safetensors"}
        ]
        return {"required": {
            "model_name": (models, {"tooltip": "Weights SAM hoặc SAM 2 trong ComfyUI/models/sams."}),
            "device_mode": (["AUTO", "Prefer GPU", "CPU"], {
                "tooltip": "AUTO đưa model lên thiết bị tính toán khi dự đoán. Prefer GPU giữ model trên thiết bị tính toán. CPU chạy trên CPU.",
            }),
        }}

    def load_model(self, model_name, device_mode):
        from comfy.model_management import get_torch_device
        from comfy.utils import load_torch_file

        self.INPUT_TYPES()  # Also register the model folder for direct execution.
        path = folder_paths.get_full_path_or_raise("sams", model_name)
        device = get_torch_device() if device_mode == "Prefer GPU" else "cpu"
        config = _SAM2_CONFIGS.get(Path(model_name).stem)
        if config:
            try:
                from sam2.build_sam import build_sam2
                from sam2.sam2_image_predictor import SAM2ImagePredictor
            except ImportError as error:
                raise RuntimeError("Weights SAM 2 cần thư viện sam2. Cài thêm bằng python -m pip install -r requirements-sam2.txt.") from error
            model = build_sam2(config, device=device)
            model.load_state_dict(load_torch_file(path, safe_load=True)["model"])
            predictor = SAM2ImagePredictor(model)
        else:
            from segment_anything import SamPredictor, sam_model_registry

            filename = Path(model_name).name
            kind = next((kind for kind in ("vit_h", "vit_l") if kind in filename), "vit_b")
            model = sam_model_registry[kind]()
            model.load_state_dict(load_torch_file(path, safe_load=True))
            model.to(device)
            predictor = SamPredictor(model)
        model.sam_wrapper = ShankSAMPredictor(model, predictor, device_mode)
        return (model,)
