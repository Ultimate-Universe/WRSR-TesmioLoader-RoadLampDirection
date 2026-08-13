# Building version 1.1.0

## Requirements

- Python 3.10 or newer.
- GNU `gcc`, `nm`, and `objcopy` only when independently assembling or examining
  the readable overlay implementation.

## Build and verify

Run these commands from the `Source` directory:

```text
python build_release.py
python verify_release.py
```

The builder writes both finished DLLs directly to `../ModFiles/plugins/`.

`build_release.py` validates the SHA-256 identity of the two known-good native
reference images before making any change. It then applies only the verified
WRSR v1.1.1.9 RVA relocations, the complete TesmioLoader API 4 handshake, the
v1.1.0 version metadata, and valid PE checksums.

`verify_release.py` independently checks the expected RVA replacements, API
entry points, executable-code change boundaries, exports, imports, x64 unwind
data, section permissions, security flags, version metadata, and checksums.

The reference images are required build inputs. They are not installed from
the `Source` directory. The readable overlay hook, callback, and instruction
span decoder are retained in `overlay/`.
