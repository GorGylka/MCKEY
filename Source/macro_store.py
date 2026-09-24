import os
import struct
from macro_core import (LIMIT, HEADER, EVENT, CAPACITY, header, parse_header,
                        event, checksum_update)

def exists(path):
    try: os.stat(path); return True
    except OSError: return False

def remove(path):
    if exists(path): os.remove(path)

def path_for(slot): return '/macros%d.dat' % (slot + 1)

def inspect(path, full=False):
    with open(path, 'rb') as f:
        name, count, check = parse_header(f.read(HEADER))
        if os.stat(path)[6] != HEADER + count * EVENT: raise ValueError('File size')
        if full:
            value = 1
            for _ in range(count):
                raw = f.read(EVENT)
                ticks, kind, key = struct.unpack('<IBB', raw)
                event(ticks, kind, key)
                value = checksum_update(value, raw)
            if value != check: raise ValueError('Checksum')
        return name, count, check

def valid(path):
    try: inspect(path, True); return True
    except (OSError, ValueError, UnicodeError): return False

def recover(slot):
    path = path_for(slot)
    # Only a interrupted replacement needs full recovery validation.
    if exists(path + '.bak'):
        if valid(path): remove(path + '.bak')
        elif valid(path + '.bak'):
            remove(path)
            os.rename(path + '.bak', path)
        # If both invalid, leave evidence for service mode.
    # A temp file is never committed unless the user chose Save.
    remove(path + '.tmp')

def commit(path):
    backup = path + '.bak'
    if exists(backup): raise OSError('Unresolved backup')
    if exists(path): os.rename(path, backup)
    try: os.rename(path + '.tmp', path)
    except OSError:
        if exists(backup): os.rename(backup, path)
        raise
    remove(backup)

def metadata(slot):
    try: return inspect(path_for(slot))
    except (OSError, ValueError, UnicodeError): return None

class Recorder:
    def __init__(self, slot):
        st = os.statvfs('/')
        if st[0] * st[4] < LIMIT + 8192: raise OSError('Need 88 KiB free')
        self.path = path_for(slot)
        self.name = 'Macro%d' % (slot+1)
        self.count = 0
        self.checksum = 1
        self.last_ms = None
        self.f = open(self.path + '.tmp', 'wb')
        self.f.write(b'\0' * HEADER)
    def add(self, kind, key, now_ms):
        if self.count >= CAPACITY: return False
        # Round each event's timestamp relative to first action, so rounding
        # errors do not accumulate across thousands of short intervals.
        if self.last_ms is None:
            self.origin_ms = now_ms
            self.last_ms = 0
        stamp = (now_ms - self.origin_ms + 50) // 100
        ticks = stamp - self.last_ms
        raw = event(ticks, kind, key)
        if self.f.write(raw) != EVENT: raise OSError('Short write')
        self.checksum = checksum_update(self.checksum, raw)
        self.count += 1
        self.last_ms = stamp
        if self.count % 64 == 0: self.f.flush()
        return self.count < CAPACITY
    def cancel(self):
        if self.f:
            self.f.close()
            self.f = None
        remove(self.path + '.tmp')
    def save(self):
        if not self.count:
            self.cancel()
            return False
        self.f.seek(0)
        self.f.write(header(self.name, self.count, self.checksum))
        self.f.flush()
        self.f.close()
        self.f = None
        inspect(self.path + '.tmp', True)
        commit(self.path)
        return True

def rename(slot, name):
    path = path_for(slot)
    _, count, checksum = inspect(path, True)
    with open(path, 'rb') as src, open(path + '.tmp', 'wb') as dst:
        src.read(HEADER)
        dst.write(header(name, count, checksum))
        while True:
            data = src.read(512)
            if not data: break
            dst.write(data)
        dst.flush()
    inspect(path + '.tmp', True)
    commit(path)

def delete(slot):
    path = path_for(slot)
    remove(path)
    remove(path + '.bak')
    remove(path + '.tmp')
