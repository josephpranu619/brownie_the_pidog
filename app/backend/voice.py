import os
import shutil
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from robot_hat import Music

router = APIRouter(prefix="/api/voice", tags=["voice"])

SOUND_DIR = Path.home() / "pidog" / "sounds"
RECORDINGS_ROOT = Path.home() / ".local" / "share" / "brownie" / "recordings"
RECENT_DIR = RECORDINGS_ROOT / "recent"
SAVED_DIR = RECORDINGS_ROOT / "saved"
REPLAY_PATH = Path("/tmp/brownie-voice-replay.wav")
RECENT_MAX_FILES = 10
RECENT_MAX_BYTES = 100 * 1024 * 1024
BROWNIE_RECORD_MAX_SECONDS = 180
DEVICE_RECORD_MAX_SECONDS = 180
DEVICE_UPLOAD_MAX_BYTES = 25 * 1024 * 1024
ALLOWED_SOUND_SUFFIXES = {".mp3", ".wav"}
DEVICE_AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}

_player_lock = threading.Lock()
_player = None
_replay_lock = threading.RLock()
_replay_process = None
_record_lock = threading.RLock()
_record_process = None
_record_temp_path = None
_record_final_path = None
_record_started_monotonic = None
_record_started_at = None


def ensure_recording_dirs():
    RECENT_DIR.mkdir(parents=True, exist_ok=True)
    SAVED_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_recent():
    ensure_recording_dirs()
    files = sorted(
        (path for path in RECENT_DIR.iterdir() if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )

    total_bytes = sum(path.stat().st_size for path in files)
    while files and (len(files) > RECENT_MAX_FILES or total_bytes > RECENT_MAX_BYTES):
        oldest = files.pop(0)
        try:
            size = oldest.stat().st_size
            oldest.unlink()
            total_bytes -= size
        except OSError:
            pass


def sound_path(name: str):
    if not name or Path(name).name != name:
        raise HTTPException(status_code=400, detail="Invalid default sound name")

    path = SOUND_DIR / name
    if path.suffix.lower() not in ALLOWED_SOUND_SUFFIXES or not path.is_file():
        raise HTTPException(status_code=404, detail="Default sound not found")
    return path


def audio_media_type(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".wav":
        return "audio/wav"
    return "application/octet-stream"


def recording_path(recording_id: str):
    parts = recording_id.split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid recording id")

    bucket, filename = parts
    if bucket not in {"recent", "saved"} or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid recording id")

    root = RECENT_DIR if bucket == "recent" else SAVED_DIR
    path = root / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")
    return bucket, path


def source_for_filename(filename: str):
    if filename.startswith("brownie_"):
        return "brownie"
    if filename.startswith("device_"):
        return "device"
    return "unknown"


def duration_seconds(path: Path):
    if not shutil.which("soxi"):
        return None
    try:
        result = subprocess.run(
            ["soxi", "-D", str(path)],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if result.returncode != 0:
            return None
        return round(float(result.stdout.strip()), 1)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def recording_info(bucket: str, path: Path):
    stat = path.stat()
    return {
        "id": f"{bucket}/{path.name}",
        "name": path.name,
        "bucket": bucket,
        "saved": bucket == "saved",
        "source": source_for_filename(path.name),
        "bytes": stat.st_size,
        "duration_seconds": duration_seconds(path),
        "created_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
        "preview_url": f"/api/voice/recordings/file/{bucket}/{path.name}",
    }


def list_recordings():
    ensure_recording_dirs()
    cleanup_recent()
    result = []
    for bucket, root in (("recent", RECENT_DIR), ("saved", SAVED_DIR)):
        for path in root.iterdir():
            if path.is_file():
                result.append(recording_info(bucket, path))
    result.sort(key=lambda item: item["created_at"], reverse=True)
    return result


def play_pidog_sound(name: str, volume: int):
    global _player
    path = sound_path(name)
    with _player_lock:
        if _player is None:
            _player = Music()
        _player.sound_play_threading(str(path), volume=volume)


def _finalize_recording_locked():
    global _record_process, _record_temp_path, _record_final_path
    global _record_started_monotonic, _record_started_at

    temp_path = _record_temp_path
    final_path = _record_final_path

    _record_process = None
    _record_temp_path = None
    _record_final_path = None
    _record_started_monotonic = None
    _record_started_at = None

    if temp_path is None or final_path is None:
        return None

    if not temp_path.exists() or temp_path.stat().st_size <= 44:
        temp_path.unlink(missing_ok=True)
        return None

    ensure_recording_dirs()
    shutil.move(str(temp_path), str(final_path))
    cleanup_recent()
    return recording_info("recent", final_path)


def _refresh_recording_process_locked():
    if _record_process is not None and _record_process.poll() is not None:
        return _finalize_recording_locked()
    return None


def start_brownie_recording():
    global _record_process, _record_temp_path, _record_final_path
    global _record_started_monotonic, _record_started_at

    with _record_lock:
        _refresh_recording_process_locked()
        if _record_process is not None and _record_process.poll() is None:
            raise HTTPException(status_code=409, detail="Brownie microphone is already recording")

        ensure_recording_dirs()
        token = uuid4().hex[:6]
        filename = f"brownie_{datetime.now().strftime('%Y%m%d-%H%M%S')}_{token}.wav"
        temp_path = Path(f"/tmp/brownie-voice-recording-{token}.wav")
        final_path = RECENT_DIR / filename
        temp_path.unlink(missing_ok=True)

        if shutil.which("parecord"):
            recorder = [
                "parecord",
                "--device=brownie_mic_boosted",
                "--file-format=wav",
                "--format=s16le",
                "--rate=48000",
                "--channels=2",
                str(temp_path),
            ]
        elif shutil.which("arecord"):
            recorder = [
                "arecord",
                "-D",
                "pulse",
                "-f",
                "S16_LE",
                "-r",
                "48000",
                "-c",
                "2",
                str(temp_path),
            ]
        else:
            raise HTTPException(status_code=503, detail="No microphone recording utility is installed")

        _record_process = subprocess.Popen(
            [
                "timeout",
                "--signal=INT",
                "--kill-after=2s",
                f"{BROWNIE_RECORD_MAX_SECONDS}s",
                *recorder,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _record_temp_path = temp_path
        _record_final_path = final_path
        _record_started_monotonic = time.monotonic()
        _record_started_at = datetime.now().astimezone().isoformat(timespec="seconds")

        return {
            "active": True,
            "started_at": _record_started_at,
            "max_seconds": BROWNIE_RECORD_MAX_SECONDS,
        }


def stop_brownie_recording():
    with _record_lock:
        _refresh_recording_process_locked()
        if _record_process is None:
            raise HTTPException(status_code=409, detail="Brownie microphone is not recording")

        process = _record_process
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass

            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=1.0)

        item = _finalize_recording_locked()
        if item is None:
            raise HTTPException(status_code=503, detail="Brownie microphone recording was empty")
        return item


def recording_status():
    with _record_lock:
        completed = _refresh_recording_process_locked()
        if _record_process is None:
            return {
                "active": False,
                "elapsed_seconds": 0,
                "max_seconds": BROWNIE_RECORD_MAX_SECONDS,
                "completed_recording": completed,
            }

        elapsed = 0
        if _record_started_monotonic is not None:
            elapsed = min(
                BROWNIE_RECORD_MAX_SECONDS,
                max(0, int(time.monotonic() - _record_started_monotonic)),
            )
        return {
            "active": True,
            "elapsed_seconds": elapsed,
            "max_seconds": BROWNIE_RECORD_MAX_SECONDS,
            "started_at": _record_started_at,
        }


async def save_device_recording(request: Request):
    if not shutil.which("ffmpeg"):
        raise HTTPException(status_code=503, detail="ffmpeg is required for device microphone uploads")

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    suffix = DEVICE_AUDIO_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=415, detail=f"Unsupported device audio type: {content_type or 'unknown'}")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > DEVICE_UPLOAD_MAX_BYTES:
                raise HTTPException(status_code=413, detail="Device microphone upload is too large")
        except ValueError:
            pass

    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Device microphone upload was empty")
    if len(payload) > DEVICE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Device microphone upload is too large")

    ensure_recording_dirs()
    token = uuid4().hex[:6]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    input_path = Path(f"/tmp/brownie-device-upload-{token}{suffix}")
    output_path = RECENT_DIR / f"device_{timestamp}_{token}.wav"

    try:
        input_path.write_bytes(payload)
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(input_path),
                "-t",
                str(DEVICE_RECORD_MAX_SECONDS),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=45.0,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "ffmpeg failed"
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail=f"Could not prepare device recording: {detail}")

        if not output_path.exists() or output_path.stat().st_size <= 44:
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail="Device microphone recording was empty")

        cleanup_recent()
        return recording_info("recent", output_path)
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Device recording conversion timed out") from exc
    finally:
        input_path.unlink(missing_ok=True)


def start_recording_playback(path: Path, volume: int):
    global _replay_process

    if not shutil.which("sox"):
        raise HTTPException(status_code=503, detail="sox is required for recording playback")
    if not shutil.which("aplay"):
        raise HTTPException(status_code=503, detail="aplay is required for recording playback")
    if not shutil.which("pasuspender"):
        raise HTTPException(status_code=503, detail="pasuspender is required for Robot HAT playback")

    volume_factor = max(0.0, min(1.0, volume / 100.0))

    with _replay_lock:
        previous = _replay_process
        if previous is not None and previous.poll() is None:
            previous.terminate()
            try:
                previous.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                previous.kill()

        REPLAY_PATH.unlink(missing_ok=True)
        result = subprocess.run(
            [
                "sox",
                "-v",
                f"{volume_factor:.2f}",
                str(path),
                str(REPLAY_PATH),
                "remix",
                "1",
                "gain",
                "-n",
                "-3",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=4.0,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "sox failed"
            raise HTTPException(status_code=503, detail=f"Could not prepare recording playback: {detail}")

        process = subprocess.Popen(
            ["pasuspender", "--", "aplay", "-D", "plughw:1,0", str(REPLAY_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.15)
        if process.poll() not in {None, 0}:
            detail = process.stderr.read().strip() if process.stderr is not None else "aplay failed"
            raise HTTPException(status_code=503, detail=f"Brownie speaker playback failed: {detail or 'aplay failed'}")

        _replay_process = process


@router.get("/sounds")
def get_sounds():
    if not SOUND_DIR.is_dir():
        return {"sounds": []}

    sounds = sorted(
        path.name
        for path in SOUND_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_SOUND_SUFFIXES
    )
    return {"sounds": sounds}


@router.get("/sounds/file/{name}")
def get_sound_file(name: str):
    path = sound_path(name)
    return FileResponse(path, media_type=audio_media_type(path))


@router.post("/sounds/play")
def play_sound(name: str, volume: int = 80):
    if not 0 <= volume <= 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    play_pidog_sound(name, volume)
    return {"ok": True, "message": f"Playing {name}", "volume": volume}


@router.get("/recordings")
def get_recordings():
    recordings = list_recordings()
    recent_bytes = sum(item["bytes"] for item in recordings if not item["saved"])
    return {
        "recordings": recordings,
        "recent_policy": {
            "max_files": RECENT_MAX_FILES,
            "max_bytes": RECENT_MAX_BYTES,
            "current_bytes": recent_bytes,
        },
    }


@router.get("/recordings/record-status")
def get_recording_status():
    return recording_status()


@router.post("/recordings/record-brownie/start")
def start_recording_from_brownie():
    state = start_brownie_recording()
    return {"ok": True, **state, "message": "Brownie microphone recording started"}


@router.post("/recordings/record-brownie/stop")
def stop_recording_from_brownie():
    item = stop_brownie_recording()
    return {"ok": True, "recording": item, "message": "Brownie microphone recording stopped"}


@router.post("/recordings/upload-device")
async def upload_device_recording(request: Request):
    item = await save_device_recording(request)
    return {"ok": True, "recording": item, "message": "Device microphone recording saved to Recent"}


@router.post("/recordings/play")
def play_recording(recording_id: str, volume: int = 80):
    if not 0 <= volume <= 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    _, path = recording_path(recording_id)
    start_recording_playback(path, volume)
    return {"ok": True, "message": f"Playing {path.name} on Brownie", "volume": volume}


@router.post("/recordings/keep")
def keep_recording(recording_id: str):
    bucket, path = recording_path(recording_id)
    if bucket == "saved":
        return {"ok": True, "recording": recording_info("saved", path), "message": "Recording is already saved"}

    ensure_recording_dirs()
    destination = SAVED_DIR / path.name
    if destination.exists():
        destination = SAVED_DIR / f"{path.stem}_{uuid4().hex[:6]}{path.suffix}"
    shutil.move(str(path), str(destination))
    return {"ok": True, "recording": recording_info("saved", destination), "message": "Recording kept in Saved"}


@router.delete("/recordings")
def delete_recording(recording_id: str):
    _, path = recording_path(recording_id)
    name = path.name
    path.unlink()
    return {"ok": True, "message": f"Deleted {name}"}


@router.get("/recordings/file/{bucket}/{filename}")
def get_recording_file(bucket: str, filename: str):
    _, path = recording_path(f"{bucket}/{filename}")
    return FileResponse(path, media_type=audio_media_type(path))
