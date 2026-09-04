import json
import socket
import subprocess
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI(title="Brownie Web API", version="0.1.0")

CPU_TEMP_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
CPU_STAT_PATH = Path("/proc/stat")
BODY_SOCKET_PATH = "/tmp/brownie-body.sock"
CAMERA_COMMAND = [
    "rpicam-vid",
    "-n",
    "--codec",
    "mjpeg",
    "--width",
    "1280",
    "--height",
    "720",
    "--framerate",
    "15",
    "-t",
    "0",
    "-o",
    "-",
]

_cpu_sample_lock = threading.Lock()
_previous_cpu_sample = None
_camera_process_lock = threading.RLock()
_camera_process = None


def read_cpu_temp_c():
    try:
        millidegrees = int(CPU_TEMP_PATH.read_text().strip())
        return round(millidegrees / 1000, 1)
    except (OSError, ValueError):
        return None


def read_cpu_counters():
    try:
        fields = CPU_STAT_PATH.read_text().splitlines()[0].split()[1:9]
        values = [int(value) for value in fields]
        total = sum(values)
        idle = values[3] + values[4]
        return total, idle
    except (OSError, ValueError, IndexError):
        return None


def read_cpu_usage_percent():
    global _previous_cpu_sample

    current = read_cpu_counters()
    if current is None:
        return None

    with _cpu_sample_lock:
        previous = _previous_cpu_sample
        _previous_cpu_sample = current

    if previous is None:
        return None

    total_delta = current[0] - previous[0]
    idle_delta = current[1] - previous[1]

    if total_delta <= 0:
        return None

    usage = 100.0 * (1.0 - idle_delta / total_delta)
    return round(max(0.0, min(100.0, usage)), 1)


def approx_battery_percent(voltage):
    if voltage is None:
        return None

    points = [
        (6.00, 0), (6.60, 5), (7.00, 15), (7.20, 30),
        (7.40, 50), (7.60, 65), (7.80, 80), (8.00, 90),
        (8.20, 97), (8.40, 100),
    ]

    if voltage <= points[0][0]:
        return 0
    if voltage >= points[-1][0]:
        return 100

    for (v1, p1), (v2, p2) in zip(points, points[1:]):
        if v1 <= voltage <= v2:
            fraction = (voltage - v1) / (v2 - v1)
            return round(p1 + fraction * (p2 - p1))

    return None


def body_command(command):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            client.connect(BODY_SOCKET_PATH)
            client.sendall((command + "\n").encode())

            chunks = []
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break

        payload = b"".join(chunks).decode().strip()
        return json.loads(payload) if payload else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _terminate_camera_process(process):
    if process is None:
        return

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)

    if process.stdout is not None:
        try:
            process.stdout.close()
        except OSError:
            pass


def start_camera_process():
    """Start one camera encoder, replacing any stale/previous stream process."""
    global _camera_process

    with _camera_process_lock:
        previous = _camera_process
        _camera_process = None

        if previous is not None:
            _terminate_camera_process(previous)

        process = subprocess.Popen(
            CAMERA_COMMAND,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        _camera_process = process
        return process


def stop_camera_process(expected_process=None):
    """Stop the active camera, without letting an old stream kill a newer one."""
    global _camera_process

    with _camera_process_lock:
        process = expected_process if expected_process is not None else _camera_process
        if process is None:
            return False

        if expected_process is None or _camera_process is expected_process:
            _camera_process = None

        _terminate_camera_process(process)
        return True


def camera_mjpeg_stream(process):
    try:
        if process.stdout is None:
            raise RuntimeError("Camera stream stdout unavailable")

        buffer = bytearray()

        while True:
            chunk = process.stdout.read(65536)
            if not chunk:
                break

            buffer.extend(chunk)

            while True:
                start = buffer.find(b"\xff\xd8")
                if start < 0:
                    if len(buffer) > 1:
                        del buffer[:-1]
                    break

                end = buffer.find(b"\xff\xd9", start + 2)
                if end < 0:
                    if start > 0:
                        del buffer[:start]
                    break

                frame = bytes(buffer[start:end + 2])
                del buffer[:end + 2]

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(frame)}\r\n\r\n".encode()
                    + frame
                    + b"\r\n"
                )
    finally:
        stop_camera_process(expected_process=process)


@app.get("/api/system")
def get_system():
    return {
        "online": True,
        "cpu_temp_c": read_cpu_temp_c(),
        "cpu_usage_percent": read_cpu_usage_percent(),
    }


@app.get("/api/status")
def get_status():
    body = body_command("status")
    voltage = body.get("battery_voltage") if body else None

    return {
        "body_controller_online": bool(body and body.get("ok")),
        "battery_voltage": voltage,
        "battery_percent": approx_battery_percent(voltage),
        "pose": body.get("pose") if body else None,
    }


@app.get("/api/distance")
def get_distance():
    body = body_command("distance")

    if not body or not body.get("ok"):
        raise HTTPException(status_code=503, detail="Distance sensor unavailable")

    return {
        "distance_cm": body.get("distance_cm"),
    }


@app.get("/api/camera/stream")
def get_camera_stream():
    process = start_camera_process()

    return StreamingResponse(
        camera_mjpeg_stream(process),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.post("/api/camera/stop")
def stop_camera_stream():
    return {
        "camera_live": False,
        "stopped": stop_camera_process(),
    }
