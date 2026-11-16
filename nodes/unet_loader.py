import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from nodes import CheckpointLoaderSimple, UNETLoader


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


class ShankCheckpointLoader(CheckpointLoaderSimple):
    """Load a checkpoint and expose its selected filename."""

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "VAE", "model_name")
    OUTPUT_TOOLTIPS = (
        "Model dùng để khử nhiễu latent.",
        "Text encoder dùng để mã hóa prompt.",
        "VAE từ checkpoint.",
        "Tên file checkpoint, gồm cả thư mục con, để nối vào Metadata.",
    )
    DESCRIPTION = "Nạp checkpoint và trả tên file checkpoint cho Metadata."

    def load_checkpoint(self, ckpt_name):
        model, clip, vae = super().load_checkpoint(ckpt_name)
        return model, clip, vae, ckpt_name


def _model_info(path):
    import hashlib
    import json
    from urllib.error import URLError
    from urllib.request import urlopen

    digest = hashlib.sha256()
    with open(path, "rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    with urlopen("https://civitai.com/api/v1/model-versions/by-hash/" + digest.hexdigest(),
                 timeout=15) as response:
        version = json.load(response)
    info = _civitai_info(version)
    info["sha256"] = digest.hexdigest()
    model_id = version.get("modelId")
    if type(model_id) is int and not info["description"]:
        try:
            with urlopen(f"https://civitai.com/api/v1/models/{model_id}", timeout=8) as response:
                model = json.load(response)
            if isinstance(model, dict):
                info["description"] = _first_text(model.get("description"))
        except (URLError, TimeoutError, ValueError):
            pass
    return info


