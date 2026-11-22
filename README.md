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
| `Concatenate Text (shanksimi)` | Nối văn bản từ trên xuống, bỏ qua dòng trống. Thêm hoặc xoá từng dòng, nhập trực tiếp hoặc nối từ cổng STRING. |
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

## Nguồn tham chiếu của các node

Các liên kết upstream trỏ tới commit đã dùng để đối chiếu khi tích hợp.
Mục tiêu là mỗi node Shank thực hiện được chức năng của node tham chiếu
mà chỉ cần cài gói Shank cùng thư viện và weights cần thiết. Các node đang
gọi trực tiếp extension khác được ghi rõ bên dưới.

| Node | Nguồn tham chiếu |
| --- | --- |
| [`ShankImageLoad`](nodes/load_image_metadata.py) | Node nội bộ. Đọc metadata A1111/Image Saver và ComfyUI. |
| [`ShankSeed`](nodes/seed.py) | [rgthree-comfy · bc48c6a](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/py/seed.py) |
| [`ShankSimpleMath`](nodes/simple_math.py) | [ComfyUI Essentials · 9d9f4be](https://github.com/cubiq/ComfyUI_essentials/blob/9d9f4bedfc9f0321c19faf71855e228c93bd0dc9/misc.py#L122) |
| [`ShankWildcardEncode`](nodes/wildcard_encode.py) | [Impact Pack · 7ff671a](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/7ff671ad5f407c3eba907a9b83b6b8c9d13f64b6/modules/impact/impact_pack.py#L2711) |
| [`ShankAnimaLLLiteApply`](nodes/anima_lllite/__init__.py) | [kohya-ss · b7495bd](https://github.com/kohya-ss/ComfyUI-Anima-LLLite/blob/b7495bd8eb876e334509976896702484ed19cdbb/nodes.py) |
| [`ShankUNETLoader`](nodes/unet_loader.py) | [Image Saver · 2cccbf0](https://github.com/alexopus/ComfyUI-Image-Saver/blob/2cccbf07ca27a86fd2639cf173481f18eab5f4d3/nodes_loaders.py) |
| [`ShankImageSaverSimple`](nodes/image_saver_simple.py) | [Image Saver · 2cccbf0](https://github.com/alexopus/ComfyUI-Image-Saver/blob/2cccbf07ca27a86fd2639cf173481f18eab5f4d3/nodes.py#L281) |
| [`ShankMetadata`](nodes/image_saver_simple.py) | [Image Saver · 2cccbf0](https://github.com/alexopus/ComfyUI-Image-Saver/blob/2cccbf07ca27a86fd2639cf173481f18eab5f4d3/nodes.py#L149) |
| [`ShankImageComparer`](nodes/image_comparer.py) | [rgthree-comfy · bc48c6a](https://github.com/rgthree/rgthree-comfy/tree/bc48c6aaeca87bedbc14245d89f9bc6be37a630e) |
| [`ShankPowerLoraLoader`](nodes/power_lora_loader.py) | [rgthree-comfy · bc48c6a](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/py/power_lora_loader.py) |
| [`ShankAIOAuxPreprocessor`](nodes/aio_aux_preprocessor.py) | [ControlNet Aux · b9abafa](https://github.com/Fannovel16/comfyui_controlnet_aux/blob/b9abafa1019e230ebd674e4ae93f11bdf9d8dfc2/__init__.py#L84) |
| [`ShankReroutePrimitive`](nodes/reroute_primitive.py) | [Custom Scripts · 609f3af](https://github.com/pythongosssss/ComfyUI-Custom-Scripts/blob/609f3afaa74b2f88ef9ce8d939626065e3247469/web/js/reroutePrimitive.js) |
| [`ShankUltimateSDUpscale`](nodes/ultimate_sd_upscale.py) | [Ultimate SD Upscale · a5547db](https://github.com/ssitu/ComfyUI_UltimateSDUpscale/blob/a5547db9e1d07d3318bb21e9e9c474f4c1e9c8df/usdu_nodes.py#L109) |
| [`ShankBatchToImage`](nodes/batch_to_image.py) | [Impact Pack · 7ff671a](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/7ff671ad5f407c3eba907a9b83b6b8c9d13f64b6/modules/impact/util_nodes.py#L418) |
| [`ShankFaceDetailer`](nodes/face_detailer.py) | [Impact Pack · 61b9388](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/61b9388388ef127987dc4277a7ca94b985d0d075/modules/impact/impact_pack.py#L767) |
| [`ShankHanDetailer`](nodes/face_detailer.py) | [FaceDetailer của Impact Pack · 61b9388](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/61b9388388ef127987dc4277a7ca94b985d0d075/modules/impact/impact_pack.py#L767), dùng detector bàn tay và prompt mặc định riêng. |
| [`ShankUltralyticsDetectorProvider`](nodes/ultralytics_detector.py) | [Impact Subpack · 50c7b71](https://github.com/ltdrdata/ComfyUI-Impact-Subpack/blob/50c7b71a6a224734cc9b21963c6d1926816a97f1/modules/subpack_nodes.py) |
| [`ShankSAMLoader`](nodes/sam_loader.py) | [Impact Pack · 9e2d41d](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/9e2d41da75c185bf7638f860d5d004035f378e9b/modules/impact/impact_pack.py) |
| [`ShankBasicInfo`](nodes/basic_info.py) | Node nội bộ dựa trên subgraph Basic Info. Tham chiếu [Sampler và Scheduler Selector của Image Saver](https://github.com/alexopus/ComfyUI-Image-Saver/blob/2cccbf07ca27a86fd2639cf173481f18eab5f4d3/nodes_selectors.py). |
| [`ShankFastGroupsBypasser`](web/fast_groups_bypasser.js) | [rgthree-comfy · bc48c6a](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/web/comfyui/fast_groups_bypasser.js) |


## License

Mã Shank phát hành theo MIT. Mã bên thứ ba đi kèm có giấy phép riêng,
gồm GPL-3.0 cho Ultimate SD Upscale và AGPL-3.0 cho mã detector từ Impact Subpack.

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

### SeedVR2 Video Upscaler

Bản tích hợp [SeedVR2 VideoUpscaler của numz và AInVFX](https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler/commit/4490bd1f482e026674543386bb2a4d176da245b9)
giữ ID `SeedVR2LoadDiTModel`, `SeedVR2LoadVAEModel`, `SeedVR2VideoUpscaler`
và `SeedVR2TorchCompileSettings` để mở lại workflow đã tạo với extension gốc.
Mã upstream, cấu hình và embedding đi kèm nằm trong
[`nodes/_seedvr2/`](nodes/_seedvr2/) theo [Apache-2.0](nodes/_seedvr2/LICENSE).

Sau khi cập nhật repo, cài lại `requirements.txt` và khởi động lại ComfyUI.
Node tải model đã chọn khi chạy lần đầu, hoặc dùng model có sẵn trong
`ComfyUI/models/SEEDVR2/`. Workflow Colab T4 dùng
`seedvr2_ema_3b-Q4_K_M.gguf` và `ema_vae_fp16.safetensors`.

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
Dùng `BREAK` để encode từng đoạn và nối conditioning. Hai menu **Chèn LoRA** và **Chèn wildcard** chèn vào ô prompt đang dùng.
Khi queue ở chế độ **populate** với prompt tĩnh và seed trực tiếp hoặc từ
`ShankSeed`, bản workflow gửi đi lưu prompt đã bung ở chế độ **reproduce**.
Input chỉ có giá trị lúc thực thi được xử lý trong node.

Dùng `<lora:tên:0.8:LBW=PRESET;A=1;B=1>` với mã LBW đi kèm hoặc
`<lora:tên:0.8:LOADER=nunchaku>` với Nunchaku.

### U-Net Loader with Filename (shanksimi)

`ShankUNETLoader` dùng loader diffusion model gốc của ComfyUI, giữ tùy chọn
`weight_dtype` và trả thêm `filename` dạng STRING để nối vào node lưu ảnh.
Hành vi tham chiếu [UNETLoaderWithName của Image Saver](https://github.com/alexopus/ComfyUI-Image-Saver/blob/2cccbf07ca27a86fd2639cf173481f18eab5f4d3/nodes_loaders.py).

### Load Checkpoint with Model Name (shanksimi)

`ShankCheckpointLoader` dùng cùng cơ chế nạp checkpoint của ComfyUI, trả
`MODEL`, `CLIP`, `VAE` và `model_name` dạng STRING. Nối `model_name` vào
`modelname` của `ShankMetadata` để lưu tên file checkpoint cùng ảnh. Nút **ⓘ
Thông tin Civitai** mở bảng Info dùng chung và ưu tiên metadata cạnh checkpoint.

### AIO Aux Preprocessor (shanksimi)

`ShankAIOAuxPreprocessor` dùng mã annotator và wrapper đi kèm gói Shank.
Nguồn [ControlNet Aux · b9abafa](https://github.com/Fannovel16/comfyui_controlnet_aux/tree/b9abafa1019e230ebd674e4ae93f11bdf9d8dfc2)
và [giấy phép Apache-2.0](nodes/_controlnet_aux/LICENSE.txt).
Đặt `AUX_ANNOTATOR_CKPTS_PATH` trước khi mở ComfyUI nếu weights annotator
nằm trên Drive. Menu hiện các preprocessor đã nạp thành công.

Danh sách tham chiếu:

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

### Ultimate SD Upscale (shanksimi)

`ShankUltimateSDUpscale` phóng lớn ảnh rồi vẽ lại từng ô bằng diffusion.
Dùng `upscale_by` để chọn hệ số phóng, `denoise` để chỉnh mức vẽ lại và
`seam_fix_mode` để xử lý đường nối. Mô tả node và tooltip được dịch sang tiếng Việt.

Bộ xử lý dùng mã đi kèm gói Shank tại `nodes/_ultimate_upscale/`,
gồm [ComfyUI Ultimate SD Upscale · a5547db](https://github.com/ssitu/ComfyUI_UltimateSDUpscale/tree/a5547db9e1d07d3318bb21e9e9c474f4c1e9c8df)
và [Ultimate Upscale for Automatic1111 · 2322caa](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111/tree/2322caa480535b1011a1f9c18126d85ea444f146).
Mã tích hợp đổi các import nội bộ sang đường dẫn tương đối. Xem
[giấy phép GPL-3.0 đi kèm](nodes/_ultimate_upscale/LICENSE).

### Batch to Image (shanksimi)

`ShankBatchToImage` tách batch thành danh sách ảnh riêng lẻ, giữ nguyên thứ tự.
Ví dụ, batch 4 ảnh sẽ cho 4 phần tử để node kế tiếp xử lý từng ảnh.
Cách hoạt động tham chiếu [Image Batch to Image List của Impact Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/7ff671ad5f407c3eba907a9b83b6b8c9d13f64b6/modules/impact/util_nodes.py#L418).

### FaceDetailer (shanksimi)

`ShankFaceDetailer` dùng bộ xử lý Impact Pack đi kèm gói Shank.
Nối detector vào `bbox_detector`. Tham chiếu
[Impact Pack · 61b9388](https://github.com/ltdrdata/ComfyUI-Impact-Pack/tree/61b9388388ef127987dc4277a7ca94b985d0d075)
và [giấy phép GPL-3.0](nodes/_impact_detailer/LICENSE.txt).

### HandDetailer (shanksimi)

`ShankHanDetailer` dùng pipeline FaceDetailer của Impact Pack để cải thiện
chi tiết bàn tay. Nối detector nhận diện bàn tay vào `bbox_detector`. Các
đầu vào, thông số và đầu ra dùng cùng cấu trúc với FaceDetailer.

### Ultralytics Detector Provider (shanksimi)

`ShankUltralyticsDetectorProvider` dùng thư viện Python `ultralytics` và mã detector
tích hợp từ [ComfyUI-Impact-Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack),
kèm [giấy phép AGPL-3.0](nodes/_ultralytics/LICENSE.txt).
Đặt weights trong `ComfyUI/models/ultralytics/bbox/` hoặc
`ComfyUI/models/ultralytics/segm/`, chọn model phù hợp rồi nối
`BBOX_DETECTOR` vào `bbox_detector` của FaceDetailer hoặc HandDetailer.
Tham chiếu [mã upstream tại commit `50c7b71`](https://github.com/ltdrdata/ComfyUI-Impact-Subpack/blob/50c7b71a6a224734cc9b21963c6d1926816a97f1/modules/subpack_nodes.py).

### Image Saver Simple (shanksimi)

`ShankImageSaverSimple` dùng mã Image Saver đi kèm gói Shank. Mã nguồn tham chiếu
và giấy phép MIT nằm trong bảng trên và [nodes/_image_saver/LICENSE](nodes/_image_saver/LICENSE).
Node hỗ trợ metadata Civitai/A1111, nhúng workflow và xem trước ảnh đã lưu.

### Image Comparer (shanksimi)

Nối ảnh trước và sau xử lý vào `image_a` và `image_b`, rồi chạy workflow.
Kéo thanh trượt để xem hai ảnh trong cùng khung hoặc chọn chế độ bấm để đổi
ảnh A/B. Với batch, chọn từng ảnh bằng menu A và B. Node dùng PreviewImage
của ComfyUI. Hành vi tham chiếu
[Image Comparer của rgthree](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/py/image_comparer.py).

### Power Lora Loader (shanksimi)

Node dùng giao diện Shank và bộ nạp LoRA của ComfyUI. Workflow đã lưu bằng
giao diện rgthree và API prompt có các đầu vào `lora_*` vẫn đọc được.

Nối MODEL và CLIP nếu có, rồi chọn file ở dòng **Thêm LoRA**. Node tự tạo
dòng trống phía dưới và mở rộng khi có thêm LoRA. Mỗi dòng dùng một ô strength
cho cả MODEL và CLIP. Mở menu chuột phải của node để bật **Chỉnh riêng MODEL
và CLIP**. Các dòng đã lưu hai giá trị khác nhau vẫn hiện cả hai ô. Node áp
dụng các dòng đang bật theo thứ tự từ trên xuống.

### Basic Info (shanksimi)

`ShankBasicInfo` gom width, height, CFG, steps, hệ số upscale, sampler và
scheduler vào một node. Cổng `sampler` và `scheduler` nối vào KSampler.
Hai cổng có hậu tố `_name` trả chuỗi để ghi metadata. Danh sách lựa chọn lấy
từ KSampler của ComfyUI. Width và height mặc định là 0 như subgraph mẫu.
Đặt kích thước dương nếu nối vào node tạo latent yêu cầu kích thước cụ thể.

Dropdown `aspect_ratio` có preset ngang, dọc và vuông cho nhóm
Anima / Illu / Pony và FLUX / Krea / MOSS / Qwen. Các kích thước là gợi ý
khởi đầu và tỷ lệ có thể được làm tròn. Chọn preset để dùng kích thước ghi
trong tên preset, hoặc chọn **Custom** để dùng width và height nhập tay.

### Metadata

Nối thông số từ Basic Info, seed, tên model và prompt vào
`ShankMetadata`. Nối output `metadata` vào cổng cùng tên của
Image Saver Simple. Node dùng bộ tạo metadata đi kèm gói Shank.

### Fast Groups Bypasser (shanksimi)

`ShankFastGroupsBypasser` chạy trên giao diện. Mỗi công tắc bật hoặc bypass
các node trong một nhóm của graph hiện tại. Bản tích hợp tham chiếu
[Fast Groups Bypasser của rgthree](https://github.com/rgthree/rgthree-comfy/blob/bc48c6aaeca87bedbc14245d89f9bc6be37a630e/web/comfyui/fast_groups_bypasser.js).

### SAM Loader (shanksimi)

Nạp weights từ `ComfyUI/models/sams/` hoặc đường dẫn `sams` trong
`extra_model_paths.yaml`. `requirements.txt` cài `segment-anything` cho SAM
đời đầu. Chỉ khi dùng weights SAM 2/2.1, cài thêm bằng Python của ComfyUI
với `python -m pip install -r requirements-sam2.txt`. Node hỗ trợ tạo mask
ảnh tĩnh. SAM 2 video và EfficientSAM cần các node chuyên dụng.


#### LoRA theo block và Nunchaku

- `LBW` dùng mã và preset đi kèm từ [Inspire Pack · d23db9a](https://github.com/ltdrdata/ComfyUI-Inspire-Pack/blob/d23db9aa544de9a6d4c609cb7005fa9e0d42031d/inspire/lora_block_weight.py), theo [GPL-3.0](nodes/_inspire_lbw/LICENSE).
- `LOADER=nunchaku` dùng logic từ [ComfyUI-nunchaku · b600f87](https://github.com/nunchaku-ai/ComfyUI-nunchaku/blob/b600f879a777fdef1466c362e850f7e8c31bf89a/nodes/lora/flux.py), theo [Apache-2.0](nodes/_nunchaku_lora/LICENCE.txt). Tùy chọn này cần thư viện `nunchaku` và đầu vào FLUX đã được nạp dưới dạng Nunchaku. Shank chưa tích hợp node nạp FLUX Nunchaku.

## Upscale video

Workflow `shank-video-upscale.json` dùng bốn node được tích hợp từ
[ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite/tree/4d907bee61e92c2e65af3bd6383a4e4d356126d1).
Mã nguồn và giấy phép GPL-3.0 nằm trong `nodes/_video_helper`.

- **Load Video FFmpeg (Upload)** có nút **Browse files...** để chọn, xem hoặc tải video lên `ComfyUI/input`.
- **Video Info (Loaded)** xuất FPS, số khung hình, kích thước và thời lượng đã nạp.
- **Meta Batch Manager** chia video thành nhiều lô. Nối cùng một output vào hai cổng `meta_batch` của node đọc và node xuất video.
- **Video Combine** ghép khung hình và âm thanh. Bật `save_output` để lưu vào `ComfyUI/output`. **Browse files...** cho phép xem, tải hoặc xoá video đã xuất. Output tạm khi tắt `save_output` nằm ngoài cửa sổ này.

Cài dependencies từ `requirements.txt`. Nếu đã cài VideoHelperSuite riêng thì tắt bản đó trong Manager để bốn ID này do repo `comfy` đăng ký.
