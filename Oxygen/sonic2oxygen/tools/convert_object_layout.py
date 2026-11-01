#!/usr/bin/env python3
"""
Convert a Sonic 2 object layout .bin (s2disasm's level/objects/*.bin) into
Oxygen-style LevelObjectTableBuilder.addObject(...) lemonscript calls.

Entry format (verified against s2disasm's ChkLoadObj routine, s2.asm
~line 33650, not guessed from docs):
  6 bytes per object:
    bytes 0-1 : X position, u16 big-endian
    bytes 2-3 : u16 big-endian, packed:
                  bits 0-11  = Y position
                  bit 12     = unused
                  bit 13     = x_flip (render_flags bit 0)
                  bit 14     = y_flip (render_flags bit 1)
                  bit 15     = respawn-table flag
    byte  4   : object ID
    byte  5   : subtype

Object ID -> name mapping is pulled live from s2disasm's s2.constants.asm
(lines of the form "ObjID_Foo = id(ObjPtr_Foo) ; XX") rather than
hardcoded, so it stays correct if the disasm updates.

Usage:
  python3 convert_object_layout.py <constants_asm> <layout_bin> [zone_label]
"""
import sys
import re
import struct


def load_id_names(constants_asm_path):
    id_to_name = {}
    pattern = re.compile(r"^ObjID_(\w+)\s*=.*;\s*([0-9A-Fa-f]{1,2})\s*$")
    with open(constants_asm_path, "r", encoding="latin-1") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                name, hexid = m.group(1), m.group(2)
                obj_id = int(hexid, 16)
                # First definition wins (file lists canonical name first per ID in most cases)
                id_to_name.setdefault(obj_id, name)
    return id_to_name


def parse_layout(bin_path):
    with open(bin_path, "rb") as f:
        data = f.read()

    if len(data) % 6 != 0:
        print(f"WARNING: file size {len(data)} is not a multiple of 6 bytes "
              f"({len(data) % 6} leftover) -- format assumption may be wrong, "
              f"or there's a trailing boundary marker.", file=sys.stderr)

    entries = []
    for off in range(0, len(data) - (len(data) % 6), 6):
        chunk = data[off:off + 6]
        x, word2, obj_id, subtype = struct.unpack(">HHBB", chunk)
        y = word2 & 0x0FFF
        x_flip = (word2 >> 13) & 1
        y_flip = (word2 >> 14) & 1
        respawns = (word2 >> 15) & 1
        entries.append({
            "x": x, "y": y, "id": obj_id, "subtype": subtype,
            "x_flip": x_flip, "y_flip": y_flip, "respawns": respawns,
        })
    return entries


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    constants_path = sys.argv[1]
    bin_path = sys.argv[2]
    zone_label = sys.argv[3] if len(sys.argv) > 3 else "ZONE"

    id_names = load_id_names(constants_path)
    entries = parse_layout(bin_path)

    print(f"// Converted from {bin_path}")
    print(f"// {len(entries)} objects, {len(entries) * 6} bytes")
    print(f"// Object type IDs resolved against {constants_path}")
    print()
    print(f"function void LevelObjectTableBuilder.buildObjects_{zone_label}()")
    print("{")
    for e in entries:
        name = id_names.get(e["id"], None)
        if name:
            type_comment = f"ObjID_{name}"
        else:
            type_comment = "UNKNOWN"
        flags = []
        if e["x_flip"]:
            flags.append("x_flip")
        if e["y_flip"]:
            flags.append("y_flip")
        if e["respawns"]:
            flags.append("respawns")
        flag_comment = (" [" + ",".join(flags) + "]") if flags else ""
        print(f"	LevelObjectTableBuilder.addObject(0x{e['x']:04x}, 0x{e['y']:04x}, "
              f"0x{e['id']:02x}, 0x{e['subtype']:02x}, 0x00)"
              f"	// {type_comment}{flag_comment}")
    print("}")

    # Summary of unresolved IDs, so follow-up work is obvious
    unresolved = sorted({e["id"] for e in entries if e["id"] not in id_names})
    if unresolved:
        print(f"\n// Unresolved object IDs needing a name lookup: "
              f"{', '.join(f'0x{i:02x}' for i in unresolved)}", file=sys.stderr)


if __name__ == "__main__":
    main()
