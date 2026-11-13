"""
Script chạy tự động sau khi ComfyUI Manager clone repo xong.
Có thể dùng để cài model, tạo thư mục, v.v.
"""

import os


def install():
    print("[my-comfy-nodes] Running install.py...")

    # Ví dụ: tạo thư mục output nếu chưa có
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    print(f"[my-comfy-nodes] Ensured output directory: {output_dir}")


if __name__ == "__main__":
    install()