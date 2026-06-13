"""
SreeBase Query Language — Token definitions.
=============================================

Every lexeme produced by the Lexer is represented as a ``Token``
with a ``TokenType`` discriminator, a native Python ``value``,
and source-location info (``line``, ``col``) for error messages.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    """Discriminated types for every lexeme in the SreeBase query language."""

    # ---- Keywords ----
    GET = auto()
    INSERT = auto()
    INTO = auto()
    UPDATE = auto()
    DELETE = auto()
    FROM = auto()

    # Punctuation & Operators
    EQ = auto()
    NEQ = auto()
    GT = auto()
    GTE = auto()
    LT = auto()
    LTE = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    SET = auto()       # used by UPDATE:  update users where … set field = value
    WHERE = auto()     # optional explicit keyword; clauses also imply filtering
    SORT = auto()      # sort by <field>
    BY = auto()
    ASC = auto()
    DESC = auto()
    LIMIT = auto()
    SHOW = auto()
    COLLECTIONS = auto()
    CREATE = auto()
    INDEX = auto()
    ON = auto()
    FIELD = auto()
    USER = auto()
    PASSWORD = auto()
    ROLE = auto()
    LOGIN = auto()
    AGGREGATE = auto()
    GROUP = auto()
    CALCULATE = auto()

    # ---- Identifiers & literals ----
    IDENT = auto()     # collection or field name
    STRING = auto()
    NUMBER = auto()
    BOOL = auto()
    NULL = auto()

    # ---- Structure ----
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


@dataclass
class Token:
    """A single lexeme with type, value, and source location."""
    type: TokenType
    value: Any          # native python value for literals, raw text otherwise
    line: int
    col: int

    def __repr__(self) -> str:
        return (
            f"Token({self.type.name}, {self.value!r}, "
            f"L{self.line}:C{self.col})"
        )
