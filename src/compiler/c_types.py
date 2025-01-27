from dataclasses import dataclass


@dataclass(frozen=True)
class Type:
    name: str


Int = Type("Integer")
Bool = Type("Boolean")
Unit = Type("Unit")


@dataclass(frozen=True)
class FunType(Type):
    params: tuple[Type, ...]
    return_type: Type
