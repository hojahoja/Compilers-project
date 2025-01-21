import compiler.bast as ast
from compiler.tokenizer import Token


def parse(tokens: list[Token], left_ast: bool = True) -> ast.Expression:
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

    def parse_expression() -> ast.Expression:
        left: ast.Expression = parse_term()

        while peek().text in ["+", "-"]:
            operator_token: Token = consume()
            operator: str = operator_token.text

            right: ast.Expression = parse_term()
            left = ast.BinaryOp(left, operator, right)

        return left

    def parse_expression_right() -> ast.Expression:
        left: ast.Expression = parse_term()

        if peek().text in ["+", "-"]:
            operator_token: Token = consume()
            operator: str = operator_token.text

            right: ast.Expression = parse_expression_right()
            return ast.BinaryOp(left, operator, right)

        return left

    def parse_term() -> ast.Expression:
        left: ast.Expression = parse_factor()

        while peek().text in ["*", "/"]:
            operator_token: Token = consume()
            operator: str = operator_token.text

            right: ast.Expression = parse_factor()
            left = ast.BinaryOp(left, operator, right)

        return left

    def parse_factor() -> ast.Expression:
        if peek().text == "(":
            return parse_parenthesized()
        elif peek().text == "if":
            return parse_if_expression()
        elif peek().type == "int_literal":
            return parse_int_literal()
        elif peek().type == "identifier":
            return parse_identifier()
        else:
            raise SyntaxError(f"{peek().location}: expected an integer literal or an identifier")

    def parse_if_expression() -> ast.Expression:
        consume("if")
        condition: ast.Expression = parse_expression()
        consume("then")
        then_clause: ast.Expression = parse_expression()
        if peek().text == "else":
            consume("else")
            else_clause: ast.Expression | None = parse_expression()
        else:
            else_clause = None
        return ast.IfExpression(condition, then_clause, else_clause)

    def parse_parenthesized() -> ast.Expression:
        consume("(")
        expr: ast.Expression = parse_expression()
        consume(")")
        return expr

    def parse_int_literal() -> ast.Literal:
        if peek().type != "int_literal":
            raise Exception(f"{peek().location}: expected an integer literal")
        token: Token = consume()
        return ast.Literal(int(token.text))

    def parse_identifier() -> ast.Identifier:
        if peek().type != "identifier":
            raise Exception(f"{peek().location}: expected an identifier")
        token: Token = consume()
        return ast.Identifier(token.text)

    expression: ast.Expression = parse_expression() if left_ast else parse_expression_right()
    if pos < len(tokens):
        raise SyntaxError(f"{peek().location}: could not parse the whole expression")
    return expression
