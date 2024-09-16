# Microscopy in Blender
This is a project building bioimage support for the open source software blender. This currently exists as the Blender add-on `Microscopy Nodes`, previously named `tif2blender`. This is able to easily load tif files as volumetric objects in Blender. 

Please make some pretty figures with this add-on! 
If you post using this addon on social media please either tag me (@GrosOane on twitter) or use hashtag `#microscopynodes`.

## Current Features
Microscopy Nodes supports:

- up to 5D (up to tzcyx in any axis order) tifs and OME-Zarr files can be loaded. 
- Channel interface to define how to load data
- Replacing a pyramidal dataset with it's higher resolution version
- Accurate scale bars
- Load per-index label masks
- Lazy loading of giant files (no data is loaded in RAM outside what's rendered)

### [Get Started!](./new_user.md)
<img src="https://github.com/oanegros/MicroscopyNodes/blob/main/figures/newprettyside.png?raw=true" width="600"/>