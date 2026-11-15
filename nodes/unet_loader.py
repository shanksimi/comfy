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
    return _civitai_info(version)


def _civitai_info(version):
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


def _read_json(sidecar):
    import json

    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read_rgthree_info(sidecar):
    data = _read_json(sidecar)
    if data is None:
        return None

    raw = data.get("raw")
    version = raw.get("civitai") if isinstance(raw, dict) else None
    version = version if isinstance(version, dict) else {}
    if not isinstance(version.get("model"), dict):
        version = {**version, "model": {}}
    info = _civitai_info(version)
    info["model"] = info["model"] or data.get("name")
    info["base_model"] = data.get("baseModel") or info["base_model"]

    def words(items):
        for item in items if isinstance(items, list) else []:
            word = item.get("word") if isinstance(item, dict) else item
            if isinstance(word, str) and word.strip():
                yield word.strip()

    info["trained_words"] = list(dict.fromkeys([
        *words(data.get("trainedWords")),
        *words(info["trained_words"]),
        *words(version.get("triggerWords")),
    ]))
    links = data.get("links")
    if isinstance(links, list) and not info["url"]:
        info["url"] = next((link for link in links if isinstance(link, str)
                            and link.startswith("https://civitai.com/models/")), None)
    return info if any(info.values()) else None


def _read_info(sidecar, rgthree_sidecar):
    if rgthree_sidecar is not None:
        try:
            info = _read_rgthree_info(rgthree_sidecar)
        except OSError:
            info = None
        if info is not None:
            return info
    data = _read_json(sidecar)
    return data if data is not None and "trained_words" in data else None


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

    async def lookup(path, sidecar, rgthree_sidecar):
        try:
            async with worker:
                if await asyncio.to_thread(_read_info, sidecar, rgthree_sidecar) is not None:
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

    routes = PromptServer.instance.routes

    @routes.get("/shanksimi/unet-info")
    @routes.get("/shanksimi/lora-info")
    async def info(request):
        category = "loras" if request.path.endswith("/lora-info") else "diffusion_models"
        name = request.query.get("name", "")
        if name not in folder_paths.get_filename_list(category):
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        path = folder_paths.get_full_path(category, name)
        if path is None:
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        sidecar = Path(path + ".shank-info.json")
        rgthree_sidecar = Path(path + ".rgthree-info.json") if category == "loras" else None
        try:
            saved = await asyncio.to_thread(_read_info, sidecar, rgthree_sidecar)
        except OSError:
            return web.json_response({"error": "Không đọc được file thông tin model."}, status=500)
        if saved is not None:
            return web.json_response(saved)
        if request.query.get("poll") == "1" and path in failures:
            return web.json_response({"error": failures[path]}, status=502)
        if path not in pending:
            failures.pop(path, None)
            pending[path] = asyncio.create_task(lookup(path, sidecar, rgthree_sidecar))
        return web.json_response({"status": "pending"}, status=202)


_register_info_route()
