"""Small SSD1306 I2C driver. Built-in 5x7 ASCII font, no font file required.
Optional logo.bin: 128x32, four SSD1306 pages (512 bytes).
"""
import busio
import board
from logo_anim import Animation

# Original compact uppercase font; five column bytes per glyph, top bit = row 0.
FONT = {
' ': '0000000000', 'A':'7e0909097e','B':'7f49494936','C':'3e41414122',
'D':'7f4141221c','E':'7f49494941','F':'7f09090901','G':'3e41495172',
'H':'7f0808087f','I':'00417f4100','J':'2040413f01','K':'7f08142241',
'L':'7f40404040','M':'7f020c027f','N':'7f0408107f','O':'3e4141413e',
'P':'7f09090906','Q':'3e4151215e','R':'7f09192946','S':'2649494932',
'T':'01017f0101','U':'3f4040403f','V':'1f2040201f','W':'3f4030403f',
'X':'6314081463','Y':'0304780403','Z':'6151494543',
'0':'3e4549513e','1':'00427f4000','2':'6251494946','3':'2241494936',
'4':'1814127f10','5':'2745454539','6':'3e49494932','7':'0171090503',
'8':'3649494936','9':'264949493e','-':'0808080808','_':'4040404040',
'.':'0060600000',':':'0036360000','/':'2010080402','>':'0041221408',
'<':'0814224100','!':'00005f0000','?':'0201510906','[':'007f414100',
']':'0041417f00','=':'1414141414','+':'08083e0808','*':'14083e0814',
';':'0056360000',"'":'0000030000',',':'0050300000','`':'0001020000'}
for k in FONT: FONT[k] = bytes.fromhex(FONT[k])

class OLED:
    def __init__(self):
        self.bus = busio.I2C(board.GP5, board.GP4, frequency=400000)
        while not self.bus.try_lock(): pass
        try:
            addresses = self.bus.scan()
            self.addr = 0x3c if 0x3c in addresses else 0x3d
            if self.addr not in addresses: raise RuntimeError('SSD1306 not found')
            self.bus.writeto(self.addr, bytes((0,0xae,0xd5,0x80,0xa8,0x3f,
                0xd3,0,0x40,0x8d,0x14,0x20,0,0xa1,0xc8,0xda,0x12,
                0x81,0x7f,0xd9,0xf1,0xdb,0x40,0xa4,0xa6,0xaf)))
        finally: self.bus.unlock()
        self.buf = bytearray(1025)
        self.buf[0] = 0x40
        self.zero = bytes(1024)
        self.animation = Animation()
        self.logo = None
        try:
            with open('/logo.bin','rb') as f: raw = f.read(513)
            if len(raw) == 512: self.logo = raw
        except OSError: pass
        self.clear()
        self.show()
    def clear(self): self.buf[1:] = self.zero
    def text(self, s, row, col=0):
        offset = 1 + row * 128 + col * 6
        for c in s.upper()[:21-col]:
            glyph = FONT.get(c, FONT['?'])
            self.buf[offset:offset+5] = glyph
            offset += 6
    def invert_row(self, row):
        # One SSD1306 page = one 8-pixel text row, full 128-pixel width.
        start = 1 + row * 128
        for offset in range(start, start + 128):
            self.buf[offset] ^= 0xff
        # Bottom status strip: one white padding pixel above the glyphs.
        if row == 7:
            for offset in range(start - 128, start):
                self.buf[offset] |= 0x80

    def animate(self, active, now):
        return self.animation.tick(active, now)
    def splash(self):
        if self.animation.ready: self.buf[1:513] = self.animation.frame
        elif self.logo: self.buf[1:513] = self.logo
        else:
            self.text('MACRO',1,8)
            self.text('KEYBOARD',2,6)
    def show(self):
        while not self.bus.try_lock(): pass
        try:
            self.bus.writeto(self.addr,b'\x00\x21\x00\x7f\x22\x00\x07')
            self.bus.writeto(self.addr,self.buf)
        finally: self.bus.unlock()
