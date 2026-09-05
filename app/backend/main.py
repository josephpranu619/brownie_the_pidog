import json
import shutil
import socket
import subprocess
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from voice import router as voice_router

app = FastAPI(title="Brownie Web API", version="0.1.0")
app.include_router(voice_router)

CPU_TEMP_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
CPU_STAT_PATH = Path("/proc/stat")
BODY_SOCKET_PATH = "/tmp/brownie-body.sock"
MIC_RECORDING_PATH = Path("/tmp/brownie-web-mic.wav")
MIC_REPLAY_PATH = Path("/tmp/brownie-web-mic-mono.wav")
MIC_RECORD_SECONDS = 5
BARK_SOUND_PATH = Path.home() / "pidog" / "sounds" / "single_bark_1.mp3"
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
_music_player_lock = threading.Lock()
_music_player = None
_mic_replay_lock = threading.RLock()
_mic_replay_process = None


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


def body_command(command, timeout=1.0):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
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


def require_body_response(command, conflict_message=None, timeout=1.0):
    body = body_command(command, timeout=timeout)

    if body is None:
        raise HTTPException(status_code=503, detail="Brownie body controller unavailable")

    if not body.get("ok"):
        raise HTTPException(
            status_code=409,
            detail=conflict_message or body.get("error") or "Brownie control request rejected",
        )

    return body


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


def play_bark_sound():
    global _music_player

    if not BARK_SOUND_PATH.exists():
        raise HTTPException(status_code=503, detail="Brownie bark sound file not found")

    try:
        from robot_hat import Music

        with _music_player_lock:
            if _music_player is None:
                _music_player = Music()
            _music_player.sound_play_threading(str(BARK_SOUND_PATH), volume=80)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Brownie speaker unavailable: {exc}") from exc


