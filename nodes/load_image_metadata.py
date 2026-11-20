"""
Load Image + Metadata  (single-file ComfyUI custom node, no extra dependencies)

Copy this file into  ComfyUI/custom_nodes/  and restart ComfyUI (roi tai lai trang).

Cach dung:
  * Bam "Browse files..." tren node -> cua so duyet thu muc co anh thu nho.
      - Tab "Input folder": ComfyUI/input (co the Upload them anh vao day)
      - Tab "Drive folder": thu muc Drive (mac dinh mo thang thu muc cua ngay hom nay)
    Bam vao anh de chon / bo chon, chon 1 anh thi chay 1, chon nhieu anh thi load nhieu
    (cac node phia sau chay lan luot tung anh). Bam OK de xac nhan.
  * Danh sach anh da chon nam trong o "images" (moi dong 1 anh); co the go tay.
    Duong dan tuong doi = tinh tu ComfyUI/input, duong dan tuyet doi = giu nguyen.

  * Ve mask: trong cua so duyet file, bam nut but chi (goc tren trai moi thumbnail) de
    xem anh lon va ve mask. Bam \"Save mask\" -> luu PNG moi vao ComfyUI/input/masks/
    (vung ve = trong suot, giong quy uoc cua Load Image goc) va tu dong chon file do
    thay cho anh goc. Output MASK lay tu kenh alpha nen ra dung vung da ve.

Output: IMAGE, MASK, POSITIVE, NEGATIVE, METADATA (chuoi JSON day du: seed, steps,
cfg, sampler, scheduler, model, kich thuoc ...), FILENAME (ten anh khong duoi file),
FOLDER (thu muc chua anh) - dung de luu tag/caption thanh ten-anh.txt.

Doc metadata:
  * A1111 / Civitai "parameters" text  (Image Saver, A1111, Forge)
  * ComfyUI "prompt" JSON (best effort)

Neu anh khong co metadata, text rong nen workflow van chay binh thuong.
"""
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import tempfile
import zipfile
import zlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import torch
from PIL import Image, ImageChops, ImageOps, ImageSequence
from PIL.PngImagePlugin import PngInfo

import folder_paths
import node_helpers

# Thu muc Drive mac dinh (doi o day neu can). Cua so duyet file se mo thang thu muc
# theo ngay hom nay va cho phep di len thu muc cha (phan truoc ky hieu %).
DRIVE_FOLDER_DEFAULT = "/content/drive/MyDrive/SD-Data/Export/ComfyUI/%Y-%m-%d"
DRIVE_UTC_OFFSET_DEFAULT = 7  # Colab chay gio UTC; 7 = gio Viet Nam, dat 0 neu khong can

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".gif", ".webp", ".avi", ".m4v"}

# "Key: value, Key2: value2" with optional "quoted, values" (same idea as A1111)
_RE_PARAM = re.compile(r'\s*([\w ]+):\s*("(?:\\.|[^\\"])+"|[^,]*)(?:,|$)')


def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        try:
            return int(Decimal(str(v).strip()))
        except (ArithmeticError, ValueError, TypeError):
            return default


def _to_float(v, default=0.0):
    try:
        return float(str(v).strip())
    except Exception:
        return default


# ----------------------------------------------------------------------------
# A1111 / Civitai "parameters" text
# ----------------------------------------------------------------------------
def _parse_a1111(text):
    text = text.replace("\r\n", "\n").strip()
    settings, body = "", text

    idx = text.rfind("\nSteps: ")
    if idx != -1:
        settings, body = text[idx + 1:], text[:idx]
    elif text.startswith("Steps: "):
        settings, body = text, ""

    positive, negative = body.strip(), ""
    marker = "\nNegative prompt:"
    if body.startswith("Negative prompt:"):
        positive, negative = "", body[len("Negative prompt:"):].strip()
    elif marker in body:
        i = body.find(marker)
        positive, negative = body[:i].strip(), body[i + len(marker):].strip()

    params = {}
    for k, v in _RE_PARAM.findall(settings):
        v = v.strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        params[k.strip()] = v
    return positive, negative, params


# ----------------------------------------------------------------------------
# ComfyUI "prompt" JSON (API format) - best effort tracing
# ----------------------------------------------------------------------------
def _is_link(x):
    return isinstance(x, list) and len(x) == 2 and not isinstance(x[0], (list, dict))


def _resolve_text(prompt, ref, depth=0):
    if depth > 14:
        return ""
    if not _is_link(ref):
        return "" if ref is None else str(ref)
    node = prompt.get(str(ref[0]))
    if not isinstance(node, dict):
        return ""
    ins = node.get("inputs", {}) or {}
    ctype = node.get("class_type", "")
    if ctype == "StringConcatenate":
        a = _resolve_text(prompt, ins.get("string_a"), depth + 1)
        b = _resolve_text(prompt, ins.get("string_b"), depth + 1)
        d = _resolve_text(prompt, ins.get("delimiter"), depth + 1)
        return d.join((a, b))
    for key in ("text", "string", "value", "text_g", "prompt"):
        if key in ins:
            return _resolve_text(prompt, ins[key], depth + 1)
    for key in ("conditioning", "conditioning_1", "positive"):
        if key in ins:
            return _resolve_text(prompt, ins[key], depth + 1)
    return ""


def _resolve_value(prompt, ref, depth=0):
    if depth > 14:
        return None
    if not _is_link(ref):
        return ref
    node = prompt.get(str(ref[0]))
    if not isinstance(node, dict):
        return None
    ins = node.get("inputs", {}) or {}
    for key in ("value", "seed", "int", "number", "float", "steps", "cfg"):
        if key in ins:
            return _resolve_value(prompt, ins[key], depth + 1)
    return None


def _parse_comfy_prompt(prompt):
    """Return dict with positive/negative/seed/steps/cfg/sampler/scheduler (missing keys omitted)."""
    candidates = []
    for nid, node in prompt.items():
        if not isinstance(node, dict):
            continue
        ins = node.get("inputs", {}) or {}
        if "positive" in ins and "negative" in ins and ("seed" in ins or "noise_seed" in ins) and "steps" in ins:
            ctype = node.get("class_type", "")
            if ctype in ("KSampler", "KSamplerAdvanced"):
                rank = 0
            elif ctype == "UltimateSDUpscale":
                rank = 1
            else:
                rank = 2
            try:
                order = int(nid)
            except Exception:
                order = 10 ** 9
            candidates.append((rank, order, ins))
    if not candidates:
        return {}
    candidates.sort(key=lambda c: (c[0], c[1]))
    ins = candidates[0][2]
    out = {
        "positive": _resolve_text(prompt, ins.get("positive")),
        "negative": _resolve_text(prompt, ins.get("negative")),
    }
    seed = _resolve_value(prompt, ins.get("seed", ins.get("noise_seed")))
    steps = _resolve_value(prompt, ins.get("steps"))
    cfg = _resolve_value(prompt, ins.get("cfg"))
    sampler = _resolve_value(prompt, ins.get("sampler_name"))
    scheduler = _resolve_value(prompt, ins.get("scheduler"))
    if seed is not None:
        out["seed"] = _to_int(seed)
    if steps is not None:
        out["steps"] = _to_int(steps)
    if cfg is not None:
        out["cfg"] = _to_float(cfg)
    if isinstance(sampler, str):
        out["sampler"] = sampler
    if isinstance(scheduler, str):
        out["scheduler"] = scheduler
    return out


# ----------------------------------------------------------------------------
# JPEG / WEBP: A1111 stores the text in EXIF UserComment
# ----------------------------------------------------------------------------
def _exif_user_comment(img):
    try:
        exif = img.getexif()
        sub = exif.get_ifd(0x8769)
        uc = sub.get(0x9286)
        if isinstance(uc, bytes):
            if uc.startswith(b"UNICODE\x00"):
                raw = uc[8:]
                for enc in ("utf-16-be", "utf-16-le"):
                    try:
                        s = raw.decode(enc)
                        if "Steps:" in s or "Negative prompt" in s:
                            return s
                    except Exception:
                        pass
                return raw.decode("utf-16-be", errors="ignore")
            return uc.decode("utf-8", errors="ignore")
        if isinstance(uc, str):
            return uc
    except Exception:
        pass
    return ""


