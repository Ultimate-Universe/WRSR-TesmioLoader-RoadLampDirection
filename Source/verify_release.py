#!/usr/bin/env python3
"""Structural checks for the two native Road Lamp Direction release DLLs."""

from pathlib import Path
import hashlib
import struct
import sys


def checksum(data: bytearray, at: int) -> int:
    stored = struct.unpack_from("<I", data, at)[0]
    struct.pack_into("<I", data, at, 0)
    total = 0
    for i in range(0, len(data) - (len(data) % 2), 2):
        total += data[i] | (data[i + 1] << 8)
        total = (total & 0xFFFF) + (total >> 16)
    if len(data) & 1:
        total += data[-1]
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    calculated = ((total & 0xFFFF) + len(data)) & 0xFFFFFFFF
    struct.pack_into("<I", data, at, stored)
    if not stored or stored != calculated:
        raise ValueError(f"bad PE checksum: stored={stored:#x} calculated={calculated:#x}")
    return stored


def verify(path: Path) -> None:
    raw = path.read_bytes()
    data = bytearray(raw)
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    coff = pe + 4
    optional = coff + 20
    if struct.unpack_from("<H", data, coff)[0] != 0x8664:
        raise ValueError("not x86-64")
    if struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ValueError("not PE32+")
    if not (struct.unpack_from("<H", data, coff + 18)[0] & 0x2000):
        raise ValueError("DLL flag missing")
    if not struct.unpack_from("<I", data, optional + 16)[0]:
        raise ValueError("entry point missing")
    dll_chars = struct.unpack_from("<H", data, optional + 70)[0]
    for bit, label in ((0x20, "HIGH_ENTROPY_VA"), (0x40, "DYNAMIC_BASE"), (0x100, "NX_COMPAT")):
        if not dll_chars & bit:
            raise ValueError(f"{label} missing")
    checksum(data, optional + 64)
    directory = optional + 112
    if struct.unpack_from("<II", data, directory + 8) == (0, 0):
        raise ValueError("import directory missing")
    if struct.unpack_from("<II", data, directory + 24) == (0, 0):
        raise ValueError("x64 exception directory missing")
    if struct.unpack_from("<II", data, directory + 14 * 8) != (0, 0):
        raise ValueError("CLR payload present")
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    sections_at = optional + struct.unpack_from("<H", data, coff + 16)[0]
    for index in range(section_count):
        header = sections_at + index * 40
        name = bytes(data[header:header + 8]).rstrip(b"\0").decode("ascii", "replace")
        flags = struct.unpack_from("<I", data, header + 36)[0]
        if flags & 0x20000000 and flags & 0x80000000:
            raise ValueError(f"RWX section: {name}")
    for export in (b"TsmPluginApiVersion\0", b"TsmPluginInit\0", b"TsmPluginStart\0"):
        if export not in data:
            raise ValueError(f"missing export name {export[:-1].decode()}")
    if b"DisableThreadLibraryCalls\0" not in data:
        raise ValueError("expected conventional import missing")
    if b"1.0.0\0" not in data or "1.0.0".encode("utf-16le") not in data:
        raise ValueError("release version metadata missing")
    if b"-test" in data or b"OPTION7" in data or b"RSDS" in data or b".pdb" in data.lower():
        raise ValueError("development artefact remains")
    print(f"PASS {path.name} {len(raw)} bytes {hashlib.sha256(raw).hexdigest()}")


def main() -> int:
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        paths = [Path(__file__).resolve().parent / "out" / name for name in (
            "RoadLampDirection.dll", "RoadLampDirectionOverlay.dll")]
    for path in paths:
        verify(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
