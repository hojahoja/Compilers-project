from typing import Callable

import compiler.bast as ast
from compiler.symtab import SymTab

type Value = int | bool | Callable[..., Value] | None


def interpret(node: ast.Expression | None, table: SymTab[Value] | None = None) -> Value:
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

    def set_value(ident: ast.Identifier, val: Value) -> None:
        symbol = ident.name
        if not table.assign_value(symbol, val):
            raise NameError(f"{ident.location}: Variable '{symbol}' is not defined")

    match node:
        case ast.Literal():
            return node.value

        case ast.Identifier():
            return table.get_value(node.name)

        case ast.UnaryOp():
            value: Value = interpret(node.expression, table)
            operator: Value = table.get_value(f"unary_{node.op}")
            if callable(operator):
                return operator(value)
            else:
                raise Exception(f"{node.location} expected an operator")

        case ast.BinaryOp():
            get_a: Callable[..., Value] = lambda: interpret(node.left, table)
            get_b: Callable[..., Value] = lambda: interpret(node.right, table)

            if node.op == "=":
                if isinstance(node.left, ast.Identifier):
                    set_value(node.left, get_b())
                else:
                    raise SyntaxError(f"{node.location} left side of assignment must be a variable name")
            elif node.op == "or":
                return get_a() or get_b()
            elif node.op == "and":
                return get_a() and get_b()
            else:
                operator = table.get_value(node.op)
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
            block_table: SymTab[Value] = SymTab(parent=table)
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

            operator = table.get_value(name)
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
