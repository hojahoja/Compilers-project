from unittest import TestCase

from compiler.c_types import Int, Bool
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck


# mypy: ignore-errors

def check(code: str):
    return typecheck(parse(tokenize(code)))


class TestTypeChecker(TestCase):

    def test_type_check_literals(self):
        test_cases = [
            ("Integer", "2", Int),
            ("Boolean", "false", Bool),
            ("Boolean", "true", Bool),
            ("Unit", "true", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(case=case):
                self.assertEqual(expect, check(code))

    def test_type_check_binary_operators(self):
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
            with self.subTest(case=case):
                self.assertEqual(expect, check(code))

    def test_type_check_unary_operators(self):
        test_cases = [
            ("Unary -", "-3", Int),
            ("not", "not true", Bool),
            ("not", "not false", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(case=case):
                self.assertEqual(expect, check(code))


    def test_type_check_errors(self):
        pass
        test_cases = [
            ("Left side binary operator", "true + 1", TypeError, r'mn=6.* "\+".*left.*Integer.*Boolean'),
            ("Right side binary operator", "1 < false", TypeError, r'mn=3.* "<".*right.*Integer.*Boolean'),
            ("Unary - boolean", "- true", TypeError, r'mn=1.* "-".*Integer.*Boolean'),
            ("Unary not integer", "not 20", TypeError, r'mn=3.* "not".*Boolean.*Integer'),
        ]

        for case, code, error, message in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertRaisesRegex(error, message, check, code)