def record_microphone_clip():
    try:
        MIC_RECORDING_PATH.unlink(missing_ok=True)
        MIC_REPLAY_PATH.unlink(missing_ok=True)
    except OSError:
        pass

    if shutil.which("parecord"):
        command = [
            "timeout",
            "--signal=INT",
            f"{MIC_RECORD_SECONDS}s",
            "parecord",
            "--device=brownie_mic_boosted",
            "--file-format=wav",
            "--format=s16le",
            "--rate=48000",
            "--channels=2",
            str(MIC_RECORDING_PATH),
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=MIC_RECORD_SECONDS + 3,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=503, detail="Microphone recording did not finish") from exc

        if result.returncode not in {0, 124, 130}:
            detail = result.stderr.strip() or "parecord failed"
            raise HTTPException(status_code=503, detail=f"Microphone recording failed: {detail}")

    elif shutil.which("arecord"):
        command = [
            "arecord",
            "-D",
            "pulse",
            "-f",
            "S16_LE",
            "-r",
            "48000",
            "-c",
            "2",
            "-d",
            str(MIC_RECORD_SECONDS),
            str(MIC_RECORDING_PATH),
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=MIC_RECORD_SECONDS + 3,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "arecord failed"
            raise HTTPException(status_code=503, detail=f"Microphone recording failed: {detail}")

    else:
        raise HTTPException(status_code=503, detail="No microphone recording utility is installed")

    try:
        size = MIC_RECORDING_PATH.stat().st_size
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Microphone recording file was not created") from exc

    if size <= 44:
        raise HTTPException(status_code=503, detail="Microphone recording was empty")

    return size


def start_microphone_replay():
    global _mic_replay_process

    if not MIC_RECORDING_PATH.exists() or MIC_RECORDING_PATH.stat().st_size <= 44:
        raise HTTPException(status_code=409, detail="Record a microphone clip before replaying")

    if not shutil.which("sox"):
        raise HTTPException(status_code=503, detail="sox is required for microphone replay")
    if not shutil.which("aplay"):
        raise HTTPException(status_code=503, detail="aplay is required for microphone replay")

    with _mic_replay_lock:
        previous = _mic_replay_process
        if previous is not None and previous.poll() is None:
            previous.terminate()
            try:
                previous.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                previous.kill()

        result = subprocess.run(
            [
                "sox",
                str(MIC_RECORDING_PATH),
                str(MIC_REPLAY_PATH),
                "remix",
                "1",
                "gain",
                "-n",
                "-3",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "sox failed"
            raise HTTPException(status_code=503, detail=f"Could not prepare microphone replay: {detail}")

        _mic_replay_process = subprocess.Popen(
            ["aplay", "-D", "plughw:1,0", str(MIC_REPLAY_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


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
        "control_mode": body.get("control_mode") if body else None,
    }


@app.get("/api/control")
def get_control_mode():
    body = require_body_response("control-status")
    return {
        "control_mode": body.get("control_mode", "autonomous"),
        "manual_lease_active": body.get("manual_lease_active", False),
        "manual_lease_remaining_s": body.get("manual_lease_remaining_s", 0.0),
    }


@app.post("/api/control/manual/acquire")
def acquire_manual_control():
    lease_id = uuid4().hex
    body = require_body_response(
        f"manual-acquire {lease_id}",
        conflict_message="Manual control is already active on another device",
    )

    return {
        "lease_id": lease_id,
        "control_mode": body.get("control_mode", "manual"),
        "manual_lease_remaining_s": body.get("manual_lease_remaining_s", 0.0),
    }


@app.post("/api/control/manual/heartbeat")
def heartbeat_manual_control(lease_id: str):
    body = require_body_response(
        f"manual-heartbeat {lease_id}",
        conflict_message="Manual control lease expired or belongs to another device",
    )

    return {
        "control_mode": body.get("control_mode", "manual"),
        "manual_lease_remaining_s": body.get("manual_lease_remaining_s", 0.0),
    }


@app.post("/api/control/manual/release")
def release_manual_control(lease_id: str):
    body = require_body_response(
        f"manual-release {lease_id}",
        conflict_message="Manual control lease belongs to another device",
    )

    return {
        "control_mode": body.get("control_mode", "autonomous"),
        "manual_lease_remaining_s": body.get("manual_lease_remaining_s", 0.0),
    }


@app.post("/api/posture/stand")
def posture_stand(lease_id: str):
    body = require_body_response(
        f"stand {lease_id}",
        conflict_message="Stand requires this device to own Manual Control",
        timeout=15.0,
    )
    return {
        "pose": body.get("pose", "stand"),
        "message": body.get("message", "Stand requested"),
    }


@app.post("/api/posture/sit")
def posture_sit(lease_id: str):
    body = require_body_response(
        f"sit {lease_id}",
        conflict_message="Sit requires this device to own Manual Control",
        timeout=15.0,
    )
    return {
        "pose": body.get("pose", "sit"),
        "message": body.get("message", "Sit requested"),
    }


@app.post("/api/posture/lie")
def posture_lie(lease_id: str):
    body = require_body_response(
        f"lie {lease_id}",
        conflict_message="Lie requires this device to own Manual Control",
        timeout=15.0,
    )
    return {
        "pose": body.get("pose", "lie"),
        "message": body.get("message", "Lie requested"),
    }


@app.post("/api/motion/body")
def move_body(direction: str, lease_id: str, speed: int = 80):
    if direction not in {"up", "down", "left", "right"}:
        raise HTTPException(status_code=400, detail="Unsupported body direction")

    if not 30 <= speed <= 100:
        raise HTTPException(status_code=400, detail="Movement speed must be between 30 and 100")

    body = require_body_response(
        f"move {lease_id} {direction} {speed}",
        timeout=2.0,
    )

    return {
        "pose": body.get("pose", "stand"),
        "direction": body.get("direction", direction),
        "speed": body.get("speed", speed),
        "message": body.get("message", "Body movement requested"),
    }


@app.post("/api/motion/stop")
def stop_motion():
    body = require_body_response("stop", timeout=2.0)
    return {
        "pose": body.get("pose"),
        "message": body.get("message", "Stop requested"),
    }


@app.get("/api/distance")
def get_distance():
    body = body_command("distance")

    if not body or not body.get("ok"):
        raise HTTPException(status_code=503, detail="Distance sensor unavailable")

    return {
        "distance_cm": body.get("distance_cm"),
    }


@app.post("/api/accessories/sound/bark")
def bark_sound():
    play_bark_sound()
    return {"ok": True, "message": "Bark played"}


@app.get("/api/accessories/mic/status")
def microphone_status():
    available = MIC_RECORDING_PATH.exists() and MIC_RECORDING_PATH.stat().st_size > 44
    return {
        "recording_available": available,
        "temporary": True,
        "record_seconds": MIC_RECORD_SECONDS,
        "bytes": MIC_RECORDING_PATH.stat().st_size if available else 0,
    }


@app.post("/api/accessories/mic/record")
def microphone_record():
    size = record_microphone_clip()
    return {
        "ok": True,
        "recording_available": True,
        "temporary": True,
        "record_seconds": MIC_RECORD_SECONDS,
        "bytes": size,
        "message": f"Recorded {MIC_RECORD_SECONDS} second microphone clip",
    }


@app.post("/api/accessories/mic/replay")
def microphone_replay():
    start_microphone_replay()
    return {"ok": True, "message": "Microphone replay started"}


@app.post("/api/accessories/led/loading")
def led_loading():
    body = require_body_response(
        "led loading",
        conflict_message="Initialize Brownie's body hardware before using the LED pattern",
        timeout=2.0,
    )
    return {
        "led_mode": body.get("led_mode", "loading"),
        "message": body.get("message", "LED loading pattern enabled"),
    }


@app.post("/api/accessories/led/off")
def led_off():
    body = require_body_response(
        "led off",
        conflict_message="Initialize Brownie's body hardware before using LED control",
        timeout=2.0,
    )
    return {
        "led_mode": body.get("led_mode", "off"),
        "message": body.get("message", "LEDs turned off"),
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
