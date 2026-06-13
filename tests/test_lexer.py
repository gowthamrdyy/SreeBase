"""
Tests for the SreeBase Lexer.
"""

import pytest

from sreebase.query.lexer import Lexer
from sreebase.query.tokens import TokenType
from sreebase.errors import LexerError


def types(source: str):
    """Helper: return just the token types (excluding NEWLINE/INDENT/DEDENT/EOF)."""
    tokens = Lexer(source).tokenize()
    return [
        t.type for t in tokens
        if t.type not in (
            TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.EOF
        )
    ]


def values(source: str):
    """Helper: return (type, value) pairs for non-structural tokens."""
    tokens = Lexer(source).tokenize()
    return [
        (t.type, t.value) for t in tokens
        if t.type not in (
            TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.EOF
        )
    ]


class TestKeywords:
    def test_get(self):
        assert types("get users") == [TokenType.GET, TokenType.IDENT]

    def test_insert_into(self):
        assert types("insert into users") == [
            TokenType.INSERT, TokenType.INTO, TokenType.IDENT
        ]

    def test_delete_from(self):
        assert types("delete from users") == [
            TokenType.DELETE, TokenType.FROM, TokenType.IDENT
        ]

    def test_keywords_case_insensitive(self):
        assert types("GET Users") == [TokenType.GET, TokenType.IDENT]


class TestLiterals:
    def test_string(self):
        result = values('name = "Gowtham"')
        assert result == [
            (TokenType.IDENT, "name"),
            (TokenType.EQ, "="),
            (TokenType.STRING, "Gowtham"),
        ]

    def test_number_int(self):
        result = values("age > 25")
        assert result[2] == (TokenType.NUMBER, 25)

    def test_number_float(self):
        result = values("score >= 9.5")
        assert result[2] == (TokenType.NUMBER, 9.5)

    def test_negative_number(self):
        result = values("temp < -10")
        assert result[2] == (TokenType.NUMBER, -10)

    def test_bool_true(self):
        result = values("active = true")
        assert result[2] == (TokenType.BOOL, True)

    def test_bool_false(self):
        result = values("active = false")
        assert result[2] == (TokenType.BOOL, False)

    def test_null(self):
        result = values("email = null")
        assert result[2] == (TokenType.NULL, None)


class TestOperators:
    @pytest.mark.parametrize("sym,expected", [
        ("=", TokenType.EQ),
        ("!=", TokenType.NEQ),
        (">", TokenType.GT),
        (">=", TokenType.GTE),
        ("<", TokenType.LT),
        ("<=", TokenType.LTE),
    ])
    def test_all_operators(self, sym, expected):
        tokens = Lexer(f"x {sym} 1").tokenize()
        op_tokens = [t for t in tokens if t.type == expected]
        assert len(op_tokens) == 1


class TestIndentation:
    def test_indent_dedent(self):
        source = "get users\n    age > 25\n"
        tokens = Lexer(source).tokenize()
        ttypes = [t.type for t in tokens]
        assert TokenType.INDENT in ttypes
        assert TokenType.DEDENT in ttypes

    def test_blank_lines_ignored(self):
        source = "get users\n\n    age > 25\n"
        tokens = Lexer(source).tokenize()
        ttypes = [t.type for t in tokens]
        assert TokenType.INDENT in ttypes

    def test_comment_lines_ignored(self):
        source = "get users\n# this is a comment\n    age > 25\n"
        tokens = Lexer(source).tokenize()
        ttypes = [t.type for t in tokens]
        assert TokenType.INDENT in ttypes


class TestStringEscapes:
    def test_escaped_quote(self):
        result = values(r'msg = "say \"hello\""')
        assert result[2] == (TokenType.STRING, 'say "hello"')

    def test_escaped_newline(self):
        result = values(r'msg = "line1\nline2"')
        assert result[2] == (TokenType.STRING, "line1\nline2")


class TestErrors:
    def test_unterminated_string(self):
        with pytest.raises(LexerError):
            Lexer('name = "oops').tokenize()

    def test_unexpected_character(self):
        with pytest.raises(LexerError):
            Lexer("x = @bad").tokenize()
