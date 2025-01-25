from unittest import TestCase
from unittest.mock import patch

from compiler.interpreter import interpret
from compiler.parser import parse
from compiler.tokenizer import tokenize


# mypy: ignore-errors
class TestInterpreter(TestCase):

    def test_interpret_literal(self):
        test_cases = [
            ("9001", 9001),
            ("false", False),
            ("true", True),
            ("unit", None),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_unary_op(self):
        test_cases = [
            ("-9001", -9001),
            ("--9001", 9001),
            ("not false", True),
            ("not not false", False),
            ("not true", False),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_simple_arithmetics(self):
        test_cases = [
            ("2 + 3", 5),
            ("2 - 1", 1),
            ("2 * 3", 6),
            ("4 / 2", 2),
            ("4 / 3", 1),
            ("5 % 3", 2),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_simple_comparisons(self):
        test_cases = [
            ("2 == 3", False),
            ("2 != 1", True),
            ("2 <= 2", True),
            ("2 < 2", False),
            ("4 >= 4", True),
            ("4 > 4", False),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_assignment(self):
        test_cases = [
            ("var x = 4; x = 3; x", 3),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_if_clause(self):
        test_cases = [
            ("if 1 < 2 then 3", 3),
            ("if 3 < 2 then 3 else 5", 5),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_variable_assignment(self):
        test_cases = [
            ("var k = true; k", True),
            ("var k = unit; k", None),
            ("var x = 3; var y = 3;  x+y", 6),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_blocks(self):
        test_cases = [
            ("{}", None),
            ("{}{}", None),
            ("{}{2}", 2),
            ("2{}{}", None),
            ("{}{}2", 2),
            ("{var x= 3;}{x}", None),
            ("{var x= 3;}{}x", None),
            ("{}{var x= 3;}x", None),
            ("var x= 3;{}{}x", 3),
            ("var x = 3; if x >= 3 then 4", 4),
            ("{var x = 3;{{x}}}", 3),
            ("{var x = 3;{{x}x=2}x}", 2),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_while_loop(self):
        code = """
        var x = 3;
        while x > 0 do {
            x = x - 1;
        }
        x
        """
        self.assertEqual(0, interpret(parse(tokenize(code))))

    @patch("compiler.interpreter.print", side_effect=lambda x: None)
    def test_interpret_print_function_calls(self, mock_print):
        test_cases = [
            ("var x = 2; print_int(x); 2", 2),
            ("var x = false; print_bool(x); 2", False),
            ("var x = true; print_bool(x); 2", True),
        ]
        for case, expect in test_cases:
            with self.subTest(input=case):
                interpret(parse(tokenize(case)))
                mock_print.assert_called_once_with(expect)
                mock_print.reset_mock()

    @patch("compiler.interpreter.input")
    def test_interpret_input_function_calls(self, mock_input):
        mock_input.return_value = "4"
        self.assertEqual(4, interpret(parse(tokenize("var x = read_int(); x"))))

    @patch("compiler.interpreter.print", side_effect=lambda x: None)
    @patch("compiler.interpreter.input")
    def test_interpret_input_and_print_function_call(self, mock_input, mock_print):
        mock_input.return_value = "4"
        interpret(parse(tokenize("print_int(read_int())")))
        mock_print.assert_called_once_with(4)

    def test_interpret_and_or_operators(self):
        overload_or = """
        var evaluated_right_hand_side = false;
        true or { evaluated_right_hand_side = true; true };
        evaluated_right_hand_side
        """
        overload_and = """
        var evaluated_right_hand_side = false;
        false and { evaluated_right_hand_side = true; true };
        evaluated_right_hand_side
        """
        test_cases = [
            ("true or true", True),
            ("false or true", True),
            ("false or false", False),
            ("true or false", True),
            ("true and true", True),
            ("false and true", False),
            ("false and false", False),
            ("true and false", False),
            (overload_or, False),
            (overload_and, False),
        ]

        for case, expect in test_cases:
            with self.subTest(input=case):
                self.assertEqual(expect, interpret(parse(tokenize(case))))

    def test_interpret_invalid_input(self):
        test_cases = [
            ("2; x = 3", NameError, "column=4.* 'x' is not defined"),
            ("2; 3 = 3", SyntaxError, "column=6.* must be a variable name"),
            ("print_int(unit)", TypeError, "column=9.* expected int.* got, NoneType"),
            ("print_int(false)", TypeError, "column=9.* expected int.* got, bool"),
            ("print_bool(2)", TypeError, "column=10.* expected bool.* got, int"),
            ("print_int(2, 2)", TypeError, "column=9.* print_int.* 1 argument but 2"),
            ("print_bool(2, 2, 3)", TypeError, "column=10.* print_bool.* 1 argument but 3"),
            ("read_int(2)", TypeError, "column=8.* read_int.* 0 arguments but 1"),
        ]
        for case, error, msg in test_cases:
            with self.subTest(input=case):
                ast = parse(tokenize(case))
                self.assertRaisesRegex(error, msg, interpret, ast)
