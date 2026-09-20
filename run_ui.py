"""Launcher for GraphPulse-R Dashboard.

Usage:
    python run_ui.py [--port 8000] [--no-browser]
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser

from graphpulse.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphPulse-R Interactive Dashboard")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"

    if not args.no_browser:
        def open_tab():
            time.sleep(0.5)
            print(f"[*] Opening dashboard at {url} ...")
            webbrowser.open(url)

        threading.Thread(target=open_tab, daemon=True).start()

    print(f"[*] Starting GraphPulse-R Dashboard on {url}")
    try:
        run_server(port=args.port, host=args.host)
    except KeyboardInterrupt:
        print("\n[!] Dashboard terminated.")


if __name__ == "__main__":
    main()
