#!/usr/bin/env python3
import importlib
import json
import shutil
import sys
from pathlib import Path

EXPECTED_DIRS = [
    Path.home() / "pidog",
    Path.home() / "robot-hat",
    Path.home() / "vilib",
]


def main():
    result = {
        "python": sys.executable,
        "expected_dirs": {str(p): p.exists() for p in EXPECTED_DIRS},
        "pidog_importable": False,
        "pidog_module": None,
        "pidog_class_available": False,
        "import_error": None,
        "tools": {
            cmd: bool(shutil.which(cmd))
            for cmd in ["espeak", "pico2wave", "aplay"]
        },
    }

    try:
        module = importlib.import_module("pidog")
        result["pidog_importable"] = True
        result["pidog_module"] = getattr(module, "__file__", None)
        result["pidog_class_available"] = getattr(module, "Pidog", None) is not None
    except Exception as exc:
        result["import_error"] = str(exc)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
