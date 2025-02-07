import sys

from src.compiler.assembly_generator import generate_assembly
from src.compiler.ir_generator import generate_ir, ROOT_TYPES
from src.compiler.type_checker import typecheck
from src.compiler.parser import parse
from src.compiler.tokenizer import tokenize

def read_file(filename: str) -> str:
    with open(filename) as f:
        return f.read()

def turn_to_assembly(code: str) -> str:
    expression = parse(tokenize(code))
    typecheck(expression)
    assembly_code = generate_assembly(generate_ir(ROOT_TYPES, expression))
    return assembly_code

def write_to_file(filename: str, assembly_code: str) -> None:
    with open(filename, 'w') as f:
        f.write(assembly_code)


if __name__ == "__main__":
    input_name, output_name = sys.argv[1:]
    assembly = turn_to_assembly(read_file(input_name))
    write_to_file(output_name, assembly)


