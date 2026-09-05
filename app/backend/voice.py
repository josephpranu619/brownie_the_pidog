import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
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
BROWNIE_RECORD_SECONDS = 5
ALLOWED_SOUND_SUFFIXES = {".mp3", ".wav"}

_player_lock = threading.Lock()
_player = None
_replay_lock = threading.RLock()
_replay_process = None


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


def record_brownie_microphone():
    ensure_recording_dirs()
    filename = f"brownie_{datetime.now().strftime('%Y%m%d-%H%M%S')}_{uuid4().hex[:6]}.wav"
    path = RECENT_DIR / filename

    if shutil.which("parecord"):
        command = [
            "timeout",
            "--signal=INT",
            f"{BROWNIE_RECORD_SECONDS}s",
            "parecord",
            "--device=brownie_mic_boosted",
            "--file-format=wav",
            "--format=s16le",
            "--rate=48000",
            "--channels=2",
            str(path),
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=BROWNIE_RECORD_SECONDS + 3,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail="Brownie microphone recording did not finish") from exc

        if result.returncode not in {0, 124, 130}:
            detail = result.stderr.strip() or "parecord failed"
            path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail=f"Brownie microphone recording failed: {detail}")

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
            str(BROWNIE_RECORD_SECONDS),
            str(path),
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=BROWNIE_RECORD_SECONDS + 3,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "arecord failed"
            path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail=f"Brownie microphone recording failed: {detail}")
    else:
        raise HTTPException(status_code=503, detail="No microphone recording utility is installed")

    if not path.exists() or path.stat().st_size <= 44:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Brownie microphone recording was empty")

    cleanup_recent()
    return recording_info("recent", path)


def start_recording_playback(path: Path, volume: int):
    global _replay_process

    if not shutil.which("sox"):
        raise HTTPException(status_code=503, detail="sox is required for recording playback")
    if not shutil.which("aplay"):
        raise HTTPException(status_code=503, detail="aplay is required for recording playback")

    volume_factor = max(0.0, min(1.0, volume / 100.0))

    with _replay_lock:
        previous = _replay_process
        if previous is not None and previous.poll() is None:
            previous.terminate()
            try:
                previous.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                previous.kill()

        result = subprocess.run(
            [
                "sox",
                "-v",
                f"{volume_factor:.2f}",
                str(path),
                str(REPLAY_PATH),
                "remix",
                "1",
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

        _replay_process = subprocess.Popen(
            ["aplay", "-D", "plughw:1,0", str(REPLAY_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


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


@router.post("/recordings/record-brownie")
def record_from_brownie():
    item = record_brownie_microphone()
    return {"ok": True, "recording": item, "message": "Brownie microphone recording saved to Recent"}


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
