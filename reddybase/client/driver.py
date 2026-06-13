"""
ReddyBase Official Python SDK
=============================

Programmatic driver for connecting to SreeBase servers.
Provides a clean Pythonic API that compiles to SreeBase bracketless syntax.
"""
import socket
import struct
import json
from typing import Any, Dict, List, Optional

HEADER_FMT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

class ReddyBaseError(Exception):
    """Exception raised for ReddyBase driver or server errors."""
    pass

class Collection:
    def __init__(self, client, name: str):
        self.client = client
        self.name = name
        
    def _format_literal(self, val: Any) -> str:
        if isinstance(val, str):
            return f'"{val}"'
        elif isinstance(val, bool):
            return 'true' if val else 'false'
        elif val is None:
            return 'null'
        else:
            return str(val)

    def _format_condition(self, k: str, v: Any) -> str:
        if isinstance(v, str):
            v_stripped = v.strip()
            for op in ['>=', '<=', '!=', '=', '>', '<']:
                if v_stripped.startswith(op):
                    # Operator explicitly provided in string (e.g. '> 90' or '= "critical"')
                    return f"{k} {v_stripped}"
        return f"{k} = {self._format_literal(v)}"

    def insert(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a document into the collection."""
        lines = [f"insert into {self.name}"]
        for k, v in document.items():
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
            lines.append(f"    sort by {sort}")
        if limit:
            lines.append(f"    limit {limit}")
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
        query = f'login {username} password "{password}"\n'
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
