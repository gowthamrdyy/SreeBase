"""
Tests for the SreeBase Parser.
"""

import pytest

from sreebase.query.lexer import Lexer
from sreebase.query.parser import Parser
from sreebase.query.ast_nodes import (
    GetStatement,
    InsertStatement,
    UpdateStatement,
    DeleteStatement,
    Condition,
    SortClause,
)
from sreebase.errors import ParserError


def parse(source: str):
    """Helper: lex + parse, return the list of AST statements."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def parse_one(source: str):
    """Helper: parse and return the single statement."""
    stmts = parse(source)
    assert len(stmts) == 1
    return stmts[0]


# ---------------------------------------------------------------------- #
# GET
# ---------------------------------------------------------------------- #
class TestGet:
    def test_simple_get(self):
        stmt = parse_one("get users\n")
        assert isinstance(stmt, GetStatement)
        assert stmt.collection == "users"
        assert stmt.conditions == []

    def test_get_with_conditions(self):
        source = "get users\n    age > 25\n    city = \"Chennai\"\n"
        stmt = parse_one(source)
        assert isinstance(stmt, GetStatement)
        assert len(stmt.conditions) == 2
        assert stmt.conditions[0] == Condition("age", ">", 25)
        assert stmt.conditions[1] == Condition("city", "=", "Chennai")

    def test_get_with_sort(self):
        source = "get users\n    sort by name asc\n"
        stmt = parse_one(source)
        assert stmt.sort == SortClause("name", ascending=True)

    def test_get_with_sort_desc(self):
        source = "get users\n    sort by age desc\n"
        stmt = parse_one(source)
        assert stmt.sort == SortClause("age", ascending=False)

    def test_get_with_limit(self):
        source = "get users\n    limit 10\n"
        stmt = parse_one(source)
        assert stmt.limit == 10


# ---------------------------------------------------------------------- #
# INSERT
# ---------------------------------------------------------------------- #
class TestInsert:
    def test_simple_insert(self):
        source = 'insert into users\n    name = "Gowtham"\n    role = "developer"\n'
        stmt = parse_one(source)
        assert isinstance(stmt, InsertStatement)
        assert stmt.collection == "users"
        assert stmt.document == {"name": "Gowtham", "role": "developer"}

    def test_insert_mixed_types(self):
        source = (
            "insert into metrics\n"
            "    score = 9.5\n"
            "    active = true\n"
            "    count = 42\n"
        )
        stmt = parse_one(source)
        assert stmt.document == {"score": 9.5, "active": True, "count": 42}

    def test_insert_empty_raises(self):
        """INSERT with no assignments should fail."""
        with pytest.raises(ParserError):
            parse("insert into users\n")


# ---------------------------------------------------------------------- #
# UPDATE
# ---------------------------------------------------------------------- #
class TestUpdate:
    def test_update_with_where_and_set(self):
        source = (
            "update users\n"
            "    where\n"
            "        _id = \"user-42\"\n"
            "    set\n"
            "        role = \"architect\"\n"
        )
        stmt = parse_one(source)
        assert isinstance(stmt, UpdateStatement)
        assert stmt.collection == "users"
        assert len(stmt.conditions) == 1
        assert stmt.conditions[0] == Condition("_id", "=", "user-42")
        assert stmt.assignments == {"role": "architect"}

    def test_update_without_where(self):
        """UPDATE with only SET (updates all docs)."""
        source = (
            "update users\n"
            "    set\n"
            "        active = false\n"
        )
        stmt = parse_one(source)
        assert isinstance(stmt, UpdateStatement)
        assert stmt.conditions == []
        assert stmt.assignments == {"active": False}


# ---------------------------------------------------------------------- #
# DELETE
# ---------------------------------------------------------------------- #
class TestDelete:
    def test_delete_with_conditions(self):
        source = "delete from users\n    age < 18\n"
        stmt = parse_one(source)
        assert isinstance(stmt, DeleteStatement)
        assert stmt.collection == "users"
        assert len(stmt.conditions) == 1
        assert stmt.conditions[0] == Condition("age", "<", 18)

    def test_delete_all(self):
        source = "delete from users\n"
        stmt = parse_one(source)
        assert isinstance(stmt, DeleteStatement)
        assert stmt.conditions == []


# ---------------------------------------------------------------------- #
# Multi-statement
# ---------------------------------------------------------------------- #
class TestMultiStatement:
    def test_two_statements(self):
        source = (
            "get users\n"
            "get logs\n"
        )
        stmts = parse(source)
        assert len(stmts) == 2
        assert all(isinstance(s, GetStatement) for s in stmts)


# ---------------------------------------------------------------------- #
# Error cases
# ---------------------------------------------------------------------- #
class TestParserErrors:
    def test_unknown_statement(self):
        with pytest.raises(ParserError):
            parse("fly users\n")

    def test_missing_collection(self):
        with pytest.raises(ParserError):
            parse("get\n")
