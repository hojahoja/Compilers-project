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


def trim(code: str, remove_bp: bool = True) -> str:
    if remove_bp:
        code = re.sub(r".*(?<=\.Lmain_start:)", '', code, flags=re.DOTALL)
    lines = code.splitlines()

    empty_or_comment_line: str = r"(^\s*$)|(^\s*#)"
    code = "\n".join((line.strip() for line in lines if not re.match(empty_or_comment_line, line)))
    return code.rstrip("\n")


class TestAssemblyGenerator(TestCase):

    def test_assemble_basic_case(self):
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
            
                movq $1, -8(%rbp)
            
                movq -8(%rbp), %rax
                movq %rax, -16(%rbp)
            
                cmpq $0, -16(%rbp)
                jne .Lmain_then
                jmp .Lmain_else
            
            .Lmain_then:
            
                movq $1, -24(%rbp)
            
                movq -24(%rbp), %rax
                movq %rax, -32(%rbp)
            
                jmp .Lmain_if_end
            
            .Lmain_else:
            
                movq $2, -40(%rbp)
            
                movq -40(%rbp), %rax
                movq %rax, -32(%rbp)
            
            .Lmain_if_end:
            
                movq $0, %rax
                movq %rbp, %rsp
                popq %rbp
                ret
        """

        code = "{ var x = true; if x then 1 else 2; }"
        self.assertEqual(trim(expect, False), trim(assemble(code), False))

    def test_assemble_arithmetic(self):
        expect = """
        # LoadIntConst(1, x)
        movq $1, -8(%rbp)
    
        # LoadIntConst(2, x2)
        movq $2, -16(%rbp)
    
        # Call(+, [x, x2], x3)
        movq -8(%rbp), %rax
        addq -16(%rbp), %rax
        movq %rax, -24(%rbp)
    
        # LoadIntConst(3, x4)
        movq $3, -32(%rbp)
    
        # LoadIntConst(4, x5)
        movq $4, -40(%rbp)
    
        # Call(*, [x4, x5], x6)
        movq -32(%rbp), %rax
        imulq -40(%rbp), %rax
        movq %rax, -48(%rbp)
    
        # LoadIntConst(2, x7)
        movq $2, -56(%rbp)
    
        # Call(/, [x6, x7], x8)
        movq -48(%rbp), %rax
        cqto
        idivq -56(%rbp)
        movq %rax, -64(%rbp)
    
        # Call(-, [x3, x8], x9)
        movq -24(%rbp), %rax
        subq -64(%rbp), %rax
        movq %rax, -72(%rbp)
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret 
        """

        self.assertEqual(trim(expect), trim(assemble("1 + 2 - 3 * 4 / 2;")))

    def test_assemble_comparison(self):
        expect =  """
        # LoadBoolConst(True, x)
        movq $1, -8(%rbp)
    
        # LoadIntConst(3, x2)
        movq $3, -16(%rbp)
    
        # LoadIntConst(2, x3)
        movq $2, -24(%rbp)
    
        # Call(<, [x2, x3], x4)
        xor %rax, %rax
        movq -16(%rbp), %rdx
        cmpq -24(%rbp), %rdx
        setl %al
        movq %rax, -32(%rbp)
    
        # Call(!=, [x, x4], x5)
        xor %rax, %rax
        movq -8(%rbp), %rdx
        cmpq -32(%rbp), %rdx
        setne %al
        movq %rax, -40(%rbp)
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
        """

        self.assertEqual(trim(expect), trim(assemble("true != 3 < 2;")))

    def test_assemble_unary_ops(self):
        expect = """
        # LoadIntConst(3, x)
        movq $3, -8(%rbp)
    
        # Call(unary_-, [x], x2)
        movq -8(%rbp), %rax
        negq %rax
        movq %rax, -16(%rbp)
    
        # LoadBoolConst(False, x3)
        movq $0, -24(%rbp)
    
        # Call(unary_not, [x3], x4)
        movq -24(%rbp), %rax
        xorq $1, %rax
        movq %rax, -32(%rbp)
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
        """

        self.assertEqual(trim(expect), trim(assemble("-3; not false;")))

    def test_assemble_built_in_functions(self):
        expect = """
        subq $8, %rsp
        callq read_int
        movq %rax, -8(%rbp)
        addq $8, %rsp
    
        # Copy(x, x2)
        movq -8(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # Call(print_int, [x2], x3)
        subq $8, %rsp
        movq -16(%rbp), %rdi
        callq print_int
        movq %rax, -24(%rbp)
        addq $8, %rsp
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
        """

        self.assertEqual(trim(expect), trim(assemble("var x: Int = read_int(); x")))
