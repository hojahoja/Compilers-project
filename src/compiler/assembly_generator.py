import dataclasses

import compiler.ir as ir
from compiler.intrinsics import all_intrinsics as intrinsics, Intrinsic, IntrinsicArgs


class Locals:
    _var_to_location: dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: list[ir.IRVar]) -> None:
        self._var_to_location = {var: f"-{i * 8}(%rbp)" for i, var in enumerate(variables, start=1)}
        self._stack_used = len(variables)

    def in_locals(self, v: ir.IRVar) -> bool:
        return v in self._var_to_location

    def get_ref(self, v: ir.IRVar) -> str:
        return self._var_to_location[v]

    def stack_used(self) -> int:
        return self._stack_used


def get_all_ir_variables(instructions: list[ir.Instruction], reserved: set[ir.IRVar]) -> list[ir.IRVar]:
    result_list: list[ir.IRVar] = []
    result_set: set[ir.IRVar] = {
        ir.IRVar("print_int"),
        ir.IRVar("print_bool"),
        ir.IRVar("read_int"),
        ir.IRVar("+"),
        ir.IRVar("-"),
        ir.IRVar("*"),
        ir.IRVar("/"),
        ir.IRVar("%"),
        ir.IRVar("<"),
        ir.IRVar("<="),
        ir.IRVar(">"),
        ir.IRVar(">="),
        ir.IRVar("=="),
        ir.IRVar("!="),
        ir.IRVar("unary_-"),
        ir.IRVar("unary_not"),
    }

    def add(val: ir.IRVar) -> None:
        if val not in result_set and val.name != "unit":
            result_list.append(val)
            result_set.add(val)

    result_set.update(reserved)

    for ins in instructions[1:]:
        for field in dataclasses.fields(ins):
            value: ir.IRVar = getattr(ins, field.name)
            if isinstance(value, ir.IRVar):
                add(value)
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, ir.IRVar):
                        add(v)

    return result_list


def generate_assembly(instructions_dict: dict[str, list[ir.Instruction]]) -> str:
    reserved_vars: set[ir.IRVar] = set()
    assembly_code: list[str] = []
    top_section: str = """
    .extern print_int
    .extern print_bool
    .extern read_int
    .section .text
    """
    assembly_code.append(top_section)
    for func, ins_list in instructions_dict.items():
        reserved_vars.add(ir.IRVar(func))
        assembly_code.append(generate_assembly_function(ins_list, func, reserved_vars))
    return "\n".join(assembly_code)


def generate_assembly_function(instructions: list[ir.Instruction], func: str, reserved_vars: set[ir.IRVar]) -> str:
    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)

    local_vars: Locals = Locals(variables=get_all_ir_variables(instructions, reserved_vars))

    call_registers: tuple[str, ...] = ("%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9")

    emit(f"    # {func}()")
    emit(f"    .global {func}")
    emit(f"    .type {func}, @function")

    emit("")
    emit(f"    {func}:")
    emit("    pushq %rbp")
    emit("    movq %rsp, %rbp")

    vars_used: int = 0
    if isinstance(instructions[0], ir.FunctionDef):
        for arg, reg in zip(instructions[0].args, call_registers):
            if local_vars.in_locals(arg):
                vars_used += 1
                emit(f"    movq {reg}, {local_vars.get_ref(arg)}")

    emit(f"    subq ${local_vars.stack_used() * 8 or 8}, %rsp")

    for ins in instructions:
        emit("")
        emit("    # " + str(ins))
        match ins:
            case ir.Label():
                emit(f"    .L{func}_{ins.name}:")

            case ir.LoadIntConst():
                if -2 ** 31 <= ins.value < 2 ** 31:
                    emit(f"    movq ${ins.value}, {local_vars.get_ref(ins.dest)}")
                else:
                    emit(f"    movabsq ${ins.value}, %rax")
                    emit(f"    movq %rax, {local_vars.get_ref(ins.dest)}")

            case ir.LoadBoolConst():
                emit(f"    movq ${int(ins.value)}, {local_vars.get_ref(ins.dest)}")

            case ir.Jump():
                emit(f"    jmp .L{func}_{ins.label.name}")

            case ir.Copy():
                emit(f"    movq {local_vars.get_ref(ins.source)}, %rax")
                emit(f"    movq %rax, {local_vars.get_ref(ins.dest)}")

            case ir.CondJump():
                emit(f"    cmpq $0, {local_vars.get_ref(ins.cond)}")
                emit(f"    jne .L{func}_{ins.then_label.name}")
                emit(f"    jmp .L{func}_{ins.else_label.name}")

            case ir.Call():
                args: list[str] = [local_vars.get_ref(var) for var in ins.args]
                if ins.fun.name in intrinsics:
                    call: Intrinsic = intrinsics[ins.fun.name]
                    intrinsic_args: IntrinsicArgs = IntrinsicArgs(args, "%rax", emit)
                    call(intrinsic_args)
                    emit(f"movq %rax, {local_vars.get_ref(ins.dest)}")
                else:
                    stack_not_aligned: bool = local_vars.stack_used() * 8 % 16 != 0
                    if stack_not_aligned:
                        emit(f"subq $8, %rsp")  # This changes when function defs are supported or does it?
                    for var, reg in zip(args, call_registers):
                        emit(f"movq {var}, {reg}")

                    emit(f"callq {ins.fun.name}")
                    emit(f"movq %rax, {local_vars.get_ref(ins.dest)}")
                    if stack_not_aligned:
                        emit(f"addq $8, %rsp")

            case ir.Return():
                return_value = f"{local_vars.get_ref(ins.result)}" if local_vars.in_locals(ins.result) else "$0"
                emit(f"    movq {return_value}, %rax")
                emit("    movq %rbp, %rsp")
                emit("    popq %rbp")
                emit("    ret")

    return "\n".join(lines)