def read_metadata(img_info, img):
    """Returns (source, positive, negative, seed, steps, cfg, sampler, scheduler, model, gen_size)."""
    positive = negative = sampler = scheduler = model = ""
    seed = steps = 0
    cfg = 0.0
    source = "none"
    gen_size = ""

    params_text = img_info.get("parameters") or ""
    if not params_text:
        params_text = _exif_user_comment(img)

    if params_text:
        positive, negative, p = _parse_a1111(str(params_text))
        seed = _to_int(p.get("Seed"))
        steps = _to_int(p.get("Steps"))
        cfg = _to_float(p.get("CFG scale"))
        sampler = p.get("Sampler", "")
        scheduler = p.get("Schedule type", p.get("Scheduler", ""))
        model = p.get("Model", "")
        gen_size = p.get("Size", "")
        source = "A1111 / Image Saver"

    comfy = {}
    raw_prompt = img_info.get("prompt")
    if raw_prompt:
        try:
            comfy = _parse_comfy_prompt(json.loads(raw_prompt))
        except Exception:
            comfy = {}
    if comfy:
        if source == "none":
            source = "ComfyUI workflow"
            positive = comfy.get("positive", "")
            negative = comfy.get("negative", "")
        else:
            positive = positive or comfy.get("positive", "")
            negative = negative or comfy.get("negative", "")
        seed = seed or comfy.get("seed", 0)
        steps = steps or comfy.get("steps", 0)
        cfg = cfg or comfy.get("cfg", 0.0)
        sampler = sampler or comfy.get("sampler", "")
        scheduler = scheduler or comfy.get("scheduler", "")

    return source, positive, negative, seed, steps, cfg, sampler, scheduler, model, gen_size




# ----------------------------------------------------------------------------
# Selection helpers
# ----------------------------------------------------------------------------
def _is_image_name(name):
    return os.path.splitext(name)[1].lower() in IMAGE_EXTS


def _resolve_drive_folder(template, utc_offset_hours):
    """Thay ky hieu strftime (%Y-%m-%d ...) bang ngay hien tai (theo mui gio utc_offset)."""
    now = datetime.now(timezone.utc) + timedelta(hours=utc_offset_hours)
    return now.strftime(str(template).strip())


def _resolve_entry(entry):
    """Duong dan tuyet doi -> giu nguyen; duong dan tuong doi -> tinh tu ComfyUI/input."""
    e = entry.strip().strip('"')
    if os.path.isabs(e):
        return _thumb_path_for_entry(e, "")
    return _join_inside(folder_paths.get_input_directory(), e)[0]


def _parse_selection(images):
    """Moi dong = 1 anh. Tra ve list duong dan, bao loi ro rang neu thieu file."""
    entries = [ln.strip() for ln in str(images or "").splitlines() if ln.strip()]
    if not entries:
        raise ValueError("Chua chon anh nao. Bam 'Browse files...' de chon anh.")
    paths = []
    for e in entries:
        p = _resolve_entry(e)
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Khong tim thay file: {p}")
        paths.append(p)
    return paths


# ----------------------------------------------------------------------------
# Load one image
# ----------------------------------------------------------------------------
def _load_one(path):
    img = node_helpers.pillow(Image.open, path)

    info = dict(img.info or {})
    fmt = img.format or os.path.splitext(path)[1].lstrip(".").upper()
    source, pos, neg, seed, steps, cfg, sampler, scheduler, model, gen_size = read_metadata(info, img)

    img = node_helpers.pillow(ImageOps.exif_transpose, img)
    if img.mode == "I":
        img = img.point(lambda i: i * (1 / 255))
    rgb = img.convert("RGB")
    arr = np.array(rgb).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr)[None,]
    if "A" in img.getbands():
        m = np.array(img.getchannel("A")).astype(np.float32) / 255.0
        mask = 1.0 - torch.from_numpy(m)
    else:
        mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

    w, h = rgb.size
    metadata = json.dumps({
        "file": os.path.basename(path),
        "format": fmt,
        "width": int(w),
        "height": int(h),
        "metadata_source": source,
        "positive": pos,
        "negative": neg,
        "seed": int(seed),
        "steps": int(steps),
        "cfg": float(cfg),
        "sampler": sampler,
        "scheduler": scheduler,
        "model": model,
        "generated_size": gen_size,
    }, ensure_ascii=False, indent=2)

    stem = os.path.splitext(os.path.basename(path))[0]
    return tensor, mask, pos, neg, metadata, stem, os.path.dirname(path)


class ShankImageLoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Moi dong 1 anh; dien bang nut "Browse files..." (hoac go tay)
                "images": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                # Thu muc Drive mo dau trong cua so duyet file (ho tro %Y-%m-%d ...)
                "drive_folder": ("STRING", {"default": os.environ.get("SHANK_COMFY_DRIVE_ROOT") or DRIVE_FOLDER_DEFAULT, "multiline": False}),
            },
        }

    CATEGORY = "image"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "MASK", "POSITIVE", "NEGATIVE", "METADATA", "FILENAME", "FOLDER")
    # Moi output la LIST -> chon N anh thi cac node phia sau chay N lan
    OUTPUT_IS_LIST = (True,) * 7
    FUNCTION = "load"

    def load(self, images, drive_folder=""):
        paths = _parse_selection(images)
        rows = [_load_one(p) for p in paths]
        return tuple(list(col) for col in zip(*rows))

    @classmethod
    def IS_CHANGED(cls, images, drive_folder=""):
        try:
            paths = _parse_selection(images)
        except Exception:
            return float("nan")  # loi -> luon chay lai de hien thong bao loi
        m = hashlib.sha256()
        if len(paths) == 1:
            with open(paths[0], "rb") as f:
                m.update(f.read())
        else:
            for p in paths:
                st = os.stat(p)
                m.update(f"{p}|{st.st_mtime_ns}|{st.st_size}".encode())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, images, **kwargs):
        try:
            _parse_selection(images)
        except Exception as e:
            return str(e)
        return True


