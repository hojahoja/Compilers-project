from dataclasses import dataclass, field
from typing import Self

import compiler.bast as ast
from compiler.c_types import Int, Bool, Unit, Type, FunType


@dataclass
class SymTab:
    locals: dict[str, Type] = field(default_factory=dict)
    parent: Self | None = None


def typecheck(node: ast.Expression | None, table: SymTab | None = None) -> Type:
    if table is None:
        table = SymTab({
            "print_int": FunType("function", (Int,), Unit),
            "print_bool": FunType("function", (Int,), Unit),
            "read_int": FunType("function", (Int,), Unit),
            "+": FunType("operator", (Int, Int), Int),
            "-": FunType("operator", (Int, Int), Int),
            "*": FunType("operator", (Int, Int), Int),
            "/": FunType("operator", (Int, Int), Int),
            "%": FunType("operator", (Int, Int), Int),
            # "==": FunType("operator", (Int, Int), Int),
            # "!=": FunType("operator", (Int, Int), Int),
            "<": FunType("operator", (Int, Int), Bool),
            "<=": FunType("operator", (Int, Int), Bool),
            ">": FunType("operator", (Int, Int), Bool),
            ">=": FunType("operator", (Int, Int), Bool),
            "unary_-": FunType("operator", (Int,), Int),
            "unary_not": FunType("operator", (Bool,), Bool),
            # "and": FunType("operator", (Bool, Bool), Int),
            # "or": FunType("operator", (Bool, Bool), Int),
        })

    def get_type(symbol: str, symbol_table: SymTab | None = table) -> Type:
        if symbol_table is None:
            return Unit
        if symbol not in symbol_table.locals:
            return get_type(symbol, symbol_table.parent)

        return symbol_table.locals[symbol]

    match node:
        case ast.Literal():
            for ptype, ctype in ((int, Int), (bool, Bool), (None, Unit)):
                if type(node.value) == ptype:
                    return ctype

        case ast.BinaryOp():
            t1: Type = typecheck(node.left, table)
            t2: Type = typecheck(node.right, table)
            binary_type: Type = table.locals[node.op]
            if isinstance(binary_type, FunType):
                b1, b2 = binary_type.params
                if t1 is not b1:
                    raise TypeError(f'{node.location}: Operator "{node.op}" left side expected {b1}, got {t1}')
                if t2 is not b2:
                    raise TypeError(f'{node.location}: Operator "{node.op}" right side expected {b2}, got {t2}')
                return binary_type.return_type

        case ast.UnaryOp():
            t1 = typecheck(node.expression, table)
            unary_type = table.locals[f"unary_{node.op}"]
            if isinstance(unary_type, FunType):
                if t1 is not unary_type.params[0]:
                    raise TypeError(f'{node.location}: Operator "{node.op}" expected {unary_type.params[0]}, got {t1}')
                return unary_type.return_type

        case ast.IfExpression():
                t1 = typecheck(node.if_condition)
                if t1 is not Bool:
                    raise TypeError(f'{node.location}:  expected {Bool}, got {t1}')
                t1 = typecheck(node.then_clause)
                t2 = typecheck(node.else_clause)
                if t2 is Unit:
                    return t1
                elif t1 != t2:
                    raise TypeError(f'{node.location}:  expected {Bool}, got {t1}')
    return Unit
