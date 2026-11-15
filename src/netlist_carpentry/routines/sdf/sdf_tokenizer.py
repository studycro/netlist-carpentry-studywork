"""Tokenizer and parser for s-expressions, plus helpers for walking the result.

Nothing in here knows about SDF. The layer turns text into nested lists:

    '(CELL (CELLTYPE "AND2_X1"))'  ->  ['CELL', ['CELLTYPE', 'AND2_X1']]

Giving that structure a meaning is the job of the module that uses it.
"""

from __future__ import annotations
import re
from typing import Any

__all__ = [
    "IGNORED_TOKEN_KINDS",
    "TOKEN_PATTERN",
    "find_tagged",
    "has_tag",
    "parse_tokens",
    "stringify",
    "tokenize",
]

IGNORED_TOKEN_KINDS = frozenset({"COMMENT", "WS"})

TOKEN_PATTERN = re.compile(
    r"""
    (?P<COMMENT>//[^\n]*|/\*[\s\S]*?\*/) |
    (?P<WS>\s+) |
    (?P<LPAREN>\() |
    (?P<RPAREN>\)) |
    (?P<STRING>"(?:\\.|[^"\\])*") |
    (?P<ESCAPED>\\\S+) |
    (?P<ATOM>[^\s()"]+)
    """,
    re.VERBOSE,
)


def tokenize(text: str) -> list[str]:
    """Turns text into a flat list of tokens.

    Comments and whitespace are dropped, quotes around strings are stripped.
    """
    tokens: list[str] = []
    for match in TOKEN_PATTERN.finditer(text):
        kind = match.lastgroup
        if kind in IGNORED_TOKEN_KINDS:
            continue

        value = match.group()
        if kind == "STRING":
            value = value[1:-1]
        tokens.append(value)

    return tokens


def parse_tokens(tokens: list[str]) -> list[Any]:
    """Turns tokens into nested lists, mirroring the parentheses."""
    stack: list[list[Any]] = [[]]
    for token in tokens:
        if token == "(":
            stack.append([])
        elif token == ")":
            if len(stack) == 1:
                raise ValueError("Syntax error: unexpected ')'")
            completed_block = stack.pop()
            stack[-1].append(completed_block)
        else:
            stack[-1].append(token)

    if len(stack) != 1:
        raise ValueError("Syntax error: missing ')'")
    return stack[0]

def has_tag(node: Any, tag: str) -> bool:
    """Checks whether a node is a list starting with the expected tag."""
    return isinstance(node, list) and bool(node) and node[0] == tag


def find_tagged(parent: list[Any], tag: str) -> list[Any] | None:
    """First direct child of `parent` carrying `tag`, None if there is none."""
    for entry in parent[1:]:
        if has_tag(entry, tag):
            return entry
    return None


def stringify(node: Any) -> str:
    """Renders a node back into a readable string, parentheses included."""
    if isinstance(node, list):
        return "(" + " ".join(stringify(part) for part in node) + ")"
    return str(node)