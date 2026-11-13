# ComfyUI Custom Nodes Repository

Repo này lưu trữ các custom nodes dùng cho ComfyUI. Bạn có thể cài đặt qua **ComfyUI Manager** (tự động) hoặc **git clone** (thủ công).

## Cách cài đặt

### Cách 1: Qua ComfyUI Manager (Khuyên dùng)

1. Mở ComfyUI Manager → **Install Custom Nodes**
2. Tìm tên repository này (ví dụ: `my-comfy-nodes`)
3. Nhấn **Install** → ComfyUI Manager sẽ tự:
   - `git clone` repo vào `custom_nodes/`
   - Cài các thư viện Python trong `requirements.txt`
   - Chạy `install.py` (nếu có)
4. Khởi động lại ComfyUI

### Cách 2: Thủ công bằng Git

```bash
cd /đường/dẫn/đến/ComfyUI/custom_nodes
git clone https://github.com/USERNAME/my-comfy-nodes.git
cd my-comfy-nodes
pip install -r requirements.txt
```

Sau đó khởi động lại ComfyUI.

## Cấu trúc repo

```
my-comfy-nodes/
├── __init__.py
├── nodes/
│   ├── __init__.py
│   └── example_node.py
├── requirements.txt
├── install.py          # tùy chọn: script chạy sau khi clone
├── uninstall.py        # tùy chọn
├── node_list.json      # tùy chọn: nếu NODE_CLASS_MAPPINGS không chuẩn
└── README.md
```

## Đăng ký vào ComfyUI-Manager (để xuất hiện trong danh sách cài tự động)

Để repo của bạn xuất hiện trong ComfyUI Manager và được "tự động down về" khi người dùng nhấn Install, bạn cần gửi Pull Request lên repository chính thức của ComfyUI-Manager:

1. Fork repo: https://github.com/comfy-org/ComfyUI-Manager
2. Chỉnh sửa file `node_db/dev/custom-node-list.json` (hoặc `new/custom-node-list.json`)
3. Thêm entry cho node của bạn theo mẫu sau:

```json
{
  "title": "Tên hiển thị của node",
  "name": "my-comfy-nodes",
  "files": ["https://github.com/USERNAME/my-comfy-nodes.git"],
  "install_type": "git",
  "description": "Mô tả ngắn gọn về node của bạn",
  "pip": ["ten-thu-vien-can-thiet"],
  "tags": ["image", "example"]
}
```

4. Gửi Pull Request và chờ duyệt.

Sau khi duyệt, mọi người dùng ComfyUI Manager có thể tìm và cài đặt node của bạn một cách tự động.

## Ví dụ node

Xem file `nodes/example_node.py` để biết cách viết một custom node đơn giản.

## License

MIT