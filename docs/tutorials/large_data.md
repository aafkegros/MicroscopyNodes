# Large datasets and sparse reloading

Build the scene with a small version of the data, then load full resolution only where it contributes to the final result.

{{ youtube("n2w0pI7tzu8", 560, 315) }}

## Start small

OME-Zarr datasets can contain multiple prepared scales. Microscopy Nodes can also create downsampled scales for a large TIFF.

Choose a small scale while setting up:

- channel representations;
- {{ svg("material") }} shaders and color maps;
- {{ svg("view_camera") }} cameras and animation;
- {{ svg("geometry_nodes") }} masks and processing;
- render settings.

This keeps Blender responsive and reduces the time spent converting local cache files.

## Reload at higher resolution

In the {{ svg("microscopy_nodes") }} loading panel, point the {{ svg("file_refresh") }} Reload field to the existing dataset holder. Choose a larger scale and keep:

- {{ svg("file") }} **Update data** on;
- {{ svg("material") }} **Update settings** off.

Press **Reload**. The holder and edited visualization remain in place while the underlying data is replaced.

Use ordinary reloading when the complete high-resolution volume fits comfortably on the machine.

## Reload only a region

Often only a small region needs full resolution. Microscopy Nodes can use the currently visible geometry-masked voxels as a sparse reload mask.

### 1. Build the mask at low resolution

Load or reload the dataset with {{ svg("geometry_nodes") }} **Geometry slicing** enabled. Position and scale the Slice Cube around the region of interest, or use any geometry-mask source described in [Slice, mask, and recolor data](./slicing_masking.md).

The mask can come from:

- the Slice Cube;
- a custom or sculpted mesh;
- a label mask;
- an isosurface;
- multiple masks combined in Geometry Nodes.

What matters is the grid present at the end of the volume's Geometry Nodes masking branch.

### 2. Choose sparse reload

In the loading panel:

1. Keep the existing holder in the {{ svg("file_refresh") }} Reload field.
2. Enable **Reload only visible** with the {{ svg("hide_off") }} eye control.
3. Turn off {{ svg("material") }} **Update settings** if shader and node edits should remain unchanged.
4. Choose the desired higher-resolution scale.
5. Press **Reload**.

Only voxels surviving the spatial mask are requested and written into the new cache files.

!!! note "Conversion can still take time"
    Sparse loading reduces the resulting data, but requesting and writing a high-resolution region may still be slow. The loaded result should be much more responsive afterward.

## Combine low and high resolution

A useful final scene can contain:

- one sparse high-resolution dataset for the region of interest;
- one low-resolution copy providing whole-cell or whole-volume context.

Load the low-resolution dataset as a separate hierarchy. In its Geometry Nodes mask, exclude the region occupied by the high-resolution copy. This avoids double-rendering the same voxels and makes it possible to animate a multiscale zoom.

Match the two datasets' {{ svg("material") }} intensity limits, LUTs, and transparency where the transition should be visually continuous. Alternatively, use different colors to communicate the difference in scale explicitly.

## Performance guidance

- Hide unused channels in the {{ svg("modifier") }} modifier so they are not loaded into RAM.
- Keep render samples low while working.
- Use {{ svg("shading_rendered") }} Cycles for volumes that exceed EEVEE's practical limits or rely on dense scattering.
- Make and edit masks at a small data scale, then reload the result at high resolution.
- Store cache data **With Project** when moving the `.blend` file to another workstation.
