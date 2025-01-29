from unittest import TestCase

from compiler.ir_generator import generate_ir, ROOT_TYPES
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck


# mypy: ignore-errors

def string_ir(code: str) -> str:
    expr = parse(tokenize(code))
    typecheck(expr)
    ir = generate_ir(ROOT_TYPES, expr)
    return "\n".join([str(i) for i in ir])


def trim(ir_code: str) -> str:
    lines = ir_code.splitlines()
    ir_code = "\n".join(line.strip() for line in lines[1:])
    return ir_code.rstrip("\n")


class TestIrGenerator(TestCase):

    def test_simple_calculation(self):
        expect = """
        LoadIntConst(1, x1)
        LoadIntConst(2, x2)
        LoadIntConst(3, x3)
        Call(*, [x2, x3], x4)
        Call(+, [x1, x4], x5)
        Call(print_int, [x5], x6)
        """

        self.assertEqual(trim(expect), string_ir("1 + 2 * 3"))

    def test_if(self):
        expect = """
        LoadBoolConst(True, x1)
        CondJump(x1, Label(L1), Label(L2))
        Label(L1)
        LoadBoolConst(False, x2)
        Label(L2)
        """

        self.assertEqual(trim(expect), string_ir("if true then false"))
