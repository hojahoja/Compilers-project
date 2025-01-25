from dataclasses import dataclass


@dataclass
class Type:
    name: str


Int = Type("Integer")
Bool = Type("Boolean")
Unit = Type("Unit")


@dataclass
class FunType(Type):
    params: tuple[Type, ...]
    return_type: Type
