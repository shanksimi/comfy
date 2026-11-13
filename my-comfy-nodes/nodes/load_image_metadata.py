"""
Load Image Metadata - Custom Node cho ComfyUI
Node đầu tiên của repo. Trích xuất metadata (EXIF, PNG info, kích thước, ...)
từ file ảnh và xuất ra dưới dạng văn bản.
"""

import os
import json
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

import folder_paths


def _get_exif_data(image):
    """Trích xuất dữ liệu EXIF từ ảnh PIL."""
    exif = image.getexif()
    if not exif:
        return {}
    result = {}
    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, tag_id)
        # Chuyển bytes thành string để tránh lỗi serialize
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="ignore")
            except Exception:
                value = str(value)
        result[str(tag)] = value
    return result


def _get_gps_info(exif_data):
    """Trích xuất thông tin GPS từ EXIF (nếu có)."""
    gps = {}
    for key in list(exif_data.keys()):
        if "GPS" in str(key):
            gps[key] = exif_data[key]
    return gps


class LoadImageMetadata:
    """
    Load metadata từ một file ảnh (EXIF, PNG text chunks, kích thước, định dạng, ...).
    """

    @classmethod
    def INPUT_TYPES(cls):
        # Lấy danh sách thư mục input của ComfyUI để gợi ý
        input_dir = folder_paths.get_input_directory()
        files = []
        if os.path.isdir(input_dir):
            files = [
                f for f in os.listdir(input_dir)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"))
            ]
        files.sort()

        return {
            "required": {
                "image_path": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "select_from_input": (["false"] + files,),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("metadata_json", "metadata_text", "width", "height", "format", "mode")
    FUNCTION = "load_metadata"
    CATEGORY = "image/metadata"
    OUTPUT_NODE = False

    def load_metadata(self, image_path="", select_from_input="false"):
        # Nếu người dùng chọn từ danh sách input folder, ưu tiên chọn đó
        if select_from_input and select_from_input != "false":
            image_path = os.path.join(folder_paths.get_input_directory(), select_from_input)

        if not image_path or not os.path.isfile(image_path):
            empty = "{}"
            return (
                empty,
                "Không tìm thấy file ảnh hoặc chưa cung cấp đường dẫn.",
                0,
                0,
                "",
                "",
            )

        try:
            with Image.open(image_path) as img:
                width, height = img.size
                fmt = img.format or ""
                mode = img.mode or ""

                # EXIF
                exif_data = _get_exif_data(img)
                gps_info = _get_gps_info(exif_data)

                # PNG metadata (text chunks)
                png_info = {}
                if fmt == "PNG":
                    try:
                        info = img.info
                        for k, v in info.items():
                            if isinstance(v, bytes):
                                try:
                                    v = v.decode("utf-8", errors="ignore")
                                except Exception:
                                    v = str(v)
                            png_info[str(k)] = v
                    except Exception:
                        png_info = {}

                metadata = {
                    "file": os.path.basename(image_path),
                    "path": os.path.abspath(image_path),
                    "width": width,
                    "height": height,
                    "format": fmt,
                    "mode": mode,
                    "exif": exif_data,
                    "gps": gps_info,
                    "png_info": png_info,
                    "file_size_bytes": os.path.getsize(image_path),
                }

            metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

            # Tạo bản tóm tắt văn bản dễ đọc
            lines = [
                f"File: {metadata['file']}",
                f"Path: {metadata['path']}",
                f"Format: {fmt}",
                f"Mode: {mode}",
                f"Size: {width} x {height}",
                f"File size: {metadata['file_size_bytes']} bytes",
                "",
            ]
            if exif_data:
                lines.append("=== EXIF ===")
                for k, v in exif_data.items():
                    lines.append(f"{k}: {v}")
                lines.append("")
            if gps_info:
                lines.append("=== GPS ===")
                for k, v in gps_info.items():
                    lines.append(f"{k}: {v}")
                lines.append("")
            if png_info:
                lines.append("=== PNG Info ===")
                for k, v in png_info.items():
                    lines.append(f"{k}: {v}")
                lines.append("")
            metadata_text = "\n".join(lines)

            return (metadata_json, metadata_text, width, height, fmt, mode)

        except Exception as e:
            err_msg = f"Lỗi khi đọc metadata: {str(e)}"
            return ("{}", err_msg, 0, 0, "", "")


# Đăng ký node
NODE_CLASS_MAPPINGS = {
    "LoadImageMetadata": LoadImageMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageMetadata": "Load Image Metadata",
}