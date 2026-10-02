# How Microscopy Nodes works

Microscopy Nodes separates the **data**, its **3D representation**, and its **appearance**. Knowing which layer you want to change makes the rest of the interface much easier to navigate.

```text
TIFF or OME-Zarr
    → resolution and channel selection
    → cached volume grids
    → Geometry Nodes: objects, masks, and data processing
    → Shader Nodes: color, opacity, and lighting
    → camera, annotation, and output
```

## 1. Source data and cache

The :blender-MICROSCOPY_NODES: loading panel reads the metadata from a TIFF or OME-Zarr source. Here you choose the resolution, time range, storage location, and which channels should be loaded.

Microscopy Nodes converts the selected data into local files that Blender can use. The source data is not edited.

!!! tip "Start with a small scale"
    Choose a small multiscale level while you build the scene. You can later use :blender-FILE_REFRESH: **Reload** to replace it with higher-resolution data without rebuilding the visualization.

## 2. Choose a representation

Each channel can produce one or more Blender objects:

- :blender-OUTLINER_OB_VOLUME: **Volume** preserves the full 3D intensity grid.
- :blender-OUTLINER_OB_SURFACE: **Surface** extracts a mesh above an intensity threshold.
- :blender-OUTLINER_OB_POINTCLOUD: **Label mask** turns integer segmentation labels into separate mesh regions.

See [Objects and modifiers](./3_objects.md) for the controls belonging to each representation.

## 3. Geometry Nodes changes what data exists

The :blender-GEOMETRY_NODES: Geometry Nodes workspace controls how the cached data becomes geometry or grids in the scene. Use it when you want to:

- include or exclude channels;
- change an isosurface threshold;
- mask or crop data;
- create separate inside and outside regions;
- sample a volume on a mesh;
- process a volume before visualization.

The [slicing and masking](./slicing_masking.md), [large-data](./large_data.md), and [mesh-projection](./mesh_projection.md) workflows all build on this layer.

### Coordinate spaces

Microscopy Nodes moves the data through three coordinate spaces:

1. **Array space** is the source image grid. Positions are voxel indices and the channel's affine transform carries the pixel size and orientation.
2. **Unit space** is used inside Geometry Nodes. The affine transform converts array positions into the dataset's physical unit, such as nm or µm. Channels from the same holder meet in this space, which keeps masks, surfaces, grids, and measurements aligned.
3. **World space** is Blender's scene. The :blender-OUTLINER_OB_EMPTY: holder is the parent of the generated objects; its scale converts the dataset unit to the selected Blender scale, and its location, rotation, and any user transform place the complete dataset in the world.

In short: the channel affine maps **array space → unit space**, then the holder transform maps **unit space → world space**. Move or scale the holder when you want to transform the whole dataset without changing how its channels align internally.

## 4. Shader Nodes changes appearance

The :blender-MATERIAL: Shading workspace controls how the existing data interacts with color, transparency, and light. Use it when you want to change:

- intensity limits and contrast;
- the color lookup table;
- transparency or density;
- emission versus scattering;
- surface material properties.

Start with [Adjust color, contrast, and opacity](./visualization.md), then use the detailed [shading reference](./4_shading.md) when you need a specific node.

## 5. Scene and output

The :blender-VIEW_CAMERA: camera, :blender-TIME: timeline, :blender-WORLD: world lighting, and :blender-OUTPUT: output settings belong to Blender's scene. They can be animated independently of the microscopy data.

Use [Cameras, animation, and output](./creating_output.md) to compose a result and [Scale bars, grids, and time labels](./annotation.md) to communicate physical or temporal scale.

## Where should I make a change?

- To load another scale or time range, use the :blender-MICROSCOPY_NODES: **Microscopy Nodes** panel.
- To include or exclude a loaded channel, use the :blender-MODIFIER: **modifier** of the relevant data object.
- To crop, mask, project, or process data, use :blender-GEOMETRY_NODES: **Geometry Nodes**.
- To change color, contrast, or transparency, use :blender-MATERIAL: **Shader Nodes**.
- To move the complete dataset, transform its :blender-OUTLINER_OB_EMPTY: **holder** object.
- To animate or render the scene, use the :blender-VIEW_CAMERA: **camera**, timeline, and :blender-OUTPUT: **output settings**.
