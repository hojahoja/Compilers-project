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

    def test_parse_if_then_else_expression(self):
        tokens = tokenize("if a then b + c else x * 3")

        plus = ast.BinaryOp(ast.Identifier("b"), "+", ast.Identifier("c"))
        mult = ast.BinaryOp(ast.Identifier("x"), "*", ast.Literal(3))
        expect = ast.IfExpression(ast.Identifier("a"), plus, mult)

        self.assertEqual(expect, parse(tokens))

    # TODO change operators
    def test_parse_nested_if_statements(self):
        mult = ast.BinaryOp(ast.Identifier("a"), "*", ast.Identifier("b"))
        second_if = ast.IfExpression(ast.Identifier("true"), ast.Identifier("c"), None)
        expect = ast.IfExpression(mult, second_if, None)

        self.assertEqual(expect, parse(tokenize("if a * b then if true then c")))

    # TODO change operators
    def test_parse_if_else_if_expressions(self):
        plus = ast.BinaryOp(ast.Identifier("a"), "+", ast.Identifier("b"))
        mult = ast.BinaryOp(ast.Identifier("b"), "*", ast.Identifier("c"))
        second_if = ast.IfExpression(mult, ast.Identifier("b"), None)
        expect = ast.IfExpression(plus, ast.Identifier("a"), second_if)

        self.assertEqual(expect, parse(tokenize("if a + b then a else if b * c then b")))

    def test_parse_if_statements_as_part_of_other_expressions(self):
        if_expr = ast.IfExpression(ast.Identifier("a"), ast.Identifier("b"), None)
        expected = ast.BinaryOp(ast.Literal(1), "+", if_expr)

        self.assertEqual(expected, parse(tokenize("1 + if a then b")))

    def test_parse_function_call(self):
        args = [ast.Identifier("a"), ast.Literal(3)]
        expect = ast.FuncExpression(ast.Identifier("function"), args)

        self.assertEqual(expect, parse(tokenize("function(a, 3)")))

    def test_parse_nested_function_call(self):
        tokens = tokenize("function(a, function(b, c))")

        func2 = ast.FuncExpression(ast.Identifier("function"), [ast.Identifier("b"), ast.Identifier("c")])
        args = [ast.Identifier("a"), func2]
        expect = ast.FuncExpression(ast.Identifier("function"), args)

        self.assertEqual(expect, parse(tokens))

    def test_expression_inside_function_call(self):
        tokens = tokenize("function(if a then b, c)")

        if_expr = ast.IfExpression(ast.Identifier("a"), ast.Identifier("b"), None)
        expect = ast.FuncExpression(ast.Identifier("function"), [if_expr, ast.Identifier("c")])

        self.assertEqual(expect, parse(tokens))

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
            ("If without then", "if true x + 1", SyntaxError, r'line=1, column=9.* expected: "then"'),
            ("Else without if", "1 + 2 else 3", SyntaxError, "could not parse the whole expression"),
            ("Single else", "else", SyntaxError, "integer literal or an identifier"),
            ("No function identifier", "1 + (a, 3)", SyntaxError, r'line=1, column=7.* expected: "\)"'),
            ("Literal is not a valid func name", "2 (a, 3)", SyntaxError, "could not parse the whole expression"),
            ("Function missing punctuation", "func(a 3)", SyntaxError, r'line=1, column=8.* expected: "\)"'),
        ]

        for case, code, exception, msg in test_cases:
            with self.subTest(input=case):
                tokens = tokenize(code)
                self.assertRaisesRegex(exception, msg, parse, tokens)
