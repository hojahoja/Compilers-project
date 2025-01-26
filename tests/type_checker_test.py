from unittest import TestCase
from unittest.mock import patch

from compiler.c_types import Int, Bool, Unit, FunType
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck, SymTab


# mypy: ignore-errors

def check(code: str):
    return typecheck(parse(tokenize(code)))


class TestTypeChecker(TestCase):

    def test_typecheck_literals(self):
        test_cases = [
            ("Integer", "2", Int),
            ("Boolean", "false", Bool),
            ("Boolean", "true", Bool),
            ("Unit", "true", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_binary_operators(self):
        test_cases = [
            ("Addition", "1 + 3", Int),
            ("Subtraction", "1 - 3", Int),
            ("Multiplication", "2 * 3", Int),
            ("Division", "1 / 3", Int),
            ("Modulo", "3 % 3", Int),
            ("Multiple arithmetic operators", "1 + 3 - 2 * 4 / 2 % 2", Int),
            ("Less than", "3 < 3", Bool),
            ("Less or Equal", "3 <= 3", Bool),
            ("Greater than", "3 > 3", Bool),
            ("Greater or Equal", "3 >= 3", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_binary_operators_equal_not_equal(self):
        test_cases = [
            ("is equals", "1 == 3", Bool),
            ("is equals", "true == true", Bool),
            ("is not equals", "false != true", Bool),
            ("is not equals", "3 != 3", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_and_or_operators(self):
        short_circuit_or = """
        var evaluated_right_hand_side = false;
        true or { evaluated_right_hand_side = true; true };
        evaluated_right_hand_side
        """
        short_circuit_and = """
        var evaluated_right_hand_side = false;
        false and { evaluated_right_hand_side = true; true };
        evaluated_right_hand_side
        """
        test_cases = [
            ("false or true", Bool),
            ("true or false", Bool),
            ("false and true", Bool),
            ("true and true", Bool),
        ]

        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, check(case))

        for case, code in (("Short circuit or", short_circuit_or), ("Short circuit or", short_circuit_and)):
            with self.subTest(msg=case):
                self.assertEqual(Bool, check(code))

    def test_typecheck_unary_operators(self):
        test_cases = [
            ("Unary -", "-3", Int),
            ("not true", "not true", Bool),
            ("not false", "not false", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_while_loop(self):
        code = """
        var x = 3;
        while x > 0 do {
            x = x - 1;
        }
        x
        """
        self.assertEqual(Int, check(code))

    def test_typecheck_if_condition(self):
        test_cases = [
            ("Basic case integers", "if true then 3 else 4", Int),
            ("No else clause", "if 3 >= 3 then 5", Int),
            ("Boolean variable", "var x = true; if x then x", Bool),
            ("using blocks", "if {3 > 2} then {false} else {true}", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_untyped_variables(self):
        test_cases = [
            ("Boolean", "var k = true; k", Bool),
            ("Integer", "var x = 3; x", Int),
            ("Integer operation", "var x = 3; var y = 3;  x+y", Int),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_variable_assignment(self):
        test_cases = [
            ("Boolean", "var k = true; k = false", Bool),
            ("Integer", "var k = 4; k = 6", Int),
            ("Assign variable to another variable", "var x = 3; var k = 4; k = x", Int),
            ("Assign variable to same variable", "var x = true; x = x", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_blocks(self):
        test_cases = [
            ("{}", Unit),
            ("{}{}", Unit),
            ("{}{2}", Int),
            ("{}{2}", Int),
            ("{}{}false", Bool),
            ("var x = 3;{}{}x", Int),
            ("var x = 3; if x >= 3 then 4", Int),
            ("{var x = 3;{{x}}}", Int),
            ("{var x = 3;{{x}x=2}x}", Int),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, check(case))

    def test_typecheck_function_calls(self):
        test_cases = [
            ("Builtin: print_int", "var x = 2; print_int(x)", Unit),
            ("Builtin: print_bool", "var x = false; print_bool(x)", Unit),
            ("Builtin: read_int", "read_int()", Int),
        ]
        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    @patch("compiler.type_checker.SymTab")
    def test_typecheck_multiple_parameter_function_calls(self, mock_table):
        table = SymTab({"triple_param": FunType("function", (Int, Int, Bool), Bool)})
        mock_table.return_value = table

        code = "triple_param(3, 21, false)"
        with self.subTest(msg="Correct parameter types", input=code):
            self.assertEqual(Bool, check(code))

        code = "triple_param(3, 21, 0)"
        with self.subTest(msg="Incorrect parameter types", input=code):
            message = "mn=12.* parameter 3.*Bool.*Int"
            self.assertRaisesRegex(TypeError, message, check, code)

    def test_typecheck_errors(self):
        test_cases = [
            ("Left side binary operator", "true + 1", TypeError, r'mn=6.* "\+".*left.*Int.*Bool'),
            ("Right side binary operator", "1 < false", TypeError, r'mn=3.* "<".*right.*Int.*Bool'),
            ("Or operator accepts only bool", "1 or 2", TypeError, r'mn=4.* "or".*left.*Bool.*Int'),
            ("Unary - boolean", "- true", TypeError, r'mn=1.* "-".*Int.*Bool'),
            ("Unary not integer", "not 20", TypeError, r'mn=3.* "not".*Bool.*Int'),
            ("If condition not bool", "if 3 then 4", TypeError, r'mn=2.* expected.*Bool.*Int'),
            ("Then and else clause different type", "if true then 4 else false", TypeError, r'mn=2.*Int.*Bool'),
            ("Variable doesn't exist: Assignment", "x = 2", NameError, r'mn=1.* "x" is not defined'),
            ("Variable doesn't exist: Operator", "4 >= y", NameError, r'mn=6.* "y" is not defined'),
            ('Mismatching type for "="', "var x = true; x = 2", TypeError, r'mn=17.* "=".*Bool.*not.*Int'),
            ('Mismatching type for "=="', "2 == false", TypeError, r'mn=4.* "==".*Int.*not.*Bool'),
            ('Mismatching type for "!="', "true != 0", TypeError, r'mn=7.* "!=".*Bool.*not.*Int'),
            ("While-loop condition not bool", "while 1 do 3", TypeError, r'mn=5.* while-loop.*Bool.*Int'),
            ("print_int param not int", "print_int(false)", TypeError, r'mn=9.* parameter 1.*Int.*Bool'),
            ("print_bool param not bool", "print_bool(22)", TypeError, r'mn=10.* parameter 1.*Bool.*Int'),
        ]

        for case, code, error, message in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertRaisesRegex(error, message, check, code)
