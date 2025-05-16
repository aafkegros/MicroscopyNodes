# <img src="./docs/grey_icons/icon_microscopy_nodes.svg" width="40" style="vertical-align:-0.4em;"/> Microscopy in Blender

**Microscopy Nodes** is a Blender add-on for visualizing high-dimensional microscopy data—designed for scientists, or anyone working with biological images 😊.

 For any type of microscopy: fluorescence, electron microscopy, or anything in between! This tool helps you turn complex 3D+ datasets into stunning, accurate, and animatable visualizations. 


## <img src="./docs/grey_icons/blender_icon_settings.svg" width="20" style="vertical-align:-0.2em;"/>  What It Does

Microscopy Nodes supports importing **up to 5D** microscopy datasets (XYZ + time + channels) from `.tif` and **OME-Zarr** files, setting easy and adaptable settings to start with visualizing your data.


| Feature | Description |
|--------|-------------|
| **5D Support** | Load `.tif` and `.zarr` files with any axis order 'tzcyx' or any subset |
| **Channel Interface** | Define how to load each channel: <img src="./docs/grey_icons/blender_icon_outliner_data_volume.svg" width="15" style="vertical-align:-0.2em;"/> volume, <img src="./docs/grey_icons/blender_icon_outliner_data_surface.svg" width="15" style="vertical-align:-0.2em;"/> surface, <img src="./docs/grey_icons/blender_icon_outliner_data_pointcloud.svg" width="15" style="vertical-align:-0.2em;"/> label mask |
| **Colors and LUTs** | Easy picking of colors per channel or non-linear LUT selection from [many colormaps](https://cmap-docs.readthedocs.io/en/stable/).  |
| **Intuitive Slicing** | Slice any object by moving the Slicing Cube, as you would move any other Blender object |
| **Scales** | 3D scale grid for accurate representation and physical Blender scales for easy registration.  |
| **Large Volumes** | Build your animation and visualization on a downscaled version, render with your massive dataset! |


## <img src="./docs/grey_icons/blender_icon_file.svg" width="20" style="vertical-align:-0.2em;"/> Installation

You can grab the add-on on the [Blender Extensions Platform](https://extensions.blender.org/add-ons/microscopynodes/)  
Or, search **Microscopy Nodes** in Blender Preferences → Get Extensions. (Blender 4.2+)

For earlier versions, check the [legacy install guide](https://oanegros.github.io/MicroscopyNodes/outdated).

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