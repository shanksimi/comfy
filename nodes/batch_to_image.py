class ShankBatchToImage:
    CATEGORY = "image"
    FUNCTION = "split"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    OUTPUT_IS_LIST = (True,)
    OUTPUT_TOOLTIPS = ("Danh sách ảnh theo thứ tự ban đầu. Mỗi phần tử chứa đúng một ảnh.",)
    DESCRIPTION = "Tách batch thành từng ảnh để ComfyUI có thể chạy node phía sau lần lượt cho mỗi ảnh."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE", {"tooltip": "Batch ảnh đầu vào. Tách theo chiều batch và giữ nguyên kích thước, màu sắc của mỗi ảnh."}),
        }}

    def split(self, image):
        return (list(image.split(1, dim=0)) if image.shape[0] else [],)
