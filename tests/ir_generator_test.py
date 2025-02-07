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

    def test_ir_simple_calculation(self):
        expect = """
        Label(start)
        LoadIntConst(1, x1)
        LoadIntConst(2, x2)
        LoadIntConst(3, x3)
        Call(*, [x2, x3], x4)
        Call(+, [x1, x4], x5)
        Call(print_int, [x5], x6)
        """

        self.assertEqual(trim(expect), string_ir("1 + 2 * 3"))

    def test_ir_assignment(self):
        expect = """
        Label(start)
        LoadIntConst(3, x1)
        Copy(x1, x2)
        LoadIntConst(2, x3)
        Copy(x3, x2)
        Call(print_int, [x2], x4)
        """

        self.assertEqual(trim(expect), string_ir("var x: Int = 3; x = 2"))

    def test_ir_and(self):
        expect = """
        Label(start)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(and_right), Label(and_skip))
        Label(and_right)
        LoadBoolConst(True, x2)
        Copy(x2, x3)
        Jump(Label(and_end))
        Label(and_skip)
        LoadBoolConst(False, x3)
        Jump(Label(and_end))
        Label(and_end)
        Call(print_bool, [x3], x4)
        """

        self.assertEqual(trim(expect), string_ir("true and true"))

    def test_ir_or(self):
        expect = """
        Label(start)
        LoadBoolConst(False, x1)
        CondJump(x1, Label(or_skip), Label(or_right))
        Label(or_right)
        LoadBoolConst(True, x2)
        Copy(x2, x3)
        Jump(Label(or_end))
        Label(or_skip)
        LoadBoolConst(True, x3)
        Jump(Label(or_end))
        Label(or_end)
        Call(print_bool, [x3], x4)
        """

        self.assertEqual(trim(expect), string_ir("false or true"))

    def test_ir_multiple_labels_with_the_same_name(self):
        expect = """
        Label(start)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(then), Label(if_end))
        Label(then)
        LoadBoolConst(False, x2)
        Label(if_end)
        LoadBoolConst(True, x3)
        CondJump(x3, Label(then2), Label(if_end2))
        Label(then2)
        LoadBoolConst(False, x4)
        Label(if_end2)
        LoadBoolConst(True, x5)
        CondJump(x5, Label(then3), Label(if_end3))
        Label(then3)
        LoadBoolConst(False, x6)
        Label(if_end3)
        """

        self.assertEqual(trim(expect), string_ir("if true then false; if true then false; if true then false"))

    def test_ir_variable_unary_minus(self):
        expect = """
        Label(start)
        LoadIntConst(1, x1)
        Call(unary_-, [x1], x2)
        Call(print_int, [x2], x3)
        """

        self.assertEqual(trim(expect), string_ir("-1"))

    def test_ir_while(self):
        expect = """
        Label(start)
        Label(while_start)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(while_body), Label(while_end))
        Label(while_body)
        LoadBoolConst(False, x2)
        Jump(Label(while_start))
        Label(while_end)
        """

        self.assertEqual(trim(expect), string_ir("while true do false"))

    def test_ir_break_continue(self):
        code_break = """
        var x = 0;
        while true do {
            while true do {
                if x % 5 == 0 then {
                    break;
                } else {
                    x = x + 1;
                    break;
                }
            }
            if x > 77 then {
                break;
            }
            x = x + 1;
        }
        x
        """

        expect_break = """
        Label(start)
        LoadIntConst(0, x1)
        Copy(x1, x2)
        Label(while_start)
        LoadBoolConst(True, x3)
        CondJump(x3, Label(while_body), Label(while_end))
        Label(while_body)
        Label(while_start2)
        LoadBoolConst(True, x4)
        CondJump(x4, Label(while_body2), Label(while_end2))
        Label(while_body2)
        LoadIntConst(5, x5)
        Call(%, [x2, x5], x6)
        LoadIntConst(0, x7)
        Call(==, [x6, x7], x8)
        CondJump(x8, Label(then), Label(else))
        Label(then)
        Jump(Label(while_end2))
        Copy(unit, x9)
        Jump(Label(if_end))
        Label(else)
        LoadIntConst(1, x10)
        Call(+, [x2, x10], x11)
        Copy(x11, x2)
        Jump(Label(while_end2))
        Copy(unit, x9)
        Label(if_end)
        Jump(Label(while_start2))
        Label(while_end2)
        LoadIntConst(77, x12)
        Call(>, [x2, x12], x13)
        CondJump(x13, Label(then2), Label(if_end2))
        Label(then2)
        Jump(Label(while_end))
        Label(if_end2)
        LoadIntConst(1, x14)
        Call(+, [x2, x14], x15)
        Copy(x15, x2)
        Jump(Label(while_start))
        Label(while_end)
        Call(print_int, [x2], x16)
        """

        code_continue = code_break.replace("break", "continue")
        expect_continue = expect_break.replace("Jump(Label(while_end", "Jump(Label(while_start")

        test_cases = [
            ("break", code_break, expect_break),
            ("continue", code_continue, expect_continue),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case):
                self.assertEqual(trim(expect), string_ir(code))

    def test_ir_if_then(self):
        expect = """
        Label(start)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(then), Label(if_end))
        Label(then)
        LoadBoolConst(False, x2)
        Label(if_end)
        """

        self.assertEqual(trim(expect), string_ir("if true then false"))

    def test_ir_if_then_else(self):
        expect = """
        Label(start)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(then), Label(else))
        Label(then)
        LoadIntConst(1, x3)
        LoadIntConst(2, x4)
        Call(+, [x3, x4], x5)
        LoadIntConst(3, x6)
        Call(*, [x5, x6], x7)
        Copy(x7, x2)
        Jump(Label(if_end))
        Label(else)
        LoadIntConst(5, x8)
        LoadIntConst(4, x9)
        Call(/, [x8, x9], x10)
        Copy(x10, x2)
        Label(if_end)
        Call(print_int, [x2], x11)
        """

        self.assertEqual(trim(expect), string_ir("if true then (1+2) * 3 else 5 / 4"))

    def test_ir_if_returns_unit_when_clauses_have_no_return_values(self):
        code = "if true then {print_int(2);} else {print_int(3);}"
        expect = """
        Label(start)
        LoadBoolConst(True, x1)
        CondJump(x1, Label(then), Label(else))
        Label(then)
        LoadIntConst(2, x3)
        Call(print_int, [x3], x4)
        Copy(unit, x2)
        Jump(Label(if_end))
        Label(else)
        LoadIntConst(3, x5)
        Call(print_int, [x5], x6)
        Copy(unit, x2)
        Label(if_end)
        """

        self.assertEqual(trim(expect), string_ir(code))

    def test_ir_block_expression(self):
        expect = """
        Label(start)
        LoadIntConst(2, x1)
        LoadIntConst(2, x2)
        Call(%, [x1, x2], x3)
        """

        self.assertEqual(trim(expect), string_ir("{{2%2};}"))

    def test_ir_variable_declaration(self):
        expect = """
        Label(start)
        LoadBoolConst(True, x1)
        Copy(x1, x2)
        LoadBoolConst(False, x3)
        Call(!=, [x2, x3], x4)
        Call(print_bool, [x4], x5)
        """

        self.assertEqual(trim(expect), string_ir("var x: Bool = true; x != false"))

    def test_ir_builtin_function_calls(self):
        print_int = """
        Label(start)
        LoadIntConst(5, x1)
        Call(print_int, [x1], x2)
        """
        print_bool = """
        Label(start)
        LoadBoolConst(True, x1)
        Call(print_bool, [x1], x2)
        """
        read_int = """
        Label(start)
        Call(read_int, [], x1)
        Call(print_int, [x1], x2)
        """

        test_cases = [
            ("print_int", "print_int(5)", print_int),
            ("print_bool", "print_bool(true)", print_bool),
            ("read_int", "read_int()", read_int),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, code=code):
                self.assertEqual(trim(expect), string_ir(code))
