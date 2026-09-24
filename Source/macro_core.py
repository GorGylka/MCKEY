"""Hardware-independent format and PS/2 set-2 decoder. Original implementation."""
import struct

LIMIT = 80 * 1024
HEADER = 32
EVENT = 6
CAPACITY = (LIMIT - HEADER) // EVENT
MAX_TICKS = 0xFFFFFFFF
TAP, DOWN, UP = 0, 1, 2
MAGIC = b'MK01'
MENU = (74, 77, 75, 78)  # Home End PageUp PageDown, USB usage IDs

# Standard PS/2 scan-code set 2 -> USB Keyboard/Keypad usage.
BASE = {
0x1c:4,0x32:5,0x21:6,0x23:7,0x24:8,0x2b:9,0x34:10,0x33:11,
0x43:12,0x3b:13,0x42:14,0x4b:15,0x3a:16,0x31:17,0x44:18,
0x4d:19,0x15:20,0x2d:21,0x1b:22,0x2c:23,0x3c:24,0x2a:25,
0x1d:26,0x22:27,0x35:28,0x1a:29,
0x16:30,0x1e:31,0x26:32,0x25:33,0x2e:34,0x36:35,0x3d:36,
0x3e:37,0x46:38,0x45:39,0x5a:40,0x76:41,0x66:42,0x0d:43,
0x29:44,0x4e:45,0x55:46,0x54:47,0x5b:48,0x5d:49,0x4c:51,
0x52:52,0x0e:53,0x41:54,0x49:55,0x4a:56,0x58:57,
0x05:58,0x06:59,0x04:60,0x0c:61,0x03:62,0x0b:63,0x83:64,
0x0a:65,0x01:66,0x09:67,0x78:68,0x07:69,0x7e:71,
0x77:83,0x7c:85,0x7b:86,0x79:87,0x69:89,0x72:90,0x7a:91,
0x6b:92,0x73:93,0x74:94,0x6c:95,0x75:96,0x7d:97,0x70:98,
0x71:99,0x61:100,0x14:224,0x12:225,0x11:226,0x59:229,
}
EXT = {0x14:228,0x11:230,0x1f:227,0x27:231,0x2f:101,
0x4a:84,0x5a:88,0x70:73,0x6c:74,0x7d:75,0x71:76,0x69:77,
0x7a:78,0x74:79,0x6b:80,0x72:81,0x75:82,0x7c:70}
VALID = frozenset(BASE.values()) | frozenset(EXT.values()) | {72}
NAMES = {40:'ENTER',41:'ESC',42:'BACKSPACE',43:'TAB',44:'SPACE',
45:'-',46:'=',47:'[',48:']',49:'BACKSLASH',51:';',52:"'",53:'`',
54:',',55:'.',56:'/',57:'CAPS',70:'PRINT',71:'SCROLL',72:'PAUSE',
73:'INSERT',74:'HOME',75:'PAGEUP',76:'DELETE',77:'END',78:'PAGEDOWN',
79:'RIGHT',80:'LEFT',81:'DOWN',82:'UP',83:'NUMLOCK',84:'/',85:'*',
86:'-',87:'+',88:'ENTER',98:'0',99:'.',100:'BACKSLASH',101:'MENU',
224:'CTRL',225:'SHIFT',226:'ALT',227:'WINDOWS',228:'CTRL',229:'SHIFT',
230:'ALT',231:'WINDOWS'}

def key_name(key):
    if 4 <= key <= 29: return chr(65 + key - 4)
    if 30 <= key <= 39: return '1234567890'[key-30]
    if 58 <= key <= 69: return 'F' + str(key-57)
    if 89 <= key <= 97: return str(key-88)
    return NAMES.get(key, '?')

class Decoder:
    def __init__(self): self.reset()
    def reset(self):
        self.ext = False
        self.brk = False
        self.pause = 0
        self.last = 0
    def feed(self, byte, now):
        # Prefixes must not survive a truncated PS/2 sequence.
        if now - self.last > 250: self.reset()
        self.last = now
        if self.pause:
            expected = (0x14,0x77,0xe1,0xf0,0x14,0xf0,0x77)
            if byte != expected[self.pause-1]:
                self.reset()
                return None
            self.pause += 1
            if self.pause == 8:
                self.reset()
                return (72, True, True)  # Pause has no break code
            return None
        if byte == 0xe1:
            self.pause = 1
            return None
        if byte == 0xe0:
            self.ext = True
            return None
        if byte == 0xf0:
            self.brk = True
            return None
        key = (EXT if self.ext else BASE).get(byte)
        down = not self.brk
        self.ext = self.brk = False
        # E0 12/E0 F0 12 are PrintScreen's fake shift, deliberately unmapped.
        return (key, down, False) if key is not None else None

def ascii_alnum(text):
    # CircuitPython 10.2.1 does not provide str.isalnum().
    if not text:
        return False
    for char in text:
        if not ('A' <= char <= 'Z' or 'a' <= char <= 'z' or '0' <= char <= '9'):
            return False
    return True

def valid_name(name):
    return (1 <= len(name) <= 10 and bool(name.strip())
            and all(char == ' ' or ascii_alnum(char) for char in name))

def header(name, count, checksum):
    if not valid_name(name):
        raise ValueError('Bad name')
    raw = name.encode('ascii')
    return struct.pack('<4sII10s10s', MAGIC, count, checksum, raw, b'\0'*10)

def parse_header(raw):
    if len(raw) != HEADER: raise ValueError('Short header')
    magic, count, checksum, name, reserved = struct.unpack('<4sII10s10s', raw)
    name = name.rstrip(b'\0').decode('ascii')
    if magic != MAGIC or not 1 <= count <= CAPACITY: raise ValueError('Bad header')
    if not valid_name(name) or reserved != b'\0'*10:
        raise ValueError('Bad name/header')
    return name, count, checksum

def checksum_update(value, data):
    # Adler-32, initialized to 1. No external package needed.
    a, b = value & 65535, value >> 16
    for v in data:
        a = (a + v) % 65521
        b = (b + a) % 65521
    return (b << 16) | a

def event(ticks, kind, key):
    if not 0 <= ticks <= MAX_TICKS: raise ValueError('Delay limit')
    if key not in VALID or key in MENU: raise ValueError('Bad key')
    if kind == TAP:
        if key >= 224: raise ValueError('Modifier tap')
    elif kind in (DOWN, UP):
        if not 224 <= key <= 231: raise ValueError('Not modifier')
    else: raise ValueError('Bad event')
    return struct.pack('<IBB', ticks, kind, key)
