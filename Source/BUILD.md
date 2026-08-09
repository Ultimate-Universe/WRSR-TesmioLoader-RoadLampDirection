# Building v1.0.0

Requirements:

- Python 3.10 or newer.
- GNU `gcc`, `nm` and `objcopy` only if independently assembling the overlay implementation files.

From this directory run:

```text
python build_release.py
python verify_release.py
```

The release DLLs are written to `out/`.

The builder validates the SHA-256 identity of both known-working reference inputs, applies only release-facing metadata and bounded log-label changes, recalculates each PE checksum, and verifies that executable code and x64 unwind tables remain byte-for-byte unchanged from the verified implementation inputs.

The readable overlay implementation is in `overlay/`. The final tested plugin is deliberately split into two DLLs: the core owns toolbar registration and lamp-direction commits; the overlay support DLL filters the one-way arrow material only from the custom tool's green preview.

The reference inputs are retained so this exact release can be reproduced. They are not files users need to install from the source directory.
