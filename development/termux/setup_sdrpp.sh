#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This setup script must run inside Termux." >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REMOTE_CONTROL_SRC="$ORC_ROOT/development/sdrpp/remote_control"
TELEMETRY_SRC="$ORC_ROOT/development/sdrpp/telemetry"
ORCU_RTL_SRC="$ORC_ROOT/development/sdrpp/rtl_usb_proxy"

for module_dir in "$REMOTE_CONTROL_SRC" "$TELEMETRY_SRC"; do
  [[ -f "$module_dir/CMakeLists.txt" && -f "$module_dir/src/main.cpp" ]] || {
    echo "OpenRoadCode SDR++ module was not found at $module_dir" >&2
    exit 1
  }
done

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"

command -v pkg >/dev/null 2>&1 || {
  echo "Termux pkg command was not found." >&2
  exit 1
}

TERMUX_PACKAGES=(proot-distro git)
missing_termux_packages=()
for package in "${TERMUX_PACKAGES[@]}"; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$' || missing_termux_packages+=("$package")
done
if ((${#missing_termux_packages[@]})); then
  echo "[*] Installing missing Termux packages: ${missing_termux_packages[*]}"
  pkg install -y "${missing_termux_packages[@]}"
else
  echo "[*] Required Termux packages are already installed"
fi

if proot-distro login debian -- /bin/true >/dev/null 2>&1; then
  echo "[*] Debian proot is already installed"
else
  echo "[*] Installing Debian proot"
  proot-distro install debian
fi

echo "[*] Installing SDR++ dependencies and building inside Debian"
proot-distro login debian --shared-tmp -- env \
  SDRPP_REF="$SDRPP_REF" \
  BUILD_JOBS="$BUILD_JOBS" \
  REMOTE_CONTROL_SRC="$REMOTE_CONTROL_SRC" \
  TELEMETRY_SRC="$TELEMETRY_SRC" \
  ORCU_RTL_SRC="$ORCU_RTL_SRC" \
  bash -s <<'DEBIAN'
set -euo pipefail

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"
REMOTE_CONTROL_SRC="${REMOTE_CONTROL_SRC:?REMOTE_CONTROL_SRC is required}"
TELEMETRY_SRC="${TELEMETRY_SRC:?TELEMETRY_SRC is required}"
ORCU_RTL_SRC="${ORCU_RTL_SRC:?ORCU_RTL_SRC is required}"
SDRPP_SRC="$HOME/SDRPlusPlus"
SDRPP_BUILD="$SDRPP_SRC/build"
SDRPP_ROOT="$SDRPP_SRC/root_dev"
RTLSDR_SRC="$HOME/rtl-sdr-orcu"
RTLSDR_PREFIX="$HOME/.local/orcu-rtlsdr"
REMOTE_CONTROL_DST="$SDRPP_SRC/misc_modules/remote_control"
TELEMETRY_DST="$SDRPP_SRC/misc_modules/telemetry"

export DEBIAN_FRONTEND=noninteractive

DEBIAN_PACKAGES=(
  build-essential cmake git binutils python3 libfftw3-dev libglfw3-dev libvolk-dev
  libzstd-dev libusb-1.0-0-dev librtlsdr-dev libsoapysdr-dev librtaudio-dev libhackrf-dev
  pulseaudio pulseaudio-utils alsa-utils
)
missing_debian_packages=()
for package in "${DEBIAN_PACKAGES[@]}"; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$' || missing_debian_packages+=("$package")
done
if ((${#missing_debian_packages[@]})); then
  echo "[*] Installing missing Debian packages: ${missing_debian_packages[*]}"
  apt-get update
  apt-get install -y "${missing_debian_packages[@]}"
else
  echo "[*] Required Debian packages are already installed"
fi

if [[ ! -d "$SDRPP_SRC/.git" ]]; then
  echo "[*] Cloning SDR++"
  git clone https://github.com/AlexandreRouma/SDRPlusPlus.git "$SDRPP_SRC"
fi

echo "[*] Updating SDR++"
git -C "$SDRPP_SRC" fetch --tags --prune origin
git -C "$SDRPP_SRC" checkout "$SDRPP_REF"
if git -C "$SDRPP_SRC" show-ref --verify --quiet "refs/remotes/origin/$SDRPP_REF"; then
  git -C "$SDRPP_SRC" reset --hard "origin/$SDRPP_REF"
fi

echo "[*] Building ORCU-backed librtlsdr"
if [[ ! -d "$RTLSDR_SRC/.git" ]]; then
  git clone https://github.com/steve-m/librtlsdr.git "$RTLSDR_SRC"
fi
git -C "$RTLSDR_SRC" fetch --prune origin
git -C "$RTLSDR_SRC" reset --hard origin/master
git -C "$RTLSDR_SRC" clean -fdx
cp "$ORCU_RTL_SRC/orcu_usb_transport.c" "$RTLSDR_SRC/src/"
cp "$ORCU_RTL_SRC/orcu_usb_transport.h" "$RTLSDR_SRC/src/"
python3 "$ORCU_RTL_SRC/patch_librtlsdr_orcu.py" "$RTLSDR_SRC"
cmake -S "$RTLSDR_SRC" -B "$RTLSDR_SRC/build-orcu" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$RTLSDR_PREFIX" \
  -DINSTALL_UDEV_RULES=OFF
cmake --build "$RTLSDR_SRC/build-orcu" --parallel "$BUILD_JOBS"
cmake --install "$RTLSDR_SRC/build-orcu"
export PKG_CONFIG_PATH="$RTLSDR_PREFIX/lib/pkgconfig:$RTLSDR_PREFIX/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"
export CMAKE_PREFIX_PATH="$RTLSDR_PREFIX:${CMAKE_PREFIX_PATH:-}"
export LD_LIBRARY_PATH="$RTLSDR_PREFIX/lib:$RTLSDR_PREFIX/lib64:${LD_LIBRARY_PATH:-}"

echo "[*] Hardening SDR++ audio sink for delayed PulseAudio device discovery"
python3 - "$SDRPP_SRC/sink_modules/audio_sink/src/main.cpp" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
old = """    void selectFirst() {
        selectById(defaultDevId);
    }
"""
new = """    void selectFirst() {
        if (devList.empty()) {
            flog::warn(\"AudioSinkModule No output audio devices available yet\");
            return;
        }
        selectById(defaultDevId);
    }
"""
if new not in source:
    if old not in source:
        raise SystemExit("Could not locate SDR++ AudioSink::selectFirst() for ORC hardening")
    source = source.replace(old, new, 1)
path.write_text(source)
PY

echo "[*] Staging OpenRoadCode SDR++ modules"
rm -rf "$REMOTE_CONTROL_DST" "$TELEMETRY_DST"
cp -a "$REMOTE_CONTROL_SRC" "$REMOTE_CONTROL_DST"
cp -a "$TELEMETRY_SRC" "$TELEMETRY_DST"

python3 - "$SDRPP_SRC/CMakeLists.txt" "$SDRPP_SRC/core/src/core.cpp" <<'PY'
from pathlib import Path
import sys
cmake_path = Path(sys.argv[1]); core_path = Path(sys.argv[2])
cmake = cmake_path.read_text()
for comment, line in (("OpenRoadCode application remote control module", 'add_subdirectory("misc_modules/remote_control")'), ("OpenRoadCode telemetry module", 'add_subdirectory("misc_modules/telemetry")')):
    if line not in cmake: cmake = cmake.rstrip() + f"\n\n# {comment}\n{line}\n"
cmake_path.write_text(cmake)
core = core_path.read_text()
marker = '    defConfig["moduleInstances"]["Rigctl Server"] = "rigctl_server";\n'
if marker not in core: raise SystemExit("Could not locate Rigctl Server default module instance in SDR++ core.cpp")
for instance, module in (("Remote Control", "remote_control"), ("Telemetry", "telemetry")):
    if f'moduleInstances"]["{instance}"]' not in core:
        lines = f'    defConfig["moduleInstances"]["{instance}"]["module"] = "{module}";\n    defConfig["moduleInstances"]["{instance}"]["enabled"] = true;\n'
        core = core.replace(marker, marker + lines, 1)
core_path.write_text(core)
PY

echo "[*] Instrumenting SDR++ waterfall framebuffer for native crash diagnosis"
python3 - "$SDRPP_SRC/core/src/gui/widgets/waterfall.cpp" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()

alloc = '''            waterfallFb = new uint32_t[dataWidth * waterfallHeight];
            memset(waterfallFb, 0, dataWidth * waterfallHeight * sizeof(uint32_t));'''
alloc_diag = '''            waterfallFb = new uint32_t[dataWidth * waterfallHeight];
            fprintf(stderr, "[ORC waterfall] alloc fb=%p width=%d height=%d pixels=%zu\\n",
                    (void*)waterfallFb, dataWidth, waterfallHeight,
                    (size_t)dataWidth * (size_t)waterfallHeight);
            fflush(stderr);
            memset(waterfallFb, 0, dataWidth * waterfallHeight * sizeof(uint32_t));'''
if alloc not in source:
    raise SystemExit("Could not locate SDR++ waterfall framebuffer allocation")
source = source.replace(alloc, alloc_diag, 1)

move = '''            memmove(&waterfallFb[dataWidth], waterfallFb, dataWidth * (waterfallHeight - 1) * sizeof(uint32_t));'''
move_diag = '''            fprintf(stderr, "[ORC waterfall] push fb=%p width=%d height=%d rawFFTSize=%d currentFFTLine=%d latestFFT=%p visible=%d bytes=%zu\\n",
                    (void*)waterfallFb, dataWidth, waterfallHeight, rawFFTSize,
                    currentFFTLine, (void*)latestFFT, waterfallVisible ? 1 : 0,
                    (dataWidth > 0 && waterfallHeight > 1)
                        ? (size_t)dataWidth * (size_t)(waterfallHeight - 1) * sizeof(uint32_t)
                        : 0u);
            fflush(stderr);
            memmove(&waterfallFb[dataWidth], waterfallFb, dataWidth * (waterfallHeight - 1) * sizeof(uint32_t));'''
if move not in source:
    raise SystemExit("Could not locate SDR++ waterfall framebuffer shift")
source = source.replace(move, move_diag, 1)

path.write_text(source)
PY

echo "[*] Guarding SDR++ waterfall until its first valid resize"
python3 - "$SDRPP_SRC/core/src/gui/widgets/waterfall.cpp" "$SDRPP_SRC/core/src/signal_path/iq_frontend.cpp" <<'PY'
from pathlib import Path
import sys

waterfall = Path(sys.argv[1])
frontend = Path(sys.argv[2])
source = waterfall.read_text()

old = '''    float* WaterFall::getFFTBuffer() {
        if (rawFFTs == NULL) { return NULL; }
        buf_mtx.lock();
        if (waterfallVisible) {
            currentFFTLine--;'''
new = '''    float* WaterFall::getFFTBuffer() {
        if (rawFFTs == NULL) { return NULL; }
        buf_mtx.lock();
        if (waterfallVisible) {
            // IQ can arrive before the GUI has performed its first resize.
            // Until then waterfallHeight is zero and waterfallFb is only the
            // constructor's one-pixel placeholder.
            if (waterfallHeight <= 0) {
                buf_mtx.unlock();
                return NULL;
            }
            currentFFTLine--;'''
if old not in source:
    raise SystemExit("Could not locate SDR++ WaterFall::getFFTBuffer()")
source = source.replace(old, new, 1)
waterfall.write_text(source)

source = frontend.read_text()
old = '''    // Release buffer
    _this->_releaseFFTBuffer(_this->_fftCtx);'''
new = '''    // Only release/publish an FFT buffer that was actually acquired.
    // The waterfall can intentionally decline a buffer before its first
    // valid GUI resize.
    if (fftBuf) {
        _this->_releaseFFTBuffer(_this->_fftCtx);
    }'''
if old not in source:
    raise SystemExit("Could not locate SDR++ IQFrontEnd FFT release")
source = source.replace(old, new, 1)
frontend.write_text(source)
PY

echo "[*] Instrumenting SDR++ RTL source handoff for stalled-DSP diagnosis"
python3 - "$SDRPP_SRC/source_modules/rtl_sdr_source/src/main.cpp" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
old = '''        if (!_this->stream.swap(sampCount)) { return; }
    }'''
new = '''        static unsigned long long orcCallbacks = 0;
        static unsigned long long orcSwapFailures = 0;
        orcCallbacks++;
        bool swapped = _this->stream.swap(sampCount);
        if (!swapped) { orcSwapFailures++; }
        if (orcCallbacks <= 16 || (orcCallbacks % 4096) == 0 || (!swapped && orcSwapFailures <= 16)) {
            fprintf(stderr,
                    "[ORC RTL source] callback=%llu samples=%d swap=%d failures=%llu\\n",
                    orcCallbacks, sampCount, swapped ? 1 : 0, orcSwapFailures);
            fflush(stderr);
        }
        if (!swapped) { return; }
    }'''
if old not in source:
    raise SystemExit("Could not locate RTLSDRSourceModule::asyncHandler stream swap")
source = source.replace(old, new, 1)
path.write_text(source)
PY

echo "[*] Instrumenting SDR++ IQ frontend boundary for stalled-DSP diagnosis"
python3 - "$SDRPP_SRC/core/src/signal_path/iq_frontend.cpp" "$SDRPP_SRC/core/src/dsp/buffer/frame_buffer.h" <<'PY'
from pathlib import Path
import sys

frontend = Path(sys.argv[1])
source = frontend.read_text()
old = '''    split.init(preproc.out);

    // TODO: Do something to avoid basically repeating this code twice'''
new = '''    split.init(preproc.out);
    fprintf(stderr,
            "[ORC frontend] self=%p sourceIn=%p inBufOut=%p preprocOut=%p split=%p splitIn=%p fftIn=%p decimOut=%p dcOut=%p conjugateOut=%p\\n",
            (void*)this, (void*)in, (void*)&inBuf.out, (void*)preproc.out,
            (void*)&split, (void*)preproc.out, (void*)&fftIn,
            (void*)&decim.out, (void*)&dcBlock.out, (void*)&conjugate.out);
    fflush(stderr);

    // TODO: Do something to avoid basically repeating this code twice'''
if old not in source:
    raise SystemExit("Could not locate IQFrontEnd split.init(preproc.out)")
source = source.replace(old, new, 1)
frontend.write_text(source)

frame = Path(sys.argv[2])
source = frame.read_text()
old = '''        int run() {
            // Wait for data
            int count = _in->read();'''
new = '''        int run() {
            static unsigned long long orcFrameRuns = 0;
            orcFrameRuns++;
            bool orcTrace = orcFrameRuns <= 80 || (orcFrameRuns % 256) == 0;
            if (orcTrace) {
                fprintf(stderr, "[ORC framebuf] self=%p run=%llu in=%p out=%p bypass=%d before-read\\n",
                        (void*)this, orcFrameRuns, (void*)_in, (void*)&out, bypass ? 1 : 0);
                fflush(stderr);
            }
            // Wait for data
            int count = _in->read();
            if (orcTrace || count < 0) {
                fprintf(stderr, "[ORC framebuf] self=%p run=%llu in=%p out=%p bypass=%d after-read count=%d\\n",
                        (void*)this, orcFrameRuns, (void*)_in, (void*)&out, bypass ? 1 : 0, count);
                fflush(stderr);
            }'''
if old not in source:
    raise SystemExit("Could not locate SampleFrameBuffer::run()")
source = source.replace(old, new, 1)

old = '''                // Swap
                if (!out.swap(count)) { break; }'''
new = '''                // Swap
                static unsigned long long orcFrameOutputs = 0;
                orcFrameOutputs++;
                bool orcTrace = orcFrameOutputs <= 80 || (orcFrameOutputs % 256) == 0;
                if (orcTrace) {
                    fprintf(stderr, "[ORC framebuf worker] self=%p output=%llu out=%p count=%d before-swap\\n",
                            (void*)this, orcFrameOutputs, (void*)&out, count);
                    fflush(stderr);
                }
                bool orcSwapped = out.swap(count);
                if (orcTrace || !orcSwapped) {
                    fprintf(stderr, "[ORC framebuf worker] self=%p output=%llu out=%p count=%d swap=%d\\n",
                            (void*)this, orcFrameOutputs, (void*)&out, count, orcSwapped ? 1 : 0);
                    fflush(stderr);
                }
                if (!orcSwapped) { break; }'''
if old not in source:
    raise SystemExit("Could not locate SampleFrameBuffer worker swap")
source = source.replace(old, new, 1)
frame.write_text(source)
PY

echo "[*] Instrumenting SDR++ FFT stream identity for stalled-waterfall diagnosis"
python3 - "$SDRPP_SRC/core/src/dsp/buffer/reshaper.h" "$SDRPP_SRC/core/src/dsp/routing/splitter.h" <<'PY'
from pathlib import Path
import sys

reshape = Path(sys.argv[1])
s = reshape.read_text()
old = '''        int run() {
            int count = _in->read();'''
new = '''        int run() {
            static unsigned long long orcIdentityRuns = 0;
            orcIdentityRuns++;
            if (orcIdentityRuns <= 80 || (orcIdentityRuns % 256) == 0) {
                fprintf(stderr, "[ORC reshape identity] self=%p run=%llu in=%p out=%p\\n",
                        (void*)this, orcIdentityRuns, (void*)_in, (void*)&out);
                fflush(stderr);
            }
            int count = _in->read();'''
if old in s:
    s=s.replace(old,new,1)
else:
    producer = 'fprintf(stderr, "[ORC reshape producer] self=%p run=%llu before-input-read'
    pos = s.find(producer)
    if pos < 0:
        raise SystemExit("Could not locate SDR++ Reshaper::run() or producer trace")
    line_start = s.rfind("\n", 0, pos) + 1
    indent = s[line_start:pos]
    identity = indent + 'fprintf(stderr, "[ORC reshape identity] self=%p in=%p out=%p\\\\n", (void*)this, (void*)_in, (void*)&out); fflush(stderr);\\n'
    s = s[:line_start] + identity + s[line_start:]
reshape.write_text(s)

splitter=Path(sys.argv[2]); s=splitter.read_text()
old='''            for (const auto& stream : streams) {
                memcpy(stream->writeBuf, base_type::_in->readBuf, count * sizeof(T));
                if (!stream->swap(count)) {'''
new='''            static unsigned long long orcSplitRuns = 0;
            orcSplitRuns++;
            for (const auto& stream : streams) {
                if (orcSplitRuns <= 80 || (orcSplitRuns % 256) == 0) {
                    fprintf(stderr, "[ORC splitter] self=%p run=%llu in=%p dest=%p count=%d streams=%zu\\n",
                            (void*)this, orcSplitRuns, (void*)base_type::_in, (void*)stream, count, streams.size());
                    fflush(stderr);
                }
                memcpy(stream->writeBuf, base_type::_in->readBuf, count * sizeof(T));
                fprintf(stderr,
                        "[ORC splitter exact] self=%p run=%llu dest=%p before-swap count=%d streams=%zu\\n",
                        (void*)this, orcSplitRuns, (void*)stream, count, streams.size());
                fflush(stderr);
                bool orcDestSwapped = stream->swap(count);
                fprintf(stderr,
                        "[ORC splitter exact] self=%p run=%llu dest=%p after-swap swap=%d\\n",
                        (void*)this, orcSplitRuns, (void*)stream, orcDestSwapped ? 1 : 0);
                fflush(stderr);
                if (!orcDestSwapped) {'''
if old not in s: raise SystemExit("Could not locate Splitter::run loop")
s=s.replace(old,new,1)

flush_old = '''            base_type::_in->flush();

            return count;'''
flush_new = '''            fprintf(stderr,
                    "[ORC splitter exact] self=%p run=%llu input=%p before-flush\\n",
                    (void*)this, orcSplitRuns, (void*)base_type::_in);
            fflush(stderr);
            base_type::_in->flush();
            fprintf(stderr,
                    "[ORC splitter exact] self=%p run=%llu input=%p after-flush\\n",
                    (void*)this, orcSplitRuns, (void*)base_type::_in);
            fflush(stderr);

            return count;'''
if flush_old not in s: raise SystemExit("Could not locate Splitter::run input flush")
s=s.replace(flush_old,flush_new,1)
s=s.replace('''        void bindStream(stream<T>* stream) {
            assert(base_type::_block_init);''','''        void bindStream(stream<T>* stream) {
            fprintf(stderr, "[ORC splitter] self=%p bind dest=%p\\n", (void*)this, (void*)stream); fflush(stderr);
            assert(base_type::_block_init);''',1)
s=s.replace('''        void unbindStream(stream<T>* stream) {
            assert(base_type::_block_init);''','''        void unbindStream(stream<T>* stream) {
            fprintf(stderr, "[ORC splitter] self=%p unbind dest=%p\\n", (void*)this, (void*)stream); fflush(stderr);
            assert(base_type::_block_init);''',1)
splitter.write_text(s)
PY

echo "[*] Instrumenting SDR++ VFO consumer for stalled-waterfall diagnosis"
python3 - "$SDRPP_SRC/core/src/signal_path/iq_frontend.cpp" "$SDRPP_SRC/core/src/dsp/channel/rx_vfo.h" <<'PY'
from pathlib import Path
import sys

frontend = Path(sys.argv[1])
vfo_header = Path(sys.argv[2])

s = frontend.read_text()
old = '''    // Register them
    vfoStreams[name] = vfoIn;
    vfos[name] = vfo;
    bindIQStream(vfoIn);

    // Start VFO
    vfo->start();'''
new = '''    // Register them
    vfoStreams[name] = vfoIn;
    vfos[name] = vfo;
    fprintf(stderr,
            "[ORC VFO identity] frontend=%p name=%s vfo=%p input=%p output=%p\\n",
            (void*)this, name.c_str(), (void*)vfo, (void*)vfoIn, (void*)&vfo->out);
    fflush(stderr);
    bindIQStream(vfoIn);

    // Start VFO
    vfo->start();'''
if old not in s:
    raise SystemExit("Could not locate IQFrontEnd::addVFO registration")
s = s.replace(old, new, 1)
frontend.write_text(s)

s = vfo_header.read_text()
old = '''        int run() {
            int count = base_type::_in->read();
            if (count < 0) { return -1; }

            int outCount = process(count, base_type::_in->readBuf, out.writeBuf);

            // Swap if some data was generated
            base_type::_in->flush();
            if (outCount) {
                if (!out.swap(outCount)) { return -1; }
            }
            return outCount;
        }'''
new = '''        int run() {
            static unsigned long long orcVfoRuns = 0;
            unsigned long long orcRun = ++orcVfoRuns;
            fprintf(stderr,
                    "[ORC VFO run] self=%p run=%llu input=%p output=%p before-read\\n",
                    (void*)this, orcRun, (void*)base_type::_in, (void*)&out);
            fflush(stderr);
            int count = base_type::_in->read();
            fprintf(stderr,
                    "[ORC VFO run] self=%p run=%llu input=%p after-read count=%d\\n",
                    (void*)this, orcRun, (void*)base_type::_in, count);
            fflush(stderr);
            if (count < 0) { return -1; }

            fprintf(stderr,
                    "[ORC VFO run] self=%p run=%llu before-process count=%d\\n",
                    (void*)this, orcRun, count);
            fflush(stderr);
            int outCount = process(count, base_type::_in->readBuf, out.writeBuf);
            fprintf(stderr,
                    "[ORC VFO run] self=%p run=%llu after-process outCount=%d\\n",
                    (void*)this, orcRun, outCount);
            fflush(stderr);

            // Swap if some data was generated
            fprintf(stderr,
                    "[ORC VFO run] self=%p run=%llu input=%p before-input-flush\\n",
                    (void*)this, orcRun, (void*)base_type::_in);
            fflush(stderr);
            base_type::_in->flush();
            fprintf(stderr,
                    "[ORC VFO run] self=%p run=%llu input=%p after-input-flush\\n",
                    (void*)this, orcRun, (void*)base_type::_in);
            fflush(stderr);
            if (outCount) {
                fprintf(stderr,
                        "[ORC VFO run] self=%p run=%llu output=%p before-output-swap outCount=%d\\n",
                        (void*)this, orcRun, (void*)&out, outCount);
                fflush(stderr);
                bool orcSwap = out.swap(outCount);
                fprintf(stderr,
                        "[ORC VFO run] self=%p run=%llu output=%p after-output-swap swap=%d\\n",
                        (void*)this, orcRun, (void*)&out, orcSwap ? 1 : 0);
                fflush(stderr);
                if (!orcSwap) { return -1; }
            }
            return outCount;
        }'''
if old not in s:
    raise SystemExit("Could not locate RxVFO::run")
s = s.replace(old, new, 1)
vfo_header.write_text(s)
PY

echo "[*] Instrumenting SDR++ block lifecycle for stalled-waterfall diagnosis"
python3 - "$SDRPP_SRC/core/src/dsp/block.h" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
source = source.replace('''        virtual void start() {
            assert(_block_init);''', '''        virtual void start() {
            fprintf(stderr, "[ORC block] self=%p start running=%d tempStopped=%d depth=%d inputs=%zu outputs=%zu\\n", (void*)this, running ? 1 : 0, tempStopped ? 1 : 0, tempStopDepth, inputs.size(), outputs.size()); fflush(stderr);
            assert(_block_init);''', 1)
source = source.replace('''        virtual void stop() {
            assert(_block_init);''', '''        virtual void stop() {
            fprintf(stderr, "[ORC block] self=%p stop running=%d tempStopped=%d depth=%d inputs=%zu outputs=%zu\\n", (void*)this, running ? 1 : 0, tempStopped ? 1 : 0, tempStopDepth, inputs.size(), outputs.size()); fflush(stderr);
            assert(_block_init);''', 1)
source = source.replace('''        void tempStart() {
            assert(_block_init);''', '''        void tempStart() {
            fprintf(stderr, "[ORC block] self=%p tempStart running=%d tempStopped=%d depth=%d\\n", (void*)this, running ? 1 : 0, tempStopped ? 1 : 0, tempStopDepth); fflush(stderr);
            assert(_block_init);''', 1)
source = source.replace('''        void tempStop() {
            assert(_block_init);''', '''        void tempStop() {
            fprintf(stderr, "[ORC block] self=%p tempStop running=%d tempStopped=%d depth=%d\\n", (void*)this, running ? 1 : 0, tempStopped ? 1 : 0, tempStopDepth); fflush(stderr);
            assert(_block_init);''', 1)
source = source.replace('''        virtual void doStop() {
            for (auto& in : inputs) {
                in->stopReader();
            }''', '''        virtual void doStop() {
            fprintf(stderr, "[ORC block] self=%p doStop inputs=%zu outputs=%zu\\n", (void*)this, inputs.size(), outputs.size()); fflush(stderr);
            for (auto& in : inputs) {
                fprintf(stderr, "[ORC block] self=%p stopReader stream=%p\\n", (void*)this, (void*)in); fflush(stderr);
                in->stopReader();
            }''', 1)
path.write_text(source)
PY

echo "[*] Instrumenting SDR++ stream handoff for stalled-waterfall diagnosis"
python3 - "$SDRPP_SRC/core/src/dsp/stream.h" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
old = '''                swapCV.wait(lck, [this] { return (canSwap || writerStop); });'''
new = '''                static unsigned long long orcSwaps = 0;
                orcSwaps++;
                bool orcTrace = orcSwaps <= 80 || (orcSwaps % 256) == 0;
                if (orcTrace) {
                    fprintf(stderr, "[ORC stream] self=%p swap=%llu pre canSwap=%d writerStop=%d dataReady=%d readerStop=%d size=%d\\n",
                            (void*)this, orcSwaps, canSwap ? 1 : 0, writerStop ? 1 : 0,
                            dataReady ? 1 : 0, readerStop ? 1 : 0, size);
                    fflush(stderr);
                }
                swapCV.wait(lck, [this] { return (canSwap || writerStop); });
                if (orcTrace) {
                    fprintf(stderr, "[ORC stream] self=%p swap=%llu woke canSwap=%d writerStop=%d\\n",
                            (void*)this, orcSwaps, canSwap ? 1 : 0, writerStop ? 1 : 0);
                    fflush(stderr);
                }'''
if old not in source:
    raise SystemExit("Could not locate dsp::stream::swap wait")
source = source.replace(old, new, 1)
old = '''            std::unique_lock<std::mutex> lck(rdyMtx);
            rdyCV.wait(lck, [this] { return (dataReady || readerStop); });

            return (readerStop ? -1 : dataSize);'''
new = '''            static unsigned long long orcReads = 0;
            orcReads++;
            bool orcTrace = orcReads <= 80 || (orcReads % 256) == 0;
            std::unique_lock<std::mutex> lck(rdyMtx);
            if (orcTrace) {
                fprintf(stderr, "[ORC stream] self=%p read=%llu pre dataReady=%d readerStop=%d dataSize=%d\\n",
                        (void*)this, orcReads, dataReady ? 1 : 0, readerStop ? 1 : 0, dataSize);
                fflush(stderr);
            }
            rdyCV.wait(lck, [this] { return (dataReady || readerStop); });
            if (orcTrace) {
                fprintf(stderr, "[ORC stream] self=%p read=%llu woke dataReady=%d readerStop=%d dataSize=%d\\n",
                        (void*)this, orcReads, dataReady ? 1 : 0, readerStop ? 1 : 0, dataSize);
                fflush(stderr);
            }
            return (readerStop ? -1 : dataSize);'''
if old not in source:
    raise SystemExit("Could not locate dsp::stream::read wait")
source = source.replace(old, new, 1)
old = '''            swapCV.notify_all();
        }

        virtual void stopWriter() {'''
new = '''            static unsigned long long orcFlushes = 0;
            orcFlushes++;
            if (orcFlushes <= 80 || (orcFlushes % 256) == 0) {
                fprintf(stderr, "[ORC stream] self=%p flush=%llu dataReady=%d canSwap=%d\\n",
                        (void*)this, orcFlushes, dataReady ? 1 : 0, canSwap ? 1 : 0);
                fflush(stderr);
            }
            swapCV.notify_all();
        }

        virtual void stopWriter() {'''
if old not in source:
    raise SystemExit("Could not locate dsp::stream::flush notify")
source = source.replace(old, new, 1)
path.write_text(source)
PY

echo "[*] Instrumenting SDR++ FFT reshaper for stalled-waterfall diagnosis"
python3 - "$SDRPP_SRC/core/src/dsp/buffer/reshaper.h" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()

old = '''        int run() {
            int count = _in->read();
            if (count < 0) { return -1; }
            ringBuf.write(_in->readBuf, count);
            _in->flush();
            return count;
        }'''
new = '''        int run() {
            static unsigned long long orcRuns = 0;
            orcRuns++;
            bool orcTraceRun = orcRuns <= 64 || (orcRuns % 256) == 0;
            if (orcTraceRun) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu before-input-read\\n",
                        (void*)this, orcRuns);
                fflush(stderr);
            }
            int count = _in->read();
            if (orcTraceRun || count < 0) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu after-input-read count=%d\\n",
                        (void*)this, orcRuns, count);
                fflush(stderr);
            }
            if (count < 0) { return -1; }
            if (orcTraceRun) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu before-ring-write count=%d\\n",
                        (void*)this, orcRuns, count);
                fflush(stderr);
            }
            int written = ringBuf.write(_in->readBuf, count);
            if (orcTraceRun || written < 0) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu after-ring-write written=%d\\n",
                        (void*)this, orcRuns, written);
                fflush(stderr);
            }
            _in->flush();
            return written < 0 ? -1 : count;
        }'''
if old in source:
    source = source.replace(old, new, 1)
elif "[ORC reshape identity]" in source:
    # Identity instrumentation earlier in this script has already rewritten
    # run(). Preserve it and layer producer tracing onto that form.
    marker = '''            int count = _in->read();
            if (count < 0) { return -1; }
            ringBuf.write(_in->readBuf, count);
            _in->flush();
            return count;'''
    if marker not in source:
        raise SystemExit("Could not locate identity-instrumented SDR++ Reshaper::run()")
    replacement = '''            static unsigned long long orcRuns = 0;
            orcRuns++;
            bool orcTraceRun = orcRuns <= 64 || (orcRuns % 256) == 0;
            if (orcTraceRun) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu before-input-read\\n",
                        (void*)this, orcRuns);
                fflush(stderr);
            }
            int count = _in->read();
            if (orcTraceRun || count < 0) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu after-input-read count=%d\\n",
                        (void*)this, orcRuns, count);
                fflush(stderr);
            }
            if (count < 0) { return -1; }
            if (orcTraceRun) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu before-ring-write count=%d\\n",
                        (void*)this, orcRuns, count);
                fflush(stderr);
            }
            int written = ringBuf.write(_in->readBuf, count);
            if (orcTraceRun || written < 0) {
                fprintf(stderr, "[ORC reshape producer] self=%p run=%llu after-ring-write written=%d\\n",
                        (void*)this, orcRuns, written);
                fflush(stderr);
            }
            _in->flush();
            return written < 0 ? -1 : count;'''
    source = source.replace(marker, replacement, 1)
else:
    raise SystemExit("Could not locate SDR++ Reshaper::run()")

old = '''                if (ringBuf.readAndSkip(start, readCount, skip) < 0) { break; };
                memcpy(out.writeBuf, buf, _keep * sizeof(T));
                if (!out.swap(_keep)) { break; }'''
new = '''                static unsigned long long orcOutputs = 0;
                static unsigned long long orcWorkerLoops = 0;
                orcWorkerLoops++;
                bool orcTraceLoop = orcWorkerLoops <= 12 || (orcWorkerLoops % 256) == 0;
                if (orcTraceLoop) {
                    fprintf(stderr,
                            "[ORC reshape] worker=%p loop=%llu before-read keep=%d readCount=%d skip=%d\\n",
                            (void*)this, orcWorkerLoops, _keep, readCount, skip);
                    fflush(stderr);
                }
                int readResult = ringBuf.readAndSkip(start, readCount, skip);
                if (orcTraceLoop || readResult < 0) {
                    fprintf(stderr,
                            "[ORC reshape] worker=%p loop=%llu after-read result=%d\\n",
                            (void*)this, orcWorkerLoops, readResult);
                    fflush(stderr);
                }
                if (readResult < 0) {
                    fprintf(stderr,
                            "[ORC reshape] worker=%p stopped readResult=%d keep=%d readCount=%d skip=%d\\n",
                            (void*)this, readResult, _keep, readCount, skip);
                    fflush(stderr);
                    break;
                }
                memcpy(out.writeBuf, buf, _keep * sizeof(T));
                if (orcTraceLoop) {
                    fprintf(stderr,
                            "[ORC reshape] worker=%p loop=%llu before-swap keep=%d\\n",
                            (void*)this, orcWorkerLoops, _keep);
                    fflush(stderr);
                }
                bool swapped = out.swap(_keep);
                if (orcTraceLoop || !swapped) {
                    fprintf(stderr,
                            "[ORC reshape] worker=%p loop=%llu after-swap swap=%d\\n",
                            (void*)this, orcWorkerLoops, swapped ? 1 : 0);
                    fflush(stderr);
                }
                orcOutputs++;
                fprintf(stderr,
                        "[ORC reshape] worker=%p loop=%llu output=%llu keep=%d readCount=%d skip=%d swap=%d\\n",
                        (void*)this, orcWorkerLoops, orcOutputs, _keep, readCount, skip, swapped ? 1 : 0);
                fflush(stderr);
                if (!swapped) { break; }'''
if old not in source:
    raise SystemExit("Could not locate SDR++ Reshaper::bufferWorker() output")
source = source.replace(old, new, 1)

path.write_text(source)
PY

echo "[*] Instrumenting SDR++ FFT production for stalled-waterfall diagnosis"
python3 - "$SDRPP_SRC/core/src/signal_path/iq_frontend.cpp" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()

old = '''void IQFrontEnd::handler(dsp::complex_t* data, int count, void* ctx) {
    IQFrontEnd* _this = (IQFrontEnd*)ctx;

    // Apply window'''
new = '''void IQFrontEnd::handler(dsp::complex_t* data, int count, void* ctx) {
    IQFrontEnd* _this = (IQFrontEnd*)ctx;
    static unsigned long long orcFFTHandlers = 0;
    static unsigned long long orcFFTRejected = 0;
    orcFFTHandlers++;

    // Apply window'''
if old not in source:
    raise SystemExit("Could not locate SDR++ IQFrontEnd::handler()")
source = source.replace(old, new, 1)

old = '''    float* fftBuf = _this->_acquireFFTBuffer(_this->_fftCtx);

    // Convert the complex output of the FFT to dB amplitude
    if (fftBuf) {'''
new = '''    if (orcFFTHandlers <= 4) {
        fprintf(stderr, "[ORC FFT] handler=%llu acquiring waterfall buffer\\n", orcFFTHandlers);
        fflush(stderr);
    }
    float* fftBuf = _this->_acquireFFTBuffer(_this->_fftCtx);
    if (orcFFTHandlers <= 4) {
        fprintf(stderr, "[ORC FFT] handler=%llu acquired waterfall buffer=%p\\n",
                orcFFTHandlers, (void*)fftBuf);
        fflush(stderr);
    }
    if (!fftBuf) {
        orcFFTRejected++;
    }
    if (orcFFTHandlers <= 3 || (orcFFTHandlers % 256) == 0 || (!fftBuf && orcFFTRejected <= 3)) {
        fprintf(stderr,
                "[ORC FFT] handler=%llu count=%d fftSize=%d buffer=%p rejected=%llu\\n",
                orcFFTHandlers, count, _this->_fftSize, (void*)fftBuf, orcFFTRejected);
        fflush(stderr);
    }

    // Convert the complex output of the FFT to dB amplitude
    if (fftBuf) {'''
if old not in source:
    raise SystemExit("Could not locate SDR++ FFT buffer acquisition")
source = source.replace(old, new, 1)
path.write_text(source)
PY

echo "[*] Building SDR++ unoptimized with symbols for waterfall crash diagnosis"
cmake -S "$SDRPP_SRC" -B "$SDRPP_BUILD" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_C_FLAGS_DEBUG="-O0 -g3 -fno-omit-frame-pointer" \
  -DCMAKE_CXX_FLAGS_DEBUG="-O0 -g3 -fno-omit-frame-pointer" \
  -DOPT_BUILD_RIGCTL_SERVER=ON -DOPT_BUILD_BLADERF_SOURCE=OFF -DOPT_BUILD_PLUTOSDR_SOURCE=OFF -DOPT_BUILD_AIRSPY_SOURCE=OFF -DOPT_BUILD_AIRSPYHF_SOURCE=OFF
cmake --build "$SDRPP_BUILD" --parallel "$BUILD_JOBS"
[[ -x "$SDRPP_BUILD/sdrpp" ]] || { echo "SDR++ build completed but $SDRPP_BUILD/sdrpp was not found." >&2; exit 1; }

echo "[*] Preparing SDR++ development resources"
mkdir -p "$SDRPP_ROOT"; cp -a "$SDRPP_SRC/root/." "$SDRPP_ROOT/"
RIGCTL_MODULE="$(find "$SDRPP_BUILD" -type f -name 'rigctl_server.so' -print -quit)"
REMOTE_CONTROL_MODULE="$(find "$SDRPP_BUILD" -type f -name 'remote_control.so' -print -quit)"
TELEMETRY_MODULE="$(find "$SDRPP_BUILD" -type f -name 'telemetry.so' -print -quit)"
RTL_TCP_MODULE="$(find "$SDRPP_BUILD/source_modules/rtl_tcp_source" -type f -name 'rtl_tcp_source.so' -print -quit)"
RTL_SDR_MODULE="$(find "$SDRPP_BUILD/source_modules/rtl_sdr_source" -type f -name 'rtl_sdr_source.so' -print -quit)"
RADIO_MODULE="$(find "$SDRPP_BUILD/decoder_modules/radio" -type f -name 'radio.so' -print -quit)"
AUDIO_SINK_MODULE="$(find "$SDRPP_BUILD/sink_modules/audio_sink" -type f -name 'audio_sink.so' -print -quit)"
FREQUENCY_MANAGER_MODULE="$(find "$SDRPP_BUILD/misc_modules/frequency_manager" -type f -name 'frequency_manager.so' -print -quit)"
RECORDER_MODULE="$(find "$SDRPP_BUILD/misc_modules/recorder" -type f -name 'recorder.so' -print -quit)"
for pair in \
  "Rigctl Server:$RIGCTL_MODULE" \
  "OpenRoadCode remote control:$REMOTE_CONTROL_MODULE" \
  "OpenRoadCode telemetry:$TELEMETRY_MODULE" \
  "RTL-TCP source:$RTL_TCP_MODULE" \
  "RTL-SDR source:$RTL_SDR_MODULE" \
  "Radio:$RADIO_MODULE" \
  "Audio sink:$AUDIO_SINK_MODULE" \
  "Frequency manager:$FREQUENCY_MANAGER_MODULE" \
  "Recorder:$RECORDER_MODULE"; do
  name="${pair%%:*}"
  file="${pair#*:}"
  [[ -n "$file" ]] || { echo "$name module was not produced." >&2; exit 1; }
done
for module in "$REMOTE_CONTROL_MODULE" "$TELEMETRY_MODULE"; do
  echo "[*] Verifying $(basename "$module") SDR++ ABI exports"
  for symbol in _INFO_ _INIT_ _CREATE_INSTANCE_ _DELETE_INSTANCE_ _END_; do nm -D "$module" 2>/dev/null | grep -Eq "[[:space:]]${symbol}$" || { echo "$(basename "$module") is missing required SDR++ symbol: $symbol" >&2; exit 1; }; done
done
mkdir -p "$SDRPP_ROOT/modules"; rm -f "$SDRPP_ROOT/modules/"*.so
cp -f "$RIGCTL_MODULE" "$SDRPP_ROOT/modules/rigctl_server.so"
cp -f "$REMOTE_CONTROL_MODULE" "$SDRPP_ROOT/modules/remote_control.so"
cp -f "$TELEMETRY_MODULE" "$SDRPP_ROOT/modules/telemetry.so"
cp -f "$RTL_TCP_MODULE" "$SDRPP_ROOT/modules/rtl_tcp_source.so"
cp -f "$RTL_SDR_MODULE" "$SDRPP_ROOT/modules/rtl_sdr_source.so"
cp -f "$RADIO_MODULE" "$SDRPP_ROOT/modules/radio.so"
cp -f "$AUDIO_SINK_MODULE" "$SDRPP_ROOT/modules/audio_sink.so"
cp -f "$FREQUENCY_MANAGER_MODULE" "$SDRPP_ROOT/modules/frequency_manager.so"
cp -f "$RECORDER_MODULE" "$SDRPP_ROOT/modules/recorder.so"

if [[ -f "$SDRPP_ROOT/config.json" ]]; then
  echo "[*] Enabling SDR++ integration module instances"
  python3 - "$SDRPP_ROOT/config.json" <<'PY'
import json, sys
from pathlib import Path
path=Path(sys.argv[1]); data=json.loads(path.read_text()); instances=data.setdefault("moduleInstances", {})
instances.pop("ORC Telemetry", None)
instances["Remote Control"]={"module":"remote_control","enabled":True}
instances["Telemetry"]={"module":"telemetry","enabled":True}
path.write_text(json.dumps(data, indent=4)+"\n")
PY
fi

cat > "$SDRPP_ROOT/rigctl_server_config.json" <<'EOF'
{"Rigctl Server":{"host":"127.0.0.1","port":4532,"tuning":true,"recording":false,"autoStart":true,"vfo":"Radio","recorder":""}}
EOF

cat <<EOF
[+] SDR++ build complete
    source:         $SDRPP_SRC
    binary:         $SDRPP_BUILD/sdrpp
    resources:      $SDRPP_ROOT
    modules:        rtl_tcp_source.so, rtl_sdr_source.so, radio.so, audio_sink.so, frequency_manager.so,
                    recorder.so, rigctl_server.so, remote_control.so, telemetry.so
    rigctl:         127.0.0.1:4532
    remote control: 127.0.0.1:4533
    telemetry:      127.0.0.1:4534
EOF
DEBIAN
