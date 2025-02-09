from dataclasses import dataclass, field

from compiler.c_types import Type, Unit
from compiler.tokenizer import Location


@dataclass
class Expression:
    """Base class for AST nodes representing expressions."""
    # Needs default value, so I don't have to rewrite all the tests
    location: Location = field(kw_only=True, default=Location("no file", 1, 1))
    type: Type = field(kw_only=True, default=Unit)


@dataclass
class Literal(Expression):
    value: int | bool | None


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class TypeExpression(Expression):
    name: str


@dataclass
class Declaration(Expression):
    identifier: Identifier
    expression: Expression
    type_expression: TypeExpression | None = None


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
    expression: Expression


@dataclass
class IfExpression(Expression):
    if_condition: Expression
    then_clause: Expression
    else_clause: Expression | None


@dataclass
class WhileExpression(Expression):
    condition: Expression
    body: Expression


@dataclass
class BreakExpression(Expression):
    name: str = "break"


@dataclass
class ContinueExpression(Expression):
    name: str = "continue"


@dataclass
class FuncExpression(Expression):
    identifier: Identifier
    args: list[Expression]


@dataclass
class BlockExpression(Expression):
    body: list[Expression]

@dataclass
class ReturnExpression(Expression):
    result: Expression | None = None

@dataclass
class FuncParam:
    name: str
    type_expression: TypeExpression
    location: Location = field(kw_only=True, default=Location("no file", 1, 1))

@dataclass
class FuncDef:
    name: str
    params: list[FuncParam]
    body: BlockExpression
    type_expression: TypeExpression | None = None
    type: Type = Unit
    location: Location = field(kw_only=True, default=Location("no file", 1, 1))

@dataclass
class Module:
    body: list[FuncDef | Expression]
    location: Location = field(kw_only=True, default=Location("no file", 1, 1))
