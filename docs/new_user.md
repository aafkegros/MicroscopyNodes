## Installing Microscopy Nodes
You can download and install the add-on on the [Blender extensions platform](https://extensions.blender.org/add-ons/microscopynodes/) or by searching for Microscopy Nodes in the Extensions in your Blender preferences. For installing with earlier Blender versions than 4.2, follow the [legacy install instructions](./outdated.md).

The add-on will then show up as a window in the `Scene Properties`.

## Using Microscopy Nodes

Load any tif or zarr file by inputting the path or URL in the appropriate window in the `Microscopy Nodes` panel. This will read out metadata and prompt you to define how you want to load the data.

- generic options
    - axis order
    - pixel size in µm
    - dataset (for pyramidal Zarr data)
    - [reload data](./settings.md#reload)

- per-channel load options:
    - load [volumetric data](./objects.md#volumes)
    - load [Blender isosurface](./objects.md#surfaces)
    - load [labelmask](./objects.md#masks)

- per-channel visuzalization options:
    - [emission](./settings.md#emission)
    - [surface resolution](./settings.md#surface-resolution)

- extra options
    - [data storage location](./settings.md#resave-location)
    - [overwrite existing local files](./settings.md#overwrite)
    - [preset environment](./settings.md#preset-environment)


## Video tutorials

See the [video introductions](https://www.youtube.com/playlist?list=PLAv6_GEMrbKdpje81juHowSCw-gWOJwy5) to the microscopynodes add-on on youtube. There's multiple playlists on the account, and they'll show you how to go from installing to rendering a presentation-ready video for fluorescence and electron microscopy.
