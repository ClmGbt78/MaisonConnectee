import os
if os.name == 'nt':
	from .winusbpy import *
	from .winusb import *
	from .usb_cdc import ComPort
else:
	raise ImportError("WinUsbPy only works on Windows platform")
