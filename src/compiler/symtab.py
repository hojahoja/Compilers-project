from dataclasses import dataclass, field
from typing import Self


@dataclass
class SymTab[T]:
    locals: dict[str, T] = field(default_factory=dict)
    parent: Self | None = None

    def get_value(self, symbol: str) -> T | None:
        symbols: SymTab[T] = self
        while symbols.parent and symbol not in symbols.locals:
            symbols = symbols.parent
        return symbols.locals.get(symbol)

    def require(self, symbol: str) -> T:
        value: T | None = self.get_value(symbol)
        if not value:
            raise NameError(f'Variable "{symbol}" not found.')
        return value

    def assign_value(self, symbol: str, value: T) -> bool:
        symbols: SymTab[T] = self
        while symbols.parent and symbol not in symbols.locals:
            symbols = symbols.parent

        if symbol in symbols.locals:
            symbols.locals[symbol] = value
            return True
        return False

    def in_locals(self, symbol: str) -> bool:
        return symbol in self.locals

    def add_local(self, symbol: str, value: T) -> None:
        self.locals[symbol] = value
