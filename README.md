# ComfyUI Custom Nodes Repository

Repo này lưu trữ các custom nodes dùng cho ComfyUI. Bạn có thể cài đặt qua **ComfyUI Manager** (tự động) hoặc **git clone** (thủ công).

## Cách cài đặt

### Cách 1: Qua ComfyUI Manager (Khuyên dùng)

1. Mở ComfyUI Manager → **Install Custom Nodes**
2. Tìm tên repository này (ví dụ: `comfy`)
3. Nhấn **Install** → ComfyUI Manager sẽ tự:
   - `git clone` repo vào `custom_nodes/`
   - Cài các thư viện Python trong `requirements.txt`
   - Chạy `install.py` (nếu có)
4. Khởi động lại ComfyUI

### Cách 2: Thủ công bằng Git

```bash
cd /đường/dẫn/đến/ComfyUI/custom_nodes
git clone https://github.com/shanksimi/comfy.git
cd comfy
pip install -r requirements.txt
```

Sau đó khởi động lại ComfyUI.

## Các custom nodes trong repo

| Node | Mô tả |
|------|-------|
| `Load Image + Metadata` | Load ảnh + đọc metadata (A1111/ComfyUI), chọn nhiều ảnh, vẽ mask. Output: IMAGE, MASK, POSITIVE, NEGATIVE, METADATA, FILENAME, FOLDER. |
| `Shank Wildcard Encode` | Thay thế các mẫu `{a|b|c}` trong prompt bằng giá trị ngẫu nhiên. Hỗ trợ seed và ô hiển thị kết quả. |
| `Shank Seed` | Cung cấp seed cho KSampler: fixed, random, increment, decrement. |

## Cấu trúc repo

```
comfy/
├── __init__.py              # Entry point đăng ký node cho ComfyUI (metadata @author/@title/...)
├── install.py               # Script chạy sau khi cài (tùy chọn)
├── node_list.json           # Danh sách node (cho scanner của ComfyUI-Manager)
├── pyproject.toml           # Metadata cho ComfyUI Registry / Manager
├── requirements.txt         # Python dependencies
├── .gitignore
├── README.md
└── nodes/                   # Thư mục chứa custom nodes
    ├── __init__.py
    ├── load_image_metadata.py   # Node: Load Image + Metadata
    ├── wildcard_encode.py       # Node: Shank Wildcard Encode
    └── seed.py                  # Node: Shank Seed
```

## Đăng ký vào ComfyUI-Manager (để xuất hiện trong danh sách cài tự động)

Để repo của bạn xuất hiện trong ComfyUI Manager và được "tự động down về" khi người dùng nhấn Install, bạn cần gửi Pull Request lên repository chính thức của ComfyUI-Manager:

1. Fork repo: https://github.com/comfy-org/ComfyUI-Manager
2. Chỉnh sửa file `node_db/dev/custom-node-list.json` (hoặc `new/custom-node-list.json`)
3. Thêm entry cho node của bạn:

```json
{
  "author": "shanksimi",
  "title": "ComfyUI-shanksimi",
  "reference": "https://github.com/shanksimi/comfy",
  "files": ["https://github.com/shanksimi/comfy"],
  "install_type": "git-clone",
  "description": "Bộ custom node cho ComfyUI: đọc metadata ảnh, mã hóa wildcard prompt, seed.",
  "tags": ["image", "text", "vietnamese"]
}
```

4. Gửi Pull Request và chờ duyệt.

Sau khi duyệt, mọi người dùng ComfyUI Manager có thể tìm và cài đặt node của bạn một cách tự động.

## Ví dụ node

- Xem `load_image_metadata.py` để biết cách viết node đọc metadata ảnh.
- Xem `wildcard_encode.py` để biết cách viết node xử lý wildcard trong prompt.

## License

MIT

### Thư mục ảnh cho Load Image + Metadata

Node đọc ảnh trong `ComfyUI/input` và thư mục Drive được cấu hình trên server.
Mặc định thư mục Drive là `/content/drive/MyDrive/SD-Data/Export/ComfyUI`.
Nếu lưu ảnh ở nơi khác, đặt biến môi trường `SHANK_COMFY_DRIVE_ROOT` thành
đường dẫn tuyệt đối của thư mục ảnh trước khi khởi động ComfyUI. Sau đó cập
nhật ô `drive_folder` trong workflow đã lưu để trỏ vào thư mục đó hoặc một
thư mục con. Ô này hỗ trợ mẫu ngày như `%Y-%m-%d`.

### Nguồn tham chiếu cho ShankSeed

