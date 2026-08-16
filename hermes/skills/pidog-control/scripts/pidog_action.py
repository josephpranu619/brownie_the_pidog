#!/usr/bin/env python3
import argparse
import sys

from pidog import Pidog

ACTION_MAP = {
    "stand": "stand",
    "sit": "sit",
    "lie": "lie",
    "wag-tail": "wag_tail",
    "forward": "forward",
    "backward": "backward",
    "turn-left": "turn_left",
    "turn-right": "turn_right",
}


def main():
    parser = argparse.ArgumentParser(description="Brownie PiDog guarded action helper")
    parser.add_argument("action", choices=sorted(ACTION_MAP))
    parser.add_argument("--speed", type=int, default=60)
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

    dog = Pidog()
    try:
        action_name = ACTION_MAP[args.action]
        dog.do_action(action_name, speed=args.speed)
        dog.wait_all_done()
        print(f"action '{args.action}' completed via do_action('{action_name}')")
    finally:
        dog.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
