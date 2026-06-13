"""
SreeBase Query Language — Lexer (Tokenizer)
============================================

Converts raw source text into a flat list of ``Token`` objects.

Indentation handling (Python-style)
-----------------------------------
* Each logical line's leading-space count is compared to an indent stack.
* Increase  → emit INDENT.
* Decrease  → emit one DEDENT per level popped.
* Blank lines and comment-only lines are ignored for indentation.

Strings are double-quoted with ``\\`` escapes.  Comments start with ``#``.
"""

from typing import List

from sreebase.query.tokens import Token, TokenType
from sreebase.errors import LexerError


# ------------------------------------------------------------------ #
# Keyword map  (case-insensitive)
# ------------------------------------------------------------------ #
KEYWORDS = {
    "get":    TokenType.GET,
    "insert": TokenType.INSERT,
    "into":   TokenType.INTO,
    "update": TokenType.UPDATE,
    "delete": TokenType.DELETE,
    "from":   TokenType.FROM,
    "set":    TokenType.SET,
    "where":  TokenType.WHERE,
    "sort":   TokenType.SORT,
    "by":     TokenType.BY,
    "asc":    TokenType.ASC,
    "desc":   TokenType.DESC,
    "limit":  TokenType.LIMIT,
    "show":   TokenType.SHOW,
    "collections": TokenType.COLLECTIONS,
    "create": TokenType.CREATE,
    "index":  TokenType.INDEX,
    "on":     TokenType.ON,
    "field":  TokenType.FIELD,
    "user":   TokenType.USER,
    "password": TokenType.PASSWORD,
    "role":   TokenType.ROLE,
    "login":  TokenType.LOGIN,
    "aggregate": TokenType.AGGREGATE,
    "group":  TokenType.GROUP,
    "calculate": TokenType.CALCULATE,
    "true":   TokenType.BOOL,
    "false":  TokenType.BOOL,
    "null":   TokenType.NULL,
}

# Multi-char operators checked before single-char to avoid partial match.
_OPERATORS = [
    (">=", TokenType.GTE),
    ("<=", TokenType.LTE),
    ("!=", TokenType.NEQ),
    ("=",  TokenType.EQ),
    (">",  TokenType.GT),
    ("<",  TokenType.LT),
    ("(",  TokenType.LPAREN),
    (")",  TokenType.RPAREN),
    (",",  TokenType.COMMA),
]


