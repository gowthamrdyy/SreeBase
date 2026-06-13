"""
SreeBase Query Language — Parser (Tokens → AST)
=================================================

Recursive-descent parser over the lexer's token stream.

Grammar (informal)
------------------
::

    program       := statement+
    statement     := get_stmt | insert_stmt | update_stmt | delete_stmt

    get_stmt      := GET IDENT NEWLINE [INDENT condition+ DEDENT]
    delete_stmt   := DELETE FROM IDENT NEWLINE [INDENT condition+ DEDENT]
    insert_stmt   := INSERT INTO IDENT NEWLINE INDENT assignment+ DEDENT
    update_stmt   := UPDATE IDENT NEWLINE INDENT
                       (WHERE NEWLINE INDENT condition+ DEDENT)?
                       SET NEWLINE INDENT assignment+ DEDENT
                     DEDENT
    condition     := IDENT operator literal NEWLINE
    assignment    := IDENT EQ literal NEWLINE
    literal       := STRING | NUMBER | BOOL | NULL

Security
--------
Field names are validated as strict identifiers; values are typed literals
only — never ``eval``'d or string-concatenated into anything.
"""

import re
from typing import Any, List

from sreebase.query.tokens import Token, TokenType
from sreebase.query.ast_nodes import (
    Condition,
    SortClause,
    GetStatement,
    InsertStatement,
    UpdateStatement,
    DeleteStatement,
    ShowCollectionsStatement,
    CreateIndexStatement,
    CreateUserStatement,
    LoginStatement,
    AggregateStatement,
    AggregationFunction,
)
from sreebase.errors import ParserError


_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

_COMPARISON_OPS = {
    TokenType.EQ:  "=",
    TokenType.NEQ: "!=",
    TokenType.GT:  ">",
    TokenType.GTE: ">=",
    TokenType.LT:  "<",
    TokenType.LTE: "<=",
}

_LITERAL_TYPES = (
    TokenType.STRING,
    TokenType.NUMBER,
    TokenType.BOOL,
    TokenType.NULL,
)


