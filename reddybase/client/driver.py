"""
ReddyBase Official Python SDK
=============================

Programmatic driver for connecting to SreeBase servers.
Provides a clean Pythonic API that compiles to SreeBase bracketless syntax.
"""
import re
import socket
import struct
import json
from typing import Any, Dict, List, Optional

HEADER_FMT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# Only allow safe identifiers: alphanumeric, underscores, dots (for system collections)
_SAFE_IDENT = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.]*\Z')

def _escape_string(val: str) -> str:
    """Escape special characters to prevent query injection."""
    return val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

def _validate_identifier(name: str, label: str = "identifier") -> None:
    """Reject identifiers that could inject newlines or break query structure."""
    if not name or not _SAFE_IDENT.match(name):
        raise ReddyBaseError(f"Invalid {label}: {name!r}. Must be alphanumeric/underscores.")

class ReddyBaseError(Exception):
    """Exception raised for ReddyBase driver or server errors."""
    pass

class Collection:
    def __init__(self, client, name: str):
        _validate_identifier(name, "collection name")
        self.client = client
        self.name = name

    def _format_literal(self, val: Any) -> str:
        if isinstance(val, str):
            return f'"{_escape_string(val)}"'
        elif isinstance(val, bool):
            return 'true' if val else 'false'
        elif val is None:
            return 'null'
        else:
            return str(val)

    def _format_condition(self, k: str, v: Any) -> str:
        _validate_identifier(k, "field name")
        if isinstance(v, str):
            v_stripped = v.strip()
            for op in ['>=', '<=', '!=', '=', '>', '<']:
                if v_stripped.startswith(op):
                    # Operator explicitly provided in string (e.g. '> 90' or '= "critical"')
                    # The value portion after the operator may contain a string literal;
                    # we pass it through as-is since it's already in query syntax.
                    return f"{k} {v_stripped}"
        return f"{k} = {self._format_literal(v)}"

    def insert(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a document into the collection."""
        lines = [f"insert into {self.name}"]
        for k, v in document.items():
            _validate_identifier(k, "field name")
            lines.append(f"    {k} = {self._format_literal(v)}")
        query = "\n".join(lines) + "\n"
        return self.client.raw_query(query)

    def get(self, where: Optional[Dict[str, Any]] = None, sort: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch documents from the collection with optional filters."""
        lines = [f"get {self.name}"]
        if where:
            for k, v in where.items():
                lines.append(f"    {self._format_condition(k, v)}")
        if sort:
            _validate_identifier(sort.split()[0], "sort field")
            lines.append(f"    sort by {sort}")
        if limit:
            lines.append(f"    limit {int(limit)}")
        query = "\n".join(lines) + "\n"
        return self.client.raw_query(query)

    def update(self, where: Dict[str, Any], set_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update documents matching the `where` condition with `set_fields`."""
        lines = [f"update {self.name}"]
        if where:
            lines.append("    where")
            for k, v in where.items():
                lines.append(f"        {self._format_condition(k, v)}")
        lines.append("    set")
        for k, v in set_fields.items():
            _validate_identifier(k, "field name")
            lines.append(f"        {k} = {self._format_literal(v)}")
        query = "\n".join(lines) + "\n"
        return self.client.raw_query(query)

    def delete(self, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Delete documents matching the `where` condition."""
        lines = [f"delete from {self.name}"]
        if where:
            for k, v in where.items():
                lines.append(f"    {self._format_condition(k, v)}")
        query = "\n".join(lines) + "\n"
        return self.client.raw_query(query)
        
    def aggregate(self, group_by: str, calculate: List[str], where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run aggregation analytics on the collection."""
        _validate_identifier(group_by, "group_by field")
        for expr in calculate:
            # Allow function calls like "avg(salary)" and "count()"
            if not re.match(r'^[a-zA-Z_]+\([a-zA-Z0-9_]*\)$', expr.strip()):
                raise ReddyBaseError(f"Invalid calculate expression: {expr!r}")
        lines = [f"aggregate {self.name}"]
        if where:
            lines.append("    where")
            for k, v in where.items():
                lines.append(f"        {self._format_condition(k, v)}")
        lines.append(f"    group by {group_by}")
        lines.append(f"    calculate {', '.join(calculate)}")
        query = "\n".join(lines) + "\n"
        return self.client.raw_query(query)


class Client:
    """Main ReddyBase TCP Client."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 6969):
        self.host = host
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.host, self.port))
        
    def login(self, username: str, password: str) -> None:
        """Authenticate the connection."""
        query = f'login {_escape_string(username)} password "{_escape_string(password)}"\n'
        res = self._execute(query)
        if res.get("status") == "error":
            raise ReddyBaseError(f"Login failed: {res.get('message')}")
            
    def collection(self, name: str) -> Collection:
        """Get a Collection reference for ORM operations."""
        return Collection(self, name)

    def raw_query(self, query: str) -> Any:
        """Execute a raw string query against the SreeBase server."""
        return self._execute(query)

    def _execute(self, query: str) -> Any:
        # Encode
        payload = query.encode("utf-8")
        header = struct.pack(HEADER_FMT, len(payload))
        self._sock.sendall(header + payload)
        
        # Decode
        resp_header = self._recv_exactly(HEADER_SIZE)
        if not resp_header:
            raise ConnectionError("Server closed connection.")
        length, = struct.unpack(HEADER_FMT, resp_header)
        
        payload_bytes = self._recv_exactly(length)
        if not payload_bytes:
            raise ConnectionError("Server closed connection during payload read.")
            
        response = json.loads(payload_bytes.decode("utf-8"))
        if response.get("status") == "error":
            raise ReddyBaseError(f"[{response.get('error')}] {response.get('message')}")
            
        return response.get("data", response)

    def _recv_exactly(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = self._sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)
        
    def close(self):
        """Close the socket connection."""
        self._sock.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