class Lexer:
    """
    Indentation-aware tokenizer for the SreeBase bracketless query language.

    Usage::

        tokens = Lexer(source_text).tokenize()
    """

    def __init__(self, source: str) -> None:
        # Normalize line endings; ensure trailing newline for clean EOF.
        self._src = source.replace("\r\n", "\n").replace("\r", "\n")
        if not self._src.endswith("\n"):
            self._src += "\n"
        self._tokens: List[Token] = []
        self._indent_stack: List[int] = [0]

    def tokenize(self) -> List[Token]:
        """Tokenize the full source and return the token list."""
        lines = self._src.split("\n")
        # split() on the trailing newline yields a final empty string; drop it.
        if lines and lines[-1] == "":
            lines.pop()

        for lineno, raw_line in enumerate(lines, start=1):
            self._process_line(lineno, raw_line)

        # At EOF, close any open indents.
        eof_line = len(lines) + 1
        while len(self._indent_stack) > 1:
            self._indent_stack.pop()
            self._emit(TokenType.DEDENT, None, eof_line, 0)

        self._emit(TokenType.EOF, None, eof_line, 0)
        return self._tokens

    # -------------------------------------------------------------- #
    # Per-line processing
    # -------------------------------------------------------------- #
    def _process_line(self, lineno: int, raw_line: str) -> None:
        # Measure indentation (spaces; tabs expanded to 4 spaces).
        expanded = raw_line.expandtabs(4)
        stripped = expanded.lstrip(" ")
        indent = len(expanded) - len(stripped)

        # Skip blank lines and comment-only lines for indentation.
        if stripped == "" or stripped.startswith("#"):
            return

        # --- Indentation bookkeeping ---
        if indent > self._indent_stack[-1]:
            self._indent_stack.append(indent)
            self._emit(TokenType.INDENT, indent, lineno, 0)
        else:
            while indent < self._indent_stack[-1]:
                self._indent_stack.pop()
                self._emit(TokenType.DEDENT, None, lineno, indent)
            if indent != self._indent_stack[-1]:
                raise LexerError(
                    f"Inconsistent indentation on line {lineno}."
                )

        # --- Tokenize the content of the line ---
        self._tokenize_content(lineno, stripped, indent)
        self._emit(TokenType.NEWLINE, None, lineno, len(expanded))

    def _tokenize_content(
        self, lineno: int, text: str, base_col: int
    ) -> None:
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            col = base_col + i + 1

            # Skip whitespace within a line.
            if ch == " ":
                i += 1
                continue

            # Inline comment → rest of line ignored.
            if ch == "#":
                break

            # String literal.
            if ch == '"':
                value, consumed = self._read_string(text, i, lineno)
                self._emit(TokenType.STRING, value, lineno, col)
                i += consumed
                continue

            # Number (int or float, optional leading minus).
            if ch.isdigit() or (
                ch == "-" and i + 1 < n and text[i + 1].isdigit()
            ):
                value, consumed = self._read_number(text, i)
                self._emit(TokenType.NUMBER, value, lineno, col)
                i += consumed
                continue

            # Operators (multi-char checked first).
            matched = False
            for sym, ttype in _OPERATORS:
                if text.startswith(sym, i):
                    self._emit(ttype, sym, lineno, col)
                    i += len(sym)
                    matched = True
                    break
            if matched:
                continue

            # Identifier / keyword.
            if ch.isalpha() or ch == "_":
                value, consumed = self._read_identifier(text, i)
                lower = value.lower()
                if lower in KEYWORDS:
                    ttype = KEYWORDS[lower]
                    if ttype == TokenType.BOOL:
                        self._emit(ttype, lower == "true", lineno, col)
                    elif ttype == TokenType.NULL:
                        self._emit(ttype, None, lineno, col)
                    else:
                        self._emit(ttype, lower, lineno, col)
                else:
                    self._emit(TokenType.IDENT, value, lineno, col)
                i += consumed
                continue

            raise LexerError(
                f"Unexpected character {ch!r} on line {lineno}, col {col}."
            )

    # -------------------------------------------------------------- #
    # Primitive readers
    # -------------------------------------------------------------- #
    def _read_string(self, text: str, start: int, lineno: int):
        """Read a double-quoted string with backslash escapes."""
        i = start + 1  # skip opening quote
        out = []
        escape_map = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
        while i < len(text):
            ch = text[i]
            if ch == "\\" and i + 1 < len(text):
                nxt = text[i + 1]
                out.append(escape_map.get(nxt, nxt))
                i += 2
                continue
            if ch == '"':
                return "".join(out), (i - start + 1)
            out.append(ch)
            i += 1
        raise LexerError(f"Unterminated string on line {lineno}.")

    @staticmethod
    def _read_number(text: str, start: int):
        """Read an int or float literal."""
        i = start
        if text[i] == "-":
            i += 1
        is_float = False
        while i < len(text) and (text[i].isdigit() or text[i] == "."):
            if text[i] == ".":
                if is_float:  # second dot → stop
                    break
                is_float = True
            i += 1
        raw = text[start:i]
        value = float(raw) if is_float else int(raw)
        return value, (i - start)

    @staticmethod
    def _read_identifier(text: str, start: int):
        """Read an alphanumeric identifier (allows dots for nested fields)."""
        i = start
        while i < len(text) and (text[i].isalnum() or text[i] in ("_", ".")):
            i += 1
        return text[start:i], (i - start)

    # -------------------------------------------------------------- #
    def _emit(
        self, ttype: TokenType, value, lineno: int, col: int
    ) -> None:
        self._tokens.append(Token(ttype, value, lineno, col))
