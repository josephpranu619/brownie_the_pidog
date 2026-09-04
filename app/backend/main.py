import json
import socket
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Brownie Web API", version="0.1.0")

CPU_TEMP_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
BODY_SOCKET_PATH = "/tmp/brownie-body.sock"


def read_cpu_temp_c():
    try:
        millidegrees = int(CPU_TEMP_PATH.read_text().strip())
        return round(millidegrees / 1000, 1)
    except (OSError, ValueError):
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


@app.get("/api/status")
def get_status():
    body = body_command("status")

    return {
        "online": True,
        "cpu_temp_c": read_cpu_temp_c(),
        "body_controller_online": bool(body and body.get("ok")),
        "battery_voltage": body.get("battery_voltage") if body else None,
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
