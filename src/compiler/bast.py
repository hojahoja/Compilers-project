from dataclasses import dataclass


@dataclass
class Expression:
    """Base class for AST nodes representing expressions."""


@dataclass
class Literal(Expression):
    value: int | bool


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class BinaryOp(Expression):
    """AST node for a binary operation like `A + B`"""
    left: Expression
    op: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    """AST node for a unary operation like `not true`"""
    op: str
    left: Expression


@dataclass
class IfExpression(Expression):
    if_condition: Expression
    then_clause: Expression
    else_clause: Expression | None


@dataclass
class FuncExpression(Expression):
    name: Expression
    args: list[Expression]
