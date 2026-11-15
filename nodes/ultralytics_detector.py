from pathlib import Path

import folder_paths


class ShankUltralyticsDetectorProvider:
    CATEGORY = "loaders"
    FUNCTION = "load_detector"
    RETURN_TYPES = ("BBOX_DETECTOR", "SEGM_DETECTOR")
    OUTPUT_TOOLTIPS = (
        "Detector tìm khung bao. Nối vào bbox_detector của FaceDetailer hoặc HandDetailer.",
        "Detector phân vùng theo pixel khi chọn model segm. Model bbox không tạo mask phân vùng.",
    )
    DESCRIPTION = "Nạp model Ultralytics để phát hiện khuôn mặt, bàn tay hoặc đối tượng khác."

    @staticmethod
    def register_model_paths():
        root = Path(folder_paths.models_dir) / "ultralytics"
        for kind in ("bbox", "segm"):
            key = f"ultralytics_{kind}"
            folder_paths.add_model_folder_path(key, str(root / kind))
            paths, extensions = folder_paths.folder_names_and_paths[key]
            folder_paths.folder_names_and_paths[key] = (paths, extensions | {".pt"})

    @classmethod
    def INPUT_TYPES(cls):
        cls.register_model_paths()
        choices = [
            f"{kind}/{name}" for kind in ("bbox", "segm")
            for name in folder_paths.get_filename_list(f"ultralytics_{kind}")
            if Path(name).suffix.lower() == ".pt"
        ]
        return {"required": {"model_name": (
            choices, {"tooltip": "Chọn weights bbox hoặc segm từ thư mục model đã cấu hình."},
        )}}

    def load_detector(self, model_name):
        from ultralytics import YOLO

        from ._ultralytics.detectors import NO_SEGM_DETECTOR, UltraBBoxDetector, UltraSegmDetector

        self.register_model_paths()
        kind, _, name = model_name.partition("/")
        if kind not in ("bbox", "segm") or Path(name).suffix.lower() != ".pt":
            raise ValueError("Chọn weights .pt thuộc nhóm bbox hoặc segm.")
        path = folder_paths.get_full_path_or_raise(f"ultralytics_{kind}", name)
        model = YOLO(path)
        return UltraBBoxDetector(model), UltraSegmDetector(model) if kind == "segm" else NO_SEGM_DETECTOR()
