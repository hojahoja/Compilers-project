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
    # IRVar("and"): Unit,
    # IRVar("or"): Unit,
}


def generate_ir(root_types: dict[IRVar, Type], root_expr: ast.Expression) -> list[ir.Instruction]:
    var_types: dict[IRVar, Type] = root_types.copy()

    var_unit = IRVar("unit")
    var_types[var_unit] = Unit

    def ir_var_generator(prefix: str, cls: typing.Type[IRVar]) -> Generator[IRVar, None, None]:
        i: int = 1
        while True:
            variable: IRVar = cls(name=f"{prefix}{i}")
            i += 1
            yield variable

    def label_generator(prefix: str, cls: typing.Type[ir.Label]) -> Generator[ir.Label, None, None]:
        i: int = 1
        while True:
            variable: ir.Label = cls(Location("no file", 0, 0), name=f"{prefix}{i}")
            i += 1
            yield variable

    ir_vars: Generator[IRVar, None, None] = ir_var_generator("x", IRVar)
    ir_labels: Generator[ir.Label, None, None] = label_generator("L", ir.Label)

    def new_var(t: Type) -> IRVar:
        variable: IRVar = next(ir_vars)
        var_types[variable] = t

        return variable

    def new_label() -> ir.Label:
        return next(ir_labels)

    ins: list[ir.Instruction] = []

    def visit(st: SymTab[IRVar], expr: ast.Expression) -> IRVar:
        loc: Location = expr.location

        match expr:
            case ast.Literal():

                match expr.value:
                    case bool():
                        var: IRVar = new_var(Bool)
                        ins.append(ir.LoadBoolConst(loc, expr.value, var))
                    case int():
                        var = new_var(Bool)
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
                var_op: IRVar = st.require(expr.op)
                var_left: IRVar = visit(st, expr.left)
                var_right: IRVar = visit(st, expr.right)
                var_result = new_var(expr.type)

                ins.append(ir.Call(loc, var_op, [var_left, var_right], var_result))

                return var_result

            case ast.IfExpression():
                if expr.else_clause is None:
                    l_then: ir.Label = new_label()
                    l_end: ir.Label = new_label()

                    var_cond: IRVar = visit(st, expr.if_condition)

                    ins.append(ir.CondJump(loc, var_cond, l_then, l_end))
                    ins.append(l_then)

                    visit(st, expr.then_clause)

                    ins.append(l_end)

                    return var_unit
                else:
                    # TODO
                    return var_unit

            # TODO other cases
            # case ast.:

            case _:
                raise Exception(f"{loc}: unexpected error")

    root_symtable: SymTab[IRVar] = SymTab({v.name: v for v in root_types.keys()})

    var_final_result = visit(root_symtable, root_expr)
    if var_types[var_final_result] == Int:
        no_loc = Location("no file", 0, 0)
        ins.append(ir.Call(no_loc, root_symtable.require("print_int"), [var_final_result], new_var(Int)))
    if var_types[var_final_result] == Bool:
        no_loc = Location("no file", 0, 0)
        ins.append(ir.Call(no_loc, root_symtable.require("print_bool"), [var_final_result], new_var(Bool)))

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
