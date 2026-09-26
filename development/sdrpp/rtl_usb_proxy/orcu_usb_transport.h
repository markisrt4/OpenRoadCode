#ifndef OPENROADCODE_ORCU_USB_TRANSPORT_H
#define OPENROADCODE_ORCU_USB_TRANSPORT_H
#include <stdint.h>
int orcu_connect(const char *host, uint16_t port);
int orcu_claim(int fd, int iface, int force);
int orcu_release(int fd, int iface);
int orcu_control(int fd, int request_type, int request, int value, int index, uint8_t *buf, int len, int timeout_ms);
int orcu_bulk_read(int fd, int endpoint, uint8_t *buf, int len, int timeout_ms);
int orcu_reset(int fd);
void orcu_close(int fd);
#endif
