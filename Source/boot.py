# GP15 -> GND during power-on/reset = writable USB service drive.
import board
import digitalio
import storage
import usb_hid
import usb_cdc
import usb_midi

service_pin = digitalio.DigitalInOut(board.GP15)
service_pin.switch_to_input(pull=digitalio.Pull.UP)
service = not service_pin.value
service_pin.deinit()
usb_midi.disable()
usb_cdc.enable(console=service, data=False)
if service:
    storage.enable_usb_drive()
    usb_hid.disable()
else:
    storage.disable_usb_drive()
    storage.remount('/', readonly=False)
    usb_hid.enable((usb_hid.Device.KEYBOARD,))
