"""Macro Keyboard v1.7 — CircuitPython 10.x, RP2040 Zero / Pico.
No external libraries needed. See README_RU.md before installation.
"""
import gc
import os
import time
import struct
import supervisor
import usb_hid
from macro_core import CAPACITY, HEADER, TAP, DOWN, UP, MENU, Decoder, key_name, ascii_alnum
from macro_store import (Recorder, inspect, metadata, path_for, recover,
                         rename, delete)
from oled import OLED
from startup import stage, wait_usb, show_error, cleanup
from keyboard_leds import KeyboardLEDs


def ms(): return time.monotonic_ns() // 1_000_000

class HID:
    def __init__(self):
        self.dev = None
        for device in usb_hid.devices:
            if device.usage_page == 1 and device.usage == 6:
                self.dev = device
                break
        if self.dev is None: raise RuntimeError('No USB keyboard: check boot.py')
        self.keys = bytearray(256)
        self.report = bytearray(8)
    def send(self):
        for i in range(8): self.report[i] = 0
        for i in range(8): self.report[0] |= self.keys[224+i] << i
        pos = 2
        for k in range(4, 224):
            if self.keys[k]:
                if pos == 8:
                    # USB boot keyboard rollover error; state retained until release.
                    for j in range(2,8): self.report[j] = 1
                    break
                self.report[pos] = k
                pos += 1
        self.dev.send_report(self.report)
    def set(self, key, down):
        if self.keys[key] != down:
            self.keys[key] = down
            self.send()
    def release(self):
        for i in range(256): self.keys[i] = 0
        self.send()

