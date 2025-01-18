from unittest import TestCase
from unittest.mock import patch

from compiler.tokenizer import tokenize, Token, Location


# mypy: ignore-errors
class TestTokenizer(TestCase):

    def setUp(self):
        self.location_patcher = patch('compiler.tokenizer.Location')
        self.L = self.location_patcher.start().return_value

    def tearDown(self):
        self.location_patcher.stop()

    def test_tokenizer_integers(self):
        expect = [
            Token("int_literal", "123", self.L),
            Token("int_literal", "196123", self.L),
            Token("int_literal", "0", self.L),
            Token("int_literal", "2", self.L)
        ]
        self.assertEqual(expect, tokenize("123     196123 \n0 2"))

    def test_tokenizer_identifiers(self):
        expect = [
            Token("identifier", "variableName", self.L),
            Token("identifier", "name_of_variable", self.L),
            Token("identifier", "if", self.L),
            Token("identifier", "when", self.L)
        ]
        code = "variableName \n\n\n name_of_variable   if   when"

        self.assertEqual(expect, tokenize(code))

    def test_tokenizer_operators(self):
        operators = "+ - * / = == != < <= > >="

        expect = []
        for op in operators.split(" "):
            expect.append(Token("operator", op, self.L))

        self.assertEqual(expect, tokenize(operators))

    def test_tokenizer_punctuation(self):
        punctuation = "{ ) ( } , ;"

        expect = []
        for pun in punctuation.split(" "):
            expect.append(Token("punctuation", pun, self.L))

        self.assertEqual(expect, tokenize(punctuation))

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
            Token("identifier", "if", self.L),
            Token("punctuation", "(", self.L),
            Token("int_literal", "3", self.L),
            Token("operator", "+", self.L),
            Token("int_literal", "2", self.L),
            Token("punctuation", ")", self.L),
            Token("operator", "==", self.L),
            Token("int_literal", "5", self.L),
            Token("identifier", "x", self.L),
            Token("operator", "=", self.L),
            Token("int_literal", "2", self.L),
        ]

        command = """
        // commentary
        if (3 + 2) == 5\n
            x = 2
        """

        self.assertEqual(expect, tokenize(command))

    def test_tokenizer_raises_exception_from_unrecognized_symbol(self):
        with self.assertRaises(SyntaxError):
            tokenize("while @  if True")

    def test_token_defined_with_place_holder_location_by_default(self):
        self.location_patcher.stop()
        placeholder = Location("placeholder", 0, 0)

        self.assertEqual([Token("identifier", "variableName", placeholder)], tokenize("variableName"))