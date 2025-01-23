from dataclasses import dataclass, field

from compiler.tokenizer import Location


@dataclass
class Expression:
    """Base class for AST nodes representing expressions."""


@dataclass
class Literal(Expression):
    value: int | bool | None
    # Needs default value, so I don't have to rewrite all the tests
    location: Location = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class Identifier(Expression):
    name: str
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class Declaration(Expression):
    identifier: Identifier
    expression: Expression
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class BinaryOp(Expression):
    """AST node for a binary operation like `A + B`"""
    left: Expression
    op: str
    right: Expression
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class UnaryOp(Expression):
    """AST node for a unary operation like `not true`"""
    op: str
    left: Expression
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class IfExpression(Expression):
    if_condition: Expression
    then_clause: Expression
    else_clause: Expression | None
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class FuncExpression(Expression):
    name: Expression
    args: list[Expression]
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))


@dataclass
class BlockExpression(Expression):
    body: list[Expression]
    location: Location | None = field(default_factory=lambda: Location("no file", 1, 1))
