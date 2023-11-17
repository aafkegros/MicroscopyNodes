# tif to blender 
This is a project building bioimage support for the open source software blender. This currently exists as the Blender add-on `tif loader` which is able to easily load tif files as volumetric objects in Blender. 

This originally started as a script for the [Blender for Biologists workshop](https://github.com/oanegros/Blender_for_Biologists_2023) Because the scope seems to have outgrown this workshop, the development has split off.

Please make some pretty figures with this add-on! 
If you post using this addon on social media please either tag me (@GrosOane on twitter) or use hashtag `#tif2blender`.

<img src="./figures/newprettyside.png" width="600"/>

## Current Features
The `tif loader` Blender addon is still under active development, but some notable features are already supported:

- 3D to 5D (zyx to tzcyx in any axis order) tifs are supported. 
- Axes order and pixel size will be attempted to be read out automatically
- Otsu initial volumetric emission material is applied
- Scale bars are added to the `Geometry Nodes` container of your volumetric data

## Video introduction

See the [video introduction](https://youtu.be/TCQojYEYxVo) to the tif2blender add-on on youtube.


## Installing `tif loader`

Download:

- Download blender from https://www.blender.org/download/. You need version 3.5 or 3.6 for the tif loader Add-On. Blender 4.0 support is coming soon

- Download the tif loader zip file from the [releases page](https://github.com/oanegros/tif2blender/releases). 

Start blender.

Install the `tif loader` Add-On:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences`
- Press `Install` and give the `tif_loader.zip` file (as .zip)
- In the added `tif loader` add-on window in `Preferences`: press the tick box to enable, and the arrow to unfold the details
- in the details press `install tifffile`
- (if this fails please try restarting blender and seeing if it can then find `tifffile`)

This should create the `tif loader` panel in `Scene Properties`.

## Using `tif loader`
Load in tif-files in the file explorer from the panel in `Scene Properties`. 

Loading with preset environment recently had a small bug, fixed on 7th nov 18:45. So either uncheck this or update your tif_loader(see below), if you have this issue. For any other problems, please open an [issue](https://github.com/oanegros/tif2blender/issues).

- The `tif loader` panel should be able to automatically read out your axis order and pixel size, but these can otherwise also manually be entered
- Any tif stack from zyx to tzcyx (in any axis order) is supported
- The `tif loader` resaves your tif as a `.vdb` file (in a `blender_volumes` subfolder) and loads this as a volume object in your blender scene, connected to a `Container` object.
- With large files (over 2048 px in an axis), the volumes will be split to avoid blender crashes.
- With the `Import option: Force Remake` you will force remaking the vdb files, if this is unchecked and the vdb files exist, these will be loaded.
- With the `Import option: Preset Environment` some default environment variables will be set. These overwrite current other environment settings, but are useful for quickly looking at data:
  - Sets background to black (as emission material is default)
  - Sets `Eevee` volumetric `tile_size` to 2 px (might be heavy for enormous data)
  - Sets `Cycles` `Samples` to manageable numbers for volumetric data
  - Sets `View Transform` to `Standard` (the default `Filmic` crunches dynamic range post-render)

Upon load, multiple defaults are applied, but all of these can be changed as granularly as you want:
- A default `Emission Material` is applied. You can find and edit this in the `Shading` tab when selecting a volume (not the container of the volume):
  - This takes each channel from an Otsu threshold up. This threshold is set and can be changed in the `Map Range`
  - This is piped to the `Emission Strength` of the `Volume shader`.
- A default `Scale bar` is applied. This is implemented as a `Geometry Nodes Modifier` of the `Container` of the volumes. You can find and edit this in the `Geometry Nodes` tab if you have the `Container` selected:
  - By default this starts at 10 `µm per tick` but this can be changed.
  - This has many visualization options, default is a thin `grid` with `crosshatch ticks` on the major axes
  - By default this has `Frontface culling` on, so that this only renders the back axes from the view angle, however, you can also specifically select which axes to draw.
  - The `crosshatch` ticks can be replaced with any geometry.

More tutorial-like description can be found at [Blender for Biologists](https://github.com/oanegros/Blender_for_Biologists_2023). However, this asssumes a less capable version of `tif loader` that does not apply an initial material, for didactic purposes.

## Updating `tif loader`
To update the `tif loader` add-on (future versions may have bugfixes, new features) a few steps need to be taken:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences` and find the `tif loader` add-on
- Press `Remove` 
- Restart Blender
- Install the new version.