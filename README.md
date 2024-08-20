# Microscopy in Blender
This is a project building bioimage support for the open source software blender. This currently exists as the Blender add-on `microscopynodes`, previously named `tif2blender`. This is able to easily load tif files as volumetric objects in Blender. 

Please make some pretty figures with this add-on! 
If you post using this addon on social media please either tag me (@GrosOane on twitter) or use hashtag `#microscopynodes`.

You can now also find the add-on on the Blender extensions platform under https://extensions.blender.org/approval-queue/microscopynodes/ (currently still awaiting review by blender).

## Video introduction

See the [video introductions](https://www.youtube.com/playlist?list=PLAv6_GEMrbKdpje81juHowSCw-gWOJwy5) to the microscopynodes add-on on youtube. There's multiple playlists on the account, and they'll show you how to go from installing to rendering a presentation-ready video for fluorescence and electron microscopy.

<img src="./figures/newprettyside.png" width="600"/>

## Current Features
The `microscopynodes` Blender addon is still under active development, but some notable features are already supported:

- up to 5D (up to tzcyx in any axis order) tifs are supported. 
- Axes order and pixel size will be attempted to be read out automatically
- Initial volumetric emission material is applied
- Scale bars are added to the `Geometry Nodes` container of your volumetric data




## Installing `microscopynodes`

You can now find the add-on on the Blender extensions platform under https://extensions.blender.org/approval-queue/microscopynodes/ (currently still awaiting review by blender). You can download this and drag it into the Blender 4.2 window.

For older versions than Blender 4.2:

- Download blender from https://www.blender.org/download/. Check the supported blender version next to the release!

- Download the microscopynodes zip file from the [releases page](https://github.com/oanegros/microscopynodes/releases). 

Start blender.

Install the `microscopynodes` Add-On:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences`
- Press `Install` and give the `tif_loader.zip` file (as .zip)
- In the added `microscopynodes` add-on window in `Preferences`: press the tick box to enable, and the arrow to unfold the details
- in the details press `install tifffile`
- (if this fails please try restarting blender and seeing if it can then find `tifffile`)

This should create the `microscopynodes` panel in `Scene Properties`.

## Using `microscopynodes`
Load in tif-files in the file explorer from the panel in `Scene Properties`. 

Loading with preset environment recently had a small bug, fixed on 7th nov 18:45. So either uncheck this or update your tif_loader(see below), if you have this issue. For any other problems, please open an [issue](https://github.com/oanegros/microscopynodes/issues).

- The `microscopynodes` panel should be able to automatically read out your axis order and pixel size, but these can otherwise also manually be entered
- Any tif stack from zyx to tzcyx (in any axis order) is supported
- The `microscopynodes` resaves your tif as a `.vdb` file (in a `blender_volumes` subfolder) and loads this as a volume object in your blender scene, connected to a `Container` object.
- With large files (over 2048 px in an axis), the volumes will be split to avoid blender crashes.
- With the `Import option: Force Remake` you will force remaking the vdb files, if this is unchecked and the vdb files exist, these will be loaded.
- With the `Import option: Preset Environment` some default environment variables will be set. These overwrite current other environment settings, but are useful for quickly looking at data:
  - Sets background to black (as emission material is default)
  - Sets `Eevee` volumetric `tile_size` to 2 px (might be heavy for enormous data)
  - Sets `Cycles` `Samples` to manageable numbers for volumetric data
  - Sets `View Transform` to `Standard` (the default `Filmic` crunches dynamic range post-render)

Upon load, multiple defaults are applied, but all of these can be changed as granularly as you want.


## Updating `microscopynodes`
To update the `microscopynodes` add-on (future versions may have bugfixes, new features) a few steps need to be taken:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences` and find the `microscopynodes` add-on
- Press `Remove` 
- Restart Blender
- Install the new version.