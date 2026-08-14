#!/usr/bin/env python3

import argparse
import importlib.util
import shutil
import subprocess
import sys
import time
from pathlib import Path

PASS = "[PASS]"
WARN = "[WARN]"
FAIL = "[FAIL]"
INFO = "[INFO]"

def run(cmd, timeout=30):
    try:
        p = subprocess.run(
            cmd, text=True, capture_output=True,
            timeout=timeout, check=False
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 999, "", str(e)

def module_check(name):
    try:
        spec = importlib.util.find_spec(name)
        if spec is None:
            print(f"{FAIL} Python module: {name}")
            return False
        print(f"{PASS} Python module: {name}")
        return True
    except Exception as e:
        print(f"{FAIL} Python module {name}: {e}")
        return False

def passive_checks():
    print("=== Brownie / PiDog V2 Diagnostic ===")
    print(f"{INFO} Python {sys.version.split()[0]}")

    gpio = sorted(Path("/dev").glob("gpiochip*"))
    print(f"{PASS if gpio else FAIL} GPIO: " +
          (", ".join(map(str, gpio)) if gpio else "none"))

    i2c = sorted(Path("/dev").glob("i2c-*"))
    print(f"{PASS if i2c else FAIL} I2C devices: " +
          (", ".join(map(str, i2c)) if i2c else "none"))

    if shutil.which("i2cdetect"):
        rc, out, err = run(["i2cdetect", "-y", "1"])
        if rc == 0:
            found = []
            for line in out.splitlines()[1:]:
                for token in line.split()[1:]:
                    if len(token) == 2 and token != "--":
                        try:
                            int(token, 16)
                            found.append("0x" + token.lower())
                        except ValueError:
                            pass
            print(f"{PASS} I2C bus 1: {', '.join(found) or 'no devices'}")
        else:
            print(f"{WARN} i2cdetect: {err or out}")

    for mod in (
        "lgpio", "libcamera", "pykms", "picamera2",
        "robot_hat", "vilib", "pidog"
    ):
        module_check(mod)

    if shutil.which("rpicam-hello"):
        rc, out, err = run(["rpicam-hello", "--list-cameras"])
        if rc == 0 and "Available cameras" in out:
            print(f"{PASS} Camera detected")
            for line in out.splitlines():
                if "ov5647" in line.lower():
                    print(f"       {line.strip()}")
                    break
        else:
            print(f"{FAIL} Camera not detected")
    else:
        print(f"{FAIL} rpicam-hello missing")

    if shutil.which("aplay"):
        rc, out, _ = run(["aplay", "-l"])
        if "sndrpigooglevoi" in out:
            print(f"{PASS} Robot HAT speaker device detected")
        else:
            print(f"{WARN} Robot HAT playback device not found")

    if shutil.which("arecord"):
        rc, out, _ = run(["arecord", "-l"])
        if "sndrpigooglevoi" in out:
            print(f"{PASS} Robot HAT microphone device detected")
        else:
            print(f"{WARN} Robot HAT capture device not found")

    try:
        from robot_hat import device
        voltage = device.get_battery_voltage()
        print(f"{PASS} Battery: {voltage:.2f} V")
        if voltage < 6.2:
            print(f"{WARN} Battery is very low; do not run servos.")
    except Exception as e:
        print(f"{FAIL} Battery read: {e}")

    try:
        import lgpio
        for chip in (0, 1):
            try:
                h = lgpio.gpiochip_open(chip)
                info = lgpio.gpio_get_chip_info(h)
                lgpio.gpiochip_close(h)
                print(f"{PASS} gpiochip{chip}: {info}")
            except Exception as e:
                print(f"{WARN} gpiochip{chip}: {e}")
    except Exception:
        pass

def camera_test():
    print("\n=== Camera Capture Test ===")
    path = str(Path.home() / "pidog_camera_test.jpg")
    rc, out, err = run([
        "rpicam-jpeg", "-n", "-t", "1200", "-o", path
    ], timeout=15)
    if rc == 0 and Path(path).exists():
        print(f"{PASS} Captured {path}")
    else:
        print(f"{FAIL} Camera capture")
        print(err or out)

def speaker_test():
    print("\n=== Speaker Test ===")
    run(["robot_hat", "enable_speaker"])
    rc = subprocess.call([
        "pasuspender", "--",
        "speaker-test", "-D", "plughw:1,0",
        "-c", "2", "-t", "wav", "-l", "1"
    ])
    print(f"{PASS if rc == 0 else FAIL} Speaker test finished")

def mic_test():
    print("\n=== Microphone Test ===")
    wav = str(Path.home() / "pidog_mic_check.wav")
    print("Speak normally for 5 seconds...")
    rc = subprocess.call([
        "pasuspender", "--",
        "arecord", "-D", "plughw:1,0",
        "-f", "S16_LE", "-r", "48000",
        "-c", "2", "-d", "5", wav
    ])
    if rc != 0:
        print(f"{FAIL} Recording failed")
        return

    rc, out, err = run([
        "sox", wav, "-n", "remix", "1", "stat"
    ])
    text = (out + "\n" + err)
    print(text)

    mono = str(Path.home() / "pidog_mic_check_mono.wav")

    print("Playing recorded voice back...")

    rc = subprocess.call([
        "sox",
        wav,
        mono,
        "remix", "1",
        "gain", "-n", "-3"
    ])

    if rc != 0:
        print(f"{FAIL} Could not prepare microphone playback")
        return

    rc = subprocess.call([
        "pasuspender", "--",
        "aplay", "-D", "plughw:1,0", mono
    ])

    if rc == 0:
        print(f"{PASS} Microphone capture + playback successful")
    else:
        print(f"{FAIL} Microphone playback failed")

def ultrasonic_test():
    print("\n=== Ultrasonic Test ===")
    from robot_hat import Pin, Ultrasonic

    echo = Pin("D0")
    trig = Pin("D1")
    u = Ultrasonic(trig, echo, timeout=0.017)

    try:
        values = []
        for _ in range(5):
            value = u.read()
            values.append(value)
            print(f"Distance: {value:.2f} cm")
            time.sleep(0.2)

        if any(v > 0 for v in values):
            print(f"{PASS} Ultrasonic responding")
        else:
            print(f"{FAIL} No valid ultrasonic measurement")
    finally:
        u.close()

def touch_test():
    print("\n=== Dual Touch Test ===")
    from pidog.dual_touch import DualTouch

    touch = DualTouch()
    print("10 seconds: touch front/rear and slide both directions.")
    seen = set()

    end = time.time() + 10
    while time.time() < end:
        v = touch.read()
        if v != "N":
            seen.add(v)
            print("Touch:", v)
        time.sleep(0.1)

    print("Seen:", ", ".join(sorted(seen)) or "none")
    print(f"{PASS if seen else FAIL} Dual touch test")

def imu_test():
    print("\n=== IMU Test ===")
    from pidog.sh3001 import Sh3001

    config = str(Path.home() / ".config/pidog/pidog.conf")
    imu = Sh3001(db=config)

    good = 0
    for _ in range(5):
        data = imu._sh3001_getimudata()
        if data:
            acc, gyro = data
            print(f"ACC: {acc}   GYRO: {gyro}")
            if any(v != 0 for v in acc + gyro):
                good += 1
        time.sleep(0.2)

    print(f"{PASS if good else FAIL} IMU responding")


def sound_direction_test():
    print("\n=== Sound Direction Test ===")
    from pidog.sound_direction import SoundDirection

    sd = SoundDirection()
    print("Make a clap or sharp sound near Brownie within 10 seconds...")

    detected = False
    try:
        end = time.time() + 10
        while time.time() < end:
            if sd.isdetected():
                angle = sd.read()
                print(f"Sound direction: {angle} degrees")
                if 0 <= angle < 360:
                    detected = True
                    break
            time.sleep(0.1)
    finally:
        sd.close()

    print(f"{PASS if detected else FAIL} Sound direction")


def rgb_test():
    print("\n=== RGB Strip Test ===")
    from pidog.rgb_strip import RGBStrip

    strip = RGBStrip(0x74, 11)

    try:
        for color in ("red", "green", "blue"):
            print(f"RGB: {color}")
            strip.set_mode(
                "breath",
                color=color,
                brightness=0.5,
                bps=2,
            )

            end = time.time() + 1.5
            while time.time() < end:
                strip.show()
    finally:
        try:
            strip.set_mode(
                "breath",
                color="black",
                brightness=0,
                bps=1,
            )
            strip.show()
        except Exception:
            pass

    print(f"{PASS} RGB test finished")

def mcu_reset():
    print("\n=== MCU Reset Test ===")
    rc = subprocess.call(["robot_hat", "reset_mcu"])
    print(f"{PASS if rc == 0 else FAIL} MCU reset")

parser = argparse.ArgumentParser()
parser.add_argument("--camera", action="store_true")
parser.add_argument("--speaker", action="store_true")
parser.add_argument("--mic", action="store_true")
parser.add_argument("--ultrasonic", action="store_true")
parser.add_argument("--touch", action="store_true")
parser.add_argument("--imu", action="store_true")
parser.add_argument("--sound-direction", action="store_true")
parser.add_argument("--rgb", action="store_true")
parser.add_argument("--mcu-reset", action="store_true")
parser.add_argument("--all-safe", action="store_true")

args = parser.parse_args()

passive_checks()

if args.camera or args.all_safe:
    camera_test()
if args.speaker or args.all_safe:
    speaker_test()
if args.mic or args.all_safe:
    mic_test()
if args.ultrasonic or args.all_safe:
    ultrasonic_test()
if args.touch or args.all_safe:
    touch_test()
if args.imu or args.all_safe:
    imu_test()
if args.sound_direction or args.all_safe:
    sound_direction_test()
if args.rgb or args.all_safe:
    rgb_test()
if args.mcu_reset:
    mcu_reset()

print("\nDiagnostic complete.")
