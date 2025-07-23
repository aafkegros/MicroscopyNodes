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
</span> nodes, and contains information on how the object interacts with **light** and its transparency. The defaults are listed here separately for the different [Microscopy Nodes data-objects](./3_objects.md).

## Volume Shading

The Shader Nodes workspace <span class="icon">
--8<-- "./docs/html_blender_icons/workspace.svg"
</span> when selecting a Microscopy Nodes <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_data_volume.svg"
</span> volume: 

![workspace outtlined](../figures/volume_shader_overview.png){: style="height:130px"}

### Data Loading

![alt text](../figures/shader_input_folded.png)

This is where the data gets read out from the vdb grid (as handed over from the Geometry Nodes) and gets normalized. You will usually not need to edit this.

??? warning "Reusing shaders"
    The normalization that is done in **Normalize Data**  is dependent on the specific data, as it rescales the min and max value of the data to 0 and 1 - after it's already transformed to small floating point values for saving to .vdb files. 
    
    Essentially, this means its best to **keep the normalization** of new data when you replace the rest. Hopefully this can be smoother in the future, but this depends on Blender/Geometry Nodes development in volume handling.

    ![unfolded loading](<../figures/shader_input>) 
    
### Pixel Intensities

The pixel intensities rescale the min and max value, and thus the linear interpolation of the data. This is analogous to a Fiji **Brightness & Contrast** window.

You can move the two handles to move the **min** and **max**. 

![alt text](../figures/volume_shader_intensities.png)

??? note "How this works"
    This is a Blender `Color Ramp` that only outputs Alpha, and not Color. We feed in normalized data between 0 and 1 (as represented in histogram) and map this to the color ramp. The color ramp is two nodes of alpha 0 (min) and 1 (max). 

    This also means you can add extra nodes in here if you want nonlinearity in your pixel intensities, or flip the nodes to invert. However, it is often easier to just change the colormap.

### Color LUT

![alt text](../figures/color_lut_bw.png){: style="height:200px"}
![alt text](../figures/lut_viridis.png){: style="height:200px"}

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

![opacity](../figures/volume_shader_transparency.png)

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
![alt text](../figures/volume_shader_emission.png){: style="height:200px"}
![alt text](../figures/volume_shader_density.png){: style="height:200px"}

??? note "Advanced"
    Some things are editable in here, such as the **Anisotropy** of the scattering, which defines whether there is more backward scattering (less penetrant) or more forward scattering. 

    Additionally, by Adding nodes (from the `Add` menu or `Shift + A`), and connecting these together, it's possible to make combined setups for emissive and scattering shaders.
### Slice Cube
![alt text](../figures/shader_slice_cube.png)

The Slice Cube section allows slicing of the volume. This has an <span class="icon">
--8<-- "./docs/html_blender_icons/object_data.svg"
</span> Object pointer to a cube in the scene (by default the loaded slice cube).

The object bounding box gets fed into the slicer, which sets all regions outside the bounding box to transparent. 

??? note "How this works"
    As shown if you press the <span class="small-icon">
    --8<-- "./docs/html_blender_icons/nodetree.svg"
    </span> icon at the top right of the group, how the slicing node works is to take the remapped locations as the **Texture Coordinate** input provides (mapping the data to the coordinates of the cube space) and compare these to the boundes (1, -1). If positions are not in the range of the cube space, the shader is set to a *Transparent Shader*.

## Surface shading

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_data_surface.svg"
</span> Surface object shader is more simple than the volumetric, as it can only have **one color**, although it can have many properties. The shader does not explicitly load the data, as the data interaction is all done through the threshold in the <span class="icon">
--8<-- "./docs/html_blender_icons/modifier.svg"
</span> Geometry options.

![surface shader overview](<../figures/Screenshot 2025-07-21 at 15.42.21.png>)

### Color LUT

![alt text](<../figures/Screenshot 2025-07-21 at 15.48.18.png>)

The color lookup table works similar to the [volume color LUT](#color-lut). However, the surface can only display one value, so the `Fac` value defines where along the lookup table the color is drawn from. 

This is done to more easily align different channels. For a regular **color picker** you can leave the `Fac` at `1` and click the rightmost handle. The other way would be to replace this box with a color box (`Add > Input > RGB`)

### Mesh shading

![alt text](<../figures/Screenshot 2025-07-21 at 15.56.07.png>){: style="height:350px"}

The **Principled BSDF** node is a combined node that combines features to create different material properties. The [Blender manual](https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html) <span class="icon">
--8<-- "./docs/html_blender_icons/blender.svg"
</span> gives a complete manual to its features. 

By default this has two inputs set differently from Blender default, the **Base Color** and **Emission Color/Strength**. These colors are set to link to the Color LUT. 

The **Emission Strength** is set to 0 or 0.5 depending on whether this was loaded with <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_ob_light.svg"
</span> emission on or <span class="icon">
--8<-- "./docs/html_blender_icons/light.svg"
</span> emission off. This is done for consistency, and that dark scenes have masks and surfaces as clearly visible as data, without setting up lighting.

??? warning "Emission can 'flatten' objects"
    The feeling of **depth** in 3D rendering is often due to the interaction of objects with light. When things are emitting light themselves, they can often look flat. For more feeling of depth, it might be better to load with <span class="small-icon">
    --8<-- "./docs/html_blender_icons/light.svg"
    </span> emission off, and set up some form of lighting.

### Slice cube

This is exactly similar to the [volume Slice Cube](#slice-cube).

## Labelmask shading

The <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_data_pointcloud.svg"
</span> label mask shader is very similar to the <span class="icon">
--8<-- "./docs/html_blender_icons/outliner_data_surface.svg"
</span> Surface shader, but is able to read out and use the `object id` to color by.

![alt text](<../figures/Screenshot 2025-07-21 at 16.26.38.png>)

### Object ID handling

![id handling](<../figures/Screenshot 2025-07-22 at 11.30.24.png>)

The `object id` (the value in the label mask) is connected and retrievable from the vertices of the labelmask objects. 

This is led into a group that maps it to values between 0 and 1 for the LUT. This has the option of a **revolving sequence**: ideal for a categorical colormap with distinct values, making the object ids loop through these values. Or a **consecutive sequence** scaling all values linearly along the `object id`s, ideal for linear colormaps.

### Color LUT

The color lookup table works similar to the [volume color LUT](#color-lut). Often categorical colormaps work best for labelmasks, if you have only one channel of masks.

### Slice cube

This is exactly similar to the [volume Slice Cube](#slice-cube).
