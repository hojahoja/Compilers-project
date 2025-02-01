import re
from unittest import TestCase

from compiler.assembly_generator import generate_assembly
from compiler.ir_generator import generate_ir, ROOT_TYPES
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck


# mypy: ignore-errors

def assemble(code: str) -> str:
    expression = parse(tokenize(code))
    typecheck(expression)
    return generate_assembly(generate_ir(ROOT_TYPES, expression))

def trim(code: str) -> str:
    lines = code.splitlines()
    code = "\n".join((line.strip() for line in lines if line.strip()))
    return code.rstrip("\n")


class TestAssemblyGenerator(TestCase):


    #TODO finish test
    def test_basic_case(self):
        expect = """
        .extern print_int
        .extern print_bool
        .extern read_int
         
        .section .text
         
        # main()
            .global main
            .type main, @function
            main:
            
                pushq %rbp
                movq %rsp, %rbp
                subq $40, %rsp
            
            .Lmain_start:
            
                # LoadBoolConst(True, x)
                movq $1, -8(%rbp)
            
                # Copy(x, x2)
                movq -8(%rbp), %rax
                movq %rax, -16(%rbp)
            
                # CondJump(x2, Label(then), Label(else))
                cmpq $0, -16(%rbp)
                jne .Lmain_then
                jmp .Lmain_else
            
            .Lmain_then:
            
                # LoadIntConst(1, x4)
                movq $1, -24(%rbp)
            
                # Copy(x4, x3)
                movq -24(%rbp), %rax
                movq %rax, -32(%rbp)
            
                # Jump(Label(if_end))
                jmp .Lmain_if_end
            
            .Lmain_else:
            
                # LoadIntConst(2, x5)
                movq $2, -40(%rbp)
            
                # Copy(x5, x3)
                movq -40(%rbp), %rax
                movq %rax, -32(%rbp)
            
            .Lmain_if_end:
            
                # Return(None)
                movq $0, %rax
                movq %rbp, %rsp
                popq %rbp
                ret
        """

        self.assertEqual(trim(expect), assemble("{ var x = true; if x then 1 else 2; }"))
