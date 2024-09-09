# Microscopy Nodes Objects

Microscopy Nodes gathers its objects in multiple main holders, for different visualization types or functions. Most of the data representation Objects are internally geometry nodes objects loading collections in the `cache`. 

## Axes
The `Axes` object is always loaded and draws a grid of scale bars based on the number of pixels and the pixel size as defined when the data is loaded. 

Many axis settings are user-adaptable in the Geometry Nodes of the object. Here you can still adapt pixel size (this will not rescale for isotropy), which parts of the grid are drawn, line thickness. 

In Microscopy Nodes, it is chosen to only implement a scale grid, as the default cameras in Blender are perspective cameras, where a scale bar is not valid. If you do want an orthographic camera with scale bar, it is recommended to use the fields in the `Axes` Geometry Nodes, where the data's size in blender meters is calculated to scale a cube object.

## Volumes 
Volumes are the default loaded object in Microscopy Nodes. This will render the microscopy data in a way where each voxel contributes to the rendered output, either by emitting light (analogous to fire) or absorbing light (analogous to fog). Switching between these modes can be quickly done through the [emission setting](./settings.md#emission).

Thresholding the data can be done in the per-channel Materials of the volumes object, easiest found in the `Shading` workflow, with a histogram of the data on load.

## Surfaces
Surfaces are isosurface objects, where a Mesh is generated at a specific threshold value to render the microscopic volume as a surface. This thus only shows a thresholded version of the image. The resolution default can be set with the [surface resolution setting](./settings.md#surface-resolution), but can be easily changed (if not at `Actual`) in the Geometry Nodes of the surfaces object. 

This is not only a useful mode for image data, but also for masks where the values of the separate objects do not matter, as it is more adaptable, lightweight and blender-integrated than the labelmasks.

This is essentially the same loaded [vdb data](./internals.md#vdb-files) as in the volumes, just with a [Volume to Mesh](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/volume/operations/volume_to_mesh.html#volume-to-mesh-node) Geometry Node in between. This means it is trivial to load either the volume or the mesh if the other is loaded, so if only one is activated the other will be loaded in deactivated state.

## Masks
Label masks - defined as masks where each object has a separate integer value - can be loaded as separate meshes when loaded as label mask in Microscopy Nodes. This will split apart each object, and turn it into a mesh and load this mesh into Blender. This means it can be slow/RAM-heavy as meshing is not alway a fast operation, and that changing [surface resolution](./settings.md#surface-resolution) will involve remeshing all objects.

However, this load mode does give a way to have every individual object in your mask have a separate color, and also Geometry Nodes programmable selectability and transformation of specific object identities.

## Slice cube
The slice cube is a generic cube with alpha set to 0 so it is invisible. When the slice cube is moved or scaled, this will slice all the objects in the data objects to show only the parts inside the cube. 

The slicing behaviour is defined in the Material of each separate object, which points to get the coordinates of the Slice Cube. This means that you can always swap out the Slice Cube for another cube, if you want to slice two different channels/objects differently. 