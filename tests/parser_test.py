from unittest import TestCase

import compiler.bast as ast
from compiler.parser import parse
from compiler.tokenizer import tokenize


# mypy: ignore-errors
class TestParser(TestCase):

    def test_simple_binary_summation_into_ast_node(self):
        tokens = tokenize("3 + 2")
        result = parse(tokens)

        expect = ast.BinaryOp(ast.Literal(3), "+", ast.Literal(2))
        self.assertEqual(expect, result)

    def test_simple_binary_summation_with_a_variable_into_ast_node(self):
        tokens = tokenize("3 - a")
        result = parse(tokens)

        expect = ast.BinaryOp(ast.Literal(3), "-", ast.Identifier("a"))
        self.assertEqual(expect, result)

    def test_binary_expression_with_multiple_variables_and_literals_into_ast_node(self):
        tokens = tokenize("2 - variable + 3 + x")
        result = parse(tokens)

        minus = ast.BinaryOp(ast.Literal(2), "-", ast.Identifier("variable"))
        plus2 = ast.BinaryOp(minus, "+", ast.Literal(3))
        expect = ast.BinaryOp(plus2, "+", ast.Identifier("x"))

        self.assertEqual(expect, result)

    def test_binary_parse_expression_right_associative(self):
        tokens = tokenize("2 - variable + 3 + x")
        result = parse(tokens, left_ast=False)

        plus2 = ast.BinaryOp(ast.Literal(3), "+", ast.Identifier("x"))
        plus1 = ast.BinaryOp(ast.Identifier("variable"), "+", plus2)
        expect = ast.BinaryOp(ast.Literal(2), "-", plus1)

        self.assertEqual(expect, result)

    def test_binary_parse_expression_multiplication(self):
        tokens = tokenize("2 - variable * 3 + x")
        result = parse(tokens)

        multi = ast.BinaryOp(ast.Identifier("variable"), "*", ast.Literal(3))
        minus = ast.BinaryOp(ast.Literal(2), "-", multi)
        expect = ast.BinaryOp(minus, "+", ast.Identifier("x"))

        self.assertEqual(expect, result)

    def test_binary_parse_expression_parenthesized(self):
        tokens = tokenize("2 - (variable + (3 + x))")
        result = parse(tokens)

        plus2 = ast.BinaryOp(ast.Literal(3), "+", ast.Identifier("x"))
        plus1 = ast.BinaryOp(ast.Identifier("variable"), "+", plus2)
        expect = ast.BinaryOp(ast.Literal(2), "-", plus1)

        self.assertEqual(expect, result)

    def test_raise_error_if_entire_input_is_not_parsed(self):
        tokens = tokenize("4 + 3 5")

        msg = "could not parse the whole expression"
        self.assertRaisesRegex(SyntaxError, msg, parse, tokens)

    def test_empty_input_returns_an_empty_ast_expression(self):
        self.assertEqual(ast.Expression(), parse([]))

    def test_invalid_input(self):
        test_cases = [
            ("Unexpected operator", "+ 2", SyntaxError, "integer literal or an identifier"),
            ("Incorrect parenthesis", ") 1 + 2(", SyntaxError, "integer literal or an identifier"),
            ("Unmatched parenthesis", "( 3 + 2 / 4", SyntaxError, r'line=1, column=11.* expected: "\)"'),
            ("Doubled Operator", " 3 ++ 4", SyntaxError, "line=1, column=5.* integer literal or an identifier"),
        ]

        for case, code, exception, msg in test_cases:
            with self.subTest(input=case):
                tokens = tokenize(code)
                self.assertRaisesRegex(exception, msg, parse, tokens)
