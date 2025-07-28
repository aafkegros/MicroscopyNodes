# Surface modification

After loading a {{ svg("outliner_data_pointcloud") }} labelmask or {{ svg("outliner_data_surface") }} surface, the geometry is often still quite jagged. 

This can be edited through two techniques:

- changing the **mesh density** in the [preferences](./preferences.md) and reloading
- adding smoothing modifiers
- editing the mesh using sculpting or modeling

## Adding modifiers

Modifiers can be added under the {{ svg("modifier") }} modifiers in the {{ svg("properties") }} properties, under the `+ Add Modifier` button. 

Useful smoothing modifiers are:

- {{ svg("mod_subsurf") }} Surface Subdivision
- {{ svg("mod_smooth") }} Smooth 
- {{ svg("mod_smooth") }} Smooth Corrective
- {{ svg("mod_smooth") }} Smooth by Laplacian

Especially {{ svg("mod_subsurf") }} Surface Subdivision is useful, although this can create too many vertices (which you could then again destroy with something such as a {{ svg("mod_decim") }} Decimate modifier)

These methods will distort your geometry, so use only in cases where you can allow this.

