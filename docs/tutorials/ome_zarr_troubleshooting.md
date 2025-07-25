# OME-Zarr troubleshooting

[OME-Zarr](https://ngff.openmicroscopy.org/about/index.html) is a developing standard and is very flexible, which sometimes makes it hard to read and write, and no software supports all features. 

{{ svg("microscopy_nodes") }} Microscopy Nodes supports OME-Zarr **up to version 0.5**, to load single, up to 5-dimensional, arrays. 

!!! tip "Is your OME-Zarr not loading?"
    A quick option is to append `/0` after your path. Some OME-Zarr writers create a **group** at the .zarr adress, with the first (and often, only) image at .zarr/0

## OME-Zarr collections

There is currently **no support** for any form of **self-discovering** collections from OME-Zarr, this can cause issues for:

- Wells
- Fields
- Labels 
- Large Zarr-groups (such as OpenOrganelle datasets)
- Bioformats2raw export

All of these images **can still be opened**, by pointing to the **specific path** of the array, which contains the different OME 'multiscales'. 

!!! example "Pointing to a specific path"
    For example, for the dataset [https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.3/idr0052A/5514375.zarr](https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.3/idr0052A/5514375.zarr) of the IDR, the labels are at [https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.3/idr0052A/5514375.zarr/labels/Cell](https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.3/idr0052A/5514375.zarr/Cell) and [https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.3/idr0052A/5514375.zarr/labels/Chromosomes](https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.3/idr0052A/5514375.zarr/Chromosomes). These are not auto-discovered, but can be loaded with the specific paths.

Support for collections will come in the future, but this will wait for the planned reorganization OME-Zarr collection structure.
