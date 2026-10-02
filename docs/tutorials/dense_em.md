# Visualize dense EM data

Dense electron-microscopy volumes use the same loading and shader controls as fluorescence data, but usually need different starting values.

## Load the data and labels

In the :blender-MICROSCOPY_NODES: loading panel:

1. Start with a small multiscale level.
2. Load the original EM channel as a :blender-OUTLINER_OB_VOLUME: volume.
3. Turn :blender-OUTLINER_OB_LIGHT: emission off to begin with scattering.
4. Load segmentation channels as :blender-OUTLINER_OB_POINTCLOUD: label masks.
5. Choose a categorical LUT for labels containing separate integer IDs.

The example used in the current tutorial series is:

`https://s3.embl.de/microscopynodes/FIBSEM_dino_masks.zarr`

## Light a scattering volume

A scattering volume will be invisible against an unlit black world. Set the :blender-WORLD: world color to white or gray, increase its strength, or add Blender lights.

Use :blender-SHADING_RENDERED: **Rendered Preview** with Cycles when you need ray-traced internal scattering. Reduce the sample count while working interactively.

## Reveal internal structure

Dense data often fills the entire bounding box. In the :blender-MATERIAL: volume shader:

- narrow the alpha range to remove uninformative material;
- use a black-to-white LUT for a conventional EM appearance;
- move the Slice Cube through the volume to expose cavities;
- use nonlinear color maps when intensity ordering benefits from color.

## Combine context and segmentation

Show the EM volume and label masks in the same coordinate space. For more control, use a label as a geometry mask so the annotated region retains its original pixel intensities while receiving a different color or slicing behavior.

See [Slice, mask, and recolor data](./slicing_masking.md) for that workflow.

!!! note "Performance"
    Dense scattering requires many light calculations. Build the scene at low resolution and low samples, then increase data resolution and render quality only for final output.
