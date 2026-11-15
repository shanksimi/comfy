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


def _read_info(sidecar):
    import json

    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    return data if isinstance(data, dict) and "trained_words" in data else None


def _save_info(sidecar, data):
    import json
    import os
    from tempfile import NamedTemporaryFile

    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=sidecar.parent, delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, sidecar)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _register_info_route():
    import asyncio
    from pathlib import Path
    from urllib.error import HTTPError, URLError

    import folder_paths
    from aiohttp import web
    from server import PromptServer

    pending = {}
    failures = {}
    worker = asyncio.Semaphore(1)

    async def lookup(path, sidecar):
        try:
            async with worker:
                if await asyncio.to_thread(_read_info, sidecar) is not None:
                    return
                data = await asyncio.to_thread(_model_info, path)
                await asyncio.to_thread(_save_info, sidecar, data)
        except HTTPError as error:
            if error.code == 404:
                failures[path] = "Civitai chưa có phiên bản khớp với file này."
            else:
                failures[path] = f"Civitai trả lỗi HTTP {error.code}."
        except (URLError, TimeoutError, ValueError, AttributeError):
            failures[path] = "Không đọc được thông tin từ Civitai."
        except OSError:
            failures[path] = "Không đọc được model hoặc không ghi được file thông tin bên cạnh model."
        finally:
            pending.pop(path, None)

    @PromptServer.instance.routes.get("/shanksimi/unet-info")
    async def info(request):
        name = request.query.get("name", "")
        if name not in folder_paths.get_filename_list("diffusion_models"):
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        path = folder_paths.get_full_path("diffusion_models", name)
        if path is None:
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        sidecar = Path(path + ".shank-info.json")
        try:
            saved = await asyncio.to_thread(_read_info, sidecar)
        except OSError:
            return web.json_response({"error": "Không đọc được file thông tin model."}, status=500)
        if saved is not None:
            return web.json_response(saved)
        if request.query.get("poll") == "1" and path in failures:
            return web.json_response({"error": failures[path]}, status=502)
        if path not in pending:
            failures.pop(path, None)
            pending[path] = asyncio.create_task(lookup(path, sidecar))
        return web.json_response({"status": "pending"}, status=202)


_register_info_route()
