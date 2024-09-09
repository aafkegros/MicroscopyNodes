# Microscopy Nodes internal structure

Microscopy Nodes as an add-on mostly exists to read microscopy data, rewrite this into Blender-loadable file formats, and load this with useful presets. 

## VDB files
The .vdb is the volume file-format that Blender uses, and is very optimized for raytraced rendering of sparse volumes, as this is often necessary in animation for clouds/fire. The Microscopy Nodes vdb files are chunked per timepoint and channel to allow relatively lazy loading, and are chunked at <2048 pixels per axis as oversized volumes can break Eevee.

## ABC files
The .abc files are the way label masks are stored, as these files allow changing the entire geometry of each object for each timepoint. These are written through the Blender writing pipeline for each separate object, which is part of why label mask loading can be slow for dense masks.