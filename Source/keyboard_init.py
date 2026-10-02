"""Bounded PS/2 keyboard startup handshake with Serial diagnostics."""
import time

ACK = 0xfa
RESEND = 0xfe
BAT_OK = 0xaa


def _ms():
    return time.monotonic_ns() // 1_000_000


def _read(rx):
    now = _ms()
    rx.poll_timeout(now)
    return rx.read()


def _wait_bat(rx, timeout_ms):
    deadline = _ms() + timeout_ms
    while _ms() < deadline:
        byte = _read(rx)
        if byte == BAT_OK:
            return True
        if byte not in (None, -1, ACK, RESEND):
            print('PS2 init: before BAT 0x%02X' % byte)
        time.sleep(0.001)
    return False


def _command(rx, value, label):
    for attempt in range(1, 4):
        print('PS2 init:', label, 'attempt', attempt)
        send_deadline = _ms() + 300
        sent = False
        while _ms() < send_deadline:
            now = _ms()
            rx.poll_timeout(now)
            byte = rx.read()
            if byte not in (None, -1, ACK, RESEND, BAT_OK):
                print('PS2 init: ignored 0x%02X' % byte)
            if not rx.transmitting and rx.send(value, now):
                sent = True
                break
            time.sleep(0.001)
        if not sent:
            print('PS2 init:', label, 'bus not idle')
            continue

        response_deadline = _ms() + 350
        resend = False
        while _ms() < response_deadline:
            byte = _read(rx)
            if rx.tx_result is False:
                print('PS2 init:', label, rx.tx_error or 'hardware ACK failed')
                resend = True
                break
            if byte == ACK:
                print('PS2 init:', label, 'ACK')
                return True
            if byte == RESEND:
                print('PS2 init:', label, 'RESEND')
                resend = True
                break
            if byte not in (None, -1, BAT_OK):
                print('PS2 init: ignored 0x%02X' % byte)
            time.sleep(0.001)
        if not resend:
            print('PS2 init:', label, 'command ACK timeout')
        time.sleep(0.05)
    return False


def initialize(rx):
    """Return True on complete initialization; never leave boot blocked."""
    print('PS2 init: waiting for power-on BAT')
    bat = _wait_bat(rx, 600)
    if bat:
        print('PS2 init: power-on BAT OK')
    else:
        print('PS2 init: no power-on BAT; sending RESET')
        if not _command(rx, 0xff, 'RESET'):
            print('PS2 init failed: RESET')
            return False
        if not _wait_bat(rx, 1200):
            print('PS2 init failed: no BAT after RESET')
            return False
        print('PS2 init: BAT OK')

    if not _command(rx, 0xf0, 'SET SCANCODE'):
        print('PS2 init failed: SET SCANCODE')
        return False
    if not _command(rx, 0x02, 'SCANCODE 2'):
        print('PS2 init failed: SCANCODE 2')
        return False
    if not _command(rx, 0xf4, 'ENABLE SCANNING'):
        print('PS2 init failed: ENABLE SCANNING')
        return False
    print('PS2 init complete: scan-code set 2 enabled')
    return True
