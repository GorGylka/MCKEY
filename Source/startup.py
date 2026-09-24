"""Visible boot progress and bounded USB readiness handshake."""
import time

STAGE = 'START'

def stage(screen, name):
    global STAGE
    STAGE = name
    print('BOOT:', name)
    screen.clear()
    screen.text('MACRO KEYBOARD 1.7', 0)
    screen.text(name, 3)
    screen.show()

def wait_usb(hid, timeout=10):
    # Device enumeration does not mean the HID endpoint is ready yet.
    deadline = time.monotonic() + timeout
    while True:
        try:
            hid.release()
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise RuntimeError('USB HID NOT READY')
            time.sleep(0.05)

def show_error(screen, exc):
    print('FAILED AT:', STAGE, type(exc).__name__, str(exc))
    screen.clear()
    screen.text('START/RUN ERROR',0)
    screen.text(STAGE,1)
    screen.text(type(exc).__name__,2)
    message = str(exc)
    for row in range(3,7):
        screen.text(message[(row-3)*21:(row-2)*21],row)
    screen.text('FULL ERROR IN SERIAL',7)
    screen.show()

def cleanup(app):
    if app is None: return
    # Cleanup failures must never hide the original traceback.
    for attr, method in (('hid','release'),('play','close'),
                         ('rec','cancel'),('rx','deinit')):
        obj = getattr(app,attr,None)
        if obj is not None:
            try: getattr(obj,method)()
            except Exception as exc: print('Cleanup:',attr,repr(exc))

    screen = getattr(app, 'o', None)
    animation = getattr(screen, 'animation', None)
    if animation is not None:
        try: animation.close()
        except Exception as exc: print('Animation cleanup:', repr(exc))