# ----------------------------------------------------------------------------
# Giao dien: nut "Browse files..." mo cua so duyet thu muc (anh thu nho, chon 1 hoac
# nhieu anh, upload vao input folder). Server route + 1 file JS tu sinh ra thu muc
# tam; khong can them file nao.
# ----------------------------------------------------------------------------
_JS = r"""
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function el(tag, style, text) {
  const e = document.createElement(tag);
  if (style) Object.assign(e.style, style);
  if (text !== undefined) e.textContent = text;
  return e;
}

let lastTab = "input_folder";

app.registerExtension({
  name: "ShankImageLoad.Browser",
  nodeCreated(node) {
    const isVideoLoader = node.comfyClass === "VHS_LoadVideoFFmpeg";
    const isVideoSaver = node.comfyClass === "VHS_VideoCombine";
    const isVideo = isVideoLoader || isVideoSaver;
    const isSaver = isVideoSaver || node.comfyClass === "ShankImageSaverSimple";
    if (!isSaver && !isVideoLoader && node.comfyClass !== "ShankImageLoad") return;
    const kind = isVideo ? "video" : "image";
    const mediaLabel = isVideo ? "video" : "ảnh";
    const get = (n) => (node.widgets || []).find((x) => x.name === n);
    const folderValue = () => { const w = get("drive_folder"); return w ? String(w.value || "") : ""; };
    const getEntries = () => {
      if (isVideoLoader) {
        const value = get("video")?.value;
        return value ? [value.replace(/ \[input\]$/, "")] : [];
      }
      const w = get("images");
      if (!w) return [];
      // uu tien gia tri that su dang hien trong o text (tranh doc gia tri cu)
      const dom = w.inputEl || w.element;
      let raw = w.value;
      if (dom && typeof dom.value === "string" && dom.value.trim()) raw = dom.value;
      const seen = new Set();
      return String(raw || "").split("\n").map((s) => s.trim()).filter((s) => {
        if (!s || seen.has(s)) return false;
        seen.add(s);
        return true;
      });
    };

    // ---- xem truoc tren node (toi da 4 anh dau) ----
    let previewToken = 0;
    function updatePreview() {
      if (isVideo) return;
      const token = ++previewToken;
      const entries = getEntries().slice(0, 4);
      if (!entries.length) {
        try {
          node.imgs = [];
          node.imageIndex = null;
          node.overIndex = null;
          if (node.computeSize && node.setSize) {
            const sz = node.computeSize();
            node.setSize([Math.max(node.size[0], sz[0]), sz[1]]);
          }
          node.setDirtyCanvas(true, true);
        } catch (e) { console.warn("ShankImageLoad clear preview:", e); }
        return;
      }
      Promise.all(entries.map((e) => new Promise((res) => {
        const im = new Image();
        im.onload = () => res(im);
        im.onerror = () => res(null);
        im.src = api.apiURL("/load_image_metadata/thumb?" + new URLSearchParams({ entry: e, drive_folder: folderValue() }).toString());
      }))).then((list) => {
        if (token !== previewToken) return;
        try {
          node.imgs = list.filter(Boolean);
          node.imageIndex = null;
          if (node.setSizeForImage) node.setSizeForImage();
          node.setDirtyCanvas(true, true);
        } catch (e) {
          console.warn("ShankImageLoad preview:", e);
        }
      });
    }

    function setEntries(list) {
      if (isVideoLoader) {
        const widget = get("video");
        const value = list[0];
        if (!widget || !value) return;
        const choices = widget.options?.values;
        if (Array.isArray(choices) && !choices.includes(value)) widget.options.values = [...choices, value];
        widget.value = value;
        widget.callback?.(value);
        node.setDirtyCanvas(true, true);
        return;
      }
      const w = get("images");
      if (!w) return;
      const v = list.join("\n");
      try {
        w.value = v;
        const dom = w.inputEl || w.element;
        if (dom && dom.value !== undefined && dom.value !== v) dom.value = v;
        if (w.callback) w.callback(v);
      } catch (e) { console.warn("ShankImageLoad setEntries:", e); }
      // tre 1 nhip de ComfyUI xu ly xong su kien click nut truoc khi doi giao dien node
      requestAnimationFrame(() => {
        try { updatePreview(); node.setDirtyCanvas(true, true); } catch (e) {}
      });
    }

    const browseBtn = node.addWidget("button", "Browse files...", null, () => openBrowser());
    browseBtn.serialize = false;
    if (isVideo) browseBtn.options.serialize = false;
    if (!isSaver && !isVideo) {
      const clearBtn = node.addWidget("button", "Clear selection", null, () => setEntries([]));
      clearBtn.serialize = false;
    }

    // ---- cua so duyet file ----
    function openBrowser() {
      const existing = getEntries();          // anh da chon tu truoc: giu nguyen, chi them vao
      const selected = new Set(existing);
      let tab = isVideo ? (isVideoSaver ? "output_folder" : "input_folder")
        : (isSaver ? "drive_folder" : lastTab);
      let data = null;
      let marks = [];
      let actionBusy = false;

      const overlay = el("div", {
        position: "fixed", inset: "0", background: "rgba(0,0,0,0.6)", zIndex: "10000",
        display: "flex", alignItems: "center", justifyContent: "center",
      });
      const panel = el("div", {
        width: "min(1000px, 94vw)", height: "min(740px, 88vh)",
        background: "var(--comfy-menu-bg, #202020)", color: "var(--input-text, #ddd)",
        border: "1px solid var(--border-color, #444)", borderRadius: "8px",
        display: "flex", flexDirection: "column", overflow: "hidden", fontFamily: "sans-serif",
      });
      const header = el("div", {
        display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", padding: "8px 10px",
        borderBottom: "1px solid var(--border-color, #444)",
      });
      const baseBtn = {
        padding: "4px 10px", cursor: "pointer", borderRadius: "4px",
        background: "var(--comfy-input-bg, #333)", color: "var(--input-text, #ddd)",
        border: "1px solid var(--border-color, #555)",
      };
      const mkBtn = (label) => el("button", { ...baseBtn }, label);

      const inputTab = mkBtn("Input folder");
      const driveTab = mkBtn("Drive folder");
      const upBtn = mkBtn("Up");
      const selAllBtn = mkBtn("Select all");
      const clearSelBtn = mkBtn("Clear");
      const uploadBtn = mkBtn("Upload");
      const okBtn = mkBtn("OK");
      const cancelBtn = mkBtn(isSaver ? "Đóng" : "Cancel");
      okBtn.style.background = "#2d7ff9";
      okBtn.style.color = "#fff";
      const fileInput = el("input", { display: "none" });
      fileInput.type = "file";
      fileInput.multiple = !isVideo;
      fileInput.accept = isVideo ? ".mp4,.mov,.webm,.mkv,.gif,.webp,.avi,.m4v" : "image/*";
      if (isSaver) {
        header.append(upBtn, el("div", { flex: "1" }), cancelBtn);
      } else {
        if (!isVideo) header.append(inputTab, driveTab);
        header.append(upBtn, uploadBtn, fileInput, el("div", { flex: "1" }), okBtn, cancelBtn);
      }

      const toolbar = el("div", {
        display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", padding: "8px 10px",
        borderBottom: "1px solid var(--border-color, #444)",
      });
      selAllBtn.textContent = "Chọn tất cả";
      clearSelBtn.textContent = "Bỏ chọn";
      const countLabel = el("span", { marginRight: "auto", fontSize: "12px" });
      const downloadBtn = mkBtn("Tải " + mediaLabel);
      const stripBtn = mkBtn("Xoá metadata");
      const deleteBtn = mkBtn("Xoá " + mediaLabel);
      deleteBtn.style.color = "#ff9e9e";
      const actionStatus = el("div", {
        width: "100%", maxHeight: "70px", overflow: "auto", fontSize: "12px", overflowWrap: "anywhere",
      });
      actionStatus.hidden = true;
      actionStatus.setAttribute("role", "status");
      if (!isVideoLoader) toolbar.append(selAllBtn, clearSelBtn);
      toolbar.append(countLabel);
      if (!isVideoLoader) toolbar.append(downloadBtn);
      if (!isVideo) toolbar.append(stripBtn);
      if (!isVideoLoader) toolbar.append(deleteBtn);
      toolbar.append(actionStatus);

      const pathLbl = el("div", {
        padding: "4px 10px", fontSize: "12px", opacity: "0.8", overflow: "hidden",
        textOverflow: "ellipsis", whiteSpace: "nowrap",
      });
      const body = el("div", {
        flex: "1", overflow: "auto", padding: "10px", display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "8px", alignContent: "start",
      });
      panel.append(header, toolbar, pathLbl, body);
      overlay.append(panel);

      function close() {
        document.removeEventListener("keydown", onKey);
        overlay.remove();
      }
      function onKey(ev) { if (ev.key === "Escape" && !overlay.querySelector("dialog[open]")) close(); }
      document.addEventListener("keydown", onKey);
      overlay.addEventListener("mousedown", (ev) => { if (ev.target === overlay) close(); });
      cancelBtn.onclick = close;

      const join = (a, b) => (a ? a + "/" + b : b);
      const checkedFiles = () => data?.files.filter((f) => selected.has(f.value)) ?? [];
      function refreshMarks() {
        marks.forEach((mark) => mark());
        const count = checkedFiles().length;
        countLabel.textContent = count + " " + mediaLabel + " đã chọn trong thư mục này";
        okBtn.textContent = "OK (" + selected.size + ")";
        okBtn.disabled = actionBusy || (isVideoLoader && !selected.size);
        selAllBtn.disabled = actionBusy || !data?.files.length;
        clearSelBtn.disabled = actionBusy || !selected.size;
        for (const button of [downloadBtn, stripBtn, deleteBtn]) {
          button.disabled = actionBusy || !count;
        }
      }

      function showStatus(message) {
        actionStatus.textContent = message;
        actionStatus.hidden = !message;
      }

      async function runAction(action, files = checkedFiles()) {
        if (actionBusy || !data || !files.length) return;
        const folder = data;
        const version = loadVersion;
        const driveFolder = folderValue();
        const count = files.length;
        if (action === "download" && count === 1) {
          const file = files[0];
          const query = new URLSearchParams({ entry: file.value, kind, source: tab, drive_folder: driveFolder, download: "1" });
          const link = el("a");
          link.href = api.apiURL("/load_image_metadata/full?" + query);
          link.download = file.name;
          link.click();
          return;
        }
        if (action !== "download") {
          const verb = action === "delete" ? "Xoá vĩnh viễn" : "Xoá metadata khỏi";
          const target = count === 1 ? mediaLabel + " “" + files[0].name + "”" : count + " " + mediaLabel + " trong thư mục này";
          if (!window.confirm(verb + " " + target + "?")) return;
        }
        actionBusy = true;
        refreshMarks();
        showStatus(action === "download" ? "Đang tạo ZIP…" : "Đang xử lý " + count + " " + mediaLabel + "…");
        try {
          const response = await api.fetchApi("/load_image_metadata/actions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              action, kind, source: tab, drive_folder: driveFolder,
              paths: files.map((file) => join(folder.path, file.name)),
            }),
          });
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || response.statusText);
          }
          if (action === "download") {
            const url = URL.createObjectURL(await response.blob());
            const link = el("a");
            link.href = url;
            link.download = isVideo ? "comfy-videos.zip" : "comfy-images.zip";
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 30000);
            showStatus("");
            return;
          }
          const result = await response.json();
          const succeeded = new Set(result.done);
          if (action === "delete") {
            const removed = new Set(files.filter((file) => succeeded.has(join(folder.path, file.name)))
              .map((file) => file.value));
            for (const entry of removed) selected.delete(entry);
            const entries = getEntries();
            const remaining = entries.filter((entry) => !removed.has(entry));
            if (remaining.length !== entries.length) setEntries(remaining);
          }
          const failures = result.errors.map(({ path, error }) => path.split("/").pop() + " (" + error + ")");
          showStatus("Đã xử lý " + succeeded.size + "/" + count + " " + mediaLabel + "."
            + (failures.length ? " Lỗi: " + failures.join(", ") : ""));
          if (overlay.isConnected && version === loadVersion) await load(folder.path);
        } catch (error) {
          showStatus("Không hoàn tất thao tác: " + error.message);
        } finally {
          actionBusy = false;
          refreshMarks();
        }
      }

      downloadBtn.onclick = () => runAction("download");
      stripBtn.onclick = () => runAction("strip_metadata");
      deleteBtn.onclick = () => runAction("delete");

      function styleTabs() {
        const on = (b, active) => { b.style.background = active ? "#2d7ff9" : "var(--comfy-input-bg, #333)"; b.style.color = active ? "#fff" : "var(--input-text, #ddd)"; };
        on(inputTab, tab === "input_folder");
        on(driveTab, tab === "drive_folder");
        uploadBtn.style.display = tab === "input_folder" ? "" : "none";
      }

      let loadVersion = 0;
      async function load(path) {
        const version = ++loadVersion;
        const source = tab;
        const driveFolder = folderValue();
        styleTabs();
        marks = [];
        data = null;
        refreshMarks();
        body.replaceChildren(el("div", { padding: "10px" }, "Loading..."));
        const params = new URLSearchParams({ source, kind, drive_folder: driveFolder });
        if (isSaver && !isVideo) params.set("export_today", "1");
        if (path !== null && path !== undefined) params.set("path", path);
        let d;
        try {
          const r = await api.fetchApi("/load_image_metadata/browse?" + params.toString());
          d = await r.json();
        } catch (e) {
          if (version === loadVersion) body.replaceChildren(el("div", { padding: "10px" }, "Loi ket noi: " + e));
          return;
        }
        if (version !== loadVersion) return;
        if (d.error) {
          data = null;
          pathLbl.textContent = "";
          body.replaceChildren(el("div", { padding: "10px" }, "Loi: " + d.error));
          refreshMarks();
          return;
        }
        data = d;
        pathLbl.textContent = d.abs;
        upBtn.style.opacity = d.path ? "1" : "0.4";
        body.replaceChildren();

        for (const name of d.dirs) {
          const t = el("div", {
            cursor: "pointer", padding: "10px 6px", textAlign: "center", borderRadius: "6px",
            background: "var(--comfy-input-bg, #333)", fontSize: "12px", overflow: "hidden",
          });
          t.append(el("div", { fontSize: "40px" }, "\u{1F4C1}"),
            el("div", { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, name));
          t.title = name;
          t.onclick = () => load(join(d.path, name));
          body.append(t);
        }
        for (const f of d.files) {
          const t = el("div", {
            position: "relative", cursor: "pointer", padding: "4px", borderRadius: "6px",
            textAlign: "center", background: "var(--comfy-input-bg, #333)", fontSize: "11px",
          });
          const img = el("img", { width: "100%", height: "110px", objectFit: "contain", background: "#111" });
          img.loading = "lazy";
          const checkbox = el("input", {
            position: "absolute", top: "8px", right: "8px", width: "18px", height: "18px",
            margin: "0", accentColor: "#2d7ff9", cursor: "pointer",
          });
          checkbox.type = "checkbox";
          checkbox.setAttribute("aria-label", "Chọn " + f.name);
          const fileLabel = el("div", {
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            direction: "rtl", textAlign: "right",
          });
          fileLabel.append(el("bdi", null, f.name));
          const viewBtn = mkBtn(isSaver || isVideo ? "Xem" : "✎");
          Object.assign(viewBtn.style, {
            position: "absolute", top: "8px", left: "8px", padding: "2px 6px",
            color: "#fff", background: "rgba(0,0,0,0.7)",
          });
          viewBtn.title = isVideo ? "Xem video" : isSaver ? "Xem ảnh kích thước đầy đủ" : "Xem ảnh hoặc vẽ mask";
          viewBtn.onclick = (event) => {
            event.stopPropagation();
            if (!isSaver && !isVideo) {
              openMaskEditor(f);
              return;
            }
            const dialog = el("dialog", { maxWidth: "95vw", background: "var(--comfy-menu-bg, #202020)" });
            const playVideo = isVideo && !/\.(gif|webp)$/i.test(f.name);
            const full = el(playVideo ? "video" : "img", {
              display: "block", maxWidth: "85vw", maxHeight: "75vh", objectFit: "contain",
            });
            if (playVideo) {
              full.controls = true;
              full.preload = "metadata";
            } else {
              full.alt = f.name;
            }
            const closeImage = mkBtn("Đóng");
            closeImage.onclick = () => dialog.close();
            dialog.addEventListener("close", () => dialog.remove(), { once: true });
            const query = new URLSearchParams({ entry: f.value, source, kind, drive_folder: driveFolder });
            full.src = api.apiURL("/load_image_metadata/full?" + query);
            query.set("download", "1");
            const download = el("a", { ...baseBtn, display: "inline-block", marginRight: "6px" }, "Tải " + mediaLabel + " gốc");
            download.href = api.apiURL("/load_image_metadata/full?" + query);
            download.download = f.name;
            dialog.append(full, download, closeImage);
            overlay.append(dialog);
            dialog.showModal();
          };
          t.append(img, checkbox, viewBtn, fileLabel);
          t.title = f.name;
          const metadataBadges = el("div", {
            position: "absolute", bottom: "22px", right: "8px", display: "flex", gap: "4px",
          });
          t.append(metadataBadges);
          if (!isVideo) img.addEventListener("load", async () => {
            const query = new URLSearchParams({ entry: f.value, drive_folder: driveFolder });
            try {
              const response = await api.fetchApi("/load_image_metadata/metadata?" + query, { cache: "no-store" });
              if (!response.ok || !t.isConnected) return;
              const metadata = await response.json();
              if (metadata.parameters) {
                const info = mkBtn("ⓘ");
                info.title = "Xem thông số Civitai / A1111";
                info.onclick = event => {
                  event.stopPropagation();
                  const dialog = el("dialog", {
                    width: "min(680px, 85vw)", color: "var(--input-text, #ddd)",
                    background: "var(--comfy-menu-bg, #202020)",
                  });
                  const closeInfo = mkBtn("Đóng");
                  closeInfo.onclick = () => dialog.close();
                  dialog.addEventListener("close", () => dialog.remove(), { once: true });
                  dialog.append(el("h3", null, f.name), el("pre", {
                    whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: "60vh", overflow: "auto",
                  }, metadata.parameters), closeInfo);
                  overlay.append(dialog);
                  dialog.showModal();
                };
                metadataBadges.append(info);
              }
              if (metadata.has_workflow) {
                const comfy = el("span", {
                  background: "#235ea8", color: "#fff", borderRadius: "4px", padding: "4px 6px",
                  alignSelf: "center",
                }, "◆ Comfy");
                comfy.title = "Có workflow ComfyUI nhúng";
                metadataBadges.append(comfy);
              }
            } catch (error) {
              console.debug("ShankImageLoad metadata:", error);
            }
          }, { once: true });
          if (isVideo) {
            img.addEventListener("error", () => {
              img.replaceWith(el("div", {
                height: "110px", display: "grid", placeItems: "center", background: "#111",
              }, "Video"));
            }, { once: true });
          }
          img.src = api.apiURL("/load_image_metadata/thumb?" + new URLSearchParams({
            source, kind, drive_folder: driveFolder, path: join(d.path, f.name), version: f.version,
          }).toString());

          marks.push(() => {
            checkbox.checked = selected.has(f.value);
            t.style.outline = checkbox.checked ? "2px solid #2d7ff9" : "none";
          });
          const toggle = () => {
            if (selected.has(f.value)) {
              selected.delete(f.value);
            } else {
              if (isVideoLoader) selected.clear();
              selected.add(f.value);
            }
            refreshMarks();
          };
          checkbox.onclick = (event) => event.stopPropagation();
          checkbox.onchange = toggle;
          t.onclick = toggle;
          body.append(t);
        }
        if (!d.dirs.length && !d.files.length) {
          body.append(el("div", { padding: "10px" }, "(Thu muc trong)"));
        }
        refreshMarks();
      }

      // ---- cua so xem anh lon + ve mask ----
      // Luu thanh PNG moi (ComfyUI/input/masks/), vung ve = trong suot -> output MASK cua node.
      function openMaskEditor(f) {
        const ed = el("div", {
          position: "fixed", inset: "0", background: "rgba(0,0,0,0.88)", zIndex: "10001",
          display: "flex", flexDirection: "column", fontFamily: "sans-serif",
          color: "var(--input-text, #ddd)",
        });
        const bar = el("div", {
          display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", padding: "8px 10px",
          background: "var(--comfy-menu-bg, #202020)", borderBottom: "1px solid var(--border-color, #444)",
        });
        const viewport = el("div", {
          flex: "1", position: "relative", overflow: "hidden", cursor: "none", touchAction: "none",
        });
        ed.append(bar, viewport);

        const brushBtn = mkBtn("Brush");
        const eraserBtn = mkBtn("Eraser");
        const sizeIn = el("input", { width: "140px" });
        sizeIn.type = "range"; sizeIn.min = "1"; sizeIn.max = "200"; sizeIn.value = "40";
        const sizeLbl = el("span", { fontSize: "12px", minWidth: "48px" }, "40px");
        const undoBtn = mkBtn("Undo");
        const clearBtn2 = mkBtn("Clear");
        const fitBtn = mkBtn("Fit");
        const saveBtn = mkBtn("Save mask");
        const closeBtn = mkBtn("Close");
        saveBtn.style.background = "#2d7ff9"; saveBtn.style.color = "#fff";
        const status = el("span", {
          fontSize: "12px", opacity: "0.85", flex: "1", overflow: "hidden",
          textOverflow: "ellipsis", whiteSpace: "nowrap",
        }, "Wheel: zoom | Right/middle drag: pan | [ ]: brush size | Ctrl+Z: undo");
        bar.append(brushBtn, eraserBtn, sizeIn, sizeLbl, undoBtn, clearBtn2, fitBtn, status, saveBtn, closeBtn);

        const world = el("div", { position: "absolute", left: "0", top: "0", transformOrigin: "0 0" });
        const img = el("img", { display: "block", userSelect: "none", pointerEvents: "none" });
        img.draggable = false;
        const mask = el("canvas", { position: "absolute", left: "0", top: "0", opacity: "0.55", pointerEvents: "none" });
        world.append(img, mask);
        const ring = el("div", {
          position: "absolute", pointerEvents: "none", border: "1px solid #fff", borderRadius: "50%",
          boxShadow: "0 0 0 1px #000", display: "none",
        });
        viewport.append(world, ring);
        const ctx = mask.getContext("2d", { willReadFrequently: true });

        let iw = 0, ih = 0, scale = 1, tx = 0, ty = 0, size = 40, erase = false;
        const undo = [];
        let drawing = false, panning = false, last = null, panStart = null;

        const applyView = () => { world.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + scale + ")"; };
        const styleMode = () => {
          const on = (b, a) => { b.style.background = a ? "#2d7ff9" : "var(--comfy-input-bg, #333)"; b.style.color = a ? "#fff" : "var(--input-text, #ddd)"; };
          on(brushBtn, !erase); on(eraserBtn, erase);
        };
        const setSize = (v) => {
          size = Math.max(1, Math.min(Number(sizeIn.max), Math.round(v)));
          sizeIn.value = String(size); sizeLbl.textContent = size + "px";
        };
        const fit = () => {
          const r = viewport.getBoundingClientRect();
          scale = Math.min(r.width / iw, r.height / ih) * 0.96;
          tx = (r.width - iw * scale) / 2; ty = (r.height - ih * scale) / 2;
          applyView();
        };
        const updateRing = (ev) => {
          const r = viewport.getBoundingClientRect();
          const d = Math.max(4, size * scale);
          ring.style.width = d + "px"; ring.style.height = d + "px";
          ring.style.left = (ev.clientX - r.left - d / 2) + "px";
          ring.style.top = (ev.clientY - r.top - d / 2) + "px";
        };
        const toImg = (ev) => {
          const r = viewport.getBoundingClientRect();
          return [(ev.clientX - r.left - tx) / scale, (ev.clientY - r.top - ty) / scale];
        };
        const maxUndo = () => Math.max(2, Math.min(20, Math.floor(2e8 / (iw * ih * 4))));
        const pushUndo = () => { undo.push(ctx.getImageData(0, 0, iw, ih)); if (undo.length > maxUndo()) undo.shift(); };
        const doUndo = () => { const s = undo.pop(); if (s) ctx.putImageData(s, 0, 0); };
        const seg = (a, b) => {
          ctx.save();
          ctx.globalCompositeOperation = erase ? "destination-out" : "source-over";
          ctx.strokeStyle = "rgb(255,40,40)";
          ctx.lineWidth = size; ctx.lineCap = "round"; ctx.lineJoin = "round";
          ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0] + 0.01, b[1]); ctx.stroke();
          ctx.restore();
        };

        sizeIn.oninput = () => setSize(Number(sizeIn.value));
        brushBtn.onclick = () => { erase = false; styleMode(); };
        eraserBtn.onclick = () => { erase = true; styleMode(); };
        undoBtn.onclick = doUndo;
        clearBtn2.onclick = () => { if (!iw) return; pushUndo(); ctx.clearRect(0, 0, iw, ih); };
        fitBtn.onclick = () => { if (iw) fit(); };
        styleMode();

        viewport.addEventListener("contextmenu", (ev) => ev.preventDefault());
        viewport.addEventListener("pointerenter", () => { ring.style.display = "block"; });
        viewport.addEventListener("pointerleave", () => { ring.style.display = "none"; });
        viewport.addEventListener("pointerdown", (ev) => {
          if (!iw) return;
          if (ev.button === 0) {
            drawing = true; pushUndo(); last = toImg(ev); seg(last, last);
          } else if (ev.button === 1 || ev.button === 2) {
            panning = true; panStart = [ev.clientX - tx, ev.clientY - ty];
          }
          viewport.setPointerCapture(ev.pointerId);
          ev.preventDefault();
        });
        viewport.addEventListener("pointermove", (ev) => {
          updateRing(ev);
          if (drawing) {
            const evs = ev.getCoalescedEvents ? ev.getCoalescedEvents() : [ev];
            for (const e of (evs.length ? evs : [ev])) { const p = toImg(e); seg(last, p); last = p; }
          } else if (panning) {
            tx = ev.clientX - panStart[0]; ty = ev.clientY - panStart[1]; applyView();
          }
        });
        const stopPtr = () => { drawing = false; panning = false; };
        viewport.addEventListener("pointerup", stopPtr);
        viewport.addEventListener("pointercancel", stopPtr);
        viewport.addEventListener("wheel", (ev) => {
          ev.preventDefault();
          if (!iw) return;
          const r = viewport.getBoundingClientRect();
          const mx = ev.clientX - r.left, my = ev.clientY - r.top;
          const ns = Math.min(40, Math.max(0.02, scale * Math.pow(1.15, -ev.deltaY / 100)));
          tx = mx - (mx - tx) * ns / scale; ty = my - (my - ty) * ns / scale; scale = ns;
          applyView(); updateRing(ev);
        }, { passive: false });

        // bat phim o pha capture de khong dong nham cua so duyet file / kich hoat phim tat cua ComfyUI
        const onEdKey = (ev) => {
          const k = ev.key;
          if (k === "Escape") { ev.stopImmediatePropagation(); ev.preventDefault(); closeEd(); }
          else if (k === "[") { ev.stopImmediatePropagation(); setSize(size * 0.85); }
          else if (k === "]") { ev.stopImmediatePropagation(); setSize(size / 0.85); }
          else if ((ev.ctrlKey || ev.metaKey) && k.toLowerCase() === "z") { ev.stopImmediatePropagation(); ev.preventDefault(); doUndo(); }
        };
        document.addEventListener("keydown", onEdKey, true);
        function closeEd() {
          document.removeEventListener("keydown", onEdKey, true);
          ed.remove();
        }
        closeBtn.onclick = closeEd;

        saveBtn.onclick = async () => {
          if (!iw) return;
          const src = ctx.getImageData(0, 0, iw, ih).data;
          const out = document.createElement("canvas");
          out.width = iw; out.height = ih;
          const octx = out.getContext("2d");
          const od = octx.createImageData(iw, ih);
          const dst = od.data;
          let any = 0;
          for (let i = 0; i < src.length; i += 4) {
            const a = src[i + 3];
            any |= a;
            dst[i] = dst[i + 1] = dst[i + 2] = a; dst[i + 3] = 255;
          }
          if (!any) { status.textContent = "Chua ve mask nao."; return; }
          status.textContent = "Saving...";
          octx.putImageData(od, 0, 0);
          const blob = await new Promise((res) => out.toBlob(res, "image/png"));
          const fd = new FormData();
          fd.append("entry", f.value);
          fd.append("drive_folder", folderValue());
          fd.append("mask", blob, "mask.png");
          try {
            const r = await api.fetchApi("/load_image_metadata/save_mask", { method: "POST", body: fd });
            const j = await r.json();
            if (j.error) throw new Error(j.error);
            // anh goc duoc thay bang ban co mask trong danh sach chon
            selected.delete(f.value);
            selected.add(j.entry);
            refreshMarks();
            pathLbl.textContent = "Saved: " + j.entry + " (da chon)";
            closeEd();
          } catch (e) {
            status.textContent = "Loi: " + (e && e.message ? e.message : e);
          }
        };

        img.onload = () => {
          iw = img.naturalWidth; ih = img.naturalHeight;
          world.style.width = iw + "px"; world.style.height = ih + "px";
          mask.width = iw; mask.height = ih;
          const big = Math.max(iw, ih);
          sizeIn.max = String(Math.max(200, Math.round(big / 4)));
          setSize(Math.max(8, Math.round(big / 40)));
          fit();
        };
        img.onerror = () => { status.textContent = "Khong tai duoc anh."; };
        document.body.append(ed);
        img.src = api.apiURL("/load_image_metadata/full?" + new URLSearchParams({
          entry: f.value, drive_folder: folderValue(),
        }).toString());
      }

      inputTab.onclick = () => { tab = lastTab = "input_folder"; load(null); };
      driveTab.onclick = () => { tab = lastTab = "drive_folder"; load(null); };
      upBtn.onclick = () => {
        if (!data || !data.path) return;
        load(data.path.split("/").slice(0, -1).join("/"));
      };
      selAllBtn.onclick = () => {
        if (!data || !data.files.length) return;
        for (const f of data.files) selected.add(f.value);
        refreshMarks();
      };
      clearSelBtn.onclick = () => { selected.clear(); refreshMarks(); };
      okBtn.onclick = () => {
        // giu thu tu anh cu (neu van con chon), anh moi them vao cuoi
        const merged = existing.filter((e) => selected.has(e));
        for (const e of selected) if (!merged.includes(e)) merged.push(e);
        setEntries(merged);
        close();
      };

      uploadBtn.onclick = () => fileInput.click();
      fileInput.onchange = async () => {
        const files = [...fileInput.files];
        fileInput.value = "";
        if (!files.length || !data) return;
        const folder = data.path;
        const version = loadVersion;
        pathLbl.textContent = "Uploading " + files.length + " file...";
        for (const file of files) {
          try {
            const fd = new FormData();
            fd.append("image", file);
            fd.append("type", "input");
            fd.append("subfolder", folder);
            const r = await api.fetchApi("/upload/image", { method: "POST", body: fd });
            if (r.status === 200) {
              const j = await r.json();
              if (isVideoLoader) selected.clear();
              selected.add((j.subfolder ? j.subfolder + "/" : "") + j.name);
            } else {
              console.warn("Upload failed", r.status, r.statusText);
            }
          } catch (e) {
            console.warn("Upload error", e);
          }
        }
        if (version === loadVersion) load(folder);
      };

      document.body.append(overlay);
      const videoPath = isVideoSaver ? get("filename_prefix")?.value : existing[0];
      const videoFolder = videoPath?.split(/[\\/]/).slice(0, -1).join("/");
      const initialFolder = isVideo ? (node.shankVideoSubfolder ?? videoFolder) : null;
      load(initialFolder || null).then(() => {
        if (initialFolder && !data && loadVersion === 1 && overlay.isConnected) load(null);
      });
    }

    const origConfigure = node.onConfigure;
    node.onConfigure = function () {
      if (origConfigure) origConfigure.apply(this, arguments);
      setTimeout(updatePreview, 100);
    };
    setTimeout(updatePreview, 100);
  },
});
"""


