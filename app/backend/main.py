from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="Brownie Web API", version="0.1.0")

CPU_TEMP_PATH = Path("/sys/class/thermal/thermal_zone0/temp")


def read_cpu_temp_c():
    try:
        millidegrees = int(CPU_TEMP_PATH.read_text().strip())
        return round(millidegrees / 1000, 1)
    except (OSError, ValueError):
        return None


@app.get("/api/status")
def get_status():
    return {
        "online": True,
        "cpu_temp_c": read_cpu_temp_c(),
    }
