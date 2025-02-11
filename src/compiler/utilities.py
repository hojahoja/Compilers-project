import compiler.bast as ast
import compiler.ir as ir
from compiler.assembly_generator import generate_assembly
from compiler.c_types import Type, FunType
from compiler.ir import IRVar
from compiler.ir_generator import generate_ir
from compiler.parser import parse
from compiler.symtab import SymTab
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck


def extract_root_types(st: SymTab[Type]) -> dict[IRVar, Type]:
    """ Turn type checker's SymTab to root_types used, by ir and assembly generators."""
    return {
        IRVar(name): func.return_type
        for name, func in st.locals.items()
        if isinstance(func, FunType)
    }


def parse_code(code: str, filename: str = "") -> ast.Expression | ast.Module:
    """ Parse a code string into an AST tree"""
    if filename:
        return parse(tokenize(code, filename))
    else:
        return parse(tokenize(code))


def parse_code_and_typecheck(code: str, filename: str = "") -> Type:
    return typecheck(parse_code(code, filename))[0]


def typecheck_expression_and_get_root_types(expr: ast.Expression | ast.Module) -> dict[IRVar, Type]:
    return extract_root_types(typecheck(expr)[1])


def code_to_ir(code: str, filename: str = "") -> dict[str, list[ir.Instruction]]:
    ast_expr: ast.Expression | ast.Module = parse_code(code, filename)
    root_types: dict[IRVar, Type] = extract_root_types(typecheck(ast_expr)[1])
    return generate_ir(root_types, ast_expr)


def stringify_ir(ir_dict: dict[str, list[ir.Instruction]]) -> str:
    return "\n".join(str(inst) for ir_list in ir_dict.values() for inst in ir_list)


def code_to_ir_string(code: str, filename: str = "") -> str:
    return stringify_ir(code_to_ir(code, filename))


def source_code_to_assembly(code: str, filename: str = "") -> str:
    return generate_assembly(code_to_ir(code, filename))
