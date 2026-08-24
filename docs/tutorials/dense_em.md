# Visualize dense EM data

Dense electron-microscopy volumes use the same loading and shader controls as fluorescence data, but usually need different starting values.

## Load the data and labels

In the {{ svg("microscopy_nodes") }} loading panel:

1. Start with a small multiscale level.
2. Load the original EM channel as a {{ svg("outliner_ob_volume") }} volume.
3. Turn {{ svg("outliner_ob_light") }} emission off to begin with scattering.
4. Load segmentation channels as {{ svg("outliner_ob_pointcloud") }} label masks.
5. Choose a categorical LUT for labels containing separate integer IDs.

The example used in the current tutorial series is:

`https://s3.embl.de/microscopynodes/FIBSEM_dino_masks.zarr`

## Light a scattering volume

A scattering volume will be invisible against an unlit black world. Set the {{ svg("world") }} world color to white or gray, increase its strength, or add Blender lights.

Use {{ svg("shading_rendered") }} **Rendered Preview** with Cycles when you need ray-traced internal scattering. Reduce the sample count while working interactively.

## Reveal internal structure

Dense data often fills the entire bounding box. In the {{ svg("material") }} volume shader:

- narrow the alpha range to remove uninformative material;
- use a black-to-white LUT for a conventional EM appearance;
- move the Slice Cube through the volume to expose cavities;
- use nonlinear color maps when intensity ordering benefits from color.

## Combine context and segmentation

Show the EM volume and label masks in the same coordinate space. For more control, use a label as a geometry mask so the annotated region retains its original pixel intensities while receiving a different color or slicing behavior.

See [Slice, mask, and recolor data](./slicing_masking.md) for that workflow.

!!! note "Performance"
    Dense scattering requires many light calculations. Build the scene at low resolution and low samples, then increase data resolution and render quality only for final output.
