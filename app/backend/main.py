import json
import socket
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Brownie Web API", version="0.1.0")

CPU_TEMP_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
CPU_STAT_PATH = Path("/proc/stat")
BODY_SOCKET_PATH = "/tmp/brownie-body.sock"

_cpu_sample_lock = threading.Lock()
_previous_cpu_sample = None


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
