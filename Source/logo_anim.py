"""Stream monochrome logo frames. No sleeps, one reusable 512-byte frame."""
import os
import struct

# None uses the period in the file (100 ms). Set 50 for 20 fps, 200 for 5 fps.
FRAME_MS_OVERRIDE = 50

class Animation:
    def __init__(self, path='/logo.anim'):
        self.path = path
        self.file = None
        self.frame = bytearray(512)
        self.ready = False
        self.disabled = False
        self.interval_ms = 100
        self.index = -1
        self.started = 0
        self.count = 0

    def close(self):
        if self.file is not None:
            try:
                self.file.close()
            finally:
                self.file = None
        self.ready = False
        self.index = -1

    def _open(self, now):
        self.file = open(self.path, 'rb')
        header = self.file.read(12)
        if len(header) != 12:
            raise ValueError('Short animation header')
        magic, width, height, count, period = struct.unpack('<4sHHHH', header)
        if magic != b'LA01' or width != 128 or height != 32 or count < 1:
            raise ValueError('Bad animation header')
        period = FRAME_MS_OVERRIDE if FRAME_MS_OVERRIDE is not None else period
        if not 50 <= period <= 10000:
            raise ValueError('Animation period 50..10000 ms required')
        if os.stat(self.path)[6] != 12 + count * 512:
            raise ValueError('Bad animation size')
        self.interval_ms = period
        self.count = count
        self.started = now

    def tick(self, active, now):
        if not active:
            if self.file is not None:
                self.close()
            return False
        if self.disabled:
            return False
        try:
            if self.file is None:
                self._open(now)
            target = ((now - self.started) // self.interval_ms) % self.count
            if target == self.index:
                return False
            # Late frames are skipped, never replayed in a blocking catch-up loop.
            self.file.seek(12 + target * 512)
            if self.file.readinto(self.frame) != 512:
                raise ValueError('Short animation frame')
            self.index = target
            self.ready = True
            return True
        except (OSError, ValueError) as exc:
            print('Logo animation disabled:', repr(exc))
            try:
                self.close()
            except OSError:
                self.file = None
                self.ready = False
            self.disabled = True
            return True  # Redraw using the static/text fallback.
