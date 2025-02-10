from unittest import TestCase

from compiler.c_types import Int, Bool, Unit
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck
from compiler.utilities import parse_code_and_typecheck


# mypy: ignore-errors

def check(code: str):
    return parse_code_and_typecheck(code)


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

    def test_typecheck_break_continue_expressions(self):
        for name in ("break", "continue"):
            with self.subTest(msg=name):
                self.assertEqual(Unit, check(name))

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

    def test_typecheck_variable_declarations(self):
        test_cases = [
            ("Integer declaration", "var x = 3", Unit),
            ("Boolean declaration", "var x = false", Unit),
            ("Integer declaration", "var x: Int = 2", Unit),
            ("Boolean declaration", "var x: Bool = true", Unit),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_typecheck_declared_variables(self):
        test_cases = [
            ("Integer declaration", "var x = 3", Unit),
            ("Boolean declaration", "var x = false", Unit),
            ("Boolean variable", "var k = true; k", Bool),
            ("Integer variable", "var x = 3; x", Int),
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

    def test_typecheck__chained_assignment(self):
        code = """
        var a = 3;
        var b = 4;
        var c = 5;
        a = b = c;
        a
        """
        self.assertEqual(Int, check(code))

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

    def test_typecheck_multiple_parameter_function_calls(self):

        code = "fun triple_param(x: Int, y: Int, z: Bool) {} triple_param(3, 21, false)"
        with self.subTest(msg="Correct parameter types", input=code):
            self.assertEqual(Unit, check(code))

        code = "fun triple_param(x: Int, y: Int, z: Bool) {} triple_param(3, 21, 0)"
        with self.subTest(msg="Incorrect parameter types", input=code):
            message = "mn=46.* parameter 3.*Bool.*Int"
            self.assertRaisesRegex(TypeError, message, check, code)

    def test_typecheck_test_function_definition_only(self):
        code = "fun f(x :Int): Int {}"
        self.assertEqual(Unit, check(code))

    def test_typecheck_test_function_definition_with_body(self):
        self.assertEqual(Unit, check("fun f() {var x = 1; x + 1}"))

    def test_typecheck_call_defined_function(self):
        code = """
        fun f(x: Int) {var y = 1; x + y}
        f(2)
        """
        self.assertEqual(Unit, check(code))

    def test_typecheck_recursive_function_calls(self):
        code = """
        fun f() {f()}
        fun g() {k()}
        fun k() {g()}
        """

        self.assertEqual(Unit, check(code))

    def test_typecheck_complex_case(self):

        code = """
        fun f(read: Bool): Int {
            var x = 0;
            if read then {
                var x: Int = read_int();
            } else {
                return 9001
            }
            return x            
        }
        fun k () {
            var x: Int = 1;
            var y: Bool = true;
            while x != 9001 do {
                
                if x < 0 then y = false;
                x = f(true)
            }
        }
        
        k()
        """
        self.assertEqual(Unit, check(code))

    def test_typecheck_function_return_values(self):
        test_cases = [
            ("Boolean", "fun f(): Bool {return true} f()", Bool),
            ("Integer", "fun f(): Int {return 42;} f()", Int),
            ("No return value", "fun f(){} f()", Unit),
            ("Empty return value", "fun f(x: Int) {return;} f(2)", Unit),
            ("Boolean parameter", "fun f(x: Int, y: Bool): Int {return x;} f(2, true)", Int),
            ("Integer parameter", "fun f(x: Int, y: Bool): Bool {return y} f(2, false)", Bool),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertEqual(expect, check(code))

    def test_ast_type_unassigned(self):
        self.assertEqual(Unit, parse(tokenize("var x: Bool = true; x")).type)

    def test_ast_type_assignment(self):
        test_cases = [
            ("Boolean", "true", Bool),
            ("Integer", "2", Int),
            ("Binary calc", "2+2", Int),
            ("Binary comp", "2!=2", Bool),
            ("Declaration", "var x = 3", Unit),
            ("Typed declaration", "var x: Bool = false", Unit),
            ("Assignment", "var x: Bool = false; x = true", Bool),
            ("declared variable", "var x: Bool = true; x", Bool),
            ("Changed variable", "var x = 1; x = 2; x", Int),
            ("Unary -", "-2", Int),
            ("Unary not", "not false", Bool),
            ("While", "while true do 2", Int),
            ("Block", "{true}", Bool),
            ("While-Block", "while {true} do {10}", Int),
            ("if then", "if 3>3 then 5", Int),
            ("if then else", "if 3>3 then 5 else 0", Int),
            ("print_int", "print_int(2)", Unit),
            ("read_int", "read_int()", Int),
        ]

        for case, code, expect in test_cases:
            with self.subTest(msg=case, input=code):
                expression = parse(tokenize(code))
                typecheck(expression)

                self.assertEqual(expect, expression.type)

    def test_typecheck_function_definition_errors(self):
        test_cases = [
            ("Two same functions", "fun f(){} fun f(){}", NameError, r'mn=11.* Function "f" already declared'),
            ("Return outside function", "fun f(){} return 2", SyntaxError, r'mn=11.* "return" outside function'),
            ("Assign incorrect type to param", "fun f(x: Bool) {x = 2}", TypeError, r'mn=19.*Bool.*Int'),
            ("Return incorrect type", "fun f(): Int {return false}", TypeError, r'mn=15.*Int.*Bool'),
        ]

        for case, code, error, message in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertRaisesRegex(error, message, check, code)

    def test_typecheck_errors(self):
        shenanigans2 = "var x = 3; var k: x = 2"

        test_cases = [
            ("Left side binary operator", "true + 1", TypeError, r'mn=6.* "\+".*left.*Int.*Bool'),
            ("Right side binary operator", "1 < false", TypeError, r'mn=3.* "<".*right.*Int.*Bool'),
            ("Or operator accepts only bool", "1 or 2", TypeError, r'mn=3.* "or".*left.*Bool.*Int'),
            ("Unary - boolean", "- true", TypeError, r'mn=1.* "-".*Int.*Bool'),
            ("Unary not integer", "not 20", TypeError, r'mn=1.* "not".*Bool.*Int'),
            ("If condition not bool", "if 3 then 4", TypeError, r'mn=1.* expected.*Bool.*Int'),
            ("Then and else clause different type", "if true then 4 else false", TypeError, r'mn=1.*Int.*Bool'),
            ("Variable doesn't exist: Assignment", "x = 2", NameError, r'mn=1.* "x" is not defined'),
            ("Variable doesn't exist: Operator", "4 >= y", NameError, r'mn=6.* "y" is not defined'),
            ("Variable doesn't exist: Scope", "{var x = 1}x", NameError, r'mn=12.* "x" is not defined'),
            ("Variable already exists in scope", "var x = 3; var x = 2", NameError, r'mn=12.* "x" already declared'),
            ('Mismatching type for "="', "var x = true; x = 2", TypeError, r'mn=17.* "=".*Bool.*not.*Int'),
            ('Mismatching type for "=="', "2 == false", TypeError, r'mn=3.* "==".*Int.*not.*Bool'),
            ('Mismatching type for "!="', "true != 0", TypeError, r'mn=6.* "!=".*Bool.*not.*Int'),
            ("While-loop condition not bool", "while 1 do 3", TypeError, r'mn=1.* while-loop.*Bool.*Int'),
            ("print_int param not int", "print_int(false)", TypeError, r'mn=1.* parameter 1.*Int.*Bool'),
            ("print_bool param not bool", "print_bool(22)", TypeError, r'mn=1.* parameter 1.*Bool.*Int'),
            ("Trying to declare with wrong type", "var x: Int = false", TypeError, r'mn=1.*Int.*Bool'),
            ("Trying to assign variable as Unit type", "var x: Unit = 2", TypeError, r'mn=1.*Unit.*Int'),
            ("Trying to change builtin type", "var Bool = 2; var x: Bool = 2", TypeError, r'mn=15.*Bool.*Int'),
            ("Trying to use declared variable as type", shenanigans2, TypeError, r'mn=19.* Unknown type "x"'),
            ("Declaration with nonexistent type", "var x: Mint = 2", TypeError, r'mn=8.* Unknown type "Mint"'),
        ]

        for case, code, error, message in test_cases:
            with self.subTest(msg=case, input=code):
                self.assertRaisesRegex(error, message, check, code)
