#!/usr/bin/env python3

import argparse
import socket
import sys

SOCKET_PATH = "/tmp/brownie-body.sock"

ALLOWED_ACTIONS = {
    "stand",
    "sit",
}


def send_body_command(action):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        sock.connect(SOCKET_PATH)
        sock.sendall(action.encode())
        return sock.recv(4096).decode().strip()

    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(
        description="Brownie guarded persistent-body action helper"
    )

    parser.add_argument(
        "action",
        choices=sorted(ALLOWED_ACTIONS),
    )

    parser.add_argument(
        "--confirm-motion",
        action="store_true",
        help="Required acknowledgement that servo movement was explicitly requested",
    )

    args = parser.parse_args()

    if not args.confirm_motion:
        print(
            "REFUSED: servo movement requires --confirm-motion after an explicit user request.",
            file=sys.stderr,
        )
        return 2

    try:
        response = send_body_command(args.action)

    except FileNotFoundError:
        print(
            "ERROR: Brownie body controller is not running.",
            file=sys.stderr,
        )
        return 1

    except ConnectionRefusedError:
        print(
            "ERROR: Brownie body controller socket is unavailable.",
            file=sys.stderr,
        )
        return 1

    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
