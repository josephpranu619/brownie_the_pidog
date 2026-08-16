#!/usr/bin/env python3
import argparse
import json
import sys

from pidog.rgb_strip import RGBStrip

COLOR_MAP = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 255),
    "pink": (255, 0, 128),
    "cyan": (0, 255, 255),
    "white": (255, 255, 255),
    "orange": (255, 128, 0),
    "black": (0, 0, 0),
    "off": (0, 0, 0),
}

LIGHT_MODE_MAP = {
    "off": ("monochromatic", (0, 0, 0), 1.0, 0.0),
    "breath": ("breath", None, 1.0, 0.8),
    "listen": ("listen", None, 0.6, 0.8),
    "boom": ("boom", None, 1.0, 0.8),
    "solid": ("monochromatic", None, 1.0, 0.8),
}


def parse_color(value):
    value = value.strip().lower()
    if value in COLOR_MAP:
        return COLOR_MAP[value]
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 6:
        try:
            return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        "Color must be a known name or hex like #00aaff"
    )


def cmd_status(_args):
    print(json.dumps({
        "python_module": "pidog.rgb_strip.RGBStrip",
        "state": "ready",
    }, indent=2))


def cmd_light(args):
    if not args.confirm_light:
        print(
            "REFUSED: RGB actuation requires --confirm-light after an explicit user request.",
            file=sys.stderr,
        )
        return 2

    strip = RGBStrip(0x74, 11)

    try:
        mode_name, default_color, default_bps, default_brightness = (
            LIGHT_MODE_MAP[args.mode]
        )

        color = default_color if default_color is not None else args.color
        bps = args.bps if args.bps is not None else default_bps
        brightness = (
            args.brightness
            if args.brightness is not None
            else default_brightness
        )

        if mode_name == "monochromatic":
            rgb = [
                max(0, min(255, int(c * brightness)))
                for c in color
            ]
            frame = [rgb[:] for _ in range(strip.light_num)]

            for _ in range(max(args.frames, 1)):
                strip.display(frame)
        else:
            strip.set_mode(
                mode_name,
                color=color,
                bps=bps,
                brightness=brightness,
            )

            for _ in range(max(args.frames, 1)):
                strip.show()

        print(json.dumps({
            "ok": True,
            "mode": args.mode,
            "color": list(color),
            "brightness": brightness,
            "frames": args.frames,
        }, indent=2))

    finally:
        try:
            off = [[0, 0, 0] for _ in range(strip.light_num)]
            strip.display(off)
            strip.close()
        except Exception:
            pass

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Brownie guarded direct RGB controller"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("light")
    p.add_argument(
        "mode",
        choices=["off", "breath", "listen", "boom", "solid"],
    )
    p.add_argument(
        "--color",
        type=parse_color,
        default=COLOR_MAP["white"],
    )
    p.add_argument("--bps", type=float)
    p.add_argument("--brightness", type=float)
    p.add_argument("--frames", type=int, default=30)
    p.add_argument("--confirm-light", action="store_true")
    p.set_defaults(func=cmd_light)

    args = parser.parse_args()
    result = args.func(args)

    if isinstance(result, int):
        raise SystemExit(result)


if __name__ == "__main__":
    main()
