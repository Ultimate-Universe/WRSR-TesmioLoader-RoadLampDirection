# Road Lamp Direction

A TesmioLoader plugin for **Workers & Resources: Soviet Republic** that lets you change which side of an existing lit road carries its street lamps without converting the road to one-way traffic.

Current version: **1.0.0**

## Features

- Adds a dedicated Road Lamp Direction tool beside the native one-way road controls.
- Changes the lamp orientation of existing road sections that already support street lamps.
- Preserves the road's traffic direction and ordinary road behaviour.
- Keeps the normal green road preview while removing misleading one-way arrows from this tool.
- Does not replace, rebuild or upgrade the selected road.
- Writes no custom save data.
- Standalone and DLC-independent.

## Requirements

- Workers & Resources: Soviet Republic v1.1.1.7.
- [TesmioLoader](https://steamcommunity.com/sharedfiles/filedetails/?id=3773169177), API 3.
- Steam Workshop item `3779397743`.

## Installation

Subscribe to the Workshop item so its toolbar asset and plugin files are downloaded.

Then copy both files from:

```text
Steam\steamapps\workshop\content\784150\3779397743\plugins\
```

into:

```text
Steam\steamapps\common\SovietRepublic\tesmioloader\build\plugins\
```

The required files are:

```text
RoadLampDirection.dll
RoadLampDirectionOverlay.dll
```

Launch the game through `tesmiolauncher.exe` and enable both plugins.

Steam cannot automatically overwrite DLLs already copied into TesmioLoader's game folder. After a Workshop update, copy both DLLs across again.

## Usage

Open the road tools and select **Road Lamp Direction** beside the one-way road controls. Hover an existing road section with street lamps and click to apply the selected orientation. Apply the tool from the opposite direction to move the lamps to the other side.

The selected road is highlighted green. The tool deliberately omits the normal one-way arrows because it does not change traffic direction.

## Why TesmioLoader is required

WRSR's normal Workshop format cannot add a road-editor operation that changes the orientation of lamps already attached to a built road. The plugin registers that live editor tool, commits only the lamp-side change, preserves the road's traffic state, and adjusts the custom preview so it does not resemble the one-way-road tool.

## Compatibility

The plugin uses checked, chainable hooks and fails safely when a required WRSR function does not match the supported layout. It does not use VFS redirects, replace shared textures or modify persistent save structures.

Because the plugin interacts with WRSR's executable, a future game update may require a compatibility update even if the Workshop asset still loads.

## Troubleshooting

If the tool is missing or the green overlay still contains arrows:

1. Confirm both DLLs were manually copied into `tesmioloader\build\plugins`.
2. Confirm both plugins are enabled in the TesmioLoader launcher.
3. Fully restart the launcher and game.
4. If the problem remains, open a GitHub issue and attach `tesmioloader.log`.

## Source and building

Source, technical notes and reproducible build instructions are in `Source/`.

Repository:

https://github.com/Ultimate-Universe/WRSR-TesmioLoader-RoadLampDirection

## License

The plugin source code is distributed under the GNU General Public License version 3. See `LICENSE`.

The toolbar image contains game-derived visual material and remains subject to the rights of its original rights holders; it is not relicensed by the GPL.

This project is not affiliated with 3DIVISION or Hooded Horse.
