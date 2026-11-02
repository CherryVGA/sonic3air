#!/usr/bin/env python3
"""
Kosinski decompressor, ported directly (not from an external library) from
Oxygen Engine's own lemonscript implementation at
scripts/general/kosinski.lemon (Kosinski.Decompress / Kosinski.readBit),
which is itself a faithful port of Sonic 2/3K's original 68K decompression
routine. Used to decompress s2disasm's level/layout/*.kos files into the
raw bytes the engine's Level_Layout RAM buffer (and Oxygen's standalone
rawdata layout_actN.bin override) expects.
"""
import sys


class KosinskiState:
    def __init__(self, data, start=0):
        self.data = data
        self.pos = start
        self.bitbuf = 0
        self.bitcount = 0
        self._load_word()

    def _load_word(self):
        self.bitbuf = self.data[self.pos] + (self.data[self.pos + 1] << 8)
        self.pos += 2
        self.bitcount = 0x0f

    def read_bit(self):
        bit = self.bitbuf & 1
        self.bitbuf >>= 1
        self.bitcount -= 1
        if self.bitcount < 0:
            self._load_word()
        return bit

    def read_u8(self):
        b = self.data[self.pos]
        self.pos += 1
        return b


def kosinski_decompress(data, start=0, max_output=None):
    """Faithful port of Kosinski.Decompress() / Kosinski.readBit()."""
    ks = KosinskiState(data, start)
    out = bytearray()

    while True:
        # Copy literal bytes while bit == 1
        while ks.read_bit() == 1:
            out.append(ks.read_u8())
            if max_output and len(out) >= max_output:
                return bytes(out)

        length = 0
        offset = -1  # sentinel; real code treats this as s16 math

        if ks.read_bit() == 0:
            # Short match: 2-5 bytes, 8-bit offset
            r1 = ks.read_bit()
            r2 = ks.read_bit()
            length = (r1 * 2) + r2 + 2
            off_byte = ks.read_u8()
            offset = (0xff00 + off_byte) - 0x10000  # as signed 16-bit
        else:
            bits1 = ks.read_u8()
            bits2 = ks.read_u8()
            bits2a = bits2 & 0xf8
            bits2b = bits2 & 0x07
            offset_u = (0xe000 + ((bits2a << 5) & 0xffff) + bits1) & 0xffff
            offset = offset_u - 0x10000 if offset_u >= 0x8000 else offset_u

            if bits2b == 0:
                value = ks.read_u8()
                if value == 0:
                    break  # end of stream
                if value == 1:
                    continue  # no copy this round, read next control
                length = value + 1
            else:
                length = bits2b + 2

        for _ in range(length):
            src_index = len(out) + offset
            if src_index < 0:
                raise ValueError(
                    f"Kosinski stream references before start of output "
                    f"(index {src_index}) -- likely wrong start offset or corrupt data"
                )
            out.append(out[src_index])
            if max_output and len(out) >= max_output:
                return bytes(out)

    return bytes(out)


def main():
    if len(sys.argv) < 3:
        print("Usage: kosinski.py <input.kos> <output.bin> [max_bytes]")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        data = f.read()

    max_output = int(sys.argv[3]) if len(sys.argv) > 3 else None
    result = kosinski_decompress(data, 0, max_output)

    with open(sys.argv[2], "wb") as f:
        f.write(result)

    print(f"Decompressed {len(data)} bytes -> {len(result)} bytes")


if __name__ == "__main__":
    main()
