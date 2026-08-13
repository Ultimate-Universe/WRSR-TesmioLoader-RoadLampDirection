# Road Lamp Direction

A TesmioLoader plugin for **Workers & Resources: Soviet Republic** that changes
which side of an existing lit road carries its street lamps without converting
the road to one-way traffic.

Current version: **1.1.0**  
Steam Workshop ID: **3780739284**

## Features

- Adds a dedicated Road Lamp Direction tool beside the native one-way controls.
- Changes lamp orientation on existing road sections that support street lamps.
- Preserves traffic direction and normal road behaviour.
- Keeps the normal green preview without displaying misleading one-way arrows.
- Does not rebuild, replace, or upgrade the selected road.
- Writes no custom save data and does not require DLC.

## Requirements

- Workers & Resources: Soviet Republic **v1.1.1.9**.
- [TesmioLoader](https://steamcommunity.com/sharedfiles/filedetails/?id=3773169177), API 4.

## Installation

Subscribe to the Workshop item so the toolbar asset and plugin DLLs are
downloaded. Then copy both files from:

```text
Steam\steamapps\workshop\content\784150\3780739284\plugins\
```

to:

```text
Steam\steamapps\common\SovietRepublic\tesmioloader\build\plugins\
```

Required DLLs:

```text
RoadLampDirection.dll
RoadLampDirectionOverlay.dll
```

Launch the game through `tesmiolauncher.exe` and enable both plugins. Steam
cannot overwrite DLLs already copied into the game folder, so repeat the copy
after each Workshop update.

## Usage

Open the road construction tools and select **Road Lamp Direction** beside the
one-way controls. Hover an existing road section with street lamps and click to
apply the selected orientation. Apply the tool from the opposite direction to
move the lamps to the other side.

The selected road is highlighted green. One-way arrows are intentionally
filtered from this custom preview because the tool does not alter traffic flow.

## Compatibility

Version 1.1.0 targets WRSR v1.1.1.9 and TesmioLoader API 4. Both native DLLs
must be installed and enabled together.

The plugin validates executable targets before installing its hooks and fails
closed when a required layout is not recognised. It does not redirect files,
replace shared textures, or alter persistent save structures.

Future WRSR executable updates may require another compatibility update.

## Troubleshooting

If the tool is missing or the preview still contains one-way arrows:

1. Confirm both DLLs were copied into `tesmioloader\build\plugins`.
2. Confirm both plugins are enabled in `tesmioloader.ini`.
3. Fully restart TesmioLoader and the game.
4. Attach `tesmioloader.log` to a GitHub issue if the problem remains.

## Source and building

The reproducible release builder, verifier, readable overlay implementation,
and technical notes are in `Source/`.

Repository:

https://github.com/Ultimate-Universe/WRSR-TesmioLoader-RoadLampDirection

## License

The plugin source code is distributed under GNU GPL version 3. See `LICENSE`.

The toolbar image contains game-derived visual material and remains subject to
the rights of its original rights holders; it is not relicensed by the GPL.

This project is not affiliated with 3DIVISION or Hooded Horse.
