# Adapted from cubiq/ComfyUI_essentials. See LICENSE-simple-math.
import math


class _AnyType(str):
    def __ne__(self, other):
        return False


_ANY = _AnyType("*")


class ShankSimpleMath:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "a": (_ANY, {"default": 0.0, "tooltip": "Giá trị cho biến a. Có thể nối số, chuỗi số hoặc tensor."}),
                "b": (_ANY, {"default": 0.0, "tooltip": "Giá trị cho biến b. Có thể nối số, chuỗi số hoặc tensor."}),
                "c": (_ANY, {"default": 0.0, "tooltip": "Giá trị cho biến c. Có thể nối số, chuỗi số hoặc tensor."}),
            },
            "required": {
                "value": ("STRING", { "multiline": False, "default": "", "tooltip": "Biểu thức cần tính. Ví dụ: a * b + c." }),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", )
    FUNCTION = "execute"
    CATEGORY = "utils"
    DESCRIPTION = "Tính biểu thức với a, b, c. Ví dụ: round(a * b / 8) * 8 hoặc a[2] để lấy chiều rộng từ tensor IMAGE."
    OUTPUT_TOOLTIPS = ("Kết quả làm tròn thành số nguyên.", "Kết quả dạng số thực.")

    def execute(self, value, a = 0.0, b = 0.0, c = 0.0, d = 0.0):
        import ast
        import operator as op

        if hasattr(a, 'shape'):
            a = list(a.shape)
        if hasattr(b, 'shape'):
            b = list(b.shape)
        if hasattr(c, 'shape'):
            c = list(c.shape)
        if hasattr(d, 'shape'):
            d = list(d.shape)

        if isinstance(a, str):
            a = float(a)
        if isinstance(b, str):
            b = float(b)
        if isinstance(c, str):
            c = float(c)
        if isinstance(d, str):
            d = float(d)

        operators = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.FloorDiv: op.floordiv,
            ast.Pow: op.pow,
            #ast.BitXor: op.xor,
            #ast.BitOr: op.or_,
            #ast.BitAnd: op.and_,
            ast.USub: op.neg,
            ast.Mod: op.mod,
            ast.Eq: op.eq,
            ast.NotEq: op.ne,
            ast.Lt: op.lt,
            ast.LtE: op.le,
            ast.Gt: op.gt,
            ast.GtE: op.ge,
            ast.Not: op.not_
        }

        op_functions = {
            'min': min,
            'max': max,
            'round': round,
            'sum': sum,
            'len': len,
        }

        def eval_(node):
            if isinstance(node, ast.Num): # number
                return node.n
            elif isinstance(node, ast.Name): # variable
                if node.id == "a":
                    return a
                if node.id == "b":
                    return b
                if node.id == "c":
                    return c
                if node.id == "d":
                    return d
            elif isinstance(node, ast.BinOp): # <left> <operator> <right>
                return operators[type(node.op)](eval_(node.left), eval_(node.right))
            elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
                return operators[type(node.op)](eval_(node.operand))
            elif isinstance(node, ast.Compare):  # comparison operators
                left = eval_(node.left)
                for op, comparator in zip(node.ops, node.comparators):
                    right = eval_(comparator)
                    if not operators[type(op)](left, right):
                        return 0
                    left = right
                return 1
            elif isinstance(node, ast.BoolOp):  # boolean operators (And, Or)
                values = (eval_(value) for value in node.values)
                return all(values) if isinstance(node.op, ast.And) else any(values)
            elif isinstance(node, ast.Call): # custom function
                if isinstance(node.func, ast.Name) and node.func.id in op_functions and not node.keywords:
                    args =[eval_(arg) for arg in node.args]
                    return op_functions[node.func.id](*args)
                raise ValueError("Hàm không được hỗ trợ trong Simple Math.")
            elif isinstance(node, ast.Subscript): # indexing or slicing
                value = eval_(node.value)
                if isinstance(node.slice, ast.Constant):
                    return value[node.slice.value]
                else:
                    return 0
            else:
                return 0

        result = eval_(ast.parse(value, mode='eval').body)

        if isinstance(result, float) and not math.isfinite(result):
            result = 0.0

        return (round(result), float(result))