def _register_web_extension():
    try:
        import tempfile
        import nodes
        d = os.path.join(tempfile.gettempdir(), "load_image_metadata_web")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "load_image_metadata.js"), "w", encoding="utf-8") as f:
            f.write(_JS)
        nodes.EXTENSION_WEB_DIRS["load_image_metadata_web"] = d
    except Exception as e:  # khong co giao dien dong thi node van chay binh thuong
        print(f"[Load Image + Metadata] khong dang ky duoc JS: {e}")


# --- helper cho cua so duyet file --------------------------------------------
def _template_root(template):
    """Phan duong dan truoc doan dau tien co ky hieu %, vd .../ComfyUI/%Y-%m-%d -> .../ComfyUI"""
    parts = str(template).strip().replace("\\", "/").split("/")
    keep = []
    for part in parts:
        if "%" in part:
            break
        keep.append(part)
    root = "/".join(keep).rstrip("/")
    if len(root) < 2:
        raise ValueError("Duong dan drive_folder khong hop le")
    return root


def _inside(base, p):
    try:
        b = os.path.realpath(base)
        return os.path.commonpath([b, os.path.realpath(p)]) == b
    except ValueError:
        return False


def _browse_root(source, template):
    if source == "input_folder":
        return folder_paths.get_input_directory()
    if source != "drive_folder":
        raise ValueError("Nguon anh khong hop le")
    base = os.path.realpath(os.environ.get("SHANK_COMFY_DRIVE_ROOT") or _template_root(DRIVE_FOLDER_DEFAULT))
    if template and not _inside(base, _resolve_drive_folder(template, DRIVE_UTC_OFFSET_DEFAULT)):
        raise ValueError("Thu muc Drive nam ngoai thu muc cho phep")
    return base


