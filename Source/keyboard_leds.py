"""Synchronize the three PS/2 LEDs from USB HID output reports.
USB: Num=bit0, Caps=bit1, Scroll=bit2; PS/2: Scroll=0, Num=1, Caps=2.
"""
ENABLED = True

def ps2_mask(usb_mask):
    return ((usb_mask & 1) << 1) | ((usb_mask & 2) << 1) | ((usb_mask & 4) >> 2)

class KeyboardLEDs:
    def __init__(self, device, receiver):
        self.device = device
        self.rx = receiver
        self.enabled = ENABLED
        self.desired = None  # Wait for an actual host report, don't guess OS state.
        self.applied = None
        self.target = 0
        self.phase = 'idle'
        self.waiting = False
        self.attempts = 0
        self.deadline = 0
        self.next_at = 1000
        self.next_poll = 0
        self.last_input = 0
        self.error = None

    def keyboard_reset(self, now):
        self.applied = None
        self.phase = 'idle'
        self.waiting = False
        self.attempts = 0
        self.next_at = now + 500

    def _retry(self, now, reason):
        self.waiting = False
        self.rx.tx_result = None
        if self.attempts >= 3:
            self.error = reason
            self.enabled = False
            self.phase = 'idle'
            print('LED sync disabled:', reason, '; restart to retry')
        else:
            self.next_at = now + 100
            print('LED retry:', self.phase, reason)

    def consume(self, byte, now):
        # These command responses are never keystrokes and never macro events.
        if byte not in (0xfa, 0xfe):
            self.last_input = now
            return False
        if not self.waiting:
            return True
        if byte == 0xfe:
            self._retry(now, 'RESEND')
            return True
        self.waiting = False
        self.rx.tx_result = None
        self.attempts = 0
        if self.phase == 'command':
            self.phase = 'mask'
            self.next_at = now + 2
        elif self.phase == 'mask':
            self.applied = self.target
            self.phase = 'idle'
            print('PS2 LEDs synced:', self.applied)
        return True

    def tick(self, now, safe, boundary=True):
        self.rx.poll_timeout(now)
        if not self.enabled:
            return
        if now >= self.next_poll:
            self.next_poll = now + 50
            try:
                report = self.device.get_last_received_report()
                if report is not None and len(report):
                    self.desired = ps2_mask(report[0])
            except (OSError, ValueError, AttributeError) as exc:
                self.enabled = False
                self.error = str(exc)
                print('USB LED report unavailable:', repr(exc))
                return
        if self.waiting:
            if self.rx.tx_result is False:
                self._retry(now, self.rx.tx_error or 'TX failed')
            elif now >= self.deadline:
                self._retry(now, 'No command ACK')
            return
        if now < self.next_at or not boundary:
            return
        if self.phase == 'idle':
            if not safe or now - self.last_input < 50:
                return
            if self.desired is None or self.desired == self.applied:
                return
            self.target = self.desired
            self.phase = 'command'
            self.attempts = 0
        # Finish an already accepted ED transaction even if a menu action occurs.
        # Receiver.send only takes over at its receive-edge wait point.
        value = 0xed if self.phase == 'command' else self.target
        if self.rx.send(value, now):
            self.attempts += 1
            self.waiting = True
            self.deadline = now + 200
