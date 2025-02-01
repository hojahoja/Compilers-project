import dataclasses

import compiler.ir as ir


class Locals:
    _var_to_location: dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: list[ir.IRVar]) -> None:
        self._var_to_location = {var: f"-{i * 8}(%rbp)" for i, var in enumerate(variables, start=1)}
        self._stack_used = len(variables)

    def get_ref(self, v: ir.IRVar) -> str:
        return self._var_to_location[v]

    def stack_used(self) -> int:
        return self._stack_used


def get_all_ir_variables(instructions: list[ir.Instruction]) -> list[ir.IRVar]:
    result_list: list[ir.IRVar] = []
    result_set: set[ir.IRVar] = set()

    def add(val: ir.IRVar) -> None:
        if val not in result_set:
            result_list.append(val)
            result_set.add(val)

    for ins in instructions:
        for field in dataclasses.fields(ins):
            value: ir.IRVar = getattr(ins, field.name)
            if isinstance(value, ir.IRVar):
                add(value)
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, ir.IRVar):
                        add(v)

    return result_list


def generate_assembly(instructions: list[ir.Instruction]) -> str:
    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)

    local_vars: Locals = Locals(variables=get_all_ir_variables(instructions))

    emit("    .extern print_int")
    emit("    .extern print_bool")
    emit("    .extern read_int")

    emit("    .section .text")

    emit("    # main()")
    emit("    .global main")
    emit("    .type main, @function")

    emit("")
    emit("    main:")
    emit("    pushq %rbp")
    emit("    movq %rsp, %rbp")
    emit(f"    subq ${local_vars.stack_used() * 8 or 8}, %rsp")

    for ins in instructions:
        emit("")
        emit("    # " + str(ins))
        match ins:
            case ir.Label():
                emit(f"    .L{ins.name}:")

            case ir.LoadIntConst():
                if -2 ** 31 <= ins.value < 2 ** 31:
                    emit(f"    movq ${ins.value}, {local_vars.get_ref(ins.dest)}")
                else:
                    emit(f"    movabsq ${ins.value}, %rax")
                    emit(f"    movq %rax, {local_vars.get_ref(ins.dest)}")

            case ir.LoadBoolConst():
                emit(f"    movq ${int(ins.value)}, {local_vars.get_ref(ins.dest)}")

            case ir.Jump():
                emit(f"    jmp .L{ins.label.name}")

            case ir.Copy():
                emit(f"    movq {local_vars.get_ref(ins.source)}, %rax")
                emit(f"    movq %rax, {local_vars.get_ref(ins.dest)}")

            case ir.CondJump():
                emit(f"    cmpq $0, {local_vars.get_ref(ins.cond)}")
                emit(f"    jne .L{ins.then_label.name}")
                emit(f"    jmp .L{ins.else_label.name}")

    # set 0 as return value and restore stack
    emit("")
    emit("    movq $0, %rax")
    emit("    movq %rbp, %rsp")
    emit("    popq %rbp")
    emit("    ret")


    return "\n".join(lines)
