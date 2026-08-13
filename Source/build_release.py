#!/usr/bin/env python3
"""Build the Road Lamp Direction v1.1.0 release for WRSR 1.1.1.9.

This deterministic builder starts from the published v1.0.0 native runtime
images, relocates the verified SOVIET64.exe targets, advances both halves of
the TesmioLoader handshake to API 4, applies v1.1.0 metadata, and recalculates
the PE checksum. Hook callbacks and other executable logic remain unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "reference_inputs"
OUTPUT = ROOT.parent / "ModFiles" / "plugins"

CORE_INPUT = INPUTS / "RoadLampDirection_v1.0.0.dll"
OVERLAY_INPUT = INPUTS / "RoadLampDirectionOverlay_v1.0.0.dll"

INPUT_SHA256 = {
    CORE_INPUT.name:
        "a9ac6d2651ae0d19fa1ae61db3d90cc53c3b4f8a53dd2475bdc964fbbb55abc7",
    OVERLAY_INPUT.name:
        "1bd19c9e29783680547b31cf6eb9bb92e0c06c4615b5e850a0ff5d4bdf1b76ef",
}

# (WRSR 1.1.1.7 RVA, WRSR 1.1.1.9 RVA, validated entry-signature length)
CORE_RELOCATIONS = (
    (0x002960A0, 0x00296110, 0x10),
    (0x004F9FA0, 0x004FA070, 0x0F),
    (0x0051F8F0, 0x0051F9C0, 0x0E),
    (0x005204D0, 0x005205A0, 0x0F),
    (0x00548AB0, 0x00548B80, 0x0F),
    (0x00564D50, 0x00564E20, 0x13),
)

UNCHANGED_CORE_RVAS = (0x0003AAA0, 0x000B0E90)
OVERLAY_RELOCATION = (0x00585820, 0x005858F0)
UNCHANGED_OVERLAY_GLOBALS = (0x00997140, 0x00997148, 0x00997170, 0x00997178)


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def pe_layout(data: bytes | bytearray) -> tuple[int, dict[bytes, tuple[int, int, int, int]]]:
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
    sections_at = optional + struct.unpack_from("<H", data, coff + 16)[0]
    sections: dict[bytes, tuple[int, int, int, int]] = {}
    for index in range(section_count):
        header = sections_at + index * 40
        name = bytes(data[header:header + 8]).rstrip(b"\0")
        virtual_size = struct.unpack_from("<I", data, header + 8)[0]
        virtual_at = struct.unpack_from("<I", data, header + 12)[0]
        raw_size = struct.unpack_from("<I", data, header + 16)[0]
        raw_at = struct.unpack_from("<I", data, header + 20)[0]
        sections[name] = (virtual_at, virtual_size, raw_at, raw_size)
    return optional, sections


def rva_to_offset(sections: dict[bytes, tuple[int, int, int, int]], rva: int) -> int:
    for virtual_at, virtual_size, raw_at, raw_size in sections.values():
        span = max(virtual_size, raw_size)
        if virtual_at <= rva < virtual_at + span:
            return raw_at + rva - virtual_at
    raise ValueError(f"RVA {rva:#x} is outside all sections")


def collect_dword_patches(
    original: bytes,
    start: int,
    size: int,
    replacements: list[tuple[int, int, int]],
) -> list[tuple[int, bytes]]:
    """Return checked, non-overlapping dword patches within one PE section."""
    section = original[start:start + size]
    patches: list[tuple[int, bytes]] = []
    occupied: set[int] = set()
    for old, new, expected in replacements:
        old_raw = struct.pack("<I", old)
        new_raw = struct.pack("<I", new)
        if section.count(new_raw):
            raise ValueError(f"new RVA unexpectedly already present: {new:#010x}")
        positions: list[int] = []
        cursor = 0
        while True:
            found = section.find(old_raw, cursor)
            if found < 0:
                break
            positions.append(start + found)
            cursor = found + 1
        if len(positions) != expected:
            raise ValueError(
                f"RVA {old:#010x}: expected {expected} occurrence(s), found {len(positions)}"
            )
        for position in positions:
            byte_positions = set(range(position, position + 4))
            if occupied & byte_positions:
                raise ValueError(f"overlapping RVA patch at file offset {position:#x}")
            occupied |= byte_positions
            patches.append((position, new_raw))
    return patches


def apply_patches(data: bytearray, patches: list[tuple[int, bytes]]) -> None:
    for position, replacement in sorted(patches):
        data[position:position + len(replacement)] = replacement


def patch_api_version_4(
    data: bytearray,
    sections: dict[bytes, tuple[int, int, int, int]],
    export_rva: int,
    init_compare_rva: int,
) -> None:
    export_at = rva_to_offset(sections, export_rva)
    old_export = bytes.fromhex("B8 03 00 00 00 C3")
    new_export = bytes.fromhex("B8 04 00 00 00 C3")
    if data[export_at:export_at + len(old_export)] != old_export:
        raise ValueError(f"unexpected API export at RVA {export_rva:#x}")
    data[export_at:export_at + len(new_export)] = new_export

    compare_at = rva_to_offset(sections, init_compare_rva)
    old_compare = bytes.fromhex("83 39 03")
    new_compare = bytes.fromhex("83 39 04")
    if data[compare_at:compare_at + len(old_compare)] != old_compare:
        raise ValueError(f"unexpected init API check at RVA {init_compare_rva:#x}")
    data[compare_at:compare_at + len(new_compare)] = new_compare


def patch_version(data: bytearray, optional: int, ascii_count: int) -> None:
    old_ascii = b"1.0.0"
    new_ascii = b"1.1.0"
    old_utf16 = "1.0.0".encode("utf-16le")
    new_utf16 = "1.1.0".encode("utf-16le")
    if data.count(old_ascii) != ascii_count:
        raise ValueError("unexpected ASCII version-string count")
    if data.count(old_utf16) != 2:
        raise ValueError("unexpected UTF-16 version-string count")
    data[:] = data.replace(old_ascii, new_ascii)
    data[:] = data.replace(old_utf16, new_utf16)

    fixed = data.find(bytes.fromhex("BD 04 EF FE"))
    if fixed < 0:
        raise ValueError("VS_FIXEDFILEINFO not found")
    current = struct.unpack_from("<IIII", data, fixed + 8)
    expected = (0x00010000, 0, 0x00010000, 0)
    if current != expected:
        raise ValueError(f"unexpected fixed version: {current!r}")
    version_1_1_0_0 = (0x00010001, 0, 0x00010001, 0)
    struct.pack_into("<IIII", data, fixed + 8, *version_1_1_0_0)

    if struct.unpack_from("<HH", data, optional + 44) != (1, 0):
        raise ValueError("unexpected PE image version")
    struct.pack_into("<HH", data, optional + 44, 1, 1)


def pe_checksum(data: bytearray, checksum_at: int) -> int:
    struct.pack_into("<I", data, checksum_at, 0)
    total = 0
    for index in range(0, len(data) - (len(data) % 2), 2):
        total += data[index] | (data[index + 1] << 8)
        total = (total & 0xFFFF) + (total >> 16)
    if len(data) & 1:
        total += data[-1]
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return ((total & 0xFFFF) + len(data)) & 0xFFFFFFFF


def finish_checksum(data: bytearray, optional: int) -> None:
    checksum_at = optional + 64
    struct.pack_into("<I", data, checksum_at, pe_checksum(data, checksum_at))


def build_core(source: bytes) -> bytes:
    data = bytearray(source)
    optional, sections = pe_layout(data)
    text_rva, _, text_at, text_size = sections[b".text"]
    if text_rva != 0x1000:
        raise ValueError("unexpected .text RVA")

    replacements: list[tuple[int, int, int]] = []
    for old, new, signature_length in CORE_RELOCATIONS:
        # The base occurs once in the preflight and once at its call/hook site.
        # Each following byte displacement occurs once in the preflight.  The
        # one-past-signature displacement is the image-size safety bound.
        for offset in range(signature_length + 1):
            expected = 2 if offset == 0 else 1
            replacements.append((old + offset, new + offset, expected))
    patches = collect_dword_patches(source, text_at, text_size, replacements)
    apply_patches(data, patches)

    for rva in UNCHANGED_CORE_RVAS:
        if source[text_at:text_at + text_size].count(struct.pack("<I", rva)) == 0:
            raise ValueError(f"unchanged core RVA missing: {rva:#x}")

    patch_api_version_4(data, sections, 0x1020, 0x1079)
    patch_version(data, optional, ascii_count=3)
    finish_checksum(data, optional)
    return bytes(data)


def build_overlay(source: bytes) -> bytes:
    data = bytearray(source)
    optional, sections = pe_layout(data)
    text_rva, _, text_at, text_size = sections[b".text"]
    old, new = OVERLAY_RELOCATION
    patches = collect_dword_patches(source, text_at, text_size, [(old, new, 1)])
    apply_patches(data, patches)

    _, _, xcode_at, xcode_size = sections[b".xcode"]
    for rva in UNCHANGED_OVERLAY_GLOBALS:
        count = source[xcode_at:xcode_at + xcode_size].count(struct.pack("<I", rva))
        if count != 1:
            raise ValueError(f"overlay global {rva:#x}: expected once, found {count}")

    patch_api_version_4(data, sections, 0x1000, 0x105F)
    patch_version(data, optional, ascii_count=2)
    finish_checksum(data, optional)
    return bytes(data)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    products = {
        "RoadLampDirection.dll": (CORE_INPUT, build_core),
        "RoadLampDirectionOverlay.dll": (OVERLAY_INPUT, build_overlay),
    }
    for name, (input_path, builder) in products.items():
        source = input_path.read_bytes()
        actual = sha256(source)
        if actual != INPUT_SHA256[input_path.name]:
            raise ValueError(f"unexpected reference input: {input_path.name} {actual}")
        product = builder(source)
        output = OUTPUT / name
        output.write_bytes(product)
        print(f"{name}  {len(product)} bytes  {sha256(product)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