class Parser:
    """
    Recursive-descent parser for the SreeBase bracketless query language.

    Usage::

        statements = Parser(tokens).parse()
    """

    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------ #
    # Token cursor helpers
    # ------------------------------------------------------------------ #
    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, ttype: TokenType) -> bool:
        return self._peek().type == ttype

    def _expect(self, ttype: TokenType, what: str) -> Token:
        if not self._check(ttype):
            got = self._peek()
            raise ParserError(
                f"Expected {what} but got {got.type.name} "
                f"({got.value!r}) at line {got.line}."
            )
        return self._advance()

    def _skip_newlines(self) -> None:
        while self._check(TokenType.NEWLINE):
            self._advance()

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def parse(self) -> List[Any]:
        """Parse the whole program into a list of statement AST nodes."""
        statements: List[Any] = []
        self._skip_newlines()
        while not self._check(TokenType.EOF):
            statements.append(self._parse_statement())
            self._skip_newlines()
        return statements

    def _parse_statement(self) -> Any:
        tok = self._peek()
        if tok.type == TokenType.SHOW:
            return self._parse_show()
        if tok.type == TokenType.CREATE:
            nxt = self._tokens[self._pos + 1] if self._pos + 1 < len(self._tokens) else None
            if nxt and nxt.type == TokenType.INDEX:
                return self._parse_create_index()
            elif nxt and nxt.type == TokenType.USER:
                return self._parse_create_user()
            raise ParserError(f"Unknown create statement at line {tok.line}.")
        if tok.type == TokenType.LOGIN:
            return self._parse_login()
        if tok.type == TokenType.AGGREGATE:
            return self._parse_aggregate()
        if tok.type == TokenType.GET:
            return self._parse_get()
        if tok.type == TokenType.INSERT:
            return self._parse_insert()
        if tok.type == TokenType.UPDATE:
            return self._parse_update()
        if tok.type == TokenType.DELETE:
            return self._parse_delete()
        raise ParserError(
            f"Unknown statement starting with {tok.type.name} "
            f"at line {tok.line}."
        )

    # ------------------------------------------------------------------ #
    # SHOW
    # ------------------------------------------------------------------ #
    def _parse_show(self) -> ShowCollectionsStatement:
        self._expect(TokenType.SHOW, "'show'")
        self._expect(TokenType.COLLECTIONS, "'collections'")
        self._expect(TokenType.NEWLINE, "newline after 'show collections'")
        return ShowCollectionsStatement()

    # ------------------------------------------------------------------ #
    # CREATE INDEX & USER
    # ------------------------------------------------------------------ #
    def _parse_create_index(self) -> CreateIndexStatement:
        self._expect(TokenType.CREATE, "'create'")
        self._expect(TokenType.INDEX, "'index'")
        self._expect(TokenType.ON, "'on'")
        collection = self._parse_collection_name()
        self._expect(TokenType.FIELD, "'field'")
        field_name = self._parse_field_name()
        self._expect(TokenType.NEWLINE, "newline after 'create index'")
        return CreateIndexStatement(collection=collection, field=field_name)

    def _parse_create_user(self) -> CreateUserStatement:
        self._expect(TokenType.CREATE, "'create'")
        self._expect(TokenType.USER, "'user'")
        username = self._expect(TokenType.IDENT, "username").value
        self._expect(TokenType.PASSWORD, "'password'")
        password = self._expect(TokenType.STRING, "password string").value
        self._expect(TokenType.ROLE, "'role'")
        role = self._expect(TokenType.IDENT, "role name (admin/read)").value
        self._expect(TokenType.NEWLINE, "newline after 'create user'")
        return CreateUserStatement(username=username, password=password, role=role)

    # ------------------------------------------------------------------ #
    # LOGIN
    # ------------------------------------------------------------------ #
    def _parse_login(self) -> LoginStatement:
        self._expect(TokenType.LOGIN, "'login'")
        username = self._expect(TokenType.IDENT, "username").value
        self._expect(TokenType.PASSWORD, "'password'")
        password = self._expect(TokenType.STRING, "password string").value
        self._expect(TokenType.NEWLINE, "newline after 'login'")
        return LoginStatement(username=username, password=password)

    # ------------------------------------------------------------------ #
    # AGGREGATE
    # ------------------------------------------------------------------ #
    def _parse_aggregate(self) -> AggregateStatement:
        self._expect(TokenType.AGGREGATE, "'aggregate'")
        collection = self._parse_collection_name()
        self._expect(TokenType.NEWLINE, "newline after collection")

        conditions = []
        group_by = ""
        calculations = []

        self._expect(TokenType.INDENT, "indented blocks for aggregate")

        # Optional WHERE block
        if self._check(TokenType.WHERE):
            self._advance()
            self._expect(TokenType.NEWLINE, "newline after 'where'")
            self._expect(TokenType.INDENT, "indented conditions")
            while not self._check(TokenType.DEDENT) and not self._check(TokenType.EOF):
                conditions.append(self._parse_condition())
            if self._check(TokenType.DEDENT):
                self._advance()

        # GROUP BY block
        self._expect(TokenType.GROUP, "'group'")
        self._expect(TokenType.BY, "'by'")
        group_by = self._expect(TokenType.IDENT, "group by field").value
        self._expect(TokenType.NEWLINE, "newline after 'group by'")

        # CALCULATE block
        self._expect(TokenType.CALCULATE, "'calculate'")
        while not self._check(TokenType.NEWLINE) and not self._check(TokenType.EOF):
            func_name = self._expect(TokenType.IDENT, "aggregation function name").value
            self._expect(TokenType.LPAREN, "'('")
            
            field = None
            if not self._check(TokenType.RPAREN):
                field = self._expect(TokenType.IDENT, "field name").value
            self._expect(TokenType.RPAREN, "')'")
            
            calculations.append(AggregationFunction(func_name=func_name, field=field))
            
            if self._check(TokenType.COMMA):
                self._advance()
            else:
                break
                
        self._expect(TokenType.NEWLINE, "newline after calculations")

        if self._check(TokenType.DEDENT):
            self._advance()

        return AggregateStatement(
            collection=collection,
            group_by=group_by,
            calculations=calculations,
            conditions=conditions
        )

    # ------------------------------------------------------------------ #
    # GET
    # ------------------------------------------------------------------ #
    def _parse_get(self) -> GetStatement:
        self._expect(TokenType.GET, "'get'")
        collection = self._parse_collection_name()
        self._expect(TokenType.NEWLINE, "newline after collection")

        conditions: List[Condition] = []
        sort = None
        limit = None

        if self._check(TokenType.INDENT):
            self._advance()  # consume INDENT
            while not self._check(TokenType.DEDENT) and not self._check(
                TokenType.EOF
            ):
                # Check for sort clause.
                if self._check(TokenType.SORT):
                    sort = self._parse_sort_clause()
                    continue
                # Check for limit clause.
                if self._check(TokenType.LIMIT):
                    limit = self._parse_limit_clause()
                    continue
                conditions.append(self._parse_condition())

            if self._check(TokenType.DEDENT):
                self._advance()  # consume DEDENT

        return GetStatement(
            collection=collection,
            conditions=conditions,
            sort=sort,
            limit=limit,
        )

    # ------------------------------------------------------------------ #
    # INSERT
    # ------------------------------------------------------------------ #
    def _parse_insert(self) -> InsertStatement:
        self._expect(TokenType.INSERT, "'insert'")
        self._expect(TokenType.INTO, "'into'")
        collection = self._parse_collection_name()
        self._expect(TokenType.NEWLINE, "newline after collection")
        self._expect(TokenType.INDENT, "indented assignments")

        document = {}
        while not self._check(TokenType.DEDENT) and not self._check(
            TokenType.EOF
        ):
            field_name, value = self._parse_assignment()
            document[field_name] = value

        if self._check(TokenType.DEDENT):
            self._advance()  # consume DEDENT

        if not document:
            raise ParserError("INSERT requires at least one field = value.")

        return InsertStatement(collection=collection, document=document)

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    def _parse_update(self) -> UpdateStatement:
        self._expect(TokenType.UPDATE, "'update'")
        collection = self._parse_collection_name()
        self._expect(TokenType.NEWLINE, "newline after collection")
        self._expect(TokenType.INDENT, "indented where/set blocks")

        conditions: List[Condition] = []
        assignments = {}

        # ---- WHERE block (optional) ----
        if self._check(TokenType.WHERE):
            self._advance()  # consume WHERE
            self._expect(TokenType.NEWLINE, "newline after 'where'")
            self._expect(TokenType.INDENT, "indented conditions")
            while not self._check(TokenType.DEDENT) and not self._check(
                TokenType.EOF
            ):
                conditions.append(self._parse_condition())
            if self._check(TokenType.DEDENT):
                self._advance()

        # ---- SET block (required) ----
        self._expect(TokenType.SET, "'set'")
        self._expect(TokenType.NEWLINE, "newline after 'set'")
        self._expect(TokenType.INDENT, "indented assignments")
        while not self._check(TokenType.DEDENT) and not self._check(
            TokenType.EOF
        ):
            field_name, value = self._parse_assignment()
            assignments[field_name] = value
        if self._check(TokenType.DEDENT):
            self._advance()

        if not assignments:
            raise ParserError("UPDATE requires at least one set assignment.")

        # Consume the outer DEDENT.
        if self._check(TokenType.DEDENT):
            self._advance()

        return UpdateStatement(
            collection=collection,
            conditions=conditions,
            assignments=assignments,
        )

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #
    def _parse_delete(self) -> DeleteStatement:
        self._expect(TokenType.DELETE, "'delete'")
        self._expect(TokenType.FROM, "'from'")
        collection = self._parse_collection_name()
        self._expect(TokenType.NEWLINE, "newline after collection")

        conditions: List[Condition] = []
        if self._check(TokenType.INDENT):
            self._advance()  # consume INDENT
            while not self._check(TokenType.DEDENT) and not self._check(
                TokenType.EOF
            ):
                conditions.append(self._parse_condition())
            if self._check(TokenType.DEDENT):
                self._advance()

        return DeleteStatement(
            collection=collection, conditions=conditions
        )

    # ------------------------------------------------------------------ #
    # Sub-parsers
    # ------------------------------------------------------------------ #
    def _parse_field_name(self) -> str:
        """Parse a field name, allowing keywords to be used as fields."""
        tok = self._advance()
        if tok.type == TokenType.IDENT or isinstance(tok.value, str):
            name = str(tok.value)
            if _IDENT_RE.match(name):
                return name
        raise ParserError(
            f"Expected field name but got {tok.type.name} at line {tok.line}."
        )

    def _parse_collection_name(self) -> str:
        tok = self._expect(TokenType.IDENT, "collection name")
        name = tok.value
        if not _IDENT_RE.match(name):
            raise ParserError(
                f"Invalid collection name: {name!r} at line {tok.line}."
            )
        return name

    def _parse_condition(self) -> Condition:
        """Parse ``field op literal NEWLINE``."""
        field_name = self._parse_field_name()

        # Operator.
        op_tok = self._peek()
        if op_tok.type not in _COMPARISON_OPS:
            raise ParserError(
                f"Expected comparison operator but got {op_tok.type.name} "
                f"at line {op_tok.line}."
            )
        self._advance()
        op = _COMPARISON_OPS[op_tok.type]

        # Value.
        value = self._parse_literal()

        self._expect(TokenType.NEWLINE, "newline after condition")
        return Condition(field=field_name, op=op, value=value)

    def _parse_assignment(self):
        """Parse ``field = literal NEWLINE``.  Returns (field, value)."""
        field_name = self._parse_field_name()

        self._expect(TokenType.EQ, "'='")
        value = self._parse_literal()
        self._expect(TokenType.NEWLINE, "newline after assignment")
        return field_name, value

    def _parse_literal(self) -> Any:
        """Parse a single literal value (string, number, bool, null)."""
        tok = self._peek()
        if tok.type in _LITERAL_TYPES:
            self._advance()
            return tok.value
        raise ParserError(
            f"Expected a literal value but got {tok.type.name} "
            f"({tok.value!r}) at line {tok.line}."
        )

    def _parse_sort_clause(self) -> SortClause:
        """Parse ``sort by <field> [asc|desc] NEWLINE``."""
        self._expect(TokenType.SORT, "'sort'")
        self._expect(TokenType.BY, "'by'")
        field_tok = self._expect(TokenType.IDENT, "sort field")
        ascending = True
        if self._check(TokenType.ASC):
            self._advance()
        elif self._check(TokenType.DESC):
            self._advance()
            ascending = False
        self._expect(TokenType.NEWLINE, "newline after sort clause")
        return SortClause(field=field_tok.value, ascending=ascending)

    def _parse_limit_clause(self) -> int:
        """Parse ``limit <number> NEWLINE``."""
        self._expect(TokenType.LIMIT, "'limit'")
        tok = self._expect(TokenType.NUMBER, "limit count")
        if not isinstance(tok.value, int) or tok.value < 1:
            raise ParserError(
                f"LIMIT must be a positive integer, got {tok.value!r} "
                f"at line {tok.line}."
            )
        self._expect(TokenType.NEWLINE, "newline after limit")
        return tok.value
