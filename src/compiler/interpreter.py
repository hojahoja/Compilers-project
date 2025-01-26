from dataclasses import dataclass, field
from typing import Self, Callable

import compiler.bast as ast

type Value = int | bool | Callable[..., Value] | None


@dataclass
class SymTab:
    locals: dict[str, Value] = field(default_factory=dict)
    parent: Self | None = None


def interpret(node: ast.Expression | None, table: SymTab | None = None) -> Value:
    if table is None:
        table = SymTab({
            "print_int": lambda val: print(val) if type(val) == int else type(val),
            "print_bool": lambda val: print(val) if type(val) == bool else type(val),
            "read_int": lambda: int(input()),
            "+": lambda val_a, val_b: val_a + val_b,
            "-": lambda val_a, val_b: val_a - val_b,
            "*": lambda val_a, val_b: val_a * val_b,
            "/": lambda val_a, val_b: val_a // val_b,
            "%": lambda val_a, val_b: val_a % val_b,
            "==": lambda val_a, val_b: val_a == val_b,
            "!=": lambda val_a, val_b: val_a != val_b,
            "<": lambda val_a, val_b: val_a < val_b,
            "<=": lambda val_a, val_b: val_a <= val_b,
            ">": lambda val_a, val_b: val_a > val_b,
            ">=": lambda val_a, val_b: val_a >= val_b,
            "unary_-": lambda val_a: -val_a,
            "unary_not": lambda val_a: not val_a,
            "and": lambda val_a, val_b: val_a and val_b,
            "or": lambda val_a, val_b: val_a or val_b,
        })

    def get_value(symbol: str, symbol_table: SymTab | None = table) -> Value:
        if symbol_table is None:
            return None
        if symbol not in symbol_table.locals:
            return get_value(symbol, symbol_table.parent)

        return symbol_table.locals[symbol]

    def set_value(ident: ast.Identifier, val: Value, symbol_table: SymTab | None = table) -> None:
        symbol = ident.name
        current_table = symbol_table
        while current_table:
            if symbol in current_table.locals:
                current_table.locals[symbol] = val
                return
            current_table = current_table.parent
        raise NameError(f"{ident.location}: Variable '{symbol}' is not defined")

    match node:
        case ast.Literal():
            return node.value

        case ast.Identifier():
            return get_value(node.name, table)

        case ast.UnaryOp():
            value: Value = interpret(node.expression, table)
            operator: Value = get_value(f"unary_{node.op}")
            if callable(operator):
                return operator(value)
            else:
                raise Exception(f"{node.location} expected an operator")

        case ast.BinaryOp():
            get_a: Callable[..., Value] = lambda: interpret(node.left, table)
            get_b: Callable[..., Value] = lambda: interpret(node.right, table)

            if node.op == "=":
                if isinstance(node.left, ast.Identifier):
                    set_value(node.left, get_b(), table)
                else:
                    raise SyntaxError(f"{node.location} left side of assignment must be a variable name")
            elif node.op == "or":
                return get_a() or get_b()
            elif node.op == "and":
                return get_a() and get_b()
            else:
                operator = get_value(node.op)
                if callable(operator):
                    return operator(get_a(), get_b())
                raise Exception(f"{node.location} expected an operator")

        case ast.IfExpression():
            if interpret(node.if_condition, table):
                return interpret(node.then_clause, table)
            else:
                return interpret(node.else_clause, table)

        case ast.WhileExpression():
            value = None
            while interpret(node.condition, table):
                value = interpret(node.body, table)

            return value

        case ast.BlockExpression():
            value = None
            block_table: SymTab = SymTab(parent=table)
            for expression in node.body:
                value = interpret(expression, block_table)

            return value

        case ast.Declaration():
            value = interpret(node.expression, table)
            table.locals[node.identifier.name] = value
            return None

        case ast.FuncExpression():
            name: str = node.name.name
            args: list[Value] = [interpret(arg, table) for arg in node.args]

            operator = get_value(name)
            if name in ["print_int", "print_bool"] and callable(operator):
                if len(args) == 1:
                    incorrect_type = operator(*args)
                    if incorrect_type:
                        incorrect: str = incorrect_type.__name__  # type: ignore
                        expected: str = name.removeprefix("print_")
                        raise TypeError(f"{node.location}: expected {expected} argument got, {incorrect} argument")
                else:
                    raise TypeError(f"{node.location}: {name} takes 1 argument but {len(args)} were given")

            elif name == "read_int" and callable(operator):
                if len(args) == 0:
                    return operator()
                else:
                    raise TypeError(f"{node.location}: {name} takes 0 arguments but {len(args)} were given")

    return None

# if __name__ == "__main__":
#     # Manually tested on terminal that this works with input
#     interpret(parse(tokenize("var x = read_int(); print_int(x)")))
