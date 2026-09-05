"""Minimal FastAPI-side bridge to Brownie's system Robot HAT audio environment.

The web backend runs in its own virtualenv, while the working robot_hat package is
installed for Brownie's system Python.  Keep hardware/audio dependencies out of
the web virtualenv and launch playback with /usr/bin/python3 instead.

Only the tiny Music surface currently used by app/backend/main.py is exposed here.
"""

import subprocess


SYSTEM_PYTHON = "/usr/bin/python3"


class Music:
    """Compatibility bridge for Robot HAT sound-effect playback."""

    def sound_play_threading(self, filename, volume=None):
        volume_arg = "None" if volume is None else str(int(volume))
        code = (
            "from robot_hat import Music; "
            "player = Music(); "
            f"player.sound_play({filename!r}, volume={volume_arg})"
        )

        # Run outside the repo/app directory so system Python resolves the real
        # robot_hat package rather than this FastAPI compatibility module.
        subprocess.Popen(
            [SYSTEM_PYTHON, "-c", code],
            cwd="/tmp",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
