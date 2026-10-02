"""Small, atomic settings store. No legacy formats or migrations."""
import os
import struct

PATH = '/settings.dat'
MAGIC = b'MKS1'
SIZE = 8


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _remove(path):
    if _exists(path):
        os.remove(path)


def _valid(path):
    try:
        with open(path, 'rb') as f:
            raw = f.read(SIZE + 1)
        if len(raw) != SIZE:
            return False
        magic, value, inverse, marker = struct.unpack('<4sBBH', raw)
        return (magic == MAGIC and value in (0, 1)
                and inverse == (value ^ 0xff) and marker == 0x5aa5)
    except (OSError, ValueError):
        return False


def recover():
    backup = PATH + '.bak'
    temp = PATH + '.tmp'
    if _exists(backup):
        if _valid(PATH):
            _remove(backup)
        elif _valid(backup):
            _remove(PATH)
            os.rename(backup, PATH)
    _remove(temp)


def load():
    if not _valid(PATH):
        return False
    with open(PATH, 'rb') as f:
        _, value, _, _ = struct.unpack('<4sBBH', f.read(SIZE))
    return bool(value)


def save(num_hotkey):
    value = 1 if num_hotkey else 0
    raw = struct.pack('<4sBBH', MAGIC, value, value ^ 0xff, 0x5aa5)
    temp = PATH + '.tmp'
    backup = PATH + '.bak'
    with open(temp, 'wb') as f:
        if f.write(raw) != SIZE:
            raise OSError('Short settings write')
        f.flush()
    if not _valid(temp):
        raise ValueError('Settings verify')
    if _exists(backup):
        raise OSError('Unresolved settings backup')
    if _exists(PATH):
        os.rename(PATH, backup)
    try:
        os.rename(temp, PATH)
    except OSError:
        if _exists(backup):
            os.rename(backup, PATH)
        raise
    _remove(backup)
