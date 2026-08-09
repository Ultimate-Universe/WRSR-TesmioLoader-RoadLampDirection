#!/usr/bin/env python3
"""Produce the Road Lamp Direction v1.0.0 release DLLs reproducibly.

The runtime logic is retained byte-for-byte from the user-tested v0.1.32
package. This builder changes release-facing version strings, bounded log
labels, fixed file/product versions, image version fields, and PE checksums.
Executable code and unwind tables are verified unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "reference_inputs"
OUTPUT = ROOT / "out"

CORE_INPUT = INPUTS / "RoadLampDirection_core_verified.dll"
OVERLAY_INPUT = INPUTS / "RoadLampDirectionOverlay_verified.dll"

EXPECTED = {
    CORE_INPUT.name: "ac82347b80a8e8f2ac09ae738ccec65402ee6635d4210884f936e107413280e2",
    OVERLAY_INPUT.name: "fd87a7fe39aec5c291e9abdc4fe296a30c9f6b059b43aef0ef73c8173c6247c0",
}


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def pe_layout(data: bytes | bytearray) -> tuple[int, int, dict[bytes, tuple[int, int]]]:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image")
    coff = pe + 4
    optional = coff + 20
    if struct.unpack_from("<H", data, coff)[0] != 0x8664:
        raise ValueError("not an x86-64 PE image")
    if struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ValueError("not PE32+")
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    section_at = optional + struct.unpack_from("<H", data, coff + 16)[0]
    sections: dict[bytes, tuple[int, int]] = {}
    for index in range(section_count):
        header = section_at + index * 40
        name = bytes(data[header:header + 8]).rstrip(b"\0")
        raw_size = struct.unpack_from("<I", data, header + 16)[0]
        raw_at = struct.unpack_from("<I", data, header + 20)[0]
        sections[name] = (raw_at, raw_size)
    return optional, section_at, sections


def replace_c_string(data: bytearray, old: str, new: str) -> None:
    old_raw = old.encode("ascii") + b"\0"
    new_raw = new.encode("ascii") + b"\0"
    if len(new_raw) > len(old_raw):
        raise ValueError(f"replacement is too long: {new!r}")
    if data.count(old_raw) != 1:
        raise ValueError(f"expected one C string: {old!r}")
    at = data.find(old_raw)
    data[at:at + len(old_raw)] = new_raw + b"\0" * (len(old_raw) - len(new_raw))


def replace_fixed(data: bytearray, old: bytes, new: bytes, expected: int) -> None:
    if len(new) > len(old):
        raise ValueError("fixed replacement is too long")
    if data.count(old) != expected:
        raise ValueError(f"expected {expected} occurrence(s) of {old!r}")
    data[:] = data.replace(old, new + b"\0" * (len(old) - len(new)))


def pe_checksum(data: bytearray, checksum_offset: int) -> int:
    struct.pack_into("<I", data, checksum_offset, 0)
    total = 0
    for index in range(0, len(data) - (len(data) % 2), 2):
        total += data[index] | (data[index + 1] << 8)
        total = (total & 0xFFFF) + (total >> 16)
    if len(data) & 1:
        total += data[-1]
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return ((total & 0xFFFF) + len(data)) & 0xFFFFFFFF


def set_version(data: bytearray, optional: int, expected_fixed: tuple[int, int, int, int]) -> None:
    fixed = data.find(bytes.fromhex("BD 04 EF FE"))
    if fixed < 0:
        raise ValueError("VS_FIXEDFILEINFO not found")
    current = struct.unpack_from("<IIII", data, fixed + 8)
    if current != expected_fixed:
        raise ValueError(f"unexpected fixed version: {current!r}")
    struct.pack_into("<IIII", data, fixed + 8, 0x00010000, 0, 0x00010000, 0)
    struct.pack_into("<HH", data, optional + 44, 1, 0)


def assert_code_unchanged(before: bytes, after: bytes) -> None:
    _, _, before_sections = pe_layout(before)
    _, _, after_sections = pe_layout(after)
    for name in (b".text", b".pdata"):
        if name not in before_sections:
            continue
        before_at, before_size = before_sections[name]
        after_at, after_size = after_sections[name]
        if before_size != after_size:
            raise ValueError(f"{name.decode()} size changed")
        if before[before_at:before_at + before_size] != after[after_at:after_at + after_size]:
            raise ValueError(f"{name.decode()} changed")
    if b".xcode" in before_sections:
        before_at, before_size = before_sections[b".xcode"]
        after_at, after_size = after_sections[b".xcode"]
        if before_size != after_size:
            raise ValueError(".xcode size changed")
        old_marker = before.find(b"roadlamps.queue OPTION7", before_at, before_at + before_size)
        new_marker = after.find(b"roadlamps.preview active", after_at, after_at + after_size)
        if old_marker < 0 or new_marker < 0:
            raise ValueError("overlay diagnostic boundary missing")
        old_code_size = old_marker - before_at
        new_code_size = new_marker - after_at
        if old_code_size != new_code_size:
            raise ValueError("overlay code/string boundary moved")
        if before[before_at:old_marker] != after[after_at:new_marker]:
            raise ValueError(".xcode executable callback changed")


def build_core(source: bytes) -> bytes:
    data = bytearray(source)
    optional, _, _ = pe_layout(data)
    replace_c_string(
        data,
        "roadlamps  ready - one-shot menu+availability registration; no UI/render/frame polling; arrow suppression DISABLED; safe stable commit path retained    ; one-way writes replaced only at commit",
        "roadlamps  ready v1.0.0 - toolbar registered; lamp-side commit active; preview arrows handled by RoadLampDirectionOverlay",
    )
    replace_c_string(
        data,
        "roadlamps  init v0.1.11-test (API %u) - one-shot GUI/menu + availability registration, preview-arrow suppression OFF   , and narrow road-commit hook",
        "roadlamps  init v1.0.0 (API %u) - toolbar registration and narrow lamp-direction commit hook",
    )
    replace_c_string(
        data,
        "RoadLampDirection scoped road-preview arrow suppression",
        "RoadLampDirection reserved preview compatibility",
    )
    replace_c_string(
        data,
        "roadlamps  lamp preview arrows suppressed: manager=%p bpOneWay=(%p,%p); normal green overlay/lamp preview unchanged",
        "roadlamps  preview filtering provided by RoadLampDirectionOverlay: manager=%p materials=(%p,%p)",
    )
    replace_fixed(data, b"0.1.11-test", b"1.0.0", 1)
    replace_fixed(data, "0.1.11-test".encode("utf-16le"), "1.0.0".encode("utf-16le"), 2)
    set_version(data, optional, (0x00000001, 0x000B0000, 0x00000001, 0x000B0000))
    checksum_at = optional + 64
    struct.pack_into("<I", data, checksum_at, pe_checksum(data, checksum_at))
    return bytes(data)


def build_overlay(source: bytes) -> bytes:
    data = bytearray(source)
    optional, _, _ = pe_layout(data)
    replace_c_string(
        data,
        "roadlamps.preview init v0.1.32-test - Option 7 live-road material rewrite",
        "roadlamps.preview init v1.0.0 - live-road arrow material filter",
    )
    replace_c_string(
        data,
        "roadlamps.preview ready - Option 7 live-road frame material filter",
        "roadlamps.preview ready - live-road arrow material filter",
    )
    replace_c_string(
        data,
        "roadlamps.queue OPTION7 ACTIVE roadSystem=%p oneway1=%p line=%p scan=%u",
        "roadlamps.preview active roadSystem=%p oneway1=%p line=%p scan=%u",
    )
    replace_c_string(
        data,
        "roadlamps.queue OPTION7 candidate queue=%c record=%p material=%p liveOne1=%p liveOne2=%p",
        "roadlamps.preview candidate queue=%c record=%p material=%p liveOne1=%p liveOne2=%p",
    )
    replace_c_string(
        data,
        "roadlamps.queue OPTION7 REWRITE queue=%c record=%p material=%p->%p count=%u",
        "roadlamps.preview arrows hidden queue=%c record=%p material=%p->%p count=%u",
    )
    replace_fixed(data, b"0.1.32-test", b"1.0.0", 1)
    replace_fixed(data, "0.1.32-test".encode("utf-16le"), "1.0.0".encode("utf-16le"), 2)
    set_version(data, optional, (0x00000001, 0x00200000, 0x00000001, 0x00200000))
    checksum_at = optional + 64
    struct.pack_into("<I", data, checksum_at, pe_checksum(data, checksum_at))
    return bytes(data)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_core = CORE_INPUT.read_bytes()
    source_overlay = OVERLAY_INPUT.read_bytes()
    for path, data in ((CORE_INPUT, source_core), (OVERLAY_INPUT, source_overlay)):
        actual = sha256(data)
        if actual != EXPECTED[path.name]:
            raise ValueError(f"unexpected reference input: {path.name} {actual}")

    products = {
        "RoadLampDirection.dll": (source_core, build_core(source_core)),
        "RoadLampDirectionOverlay.dll": (source_overlay, build_overlay(source_overlay)),
    }
    for name, (before, after) in products.items():
        assert_code_unchanged(before, after)
        if b"-test" in after or b"OPTION7" in after:
            raise ValueError(f"development label remains in {name}")
        output = OUTPUT / name
        output.write_bytes(after)
        print(f"{name}  {sha256(after)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
