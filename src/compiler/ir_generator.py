import typing
from typing import Generator

import compiler.bast as ast
import compiler.ir as ir
from compiler.c_types import Type, Unit, Bool, Int
from compiler.ir import IRVar
from compiler.symtab import SymTab
from compiler.tokenizer import Location

type IrTypes = dict[IRVar, Type]
type IrList = list[ir.Instruction]
type IrDict = dict[str, IrList]


def generate_ir(root_types: IrTypes, root_node: ast.Expression | ast.Module) -> IrDict:
    instructions: dict[str, list[ir.Instruction]] = {}

    def add_instructions(func: ir.FunctionDef, ir_list: IrList, types: IrTypes, body: ast.Expression,
                         is_function: bool) -> None:
        instruction_list.append(func)
        generate_ir_body(types, body, ir_list, is_function)
        instructions[func_ir.name] = ir_list

    if isinstance(root_node, ast.Module):
        for node in root_node.body:
            instruction_list: list[ir.Instruction] = []
            if isinstance(node, ast.FuncDef):

                function_types = root_types.copy()
                param_list: list[IRVar] = []

                for param in node.params:
                    param_var = IRVar(param.name)
                    param_list.append(param_var)
                    function_types[param_var] = param.type_expression.type

                func_ir: ir.FunctionDef = ir.FunctionDef(node.location, node.name, param_list)
                add_instructions(func_ir, instruction_list, function_types, node.body, is_function=True)
            else:
                func_ir = ir.FunctionDef(node.location, "main", [])
                add_instructions(func_ir, instruction_list, root_types, node, is_function=False)
    else:
        instruction_list = []
        func_ir = ir.FunctionDef(root_node.location, "main", [])
        add_instructions(func_ir, instruction_list, root_types, root_node, is_function=False)

    return instructions


def generate_ir_body(root_types: IrTypes, root_expr: ast.Expression, ins: list[ir.Instruction],
                     is_function: bool = True) -> list[
    ir.Instruction]:
    var_types: IrTypes = root_types.copy()

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

    new_var_count: int = 0

    def new_var(t: Type) -> IRVar:
        nonlocal new_var_count
        variable: IRVar = next(ir_vars)
        new_var_count += 1
        while variable in var_types:
            variable = next(ir_vars)
            new_var_count += 1
        var_types[variable] = t

        return variable

    def new_label(name: str) -> ir.Label:
        if name in ir_labels_adjust:
            ir_labels_adjust[name] += 1
            name = f"{name}{ir_labels_adjust[name]}"
        else:
            ir_labels_adjust[name] = 1

        return ir.Label(root_loc, name)

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
                    if then_var.name == "unit":
                        then_var = IRVar("Unit")
                    ins.append(ir.Copy(loc, then_var, copy_var))
                    ins.append(ir.Jump(loc, l_if_end))

                    # Else
                    ins.append(l_else)
                    else_var: IRVar = visit(st, expr.else_clause)
                    if else_var.name == "unit":
                        else_var = IRVar("Unit")
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

            case ast.ReturnExpression():
                if expr.result:
                    result: IRVar = visit(st, expr.result)
                    ins.append(ir.Return(loc, result))
                else:
                    ins.append(ir.Return(loc, var_unit))

            case ast.FuncExpression():
                func_vars: list[IRVar] = [visit(st, a) for a in expr.args]
                func: IRVar = st.require(expr.identifier.name)

                result_var: IRVar = new_var(var_types[func])
                ins.append(ir.Call(loc, func, func_vars, result_var))
                return result_var

            case _:
                raise Exception(f"{loc}: unexpected error")

        return var_unit

    root_symtable: SymTab[IRVar] = SymTab({v.name: v for v in root_types.keys()})

    ins.append(new_label("start"))
    var_final_result: IRVar = visit(root_symtable, root_expr)
    if is_function:
        if not isinstance(ins[-1], ir.Return):
            ins.append(ir.Return(root_expr.location, var_unit))
    else:
        if var_types[var_final_result] == Int:
            ins.append(ir.Call(root_loc, root_symtable.require("print_int"), [var_final_result], new_var(Int)))
        elif var_types[var_final_result] == Bool:
            ins.append(ir.Call(root_loc, root_symtable.require("print_bool"), [var_final_result], new_var(Bool)))
        ins.append(ir.Return(root_expr.location, var_unit))

    return ins
