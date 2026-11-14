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
