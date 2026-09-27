#!/usr/bin/env python3
"""Patch upstream librtlsdr to use the OpenRoadCode Android USB proxy.

This deliberately changes only the USB transport. RTL2832U register logic,
R82xx tuner logic, gain/sample-rate handling, and the public librtlsdr ABI
remain upstream code.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_librtlsdr_orcu.py <librtlsdr-source>")

root = Path(sys.argv[1])
path = root / "src" / "librtlsdr.c"
text = path.read_text()

text = text.replace('#include <libusb.h>', '#include <libusb.h>\n#include "orcu_usb_transport.h"')
text = text.replace(
    'struct libusb_device_handle *devh;\n',
    'struct libusb_device_handle *devh;\n\tint orcu_fd;\n\tint orcu_mode;\n'
)

# All RTL2832U vendor control traffic uses the same libusb call shape.
text = text.replace(
    'libusb_control_transfer(dev->devh, CTRL_IN, 0, addr, index, array, len, CTRL_TIMEOUT)',
    'dev->orcu_mode ? orcu_control(dev->orcu_fd, CTRL_IN, 0, addr, index, array, len, CTRL_TIMEOUT) : libusb_control_transfer(dev->devh, CTRL_IN, 0, addr, index, array, len, CTRL_TIMEOUT)'
)
text = text.replace(
    'libusb_control_transfer(dev->devh, CTRL_OUT, 0, addr, index, array, len, CTRL_TIMEOUT)',
    'dev->orcu_mode ? orcu_control(dev->orcu_fd, CTRL_OUT, 0, addr, index, array, len, CTRL_TIMEOUT) : libusb_control_transfer(dev->devh, CTRL_OUT, 0, addr, index, array, len, CTRL_TIMEOUT)'
)
text = text.replace(
    'libusb_control_transfer(dev->devh, CTRL_IN, 0, addr, index, data, len, CTRL_TIMEOUT)',
    'dev->orcu_mode ? orcu_control(dev->orcu_fd, CTRL_IN, 0, addr, index, data, len, CTRL_TIMEOUT) : libusb_control_transfer(dev->devh, CTRL_IN, 0, addr, index, data, len, CTRL_TIMEOUT)'
)
text = text.replace(
    'libusb_control_transfer(dev->devh, CTRL_OUT, 0, addr, index, data, len, CTRL_TIMEOUT)',
    'dev->orcu_mode ? orcu_control(dev->orcu_fd, CTRL_OUT, 0, addr, index, data, len, CTRL_TIMEOUT) : libusb_control_transfer(dev->devh, CTRL_OUT, 0, addr, index, data, len, CTRL_TIMEOUT)'
)

# Proxy mode presents one known RTL2832U. SDR++ only needs stable strings for
# its device selector; Android owns the real USB descriptor access.
start = text.index('uint32_t rtlsdr_get_device_count(void)')
end = text.index('int rtlsdr_get_index_by_serial(', start)
replacement = r'''static int orcu_available(void)
{
	const char *enabled = getenv("OPENROADCODE_RTL_USB_PROXY");
	int fd;
	if (!enabled || !*enabled || !strcmp(enabled, "0"))
		return 0;
	fd = orcu_connect("127.0.0.1", 35100);
	if (fd < 0)
		return 0;
	orcu_close(fd);
	return 1;
}

uint32_t rtlsdr_get_device_count(void)
{
	if (getenv("OPENROADCODE_RTL_USB_PROXY"))
		return orcu_available() ? 1 : 0;
	return 0;
}

const char *rtlsdr_get_device_name(uint32_t index)
{
	if (getenv("OPENROADCODE_RTL_USB_PROXY") && index == 0)
		return "OpenRoadCode RTL2832U";
	return "";
}

int rtlsdr_get_device_usb_strings(uint32_t index, char *manufact, char *product, char *serial)
{
	if (!getenv("OPENROADCODE_RTL_USB_PROXY") || index != 0)
		return -1;
	if (manufact) { memset(manufact, 0, 256); strncpy(manufact, "OpenRoadCode", 255); }
	if (product) { memset(product, 0, 256); strncpy(product, "RTL2832U USB Proxy", 255); }
	if (serial) { memset(serial, 0, 256); strncpy(serial, "ORCU", 255); }
	return 0;
}

'''
text = text[:start] + replacement + text[end:]

# Replace open's libusb discovery/claim preamble while leaving all RTL/tuner
# initialization below it untouched.
open_start = text.index('int rtlsdr_open(rtlsdr_dev_t **out_dev, uint32_t index)')
init_marker = '\tdev->rtl_xtal = DEF_RTL_XTAL_FREQ;'
init_at = text.index(init_marker, open_start)
body_start = text.index('{', open_start) + 1
preamble = r'''
	int r = 0;
	uint8_t reg;
	rtlsdr_dev_t *dev = NULL;

	if (!getenv("OPENROADCODE_RTL_USB_PROXY") || index != 0)
		return -1;

	dev = malloc(sizeof(rtlsdr_dev_t));
	if (!dev)
		return -ENOMEM;
	memset(dev, 0, sizeof(rtlsdr_dev_t));
	memcpy(dev->fir, fir_default, sizeof(fir_default));
	dev->orcu_fd = -1;
	dev->orcu_mode = 1;
	dev->dev_lost = 1;

	fprintf(stderr, "[ORCU] connecting to Android USB proxy...\n");
	dev->orcu_fd = orcu_connect("127.0.0.1", 35100);
	if (dev->orcu_fd < 0) {
		fprintf(stderr, "[ORCU] connect failed\n");
		r = -1;
		goto err;
	}
	r = orcu_claim(dev->orcu_fd, 0, 1);
	fprintf(stderr, "[ORCU] claim interface 0: %d\n", r);
	if (r < 0)
		goto err;

'''
text = text[:body_start] + preamble + text[init_at:]

# Preserve upstream initialization behavior. The dummy-write reset must use\n# Android transport because proxy mode has no libusb device handle.
text = text.replace(
    'if (rtlsdr_write_reg(dev, USBB, USB_SYSCTL, 0x09, 1) < 0) {',
    'fprintf(stderr, "[ORCU] first RTL2832U register write...\\n");\n\tif (rtlsdr_write_reg(dev, USBB, USB_SYSCTL, 0x09, 1) < 0) {'
)
text = text.replace(
    'fprintf(stderr, "Resetting device...\\n");\n\t\tlibusb_reset_device(dev->devh);',
    'fprintf(stderr, "[ORCU] first register write failed; resetting proxy device...\\n");\n\t\tr = orcu_reset(dev->orcu_fd);\n\t\tfprintf(stderr, "[ORCU] reset result: %d\\n", r);\n\t\tif (r >= 0) { r = orcu_claim(dev->orcu_fd, 0, 1); fprintf(stderr, "[ORCU] reclaim result: %d\\n", r); }'
)
text = text.replace(
    '\trtlsdr_init_baseband(dev);',
    '\tfprintf(stderr, "[ORCU] initializing RTL2832U baseband...\\n");\n\trtlsdr_init_baseband(dev);\n\tfprintf(stderr, "[ORCU] baseband initialization returned\\n");'
)
text = text.replace(
    '\t/* Probe tuners */',
    '\tfprintf(stderr, "[ORCU] probing tuner over I2C...\\n");\n\t/* Probe tuners */'
)

# Descriptor strings are unavailable in protocol v1. Stable proxy strings are
# enough for tuner model checks and SDR++'s selector.
text = text.replace(
    'r = rtlsdr_get_usb_strings(dev, dev->manufact, dev->product, NULL);',
    'strncpy(dev->manufact, "OpenRoadCode", sizeof(dev->manufact) - 1);\n\tstrncpy(dev->product, "RTL2832U USB Proxy", sizeof(dev->product) - 1);\n\tr = 0;'
)

# Replace the old libusb cleanup tail in open().
err_at = text.index('err:', open_start)
close_at = text.index('\nint rtlsdr_close(', err_at)
text = text[:err_at] + r'''err:
	if (dev) {
		if (dev->orcu_fd >= 0) {
			orcu_release(dev->orcu_fd, 0);
			orcu_close(dev->orcu_fd);
		}
		free(dev);
	}
	return r;
}
''' + text[close_at:]

# Close and synchronous reads.
close_start = text.index('int rtlsdr_close(')
reset_start = text.index('\nint rtlsdr_reset_buffer(', close_start)
old_close = text[close_start:reset_start]
new_close = r'''int rtlsdr_close(rtlsdr_dev_t *dev)
{
	if (!dev)
		return -1;
	while (RTLSDR_INACTIVE != dev->async_status)
		usleep(1000);
	if (!dev->dev_lost)
		rtlsdr_deinit_baseband(dev);
	if (dev->orcu_fd >= 0) {
		orcu_release(dev->orcu_fd, 0);
		orcu_close(dev->orcu_fd);
	}
	free(dev);
	return 0;
}
'''
text = text.replace(old_close, new_close, 1)
text = text.replace(
    'return libusb_bulk_transfer(dev->devh, 0x81, buf, len, n_read, BULK_TIMEOUT);',
    'int r;\n\tr = orcu_bulk_read(dev->orcu_fd, 0x81, buf, len, 1000);\n\tif (n_read) *n_read = r > 0 ? r : 0;\n\treturn r < 0 ? r : 0;'
)

# Replace libusb async machinery with blocking proxy reads. SDR++ already runs
# rtlsdr_read_async on its own worker thread, so the public behavior is the same.
async_start = text.index('static void LIBUSB_CALL _libusb_callback(')
async_end = text.index('\nuint32_t rtlsdr_get_tuner_clock(', async_start)
async_code = r'''int rtlsdr_wait_async(rtlsdr_dev_t *dev, rtlsdr_read_async_cb_t cb, void *ctx)
{
	return rtlsdr_read_async(dev, cb, ctx, 0, 0);
}

int rtlsdr_read_async(rtlsdr_dev_t *dev, rtlsdr_read_async_cb_t cb, void *ctx,
			  uint32_t buf_num, uint32_t buf_len)
{
	unsigned char *buf;
	int n;
	(void)buf_num;
	if (!dev || !cb)
		return -1;
	if (RTLSDR_INACTIVE != dev->async_status)
		return -2;
	if (!buf_len || buf_len % 512)
		buf_len = DEFAULT_BUF_LENGTH;
	/* Preserve librtlsdr's normal async callback buffer size. The Android
	 * Bridge keeps multiple 256 KiB UsbRequests queued concurrently, so ORCU
	 * no longer needs oversized 1 MiB callbacks to avoid USB idle gaps. */
	buf = malloc(buf_len);
	if (!buf)
		return -ENOMEM;

	dev->async_status = RTLSDR_RUNNING;
	dev->async_cancel = 0;
	dev->cb = cb;
	dev->cb_ctx = ctx;

	fprintf(stderr, "[ORCU] read_async start: buf_num=%u buf_len=%u\\n", buf_num, buf_len);
	fflush(stderr);
	/* SDR++ may request small callback buffers (for example 11776 bytes).
	 * Android UsbRequest streaming must stay packet-aligned for RTL2832U bulk
	 * input, so request at least librtlsdr's normal 256 KiB transport chunk.
	 * The callback length may be larger than SDR++ requested, which upstream
	 * librtlsdr already permits for its default async buffering contract. */
	{
		int stream_len = (int)buf_len;
		if (stream_len < DEFAULT_BUF_LENGTH)
			stream_len = DEFAULT_BUF_LENGTH;
		if (orcu_stream_bulk_in_start(dev->orcu_fd, 0x81, stream_len, 250) < 0) {
		fprintf(stderr, "[ORCU] stream start failed\\n");
		fflush(stderr);
		free(buf);
		dev->async_status = RTLSDR_INACTIVE;
			return -1;
		}
	}
	fprintf(stderr, "[ORCU] stream command sent; waiting for IQ\\n");
	fflush(stderr);
	{
		unsigned int orcu_callbacks = 0;
		while (1) {
			n = orcu_stream_bulk_in_read(dev->orcu_fd, buf, (int)buf_len);
			if (n <= 0) {
				fprintf(stderr, "[ORCU] stream read ended: %d\\n", n);
				fflush(stderr);
				break;
			}
			orcu_callbacks++;
			if (orcu_callbacks <= 3) {
				fprintf(stderr, "[ORCU] IQ callback %u: %d bytes\\n", orcu_callbacks, n);
				fflush(stderr);
			}
			if (!dev->async_cancel)
				cb(buf, (uint32_t)n, ctx);
		}
	}
	free(buf);
	dev->async_status = RTLSDR_INACTIVE;
	return 0;
}

int rtlsdr_cancel_async(rtlsdr_dev_t *dev)
{
	if (!dev)
		return -1;
	if (RTLSDR_RUNNING != dev->async_status)
		return -2;
	dev->async_cancel = 1;
	/* STREAM_STOP is duplex: the control opcode wakes Android's queued USB
	 * requests while the read thread drains frames until the zero terminator. */
	return orcu_stream_bulk_in_stop(dev->orcu_fd);
}
'''
text = text[:async_start] + async_code + text[async_end:]

# Compile the ORCU transport into both upstream library targets.
cmake_path = root / "src" / "CMakeLists.txt"
cmake = cmake_path.read_text()
for target in ("rtlsdr", "rtlsdr_static"):
    marker = f"add_library({target} "
    pos = cmake.find(marker)
    if pos < 0:
        raise SystemExit(f"unable to find {target} target in src/CMakeLists.txt")
    line_end = cmake.find("\n", pos)
    first_line = cmake[pos:line_end]
    if "orcu_usb_transport.c" not in first_line:
        cmake = cmake[:line_end] + " orcu_usb_transport.c" + cmake[line_end:]
cmake_path.write_text(cmake)

path.write_text(text)
print(f"patched {path} and {cmake_path}")
