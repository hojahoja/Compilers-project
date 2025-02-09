from unittest import TestCase
from unittest.mock import patch

import compiler.bast as ast
from compiler.parser import parse
from compiler.tokenizer import tokenize, Location


# mypy: ignore-errors
class TestParser(TestCase):

    def setUp(self):
        mock_location = Location("no file", 1, 1)
        self.location_patcher = patch('compiler.tokenizer.Location', return_value=mock_location)
        self.location_patcher.start()

    def tearDown(self):
        self.location_patcher.stop()

    def test_parse_simple_binary_summation_into_ast_node(self):
        tokens = tokenize("3 + 2")
        result = parse(tokens)

        expect = ast.BinaryOp(ast.Literal(3), "+", ast.Literal(2))
        self.assertEqual(expect, result)

    def test_parse_simple_binary_summation_with_a_variable_into_ast_node(self):
        tokens = tokenize("3 - a")
        result = parse(tokens)

        expect = ast.BinaryOp(ast.Literal(3), "-", ast.Identifier("a"))
        self.assertEqual(expect, result)

    def test_parse_binary_expression_with_multiple_variables_and_literals_into_ast_node(self):
        tokens = tokenize("2 - variable + 3 + x")
        result = parse(tokens)

        minus = ast.BinaryOp(ast.Literal(2), "-", ast.Identifier("variable"))
        plus2 = ast.BinaryOp(minus, "+", ast.Literal(3))
        expect = ast.BinaryOp(plus2, "+", ast.Identifier("x"))

        self.assertEqual(expect, result)

    def test_parse_binary_parse_expression_multiplication(self):
        tokens = tokenize("2 - variable * 3 + x")
        result = parse(tokens)

        multi = ast.BinaryOp(ast.Identifier("variable"), "*", ast.Literal(3))
        minus = ast.BinaryOp(ast.Literal(2), "-", multi)
        expect = ast.BinaryOp(minus, "+", ast.Identifier("x"))

        self.assertEqual(expect, result)

    def test_parse_binary_parse_expression_parenthesized(self):
        tokens = tokenize("2 - (variable + (3 + x))")
        result = parse(tokens)

        plus2 = ast.BinaryOp(ast.Literal(3), "+", ast.Identifier("x"))
        plus1 = ast.BinaryOp(ast.Identifier("variable"), "+", plus2)
        expect = ast.BinaryOp(ast.Literal(2), "-", plus1)

        self.assertEqual(expect, result)

    def test_parse_remainder_expression(self):
        mod = ast.BinaryOp(ast.Literal(3), "%", ast.Literal(2))
        expect = ast.BinaryOp(ast.Identifier("a"), "+", mod)

        self.assertEqual(expect, parse(tokenize("a + 3 % 2")))

    def test_parse_expression_with_relative_operator(self):
        expect = ast.BinaryOp(ast.Literal(2), ">", ast.Identifier("x"))

        self.assertEqual(expect, parse(tokenize("2 > x")))

    def test_parse_expression_with_equals_operator(self):
        expect = ast.BinaryOp(ast.Literal(2), "==", ast.Identifier("x"))

        self.assertEqual(expect, parse(tokenize("2 == x")))

    def test_parse_expression_true_and_false_literals_have_correct_values(self):
        expect = ast.BinaryOp(ast.Literal(True), "==", ast.Literal(False))
        self.assertEqual(expect, parse(tokenize("true == false")))

    def test_parse_expression_with_equals_and_not_equals_operators(self):
        eq = ast.BinaryOp(ast.Literal(2), "==", ast.Identifier("x"))
        expect = ast.BinaryOp(eq, "!=", ast.Literal(3))

        self.assertEqual(expect, parse(tokenize("2 == x != 3")))

    def test_parse_expression_with_relative_and_arithmetic_operators(self):
        mult = ast.BinaryOp(ast.Literal(2), "*", ast.Literal(3))
        plus = ast.BinaryOp(ast.Literal(3), "+", ast.Identifier("x"))
        gt = ast.BinaryOp(ast.Literal(2), ">", plus)
        expect = ast.BinaryOp(gt, "!=", mult)

        self.assertEqual(expect, parse(tokenize("2 > 3 + x != 2 * 3")))

    def test_parse_expression_with_and_operator(self):
        expect = ast.BinaryOp(ast.Identifier("x"), "and", ast.Literal(2))
        self.assertEqual(expect, parse(tokenize("x and 2")))

    def test_parse_expression_with_or_operator(self):
        expect = ast.BinaryOp(ast.Identifier("x"), "or", ast.Literal(2))
        self.assertEqual(expect, parse(tokenize("x or 2")))

    def test_parse_chained_and_or_operators(self):
        and_expr = ast.BinaryOp(ast.Identifier("x"), "and", ast.Literal(2))
        or1 = ast.BinaryOp(and_expr, "or", ast.Literal(3))
        expect = ast.BinaryOp(or1, "or", ast.Literal(5))

        self.assertEqual(expect, parse(tokenize("x and 2 or 3 or 5")))

    def test_parse_and_or_operators_with_arithmetics_and_parentheses(self):
        plus = ast.BinaryOp(ast.Literal(3), "+", ast.Literal(3))
        and_expr = ast.BinaryOp(plus, "and", ast.Identifier("x"))
        mul = ast.BinaryOp(and_expr, "*", ast.Literal(3))
        expect = ast.BinaryOp(mul, "or", ast.Identifier("x"))

        self.assertEqual(expect, parse(tokenize("(3 + 3 and x) * 3 or x")))

    def test_parse_unary_operator(self):
        self.assertEqual(ast.UnaryOp("-", ast.Literal(3)), parse(tokenize("- 3")))

    def test_parse_chained_unary_operators(self):
        minus3 = ast.UnaryOp("-", ast.Identifier("x"))
        not3 = ast.UnaryOp("not", minus3)
        minus2 = ast.UnaryOp("-", not3)
        minus1 = ast.UnaryOp("-", minus2)
        not2 = ast.UnaryOp("not", minus1)
        expect = ast.UnaryOp("not", not2)

        self.assertEqual(expect, parse(tokenize("not not - - not - x")))

    def test_parse_chain_binary_minus_mixed_with_chained_unary_minus(self):
        minus3 = ast.UnaryOp("-", ast.Literal(3))
        minus2 = ast.UnaryOp("-", minus3)
        expect = ast.BinaryOp(ast.Literal(3), "-", minus2)

        self.assertEqual(expect, parse(tokenize("3---3")))

    def test_parse_unary_minus_and_mult_parentheses(self):
        mult = ast.BinaryOp(ast.Identifier("x"), "*", ast.Literal(3))
        plus = ast.BinaryOp(ast.Literal(1), "+", mult)
        expect = ast.UnaryOp("-", plus)

        self.assertEqual(expect, parse(tokenize("- (1 + x * 3)")))

    def test_parse_assignment_operator(self):
        expect = ast.BinaryOp(ast.Identifier("x"), "=", ast.Literal(2))
        self.assertEqual(expect, parse(tokenize("x = 2")))

    def test_parse_assignment_operator_is_right_associative(self):
        eq3 = ast.BinaryOp(ast.Literal(3), "=", ast.Identifier("x"))
        eq2 = ast.BinaryOp(ast.Identifier("variable"), "=", eq3)
        expect = ast.BinaryOp(ast.Literal(2), "=", eq2)

        self.assertEqual(expect, parse(tokenize("2 = variable = 3 = x")))

    def test_parse_assignment_operator_with_arithmetics(self):
        mul = ast.BinaryOp(ast.Literal(3), "*", ast.Identifier("x"))
        plus = ast.BinaryOp(ast.Identifier("variable"), "+", mul)
        expect = ast.BinaryOp(ast.Identifier("x"), "=", plus)

        self.assertEqual(expect, parse(tokenize("x = variable + 3 * x")))

    def test_parse_if_then_else_expression(self):
        tokens = tokenize("if a then b + c else x * 3")

        plus = ast.BinaryOp(ast.Identifier("b"), "+", ast.Identifier("c"))
        mult = ast.BinaryOp(ast.Identifier("x"), "*", ast.Literal(3))
        expect = ast.IfExpression(ast.Identifier("a"), plus, mult)

        self.assertEqual(expect, parse(tokens))

    def test_parse_nested_if_statements(self):
        mult = ast.BinaryOp(ast.Identifier("a"), "*", ast.Identifier("b"))
        second_if = ast.IfExpression(ast.Literal(True), ast.Identifier("c"), None)
        expect = ast.IfExpression(mult, second_if, None)

        self.assertEqual(expect, parse(tokenize("if a * b then if true then c")))

    def test_parse_if_else_if_expressions(self):
        plus = ast.BinaryOp(ast.Identifier("a"), ">=", ast.Identifier("b"))
        mult = ast.BinaryOp(ast.Identifier("b"), "!=", ast.Identifier("c"))
        second_if = ast.IfExpression(mult, ast.Identifier("b"), None)
        expect = ast.IfExpression(plus, ast.Identifier("a"), second_if)

        self.assertEqual(expect, parse(tokenize("if a >= b then a else if b != c then b")))

    def test_parse_if_statements_as_part_of_other_expressions(self):
        if_expr = ast.IfExpression(ast.Identifier("a"), ast.Identifier("b"), None)
        expected = ast.BinaryOp(ast.Literal(1), "+", if_expr)

        self.assertEqual(expected, parse(tokenize("1 + if a then b")))

    def test_parse_simple_while_loop(self):
        expect = ast.WhileExpression(ast.Literal(True), ast.Identifier("x"))
        self.assertEqual(expect, parse(tokenize("while true do x ")))

    def test_parse_simple_while_loop_as_part_of_other_expression(self):
        while_expr = ast.WhileExpression(ast.Identifier("a"), ast.Identifier("b"))
        expected = ast.BinaryOp(ast.Literal(1), "+", while_expr)

        self.assertEqual(expected, parse(tokenize("1 + while a do b")))

    def test_parse_nested_while_loops(self):
        eq = ast.BinaryOp(ast.Identifier("a"), "==", ast.Identifier("b"))
        assign = ast.BinaryOp(ast.Identifier("c"), "=", ast.Literal(3))
        second_while = ast.WhileExpression(ast.Literal(True), assign)
        expect = ast.WhileExpression(eq, second_while)

        self.assertEqual(expect, parse(tokenize("while a == b do while true do c = 3")))

    def test_parse_continue_expression(self):
        block = ast.BlockExpression([ast.Literal(3), ast.ContinueExpression(), ast.Identifier("x")])
        expect = ast.WhileExpression(ast.Literal(True), block)

        self.assertEqual(expect, parse(tokenize("while true do {3; continue; x}")))

    def test_parse_break_expression(self):
        block = ast.BlockExpression([ast.Literal(3), ast.BreakExpression(), ast.Identifier("x")])
        expect = ast.WhileExpression(ast.Literal(True), block)

        self.assertEqual(expect, parse(tokenize("while true do {3; break; x}")))

    def test_parse_function_call(self):
        args = [ast.Identifier("a"), ast.Literal(3)]
        expect = ast.FuncExpression(ast.Identifier("function"), args)

        self.assertEqual(expect, parse(tokenize("function(a, 3)")))

    def test_parse_empty_function_call(self):
        self.assertEqual(ast.FuncExpression(ast.Identifier("f"), []), parse(tokenize("f()")))

    def test_parse_nested_function_call(self):
        tokens = tokenize("function(a, function(b, c))")

        func2 = ast.FuncExpression(ast.Identifier("function"), [ast.Identifier("b"), ast.Identifier("c")])
        args = [ast.Identifier("a"), func2]
        expect = ast.FuncExpression(ast.Identifier("function"), args)

        self.assertEqual(expect, parse(tokens))

    def test_parse_expression_inside_function_call(self):
        tokens = tokenize("function(if a then b, c)")

        if_expr = ast.IfExpression(ast.Identifier("a"), ast.Identifier("b"), None)
        expect = ast.FuncExpression(ast.Identifier("function"), [if_expr, ast.Identifier("c")])

        self.assertEqual(expect, parse(tokens))

    def test_parse_complex_case(self):
        command = """
        if x != 3 then
            if x >= 0 then
                // This makes no sense
                print(x)
            else if x <= 0 then
                print(x * -1) 
        else
            print(end=0,x or 5)  
        """
        x = ast.Identifier("x")
        end = ast.Identifier("end")
        three = ast.Literal(3)
        zero = ast.Literal(0)
        one = ast.Literal(1)
        five = ast.Literal(5)

        x_neq_3 = ast.BinaryOp(x, '!=', three)
        x_ge_0 = ast.BinaryOp(x, '>=', zero)
        x_le_0 = ast.BinaryOp(x, '<=', zero)
        x_mult_neg_1 = ast.BinaryOp(x, '*', ast.UnaryOp('-', one))
        end_eq_0 = ast.BinaryOp(end, '=', zero)
        x_or_5 = ast.BinaryOp(x, 'or', five)

        print_x = ast.FuncExpression(ast.Identifier('print'), [x])
        print_x_mult_neg_1 = ast.FuncExpression(ast.Identifier('print'), [x_mult_neg_1])
        print_end_x_or_5 = ast.FuncExpression(ast.Identifier('print'), [end_eq_0, x_or_5])

        if_x_le_0 = ast.IfExpression(x_le_0, print_x_mult_neg_1, print_end_x_or_5)
        if_x_ge_0 = ast.IfExpression(x_ge_0, print_x, if_x_le_0)
        expect = ast.IfExpression(x_neq_3, if_x_ge_0, None)

        self.assertEqual(expect, parse(tokenize(command)))

    # Stupid because making this test was ass.
    def test_parse_stupidly_complex_case(self):
        command = """
        var x = 3;
        while x > -1 do {
            if x == 0 then
                x = x + 1
            else if x > 0 then
                x = x - 1
        }
        win_million_dollars()
        """

        x_decl = ast.Declaration(ast.Identifier("x"), ast.Literal(3))
        minus_one = ast.UnaryOp("-", ast.Literal(1))
        x_greater_than_minus_one = ast.BinaryOp(ast.Identifier("x"), ">", minus_one)
        x_equals_zero = ast.BinaryOp(ast.Identifier("x"), "==", ast.Literal(0))
        x_greater_than_zero = ast.BinaryOp(ast.Identifier("x"), ">", ast.Literal(0))

        x_plus_one = ast.BinaryOp(ast.Identifier("x"), "+", ast.Literal(1))
        x_is_x_plus_one = ast.BinaryOp(ast.Identifier("x"), "=", x_plus_one)

        x_minus_one = ast.BinaryOp(ast.Identifier("x"), "-", ast.Literal(1))
        x_is_x_minus_one = ast.BinaryOp(ast.Identifier("x"), "=", x_minus_one)

        inner_if_expression = ast.IfExpression(x_greater_than_zero, x_is_x_minus_one, None)
        outer_if_expression = ast.IfExpression(x_equals_zero, x_is_x_plus_one, inner_if_expression, )
        while_block = ast.BlockExpression([outer_if_expression], )
        while_expression = ast.WhileExpression(x_greater_than_minus_one, while_block)

        win_million_dollars_call = ast.FuncExpression(ast.Identifier("win_million_dollars"), [])

        expect = ast.BlockExpression([x_decl, while_expression, win_million_dollars_call])

        self.assertEqual(expect, parse(tokenize(command)))

    def test_parse_simple_variable_declaration(self):
        expect = ast.Declaration(ast.Identifier("x"), ast.Literal(2))
        self.assertEqual(expect, parse(tokenize("var x = 2")))

    def test_parse_var_inside_block(self):
        decl = ast.Declaration(ast.Identifier("x"), ast.Literal(2))
        expect = ast.BlockExpression([decl])
        self.assertEqual(expect, parse(tokenize("{var x = 2}")))

    def test_parse_var_inside_block_after_then(self):
        decl = ast.Declaration(ast.Identifier("x"), ast.Literal(2))
        block = ast.BlockExpression([decl])
        expect = ast.IfExpression(ast.Literal(3), block, None)
        self.assertEqual(expect, parse(tokenize("if 3 then {var x = 2}")))

    def test_parse_variable_declaration_after_braces(self):
        inner_block = ast.BlockExpression([])
        decl = ast.Declaration(ast.Identifier("x"), ast.Literal(2))
        expect = ast.BlockExpression([inner_block, decl])
        for code in ("{} var x = 2", "{}; var x = 2"):
            with self.subTest(input=code):
                self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_typed_variable_declaration(self):
        plus = ast.BinaryOp(ast.Identifier("x"), "+", ast.Literal(10))
        expect = ast.Declaration(ast.Identifier("x"), plus, ast.TypeExpression("Int"))
        self.assertEqual(expect, parse(tokenize("var x: Int = x + 10")))

    def test_parse_typed_variable_declaration_with_custom_type(self):
        plus = ast.BinaryOp(ast.Identifier("x"), "+", ast.Literal(10))
        expect = ast.Declaration(ast.Identifier("x"), plus, ast.TypeExpression("Mint"))
        self.assertEqual(expect, parse(tokenize("var x: Mint = x + 10")))

    def test_parse_expression_with_semicolon(self):
        eq = ast.BinaryOp(ast.Identifier("a"), "=", ast.Literal(3))
        expect = ast.BlockExpression([eq, ast.Literal(None)])
        self.assertEqual(expect, parse(tokenize("a = 3;")))

    def test_parse_expression_with_semicolon_and_another_expression_after(self):
        eq = ast.BinaryOp(ast.Identifier("a"), "=", ast.Literal(3))
        expect = ast.BlockExpression([eq, ast.Literal(2)])
        self.assertEqual(expect, parse(tokenize("a = 3; 2")))

    def test_parse_empty_braced_block(self):
        self.assertEqual(ast.BlockExpression([]), parse(tokenize("{}")))

    def test_parse_empty_braced_block_with_semicolon(self):
        expect = ast.BlockExpression([ast.BlockExpression([]), ast.Literal(None)])
        self.assertEqual(expect, parse(tokenize("{};")))

    def test_parse_top_level_statement_semicolon_without_braces(self):
        expect = ast.BlockExpression([ast.Literal(2), ast.Literal(None)])
        self.assertEqual(expect, parse(tokenize("2;")))

    def test_parse_top_level_multiple_statements_semicolon_without_braces(self):
        eq = ast.BinaryOp(ast.Identifier("x"), "=", ast.Literal(2))
        expect = ast.BlockExpression([eq, ast.Literal(2), ast.Literal(3)])

        with self.subTest(msg="Without trailing semicolon"):
            self.assertEqual(expect, parse(tokenize("x = 2; 2; 3")))

        with self.subTest(msg="With trailing semicolon"):
            expect.body.append(ast.Literal(None))
            self.assertEqual(expect, parse(tokenize("x = 2; 2; 3;")))

    def test_parse_braced_block_with_a_statement(self):
        expect1 = ast.BlockExpression([ast.Literal(2)])
        expect2 = ast.BlockExpression([ast.Literal(2), ast.Literal(None)])
        expect3 = ast.BlockExpression([expect1, ast.Literal(None)])
        expect4 = ast.BlockExpression([expect2, ast.Literal(None)])
        test_cases = [
            ("With a statement", "{2}", expect1),
            ("With a statement with semicolon inside", "{2;}", expect2),
            ("With a statement with semicolon outside", "{2};", expect3),
            ("With a statement with semicolon inside and outside", "{2;};", expect4),
        ]
        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_expression_after_braces_without_semicolon(self):
        expect = ast.BlockExpression([ast.BlockExpression([]), ast.Literal(2)])
        self.assertEqual(expect, parse(tokenize("{} 2")))

    def test_parse_multiple_empty_blocks(self):
        expect = ast.BlockExpression([ast.BlockExpression([]) for _ in range(3)])
        with self.subTest(msg="Without semicolons"):
            self.assertEqual(expect, parse(tokenize("{}{}{}")))

        with self.subTest(msg="With semicolons between"):
            self.assertEqual(expect, parse(tokenize("{};{};{}")))

        with self.subTest(msg="With trailing semicolon"):
            expect.body.append(ast.Literal(None))
            self.assertEqual(expect, parse(tokenize("{};{};{};")))

    def test_parse_block_cases_i_aped_from_course_material(self):
        test_cases = (
            "{ { a } { b } }",
            "{ if true then { a } b }",
            "{ if true then { a }; b }",
            "{ if true then { a } b; c }",
            "{ if true then { a } else { b } 3 }",
            "{ while {true} do 3}",
        )

        for code in test_cases:
            with self.subTest(msg="Should be allowed", input=code):
                self.assertIsInstance(parse(tokenize(code)), ast.BlockExpression)

        with self.subTest(msg="Braces directly after 'while' should be allowed"):
            self.assertIsInstance(parse(tokenize("while {true} do 3")), ast.WhileExpression)

        with self.subTest(msg="Block inside identifier should be allowed"):
            self.assertIsInstance(parse(tokenize("x = { { f(a) } { b } }")), ast.BinaryOp)

    def test_ast_expression_locations(self):
        self.location_patcher.stop()
        command = """
        //Starts at column 9
        var x = 3; x = -2; //line 3
        if x then f({2+3})
        """
        block = parse(tokenize(command))
        declaration, binary, conditional = block.body
        literal = declaration.expression
        identifier = declaration.identifier
        unary = binary.right
        function = conditional.then_clause
        block = function.args[0]

        test_cases = [
            ("block ", block.location, (4, 21)),
            ("declaration ", declaration.location, (3, 9)),
            ("binary ", binary.location, (3, 22)),
            ("conditional ", conditional.location, (4, 9)),
            ("literal ", literal.location, (3, 17)),
            ("identifier ", identifier.location, (3, 13)),
            ("unary ", unary.location, (3, 24)),
            ("function ", function.location, (4, 19))
        ]

        for case, location, expect in test_cases:
            with self.subTest(expression=case):
                self.assertEqual(location, Location("no file", *expect))

    def test_parse_empty_func_definition(self):
        code = "fun f() {}"

        body = ast.BlockExpression([])
        func = ast.FuncDef("f", [], body)
        expect = ast.Module([func])

        self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_empty_func_with_params(self):
        code = "fun f(a: Int) {}"

        body = ast.BlockExpression([])
        params = [ast.FuncParam("a", ast.TypeExpression("Int"))]
        func = ast.FuncDef("f", params, body)
        expect = ast.Module([func])

        with self.subTest(msg="One param"):
            self.assertEqual(expect, parse(tokenize(code)))

        code = "fun f(a: Int, b: Int, c: Bool) {}"
        params.append(ast.FuncParam("b", ast.TypeExpression("Int")))
        params.append(ast.FuncParam("c", ast.TypeExpression("Bool")))

        with self.subTest(msg="multiple params"):
            self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_function_def_with_body(self):
        code = "fun f(a: Int) {1+a;}"

        body = ast.BlockExpression([ast.BinaryOp(ast.Literal(1), "+", ast.Identifier("a")), ast.Literal(None)])
        params = [ast.FuncParam("a", ast.TypeExpression("Int"))]
        func = ast.FuncDef("f", params, body)
        expect = ast.Module([func])

        self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_modules_with_functions_and_body(self):
        code = """
        fun f(a: Int, b: Int) {a+b}
        fun k(a: Int, b: Int) {a+b}
        1 + f(1, 2);
        """
        a = ast.Identifier("a")
        b = ast.Identifier("b")
        params = [ast.FuncParam("a", ast.TypeExpression("Int")), ast.FuncParam("b", ast.TypeExpression("Int"))]
        body = ast.BlockExpression([ast.BinaryOp(a, "+", b)])
        func_f = ast.FuncDef("f", params, body)
        func_k = ast.FuncDef("k", params, body)

        call_f = ast.FuncExpression(ast.Identifier("f"), [ast.Literal(1), ast.Literal(2)])
        plus = ast.BinaryOp(ast.Literal(1), "+", call_f)
        module_expressions = ast.BlockExpression([plus, ast.Literal(None)])
        expect = ast.Module([func_f, func_k, module_expressions])

        self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_empty_return_value(self):
        code = "return;"

        expect = ast.BlockExpression([ast.ReturnExpression(None), ast.Literal(None)])

        self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_return_with_value(self):
        neq = ast.BinaryOp(ast.Literal(4), "!=", ast.Literal(3))
        expect = ast.ReturnExpression(neq)

        self.assertEqual(expect, parse(tokenize("return 4 != 3")))

    def test_parse_simple_function_with_return_value(self):
        code = "fun f(x: Int) {return x + 2;}"

        param = ast.FuncParam("x", ast.TypeExpression("Int"))
        plus = ast.BinaryOp(ast.Identifier("x"), "+", ast.Literal(2))
        ret = ast.ReturnExpression(plus)
        body = ast.BlockExpression([ret, ast.Literal(None)])
        func_f = ast.FuncDef("f", [param], body)
        expect = ast.Module([func_f])

        self.assertEqual(expect, parse(tokenize(code)))

    def test_parse_raise_error_if_entire_input_is_not_parsed(self):
        tokens = tokenize("4 + 3 5")

        msg = "could not parse the whole expression"
        self.assertRaisesRegex(SyntaxError, msg, parse, tokens)

    def test_parse_empty_input_returns_an_empty_ast_expression(self):
        self.assertEqual(ast.Expression(), parse([]))

    def test_parse_invalid_input(self):
        self.location_patcher.stop()
        test_cases = [
            ("Unexpected operator", "+ 2", SyntaxError, "integer literal or an identifier"),
            ("Incorrect parenthesis", ") 1 + 2(", SyntaxError, "integer literal or an identifier"),
            ("Unmatched parenthesis", "( 3 + 2 / 4", SyntaxError, r'line=1, column=11.* expected: "\)"'),
            ("Doubled Operator", " 3 ++ 4", SyntaxError, "line=1, column=5.* integer literal or an identifier"),
            ("Missing Expression for <", "<2>", SyntaxError, "line=1, column=1.* integer literal or an identifier"),
            ("Unary operator inside parenthesis", "2-(-)3", SyntaxError, "column=5.* integer literal or an identifier"),
            ("Chain and without literals", "2 and and 3", SyntaxError, "column=7.* integer literal or an identifier"),
            ("3 equals operators", " 3 === 4", SyntaxError, "line=1, column=6.* integer literal or an identifier"),
            ("If without then", "if true x + 1", SyntaxError, r'line=1, column=9.* expected: "then"'),
            ("While without do", "while true x + 1", SyntaxError, r'line=1, column=12.* expected: "do"'),
            ("Else without if", "1 + 2 else 3", SyntaxError, "could not parse the whole expression"),
            ("Single else", "else", SyntaxError, "integer literal or an identifier"),
            ("No function identifier", "1 + (a, 3)", SyntaxError, r'line=1, column=7.* expected: "\)"'),
            ("Literal is not a valid func name", "2 (a, 3)", SyntaxError, "could not parse the whole expression"),
            ("if is not a valid func name", "if (a, 3)", SyntaxError, r'line=1, column=6.* expected: "\)"'),
            ("While is not a valid func name", "while (a, 3)", SyntaxError, r'line=1, column=9.* expected: "\)"'),
            ("Function missing punctuation", "func(a 3)", SyntaxError, r'line=1, column=8.* expected: "\)"'),
            ("Semicolon alone is invalid", ";", SyntaxError, "integer literal or an identifier"),
            ("Semicolon alone is invalid", "{;}", SyntaxError, "integer literal or an identifier"),
            ("Missing semicolon after a.", "{ a b }", SyntaxError, "column=5"),
            ("Missing semicolon after b.", "{ if true then { a } b c }", SyntaxError, "column=24"),
            ("Missing semicolon after 2.", "2{}{}", SyntaxError, "column=2.* expected ';'"),
            ("Missing semicolon after 2.", "{2{}}{}", SyntaxError, "column=3.* expected ';'"),
            ("Missing semicolon", "{var x = 3} var y = 4 var z = 5;", SyntaxError, "column=23.* could not parse"),
            ("var is only allowed in blocks", "if 3 then var x = 3", SyntaxError, "column=11.* var is only"),
            ("var has to be followed by an identifier", "var 3 = 3", SyntaxError, "column=5.* expected an identifier"),
            ("var needs an initializer", "var x 3", SyntaxError, 'column=7.* expected: "="'),
            ("Using typed var without colon", "var Int x = 1", SyntaxError, 'column=9.* expected: "="'),
            ("Misplaced colon in typed var", "var: x = 1", SyntaxError, 'column=4.* expected an identifier'),
        ]

        for case, code, exception, error_msg in test_cases:
            with self.subTest(msg=case, input=code):
                tokens = tokenize(code)
                self.assertRaisesRegex(exception, error_msg, parse, tokens)

    def test_parse_function_definition_invalid_input(self):
        self.location_patcher.stop()
        test_cases = [
            ("Missing identifier", "fun (a: Int)", SyntaxError, 'line=1.*mn=5.* expected an identifier'),
            ("No opening bracket", "fun f a: Int) {}", SyntaxError, r'line=1.*mn=7.* expected: "\("'),
            ("Missing semicolon from param", "fun f (a Int) {}", SyntaxError, r'line=1.*mn=10.* expected: ":"'),
            ("Missing semicolon from return type", "fun f() Int {}", SyntaxError, r'line=1.*mn=9.* expected: "{"'),
            ("Missing type expression", "fun f (a:) {}", SyntaxError, r'line=1.*mn=10.* type hint'),
            ("Missing type expression from return type", "fun f(): {}", SyntaxError, r'line=1.*mn=10.* type hint'),
            ("Missing colon between params", "fun f (a: Int b: Int) {}", SyntaxError, r'line=1.*mn=15.* expected: ","'),
            ("Ends with a semicolon", "fun f() {};a", SyntaxError, r'line=1.*mn=11.* literal or an identifier'),
            ('Empty return needs a ";"', "fun f() {return}", SyntaxError, r'line=1.*mn=16.* literal or an identifier'),
        ]

        for case, code, exception, error_msg in test_cases:
            with self.subTest(msg=case, input=code):
                tokens = tokenize(code)
                self.assertRaisesRegex(exception, error_msg, parse, tokens)
