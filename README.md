# Microscopy in Blender
This is a project building bioimage support for the open source software blender. This currently exists as the Blender add-on `microscopynodes`, previously named `tif2blender`. This is able to easily load tif files as volumetric objects in Blender. 

Please make some pretty figures with this add-on! 
If you post using this addon on social media please either tag me (@GrosOane on twitter) or use hashtag `#microscopynodes`.

You can download and install the add-on on the [Blender extensions platform](https://extensions.blender.org/add-ons/microscopynodes/) or by searching for Microscopy Nodes in the Extensions in your Blender preferences. For installing with earlier Blender versions than 4.2, follow the [legacy install instructions]( https://oanegros.github.io/MicroscopyNodes/outdated).

The add-on will then show up as a window in the `Scene Properties`.

## Video tutorials

See the [video introductions](https://www.youtube.com/playlist?list=PLAv6_GEMrbKdpje81juHowSCw-gWOJwy5) to the microscopynodes add-on on youtube. There's multiple playlists on the account, and they'll show you how to go from installing to rendering a presentation-ready video for fluorescence and electron microscopy.

<img src="./figures/newprettyside.png" width="600"/>

## Current Features
The `microscopynodes` Blender addon supports:

- up to 5D (up to tzcyx in any axis order) tifs and OME-Zarr files can be loaded. 
- Channel interface to define how to load data
- Replacing a pyramidal dataset with it's higher resolution version
- Accurate scale bars
- Load per-index label masks
- Lazy loading of giant files (no data is loaded in RAM outside what's rendered)

## Using `microscopynodes`

Load any tif or zarr file by inputting the path or URL in the appropriate window in the `Microscopy Nodes` panel. This will read out metadata and prompt you to define how you want to load the data.

- generic options
    - axis order
    - pixel size in µm
    - dataset (for pyramidal Zarr data)
    - [reload data]( https://oanegros.github.io/MicroscopyNodes/settings#reload)

- per-channel load options:
    - load [volumetric data]( https://oanegros.github.io/MicroscopyNodes/objects#volumes)
    - load [Blender isosurface]( https://oanegros.github.io/MicroscopyNodes/objects#surfaces)
    - load [labelmask]( https://oanegros.github.io/MicroscopyNodes/objects#masks)

- per-channel visuzalization options:
    - [emission]( https://oanegros.github.io/MicroscopyNodes/settings#emission)
    - [surface resolution]( https://oanegros.github.io/MicroscopyNodes/settings#surface-resolution)

- extra options
    - [data storage location]( https://oanegros.github.io/MicroscopyNodes/settings#resave-location)
    - [overwrite existing local files]( https://oanegros.github.io/MicroscopyNodes/settings#overwrite)
    - [preset environment]( https://oanegros.github.io/MicroscopyNodes/settings#preset-environment)