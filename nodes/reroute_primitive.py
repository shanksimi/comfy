# Adapted from pythongosssss/ComfyUI-Custom-Scripts. See LICENSE-reroute-primitive.
# Hack: string type that is always equal in not equal comparisons
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


# Our any instance wants to be a wildcard string
any = AnyType("*")


class ShankReroutePrimitive:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"value": (any, )},
        }

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True

    RETURN_TYPES = (any,)
    FUNCTION = "route"
    CATEGORY = "utils"
    DESCRIPTION = "Đi dây và chia nhánh giá trị như số hoặc văn bản. Có thể thu gọn để canvas dễ đọc."

    def route(self, value):
        return (value,)
