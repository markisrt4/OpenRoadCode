# Experimental Termux navigation build

OpenRoadCode can build substantial parts of its native navigation stack directly
on Android/aarch64 under Termux. This target is experimental and intentionally
separate from the Debian/Ubuntu container pipeline.

## Proven configuration

The initial experiment was validated on Android 16/aarch64 with Termux. It
successfully built and executed:

- `prime_server`
- Valhalla 3.8.3 (`valhalla_service --help`)
- MapLibre Native core
- MapLibre Native Linux/GLFW platform build
- `mbgl-glfw` rendering through Mesa/OpenGL, X11, and the Termux:X11 Android app

## Why this needs a separate target

Termux uses Android's native ABI and does not provide a conventional Debian-like
host environment. There is no `sudo`, systemd deployment, `/srv` convention, or
Docker requirement. Native dependencies come from `pkg` and software is built
against the Termux/Android libraries.

Default OpenRoadCode paths are:

- software: `$PREFIX/opt/openroadcode/navigation`
- config: `$PREFIX/etc/openroadcode/navigation.toml`
- map/routing data: `$HOME/.local/share/openroadcode`

## Reproducing the build

From an OpenRoadCode checkout:

```bash
bash development/termux/build_navigation_stack.sh
```

`BUILD_JOBS` may be set to limit compilation parallelism, for example:

```bash
BUILD_JOBS=4 bash development/termux/build_navigation_stack.sh
```

## Termux:X11

The Termux-side X11 packages are not sufficient by themselves. Install the
Termux:X11 Android APK separately. Android may require temporarily allowing the
APK installer source according to the device's security policy.

After the Android app is installed:

```bash
termux-x11 :0 &
export DISPLAY=:0
xterm
```

Once X11 is working, the installed MapLibre GLFW test application can be run:

```bash
$PREFIX/opt/openroadcode/navigation/bin/mbgl-glfw
```

## Captured portability changes

### Valhalla stream position arithmetic

Android/Clang rejects subtraction between `std::streampos` and `int64_t` in
`src/mjolnir/graphtilebuilder.cc`. The build applies
`patches/valhalla-streampos.patch`, converting the position through
`std::streamoff` before integer arithmetic.

### Android logging

Valhalla's Android logging implementation references `__android_log_print`.
Termux therefore links executable/shared targets with Android `liblog` using
`-llog`.

### MapLibre Linux/GLFW platform

A normal native Termux configure is detected as Android and MapLibre enters its
official Android/NDK CMake path. The experimental OpenRoadCode build deliberately
selects the Linux platform with:

```text
CMAKE_SYSTEM_NAME=Linux
MLN_WITH_GLFW=ON
MLN_WITH_OPENGL=ON
```

X11 include/library locations are supplied from `$PREFIX`. This produces the
Linux `mbgl-glfw` application as an Android/Termux-native executable and allows
it to render through Termux:X11.

## Remaining work

The experiment has not yet validated the complete OpenRoadCode map renderer,
routing dataset deployment, Valhalla HTTP routing against production tiles, or
full controller integration on Android. Treat the target as a development and
portability experiment until those pieces are exercised.