class App:
    def __init__(self, screen):
        # No hardware operations in this constructor. Keep the instance
        # accessible to cleanup if initialize() fails halfway through.
        self.o = screen
        self.hid = None
        self.rx = None
        self.rec = None
        self.play = None

    def initialize(self):
        screen = self.o
        stage(screen, 'USB HID')
        self.hid = HID()
        self.decoder = Decoder()
        self.physical = bytearray(256)
        self.blocked = bytearray(256)
        self.state = 'splash'
        self.slot = self.choice = 0
        self.rec = self.play = None
        self.tap_key = None
        self.pulse_until = 0
        self.done = self.total = 0
        self.pending = None
        self.loop_play = False
        self.tail = ''
        self.name = ''
        self.message = ''
        self.message_until = 0
        self.dirty = True
        self.last_draw = self.last_gc = self.last_debug = 0
        self.deadline = 0
        self.meta = []
        stage(screen, 'MACRO FILES')
        for i in range(10):
            recover(i)
            self.meta.append(metadata(i))
        stage(screen, 'WAIT USB')
        wait_usb(self.hid)
        stage(screen, 'PS2 PIO')
        from ps2_pio import Receiver
        self.rx = Receiver()
        self.leds = KeyboardLEDs(self.hid.dev, self.rx)
        stage(screen, 'READY')
        self.o.animate(True, ms())
        self.draw(ms())
        print('Macro Keyboard 1.7; capacity', CAPACITY, '; free RAM', gc.mem_free())
        st = os.statvfs('/')
        print('Flash free:', st[0]*st[4], '; PS/2 DATA GP2 CLOCK GP3')

    def notice(self, text):
        self.message = text
        self.message_until = ms() + 3000
        self.dirty = True
        print(text)

    def options(self):
        return ('RECORD','PLAY','PLAY LOOP','DELETE','RENAME') if self.meta[self.slot] else ('RECORD',)

    def quiet(self):
        self.hid.release()
        for k in range(256): self.blocked[k] = self.physical[k]
        self.tap_key = None

    def start_record(self):
        self.rec = Recorder(self.slot)
        self.state = 'record'
        # Capture modifiers already held when HOME is pressed.
        now = ms()
        for key in range(224,232):
            if self.physical[key] and not self.blocked[key]: self.rec.add(DOWN,key,now)
        self.dirty = True

    def end_record(self, save):
        rec = self.rec
        if save:
            saved = rec.save()
        else:
            rec.cancel()
            saved = False
        self.rec = None
        self.meta[self.slot] = metadata(self.slot)
        self.state = 'actions'
        self.choice = 0
        self.notice('SAVED' if saved else 'CANCELLED')

    def start_play(self, loop=False):
        self.quiet()
        path = path_for(self.slot)
        _, self.total, _ = inspect(path, True)
        self.play = open(path,'rb')
        self.play.read(HEADER)
        self.done = 0
        self.loop_play = loop
        self.state = 'play'
        self.deadline = ms()
        self.next_event()
        self.dirty = True

    def next_event(self):
        if self.done == self.total:
            if not self.loop_play:
                self.stop_play(False)
                return
            # Release all modifiers between passes, including an unmatched DOWN.
            # Reuse the open file and preserve a USB release interval.
            self.hid.release()
            self.play.seek(HEADER)
            self.done = 0
            self.deadline = ms() + 12
            self.pulse_until = self.deadline
        raw = self.play.read(6)
        if len(raw) != 6: raise ValueError('Truncated macro')
        ticks, kind, key = struct.unpack('<IBB',raw)
        self.deadline += ticks * 100
        self.pending = kind, key

    def stop_play(self, cancelled):
        self.loop_play = False
        if self.play: self.play.close()
        self.play = None
        self.pending = None
        self.quiet()
        self.state = 'actions'
        self.notice('STOPPED' if cancelled else 'DONE %d/%d' % (self.done,self.total))

    def playback_tick(self, now):
        if self.tap_key is not None:
            if now < self.pulse_until: return
            self.hid.set(self.tap_key,False)
            self.tap_key = None
            self.pulse_until = now + 12  # Ensure separate USB release report.
            if self.state == 'play':
                self.done += 1
                self.next_event()
                self.dirty = True
            return
        if self.state != 'play' or now < self.pulse_until: return
        if now < self.deadline: return
        kind, key = self.pending
        if kind == TAP:
            self.hid.set(key,True)
            self.tap_key = key
            self.pulse_until = now + 12
        else:
            self.hid.set(key,kind == DOWN)
            self.done += 1
            self.next_event()
            self.dirty = True

    def navigate(self,key):
        if self.state == 'record':
            if key == 74: self.end_record(True)
            elif key == 77: self.end_record(False)
        elif self.state == 'play':
            if key == 77: self.stop_play(True)
        elif self.state == 'rename':
            if key == 77:
                self.quiet()
                self.state = 'actions'
            elif key == 74 and self.name.strip():
                rename(self.slot,self.name)
                self.meta[self.slot] = metadata(self.slot)
                self.quiet()
                self.state = 'actions'
                self.notice('RENAMED')
        elif self.state in ('overwrite','delete'):
            if key == 77: self.state = 'actions'
            elif key == 74:
                if self.state == 'overwrite': self.start_record()
                else:
                    delete(self.slot)
                    self.meta[self.slot] = None
                    self.state = 'actions'
                    self.choice = 0
                    self.notice('DELETED')
        elif self.state == 'splash':
            if key == 74: self.state = 'slots'
        elif self.state == 'slots':
            if key == 75: self.slot = (self.slot-1) % 10
            elif key == 78: self.slot = (self.slot+1) % 10
            elif key == 77: self.state = 'splash'
            elif key == 74:
                self.state = 'actions'
                self.choice = 0
        elif self.state == 'actions':
            options = self.options()
            if key == 75: self.choice = (self.choice-1) % len(options)
            elif key == 78: self.choice = (self.choice+1) % len(options)
            elif key == 77: self.state = 'slots'
            elif key == 74:
                action = options[self.choice]
                if action == 'RECORD':
                    if self.meta[self.slot]: self.state = 'overwrite'
                    else: self.start_record()
                elif action == 'PLAY': self.start_play()
                elif action == 'PLAY LOOP': self.start_play(True)
                elif action == 'DELETE': self.state = 'delete'
                elif action == 'RENAME':
                    self.quiet()
                    self.name = self.meta[self.slot][0]
                    self.state = 'rename'
        self.dirty = True

    def key_event(self,key,down,pulse,now):
        if down and self.physical[key]: return  # PS/2 typematic, not a new press
        self.physical[key] = down and not pulse
        if key in MENU:
            if down: self.navigate(key)
            return
        if not down:
            if self.blocked[key]:
                self.blocked[key] = 0
                return
        elif self.blocked[key]: return
        if self.state == 'rename':
            if down:
                if key == 42: self.name = self.name[:-1]
                else:
                    name = ' ' if key == 44 else key_name(key)
                    if len(name) == 1 and (name == ' ' or ascii_alnum(name)) and len(self.name) < 10:
                        self.name += name
                self.dirty = True
            return
        if self.state == 'play': return
        self.hid.set(key,down)
        if pulse and down:
            self.tap_key = key
            self.pulse_until = now + 12
        if down:
            self.tail = (self.tail + ' ' + key_name(key)).strip()[-21:]
            self.dirty = True
        if self.state == 'record':
            kind = (DOWN if down else UP) if 224 <= key <= 231 else TAP
            if down or kind == UP:
                if not self.rec.add(kind,key,now):
                    self.end_record(True)
                    self.notice('FULL - SAVED')
                self.dirty = True

    def input_error(self, text):
        self.decoder.reset()
        self.quiet()
        for i in range(256):
            self.physical[i] = self.blocked[i] = 0
        if self.rec: self.end_record(False)
        if self.play: self.stop_play(True)
        self.notice(text)

    def operation_error(self, exc):
        print('Operation error:', repr(exc))
        if self.rec:
            try: self.rec.cancel()
            except OSError: pass
            self.rec = None
        if self.play:
            self.play.close()
            self.play = None
        self.pending = None
        self.quiet()
        self.meta[self.slot] = metadata(self.slot)
        self.choice = 0
        self.state = 'actions'
        self.notice('ERROR - SEE SERIAL')

    def draw(self,now):
        if now < self.message_until:
            status = self.message
        else:
            status = self.tail
        self.o.clear()
        title = (self.meta[self.slot][0] if self.meta[self.slot]
                 else 'Macro%d' % (self.slot+1))
        if self.state == 'splash':
            self.o.splash()
            self.o.text('     Press HOME',5)
        elif self.state == 'slots':
            self.o.text('    MACROS %d/10' % (self.slot+1),0)
            first = min(max(0,self.slot-2),5)
            for row,i in enumerate(range(first,first+5),1):
                name = self.meta[i][0] if self.meta[i] else 'Macro %d EMPTY' % (i+1)
                self.o.text(('>' if i == self.slot else ' ') + name + ('<' if i == self.slot else ' '),row)
        elif self.state == 'actions':
            self.o.text('       ' + title,0)
            for row,action in enumerate(self.options(),1):
                self.o.text(('>' if row-1 == self.choice else ' ') + action + ('<' if row-1 == self.choice else ' '),row)
        elif self.state == 'record':
            self.o.text('       ' + title,0)
            self.o.text('Record %d/%d' % (self.rec.count,CAPACITY),2)
            self.o.text('HOME-SAVE',4)
            self.o.text('END-CANCEL',5)
        elif self.state == 'play':
            self.o.text('       ' + title,0)
            self.o.text('PLAY LOOP' if self.loop_play else 'PLAY',1)
            self.o.text('%d/%d' % (self.done,self.total),2)
            if self.deadline > now: self.o.text('WAIT %.1f S' % ((self.deadline-now)/1000),3)
            self.o.text('END-STOP',5)
        elif self.state == 'rename':
            self.o.text('RENAME A-Z 0-9 SPACE',0)
            self.o.text(self.name + '_' * (10-len(self.name)),2)
            self.o.text('BACKSPACE ERASE',4)
            self.o.text('HOME-SAVE END-CANCEL',5)
        elif self.state in ('overwrite','delete'):
            self.o.text('       ' + title,0)
            self.o.text('OVERWRITE?' if self.state == 'overwrite' else 'DELETE?',2)
            self.o.text('HOME-YES END-NO',4)
        self.o.text(status,7)
        self.o.invert_row(7)
        self.o.show()
        self.dirty = False
        self.last_draw = now

    def run(self):
        while True:
            now = ms()
            try:
                for _ in range(16):
                    byte = self.rx.read()
                    if byte is None: break
                    if self.leds.consume(byte, now):
                        continue
                    if byte == -1:
                        self.input_error('PS2 FRAME ERROR')
                        continue
                    if byte in (0x00,0xff,0xfc,0xfd):
                        self.input_error('PS2 DEVICE ERROR')
                        continue
                    if byte == 0xaa:
                        self.leds.keyboard_reset(now)
                        self.input_error('PS2 READY')
                        continue
                    decoded = self.decoder.feed(byte,now)
                    if decoded: self.key_event(*decoded,now)
                self.playback_tick(now)
                safe_leds = (self.state not in ('record', 'play')
                             and not any(self.physical)
                             and not self.decoder.ext and not self.decoder.brk
                             and not self.decoder.pause)
                boundary = not (self.decoder.ext or self.decoder.brk or self.decoder.pause)
                self.leds.tick(now, safe_leds, boundary)
            except (OSError, ValueError) as exc:
                self.operation_error(exc)
            if self.message and now >= self.message_until:
                self.message = ''
                self.dirty = True
            if self.o.animate(self.state == 'splash', now):
                self.dirty = True
            draw_interval = (min(100, self.o.animation.interval_ms)
                             if self.state == 'splash' else 100)
            if (self.dirty or self.state == 'play') and now-self.last_draw >= draw_interval:
                self.draw(now)
            if now-self.last_gc >= 5000:
                gc.collect()
                self.last_gc = now
            if now-self.last_debug >= 30000:
                print('RAM',gc.mem_free(),'PS2 bytes',self.rx.count,
                      'errors',self.rx.errors,'state',self.state)
                self.last_debug = now
            time.sleep(0.001)

supervisor.runtime.autoreload = False
screen = OLED()
stage(screen, 'START')
if not usb_hid.devices:
    screen.clear()
    screen.text('SERVICE MODE',1)
    screen.text('USB DRIVE ENABLED',3)
    screen.text('REMOVE GP15-GND',5)
    screen.text('THEN RESET',6)
    screen.show()
    print('SERVICE MODE: update files, safely eject, disconnect GP15-GND, reset.')
    while True: time.sleep(1)
else:
    app = None
    try:
        app = App(screen)
        app.initialize()
        app.run()
    except Exception as exc:
        try:
            show_error(screen, exc)
        except Exception as display_exc:
            print('Error screen failed:', repr(display_exc))
        raise
    finally:
        cleanup(app)