def _join_inside(root, rel):
    rel = str(rel or "").replace("\\", "/").strip("/")
    p = os.path.normpath(os.path.join(root, rel)) if rel else os.path.normpath(root)
    if not _inside(root, p):
        raise ValueError("Duong dan nam ngoai thu muc cho phep")
    return p, rel


def _thumb_path_for_entry(entry, template):
    """Entry tuong doi -> trong ComfyUI/input; tuyet doi -> phai nam trong thu muc Drive cho phep."""
    e = str(entry or "").strip().strip('"')
    if os.path.isabs(e):
        p = os.path.normpath(e)
        if _inside(folder_paths.get_input_directory(), p):
            return p
        root = _browse_root("drive_folder", template)
        if not _inside(root, p):
            raise ValueError("Duong dan nam ngoai thu muc cho phep")
        return p
    return _join_inside(folder_paths.get_input_directory(), e)[0]


def _is_media_name(name, kind):
    if kind == "video":
        return os.path.splitext(name)[1].lower() in VIDEO_EXTENSIONS
    return _is_image_name(name)


def _media_browse_root(source, template, kind):
    if kind == "image":
        return _browse_root(source, template)
    if kind == "video":
        if source == "input_folder":
            return folder_paths.get_input_directory()
        if source == "output_folder":
            return folder_paths.get_output_directory()
    raise ValueError("Invalid media source")


