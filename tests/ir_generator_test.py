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

    def test_variable_unary_minus(self):
        expect = """
        LoadIntConst(1, x1)
        Call(unary_-, [x1], x2)
        Call(print_int, [x2], x3)
        """

        self.assertEqual(trim(expect), string_ir("-1"))

    def test_while(self):
        expect = """
        Label(L1)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(L2), Label(L3))
        Label(L2)
        LoadBoolConst(False, x2)
        Jump(Label(L1))
        Label(L3)
        """

        self.assertEqual(trim(expect), string_ir("while true do false"))

    def test_if_then(self):
        expect = """
        LoadBoolConst(True, x1)
        CondJump(x1, Label(L1), Label(L2))
        Label(L1)
        LoadBoolConst(False, x2)
        Label(L2)
        """

        self.assertEqual(trim(expect), string_ir("if true then false"))

    def test_if_then_else(self):
        expect = """
        LoadBoolConst(True, x1)
        CondJump(x1, Label(L1), Label(L2))
        Label(L1)
        LoadIntConst(1, x3)
        LoadIntConst(2, x4)
        Call(+, [x3, x4], x5)
        LoadIntConst(3, x6)
        Call(*, [x5, x6], x7)
        Copy(x7, x2)
        Jump(Label(L3))
        Label(L2)
        LoadIntConst(5, x8)
        LoadIntConst(4, x9)
        Call(/, [x8, x9], x10)
        Copy(x10, x2)
        Label(L3)
        Call(print_int, [x2], x11)
        """

        self.assertEqual(trim(expect), string_ir("if true then (1+2) * 3 else 5 / 4"))

    def test_block_expression(self):
        expect = """
        LoadIntConst(2, x1)
        LoadIntConst(2, x2)
        Call(%, [x1, x2], x3)
        """

        self.assertEqual(trim(expect), string_ir("{{2%2};}"))

    def test_variable_declaration(self):
        expect = """
        LoadBoolConst(True, x1)
        Copy(x1, x2)
        LoadBoolConst(False, x3)
        Call(!=, [x2, x3], x4)
        Call(print_bool, [x4], x5)
        """

        self.assertEqual(trim(expect), string_ir("var x: Bool = true; x != false"))
