# Camera Troubleshooting

Brownie uses an OV5647 5 MP Raspberry Pi camera. The working Ubuntu 22.04 camera path combines a source-built Raspberry Pi libcamera stack, Picamera2, kmsxx/pykms, and rpicam-apps.

## Camera not detected after otherwise successful userspace setup

### Symptom

The camera stack installs, but the sensor is not detected correctly by the kernel/userspace pipeline.

### Root cause

Brownie's physical sensor is OV5647, but the boot configuration initially selected an IMX219 overlay.

### Resolution

Disable automatic camera detection and explicitly select the OV5647 overlay in the boot configuration.

### Verification

The camera listing reports one OV5647 sensor with a 2592x1944 mode, and a full-resolution JPEG capture succeeds.

## libcamera Python import missing after source installation

### Symptom

Native libcamera is installed, but Python 3.10 cannot import the bindings.

### Root cause

The source install placed the Python module under a generic local Python dist-packages path that was not automatically visible to Brownie's Python 3.10 environment.

### Resolution

Expose the installed binding to the Python 3.10 package path and refresh native shared-library discovery after installation.

### Verification

Both the `libcamera` Python module and Picamera2 import successfully.

## pykms missing after kmsxx build

### Symptom

Picamera2 dependencies are present, but importing pykms fails.

### Root cause

The kmsxx Python bindings installed into an architecture-specific local site-packages directory that Python 3.10 did not search automatically.

### Resolution

Expose the installed pykms package to the active Python 3.10 package path.

### Verification

Importing `pykms` succeeds before testing Picamera2.

## Current kmsxx source does not build with Ubuntu 22.04 toolchain

### Symptom

The build fails around newer C++ formatting support.

### Root cause

The then-current kmsxx source expected standard-library functionality beyond the GCC 11 toolchain used by Ubuntu 22.04.

### Resolution

Use the compatible kmsxx revision immediately before the project removed its dependency on the external fmt library.

### Lesson

When upstream raises its compiler baseline, pin a known-compatible revision rather than replacing the OS compiler stack during robot bring-up.

## Meson version mismatch

### Symptom

A build directory configured by the normal user cannot be cleanly used during a privileged installation step.

### Root cause

Brownie had different Meson versions available to the normal user and to root.

### Resolution

Reconfigure the existing build directory with the Meson executable that will be used for the installation phase so the build metadata stays consistent.
