import json
import re


_ROW_INPUT = re.compile(r"text_[1-9][0-9]*")


class _TextInputs(dict):
    def __contains__(self, name):
        return _ROW_INPUT.fullmatch(name) is not None

    def __getitem__(self, name):
        if name in self:
            return ("STRING", {"forceInput": True})
        raise KeyError(name)


class ShankConcatenateText:
    CATEGORY = "utils/text"
    DESCRIPTION = "Nối văn bản theo thứ tự từ trên xuống. Thêm, xoá hoặc bật/tắt từng dòng và nối từ cổng STRING."
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "concatenate"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "separator": ("STRING", {"default": " ", "widgetType": "SHANK_CONCATENATE_SEPARATOR"}),
                "text_rows": ("STRING", {
                    "default": '[["text_1",""],["text_2",""]]',
                    "widgetType": "SHANK_CONCATENATE_ROWS",
                }),
            },
            "optional": _TextInputs(),
        }

    def concatenate(self, separator, text_rows, **inputs):
        rows = json.loads(text_rows)
        if not isinstance(rows, list):
            raise ValueError("text_rows must be a list of text rows")

        values = []
        seen = set()
        for row in rows:
            if not isinstance(row, list) or len(row) not in (2, 3):
                raise ValueError("Each text row needs an input name, a value, and an optional enabled flag")
            name, fallback = row[:2]
            if not isinstance(name, str) or _ROW_INPUT.fullmatch(name) is None or name in seen:
                raise ValueError("Invalid or duplicate text row")
            seen.add(name)
            if len(row) == 3:
                if not isinstance(row[2], bool):
                    raise ValueError(f"{name} enabled flag must be a boolean")
                if not row[2]:
                    continue
            value = inputs.get(name, fallback)
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string")
            if value != "":
                values.append(value)
        return (separator.join(values),)
