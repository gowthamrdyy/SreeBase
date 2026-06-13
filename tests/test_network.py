"""
Tests for the SreeBase Network Layer (TCP Server & Protocol).
"""

import socket
import time
import threading
import pytest

from sreebase.server.tcp_server import run_server, ThreadedTCPServer
from sreebase.client.cli import encode_message, decode_message


@pytest.fixture
def tcp_server(tmp_path):
    """Run the TCP server in a background thread."""
    data_dir = str(tmp_path / "server_data")
    host = "127.0.0.1"
    port = 6970  # Use a different port for tests
    
    # We must patch run_server slightly for the test to avoid blocking and clean shutdown
    from sreebase.server.tcp_server import SreeBaseRequestHandler, _executor
    import sreebase.server.tcp_server as server_module
    
    server_module._executor = None
    
    server = ThreadedTCPServer((host, port), SreeBaseRequestHandler)
    server_module._executor = server_module.Executor(data_dir=data_dir)
    
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    # Give the server a moment to bind and listen
    time.sleep(0.1)
    
    yield (host, port)
    
    server.shutdown()
    server.server_close()
    if server_module._executor:
        server_module._executor.close()


def test_network_roundtrip(tcp_server):
    host, port = tcp_server
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    try:
        # 0. Authenticate
        sock.sendall(encode_message('create user admin password "secret" role admin\n'))
        resp0 = decode_message(sock)
        assert resp0["status"] == "ok"
        
        sock.sendall(encode_message('login admin password "secret"\n'))
        resp0b = decode_message(sock)
        assert resp0b["status"] == "ok"
        
        # 1. Insert a document
        query1 = 'insert into users\n    name = "NetworkTest"\n'
        sock.sendall(encode_message(query1))
        
        resp1 = decode_message(sock)
        assert resp1["status"] == "ok"
        assert "inserted" in resp1["data"]
        
        # 2. Get the document
        query2 = 'get users\n'
        sock.sendall(encode_message(query2))
        
        resp2 = decode_message(sock)
        assert resp2["status"] == "ok"
        assert len(resp2["data"]) == 1
        assert resp2["data"][0]["name"] == "NetworkTest"
        
        # 3. Test Error Handling (bad syntax)
        query3 = 'insert into\n' # missing collection
        sock.sendall(encode_message(query3))
        
        resp3 = decode_message(sock)
        assert resp3["status"] == "error"
        assert resp3["error"] == "ParserError"
        
    finally:
        sock.close()
