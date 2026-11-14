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


def _model_info(path):
    import hashlib
    import json
    from urllib.request import urlopen

    digest = hashlib.sha256()
    with open(path, "rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    with urlopen("https://civitai.com/api/v1/model-versions/by-hash/" + digest.hexdigest(),
                 timeout=15) as response:
        version = json.load(response)
    model = version.get("model") or {}
    model_id = version.get("modelId")
    version_id = version.get("id")
    url = None
    if type(model_id) is int and type(version_id) is int:
        url = f"https://civitai.com/models/{model_id}?modelVersionId={version_id}"
    return {
        "model": model.get("name"),
        "version": version.get("name"),
        "base_model": version.get("baseModel"),
        "trained_words": version.get("trainedWords") or [],
        "url": url,
    }


def _register_info_route():
    import asyncio
    from urllib.error import HTTPError, URLError

    import folder_paths
    from aiohttp import web
    from server import PromptServer

    @PromptServer.instance.routes.get("/shanksimi/unet-info")
    async def info(request):
        name = request.query.get("name", "")
        if name not in folder_paths.get_filename_list("diffusion_models"):
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        path = folder_paths.get_full_path("diffusion_models", name)
        if path is None:
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        try:
            return web.json_response(await asyncio.to_thread(_model_info, path))
        except HTTPError as error:
            if error.code == 404:
                return web.json_response({"error": "Civitai chưa có phiên bản khớp với file này."}, status=404)
            return web.json_response({"error": f"Civitai trả lỗi HTTP {error.code}."}, status=502)
        except (URLError, TimeoutError, ValueError):
            return web.json_response({"error": "Không đọc được thông tin từ Civitai."}, status=502)
        except OSError:
            return web.json_response({"error": "Không đọc được file model."}, status=500)


_register_info_route()
