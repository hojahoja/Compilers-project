import compiler.bast as ast
from compiler.c_types import Int, Bool, Unit, Type, FunType
from compiler.symtab import SymTab


def typecheck(node: ast.Expression | None, table: SymTab[Type] | None = None) -> Type:
    ast_type: Type = get_type(node, table)
    if node:
        node.type = ast_type
    return ast_type


def get_type(node: ast.Expression | None, table: SymTab[Type] | None = None) -> Type:
    if table is None:
        table = SymTab({
            "print_int": FunType("function", (Int,), Unit),
            "print_bool": FunType("function", (Bool,), Unit),
            "read_int": FunType("function", (Int,), Int),
            "+": FunType("operator", (Int, Int), Int),
            "-": FunType("operator", (Int, Int), Int),
            "*": FunType("operator", (Int, Int), Int),
            "/": FunType("operator", (Int, Int), Int),
            "%": FunType("operator", (Int, Int), Int),
            "<": FunType("operator", (Int, Int), Bool),
            "<=": FunType("operator", (Int, Int), Bool),
            ">": FunType("operator", (Int, Int), Bool),
            ">=": FunType("operator", (Int, Int), Bool),
            "unary_-": FunType("operator", (Int,), Int),
            "unary_not": FunType("operator", (Bool,), Bool),
            "and": FunType("operator", (Bool, Bool), Bool),
            "or": FunType("operator", (Bool, Bool), Bool),
        })

    match node:
        case ast.Literal():
            for ptype, ctype in ((int, Int), (bool, Bool), (None, Unit)):
                if type(node.value) == ptype:
                    return ctype

        case ast.Identifier():
            typ: Type | None = table.get_value(node.name)
            if not typ:
                raise NameError(f'{node.location}: Variable "{node.name}" is not defined"')
            return typ

        case ast.BinaryOp():
            t1: Type = typecheck(node.left, table)
            t2: Type = typecheck(node.right, table)
            if node.op in ["=", "==", "!="]:
                if t1 is not t2:
                    raise TypeError(f'{node.location}: Operator "{node.op}" {t1} is not {t2}')
                return Unit if node.op == "=" else Bool

            binary_type: Type | None = table.get_value(node.op)
            if isinstance(binary_type, FunType):
                b1, b2 = binary_type.params
                if t1 is not b1:
                    raise TypeError(f'{node.location}: Operator "{node.op}" left side expected {b1}, got {t1}')
                if t2 is not b2:
                    raise TypeError(f'{node.location}: Operator "{node.op}" right side expected {b2}, got {t2}')

                return binary_type.return_type

        case ast.UnaryOp():
            t1 = typecheck(node.expression, table)
            unary_type: Type | None = table.get_value(f"unary_{node.op}")
            if isinstance(unary_type, FunType):
                if t1 is not unary_type.params[0]:
                    raise TypeError(f'{node.location}: Operator "{node.op}" expected {unary_type.params[0]}, got {t1}')
                return unary_type.return_type

        case ast.WhileExpression():
            t1 = typecheck(node.condition, table)
            if t1 == Bool:
                return typecheck(node.body, table)
            raise TypeError(f'{node.location}: while-loop condition should be a Boolean, got {t1}')

        case ast.IfExpression():
            t1 = typecheck(node.if_condition, table)
            if t1 is not Bool:
                raise TypeError(f'{node.location}:  expected {Bool}, got {t1}')
            t2 = typecheck(node.then_clause, table)
            t3: Type = typecheck(node.else_clause, table)
            if t3 is Unit:
                return t2
            elif t2 != t3:
                raise TypeError(f'{node.location}:  expected {t2}, got {t3}')
            return t3

        case ast.BlockExpression():
            typ = Unit
            block_table: SymTab[Type] = SymTab(parent=table)
            for expression in node.body:
                typ = typecheck(expression, block_table)

            return typ

        case ast.Declaration():
            t1 = typecheck(node.expression, table)
            if node.type_expression:

                name: str = node.type_expression.name
                known_types: dict[str, Type] = {"Bool": Bool, "Int": Int, "Unit": Unit}
                if name not in known_types:
                    raise TypeError(f'{node.type_expression.location} Unknown type "{name}"')
                t2 = known_types[name]

                if t1 != t2:
                    raise TypeError(f"{node.location}: expected {t2}, got {t1}")

            name = node.identifier.name
            if table.in_locals(name):
                raise TypeError(f'{node.location}: Variable "{name}" already declared in scope:')
            table.add_local(name, t1)

        case ast.FuncExpression():
            name = node.name.name
            func_type: Type | None = table.get_value(name)
            if not func_type:
                raise NameError(f'{node.name.location}: Variable not found: "{name}"')

            elif isinstance(func_type, FunType):
                arg_types: list[Type] = [typecheck(arg, table) for arg in node.args]
                for i, types in enumerate(zip(func_type.params, arg_types)):
                    expect, got = types
                    if expect != got:
                        raise TypeError(f'{node.location}: Function parameter {i + 1} expected {expect}, got {got}')
                return func_type.return_type

    return Unit
