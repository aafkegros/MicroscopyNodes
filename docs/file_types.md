Microscopy Nodes as an add-on mostly exists to read microscopy data, rewrite this into Blender-loadable file formats, and load this with useful presets. 

---

# Input
Microscopy Nodes supports .tif and .zarr files/containers. These file types are used in microscopy partially because they have very flexible (or flexibly used) specifications. This means supporting all versions these files can exist in is difficult. 

## TIF files
Microscopy Nodes loads tif files, and is able to read basic metadata of imagej-tif files. LZW-compressed tif is supported. Further OME-Tif metdata is currently not read, if you really need this, please open an isssue on the github.

## OME-Zarr files
OME-Zarr is a still-developing pyramidal data format with a lot of features, some of which are harder to support in Blender. Please open an issue if you really want a certain feature.
Microscopy Nodes supports:

- OME-Zarr >= 0.3
- channel names from `omero`
- lazy loading (per channel/timpoint at least)
- dataset selection
- coordinate transform Scale
- `labels` metadata

Microscopy Nodes does not support (currently):

- wells/fields
- affine/translate coordinate transforms
- bioformats2raw multiple loading (or others with multiple datasets, one could still select the relevant internal path)


----

# Output
Output files are the files used by Blender to render your data.

## VDB files
The .vdb is the volume file-format that Blender uses, and is very optimized for raytraced rendering of sparse volumes, as this is often necessary in animation for clouds/fire. The Microscopy Nodes vdb files are chunked per timepoint and channel to allow relatively lazy loading, and are chunked at <2048 pixels per axis as oversized volumes can break Eevee.

## ABC files
The .abc files are the way label masks are stored, as these files allow changing the entire geometry of each object for each timepoint. These are written through the Blender writing pipeline for each separate object, which is part of why label mask loading can be slow for dense masks.