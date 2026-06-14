"""
SreeBase Interactive REPL Client.
=================================

Connects to the SreeBase TCP server, accumulates multi-line bracketless queries,
sends them via the length-prefixed protocol, and displays the results with
professional tabular and colored formatting.
"""

import sys
import json
import socket
import struct
import argparse
import getpass

from reddybase.client.driver import ReddyBaseError, _escape_string, _validate_identifier

try:
    import readline  # Adds history and arrow-key support to input() automatically
except ImportError:
    pass  # Windows or systems without readline

HEADER_FMT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

def encode_message(query: str) -> bytes:
    """Encode the query string with a 4-byte length prefix."""
    payload = query.encode("utf-8")
    header = struct.pack(HEADER_FMT, len(payload))
    return header + payload

def decode_message(sock: socket.socket) -> dict:
    """Read a 4-byte length prefix and decode the JSON payload."""
    header = _recv_exactly(sock, HEADER_SIZE)
    if not header:
        raise ConnectionError("Server closed connection.")
    
    length, = struct.unpack(HEADER_FMT, header)
    
    payload_bytes = _recv_exactly(sock, length)
    if not payload_bytes:
        raise ConnectionError("Server closed connection during payload read.")
        
    return json.loads(payload_bytes.decode("utf-8"))

def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from the socket."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def build_login_query(user: str, password: str) -> str:
    """Build a login query with escaped credentials."""
    _validate_identifier(user, "username")
    return f'login {user} password "{_escape_string(password)}"\n'

def print_table(data: list):
    """Prints a list of dictionaries as an ASCII table."""
    if not data:
        print("Empty set\n")
        return
    
    # Extract keys and calculate max widths
    keys = list(data[0].keys())
    col_widths = {k: len(str(k)) for k in keys}
    
    for row in data:
        for k in keys:
            col_widths[k] = max(col_widths[k], len(str(row.get(k, ''))))
            
    # Build format string
    separator = "+" + "+".join("-" * (col_widths[k] + 2) for k in keys) + "+"
    
    # Print Header
    print(separator)
    header = "|" + "|".join(f" {str(k).ljust(col_widths[k])} " for k in keys) + "|"
    print(header)
    print(separator)
    
    # Print Rows
    for row in data:
        row_str = "|" + "|".join(f" {str(row.get(k, '')).ljust(col_widths[k])} " for k in keys) + "|"
        print(row_str)
        
    print(separator)
    print(f"{len(data)} rows in set\n")

def print_pretty_json(data):
    """Prints JSON with basic coloring."""
    formatted = json.dumps(data, indent=2)
    # Very basic colorizer (keys in blue, strings in green)
    colored = formatted.replace('"', '\033[32m"\033[0m')  # Color strings green
    # A bit simplistic, but makes it look nice!
    print(formatted) # Keeping it simple standard print to avoid complex regex colorizing for now. We can colorize later if needed.
    # Actually, let's just print cleanly without ANSI to prevent broken escapes, 
    # but the structure will be very readable.
    print("")

def repl(host: str, port: int, user: str = None):
    """Run the interactive Read-Eval-Print Loop."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
    except ConnectionRefusedError:
        print(f"\033[91mError: Could not connect to SreeBase server at {host}:{port}\033[0m")
        print("Make sure the server is running.")
        sys.exit(1)

    # Handshake / Login
    if user:
        password = getpass.getpass(f"Password for {user}: ")
        try:
            login_query = build_login_query(user, password)
        except ReddyBaseError as e:
            print(f"\033[91mInvalid login input: {e}\033[0m")
            sys.exit(1)
        sock.sendall(encode_message(login_query))
        try:
            resp = decode_message(sock)
            if resp.get("status") == "error":
                print(f"\033[91mAccess denied for user '{user}': {resp.get('message', resp.get('error'))}\033[0m")
                sys.exit(1)
            print(f"Logged in successfully as \033[92m{user}\033[0m.")
        except Exception as e:
            print(f"Failed to login: {e}")
            sys.exit(1)

    print(f"Connected to \033[94mSreeBase\033[0m at {host}:{port}")
    print("Type your query. Submit an empty line to execute.")
    print("Type 'exit' or 'quit' or press Ctrl+D to exit.\n")

    try:
        while True:
            # 1. Accumulate input lines
            try:
                line = input("sreebase> ")
            except EOFError:
                break
                
            if line.strip().lower() in ("exit", "quit", "\\q"):
                break

            lines = [line]
            
            # Multi-line handling
            if line.strip() != "":
                while True:
                    try:
                        next_line = input("      ... ")
                    except EOFError:
                        break
                        
                    if next_line.strip() == "":
                        break
                    lines.append(next_line)

            query = "\n".join(lines) + "\n"
            
            if not query.strip():
                continue

            # 2. Send to server
            try:
                sock.sendall(encode_message(query))
            except (ConnectionError, BrokenPipeError):
                print("\033[91mError: Connection to server lost.\033[0m")
                break

            # 3. Receive and print response
            try:
                response = decode_message(sock)
                if response.get("status") == "error":
                    err_type = response.get('error', 'Error')
                    msg = response.get('message', 'Unknown error')
                    print(f"\033[91m[{err_type}]\033[0m {msg}\n")
                else:
                    data = response.get("data")
                    
                    # Heuristic to detect tabular data vs normal document output
                    is_show_collections = query.strip().lower().startswith("show collections")
                    
                    if is_show_collections and isinstance(data, list):
                        print_table(data)
                    elif isinstance(data, list) and len(data) > 0 and all(isinstance(d, dict) for d in data) and len(data[0].keys()) <= 5 and not any(isinstance(v, (dict, list)) for v in data[0].values()):
                        # Tabular format for flat list of dicts (like aggregate output)
                        print_table(data)
                    else:
                        # Pretty JSON for complex documents
                        print(json.dumps(data, indent=2))
                        print(f"({len(data) if isinstance(data, list) else 1} documents)\n")
                        
            except ConnectionError:
                print("\033[91mError: Connection to server lost while reading response.\033[0m")
                break
            except Exception as e:
                print(f"\033[91mError decoding response: {e}\033[0m")

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="SreeBase Professional CLI Client")
    parser.add_argument("-H", "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=6969, help="Server port (default: 6969)")
    parser.add_argument("-u", "--user", help="Username to login with")
    args = parser.parse_args()
    
    repl(args.host, args.port, args.user)


if __name__ == "__main__":
    main()
