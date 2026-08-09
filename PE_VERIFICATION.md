# Native DLL verification

Both v1.0.0 release DLLs passed the following checks:

- PE32+ x86-64 native Windows DLL.
- TesmioLoader exports: `TsmPluginApiVersion`, `TsmPluginInit`, `TsmPluginStart`.
- Conventional `DisableThreadLibraryCalls` import from KERNEL32.
- Normal Windows DLL entry point present.
- ASLR / `DYNAMIC_BASE` enabled.
- `HIGH_ENTROPY_VA` enabled.
- NX / DEP compatibility enabled.
- Valid non-empty x64 exception/unwind directory.
- Nonzero PE checksum matching a clean recalculation.
- No writable-and-executable section.
- No CLR header or managed payload.
- No embedded PDB path or RSDS debug record.
- Embedded Windows file/product version: `1.0.0`.
- No development-version or experimental-option labels in the release binaries.

The release builder additionally confirms that executable hook and callback code, together with the unwind table, is byte-for-byte unchanged from the verified implementation inputs. Only release metadata and bounded diagnostic text are changed.

## SHA-256

```text
cc17e588f3f73c5a43e2865d5ad8cb5339508abaf0a7f955ce506c69619b3db8  RoadLampDirection.dll
1bd19c9e29783680547b31cf6eb9bb92e0c06c4615b5e850a0ff5d4bdf1b76ef  RoadLampDirectionOverlay.dll
```
