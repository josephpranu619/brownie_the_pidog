import os
import signal
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/behaviors", tags=["behaviors"])

PIDOG_DIR = Path.home() / "pidog"
EXAMPLES_DIR = PIDOG_DIR / "examples"
BODY_SERVICE = "brownie-bodyd.service"
BEHAVIOR_LOG_PATH = Path("/tmp/brownie-behavior.log")

BEHAVIORS = {
    "wake-up": "1_wake_up.py",
    "patrol": "3_patrol.py",
    "response": "4_response.py",
    "rest": "5_rest.py",
    "be-picked-up": "6_be_picked_up.py",
    "face-track": "7_face_track.py",
    "push-up": "8_pushup.py",
    "howling": "9_howling.py",
    "balance": "10_balance.py",
    "ball-track": "13_ball_track.py",
}

TERMINAL_ONLY = {
    "function-demonstration": "2_function_demonstration.py",
    "keyboard-control": "11_keyboard_control.py",
}

_behavior_lock = threading.RLock()
_behavior_process = None
_behavior_name = None
_behavior_log = None


def _systemctl(action):
    try:
        result = subprocess.run(
            ["systemctl", "--user", action, BODY_SERVICE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not {action} {BODY_SERVICE}: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or f"systemctl {action} failed"
        raise RuntimeError(detail)


def _close_behavior_log():
    global _behavior_log
    handle = _behavior_log
    _behavior_log = None
    if handle is not None:
        try:
            handle.close()
        except OSError:
            pass


def _restore_body_controller():
    try:
        _systemctl("start")
    except RuntimeError as exc:
        print(f"BEHAVIOR RESTORE ERROR: {exc}", flush=True)


def _monitor_behavior(process):
    global _behavior_process, _behavior_name

    process.wait()

    with _behavior_lock:
        if _behavior_process is process:
            finished_name = _behavior_name
            _behavior_process = None
            _behavior_name = None
            _close_behavior_log()
        else:
            finished_name = None

    if finished_name is not None:
        print(f"BEHAVIOR EXIT: {finished_name}", flush=True)
        _restore_body_controller()


def _active_behavior_locked():
    global _behavior_process, _behavior_name

    process = _behavior_process
    if process is None:
        return None, None

    if process.poll() is None:
        return _behavior_name, process

    _behavior_process = None
    _behavior_name = None
    _close_behavior_log()
    return None, None


def behavior_status():
    with _behavior_lock:
        name, process = _active_behavior_locked()
        return {
            "running": process is not None,
            "behavior": name,
            "pid": process.pid if process is not None else None,
        }


def start_behavior(name):
    global _behavior_process, _behavior_name, _behavior_log

    if name in TERMINAL_ONLY:
        raise HTTPException(
            status_code=409,
            detail="This behavior needs an interactive terminal and is available through brownie-hub.",
        )

    filename = BEHAVIORS.get(name)
    if filename is None:
        raise HTTPException(status_code=404, detail="Unknown Brownie behavior")

    script = EXAMPLES_DIR / filename
    if not script.exists():
        raise HTTPException(status_code=503, detail=f"Behavior script is missing: {filename}")

    with _behavior_lock:
        active_name, active_process = _active_behavior_locked()
        if active_process is not None:
            raise HTTPException(
                status_code=409,
                detail=f"{active_name} is already running. Stop it before starting another behavior.",
            )

    try:
        _systemctl("stop")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Could not hand off PiDog hardware: {exc}") from exc

    try:
        log_handle = BEHAVIOR_LOG_PATH.open("a", buffering=1)
        process = subprocess.Popen(
            ["python3", str(script)],
            cwd=PIDOG_DIR,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as exc:
        try:
            log_handle.close()
        except Exception:
            pass
        _restore_body_controller()
        raise HTTPException(status_code=503, detail=f"Could not start behavior: {exc}") from exc

    with _behavior_lock:
        _behavior_process = process
        _behavior_name = name
        _behavior_log = log_handle

    threading.Thread(
        target=_monitor_behavior,
        args=(process,),
        name=f"brownie-behavior-{name}",
        daemon=True,
    ).start()

    print(f"BEHAVIOR START: {name} pid={process.pid}", flush=True)
    return {
        "running": True,
        "behavior": name,
        "pid": process.pid,
        "message": f"{name} started",
    }


def stop_behavior():
    with _behavior_lock:
        name, process = _active_behavior_locked()

    if process is None:
        _restore_body_controller()
        return {
            "running": False,
            "behavior": None,
            "message": "No behavior was running",
        }

    try:
        os.killpg(process.pid, signal.SIGINT)
    except (ProcessLookupError, PermissionError):
        pass

    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            process.wait(timeout=2)

    _restore_body_controller()
    return {
        "running": False,
        "behavior": None,
        "message": f"{name} stopped",
    }


@router.get("/status")
def get_behavior_status():
    return behavior_status()


@router.post("/{name}/start")
def api_start_behavior(name: str):
    return start_behavior(name)


@router.post("/stop")
def api_stop_behavior():
    return stop_behavior()
