# Split and animate subvolumes

Split a microscopy grid into independently movable volume instances when you want to separate structures, build an exploded view, reveal contact regions, or animate an assembly.

{{ youtube("7K-in7z2Dfk", 560, 315) }}

!!! warning "Microscopy Nodes 3.1.2 or newer"
    The subvolume nodes require **Microscopy Nodes 3.1.2 or newer**. This is an advanced {{ svg("geometry_nodes") }} Geometry Nodes workflow; first become comfortable with [loading data](./2_loading_data.md) and [masking grids](./slicing_masking.md).

## Prepare the source grid and regions

Load the intensity channel you want to sample as a {{ svg("outliner_ob_volume") }} **Volume**. You also need geometry defining each region that should become a separate subvolume. This can come from:

- a {{ svg("outliner_ob_surface") }} surface whose disconnected mesh islands identify separate structures; or
- a {{ svg("outliner_ob_pointcloud") }} label mask, which already supplies one mesh instance per object ID.

Open the Volume object's {{ svg("geometry_nodes") }} Geometry Nodes tree. A **Mask Grid** is enough when you only want to keep or remove a region. Use **Split to Subvolumes** when the regions need to move independently.

## Convert a surface into mesh instances

**Split to Subvolumes** expects separate mesh instances rather than one mesh containing several disconnected pieces.

For an isosurface or another single mesh:

1. Bring the surface geometry into the Volume node tree.
2. Add Blender's **Mesh Island** node.
3. Connect **Island Index** to **Group ID** on **Split to Instances**.
4. Connect the resulting **Instances** to **Mesh Instances** on **Split to Subvolumes**.

Each disconnected mesh island is now supplied as a separate instance. A loaded label mask can connect its mesh instances directly, without this conversion.

## Sample the grid into subvolumes

Connect the source channel grid to **Grid** on **Split to Subvolumes**, and set **Holder** to the dataset's {{ svg("outliner_ob_empty") }} holder. The node voxelizes every mesh instance and samples the source values into a corresponding volume instance.

**Voxel Size** controls the resolution of these generated volumes. A smaller value follows the region more accurately but increases calculation time and memory use. Start coarse while constructing the node tree.

The **Subvolumes** output is instance geometry. Place any per-region transformations between this node and the merge step.

## Move or select separate regions

Add **Set Position** after **Split to Subvolumes** to offset the volume instances.

- Use **Index** with a comparison node to transform only a subset.
- Use **Index** as part of a vector offset to spread every region along an axis.
- Animate the offset value with `I` keyframes to move between the assembled and exploded views.

Index is useful for a static dataset, but it is not a persistent biological identity and its ordering may change between timepoints.

## Preserve identities through time

Loaded {{ svg("outliner_ob_pointcloud") }} label-mask instances carry their original integer object identity in the `oid` named attribute. For a tracked time series:

1. Read `oid` with an integer **Named Attribute** node.
2. Capture it on the **Instance** domain before transforming the subvolumes.
3. Calculate the position from that captured value rather than from **Index**.

This keeps the same tracked structure at the same calculated position while the source timepoint changes. Scale or remap large identity values before using them as offsets: multiplying a raw ID such as 1500 by a large distance can create an enormous merged grid.

For curated layouts, an imported CSV can map each `oid` to a chosen position. Use the same captured identity to look up the corresponding location.

## Merge the result back into a grid

Shader channels expect a grid, so connect the transformed instances to **Merge Subvolumes to Grid**. Set its **Holder**, then connect its **Grid** output to the channel bundle like any other microscopy grid.

**Voxel Spacing** sets the resolution of the merged output. Keep it coarse while editing, then reduce it for the final result if the subvolumes look distorted. The merged grid covers the complete transformed extent, so widely separated subvolumes and fine voxel spacing can make it very large.

!!! tip "Build the workflow progressively"
    First verify one source grid and one region set. Then add the split, transformation, identity handling, and merge steps in order. If you need help, share a screenshot of the complete node tree on the [image.sc forum](https://forum.image.sc/tag/microscopy-nodes).

The example tutorial uses the [meiotic-nucleus time series with masks](https://s3.embl.de/microscopynodes/meiotic_nucleus_masks.zarr), associated with [Čavka et al. (2025), *Multi-step implementation of meiotic crossover patterning*](https://doi.org/10.1101/2025.11.12.687980).
