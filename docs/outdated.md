# Installing and using Microscopy Nodes with Blender < 4.2

## Install

- Download an appropriate microscopynodes/tif2blender zip file from the [releases page](https://github.com/oanegros/microscopynodes/releases). Please note the Blender version number.

Start blender.

Install the `microscopynodes` Add-On:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences`
- Press `Install` and give the `tif_loader.zip` file (as .zip)
- In the added `microscopynodes` add-on window in `Preferences`: press the tick box to enable, and the arrow to unfold the details
- in the details press `install tifffile`
- (if this fails please try restarting blender and seeing if it can then find `tifffile`)


## Updating `microscopynodes`
To update the `microscopynodes` add-on (future versions may have bugfixes, new features) a few steps need to be taken:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences` and find the `microscopynodes` add-on
- Press `Remove` 
- Restart Blender
- Install the new version.