`ShankSeed` mô phỏng giao diện và hành vi của node **Seed (rgthree)** trong
[rgthree-comfy](https://github.com/rgthree/rgthree-comfy). Bản tham chiếu ban đầu
là commit [`bc48c6a`](https://github.com/rgthree/rgthree-comfy/commit/bc48c6aaeca87bedbc14245d89f9bc6be37a630e).

| Phần | Mã trong repo này | Mã upstream tại commit tham chiếu |
| --- | --- | --- |
| Xử lý seed phía server | [nodes/seed.py](nodes/seed.py) | [py/seed.py](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/py/seed.py) |
| Giao diện và xử lý khi queue | [web/seed.js](web/seed.js) | [src_web/comfyui/seed.ts](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/src_web/comfyui/seed.ts) |

Khi kiểm tra bản mới của rgthree, đối chiếu thay đổi của hai file upstream
kể từ commit tham chiếu. Sau khi áp dụng thay đổi, kiểm tra seed cố định,
random mỗi lần queue, tăng/giảm seed, nút **Use Last Seed** và seed thực tế
trong metadata ảnh. Cập nhật commit tham chiếu khi đã kiểm tra xong.

### Apply Anima ControlNet-LLLite (shanksimi)

Node `ShankAnimaLLLiteApply` tích hợp
[ComfyUI-Anima-LLLite của kohya-ss](https://github.com/kohya-ss/ComfyUI-Anima-LLLite)
tại [commit `b7495bd`](https://github.com/kohya-ss/ComfyUI-Anima-LLLite/commit/b7495bd8eb876e334509976896702484ed19cdbb).
Phần này dùng [Apache-2.0](nodes/anima_lllite/LICENSE). Bản tích hợp đổi ID và
tên hiển thị. Khi upstream cập nhật, đối chiếu `nodes.py` và
`control_net_lllite_anima.py` với các file trong `nodes/anima_lllite/`.

Đặt weights LLLite `.safetensors` vào `ComfyUI/models/controlnet/`. Thêm node
**Apply Anima ControlNet-LLLite (shanksimi)**, nối model Anima và ảnh điều kiện,
chọn weights, rồi nối output `MODEL` tới sampler. Với weights inpaint, nối
thêm mask theo hướng dẫn upstream.

### Nguồn tham chiếu cho ShankWildcardEncode

Cú pháp wildcard tham chiếu [ComfyUI-Impact-Pack, commit `7ff671a`](https://github.com/ltdrdata/ComfyUI-Impact-Pack/tree/7ff671ad5f407c3eba907a9b83b6b8c9d13f64b6).
Khi đối chiếu upstream, xem `modules/impact/wildcards.py` và class
`ImpactWildcardEncode` trong `modules/impact/impact_pack.py`.

Đặt danh sách UTF-8 trong `wildcards/` ở gốc repo, mỗi lựa chọn một dòng.
Ví dụ `__outfits/dress__` đọc `wildcards/outfits/dress.txt`. Node hỗ trợ
`__outfits/*__`, `{2::red|1::blue}`, `{2$$, $$red|blue|gold}` và nhóm lồng
nhau. Dòng bắt đầu bằng `#` được bỏ qua. Node trả `MODEL`, `CLIP`, `CONDITIONING` và prompt đã xử lý.

YAML hỗ trợ mapping lồng nhau với danh sách ở cuối. Ví dụ
`outfits: {dress: [red, blue]}` tạo wildcard `__outfits/dress__`.
Chế độ **populate** xử lý `wildcard_text`, **fixed** dùng `populated_text`,
còn **reproduce** dùng `populated_text` cho lần chạy đó rồi giao diện quay về
**populate**. Dùng `<lora:tên:0.8:0.6>` để đặt strength riêng cho MODEL và CLIP.
Dùng `BREAK` để encode từng đoạn và nối conditioning. Hai menu **Add LoRA** và **Add wildcard** chèn vào ô prompt đang dùng.
Khi queue ở chế độ **populate** với prompt tĩnh và seed trực tiếp hoặc từ
`ShankSeed`, bản workflow gửi đi lưu prompt đã bung ở chế độ **reproduce**.
Input chỉ có giá trị lúc thực thi được xử lý trong node.

Dùng `<lora:tên:0.8:LBW=PRESET;A=1;B=1>` với ComfyUI-Inspire-Pack hoặc
`<lora:tên:0.8:LOADER=nunchaku>` với ComfyUI-nunchaku.

### U-Net Loader with Filename (shanksimi)

`ShankUNETLoader` dùng loader diffusion model gốc của ComfyUI, giữ tùy chọn
`weight_dtype` và trả thêm `filename` dạng STRING để nối vào node lưu ảnh.
Hành vi tham chiếu [UNETLoaderWithName của Image Saver](https://github.com/alexopus/ComfyUI-Image-Saver/blob/2cccbf07ca27a86fd2639cf173481f18eab5f4d3/nodes_loaders.py).

### AIO Aux Preprocessor (shanksimi)

`ShankAIOAuxPreprocessor` gọi node `AIO_Preprocessor` của
[comfyui_controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux/blob/a587a4c1594524c1d2de5cd1a86cd868ff448e1c/__init__.py).
Cài extension đó và khởi động lại ComfyUI để dùng danh sách preprocessor và
model của nó. Khi extension chưa có, node chỉ hiện lựa chọn `none` để trả
ảnh đầu vào.

Danh sách lựa chọn AIO tại commit upstream ở trên. Menu trong ComfyUI lấy
danh sách trực tiếp từ extension đã cài và chỉ hiện các preprocessor mà
extension nạp được.

| ID | Tên hiển thị |
| --- | --- |
| `none` | Trả ảnh đầu vào |
| `AnimalPosePreprocessor` | AnimalPose Estimator (AP10K) |
| `AnimeFace_SemSegPreprocessor` | Anime Face Segmentor |
| `AnimeLineArtPreprocessor` | Anime Lineart |
| `AnyLineArtPreprocessor_aux` | AnyLine Lineart |
| `BAE-NormalMapPreprocessor` | BAE Normal Map |
| `BinaryPreprocessor` | Binary Lines |
| `CannyEdgePreprocessor` | Canny Edge |
| `ColorPreprocessor` | Color Pallete |
| `ShufflePreprocessor` | Content Shuffle |
| `DensePosePreprocessor` | DensePose Estimator |
| `DepthAnythingPreprocessor` | Depth Anything |
| `DepthAnythingV2Preprocessor` | Depth Anything V2 - Relative |
| `DSINE-NormalMapPreprocessor` | DSINE Normal Map |
| `DWPreprocessor` | DWPose Estimator |
| `FakeScribblePreprocessor` | Fake Scribble Lines (aka scribble_hed) |
| `HEDPreprocessor` | HED Soft-Edge Lines |
| `ImageIntensityDetector` | Image Intensity |
| `ImageLuminanceDetector` | Image Luminance |
| `LeReS-DepthMapPreprocessor` | LeReS Depth Map (enable boost for leres++) |
| `M-LSDPreprocessor` | M-LSD Lines |
| `Manga2Anime_LineArt_Preprocessor` | Manga Lineart (aka lineart_anime_denoise) |
| `MediaPipe-FaceMeshPreprocessor` | MediaPipe Face Mesh |
| `MeshGraphormer-DepthMapPreprocessor` | MeshGraphormer Hand Refiner |
| `Metric3D-DepthMapPreprocessor` | Metric3D Depth Map |
| `Metric3D-NormalMapPreprocessor` | Metric3D Normal Map |
| `MiDaS-DepthMapPreprocessor` | MiDaS Depth Map |
| `MiDaS-NormalMapPreprocessor` | MiDaS Normal Map |
| `OneFormer-ADE20K-SemSegPreprocessor` | OneFormer ADE20K Segmentor |
| `OneFormer-COCO-SemSegPreprocessor` | OneFormer COCO Segmentor |
| `OpenposePreprocessor` | OpenPose Pose |
| `PiDiNetPreprocessor` | PiDiNet Soft-Edge Lines |
| `PyraCannyPreprocessor` | PyraCanny |
| `LineArtPreprocessor` | Realistic Lineart |
| `SAMPreprocessor` | SAM Segmentor |
| `ScribblePreprocessor` | Scribble Lines |
| `Scribble_PiDiNet_Preprocessor` | Scribble PiDiNet Lines |
| `Scribble_XDoG_Preprocessor` | Scribble XDoG Lines |
| `SemSegPreprocessor` | Semantic Segmentor (legacy, alias for UniFormer) |
| `LineartStandardPreprocessor` | Standard Lineart |
| `TEEDPreprocessor` | TEEDPreprocessor |
| `TilePreprocessor` | Tile |
| `TTPlanet_TileGF_Preprocessor` | TTPlanet Tile GuidedFilter |
| `TTPlanet_TileSimple_Preprocessor` | TTPlanet Tile Simple |
| `UniFormer-SemSegPreprocessor` | UniFormer Segmentor |
| `Zoe_DepthAnythingPreprocessor` | Zoe Depth Anything |
| `Zoe-DepthMapPreprocessor` | Zoe Depth Map |

### Reroute Primitive (shanksimi)

`ShankReroutePrimitive` giúp đổi hướng hoặc chia nhánh dây truyền các giá trị
như số và văn bản trên canvas. Ví dụ, nối cùng một giá trị `steps` tới hai
KSampler để chỉnh số bước ở một chỗ. Có thể thu gọn node để dây đi qua một
điểm nhỏ trên canvas.

Bản tích hợp tham chiếu [Reroute Primitive 🐍 của pythongosssss](https://github.com/pythongosssss/ComfyUI-Custom-Scripts/tree/609f3afaa74b2f88ef9ce8d939626065e3247469),
kèm [giấy phép MIT](LICENSE-reroute-primitive). Upstream đã ẩn node này khỏi
menu vì ngừng hỗ trợ. Bản này đăng ký node trong mục **utils**.
