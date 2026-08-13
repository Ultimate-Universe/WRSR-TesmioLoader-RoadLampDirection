#!/usr/bin/env python3
"""Verify the Road Lamp Direction v1.1.0 release binaries."""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys

import build_release as build


ROOT = Path(__file__).resolve().parent


def stored_checksum(data: bytearray, optional: int) -> int:
    checksum_at = optional + 64
    stored = struct.unpack_from("<I", data, checksum_at)[0]
    copy = bytearray(data)
    calculated = build.pe_checksum(copy, checksum_at)
    if not stored or stored != calculated:
        raise ValueError(f"bad PE checksum: stored={stored:#x} calculated={calculated:#x}")
    return stored


def executable_ranges(
    sections: dict[bytes, tuple[int, int, int, int]],
) -> list[tuple[int, int]]:
    result = []
    for name in (b".text", b".xcode"):
        if name in sections:
            _, _, raw_at, raw_size = sections[name]
            result.append((raw_at, raw_at + raw_size))
    return result


def in_ranges(position: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def structural_verify(path: Path) -> tuple[bytearray, int, dict[bytes, tuple[int, int, int, int]]]:
    data = bytearray(path.read_bytes())
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    coff = pe + 4
    optional, sections = build.pe_layout(data)
    if not (struct.unpack_from("<H", data, coff + 18)[0] & 0x2000):
        raise ValueError("DLL flag missing")
    if not struct.unpack_from("<I", data, optional + 16)[0]:
        raise ValueError("entry point missing")
    dll_chars = struct.unpack_from("<H", data, optional + 70)[0]
    for bit, label in ((0x20, "HIGH_ENTROPY_VA"), (0x40, "DYNAMIC_BASE"), (0x100, "NX_COMPAT")):
        if not dll_chars & bit:
            raise ValueError(f"{label} missing")
    stored_checksum(data, optional)
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
    if b"1.1.0\0" not in data or "1.1.0".encode("utf-16le") not in data:
        raise ValueError("v1.1.0 metadata missing")
    if b"1.0.0\0" in data or "1.0.0".encode("utf-16le") in data:
        raise ValueError("obsolete version metadata remains")
    fixed = data.find(bytes.fromhex("BD 04 EF FE"))
    if fixed < 0:
        raise ValueError("VS_FIXEDFILEINFO missing")
    expected_fixed = (0x00010001, 0, 0x00010001, 0)
    if struct.unpack_from("<IIII", data, fixed + 8) != expected_fixed:
        raise ValueError("fixed file/product version is not 1.1.0.0")
    if struct.unpack_from("<HH", data, optional + 44) != (1, 1):
        raise ValueError("PE image version is not 1.1")
    if b"-test" in data or b"OPTION7" in data or b"RSDS" in data or b".pdb" in data.lower():
        raise ValueError("debug artefact remains")
    return data, optional, sections


def assert_executable_diff_is_bounded(
    original: bytes,
    product: bytes,
    sections: dict[bytes, tuple[int, int, int, int]],
    allowed_spans: list[tuple[int, int]],
) -> None:
    if len(original) != len(product):
        raise ValueError("image size changed")
    executable = executable_ranges(sections)
    unexpected = []
    for position, (old, new) in enumerate(zip(original, product)):
        if old == new or not in_ranges(position, executable):
            continue
        if not any(start <= position < end for start, end in allowed_spans):
            unexpected.append(position)
    if unexpected:
        shown = ", ".join(hex(position) for position in unexpected[:8])
        raise ValueError(f"unexpected executable-code changes at {shown}")

    _, _, pdata_at, pdata_size = sections[b".pdata"]
    if original[pdata_at:pdata_at + pdata_size] != product[pdata_at:pdata_at + pdata_size]:
        raise ValueError("unwind table changed")


def verify_core(path: Path) -> None:
    product, _, sections = structural_verify(path)
    original = build.CORE_INPUT.read_bytes()
    _, _, text_at, text_size = sections[b".text"]
    allowed: list[tuple[int, int]] = []
    replacement_specs: list[tuple[int, int, int]] = []
    for old, new, signature_length in build.CORE_RELOCATIONS:
        for offset in range(signature_length + 1):
            expected = 2 if offset == 0 else 1
            replacement_specs.append((old + offset, new + offset, expected))
    for position, _ in build.collect_dword_patches(
        original, text_at, text_size, replacement_specs
    ):
        allowed.append((position, position + 4))
    api_at = build.rva_to_offset(sections, 0x1020)
    api_check_at = build.rva_to_offset(sections, 0x1079)
    allowed.append((api_at, api_at + 6))
    allowed.append((api_check_at, api_check_at + 3))
    assert_executable_diff_is_bounded(original, product, sections, allowed)

    text = bytes(product[text_at:text_at + text_size])
    for old, new, signature_length in build.CORE_RELOCATIONS:
        for offset in range(signature_length + 1):
            expected = 2 if offset == 0 else 1
            if text.count(struct.pack("<I", old + offset)):
                raise ValueError(f"old core RVA remains: {old + offset:#x}")
            if text.count(struct.pack("<I", new + offset)) != expected:
                raise ValueError(f"new core RVA count mismatch: {new + offset:#x}")
    if product[api_at:api_at + 6] != bytes.fromhex("B8 04 00 00 00 C3"):
        raise ValueError("core does not declare loader API 4")
    if product[api_check_at:api_check_at + 3] != bytes.fromhex("83 39 04"):
        raise ValueError("core init routine does not accept loader API 4")


def verify_overlay(path: Path) -> None:
    product, _, sections = structural_verify(path)
    original = build.OVERLAY_INPUT.read_bytes()
    _, _, text_at, text_size = sections[b".text"]
    old, new = build.OVERLAY_RELOCATION
    patches = build.collect_dword_patches(original, text_at, text_size, [(old, new, 1)])
    allowed = [(position, position + 4) for position, _ in patches]
    api_at = build.rva_to_offset(sections, 0x1000)
    api_check_at = build.rva_to_offset(sections, 0x105F)
    allowed.append((api_at, api_at + 6))
    allowed.append((api_check_at, api_check_at + 3))
    assert_executable_diff_is_bounded(original, product, sections, allowed)

    text = bytes(product[text_at:text_at + text_size])
    if text.count(struct.pack("<I", old)):
        raise ValueError("old overlay target remains")
    if text.count(struct.pack("<I", new)) != 1:
        raise ValueError("new overlay target count mismatch")
    _, _, xcode_at, xcode_size = sections[b".xcode"]
    xcode = bytes(product[xcode_at:xcode_at + xcode_size])
    for rva in build.UNCHANGED_OVERLAY_GLOBALS:
        if xcode.count(struct.pack("<I", rva)) != 1:
            raise ValueError(f"overlay queue global changed: {rva:#x}")
    if product[api_at:api_at + 6] != bytes.fromhex("B8 04 00 00 00 C3"):
        raise ValueError("overlay does not declare loader API 4")
    if product[api_check_at:api_check_at + 3] != bytes.fromhex("83 39 04"):
        raise ValueError("overlay init routine does not accept loader API 4")


def main() -> int:
    paths = [Path(argument) for argument in sys.argv[1:]]
    if not paths:
        paths = [build.OUTPUT / name for name in (
            "RoadLampDirection.dll", "RoadLampDirectionOverlay.dll"
        )]
    for path in paths:
        if path.name == "RoadLampDirection.dll":
            verify_core(path)
        elif path.name == "RoadLampDirectionOverlay.dll":
            verify_overlay(path)
        else:
            raise ValueError(f"unexpected plugin filename: {path.name}")
        raw = path.read_bytes()
        print(f"PASS {path.name} {len(raw)} bytes {hashlib.sha256(raw).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
