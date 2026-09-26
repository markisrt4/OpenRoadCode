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

	dev->orcu_fd = orcu_connect("127.0.0.1", 35100);
	if (dev->orcu_fd < 0) {
		r = -1;
		goto err;
	}
	r = orcu_claim(dev->orcu_fd, 0, 1);
	if (r < 0)
		goto err;

'''
text = text[:body_start] + preamble + text[init_at:]

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
	buf = malloc(buf_len);
	if (!buf)
		return -ENOMEM;

	dev->async_status = RTLSDR_RUNNING;
	dev->async_cancel = 0;
	dev->cb = cb;
	dev->cb_ctx = ctx;

	while (!dev->async_cancel) {
		n = orcu_bulk_read(dev->orcu_fd, 0x81, buf, (int)buf_len, 250);
		if (n > 0)
			cb(buf, (uint32_t)n, ctx);
		else if (n < 0 && !dev->async_cancel) {
			/* Android reports a timeout as a negative bulk result. Keep
			 * polling so cancellation remains bounded and cheap. */
			continue;
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
	return 0;
}
'''
text = text[:async_start] + async_code + text[async_end:]

# Compile the ORCU transport into both librtlsdr shared/static targets.
cmake_path = root / "src" / "CMakeLists.txt"
cmake = cmake_path.read_text()
if "orcu_usb_transport.c" not in cmake:
    marker = "set(rtlsdr_sources\n"
    if marker not in cmake:
        raise SystemExit("unable to find rtlsdr_sources in src/CMakeLists.txt")
    cmake = cmake.replace(marker, marker + "    orcu_usb_transport.c\n", 1)
    cmake_path.write_text(cmake)

path.write_text(text)
print(f"patched {path} and {cmake_path}")
