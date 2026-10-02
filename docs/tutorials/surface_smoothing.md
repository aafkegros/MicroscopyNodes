# Surface modification

After loading a :blender-OUTLINER_DATA_POINTCLOUD: labelmask or :blender-OUTLINER_DATA_SURFACE: surface, the geometry is often still quite jagged. 

This can be edited through two techniques:

- changing the **mesh density** in the [preferences](./preferences.md) and reloading
- adding smoothing modifiers
- editing the mesh using sculpting or modeling

## Adding modifiers

Modifiers can be added under the :blender-MODIFIER: modifiers in the :blender-PROPERTIES: properties, under the `+ Add Modifier` button. 

Useful smoothing modifiers are:

- :blender-MOD_SUBSURF: Surface Subdivision
- :blender-MOD_SMOOTH: Smooth 
- :blender-MOD_SMOOTH: Smooth Corrective
- :blender-MOD_SMOOTH: Smooth by Laplacian

Especially :blender-MOD_SUBSURF: Surface Subdivision is useful, although this can create too many vertices (which you could then again destroy with something such as a :blender-MOD_DECIM: Decimate modifier)

These methods will distort your geometry, so use only in cases where you can allow this.