def _action_media_path(root, relative_path, kind="image"):
    path, _ = _join_inside(root, relative_path)
    if not _is_media_name(path, kind) or os.path.islink(path):
        raise ValueError(f"Expected a regular {kind} file")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{kind.capitalize()} not found")
    return path


def _write_media_zip(output, root, relative_paths, kind):
    paths = list(dict.fromkeys(_action_media_path(root, relative, kind) for relative in relative_paths))
    directory = os.path.commonpath([os.path.dirname(path) for path in paths])
    with zipfile.ZipFile(output, "w") as archive:
        for path in paths:
            archive.write(path, os.path.relpath(path, directory))
    output.seek(0)


def _mutate_media(root, relative_paths, action, kind):
    mutate = os.unlink if action == "delete" else _strip_image_metadata
    done, errors = [], []
    for relative in relative_paths:
        try:
            mutate(_action_media_path(root, relative, kind))
            done.append(relative)
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            errors.append({"path": relative, "error": str(error)})
    return {"done": done, "errors": errors}


def _browser_metadata(path):
    with Image.open(path) as img:
        raw = img.info.get("parameters") or _exif_user_comment(img)
        parameters = (raw if isinstance(raw, str) else "").removeprefix("ASCII\x00\x00\x00").strip("\x00 \r\n")
        if not {"Steps", "Sampler", "Seed"}.intersection(_parse_a1111(parameters)[2]):
            parameters = ""
        try:
            workflow = json.loads(img.info.get("workflow", ""))
        except (ValueError, TypeError):
            workflow = None
        return {
            "parameters": parameters,
            "has_workflow": isinstance(workflow, dict) and isinstance(workflow.get("nodes"), list),
        }


def _clean_png(data, exif):
    # Keep pixel, animation, transparency and color-management chunks.
    keep = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"iCCP", b"sRGB",
            b"gAMA", b"cHRM", b"cICP", b"mDCv", b"cLLi", b"sBIT", b"acTL", b"fcTL", b"fdAT"}
    chunks = [data[:8]]
    pos = 8
    while pos + 12 <= len(data):
        size, tag = struct.unpack_from(">I4s", data, pos)
        end = pos + 12 + size
        if end > len(data):
            break
        if tag in keep:
            chunks.append(data[pos:end])
        if tag == b"IHDR" and exif:
            payload = b"eXIf" + exif[6:]
            chunks.append(struct.pack(">I", len(payload) - 4) + payload
                          + struct.pack(">I", zlib.crc32(payload)))
        if tag == b"IEND":
            return b"".join(chunks)
        pos = end
    raise ValueError("Invalid PNG chunks")


_JPEG_SCAN_END = re.compile(rb"\xff+(?![\xff\x00\xd0-\xd7])")