def _first_text(*values):
    return next((value.strip() for value in values if isinstance(value, str) and value.strip()), None)


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
    if type(model_id) is int:
        url = f"https://civitai.com/models/{model_id}"
        if type(version_id) is int:
            url += f"?modelVersionId={version_id}"
    return {
        "model": model_name,
        "version": version.get("name"),
        "base_model": version.get("baseModel"),
        "model_type": _first_text(model.get("type") if isinstance(model, dict) else None, version.get("type")),
        "description": _first_text(model.get("description") if isinstance(model, dict) else None),
        "notes": _first_text(version.get("notes"), version.get("instructions"), version.get("description")),
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
    sha256 = _first_text(data.get("sha256"), version.get("_sha256"), version.get("sha256"))
    if sha256 and re.fullmatch(r"[a-fA-F0-9]{64}", sha256):
        info["sha256"] = sha256.lower()
    for key, legacy_key in (("strength_min", "strengthMin"), ("strength_max", "strengthMax")):
        value = data.get(key, data.get(legacy_key))
        if value is not None:
            try:
                strength = float(value)
            except (ValueError, TypeError, OverflowError):
                continue
            if math.isfinite(strength):
                info[key] = strength
    info["model"] = info["model"] or data.get("model_name") or data.get("name")
    info["version"] = data.get("version") or data.get("version_name") or (
        info["version"] if version is not data or isinstance(data.get("model"), dict) or "modelId" in data else None
    )
    info["base_model"] = _first_text(data.get("baseModel"), data.get("base_model"), data.get("sd version"), info["base_model"])
    info["model_type"] = _first_text(data.get("modelType"), data.get("model_type"), data.get("type"), info["model_type"])
    info["description"] = _first_text(data.get("description"), info["description"])
    info["notes"] = _first_text(data.get("notes"), data.get("instructions"), data.get("usage"), data.get("userNote"), info["notes"])
    if info["description"] == info["notes"]:
        info["notes"] = None

    weight = data.get("preferred weight", data.get("preferred_weight"))
    if type(weight) in (int, float) or isinstance(weight, str) and weight.strip():
        info["preferred_weight"] = str(weight)

    for key in ("model", "version"):
        info[key] = _first_text(info[key])

    def words(items):
        if isinstance(items, str):
            items = items.split(",")
        for item in items if isinstance(items, list) else []:
            word = item.get("word") if isinstance(item, dict) else item
            if isinstance(word, str) and word.strip():
                yield word.strip()

    info["trained_words"] = list(dict.fromkeys([
        *words(data.get("trainedWords")),
        *words(data.get("trained_words")),
        *words(data.get("trigger_words")),
        *words(data.get("activation text")),
        *words(data.get("activation_text")),
        *words(info["trained_words"]),
        *words(version.get("triggerWords")),
    ]))
    info["images"] = list(dict.fromkeys([*_image_urls(data.get("images")), *info["images"]]))
    links = data.get("links")
    links = [data.get("url"), data.get("civitaiUrl"), data.get("civitai_url"), *(links if isinstance(links, list) else [])]
    if not info["url"]:
        info["url"] = next((link for link in links if isinstance(link, str)
                            and link.startswith("https://civitai.com/models/")), None)
    return info if any(value or key in ("strength_min", "strength_max") for key, value in info.items()) else None


def _local_sidecars(model_path):
    paths = [Path(model_path)]
    resolved = paths[0].resolve()
    if resolved != paths[0]:
        paths.append(resolved)
    return list(dict.fromkeys(
        candidate
        for path in paths
        for suffix in (".rgthree-info.json", ".metadata.json", ".civitai.info", ".info.json", ".json")
        for candidate in (Path(str(path) + suffix), path.with_suffix(suffix))
    ))


def _read_info(sidecar, local_sidecars):
    combined = {}
    for candidate in local_sidecars:
        try:
            info = _read_local_metadata(candidate)
        except OSError:
            continue
        if info is not None:
            for key, value in info.items():
                if key in ("trained_words", "images"):
                    combined[key] = list(dict.fromkeys([*combined.get(key, []), *value]))
                elif combined.get(key) is None and value is not None:
                    combined[key] = value
    if combined.get("notes") == combined.get("description"):
        combined.pop("notes", None)
    if any(value or key in ("strength_min", "strength_max") for key, value in combined.items()):
        return combined
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


_EDITABLE_FIELDS = {"model", "description", "notes", "trained_words", "strength_min", "strength_max"}


def _parse_info_edits(edits):
    if not isinstance(edits, dict) or edits.keys() - _EDITABLE_FIELDS:
        raise ValueError("Các trường chỉnh sửa không hợp lệ.")
    result = {}
    for key, value in edits.items():
        if value is None:
            result[key] = None
        elif key == "trained_words":
            if not isinstance(value, list) or len(value) > 300 or any(
                not isinstance(word, str) or len(word) > 300 for word in value
            ):
                raise ValueError("Danh sách trigger words không hợp lệ.")
            result[key] = list(dict.fromkeys(word.strip() for word in value if word.strip()))
        elif key in ("strength_min", "strength_max"):
            if type(value) not in (int, float) or not -100 <= value <= 100:
                raise ValueError("Strength Min/Max phải nằm trong khoảng −100 đến 100.")
            result[key] = value
        else:
            if not isinstance(value, str) or len(value) > (300 if key == "model" else 20000):
                raise ValueError("Tên, mô tả hoặc ghi chú quá dài hoặc không hợp lệ.")
            result[key] = value.strip()
    return result


def _user_info_path(model_path):
    return Path(str(Path(model_path).resolve()) + ".shank-user-info.json")


def _update_user_info(path, edits, source):
    sidecar = _user_info_path(path)
    saved = _read_json(sidecar) or {}
    for key, value in edits.items():
        if value is None:
            saved.pop(key, None)
        else:
            saved[key] = value
    effective = {**source, **saved}
    minimum, maximum = effective.get("strength_min"), effective.get("strength_max")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Strength Min phải nhỏ hơn hoặc bằng Strength Max.")
    _save_info(sidecar, saved)
    return saved


def _register_info_route():
    import asyncio
    from urllib.error import HTTPError, URLError

    import folder_paths
    from aiohttp import web
    from server import PromptServer

    pending = {}
    failures = {}
    worker = asyncio.Semaphore(1)
    edit_lock = asyncio.Lock()

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
    info_categories = {
        "/shanksimi/unet-info": "diffusion_models",
        "/shanksimi/lora-info": "loras",
        "/shanksimi/checkpoint-info": "checkpoints",
    }

    def model_path_for(category, name):
        if name in folder_paths.get_filename_list(category):
            return folder_paths.get_full_path(category, name)
        return None

    @routes.get("/shanksimi/model-preview")
    async def preview(request):
        category = request.query.get("category")
        if category not in info_categories.values():
            return web.Response(status=404)
        path = model_path_for(category, request.query.get("name", ""))
        image = await asyncio.to_thread(_local_preview, path) if path else None
        return web.FileResponse(image) if image else web.Response(status=404)

    @routes.post("/shanksimi/model-info-edits")
    async def save_edits(request):
        if request.content_type != "application/json":
            return web.json_response({"error": "Dữ liệu phải ở dạng JSON."}, status=415)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Dữ liệu chỉnh sửa không hợp lệ.")
            category = payload.get("category")
            name = payload.get("name")
            if category not in info_categories.values() or not isinstance(name, str):
                raise ValueError("Model cần chỉnh sửa không hợp lệ.")
            edits = _parse_info_edits(payload.get("edits"))
        except (ValueError, TypeError) as error:
            return web.json_response({"error": str(error)}, status=400)
        path = model_path_for(category, name)
        if path is None:
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        try:
            async with edit_lock:
                source = await asyncio.to_thread(_read_info, Path(path + ".shank-info.json"), _local_sidecars(path))
                overrides = await asyncio.to_thread(_update_user_info, path, edits, source or {})
        except ValueError as error:
            return web.json_response({"error": str(error)}, status=400)
        except OSError:
            return web.json_response({"error": "Không ghi được file thông tin cạnh model."}, status=500)
        return web.json_response({"overrides": overrides})

    @routes.get("/shanksimi/unet-info")
    @routes.get("/shanksimi/lora-info")
    @routes.get("/shanksimi/checkpoint-info")
    async def info(request):
        category = info_categories[request.path.removeprefix("/api")]
        name = request.query.get("name", "")
        path = model_path_for(category, name)
        if path is None:
            return web.json_response({"error": "Không tìm thấy file model đã chọn."}, status=404)
        sidecar = Path(path + ".shank-info.json")
        try:
            local_sidecars = await asyncio.to_thread(_local_sidecars, path)
            saved = await asyncio.to_thread(_read_info, sidecar, local_sidecars)
            overrides = await asyncio.to_thread(_read_json, _user_info_path(path)) or {}
        except OSError:
            return web.json_response({"error": "Không đọc được file thông tin model."}, status=500)
        if saved is not None or overrides:
            source = saved or {}
            return web.json_response({
                **source,
                **overrides,
                "images": _image_urls(source.get("images")),
                "has_local_preview": await asyncio.to_thread(_local_preview, path) is not None,
                "overrides": overrides,
                "original": {key: source[key] for key in _EDITABLE_FIELDS if key in source},
            })
        if request.query.get("poll") == "1" and path in failures:
            return web.json_response({"error": failures[path]}, status=502)
        if path not in pending:
            failures.pop(path, None)
            pending[path] = asyncio.create_task(lookup(path, sidecar, local_sidecars))
        return web.json_response({"status": "pending"}, status=202)


_register_info_route()
