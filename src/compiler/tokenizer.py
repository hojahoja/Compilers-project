import re
from dataclasses import dataclass, field
from typing import Match, Pattern, Literal

TokenType = Literal[
    "while_loop", "conditional", "identifier", "bool_literal", "int_literal",
    "operator", "punctuation", "end", "declaration",
]


@dataclass(frozen=True)
class Location:
    file: str
    line: int
    column: int


@dataclass
class Token:
    type: TokenType
    text: str
    location: Location = field(default_factory=lambda: Location("no file", 1, 1))


def tokenize(source_code: str, file_name: str = "no file") -> list[Token]:
    skip_patterns: dict[str, Pattern[str]] = {
        "whitespace": re.compile(r"\s+"),
        "comment": re.compile(r"(//|#).*"),
        "multiline_comment": re.compile(r"/\*[\s\S]*?\*/")
    }

    token_patterns: dict[TokenType, Pattern[str]] = {
        "while_loop": re.compile(r"\b(while|do)\b"),
        "conditional": re.compile(r"\b(if|then|else)\b"),
        "declaration": re.compile(r"\b(var)\b"),
        "operator": re.compile(r"\b(and|or|not)\b|(==|!=|<=|>=)|[-+*/%=<>]"),
        "bool_literal": re.compile(r"\b(true|false)\b"),
        "int_literal": re.compile(r"\d+"),
        "identifier": re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"),
        "punctuation": re.compile(r"[(){},;:]"),
    }

    line: int = 1
    column: int = 0

    def skip_pattern(skip_type: str, regex: Pattern[str], index: int) -> int:
        match: Match[str] | None = regex.match(source_code, index)
        if match:
            if skip_type in ("whitespace", "multiline_comment"):
                adjust_column_position_after_skip(match.group())
            return match.end()
        return index

    def adjust_column_position_after_skip(skipped_pattern: str) -> None:
        nonlocal line
        nonlocal column
        linebreaks: int = skipped_pattern.count("\n")
        line += linebreaks
        if linebreaks and skipped_pattern[-1] == "\n":
            column = 0
        elif linebreaks:
            column = len(skipped_pattern) - skipped_pattern.rfind("\n") - 1
        else:
            column += len(skipped_pattern)

    def extract_token(token_type: TokenType, regex: Pattern[str], index: int) -> int:
        match: Match[str] | None = regex.match(source_code, index)
        if match:
            nonlocal column
            location: Location = Location(file_name, line, column + 1)
            tokens.append(Token(token_type, match.group(), location))
            column += match.end() - index
            return match.end()
        return index

    i: int = 0
    tokens: list[Token] = []
    while i < len(source_code):
        start: int = i

        for s_type in skip_patterns.keys():
            i = skip_pattern(s_type, skip_patterns[s_type], i)

        for t_type in token_patterns.keys():
            i = extract_token(t_type, token_patterns[t_type], i)

        if i == start:
            raise SyntaxError(f"Unrecognized character: {source_code[i]}")

    return tokens
