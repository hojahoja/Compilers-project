from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from compiler.tokenizer import tokenize, Token, Location


# mypy: ignore-errors
class TestTokenizer(TestCase):

    def setUp(self):
        self.location_patcher = patch('compiler.tokenizer.Location')
        self.location_patcher.start()

    def tearDown(self):
        self.location_patcher.stop()

    def test_tokenizer_integers(self):
        expect = [
            Token("int_literal", "123"),
            Token("int_literal", "196123"),
            Token("int_literal", "0"),
            Token("int_literal", "2")
        ]
        self.assertEqual(expect, tokenize("123     196123 \n0 2"))

    def test_tokenizer_booleans(self):
        expect = [Token("bool_literal", "true"), Token("bool_literal", "false")]
        self.assertEqual(expect, tokenize("true     false"))

    def test_tokenizer_identifiers(self):
        expect = [
            Token("identifier", "variableName"),
            Token("identifier", "name_of_variable"),
            Token("identifier", "trues"),
            Token("identifier", "when"),
            Token("identifier", "Int"),
            Token("identifier", "Bool"),
            Token("identifier", "Unit"),
        ]
        code = "variableName \n\n\n name_of_variable trues  when Int Bool Unit"

        self.assertEqual(expect, tokenize(code))

    def test_tokenizer_conditionals(self):
        expect = [
            Token("conditional", "if"),
            Token("conditional", "then"),
            Token("conditional", "else"),
        ]

        code = "if then else"
        self.assertEqual(expect, tokenize(code))

    def test_tokenizer_while_loop(self):
        expect = [
            Token("while_loop", "while"),
            Token("identifier", "does"),
            Token("while_loop", "do"),
        ]
        self.assertEqual(expect, tokenize("while does do"))

    def test_tokenizer_break_continue(self):
        expect = [
            Token("break_continue", "break"),
            Token("break_continue", "continue"),
            Token("identifier", "breaks"),
            Token("identifier", "no_continue"),
        ]

        self.assertEqual(expect, tokenize("break continue breaks no_continue"))

    def test_tokenizer_operators(self):
        operators = "+ - * / % = == != < <= > >= and or not"

        expect = []
        for op in operators.split(" "):
            expect.append(Token("operator", op))

        self.assertEqual(expect, tokenize(operators))

    def test_variable_declaration(self):
        expect = [
            Token("identifier", "variable"),
            Token("declaration", "var"),
            Token("identifier", "varchar"),
            Token("operator", "="),
            Token("int_literal", "2"),
        ]

        self.assertEqual(expect, tokenize("variable var varchar = 2"))

    def test_tokenizer_punctuation(self):
        punctuation = "{ ) ( } , ; :"

        expect = []
        for pun in punctuation.split(" "):
            expect.append(Token("punctuation", pun))

        self.assertEqual(expect, tokenize(punctuation))

    def test_tokenizer_return(self):
        expect = [
            Token("return", "return"),
            Token("identifier", "returns"),
        ]

        self.assertEqual(expect, tokenize("return returns"))

    def test_tokenizer_function(self):
        expect = [
            Token("function", "fun"),
            Token("identifier", "not_fun"),
        ]

        self.assertEqual(expect, tokenize("fun not_fun"))

    def test_tokenizer_function_definition(self):
        code = """
        fun tokenize(token: Int): Int {
            return token;
        }
        """
        expect = [
            Token("function", "fun"),
            Token("identifier", "tokenize"),
            Token("punctuation", "("),
            Token("identifier", "token"),
            Token("punctuation", ":"),
            Token("identifier", "Int"),
            Token("punctuation", ")"),
            Token("punctuation", ":"),
            Token("identifier", "Int"),
            Token("punctuation", "{"),
            Token("return", "return"),
            Token("identifier", "token"),
            Token("punctuation", ";"),
            Token("punctuation", "}"),
        ]

        self.assertEqual(expect, tokenize(code))

    def test_tokenizer_one_line_comments(self):
        command = """
            // this is a comment
            if 3 // is also a comment
            // we should only have 2 tokens
            // for each 3 { == != = while
        """

        self.assertEqual(2, len(tokenize(command)))

    def test_tokenizer_multiline_comments(self):
        command = """
            /* this comment spans
            dlafj 5€£ 135€::lkjfd.s,f s,() @@@
            if (3+3) != 6
            */ 
             
            1 + 3 = 4 /* alsdfjkasdkf jasdlfjs f */\n
            {2 /*() \n
            */
            }
        """

        # Expected tokens 1 + 3 = 4 { 2 }
        self.assertEqual(8, len(tokenize(command)))

    def test_tokenizer_combined_use(self):
        expect = [
            Token("declaration", "var"),
            Token("identifier", "x"),
            Token("operator", "="),
            Token("int_literal", "2"),
            Token("conditional", "if"),
            Token("punctuation", "("),
            Token("int_literal", "3"),
            Token("operator", "+"),
            Token("int_literal", "2"),
            Token("punctuation", ")"),
            Token("operator", "=="),
            Token("int_literal", "5"),
            Token("operator", "or"),
            Token("operator", "not"),
            Token("bool_literal", "false"),
            Token("conditional", "then"),
            Token("identifier", "x"),
            Token("operator", "="),
            Token("int_literal", "6"),
        ]

        command = """
        // commentary
        var x = 2
        if (3 + 2) == 5 or not false\n then
            x = 6
        """

        self.assertEqual(expect, tokenize(command))

    def test_tokenizer_raises_exception_from_unrecognized_symbol(self):
        with self.assertRaises(SyntaxError):
            tokenize("while @  if True")

        msg = "Unrecognized character: @"
        self.assertRaisesRegex(SyntaxError, msg, tokenize, "while @  if True")

    def test_column_location(self):
        self.location_patcher.stop()
        tokens = tokenize("    3 +  4")
        columns = [t.location.column for t in tokens]
        self.assertEqual([5, 7, 10], columns)

    def test_line_location(self):
        self.location_patcher.stop()
        code = """
        // commentary
        if (3 + 2) == 5
            x = 2
        """
        tokens = tokenize(code)
        lines = [t.location.line for t in tokens]

        self.assertEqual([3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4], lines)

    def test_line_and_column_location_file_name_creation_for_token(self):
        self.location_patcher.stop()
        code = "\n// commentary\nif (3 + 2) == 5\n    x = 2\n"
        tokens = tokenize(code, "code_file.code")

        loc = Location("code_file.code", line=4, column=5)
        self.assertEqual(Token("identifier", "x", loc), tokens[8])

    def test_line_and_column_location_file_name_creation_for_token_with_longer_variable_name(self):
        self.location_patcher.stop()
        code = "\n// commentary\nif (3 + 2) == 5\n    tax = 2\n"
        tokens = tokenize(code, "code_file.code")

        loc = Location("code_file.code", line=4, column=9)
        self.assertEqual(Token("operator", "=", loc), tokens[9])

    def test_multiline_comment_location(self):
        self.location_patcher.stop()
        code = "\nx = 2\n/* this is a \nmultiline\ncomment */ 2\n3 + 2 = 1\n"
        tokens = tokenize(code)

        self.assertEqual(Location("no file", 5, 12), tokens[3].location)

    def test_location_reading_from_file(self):
        self.location_patcher.stop()
        file_path = Path(__file__).parent.resolve() / "test_code"
        with open(file_path) as file:
            tokens = tokenize(file.read(), file_path.name)
            loc = Location("test_code", line=6, column=7)
            expect = Token("operator", "+", loc)
            self.assertEqual(expect, tokens[-2])