def _clean_jpeg(data, exif):
    chunks = [data[:2]]
    pos = 2
    while pos < len(data) and data[pos] == 0xff:
        start = pos
        while pos < len(data) and data[pos] == 0xff:
            pos += 1
        if pos >= len(data):
            break
        marker = data[pos]
        if marker == 0xd9:
            return b"".join([*chunks, data[start:pos + 1]])
        size = int.from_bytes(data[pos + 1:pos + 3], "big")
        end = pos + 1 + size
        if size < 2 or end > len(data):
            break
        payload = data[pos + 3:end]
        if marker < 0xe0 or (marker > 0xef and marker != 0xfe):
            chunks.append(data[start:end])
        elif ((marker == 0xe0 and payload.startswith(b"JFIF\0"))
              or (marker == 0xe2 and payload.startswith(b"ICC_PROFILE\0"))
              or (marker == 0xee and payload.startswith(b"Adobe"))):
            chunks.append(data[start:end])
        if marker == 0xda:
            if exif:
                chunks.insert(1, b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif)
                exif = b""
            next_marker = _JPEG_SCAN_END.search(data, end)
            if next_marker is None:
                break
            chunks.append(data[end:next_marker.start()])
            end = next_marker.start()
        pos = end
    raise ValueError("Invalid JPEG markers")


def _clean_webp(data, exif):
    chunks = []
    pos = 12
    limit = 8 + struct.unpack_from("<I", data, 4)[0]
    if limit > len(data):
        raise ValueError("Invalid WebP size")
    while pos + 8 <= limit:
        tag, size = struct.unpack_from("<4sI", data, pos)
        end = pos + 8 + size + (size % 2)
        if end > limit:
            raise ValueError("Invalid WebP chunk")
        if tag == b"VP8X":
            flags = (data[pos + 8] & ~0x0c) | (0x08 if exif else 0)
            chunks.append(data[pos:pos + 8] + bytes([flags]) + data[pos + 9:end])
        elif tag in {b"ICCP", b"ANIM", b"ANMF", b"ALPH", b"VP8 ", b"VP8L"}:
            chunks.append(data[pos:end])
        pos = end
    if pos != limit:
        raise ValueError("Invalid WebP chunks")
    if exif:
        chunks.append(b"EXIF" + struct.pack("<I", len(exif)) + exif + b"\0" * (len(exif) % 2))
    body = b"WEBP" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _gif_table_size(flags):
    return 3 * (2 << (flags & 7)) if flags & 0x80 else 0


def _gif_block_end(data, pos):
    while pos < len(data):
        size = data[pos]
        pos += size + 1
        if not size:
            return pos
    raise ValueError("Invalid GIF blocks")


def _clean_gif(data):
    pos = 13 + _gif_table_size(data[10])
    chunks = [data[:pos]]
    while pos < len(data):
        start = pos
        if data[pos] == 0x3b:
            return b"".join([*chunks, b";"])
        if data[pos] == 0x2c and pos + 10 < len(data):
            pos += 11 + _gif_table_size(data[pos + 9])
            pos = _gif_block_end(data, pos)
            chunks.append(data[start:pos])
        elif data[pos] == 0x21 and pos + 2 < len(data):
            label = data[pos + 1]
            pos = _gif_block_end(data, pos + 2)
            app = data[start + 3:start + 14]
            if label == 0xf9 or (label == 0xff and app in {b"NETSCAPE2.0", b"ANIMEXTS1.0", b"ICCRGBG1012"}):
                chunks.append(data[start:pos])
        else:
            break
    raise ValueError("Invalid GIF image")


def _save_clean_image(img, output):
    options = {}
    if img.format in {"TIFF", "AVIF"} and img.info.get("icc_profile"):
        options["icc_profile"] = img.info["icc_profile"]
    if img.format == "AVIF":
        options.update(quality=100, subsampling="4:4:4")
    elif img.format == "TIFF":
        options["compression"] = "tiff_deflate"
    if img.format == "AVIF" and "loop" in img.info:
        options["loop"] = img.info["loop"]

    frames, durations = [], []
    for frame in ImageSequence.Iterator(img):
        clean = ImageOps.exif_transpose(frame)
        clean.info.clear()
        frames.append(clean)
        durations.append(frame.info.get("duration", 0))
    if len(frames) > 1:
        options.update(save_all=True, append_images=frames[1:])
        if img.format == "AVIF":
            options["duration"] = durations
    frames[0].save(output, format=img.format, **options)


def _strip_image_metadata(path):
    cleaners = {"PNG": _clean_png, "JPEG": _clean_jpeg, "WEBP": _clean_webp}
    original = os.stat(path)
    with tempfile.NamedTemporaryFile(dir=os.path.dirname(path), delete=False) as output:
        temporary = output.name
    try:
        with Image.open(path) as img, open(temporary, "w+b") as output:
            if img.format == "GIF":
                with open(path, "rb") as source:
                    output.write(_clean_gif(source.read()))
            elif img.format in cleaners:
                # Retain only EXIF orientation when removing it would rotate the image.
                orientation = img.getexif().get(274, 1)
                exif = Image.Exif()
                if orientation in range(2, 9):
                    exif[274] = orientation
                with open(path, "rb") as source:
                    cleaned = cleaners[img.format](source.read(), exif.tobytes() if exif else b"")
                output.write(cleaned)
            else:
                _save_clean_image(img, output)
            expected_frames = img.n_frames if hasattr(img, "n_frames") else 1
        with Image.open(temporary) as result:
            if getattr(result, "n_frames", 1) != expected_frames:
                raise ValueError("Unexpected frame count after removing metadata")
            result.verify()
        os.chmod(temporary, stat.S_IMODE(original.st_mode))
        current = os.stat(path, follow_symlinks=False)
        if (current.st_ino, current.st_size, current.st_mtime_ns) != (
            original.st_ino, original.st_size, original.st_mtime_ns
        ):
            raise OSError("Image changed while removing metadata")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _make_thumb(path):
    import io
    img = Image.open(path)
    try:
        img.draft("RGB", (512, 512))
    except Exception:
        pass
    img = ImageOps.exif_transpose(img)
    img.thumbnail((256, 256))
    if "A" in img.getbands():
        # vung trong suot (= mask) to do nhat de nhin thay mask ngay tren thumbnail
        a = img.getchannel("A")
        if a.getextrema()[0] < 255:
            rgb = img.convert("RGB")
            tint = Image.new("RGB", rgb.size, (255, 40, 40))
            img = Image.composite(tint, rgb, ImageOps.invert(a).point(lambda v: int(v * 0.55)))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def _make_video_thumb(path):
    from ._video_helper.videohelpersuite.utils import ffmpeg_path, local_video_input
    result = subprocess.run(
        [ffmpeg_path, "-nostdin", "-v", "error", "-threads", "1", *local_video_input(path), "-map", "0:v:0",
         "-vf", "scale=256:144:force_original_aspect_ratio=decrease",
         "-frames:v", "1", "-threads", "1", "-c:v", "mjpeg", "-f", "image2pipe", "pipe:1"],
        capture_output=True,
        check=True,
        timeout=15,
    )
    if not result.stdout:
        raise ValueError("Video has no frames")
    return result.stdout


def _make_full_png(path):
    """Anh goc (da xoay theo EXIF, giong luc load) -> PNG de trinh duyet hien thi/ve mask."""
    import io
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode == "I":
        img = img.point(lambda i: i * (1 / 255))
    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=1)
    return buf.getvalue()


def _save_mask_png(src_path, mask_bytes):
    """Ghep mask (trang = vung mask) vao kenh alpha cua anh goc: vung mask -> trong suot.
    Luu vao ComfyUI/input/masks/, tra ve duong dan tuong doi de dung lam entry."""
    import io
    with Image.open(src_path) as original:
        pnginfo = PngInfo()
        for key, value in original.info.items():
            if isinstance(value, str):
                pnginfo.add_itxt(key, value)
        if not original.info.get("parameters"):
            comment = _exif_user_comment(original)
            if comment:
                pnginfo.add_itxt("parameters", comment)
        img = ImageOps.exif_transpose(original)
    if img.mode == "I":
        img = img.point(lambda i: i * (1 / 255))
    rgba = img.convert("RGBA")
    m = Image.open(io.BytesIO(mask_bytes)).convert("L")
    if m.size != rgba.size:
        m = m.resize(rgba.size, Image.BILINEAR)
    # alpha moi = alpha cu * (1 - mask); PIL giu nguyen mau RGB duoi vung trong suot
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), ImageOps.invert(m)))
    out_dir = os.path.join(folder_paths.get_input_directory(), "masks")
    if not _inside(folder_paths.get_input_directory(), out_dir):
        raise ValueError("Thu muc mask nam ngoai input")
    os.makedirs(out_dir, exist_ok=True)
    stem = re.sub(r"[^\w\-. ]", "_", os.path.splitext(os.path.basename(src_path))[0])[:80] or "image"
    for n in range(10000):
        name = f"{stem}_mask_{n}.png" if n else f"{stem}_mask.png"
        path = os.path.join(out_dir, name)
        try:
            output = open(path, "xb")
        except FileExistsError:
            continue
        try:
            with output:
                rgba.save(output, format="PNG", compress_level=1, pnginfo=pnginfo)
        except Exception:
            os.unlink(path)
            raise
        break
    else:
        raise OSError("Khong con ten file mask kha dung")
    return "masks/" + name


