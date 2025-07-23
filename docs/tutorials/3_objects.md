# 3. Objects

Microscopy Nodes loads your microscopy data as different types of **objects**, depending on how you loaded each channel.

![mic nodes objects](../figures/outliner_objects.png)

Each type of object is placed in a <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_empty.svg"
</span>  **holder** collection. The **Axes** and **Slice Cube** are always present.

You can select an object by clicking on it in the <span class="icon">
--8<-- "./docs/html_blender_icons/outliner.svg"
</span> outliner (as shown in the screenshot) and change its properties:

- Change **underlying data** in the <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> modifier menu of the <span class="icon">
--8<-- "./docs/html_blender_icons/properties.svg"
</span> properties or the (*advanced*) Geometry Nodes workspace <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> 
- Change **visualization** in the <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> material menu of the <span class="icon">
--8<-- "./docs/html_blender_icons/properties.svg"
</span> properties or the Shader Nodes workspace <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> 

The exact settings and where to change them change per object, so see below.

---

## Holder 

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_empty.svg"
</span> **Holder** is an empty object which is the `parent` of the other Microscopy Nodes objects. 

The holder can be **scaled**, **moved** and **rotated** and then **all of its objects** will be transformed along with it.

## Axes

The  <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_mesh.svg"
</span> **Axes** object is always loaded with your dataset. It draws a **scale grid** based on the number of pixels and pixel size, and pixel unit.

-  <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> Geometry options
    - `pixel unit` per tick
      > The distance between grid lines
    - Grid
      > Whether to draw a grid or only a box 
    - Line thickness
      > Thickness of lines in arbitrary units
    - Frontface culling
      > If ticked, clips out the axes that are closest to the camera or viewpoint, so that they do not obstruct the view.
    - Separate planes
      > For each plane (xy bottom, top etc) you can check whether they will be drawn

-  <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> Shader options
    - Color 

Scale grids can be **moved**, **scaled** and **rotated** independently of the holder without losing their accuracy.

!!! note "Bars versus grids"
    In *Microscopy Nodes*, only scale grids are shown. Blender’s default cameras are perspective cameras, where traditional scale bars are not very meaningful. We'll probably add support for some form of scale bar in the future for orthographic renders.

---

## Volumes

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_volume.svg"
</span> **Volume** holds channels of **volumetric** data, which can be rendered either as emitting or scattering light. It is generated when you enable <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_volume.svg"
</span>  **Volume** during loading.

-  <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> Geometry options
    - Included channels
      > If channels are not included, they are also not loaded into RAM 
-  <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> [Shader options](./4_shading.md#volume-shading)
    - Pixel intensities
    - Opacity calculation
    - Color LUT

The easiest way to edit a volume shader is in the <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> Shader Nodes workspace, where you can most easily switch between channels in the <span class="icon">
--8<-- "./docs/html_blender_icons/properties.svg"
</span> properties.

You can toggle between emission and scattering modes using the <span class="icon">
--8<-- "./docs/html_blender_icons/light.svg"
</span> emission toggle in [loading](./2_loading_data.md).

---

## Surfaces

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_mesh.svg"
</span> **Surface** object is a mesh extracted from a volume using an **isosurface threshold**. It is generated when you enable <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_surface.svg"
</span>  **Surface** during loading.

- <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> Geometry options
    - Included channels
    - Threshold
      > The intensity value above which the surface is extracted. 
    - Voxel size *(only listed if <span class="icon">
--8<-- "./docs/html_blender_icons/preferences.svg"
</span> [Mesh Resolution](./preferences.md) is not `Actual`)*
      > Interactive scalable unit for mesh detail

- <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> [Shader options](./4_shading.md#surface-shading)
    - Standard mesh shading parameters (color, opacity etc)



---

## Label Masks

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_mesh.svg"
</span> **Label Mask** object is a mesh generated from a **label image**, such as a segmentation channel. It is generated when you enable <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_pointcloud.svg"
</span>  **Labelmask** during loading.

**Each value** in the volume is turned into a separate mesh.

- <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> Geometry options
    - Included channels

- <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> [Shader options](./4_shading.md#labelmask-shading)
    - Color per label 
    - Revolving colormap or linearly distributed among objects
    - Standard mesh shading parameters (color, opacity etc)

---

## Slice Cube

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_mesh.svg"
</span> **Slice Cube** is a movable object that defines the visibility of other objects.

The slice cube is inherently nothing else than a Cube with a transparent shader. The linkage to its transparency is done from the <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> shader **of the sliced object**. This means you can also add a new cube and point to this instead.

This has no <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> Geometry options or <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> Shader options


---

???+ info "How the **Microcopy Nodes** objects work"
    The data objects are Geometry Nodes objects that reference preloaded data stored in the `cache` collection. In the **Geometry Nodes** workspace <span class="small-icon">
    --8<-- "./docs/html_blender_icons/workspace.svg"
    </span> you can add edit the loaded data and add modifiers.  
