# Brownie Camera Stack — Known Working Revisions

Tested on:

- Raspberry Pi 4
- Ubuntu 22.04.5 LTS
- Python 3.10.12
- OV5647 5 MP camera

## libcamera

- Branch: `main`
- Commit: `ca0ba53ef1eec5e59dee7255863b943f5eaf6cfd`
- Describe: `v0.7.2+rpt20260807`

## kmsxx

- Detached HEAD
- Commit: `a31ddfd9c4e294f29b9203463022d0eac11cecc5`
- Describe: `a31ddfd`

## rpicam-apps

- Branch: `main`
- Commit: `9270b6013c4575dff2e0625c0f4b8ae750218b0f`
- Describe: `v1.12.0-10-g9270b60`

## Boot configuration

Working `/boot/firmware/config.txt` camera settings:

```ini
camera_auto_detect=0
dtoverlay=ov5647
```

## Python binding exposure

Expected symlinks on Ubuntu 22.04 / Python 3.10:

```text
/usr/local/lib/python3.10/dist-packages/libcamera -> /usr/local/lib/python3/dist-packages/libcamera
/usr/local/lib/python3.10/dist-packages/pykms -> /usr/local/lib/aarch64-linux-gnu/python3.10/site-packages/pykms
```

Create them with:

```bash
sudo mkdir -p /usr/local/lib/python3.10/dist-packages
sudo ln -sfn /usr/local/lib/python3/dist-packages/libcamera /usr/local/lib/python3.10/dist-packages/libcamera
sudo ln -sfn /usr/local/lib/aarch64-linux-gnu/python3.10/site-packages/pykms /usr/local/lib/python3.10/dist-packages/pykms
```

## Native library state

Working source-built libraries are under `/usr/local/lib/aarch64-linux-gnu`.

After installing libcamera/kmsxx, refresh the linker cache:

```bash
sudo ldconfig
```

Expected active libcamera symlinks:

```text
libcamera.so -> libcamera.so.0.7 -> libcamera.so.0.7.2
libcamera-base.so -> libcamera-base.so.0.7 -> libcamera-base.so.0.7.2
```

Older 0.5.x files may exist on the current machine, but they are not the active working target.

## libcamera Meson configuration

Known-working build options recovered from `~/libcamera/build/meson-info/intro-buildoptions.json`:

```text
buildtype = debug
prefix = /usr/local
libdir = lib/aarch64-linux-gnu
pipelines = ['rpi/pisp', 'rpi/vc4']
ipas = ['rpi/pisp', 'rpi/vc4']
pycamera = enabled
v4l2 = enabled
cam = disabled
qcam = disabled
documentation = disabled
test = False
gstreamer = auto
```

Meson versions observed on the working machine:

- user: `1.8.2` from `~/.local/bin/meson`
- root: `1.12.0` from `/usr/local/bin/meson`

Do not mix Meson versions within the same configured build directory.

## kmsxx Meson configuration

Known-working build options recovered from `~/kmsxx/build/meson-info/intro-buildoptions.json`:

```text
buildtype = debug
prefix = /usr/local
libdir = lib/aarch64-linux-gnu
utils = True
pykms = auto
kmscube = False
```

## rpicam-apps Meson configuration

Known-working build options recovered from `~/rpicam-apps/build/meson-info/intro-buildoptions.json`:

```text
buildtype = release
prefix = /usr/local
libdir = lib/aarch64-linux-gnu
enable_libav = auto
enable_drm = auto
enable_egl = auto
enable_qt = disabled
enable_opencv = disabled
enable_tflite = disabled
```
