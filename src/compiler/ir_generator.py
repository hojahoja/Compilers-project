import sys
import typing
from typing import Generator

import compiler.bast as ast
import compiler.ir as ir
from compiler.c_types import Type, Unit, Bool, Int
from compiler.ir import IRVar
from compiler.parser import parse
from compiler.symtab import SymTab
from compiler.tokenizer import Location, tokenize
from compiler.type_checker import typecheck

ROOT_TYPES: dict[IRVar, Type] = {
    IRVar("print_int"): Unit,
    IRVar("print_bool"): Unit,
    IRVar("read_int"): Int,
    IRVar("+"): Int,
    IRVar("-"): Int,
    IRVar("*"): Int,
    IRVar("/"): Int,
    IRVar("%"): Int,
    IRVar("<"): Bool,
    IRVar("<="): Bool,
    IRVar(">"): Bool,
    IRVar(">="): Bool,
    IRVar("=="): Bool,
    IRVar("!="): Bool,
    IRVar("unary_-"): Int,
    IRVar("unary_not"): Bool,
}


def generate_ir(root_types: dict[IRVar, Type], root_expr: ast.Expression) -> list[ir.Instruction]:
    var_types: dict[IRVar, Type] = root_types.copy()

    var_unit = IRVar("unit")
    var_types[var_unit] = Unit

    root_loc: Location = root_expr.location

    loop_depth: int = 0

    def ir_var_generator(prefix: str, cls: typing.Type[IRVar]) -> Generator[IRVar, None, None]:
        i: int = 1
        while True:
            variable: IRVar = cls(name=f"{prefix}{i}")
            i += 1
            yield variable

    ir_vars: Generator[IRVar, None, None] = ir_var_generator("x", IRVar)

    ir_labels_adjust: dict[str, int] = {}

    def new_var(t: Type) -> IRVar:
        variable: IRVar = next(ir_vars)
        var_types[variable] = t

        return variable

    def new_label(name: str) -> ir.Label:
        if name in ir_labels_adjust:
            ir_labels_adjust[name] += 1
            name = f"{name}{ir_labels_adjust[name]}"
        else:
            ir_labels_adjust[name] = 1

        return ir.Label(root_loc, name)

    ins: list[ir.Instruction] = []

    def visit(st: SymTab[IRVar], expr: ast.Expression) -> IRVar:
        loc: Location = expr.location
        nonlocal loop_depth

        match expr:
            case ast.Literal():

                match expr.value:
                    case bool():
                        var: IRVar = new_var(Bool)
                        ins.append(ir.LoadBoolConst(loc, expr.value, var))
                    case int():
                        var = new_var(Int)
                        ins.append(ir.LoadIntConst(loc, expr.value, var))
                    case None:
                        var = var_unit
                    case _:
                        raise Exception(f"{loc}: unsupported literal: {type(expr.value)}")

                return var

            case ast.Identifier():
                var = st.require(expr.name)
                if var:
                    return var
                raise NameError(f'{loc}: Variable "{expr.name}" is not defined"')

            case ast.BinaryOp():
                var_left: IRVar = visit(st, expr.left)

                if expr.op == "=":
                    var_right: IRVar = visit(st, expr.right)
                    ins.append(ir.Copy(loc, var_right, var_left))
                    return var_left

                elif expr.op in ["and", "or"]:
                    # Create labels and check left side value
                    prefix: str = 'and' if expr.op == 'and' else 'or'

                    l_right: ir.Label = new_label(f"{prefix}_right")
                    l_skip: ir.Label = new_label(f"{prefix}_skip")
                    l_end: ir.Label = new_label(f"{prefix}_end")
                    if prefix == "and":
                        ins.append(ir.CondJump(loc, var_left, l_right, l_skip))
                    else:
                        ins.append(ir.CondJump(loc, var_left, l_skip, l_right))

                    # Check right side value and copy result
                    ins.append(l_right)
                    var_right = visit(st, expr.right)
                    var_result: IRVar = new_var(Bool)
                    ins.append(ir.Copy(loc, var_right, var_result))
                    ins.append(ir.Jump(loc, l_end))

                    # Directly return result depending on right side value
                    ins.append(l_skip)
                    short_circuit_result: bool = False if expr.op == "and" else True
                    ins.append(ir.LoadBoolConst(loc, short_circuit_result, var_result))
                    ins.append(ir.Jump(loc, l_end))

                    ins.append(l_end)
                    return var_result

                else:
                    var_op: IRVar = st.require(expr.op)
                    var_right = visit(st, expr.right)
                    var_result = new_var(expr.type)
                    ins.append(ir.Call(loc, var_op, [var_left, var_right], var_result))
                    return var_result

            case ast.UnaryOp():
                unary_op: IRVar = st.require(f"unary_{expr.op}")
                unary_var: IRVar = visit(st, expr.expression)
                unary_result: IRVar = new_var(expr.type)

                ins.append(ir.Call(loc, unary_op, [unary_var], unary_result))

                return unary_result

            case ast.WhileExpression():
                l_while_start: ir.Label = new_label("while_start")
                l_while_body: ir.Label = new_label("while_body")
                l_while_end: ir.Label = new_label("while_end")

                # While condition
                ins.append(l_while_start)
                while_cond: IRVar = visit(st, expr.condition)
                ins.append(ir.CondJump(loc, while_cond, l_while_body, l_while_end))

                # While Body
                ins.append(l_while_body)
                loop_depth += 1

                visit(st, expr.body)
                ins.append(ir.Jump(loc, l_while_start))

                ins.append(l_while_end)
                loop_depth -= 1

            case ast.BreakExpression() | ast.ContinueExpression():
                if loop_depth > 0:
                    start_end: str = "while_start" if expr.name == "continue" else "while_end"
                    label_name: str = start_end if loop_depth == 1 else f"{start_end}{loop_depth}"
                    l_break_continue: ir.Label = ir.Label(loc, label_name)
                    ins.append(ir.Jump(loc, l_break_continue))
                else:
                    raise SyntaxError(f"{loc} {expr.name} outside of loop")

            case ast.IfExpression():
                # Creating then label and first LoadBoolConst is shared by both branches
                l_then: ir.Label = new_label("then")
                var_cond: IRVar = visit(st, expr.if_condition)

                if expr.else_clause is None:
                    # Then
                    l_if_end: ir.Label = new_label("if_end")
                    ins.append(ir.CondJump(loc, var_cond, l_then, l_if_end))
                    ins.append(l_then)
                    visit(st, expr.then_clause)

                    # If End
                    ins.append(l_if_end)
                else:
                    l_else = new_label("else")
                    l_if_end = new_label("if_end")

                    # If
                    ins.append(ir.CondJump(loc, var_cond, l_then, l_else))
                    if expr.type == Bool:
                        copy_var: IRVar = new_var(Bool)
                    elif expr.type == Int:
                        copy_var = new_var(Int)
                    else:
                        copy_var = new_var(Unit)

                    # Then
                    ins.append(l_then)
                    then_var: IRVar = visit(st, expr.then_clause)
                    ins.append(ir.Copy(loc, then_var, copy_var))
                    ins.append(ir.Jump(loc, l_if_end))

                    # Else
                    ins.append(l_else)
                    else_var: IRVar = visit(st, expr.else_clause)
                    ins.append(ir.Copy(loc, else_var, copy_var))

                    # If End
                    ins.append(l_if_end)
                    return copy_var

            case ast.BlockExpression():
                block_var: IRVar = var_unit
                block_table: SymTab[IRVar] = SymTab(parent=st)
                for expression in expr.body:
                    block_var = visit(block_table, expression)

                return block_var

            case ast.Declaration():
                dec_value: IRVar = visit(st, expr.expression)
                dec_variable: IRVar = new_var(expr.expression.type)

                ins.append(ir.Copy(loc, dec_value, dec_variable))
                st.add_local(expr.identifier.name, dec_variable)

            case ast.FuncExpression():
                func_vars: list[IRVar] = [visit(st, a) for a in expr.args]
                func: IRVar = st.require(expr.identifier.name)

                if expr.identifier.name == "read_int":
                    result_var: IRVar = new_var(Int)
                    ins.append(ir.Call(loc, func, func_vars, result_var))
                    return result_var
                else:
                    ins.append(ir.Call(loc, func, func_vars, new_var(expr.identifier.type)))
                    return var_unit

            case _:
                raise Exception(f"{loc}: unexpected error")

        return var_unit

    root_symtable: SymTab[IRVar] = SymTab({v.name: v for v in root_types.keys()})

    ins.append(new_label("start"))
    var_final_result: IRVar = visit(root_symtable, root_expr)
    if var_types[var_final_result] == Int:
        ins.append(ir.Call(root_loc, root_symtable.require("print_int"), [var_final_result], new_var(Int)))
    if var_types[var_final_result] == Bool:
        ins.append(ir.Call(root_loc, root_symtable.require("print_bool"), [var_final_result], new_var(Bool)))

    return ins


def stringify_ir(expressions: list[ir.Instruction]) -> str:
    return "\n".join([str(expr) for expr in expressions])


def code_to_ir(code: str) -> list[ir.Instruction]:
    ast_expr: ast.Expression = parse(tokenize(code))
    typecheck(ast_expr)
    return generate_ir(ROOT_TYPES, ast_expr)


if __name__ == "__main__":
    readable_ir = stringify_ir(code_to_ir(sys.argv[1]))
    print(readable_ir)
