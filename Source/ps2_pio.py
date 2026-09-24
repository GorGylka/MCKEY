"""Bidirectional PS/2: DATA GP2, CLOCK GP3, open-drain PIO.
RX frames and TX hardware acknowledgements share a held-clock mailbox.
"""
from array import array
import board
import digitalio
import rp2pio

PROGRAM = '''
.side_set 1 pindirs
.wrap_target
rx:
set x, 10 side 0
mov isr, null side 0
bit:
wait 0 pin 1 side 0
in pins, 1 side 0
set y, 31 side 0
rise:
jmp pin risen side 0
jmp y-- rise side 0 [15]
jmp rx side 0
risen:
jmp x-- bit side 0
mailbox:
push block side 1
set y, 31 side 1
hold:
jmp y-- hold side 1 [3]
pull block side 1
jmp rx side 0
.wrap
public tx:
pull block side 1
set y, 31 side 1
txhold:
jmp y-- txhold side 1 [3]
set pindirs, 1 side 1
set x, 8 side 0
wait 1 pin 1 side 0
txbit:
wait 0 pin 1 side 0
out pindirs, 1 side 0
wait 1 pin 1 side 0
jmp x-- txbit side 0
wait 0 pin 1 side 0
set pindirs, 0 side 0
wait 1 pin 1 side 0
wait 0 pin 1 side 0
in pins, 1 side 0
wait 1 pin 1 side 0
wait 1 pin 0 side 0
jmp mailbox side 1
'''
# Filled by host assembler; no assembler library needed on the Pico.
PIO_WORDS = (57386, 41155, 8225, 16385, 57439, 200, 3973, 0, 66, 36896, 61535, 5003, 37024, 0, 37024, 61535, 5008, 61569, 57384, 8353, 8225, 24705, 8353, 84, 8225, 57472, 8353, 8225, 16385, 8353, 8352, 4105)
TX_ENTRY = 14
RX_WAIT = 2

class Receiver:
    def __init__(self):
        self.sm = rp2pio.StateMachine(array('H', PIO_WORDS), frequency=1_000_000,
            first_in_pin=board.GP2, in_pin_count=2, pull_in_pin_up=3,
            first_set_pin=board.GP2, set_pin_count=1,
            initial_set_pin_state=0, initial_set_pin_direction=0,
            first_out_pin=board.GP2, out_pin_count=1,
            initial_out_pin_state=0, initial_out_pin_direction=0,
            first_sideset_pin=board.GP3, sideset_pin_count=1,
            sideset_pindirs=True, initial_sideset_pin_state=0,
            initial_sideset_pin_direction=0, jmp_pin=board.GP3,
            jmp_pin_pull=digitalio.Pull.UP, fifo_type='txrx',
            in_shift_right=True, out_shift_right=True,
            auto_push=False, auto_pull=False, wait_for_txstall=False,
            wrap_target=0, wrap=13)
        self.word = array('I', [0])
        self.ack = array('I', [0])
        self.txword = array('I', [0])
        self.jump_tx = array('H', [0x1000 | (self.sm.offset + TX_ENTRY)])
        self.release_data = array('H', [0xe080])  # SET PINDIRS 0, side 0
        self.transmitting = False
        self.tx_result = None
        self.deadline = 0
        self.tx_error = None
        self.errors = 0
        self.count = 0
        self.last_byte_ms = 0

    def send(self, value, now):
        if self.transmitting or self.sm.in_waiting:
            return False
        # Caller also requires a quiet, complete scan-code sequence.
        if self.sm.pc != self.sm.offset + RX_WAIT:
            return False
        parity = 1
        for i in range(8): parity ^= (value >> i) & 1
        # GPIO output latch always LOW: a 1 direction drives 0 on the wire.
        self.txword[0] = (~(value | (parity << 8))) & 0x1ff
        self.tx_result = None
        self.tx_error = None
        self.transmitting = True
        self.deadline = now + 100
        # write() waits for the TX FIFO to drain even with wait_for_txstall=False.
        # Enter TX first: its PULL holds CLOCK low and waits for this payload.
        # Writing while RX waits for a key would block or feed the RX mailbox.
        self.sm.run(self.jump_tx)
        self.sm.write(self.txword)
        return True

    def poll_timeout(self, now):
        if self.transmitting and now >= self.deadline and not self.sm.in_waiting:
            self.tx_error = 'TX timeout at PIO PC ' + str(self.sm.pc - self.sm.offset)
            print('PS2:', self.tx_error)
            # Release both lines and reset PIO direction/shift state on failed TX.
            self.sm.run(self.release_data)
            self.sm.restart()
            self.transmitting = False
            self.tx_result = False
            self.errors += 1

    def read(self):
        if not self.sm.in_waiting: return None
        self.sm.readinto(self.word)
        self.sm.write(self.ack)
        if self.transmitting:
            # One-bit hardware ACK, separate from subsequent byte 0xFA.
            self.transmitting = False
            self.tx_result = not bool(self.word[0] & 0x80000000)
            if not self.tx_result:
                self.tx_error = 'Missing hardware ACK'
                print('PS2:', self.tx_error)
            return None
        raw = self.word[0] >> 21
        value = (raw >> 1) & 255
        parity = (raw >> 9) & 1
        ones = 0
        for i in range(8): ones += (value >> i) & 1
        if raw & 1 or not raw & 1024 or (ones + parity) % 2 != 1:
            self.errors += 1
            return -1
        self.count += 1
        return value

    def deinit(self): self.sm.deinit()
