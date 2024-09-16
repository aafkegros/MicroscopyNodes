# Microscopy Nodes User Settings

The Microscopy Nodes panel has multiple different settings, which affect the import, resaving and reloading of data.

## Emission
A per-channel settign for whether a volume will emit light or absorb light upon load. It is standard practice for fluorescence images to emit light and electron microscopy to absorb light, as this reflects the physics of the acquisition process. However, this is of course not necessary.

## Surface Resolution
Constructing isosurfaces, such as done for both [surfaces](./objects.md#surfaces) and [label masks](./objects.md#masks) is an expensive operation and can consume too much RAM. By reducing the fineness of the surface mesh, this can be alleviated.

To note: both ways that are used to mesh volumes in Microscopy Nodes, Blender Volume to Mesh and scikit-image marching_cubes currently have issues that they do not always correctly report when they're out of RAM. If the loading seems extremely long, it may be better to restart blender and try at lower resolution.

## Reload
Reloading data of a previously loaded Microscopy Nodes object can be useful in multiple circumstances:
- Changing which/how channels are loaded
- Replacing temporary files that got deleted
- Changing resolution of Zarr
This will reload and update the visualization of the object with the data that is currently in the input file slot. It will attempt to retain as much user-made changes as possible and only update those settings that are changed. 
To do this it uses some specific names in the Microscopy Nodes objects. Any of these that are used are enclosed in square brackets.

## Resave Location
The resave location is the location where all [blender-compatible files](./file_types.md) will be stored, this will often be at the size of your entire dataset. Temporary is default, as we assume the first attempt at loading will be just temporary. 

If you want the `.blend` blender project to be portable between machines, it is often best to use the `With Project` saving, as relative paths to the data are saved in the file. 

## Overwrite
This is mostly a debug option, but may be relevant if you have files with identical filenames. This forces all Microscopy Nodes local files to be overwritten before loading.

## Preset Environment
Presetting the environment overwrites a bunch of environment variables, such as background color, render samples, volumetric target pixel size and others to provide a good starting point for rendering microscopy data. This turns itself off after the first load so user-set values are not accidentally overriden.