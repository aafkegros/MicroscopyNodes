# Troubleshooting, help, and contact

## My volume is not visible

Microscopy volumes are not shown in :blender-SHADING_SOLID: Solid mode. Switch the viewport to :blender-SHADING_TEXTURE: Material Preview or :blender-SHADING_RENDERED: Rendered Preview.

For a scattering :blender-OUTLINER_OB_VOLUME: volume, also make sure the :blender-WORLD: world is not black or add a Blender light. See [Adjust color, contrast, and opacity](./tutorials/visualization.md).

## My OME-Zarr metadata does not load

Copy the direct `.zarr` address into the field rather than using the file browser. Collections, wells, fields, and label groups may require a path to the specific image array. See [OME-Zarr troubleshooting](./tutorials/ome_zarr_troubleshooting.md).

## Blender becomes slow with my data

Begin with the smallest useful multiscale level, reduce visible channels, and work at low render samples. Reload the complete data or only a masked region at higher resolution for final output. See [Large datasets and sparse reloading](./tutorials/large_data.md).

## Where should I change something?

- Use :blender-GEOMETRY_NODES: Geometry Nodes for masks, geometry, projection, and data processing.
- Use :blender-MATERIAL: Shader Nodes for color, opacity, and lighting.
- Use the :blender-MICROSCOPY_NODES: loading panel to change scale, time range, storage, or channel representation.

The [workflow overview](./tutorials/workflow_overview.md) explains this separation.

## Ask for help

The main venue for **Usage questions** is the 
![image.sc logo](figures/imagesc_logo.png){: style="height:15px"}  [image.sc forum](https://forum.image.sc/tag/microscopy-nodes) and you can also search here for previous questions.

If you've found a **bug** (or suspect something even a little bit of being non-intended behaviour), don't be afraid to open an [issue](https://github.com/aafkegros/MicroscopyNodes/issues)!
