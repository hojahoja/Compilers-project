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

    def test_tokenizer_basics(self):
        expect = [
            Token("identifier", "if", self.L),
            Token("int_literal", "3", self.L),
            Token("identifier", "while", self.L)
        ]
        self.assertEqual(expect, tokenize("if 3\nwhile"))

    def test_tokenizer_raises_exception_from_unrecognized_symbol(self):
        with self.assertRaises(SyntaxError):
            tokenize("while @  if True")

    def test_token_defined_with_place_holder_location(self):
        self.location_patcher.stop()
        placeholder = Location("placeholder", 0, 0)
        self.assertEqual([Token("identifier", "variableName", placeholder)], tokenize("variableName"))