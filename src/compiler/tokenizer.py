import re
from dataclasses import dataclass, field
from typing import Match, Pattern


@dataclass
class Location:
    file: str
    line: int
    column: int


@dataclass
class Token:
    category: str
    text: str
    location: Location = field(default_factory=lambda: Location("placeholder", 0, 0))


def tokenize(source_code: str) -> list[Token]:
    whitespace: Pattern[str] = re.compile(r"\s+")
    patterns: dict[str, Pattern[str]] = {
        "identifier": re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"),
        "int_literal": re.compile(r"\d+")
    }

    i: int = 0
    tokens: list[Token] = []
    while i < len(source_code):
        start: int = i
        match: Match[str] | None = whitespace.match(source_code, i)
        if match:
            i = match.end()
        for pattern in patterns:
            i = _extract_token(source_code, pattern, patterns[pattern], tokens, i)
        if i == start:
            raise SyntaxError(f"Unrecognized character: {source_code[i]}")

    return tokens


def _extract_token(source_code: str, category: str, regex: Pattern[str], tokens: list[Token], position: int) -> int:
    match: Match[str] | None = regex.match(source_code, position)
    if match:
        tokens.append(Token(category, match.group()))
        return match.end()
    return position
