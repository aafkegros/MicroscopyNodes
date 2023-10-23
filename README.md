# tif to blender 
This is a project building bioimage support for the open source software blender. This currently exists as the Blender add-on `tif loader` which is able to easily load tif files as volumetric objects in Blender. 

This originally started as a script for the [Blender for Biologists workshop](https://github.com/oanegros/Blender_for_Biologists_2023) Because the scope seems to have outgrown this workshop, the development has split off.

Please make some pretty figures with this add-on! 
If you post using this addon on social media please either tag me (@GrosOane on twitter) or use hashtag `#tif2bpy`.

<img src="./figures/pretty.png" width="600"/>



## Installing `tif loader`

Download:

- Download the most recent version of blender from https://www.blender.org/download/. You need version 3.5 or higher for the tif loader Add-On.

- Download the [tif loader zip file](./tif_loader.zip). 


Start blender.

Install the `tif loader` Add-On:
- In Blender go to `Edit > Preferences`
- Go to `Add-Ons` tab in `Preferences`
- Press `Install` and give the `tif_loader.zip` file (as .zip)
- In the added `tif loader` add-on window in `Preferences`: press the tick box to enable, and the arrow to unfold the details
- in the details press `install tifffile`

This should create the `tif loader` panel in `Scene Properties`.

## Using `tif loader`
Load in tif-files in the file explorer. 
- currently 3D and 4D (3D + channel) tifs are supported. 
- Axes order and pixel size will be attempted to be read out automatically
- Unthresholded initial volumetric emission material is applied

More tutorial-like description can be found at [Blender for Biologists](https://github.com/oanegros/Blender_for_Biologists_2023). However, this asssumes a less capable version of `tif loader` that does not apply an initial material, for didactic purposes.