def _register_routes():
    try:
        import asyncio
        from urllib.parse import quote

        from aiohttp import web
        from server import PromptServer

        routes = PromptServer.instance.routes
        thumbnail_slots = asyncio.Semaphore(2)

        @routes.get("/load_image_metadata/browse")
        async def _browse(request):
            q = request.rel_url.query
            source = q.get("source", "input_folder")
            template = q.get("drive_folder", "")
            kind = q.get("kind", "image")
            try:
                root = _media_browse_root(source, template, kind)
                today = ""
                if source == "drive_folder":
                    if q.get("export_today") == "1" and not template:
                        template = os.path.join(root, "%Y-%m-%d")
                    if template:
                        today = os.path.normpath(_resolve_drive_folder(template, DRIVE_UTC_OFFSET_DEFAULT))
                rel = q.get("path")
                if rel is None:  # lan dau mo: Drive thi vao thang thu muc cua ngay
                    rel = ""
                    if today and os.path.isdir(today) and _inside(root, today):
                        r = os.path.relpath(today, os.path.normpath(root))
                        rel = "" if r == "." else r.replace(os.sep, "/")
                cur, rel = _join_inside(root, rel)
                if not os.path.isdir(cur):
                    raise FileNotFoundError(f"Thu muc khong ton tai: {cur}")
                dirs, files = [], []
                with os.scandir(cur) as it:
                    for e in it:
                        if e.name.startswith("."):
                            continue
                        try:
                            if kind == "video" and (e.is_symlink() or not _inside(root, e.path)):
                                continue
                            if e.is_dir():
                                dirs.append(e.name)
                            elif e.is_file() and _is_media_name(e.name, kind):
                                files.append((e.stat().st_mtime_ns, e.name))
                        except OSError:
                            continue
                dirs.sort(key=str.lower)
                files.sort(reverse=True)  # moi nhat len tren
                out_files = []
                for version, name in files[:3000]:
                    value = (f"{rel}/{name}" if rel else name) if source != "drive_folder" \
                        else os.path.join(cur, name)
                    out_files.append({"name": name, "value": value, "version": str(version)})
                return web.json_response({
                    "root": root, "path": rel, "abs": cur, "dirs": dirs, "files": out_files,
                })
            except Exception as e:
                return web.json_response({"error": str(e)})

        @routes.get("/load_image_metadata/thumb")
        async def _thumb(request):
            q = request.rel_url.query
            try:
                template = q.get("drive_folder", "")
                if q.get("kind") == "video":
                    root = _media_browse_root(q.get("source"), template, "video")
                    path = _action_media_path(root, q.get("path", ""), "video")
                    async with thumbnail_slots:
                        data = await asyncio.to_thread(_make_video_thumb, path)
                    return web.Response(body=data, content_type="image/jpeg",
                                        headers={"Cache-Control": "max-age=3600"})
                if q.get("entry") is not None:
                    p = _thumb_path_for_entry(q.get("entry"), template)
                else:
                    root = _browse_root(q.get("source", "input_folder"), template)
                    p, _ = _join_inside(root, q.get("path", ""))
                if not (os.path.isfile(p) and _is_image_name(p)):
                    return web.Response(status=404)
                data = await asyncio.get_running_loop().run_in_executor(None, _make_thumb, p)
                return web.Response(body=data, content_type="image/jpeg",
                                    headers={"Cache-Control": "max-age=3600"})
            except Exception:
                return web.Response(status=404)

        @routes.get("/load_image_metadata/metadata")
        async def _metadata(request):
            q = request.rel_url.query
            try:
                path = _thumb_path_for_entry(q.get("entry"), q.get("drive_folder", ""))
                if not (os.path.isfile(path) and _is_image_name(path)):
                    return web.Response(status=404)
                return web.json_response(await asyncio.to_thread(_browser_metadata, path))
            except (OSError, ValueError):
                return web.Response(status=404)

        @routes.get("/load_image_metadata/full")
        async def _full(request):
            q = request.rel_url.query
            try:
                template = q.get("drive_folder", "")
                if q.get("kind") == "video":
                    root = _media_browse_root(q.get("source"), template, "video")
                    p = _action_media_path(root, q.get("entry", ""), "video")
                else:
                    p = _thumb_path_for_entry(q.get("entry"), template)
                    if not (os.path.isfile(p) and _is_image_name(p)):
                        return web.Response(status=404)
                if q.get("download") == "1":
                    filename = quote(os.path.basename(p), safe="")
                    return web.FileResponse(p, headers={
                        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
                    })
                if q.get("kind") == "video":
                    return web.FileResponse(p, headers={"Cache-Control": "no-cache"})
                data = await asyncio.get_running_loop().run_in_executor(None, _make_full_png, p)
                return web.Response(body=data, content_type="image/png",
                                    headers={"Cache-Control": "no-cache"})
            except Exception:
                return web.Response(status=404)

        @routes.post("/load_image_metadata/delete")
        async def _delete(request):
            if request.content_type != "application/json":
                return web.json_response({"error": "Expected JSON"}, status=415)
            try:
                body = await request.json()
                if not isinstance(body, dict) or not isinstance(body.get("path"), str):
                    raise ValueError("Invalid image path")
                root = _browse_root(body.get("source"), body.get("drive_folder", ""))
                os.unlink(_action_media_path(root, body["path"]))
            except ValueError as e:
                return web.json_response({"error": str(e)}, status=400)
            except FileNotFoundError:
                return web.json_response({"error": "Image not found"}, status=404)
            except OSError as e:
                return web.json_response({"error": e.strerror or str(e)}, status=409)
            return web.json_response({"deleted": True})

        @routes.post("/load_image_metadata/actions")
        async def _actions(request):
            if request.content_type != "application/json":
                return web.json_response({"error": "Expected JSON"}, status=415)
            try:
                body = await request.json()
                if not isinstance(body, dict):
                    raise ValueError("Invalid request")
                action = body.get("action")
                if action not in ("delete", "strip_metadata", "download"):
                    raise ValueError("Invalid media action")
                paths = body.get("paths")
                if not isinstance(paths, list) or not 1 <= len(paths) <= 3000 or not all(
                    isinstance(path, str) and path for path in paths
                ):
                    raise ValueError("Expected a list of media paths")
                paths = list(dict.fromkeys(paths))
                kind = body.get("kind", "image")
                source = body.get("source")
                root = _media_browse_root(source, body.get("drive_folder", ""), kind)
                if kind == "video" and (action == "strip_metadata" or (action == "delete" and source != "output_folder")):
                    raise ValueError("This video action is unavailable")
                if action != "download":
                    return web.json_response(await asyncio.to_thread(_mutate_media, root, paths, action, kind))
                with tempfile.TemporaryFile() as output:
                    await asyncio.to_thread(_write_media_zip, output, root, paths, kind)
                    archive_name = "comfy-videos.zip" if kind == "video" else "comfy-images.zip"
                    response = web.StreamResponse(headers={
                        "Content-Type": "application/zip",
                        "Content-Disposition": f'attachment; filename="{archive_name}"',
                        "Content-Length": str(os.fstat(output.fileno()).st_size),
                    })
                    await response.prepare(request)
                    while chunk := await asyncio.to_thread(output.read, 256 * 1024):
                        await response.write(chunk)
                    return response
            except ValueError as error:
                return web.json_response({"error": str(error)}, status=400)
            except OSError as error:
                return web.json_response({"error": str(error)}, status=409)

        @routes.post("/load_image_metadata/save_mask")
        async def _save_mask(request):
            try:
                form = await request.post()
                p = _thumb_path_for_entry(form.get("entry"), form.get("drive_folder", ""))
                if not (os.path.isfile(p) and _is_image_name(p)):
                    raise FileNotFoundError("Khong tim thay anh goc")
                field = form.get("mask")
                if field is None or not hasattr(field, "file"):
                    raise ValueError("Thieu du lieu mask")
                mask_bytes = field.file.read()
                entry = await asyncio.get_running_loop().run_in_executor(None, _save_mask_png, p, mask_bytes)
                return web.json_response({"entry": entry})
            except Exception as e:
                return web.json_response({"error": str(e)})
    except Exception as e:
        print(f"[Load Image + Metadata] khong dang ky duoc route: {e}")


_register_web_extension()
_register_routes()

NODE_CLASS_MAPPINGS = {"ShankImageLoad": ShankImageLoad}
NODE_DISPLAY_NAME_MAPPINGS = {"ShankImageLoad": "Load Image + Metadata"}
