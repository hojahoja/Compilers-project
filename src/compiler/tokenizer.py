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
    comment: Pattern[str] = re.compile(r"(//|#).*")
    multiline_comment: Pattern[str] = re.compile(r"/\*[\s\S]*?\*/")

    skip_patterns: list[Pattern[str]] = [whitespace, comment, multiline_comment]
    token_patterns: dict[str, Pattern[str]] = {
        "identifier": re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"),
        "int_literal": re.compile(r"\d+"),
        "operator": re.compile(r"(==|!=|<=|>=)|[-+*/=<>]"),
        "punctuation": re.compile(r"[(){},;]"),
    }

    i: int = 0
    tokens: list[Token] = []
    while i < len(source_code):
        start: int = i

        for regex in skip_patterns:
            i = _skip_pattern(source_code, regex, i)

        for category in token_patterns.keys():
            i = _extract_token(source_code, category, token_patterns[category], tokens, i)

        if i == start:
            raise SyntaxError(f"Unrecognized character: {source_code[i]}")

    return tokens

def _skip_pattern(source_code: str, regex: Pattern[str],  position: int) -> int:
    match: Match[str] | None = regex.match(source_code, position)
    if match:
        return match.end()
    return position

def _extract_token(source_code: str, category: str, regex: Pattern[str], tokens: list[Token], position: int) -> int:
    match: Match[str] | None = regex.match(source_code, position)
    if match:
        tokens.append(Token(category, match.group()))
        return match.end()
    return position
