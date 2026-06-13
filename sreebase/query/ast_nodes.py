"""
SreeBase Query Language — Abstract Syntax Tree node definitions.
================================================================

The parser produces one of these Statement nodes per query.  The executor
pattern-matches on the node type to drive the storage engine.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Condition:
    """
    A single WHERE clause.

    Example: ``age > 25`` → ``Condition(field='age', op='>', value=25)``
    """
    field: str
    op: str          # one of: = != > >= < <=
    value: Any


@dataclass
class SortClause:
    """
    A sort directive.

    Example: ``sort by name asc`` → ``SortClause(field='name', ascending=True)``
    """
    field: str
    ascending: bool = True


@dataclass
class ShowCollectionsStatement:
    pass

@dataclass
class CreateIndexStatement:
    collection: str
    field: str

@dataclass
class CreateUserStatement:
    username: str
    password: str
    role: str

@dataclass
class LoginStatement:
    username: str
    password: str

@dataclass
class AggregationFunction:
    func_name: str
    field: Optional[str]

@dataclass
class AggregateStatement:
    collection: str
    group_by: str
    calculations: List[AggregationFunction]
    conditions: List[Condition]  # Optional WHERE clause before grouping

@dataclass
class GetStatement:
    """
    ``get <collection>`` with optional indented conditions and sorting.

    Example::

        get users
            age > 25
            city = "Chennai"
    """
    collection: str
    conditions: List[Condition] = field(default_factory=list)
    sort: Optional[SortClause] = None
    limit: Optional[int] = None


@dataclass
class InsertStatement:
    """
    ``insert into <collection>`` with indented ``field = value`` assignments.

    Example::

        insert into users
            name = "Gowtham"
            role = "developer"
    """
    collection: str
    document: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateStatement:
    """
    ``update <collection>`` with ``where`` conditions and ``set`` assignments.

    Example::

        update users
            where
                _id = "user-42"
            set
                role = "architect"
    """
    collection: str
    conditions: List[Condition] = field(default_factory=list)
    assignments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeleteStatement:
    """
    ``delete from <collection>`` with optional indented conditions.

    Example::

        delete from users
            age < 18
    """
    collection: str
    conditions: List[Condition] = field(default_factory=list)
