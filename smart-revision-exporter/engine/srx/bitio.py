"""Bit-level reading/writing helpers for H.264 RBSP parsing.

Implements exp-Golomb coding and emulation-prevention byte handling exactly as
specified in ITU-T H.264 section 7.2 / 7.4.1 and 9.1.
"""

from __future__ import annotations


class BitstreamError(ValueError):
    pass


def nal_to_rbsp(data: bytes) -> bytes:
    """Remove emulation_prevention_three_byte (0x000003 -> 0x0000)."""
    if b"\x00\x00\x03" not in data:
        return bytes(data)
    out = bytearray()
    zeros = 0
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if zeros >= 2 and b == 0x03:
            # Skip emulation prevention byte.
            zeros = 0
            i += 1
            continue
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
        i += 1
    return bytes(out)


def rbsp_to_nal(rbsp: bytes) -> bytes:
    """Insert emulation prevention bytes where required."""
    out = bytearray()
    zeros = 0
    for b in rbsp:
        if zeros >= 2 and b <= 0x03:
            out.append(0x03)
            zeros = 0
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
    return bytes(out)


class BitReader:
    __slots__ = ("data", "pos", "nbits")

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.nbits = len(data) * 8

    def bits_left(self) -> int:
        return self.nbits - self.pos

    def u(self, n: int) -> int:
        if n == 0:
            return 0
        if self.pos + n > self.nbits:
            raise BitstreamError("read past end of bitstream")
        v = 0
        for _ in range(n):
            byte = self.data[self.pos >> 3]
            bit = (byte >> (7 - (self.pos & 7))) & 1
            v = (v << 1) | bit
            self.pos += 1
        return v

    def flag(self) -> bool:
        return self.u(1) == 1

    def ue(self) -> int:
        zeros = 0
        while self.u(1) == 0:
            zeros += 1
            if zeros > 32:
                raise BitstreamError("invalid exp-golomb code")
        if zeros == 0:
            return 0
        return (1 << zeros) - 1 + self.u(zeros)

    def se(self) -> int:
        k = self.ue()
        if k & 1:
            return (k + 1) >> 1
        return -(k >> 1)

    def byte_aligned(self) -> bool:
        return (self.pos & 7) == 0

    def more_rbsp_data(self) -> bool:
        """True if there is more data before the rbsp_trailing_bits."""
        if self.pos >= self.nbits:
            return False
        # Find last set bit (the rbsp_stop_one_bit).
        data = self.data
        last = len(data) - 1
        while last >= 0 and data[last] == 0:
            last -= 1
        if last < 0:
            return False
        byte = data[last]
        trailing = 0
        while (byte >> trailing) & 1 == 0:
            trailing += 1
        stop_bit_pos = last * 8 + (7 - trailing)
        return self.pos < stop_bit_pos


class BitWriter:
    __slots__ = ("out", "cur", "nbits")

    def __init__(self):
        self.out = bytearray()
        self.cur = 0
        self.nbits = 0

    def u(self, n: int, value: int) -> None:
        for i in range(n - 1, -1, -1):
            self.cur = (self.cur << 1) | ((value >> i) & 1)
            self.nbits += 1
            if self.nbits == 8:
                self.out.append(self.cur)
                self.cur = 0
                self.nbits = 0

    def flag(self, b: bool) -> None:
        self.u(1, 1 if b else 0)

    def ue(self, value: int) -> None:
        v = value + 1
        length = v.bit_length()
        self.u(length - 1, 0)
        self.u(length, v)

    def se(self, value: int) -> None:
        if value > 0:
            self.ue(2 * value - 1)
        else:
            self.ue(-2 * value)

    def trailing_bits(self) -> None:
        self.u(1, 1)
        while self.nbits != 0:
            self.u(1, 0)

    def getvalue(self) -> bytes:
        if self.nbits:
            raise BitstreamError("bit writer not byte aligned")
        return bytes(self.out)
