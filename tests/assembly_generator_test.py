import re
from unittest import TestCase

from compiler.utilities import source_code_to_assembly


# mypy: ignore-errors

def assemble(code: str) -> str:
    return source_code_to_assembly(code)


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
        expect = """
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

    def test_function_definitions_simple_case(self):
        code = """
        fun lol(a: Int, b: Int): Int {
        a = 2;
        a = a + b;
        return a;
        }

        var k: Int = 5;
        lol(1,k);

        var x = 3;
        {{3;}}
        """

        expected = """
        .extern print_int
.extern print_bool
.extern read_int
 
.section .text
 
# lol(a, b)
    .global lol
    .type lol, @function
    lol:
        # x in -8(%rbp)
        # a in -16(%rbp)
        # b in -24(%rbp)
        # x2 in -32(%rbp)
    
        pushq %rbp
        movq %rsp, %rbp
        movq %rdi, -16(%rbp)
        movq %rsi, -24(%rbp)
        subq $32, %rsp
    
    .Llol_start:
    
        # LoadIntConst(2, x)
        movq $2, -8(%rbp)
    
        # Copy(x, a)
        movq -8(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # Call(+, [a, b], x2)
        movq -16(%rbp), %rax
        addq -24(%rbp), %rax
        movq %rax, -32(%rbp)
    
        # Copy(x2, a)
        movq -32(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # Return(a)
        movq -16(%rbp), %rax
        movq %rbp, %rsp
        popq %rbp
        ret
    
 
# main()
    .global main
    .type main, @function
    main:
        # x in -8(%rbp)
        # x2 in -16(%rbp)
        # x3 in -24(%rbp)
        # x4 in -32(%rbp)
        # x5 in -40(%rbp)
        # x6 in -48(%rbp)
        # x7 in -56(%rbp)
    
        pushq %rbp
        movq %rsp, %rbp
        subq $56, %rsp
    
    .Lmain_start:
    
        # LoadIntConst(5, x)
        movq $5, -8(%rbp)
    
        # Copy(x, x2)
        movq -8(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # LoadIntConst(1, x3)
        movq $1, -24(%rbp)
    
        # Call(lol, [x3, x2], x4)
        subq $8, %rsp
        movq -24(%rbp), %rdi
        movq -16(%rbp), %rsi
        callq lol
        movq %rax, -32(%rbp)
        addq $8, %rsp
    
        # LoadIntConst(3, x5)
        movq $3, -40(%rbp)
    
        # Copy(x5, x6)
        movq -40(%rbp), %rax
        movq %rax, -48(%rbp)
    
        # LoadIntConst(3, x7)
        movq $3, -56(%rbp)
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
        """

        self.assertEqual(trim(expected, False), trim(assemble(code), False))

    def test_function_definitions_stupid_case(self):
        code = """
        fun f(read: Bool): Int {
            var x = 0;
            if read then {
                var x: Int = read_int();
            } else {
                return 9001
            }
            return x            
        }
        fun k () {
            var x: Int = 1;
            var y: Bool = true;
            while x != 9001 do {

                if x < 0 then y = false;
                x = f(true)
            }
        }

        k();
        if true then {k()} else {k()};
        if true then {k()} else {k()};
        while false do {k()};
        while false do {1 + 2};
        """

        expect = """
        .extern print_int
.extern print_bool
.extern read_int
 
.section .text
 
# f(read)
    .global f
    .type f, @function
    f:
        # x in -8(%rbp)
        # x2 in -16(%rbp)
        # read in -24(%rbp)
        # x4 in -32(%rbp)
        # x5 in -40(%rbp)
        # unit in -48(%rbp)
        # x3 in -56(%rbp)
        # x6 in -64(%rbp)
    
        pushq %rbp
        movq %rsp, %rbp
        movq %rdi, -24(%rbp)
        subq $64, %rsp
    
    .Lf_start:
    
        # LoadIntConst(0, x)
        movq $0, -8(%rbp)
    
        # Copy(x, x2)
        movq -8(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # CondJump(read, Label(then), Label(else))
        cmpq $0, -24(%rbp)
        jne .Lf_then
        jmp .Lf_else
    
    .Lf_then:
    
        # Call(read_int, [], x4)
        callq read_int
        movq %rax, -32(%rbp)
    
        # Copy(x4, x5)
        movq -32(%rbp), %rax
        movq %rax, -40(%rbp)
    
        # Copy(unit, x3)
        movq -48(%rbp), %rax
        movq %rax, -56(%rbp)
    
        # Jump(Label(if_end))
        jmp .Lf_if_end
    
    .Lf_else:
    
        # LoadIntConst(9001, x6)
        movq $9001, -64(%rbp)
    
        # Return(x6)
        movq -64(%rbp), %rax
        movq %rbp, %rsp
        popq %rbp
        ret
    
        # Copy(unit, x3)
        movq -48(%rbp), %rax
        movq %rax, -56(%rbp)
    
    .Lf_if_end:
    
        # Return(x2)
        movq -16(%rbp), %rax
        movq %rbp, %rsp
        popq %rbp
        ret
    
 
# k()
    .global k
    .type k, @function
    k:
        # x in -8(%rbp)
        # x2 in -16(%rbp)
        # x3 in -24(%rbp)
        # x4 in -32(%rbp)
        # x5 in -40(%rbp)
        # x6 in -48(%rbp)
        # x7 in -56(%rbp)
        # x8 in -64(%rbp)
        # x9 in -72(%rbp)
        # x10 in -80(%rbp)
        # x11 in -88(%rbp)
    
        pushq %rbp
        movq %rsp, %rbp
        subq $88, %rsp
    
    .Lk_start:
    
        # LoadIntConst(1, x)
        movq $1, -8(%rbp)
    
        # Copy(x, x2)
        movq -8(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # LoadBoolConst(True, x3)
        movq $1, -24(%rbp)
    
        # Copy(x3, x4)
        movq -24(%rbp), %rax
        movq %rax, -32(%rbp)
    
    .Lk_while_start:
    
        # LoadIntConst(9001, x5)
        movq $9001, -40(%rbp)
    
        # Call(!=, [x2, x5], x6)
        xor %rax, %rax
        movq -16(%rbp), %rdx
        cmpq -40(%rbp), %rdx
        setne %al
        movq %rax, -48(%rbp)
    
        # CondJump(x6, Label(while_body), Label(while_end))
        cmpq $0, -48(%rbp)
        jne .Lk_while_body
        jmp .Lk_while_end
    
    .Lk_while_body:
    
        # LoadIntConst(0, x7)
        movq $0, -56(%rbp)
    
        # Call(<, [x2, x7], x8)
        xor %rax, %rax
        movq -16(%rbp), %rdx
        cmpq -56(%rbp), %rdx
        setl %al
        movq %rax, -64(%rbp)
    
        # CondJump(x8, Label(then), Label(if_end))
        cmpq $0, -64(%rbp)
        jne .Lk_then
        jmp .Lk_if_end
    
    .Lk_then:
    
        # LoadBoolConst(False, x9)
        movq $0, -72(%rbp)
    
        # Copy(x9, x4)
        movq -72(%rbp), %rax
        movq %rax, -32(%rbp)
    
    .Lk_if_end:
    
        # LoadBoolConst(True, x10)
        movq $1, -80(%rbp)
    
        # Call(f, [x10], x11)
        subq $8, %rsp
        movq -80(%rbp), %rdi
        callq f
        movq %rax, -88(%rbp)
        addq $8, %rsp
    
        # Copy(x11, x2)
        movq -88(%rbp), %rax
        movq %rax, -16(%rbp)
    
        # Jump(Label(while_start))
        jmp .Lk_while_start
    
    .Lk_while_end:
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
    
 
# main()
    .global main
    .type main, @function
    main:
        # x in -8(%rbp)
        # x2 in -16(%rbp)
        # x4 in -24(%rbp)
        # x3 in -32(%rbp)
        # x5 in -40(%rbp)
        # x6 in -48(%rbp)
        # x8 in -56(%rbp)
        # x7 in -64(%rbp)
        # x9 in -72(%rbp)
        # x10 in -80(%rbp)
        # x11 in -88(%rbp)
        # x12 in -96(%rbp)
        # x13 in -104(%rbp)
        # x14 in -112(%rbp)
        # x15 in -120(%rbp)
    
        pushq %rbp
        movq %rsp, %rbp
        subq $120, %rsp
    
    .Lmain_start:
    
        # Call(k, [], x)
        subq $8, %rsp
        callq k
        movq %rax, -8(%rbp)
        addq $8, %rsp
    
        # LoadBoolConst(True, x2)
        movq $1, -16(%rbp)
    
        # CondJump(x2, Label(then), Label(else))
        cmpq $0, -16(%rbp)
        jne .Lmain_then
        jmp .Lmain_else
    
    .Lmain_then:
    
        # Call(k, [], x4)
        subq $8, %rsp
        callq k
        movq %rax, -24(%rbp)
        addq $8, %rsp
    
        # Copy(x4, x3)
        movq -24(%rbp), %rax
        movq %rax, -32(%rbp)
    
        # Jump(Label(if_end))
        jmp .Lmain_if_end
    
    .Lmain_else:
    
        # Call(k, [], x5)
        subq $8, %rsp
        callq k
        movq %rax, -40(%rbp)
        addq $8, %rsp
    
        # Copy(x5, x3)
        movq -40(%rbp), %rax
        movq %rax, -32(%rbp)
    
    .Lmain_if_end:
    
        # LoadBoolConst(True, x6)
        movq $1, -48(%rbp)
    
        # CondJump(x6, Label(then2), Label(else2))
        cmpq $0, -48(%rbp)
        jne .Lmain_then2
        jmp .Lmain_else2
    
    .Lmain_then2:
    
        # Call(k, [], x8)
        subq $8, %rsp
        callq k
        movq %rax, -56(%rbp)
        addq $8, %rsp
    
        # Copy(x8, x7)
        movq -56(%rbp), %rax
        movq %rax, -64(%rbp)
    
        # Jump(Label(if_end2))
        jmp .Lmain_if_end2
    
    .Lmain_else2:
    
        # Call(k, [], x9)
        subq $8, %rsp
        callq k
        movq %rax, -72(%rbp)
        addq $8, %rsp
    
        # Copy(x9, x7)
        movq -72(%rbp), %rax
        movq %rax, -64(%rbp)
    
    .Lmain_if_end2:
    
    .Lmain_while_start:
    
        # LoadBoolConst(False, x10)
        movq $0, -80(%rbp)
    
        # CondJump(x10, Label(while_body), Label(while_end))
        cmpq $0, -80(%rbp)
        jne .Lmain_while_body
        jmp .Lmain_while_end
    
    .Lmain_while_body:
    
        # Call(k, [], x11)
        subq $8, %rsp
        callq k
        movq %rax, -88(%rbp)
        addq $8, %rsp
    
        # Jump(Label(while_start))
        jmp .Lmain_while_start
    
    .Lmain_while_end:
    
    .Lmain_while_start2:
    
        # LoadBoolConst(False, x12)
        movq $0, -96(%rbp)
    
        # CondJump(x12, Label(while_body2), Label(while_end2))
        cmpq $0, -96(%rbp)
        jne .Lmain_while_body2
        jmp .Lmain_while_end2
    
    .Lmain_while_body2:
    
        # LoadIntConst(1, x13)
        movq $1, -104(%rbp)
    
        # LoadIntConst(2, x14)
        movq $2, -112(%rbp)
    
        # Call(+, [x13, x14], x15)
        movq -104(%rbp), %rax
        addq -112(%rbp), %rax
        movq %rax, -120(%rbp)
    
        # Jump(Label(while_start2))
        jmp .Lmain_while_start2
    
    .Lmain_while_end2:
    
        # Return(None)
        movq $0, %rax
        movq %rbp, %rsp
        popq %rbp
        ret
        """

        self.assertEqual(trim(expect, False), trim(assemble(code), False))
