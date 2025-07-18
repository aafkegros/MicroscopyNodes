# Shading

**Shading** encompasses the visualization of Blender's objects. The shading options can be found in two places:

- in the <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> Shader Nodes workspace, find this in the <span class="icon">
--8<-- "./docs/html_blender_icons/topbar.svg"
</span> topbar.
- in the <span class="icon">
--8<-- "./docs/html_blender_icons/material.svg"
</span> material tab of the <span class="icon">
--8<-- "./docs/html_blender_icons/properties.svg"
</span> properties.

These two locations contain the same information, laid out in different ways. Often it's easiest to **edit** in the <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> Shader Nodes workspace. And use the <span class="icon">
--8<-- "./docs/html_blender_icons/properties.svg"
</span> properties to **switch** between channels. Quick changes can be easier in the <span class="icon">
--8<-- "./docs/html_blender_icons/properties.svg"
</span> properties as well.


The default Microscopy Nodes shaders are built from <span class="icon">
--8<-- "./docs/html_blender_icons/nodetree.svg"
</span> [nodes](./nodes.md), and contains information on how the object interacts with **light** and its transparency. The defaults are listed here separately for the different [Microscopy Nodes data-objects](./3_objects.md).

## Volume Shading

The Shader Nodes workspace <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> when selecting a Microscopy Nodes <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_data_volume.svg"
</span> volume: 

![workspace outtlined](<../figures/Screenshot 2025-07-11 at 09.59.35.png>){: style="height:130px"}

### Data Loading

![alt text](<../figures/Screenshot 2025-07-11 at 09.54.52.png>)

This is where the data gets read out from the vdb grid (as handed over from the Geometry Nodes) and gets normalized. You will usually not need to edit this.

??? warning "Reusing shaders"
    The normalization that is done in **Normalize Data**  is dependent on the specific data, as it rescales the min and max value of the data to 0 and 1 - after it's already transformed to small floating point values for saving to .vdb files. 
    
    Essentially, this means its best to **keep the normalization** of new data when you replace the rest. Hopefully this can be smoother in the future, but this depends on Blender/Geometry Nodes development in volume handling.

    ![unfolded loading](<../figures/Screenshot 2025-07-11 at 09.55.12.png>) 
    
### Pixel Intensities

The pixel intensities rescale the min and max value, and thus the linear interpolation of the data. This is analogous to a Fiji **Brightness & Contrast** window.

You can move the two handles to move the **min** and **max**. 

![alt text](<../figures/Screenshot 2025-07-11 at 09.55.00.png>)

??? note "How this works"
    This is a Blender `Color Ramp` that only outputs Alpha, and not Color. We feed in normalized data between 0 and 1 (as represented in histogram) and map this to the color ramp. The color ramp is two nodes of alpha 0 (min) and 1 (max). 

    This also means you can add extra nodes in here if you want nonlinearity in your pixel intensities, or flip the nodes to invert. However, it is often easier to just change the colormap.

### Color LUT

![alt text](<../figures/Screenshot 2025-07-11 at 09.55.20.png>){: style="height:200px"}
![alt text](<../figures/Screenshot 2025-07-11 at 10.32.13.png>){: style="height:200px"}

The lookup tables are `Color Ramp` objects, LUTs can be edited:

- **Editing** handles
    - You can drag to change its position and click on it to get a color picker. To change contrast, its recommended to change the *pixel intensities* instead of the color.
    - The bottom fields are the *index*, *position* and *color* of the selected field - allowing editing of the handles with more precision
- **Replacing** the LUT by <span class="icon">
--8<-- "./docs/html_blender_icons/mouse_rmb.svg"
</span> right clicking the LUT and selecting <span class="icon">
--8<-- "./docs/html_blender_icons/color.svg"
</span> LUTs. This lists multiple [colormaps](https://cmap-docs.readthedocs.io).
    - <span class="icon">
--8<-- "./docs/html_blender_icons/ipo_linear.svg"
</span> Sequential, monotonic rising or falling, often good for microscopy
    - <span class="icon">
--8<-- "./docs/html_blender_icons/lincurve.svg"
</span> Diverging, distinctive middle of the colormap
    - <span class="icon">
--8<-- "./docs/html_blender_icons/mesh_circle.svg"
</span> Cyclical, start and end together
    - <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_data_pointcloud.svg"
</span> Qualitative, separates consecutive values, good for labelmasks
    - <span class="icon">
--8<-- "./docs/html_blender_icons/add.svg"
</span> Miscellaneous
    - <span class="icon">
--8<-- "./docs/html_blender_icons/mesh_plane.svg"
</span> Single Color, gives a new black-to-white colormap, to easily edit LUTs
- <span class="icon">
--8<-- "./docs/html_blender_icons/arrow_leftright.svg"
</span> Flipping the LUT
    - either under the down-carrot or under <span class="icon">
  --8<-- "./docs/html_blender_icons/mouse_rmb.svg"
  </span> right clicking the LUT
    - Flipped LUTs can be [loaded by default](./preferences.md)

### Opacity

![opacity](<../figures/Screenshot 2025-07-11 at 09.55.24.png>)

The tranparency window describes the total contribution of each voxel to the image. If you are in an emission mode, this defines the volume **brightness**, in scattering mode, this describes the volume **density**.

Here there are multiple options:

- Clip Min
    - Sets all values at 0 as transparent (left from the **min** in *Pixel Intensities*).
- Clip Max
    - Sets all values at 1 to transparent (right from the **max** in *Pixel Intensities*).
- Alpha Baseline
    - Constant alpha for all voxels that are not *Clipped*.
- Alpha Multiplier
    - Alpha value that multiplies the input values, and thus linearly increases with intensity. Does not affect *Clipped* values. Adds onto *Alpha Baseline*.

### Shaders (emission/scatter)

This is where the *Microscopy Nodes* pre-processing hooks into the default Blender volume interfaces. This is split between an <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_light.svg"
</span> emissive and <span class="icon">
--8<-- "./docs/html_blender_icons/light.svg"
</span> scattering setup. Currently the easiest way to switch between them is through [reloading](./2_loading_data.md).
![alt text](<../figures/Screenshot 2025-07-11 at 12.03.08.png>){: style="height:200px"}
![alt text](<../figures/Screenshot 2025-07-11 at 12.07.29.png>){: style="height:200px"}

??? note "Advanced"
    Some things are editable in here, such as the **Anisotropy** of the scattering, which defines whether there is more backward scattering (less penetrant) or more forward scattering. 

    Additionally, by Adding nodes (from the `Add` menu or `Shift + A`), and connecting these together, it's possible to make combined setups for emissive and scattering shaders.
### Slice Cube
![alt text](<../figures/Screenshot 2025-07-11 at 12.03.14.png>)

The Slice Cube section allows slicing of the volume. This has an <span class="icon">
--8<-- "./docs/html_blender_icons/object_data.svg"
</span> Object pointer to a cube in the scene (by default the loaded slice cube).

The object gets fed into the slicer.

## Surface shading


## Labelmask shading

