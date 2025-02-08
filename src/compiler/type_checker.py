import compiler.bast as ast
from compiler.c_types import Int, Bool, Unit, Type, FunType
from compiler.symtab import SymTab


def typecheck(root_node: ast.Expression | ast.Module) -> Type:
    known_types: dict[str, Type] = {"Bool": Bool, "Int": Int, "Unit": Unit}

    root_table: SymTab[Type] = SymTab({
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

    def assign_type(node: ast.Expression | None, table: SymTab[Type]) -> Type:
        ast_type: Type = get_type(node, table)
        if node:
            node.type = ast_type
        return ast_type

    def get_type(node: ast.Expression | None, table: SymTab[Type]) -> Type:
        match node:
            case ast.Literal():
                for ptype, ctype in ((int, Int), (bool, Bool), (None, Unit)):
                    if type(node.value) == ptype:
                        return ctype

            case ast.Identifier():
                try:
                    typ: Type = table.require(node.name)
                    return typ
                except NameError:
                    raise NameError(f'{node.location}: Variable "{node.name}" is not defined"')

            case ast.BinaryOp():
                t1: Type = assign_type(node.left, table)
                t2: Type = assign_type(node.right, table)
                if node.op in ["=", "==", "!="]:
                    if t1 is not t2:
                        raise TypeError(f'{node.location}: Operator "{node.op}" {t1} is not {t2}')
                    return t2 if node.op == "=" else Bool

                binary_type: Type | None = table.get_value(node.op)
                if isinstance(binary_type, FunType):
                    b1, b2 = binary_type.params
                    if t1 is not b1:
                        raise TypeError(f'{node.location}: Operator "{node.op}" left side expected {b1}, got {t1}')
                    if t2 is not b2:
                        raise TypeError(f'{node.location}: Operator "{node.op}" right side expected {b2}, got {t2}')

                    return binary_type.return_type

            case ast.UnaryOp():
                t1 = assign_type(node.expression, table)
                unary_type: Type | None = table.get_value(f"unary_{node.op}")
                if isinstance(unary_type, FunType):
                    if t1 is not unary_type.params[0]:
                        raise TypeError(
                            f'{node.location}: Operator "{node.op}" expected {unary_type.params[0]}, got {t1}')
                    return unary_type.return_type

            case ast.WhileExpression():
                t1 = assign_type(node.condition, table)
                if t1 == Bool:
                    return assign_type(node.body, table)
                raise TypeError(f'{node.location}: while-loop condition should be a Boolean, got {t1}')

            case ast.IfExpression():
                t1 = assign_type(node.if_condition, table)
                if t1 is not Bool:
                    raise TypeError(f'{node.location}:  expected {Bool}, got {t1}')
                t2 = assign_type(node.then_clause, table)
                t3: Type = assign_type(node.else_clause, table)
                if t3 is Unit:
                    return t2
                elif t2 != t3:
                    raise TypeError(f'{node.location}:  expected {t2}, got {t3}')
                return t3

            case ast.BlockExpression():
                typ = Unit
                block_table: SymTab[Type] = SymTab(parent=table)
                for expression in node.body:
                    typ = assign_type(expression, block_table)

                return typ

            case ast.Declaration():
                t1 = assign_type(node.expression, table)
                if node.type_expression:

                    t2 = convert(node.type_expression)

                    if t1 != t2:
                        raise TypeError(f"{node.location}: expected {t2}, got {t1}")

                name = node.identifier.name
                if table.in_locals(name):
                    raise TypeError(f'{node.location}: Variable "{name}" already declared in scope:')
                table.add_local(name, t1)

            case ast.FuncExpression():
                name = node.identifier.name
                func_type: Type | None = table.get_value(name)
                if not func_type:
                    raise NameError(f'{node.identifier.location}: Variable not found: "{name}"')

                elif isinstance(func_type, FunType):
                    arg_types: list[Type] = [assign_type(arg, table) for arg in node.args]
                    for i, types in enumerate(zip(func_type.params, arg_types)):
                        expect, got = types
                        if expect != got:
                            raise TypeError(f'{node.location}: Function parameter {i + 1} expected {expect}, got {got}')
                    return func_type.return_type

        return Unit

    def convert(expr: ast.TypeExpression | None) -> Type:
        if not expr:
            return Unit
        elif expr.name in known_types:
            return known_types[expr.name]
        else:
            raise TypeError(f'{expr.location}: Unknown type "{expr.name}"')

    if isinstance(root_node, ast.Module):
        for function in root_node.body:
            if isinstance(function, ast.FuncDef):
                param_types: tuple[Type, ...] = tuple(convert(param.type_expression) for param in function.params)
                return_type: Type = convert(function.type_expression)
                fun_type: FunType = FunType("function", param_types, return_type)
                root_table.add_local(function.name, fun_type)

        if isinstance(root_node.body[-1], ast.Expression):
            root_expression = root_node.body[-1]
        else:
            root_expression = None
    else:
        root_expression = root_node

    return assign_type(root_expression, root_table)
