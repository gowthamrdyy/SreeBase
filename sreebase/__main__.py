import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog="sreebase",
        description="SreeBase: The Bracketless, Enterprise-Grade NoSQL Database"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)
    
    # ---------------------------------------------------------
    # 1. SERVER SUBCOMMAND
    # ---------------------------------------------------------
    server_parser = subparsers.add_parser("serve", help="Start the SreeBase TCP server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=6969, help="Port to bind to")
    server_parser.add_argument("--data-dir", default="data", help="Directory for storage")
    
    # ---------------------------------------------------------
    # 2. CLIENT SUBCOMMAND
    # ---------------------------------------------------------
    shell_parser = subparsers.add_parser("shell", help="Launch the interactive REPL shell (TCP Client)")
    shell_parser.add_argument("-H", "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    shell_parser.add_argument("-p", "--port", type=int, default=6969, help="Server port (default: 6969)")
    shell_parser.add_argument("-u", "--user", help="Username to login with")

    # ---------------------------------------------------------
    # 3. EMBEDDED LOCAL SUBCOMMAND
    # ---------------------------------------------------------
    local_parser = subparsers.add_parser("local", help="Start an embedded local shell (no server needed)")
    local_parser.add_argument("--data-dir", default="data", help="Directory for storage")
    local_parser.add_argument("-u", "--user", help="Username to login with")
    
    args = parser.parse_args()
    
    if args.command == "serve":
        from sreebase.server.tcp_server import run_server
        run_server(host=args.host, port=args.port, data_dir=args.data_dir)
        
    elif args.command == "shell":
        from sreebase.client.cli import repl
        repl(host=args.host, port=args.port, user=args.user)
        
    elif args.command == "local":
        from sreebase.client.cli import local_repl
        local_repl(data_dir=args.data_dir, user=args.user)

if __name__ == "__main__":
    main()
