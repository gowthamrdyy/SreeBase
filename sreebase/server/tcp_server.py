"""
SreeBase TCP Server.
====================

A multi-threaded `socketserver` that handles incoming client connections,
decodes the length-prefixed bracketless queries, executes them against
the core engine, and replies with length-prefixed JSON results.
"""

import json
import struct
import logging
import threading
import socketserver
from typing import Any

from sreebase.query.executor import Executor
from sreebase.errors import SreeBaseError

# Set up simple logging for the server
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(threadName)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("sreebase.server")

# The length-prefix format: 1 unsigned int (4 bytes, big-endian)
HEADER_FMT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# Maximum allowed request payload size (1 MB). Reject anything larger.
MAX_PAYLOAD_SIZE = 1 * 1024 * 1024

# Idle socket timeout in seconds. Drops stale connections.
SOCKET_TIMEOUT = 30

# A global/shared Executor instance for the server lifetime.
# Since the storage engine locks correctly, it is safe to share this
# across multiple request handler threads.
_executor: Executor = None


def encode_message(payload: dict) -> bytes:
    """Encode a dict as JSON, prefixed with a 4-byte length header."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = struct.pack(HEADER_FMT, len(data))
    return header + data


class SreeBaseRequestHandler(socketserver.StreamRequestHandler):
    """
    Handles exactly one TCP connection. `StreamRequestHandler` gives us
    self.rfile and self.wfile which act like standard file objects over the socket.
    """

    def handle(self):
        client_address = f"{self.client_address[0]}:{self.client_address[1]}"
        logger.info(f"Accepted connection from {client_address}")

        # Connection state
        self.role = None
        self.request.settimeout(SOCKET_TIMEOUT)

        try:
            while True:
                # 1. Read the 4-byte length header
                header = self.rfile.read(HEADER_SIZE)
                if not header:
                    # Client closed the connection gracefully
                    break
                if len(header) < HEADER_SIZE:
                    logger.warning(f"Connection torn during header read from {client_address}")
                    break

                length, = struct.unpack(HEADER_FMT, header)

                # Reject oversized payloads before reading them
                if length > MAX_PAYLOAD_SIZE:
                    logger.warning(f"Rejecting oversized payload ({length} bytes) from {client_address}")
                    response = {
                        "status": "error",
                        "error": "PayloadTooLarge",
                        "message": f"Request exceeds maximum size of {MAX_PAYLOAD_SIZE} bytes."
                    }
                    self.wfile.write(encode_message(response))
                    self.wfile.flush()
                    break

                # 2. Read the exact payload length
                payload_bytes = self.rfile.read(length)
                if len(payload_bytes) < length:
                    logger.warning(f"Connection torn during payload read from {client_address}")
                    break

                try:
                    query_text = payload_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    response = {
                        "status": "error",
                        "error": "InvalidEncoding",
                        "message": "Request payload must be valid UTF-8."
                    }
                    self.wfile.write(encode_message(response))
                    self.wfile.flush()
                    continue

                logger.debug(f"Received query from {client_address}: {query_text!r}")

                # 3. Execute the query
                try:
                    result = _executor.execute(query_text, role=self.role)

                    # Intercept login
                    if isinstance(result, dict) and "_internal_login_role" in result:
                        self.role = result.pop("_internal_login_role")

                    response = {"status": "ok", "data": result}
                except SreeBaseError as e:
                    # Catch query parsing/execution errors cleanly to send back to client
                    response = {"status": "error", "error": type(e).__name__, "message": str(e)}
                except Exception as e:
                    # Never leak internal details to the client
                    logger.exception(f"Unexpected error executing query from {client_address}")
                    response = {"status": "error", "error": "InternalServerError", "message": "An internal error occurred."}

                # 4. Send the result back
                self.wfile.write(encode_message(response))
                self.wfile.flush()

        except ConnectionError:
            logger.info(f"Connection reset by {client_address}")
        except Exception as e:
            logger.exception(f"Error handling connection from {client_address}: {e}")
        finally:
            logger.info(f"Closed connection from {client_address}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    Spawns a new thread for each connection.
    ``allow_reuse_address`` lets us restart the server quickly on the same port.
    """
    allow_reuse_address = True
    daemon_threads = True  # Allows the server program to exit even if clients are connected


def run_server(host: str = "127.0.0.1", port: int = 6969, data_dir: str = "data"):
    """
    Start the SreeBase TCP server.
    """
    global _executor
    
    logger.info(f"Initializing SreeBase storage engine at '{data_dir}'...")
    _executor = Executor(data_dir=data_dir)

    server_address = (host, port)
    
    try:
        with ThreadedTCPServer(server_address, SreeBaseRequestHandler) as server:
            BANNER = r"""
\033[92m  ____                 ____                 
 / ___| _ __ ___  ___ | __ )  __ _ ___  ___ 
 \___ \| '__/ _ \/ _ \|  _ \ / _` / __|/ _ \
  ___) | | |  __/  __/| |_) | (_| \__ \  __/
 |____/|_|  \___|\___||____/ \__,_|___/\___|\033[0m
"""
            print(BANNER)
            logger.info(f"SreeBase server listening on tcp://{host}:{port}")
            logger.info("Press Ctrl+C to stop.")
            server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down gracefully...")
    finally:
        _executor.close()
        logger.info("Storage engines closed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SreeBase TCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=6969, help="Port to bind to")
    parser.add_argument("--data-dir", default="data", help="Directory for storage")
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, data_dir=args.data_dir)
