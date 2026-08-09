# Technical notes

Road Lamp Direction is a native TesmioLoader API 3 plugin for WRSR 1.1.1.7.

## Runtime components

- `RoadLampDirection.dll` registers a dedicated road-editor leaf beside the native one-way road controls, registers its availability descriptor, and intercepts the road-operation commit narrowly enough to change lamp-side orientation without writing one-way traffic state.
- `RoadLampDirectionOverlay.dll` hooks the live frame queue transfer at `FUN_140585820`. It activates only when the exact Road Lamp Direction descriptor is selected, resolves the active editor's ordinary-road system at `editor + 0xF7A0`, and replaces copied green-preview records using the six live one-way material slots with the corresponding ordinary line material.

The overlay changes only frame-local render records. It does not modify the road object, shared material objects, textures, VFS state, staging records or the vanilla one-way tool.

## Confirmed structures for WRSR 1.1.1.7

- Frame queue transfer: `FUN_140585820`.
- Active editor road system: `editor + 0xF7A0`.
- Road render queues: `DAT_140997140/148` and `DAT_140997170/178`.
- Draw-record stride: `0x30`.
- Ordinary and one-way material slots: documented in `overlay/live_road_queue_callback.S`.

The installer validates target readability, decodes a complete instruction span and requests TesmioLoader's checked chainable hook. An unexpected target layout fails closed instead of applying an unsafe detour.

## Persistence and DLC

The mod writes no custom save data and does not depend on DLC assets, definitions or runtime objects. Disabling it leaves existing roads loadable; only the editor tool and the ability to change lamp orientation are absent.
