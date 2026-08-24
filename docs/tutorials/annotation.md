# Scale bars, grids, and time labels

Scientific annotations communicate the physical and temporal scale of a microscopy visualization.

{{ youtube("J1YDsjgBWeE", 560, 315) }}

## Check the coordinate mapping

Blender works internally in meters. The {{ svg("con_sizelike") }} input transform in the Microscopy Nodes panel maps the dataset's physical unit into a practical Blender scene size. **Auto** chooses an appropriate mapping for the dataset.

The {{ svg("orientation_parent") }} input location chooses whether the dataset is centered in XY, centered in XYZ, or placed from its source origin.

## Customize the scale grid

Every loaded dataset includes an {{ svg("outliner_ob_mesh") }} **Axes** object. Its {{ svg("modifier") }} modifier controls:

- physical units per grid step;
- grid or bounding-box display;
- line thickness;
- front-face culling;
- which planes are visible.

The Axes object can be moved and scaled independently after cropping or masking. Its generated grid remains tied to the dataset's physical scale.

## Use an accurate scale bar

!!! warning "Use an orthographic camera"
    A conventional scale bar is only globally accurate with an {{ svg("view_camera") }} **orthographic camera**. Perspective makes objects nearer the camera appear larger, so one bar cannot represent every depth in the image.

To add a scale bar:

1. Add an Empty object.
2. Open its {{ svg("geometry_nodes") }} Geometry Nodes modifier and create a node tree.
3. Under `Add > Microscopy Nodes > Annotation`, add either **Dynamic Scale Bar** or **Rigid Scale Bar**.
4. Use **To Active Camera** to align the annotation to the render plane.

The dynamic bar derives its physical length from the scale of its object. The rigid bar exposes an explicit value, unit, visual size, and decimal precision.

## Add a time label

The **Time Annotation** node converts an animated frame value into text. Provide:

- the frame input;
- the acquisition period per source frame;
- the input and display units;
- the desired text size.

For a microscopy time series, connect it to the animated holder frame so that retiming and pauses are reflected in the label.

See [Work with time-series data](./time_series.md) for retiming and [Cameras, animation, and output](./creating_output.md) for camera setup.
