from typing import Type

import compiler.bast as ast
from compiler.tokenizer import Token, Location


def parse(tokens: list[Token]) -> ast.Expression:
    if not tokens:
        return ast.Expression()

    pos: int = 0

    def peek() -> Token:
        if pos < len(tokens):
            return tokens[pos]
        else:
            return Token(type="end", text="", location=tokens[-1].location)

    def consume(expected: str | list[str] | None = None) -> Token:
        nonlocal pos
        token: Token = peek()

        if isinstance(expected, str) and token.text != expected:
            raise SyntaxError(f'{token.location}: expected: "{expected}"')
        if isinstance(expected, list) and token.text not in expected:
            comma_separated: str = ", ".join([f"{e}" for e in expected])
            raise Exception(f"{token.location}: expected one of: '{comma_separated}'")

        pos += 1
        return token

    def parse_top_level_block() -> ast.Expression:

        expr: ast.Expression = parse_expression()

        statements: list[ast.Expression] = [expr]

        while peek().text in [";", "{"] or tokens[pos - 1].text == "}" and peek().type != "end":
            if peek().text == ";":
                consume()
            elif peek().text == "{" and isinstance(expr, (ast.Literal, ast.Identifier)):
                raise SyntaxError(f"{peek().location}: expected ';'")

            expr = ast.BlockExpression(statements, location=peek().location)
            if peek().type == "end":
                statements.append(ast.Literal(None, location=peek().location))
            else:
                statements.append(parse_expression())
        return expr

    def parse_block() -> ast.BlockExpression:
        location: Location = peek().location
        consume("{")
        statements: list[ast.Expression] = []
        while peek().text != "}":
            parse_statement(statements)
        consume("}")
        return ast.BlockExpression(statements, location=location)

    def parse_statement(statements: list[ast.Expression]) -> None:
        statements.append(parse_expression())
        if peek().text == ";":
            consume()
            if peek().text == "}" or peek().type == "end":
                statements.append(ast.Literal(None, location=peek().location))
        else:
            types: tuple[str, ...] = ("int_literal", "bool_literal", "identifier")
            expressions: tuple[Type[ast.Expression], ...] = (ast.Identifier, ast.Literal)

            if isinstance(statements[-1], expressions) and (peek().type in types or peek().text == "{"):
                raise SyntaxError(f"{peek().location}: expected ';'")

    def parse_expression() -> ast.Expression:
        left: ast.Expression = parse_binary_term()

        if peek().text == "=":
            location: Location = peek().location
            operator_token: Token = consume()
            operator: str = operator_token.text

            right: ast.Expression = parse_expression()
            return ast.BinaryOp(left, operator, right, location=location)

        return left

    def parse_binary_term(binary_operators: list[list[str]] | None = None) -> ast.Expression:
        if not binary_operators:
            binary_operators = [
                ["or"],
                ["and"],
                ["==", "!="],
                ["<", ">", "<=", ">="],
                ["+", "-"],
                ["*", "/", "%"],
            ]

        left: ast.Expression = parse_next_level_term(binary_operators)

        for operators in binary_operators:
            while peek().text in operators:
                location: Location = peek().location
                operator_token: Token = consume()
                operator: str = operator_token.text

                right: ast.Expression = parse_next_level_term(binary_operators)
                left = ast.BinaryOp(left, operator, right, location=location)

        return left

    def parse_next_level_term(binary_operators: list[list[str]]) -> ast.Expression:
        if len(binary_operators) > 1:
            return parse_binary_term(binary_operators[1:])
        return parse_unary_term()

    def parse_unary_term() -> ast.Expression:
        while peek().text in ["-", "not"]:
            location: Location = peek().location
            operator_token: Token = consume()
            operator: str = operator_token.text
            return ast.UnaryOp(operator, parse_unary_term(), location=location)

        return parse_factor()

    def parse_factor() -> ast.Expression:
        if peek().text == "(":
            expr: ast.Expression = parse_parenthesized()
        elif peek().type == "declaration":
            expr = parse_variable_declaration()
        elif peek().text == "if":
            expr = parse_if_expression()
        elif peek().text == "while":
            expr = parse_while_expression()
        elif peek().type == "break_continue":
            expr = parse_break_or_continue_expression()
        elif peek().type == "int_literal":
            expr = parse_int_literal()
        elif peek().type == "bool_literal":
            expr = parse_bool_literal()
        elif peek().type == "identifier":
            expr = parse_identifier()
        elif peek().text == "{":
            expr = parse_block()
        else:
            raise SyntaxError(f"{peek().location}: expected an integer literal or an identifier")

        if peek().text == "(" and isinstance(expr, ast.Identifier):
            location: Location = tokens[pos - 1].location
            args: list[ast.Expression] = parse_arguments()
            return ast.FuncExpression(expr, args, location=location)

        return expr

    def parse_parenthesized() -> ast.Expression:
        consume("(")
        expr: ast.Expression = parse_expression()
        consume(")")
        return expr

    def parse_variable_declaration() -> ast.Declaration:
        if var_is_allowed():
            location: Location = peek().location
            typ: ast.TypeExpression | None = None
            consume("var")
            name: ast.Identifier = parse_identifier()
            if peek().text == ":":
                consume()
                typ = parse_type_expression()
            consume("=")
            body: ast.Expression = parse_expression()
            return ast.Declaration(name, body, typ, location=location)
        raise SyntaxError(f"{peek().location}: var is only allowed inside blocks or top-level expressions")

    def var_is_allowed() -> bool:
        if pos == 0:
            return True
        if tokens[pos - 1].text in ["{", "}", ";"]:
            return True
        return False

    def parse_type_expression() -> ast.TypeExpression:
        if peek().type != "identifier":
            raise SyntaxError(f"{peek().location}: expected a type hint")
        token: Token = consume()
        return ast.TypeExpression(token.text, location=token.location)

    def parse_if_expression() -> ast.IfExpression:
        location: Location = peek().location
        consume("if")
        condition: ast.Expression = parse_expression()
        consume("then")
        then_clause: ast.Expression = parse_expression()
        if peek().text == "else":
            consume("else")
            else_clause: ast.Expression | None = parse_expression()
        else:
            else_clause = None
        return ast.IfExpression(condition, then_clause, else_clause, location=location)

    def parse_while_expression() -> ast.WhileExpression:
        location: Location = peek().location
        consume("while")
        condition: ast.Expression = parse_expression()
        consume("do")
        body: ast.Expression = parse_expression()

        return ast.WhileExpression(condition, body, location=location)

    def parse_break_or_continue_expression() -> ast.BreakExpression | ast.ContinueExpression:
        location: Location = peek().location
        if peek().text == "continue":
            consume("continue")
            return ast.ContinueExpression(location=location)
        else:
            consume("break")
            return ast.BreakExpression(location=location)

    def parse_int_literal() -> ast.Literal:
        if peek().type != "int_literal":
            raise Exception(f"{peek().location}: expected an integer literal")
        token: Token = consume()
        return ast.Literal(int(token.text), location=token.location)

    def parse_bool_literal() -> ast.Literal:
        if peek().type != "bool_literal":
            raise Exception(f"{peek().location}: expected a boolean literal")
        token: Token = consume()
        boolean = True if token.text == "true" else False
        return ast.Literal(boolean, location=token.location)

    def parse_identifier() -> ast.Identifier:
        if peek().type != "identifier":
            raise SyntaxError(f"{peek().location}: expected an identifier")
        token: Token = consume()
        return ast.Identifier(token.text, location=token.location)

    def parse_arguments() -> list[ast.Expression]:
        consume("(")
        args: list[ast.Expression] = [] if peek().text == ")" else [parse_expression()]
        while peek().text == ",":
            consume(",")
            args.append(parse_expression())
        consume(")")

        return args

    expression: ast.Expression = parse_top_level_block()
    if pos < len(tokens):
        raise SyntaxError(f"{peek().location}: could not parse the whole expression")
    return expression
