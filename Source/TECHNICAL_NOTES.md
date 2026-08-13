# Technical notes

Road Lamp Direction v1.1.0 is a pair of native TesmioLoader API 4 plugins for
WRSR v1.1.1.9.

## Runtime components

- `RoadLampDirection.dll` registers the dedicated road-editor tool and applies
  only the lamp-side change when the custom operation is committed.
- `RoadLampDirectionOverlay.dll` filters one-way arrow materials from the
  custom tool's frame-local green preview.

The overlay never changes the road object, shared materials, textures, staging
records, or the vanilla one-way tool.

## Confirmed WRSR v1.1.1.9 targets

Core checked function RVAs:

```text
0x003AAA0
0x00B0E90
0x0296110
0x04FA070
0x051F9C0
0x05205A0
0x0548B80
0x0564E20
```

The core installs hooks at `0x0296110`, `0x051F9C0`, and `0x05205A0` after
validating every required entry signature.

Overlay structures:

```text
Frame queue transfer:       FUN_1405858F0
Active editor road system:  editor + 0xF7A0
Queue A begin/end:           DAT_140997140 / DAT_140997148
Queue B begin/end:           DAT_140997170 / DAT_140997178
Draw-record stride:          0x30
```

The overlay installer checks target readability, decodes a complete safe
instruction span, and requests TesmioLoader's checked chainable hook. An
unexpected layout fails closed instead of applying an unsafe detour.

## Persistence and DLC

The mod writes no custom save data and does not depend on DLC assets,
definitions, or runtime objects. Disabling it leaves existing roads loadable;
only the editor tool and the ability to change lamp orientation are absent.
