from pathlib import Path
from urllib.parse import urlsplit

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


def _image_urls(images):
    urls = []
    for image in images if isinstance(images, list) else []:
        url = image.get("url") if isinstance(image, dict) else image
        if not isinstance(url, str) or (isinstance(image, dict) and image.get("type") == "video"):
            continue
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if parsed.scheme == "https" and parsed.hostname in ("image.civitai.com", "image.civitai.red"):
            urls.append(url)
    return list(dict.fromkeys(urls))


def _local_preview(model_path):
    path = Path(model_path)
    for extension in (".png", ".jpg", ".jpeg", ".webp"):
        for candidate in (path.with_suffix(extension), path.with_suffix(".preview" + extension)):
            if candidate.is_file() and not candidate.is_symlink():
                return candidate
    return None


def _civitai_info(version):
    model = version.get("model")
    model_name = model.get("name") if isinstance(model, dict) else model
    model_id = version.get("modelId")
    version_id = version.get("id")
    url = None
    if type(model_id) is int and type(version_id) is int:
        url = f"https://civitai.com/models/{model_id}?modelVersionId={version_id}"
    return {
        "model": model_name,
        "version": version.get("name"),
        "base_model": version.get("baseModel"),
        "trained_words": version.get("trainedWords") or [],
        "url": url,
        "images": _image_urls(version.get("images")),
    }


def _read_json(sidecar):
    import json

    try:
        data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read_local_metadata(sidecar):
    data = _read_json(sidecar)
    if data is None:
        return None

    raw = data.get("raw")
    version = next((candidate for candidate in (
        raw.get("civitai") if isinstance(raw, dict) else None,
        data.get("civitai"),
        data.get("modelVersion"),
        data.get("metadata"),
    ) if isinstance(candidate, dict) and candidate), data)
    info = _civitai_info(version)
    info["model"] = info["model"] or data.get("model_name") or data.get("name")
    info["version"] = data.get("version") or data.get("version_name") or (
        info["version"] if version is not data or isinstance(data.get("model"), dict) or "modelId" in data else None
    )
    info["base_model"] = data.get("baseModel") or data.get("base_model") or info["base_model"]

    def words(items):
        for item in items if isinstance(items, list) else []:
            word = item.get("word") if isinstance(item, dict) else item
            if isinstance(word, str) and word.strip():
                yield word.strip()

    info["trained_words"] = list(dict.fromkeys([
        *words(data.get("trainedWords")),
        *words(data.get("trained_words")),
        *words(data.get("trigger_words")),
        *words(info["trained_words"]),
        *words(version.get("triggerWords")),
    ]))
    info["images"] = list(dict.fromkeys([*_image_urls(data.get("images")), *info["images"]]))
    links = data.get("links")
    links = [data.get("url"), *(links if isinstance(links, list) else [])]
    if not info["url"]:
        info["url"] = next((link for link in links if isinstance(link, str)
                            and link.startswith("https://civitai.com/models/")), None)
    return info if any(info.values()) else None


def _local_sidecars(model_path):
    paths = [Path(model_path)]
    resolved = paths[0].resolve()
    if resolved != paths[0]:
        paths.append(resolved)
    return list(dict.fromkeys(
        candidate
        for path in paths
        for suffix in (".rgthree-info.json", ".metadata.json", ".civitai.info", ".info.json")
        for candidate in (Path(str(path) + suffix), path.with_suffix(suffix))
    ))


def _read_info(sidecar, local_sidecars):
    for candidate in local_sidecars:
        try:
            info = _read_local_metadata(candidate)
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
    from urllib.error import HTTPError, URLError

    import folder_paths
    from aiohttp import web
    from server import PromptServer

    pending = {}
    failures = {}
    worker = asyncio.Semaphore(1)

    async def lookup(path, sidecar, local_sidecars):
        try:
            async with worker:
                if await asyncio.to_thread(_read_info, sidecar, local_sidecars) is not None:
                    return
                data = await asyncio.to_thread(_model_info, path)
                await asyncio.to_thread(_save_info, sidecar, data)
        except HTTPError as error:
            if error.code == 403:
                failures[path] = "Không đọc được metadata cục bộ phù hợp. Civitai từ chối yêu cầu (HTTP 403)."
            elif error.code == 404:
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

    def model_path_for(category, name):
        if name in folder_paths.get_filename_list(category):
            return folder_paths.get_full_path(category, name)
        return None

    @routes.get("/shanksimi/model-preview")
    async def preview(request):
        category = request.query.get("category")
        if category not in ("loras", "diffusion_models"):
            return web.Response(status=404)
        path = model_path_for(category, request.query.get("name", ""))
        image = await asyncio.to_thread(_local_preview, path) if path else None
        return web.FileResponse(image) if image else web.Response(status=404)

    @routes.get("/shanksimi/unet-info")
    @routes.get("/shanksimi/lora-info")
    async def info(request):
        category = "loras" if request.path.endswith("/lora-info") else "diffusion_models"
        name = request.query.get("name", "")
        path = model_path_for(category, name)
        if path is None:
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        sidecar = Path(path + ".shank-info.json")
        try:
            local_sidecars = await asyncio.to_thread(_local_sidecars, path)
            saved = await asyncio.to_thread(_read_info, sidecar, local_sidecars)
        except OSError:
            return web.json_response({"error": "Không đọc được file thông tin model."}, status=500)
        if saved is not None:
            return web.json_response({
                **saved,
                "images": _image_urls(saved.get("images")),
                "has_local_preview": await asyncio.to_thread(_local_preview, path) is not None,
            })
        if request.query.get("poll") == "1" and path in failures:
            return web.json_response({"error": failures[path]}, status=502)
        if path not in pending:
            failures.pop(path, None)
            pending[path] = asyncio.create_task(lookup(path, sidecar, local_sidecars))
        return web.json_response({"status": "pending"}, status=202)


_register_info_route()
