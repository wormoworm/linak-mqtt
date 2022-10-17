"""Entrypoint"""

import sys

import usb.core
import usb.util

dev = usb.core.find(idVendor=0x12d3, idProduct=0x0002)
if dev is None :
    raise ValueError("USB device not found")

wasAttached = False
print("About to attrmpt detach")
if dev.is_kernel_driver_active(0):
    try:
        dev.detach_kernel_driver(0)
        usb.util.claim_interface(dev, 0)
        wasAttached = True
        print("kernel driver detached")
    except usb.core.USBError as e:
        sys.exit("Could not detach kernel driver: ")
else:
    print("no kernel driver attached")