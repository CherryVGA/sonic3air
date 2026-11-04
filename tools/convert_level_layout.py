#!/usr/bin/env python3
"""
Convert a Kosinski-decompressed Sonic 2 Level_Layout buffer (s2disasm's
native format) into Oxygen Engine's standalone rawdata layout format.

SOURCE FORMAT (s2disasm, verified against the real decoder routines, not
guessed): a fixed 0x1000-byte buffer, 16 rows of 0x100 (256) bytes each.
Per GetAddressOfBlockInChunk's own comment ("$100 = size of a row of FG
and BG 128x128s in level layout table"):
  - bytes [row*0x100 .. row*0x100+0x7F]   = foreground chunk IDs, 1 byte
    each, columns 0-127 (confirmed: LoadTilesAsYouMove uses Level_Layout
    as the foreground pointer)
  - bytes [row*0x100+0x80 .. row*0x100+0xFF] = background chunk IDs, 1
    byte each, columns 0-127 (confirmed: Level_Layout+$80 used for
    background throughout, e.g. DrawInitialBG)
Chunk = 128x128 pixels (0x80).

TARGET FORMAT (Oxygen Engine, verified against defines_global.lemon's own
documentation comment and the real getTileAtWorldPosition reader in
collision.lemon -- both copied from sonic3air into this project):
  - u16[base+0x0] = foreground width in chunks
  - u16[base+0x2] = background width in chunks
  - u16[base+0x4] = foreground height in chunks
  - u16[base+0x6] = background height in chunks
  - from base+0x8: one pair of u16 RAM addresses per row (fg ptr, bg ptr),
    for however many rows are declared by the height fields. Confirmed via
    getTileAtWorldPosition: `ramAddress = u16[chunksBaseAddress + offset];
    ramAddress += input.x >> 7; chunkType = u8[0xffff0000 + ramAddress]`
    -- i.e. each pointer is a 16-bit RAM address (high word implicitly
    0xFFFF0000) of a FLAT BYTE ARRAY for that row, read exactly like
    s2disasm's own convention (1 byte per chunk, column added directly to
    the row's base address). So no reformatting of chunk ID VALUES is
    needed at all -- only the row data needs relocating and a pointer
    table needs building on top.

Width/height in chunks come from s2disasm's own `LevelSize` table (camera
boundaries in pixels, per zone/act) -- NOT from scanning the layout table
itself, since the table is always allocated at a fixed max size (128 cols
x 16 rows) regardless of a given act's real content length.

KNOWN UNCERTAINTY (flagged honestly, not glossed over): the exact pixel
origin convention of LevelSize's xend/yend (camera's own position vs. the
visible screen's far edge) introduces some rounding uncertainty in the
derived width/height-in-chunks. Using xend/yend + one screen's worth of
margin, rounded up, as a safe overestimate -- extra unused rows/columns
of real (if unused) chunk data are harmless; an underestimate would clip
real content. This should be verified once the engine can actually be run
and the level visually inspected; treat the header values as provisional
until then.
"""
import sys
import struct

CHUNK_SIZE_PX = 0x80  # 128x128 pixel chunks
SCREEN_WIDTH_PX = 320
SCREEN_HEIGHT_PX = 224
ROW_STRIDE = 0x100
FG_COLS = 128
BG_OFFSET = 0x80
BG_COLS = 128
NUM_ROWS = 16  # 0x1000 / 0x100


def parse_s2_layout(data):
    """Returns (fg_rows, bg_rows): each a list of NUM_ROWS byte-strings."""
    if len(data) != 0x1000:
        print(f"WARNING: expected exactly 0x1000 bytes, got {len(data):#x} "
              f"-- format assumption may not hold", file=sys.stderr)

    fg_rows = []
    bg_rows = []
    for row in range(NUM_ROWS):
        base = row * ROW_STRIDE
        fg_rows.append(data[base:base + FG_COLS])
        bg_rows.append(data[base + BG_OFFSET:base + BG_OFFSET + BG_COLS])
    return fg_rows, bg_rows


def chunks_needed(extent_px, chunk_px, screen_px):
    """Safe (overestimate-biased) chunk count for a camera-bound extent."""
    total_px = extent_px + screen_px  # camera bound + one screen of margin
    return (total_px + chunk_px - 1) // chunk_px  # ceil division


def build_oxygen_layout(fg_rows, bg_rows, xend_px, yend_px, load_address=0xffff8000):
    """
    Builds the full Oxygen-format blob: header + pointer table + row data,
    all self-contained (pointers reference offsets within this same blob,
    computed relative to load_address since that's where it lands in RAM).
    """
    fg_width_chunks = chunks_needed(xend_px, CHUNK_SIZE_PX, SCREEN_WIDTH_PX)
    bg_width_chunks = fg_width_chunks  # S2 doesn't track these separately in LevelSize
    fg_height_chunks = chunks_needed(yend_px, CHUNK_SIZE_PX, SCREEN_HEIGHT_PX)
    bg_height_chunks = fg_height_chunks

    num_rows_out = min(NUM_ROWS, max(fg_height_chunks, bg_height_chunks))

    header = struct.pack(">HHHH", fg_width_chunks, bg_width_chunks,
                          fg_height_chunks, bg_height_chunks)

    pointer_table_size = num_rows_out * 4  # 2x u16 per row
    row_data_start = 8 + pointer_table_size

    pointer_table = b""
    row_data = b""
    cursor = row_data_start

    for row in range(num_rows_out):
        fg_ptr = (load_address + cursor) & 0xffff
        row_data += fg_rows[row][:fg_width_chunks].ljust(fg_width_chunks, b"\x00")
        cursor += fg_width_chunks

        bg_ptr = (load_address + cursor) & 0xffff
        row_data += bg_rows[row][:bg_width_chunks].ljust(bg_width_chunks, b"\x00")
        cursor += bg_width_chunks

        pointer_table += struct.pack(">HH", fg_ptr, bg_ptr)

    blob = header + pointer_table + row_data
    info = {
        "fg_width_chunks": fg_width_chunks,
        "bg_width_chunks": bg_width_chunks,
        "fg_height_chunks": fg_height_chunks,
        "bg_height_chunks": bg_height_chunks,
        "num_rows_out": num_rows_out,
        "total_size": len(blob),
    }
    return blob, info


def main():
    if len(sys.argv) < 5:
        print("Usage: convert_level_layout.py <decompressed_s2_layout.bin> "
              "<xend_hex> <yend_hex> <output.bin>")
        print(__doc__)
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        data = f.read()

    xend_px = int(sys.argv[2], 16)
    yend_px = int(sys.argv[3], 16)
    output_path = sys.argv[4]

    fg_rows, bg_rows = parse_s2_layout(data)
    blob, info = build_oxygen_layout(fg_rows, bg_rows, xend_px, yend_px)

    with open(output_path, "wb") as f:
        f.write(blob)

    print(f"Converted {len(data)} bytes -> {len(blob)} bytes")
    for k, v in info.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
