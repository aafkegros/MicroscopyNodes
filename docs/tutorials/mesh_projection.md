# Project volume data onto meshes

Volume sampling maps microscopy intensities onto a generated, sculpted, or imported mesh while preserving the mesh as editable geometry.

{{ youtube("3K6l0ovNFZ4", 560, 315) }}

## Prepare a volume and a mesh

Load the source channel as a {{ svg("outliner_ob_volume") }} volume and create the target {{ svg("outliner_ob_surface") }} surface. The target can be an isosurface from another microscopy channel or any mesh positioned in the same coordinate space.

Open the target object's {{ svg("geometry_nodes") }} Geometry Nodes workspace.

## Retrieve a named grid

Bring the source Volume object into the node tree and use **Get Named Grid** to choose the microscopy channel. This provides the volume grid that will be sampled.

Channel names are used to connect data across node trees. Keep the chosen grid name, stored attribute name, and shader attribute name consistent.

## Sample or project

Microscopy Nodes provides two related operations:

- **Sample Grid on Mesh** reads the trilinear volume value at each mesh vertex.
- **Project Grid to Mesh** takes multiple samples along the vertex normal and averages them.

Direct sampling is useful when the mesh itself identifies the position of interest. Projection is useful when signal lies within a distance of the surface.

For projection, set the distance, number of samples, and direction: inward, outward, or both.

## Send values to the shader

Store the sampled result as a named float attribute. In the target mesh's {{ svg("material") }} shader:

1. Read the same named attribute.
2. Pass it through a **Pixel Intensity** control for contrast.
3. Connect it to a {{ svg("material") }} Color LUT.
4. Feed the resulting color into the surface material.

This makes the projected signal respond to the same scientific color-mapping controls as volume data.

## Process before projection

Volume-processing nodes can be inserted before sampling. For example, sharpening, blurring, edge detection, or a custom convolution can emphasize a feature before it is projected onto the mesh.

Because this remains a Geometry Nodes graph, mesh thresholds, projection settings, preprocessing, and shader properties can all be animated with keyframes.

!!! tip
    Build and test this workflow at a small data scale. It composes with [geometry masking](./slicing_masking.md) and [sparse high-resolution reloading](./large_data.md).
